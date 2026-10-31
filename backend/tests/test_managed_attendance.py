"""Managed attendance integration tests against the existing two-tenant staff fixture."""
from datetime import date, datetime, timedelta

import pytest

from app.models.attendance import (
    AttendanceCorrectionRequest, AttendanceRecord, LeaveRequest,
    OutletGeoFence, Shift, StaffShiftAssignment,
)
from app.services import attendance_service as service
from test_staff_management import _auth, ctx


TABLES = (
    Shift.__table__, OutletGeoFence.__table__, AttendanceRecord.__table__,
    StaffShiftAssignment.__table__, LeaveRequest.__table__,
    AttendanceCorrectionRequest.__table__,
)


@pytest.fixture
def attendance(ctx):
    for table in TABLES:
        table.create(ctx["db"].bind)
    return ctx


def call(ctx, actor, method, path, **kwargs):
    return getattr(ctx["client"], method)(f"/api/{path}", headers=_auth(ctx[actor]), **kwargs)


def location(**overrides):
    return {"latitude": 18.5204, "longitude": 73.8567, "accuracy_meters": 5,
            "device_id": "phone-device-1234", **overrides}


def fence(ctx, manager="manager_a", **overrides):
    return call(ctx, manager, "put", "manager/attendance/geofence",
                json={"latitude": 18.5204, "longitude": 73.8567, "radius_meters": 150, **overrides})


def clock(ctx, staff="staff_a", kind="in", **overrides):
    return call(ctx, staff, "post", f"staff/attendance/clock-{kind}", json=location(**overrides))


def record(ctx, staff="staff_a"):
    user = ctx[staff]
    row = AttendanceRecord(company_id=user.company_id, outlet_id=user.outlet_id, staff_id=user.id,
                           work_date=date.today(), clock_in=datetime.utcnow() - timedelta(hours=8),
                           clock_out=datetime.utcnow() - timedelta(hours=1),
                           in_latitude=18.5204, in_longitude=73.8567,
                           device_hash=service.device_fingerprint(user.id, "phone-device-1234"), flags=[])
    ctx["db"].add(row)
    ctx["db"].commit()
    return row


def dates():
    return {"start": "2026-01-01", "end": "2026-12-31"}


def test_haversine_zero_and_known_distance():
    assert service.haversine_meters(0, 0, 0, 0) == 0
    assert 110000 < service.haversine_meters(0, 0, 1, 0) < 112000


@pytest.mark.parametrize("latitude,longitude", [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_geofence_coordinates_rejected(attendance, latitude, longitude):
    assert fence(attendance, latitude=latitude, longitude=longitude).status_code == 422


@pytest.mark.parametrize("radius", [0, -1, 5001])
def test_geofence_radius_rejected(attendance, radius):
    assert fence(attendance, radius_meters=radius).status_code == 422


@pytest.mark.parametrize("actor", ["staff_a", "staff_b", "ceo_a"])
def test_manager_geofence_access_denied(attendance, actor):
    assert fence(attendance, actor).status_code == 403


def test_clock_requires_configured_fence(attendance):
    assert clock(attendance).status_code == 409


def test_clock_in_out_and_device_binding(attendance):
    assert fence(attendance).status_code == 200
    first = clock(attendance)
    assert first.status_code == 200, first.text
    assert first.json()["data"]["record"]["clock_out"] is None
    assert clock(attendance).status_code == 409
    assert clock(attendance, kind="out", device_id="another-device-123").status_code == 403
    assert clock(attendance, kind="out").status_code == 200
    assert clock(attendance, kind="out").status_code == 409
    assert clock(attendance).status_code == 409


@pytest.mark.parametrize("overrides,expected", [
    ({"latitude": 0}, 403), ({"longitude": 0}, 403),
    ({"mock_location": True}, 422), ({"latitude": 100}, 422),
    ({"accuracy_meters": -1}, 422), ({"device_id": "x"}, 422),
])
def test_invalid_punches_do_not_create_records(attendance, overrides, expected):
    fence(attendance)
    assert clock(attendance, **overrides).status_code == expected
    assert attendance["db"].query(AttendanceRecord).count() == 0


def test_low_accuracy_flag(attendance):
    fence(attendance)
    assert "low_location_accuracy" in clock(attendance, accuracy_meters=125).json()["data"]["record"]["flags"]


def test_fence_disabled_denies_punch(attendance):
    fence(attendance, enabled=False)
    assert clock(attendance).status_code == 409


def test_staff_cannot_punch_for_other_staff(attendance):
    fence(attendance)
    response = call(attendance, "staff_b", "post", "staff/attendance/clock-in",
                    json={**location(), "staff_id": attendance["staff_a"].id})
    assert response.status_code == 409  # No geofence for staff B's outlet.
    assert attendance["db"].query(AttendanceRecord).count() == 0


@pytest.mark.parametrize("actor", ["manager_a", "manager_b", "ceo_a"])
def test_only_staff_can_punch(attendance, actor):
    fence(attendance)
    assert clock(attendance, actor).status_code == 403


@pytest.mark.parametrize("actor", ["staff_a", "staff_b", "ceo_a"])
def test_only_manager_can_create_shifts(attendance, actor):
    response = call(attendance, actor, "post", "manager/attendance/shifts",
                    json={"name": "Morning", "start_time": "09:00", "end_time": "17:00"})
    assert response.status_code == 403


@pytest.mark.parametrize("start,end", [("25:00", "17:00"), ("09:99", "17:00"), ("9:00", "17:00"),
                                        ("09:00", "17:70")])
def test_shift_invalid_time(attendance, start, end):
    assert call(attendance, "manager_a", "post", "manager/attendance/shifts",
                json={"name": "Morning", "start_time": start, "end_time": end}).status_code == 422


def test_shift_assignment_scope_and_duplicate(attendance):
    response = call(attendance, "manager_a", "post", "manager/attendance/shifts",
                    json={"name": "Morning", "start_time": "09:00", "end_time": "17:00"})
    assert response.status_code == 201, response.text
    shift_id = response.json()["data"]["shift"]["id"]
    payload = {"staff_id": attendance["staff_a"].id, "shift_id": shift_id, "work_date": "2026-10-01"}
    assert call(attendance, "manager_b", "post", "manager/attendance/assignments", json=payload).status_code == 404
    assert call(attendance, "manager_a", "post", "manager/attendance/assignments", json=payload).status_code == 201
    assert call(attendance, "manager_a", "post", "manager/attendance/assignments", json=payload).status_code == 409
    assert call(attendance, "staff_a", "get", "staff/attendance/shifts",
                params={"start": "2026-10-01", "end": "2026-10-01"}).json()["data"]["assignments"][0]["shift_id"] == shift_id


@pytest.mark.parametrize("actor", ["staff_a", "staff_b", "ceo_a"])
def test_manager_roster_denied(attendance, actor):
    assert call(attendance, actor, "get", "manager/attendance/shifts").status_code == 403


@pytest.mark.parametrize("actor,expected", [("staff_a", 403), ("staff_b", 403), ("manager_b", 200), ("manager_c", 200)])
def test_manager_record_scope(attendance, actor, expected):
    record(attendance)
    response = call(attendance, actor, "get", "manager/attendance", params=dates())
    assert response.status_code == expected
    if expected == 200:
        assert response.json()["data"]["records"] == []


def test_staff_and_ceo_record_scope(attendance):
    row = record(attendance)
    response = call(attendance, "staff_a", "get", "staff/attendance", params=dates())
    assert response.status_code == 200, response.text
    assert len(response.json()["data"]["records"]) == 1
    assert call(attendance, "staff_b", "get", "staff/attendance", params=dates()).json()["data"]["records"] == []
    assert len(call(attendance, "ceo_a", "get", "company-ceo/attendance", params=dates()).json()["data"]["records"]) == 1
    response = call(attendance, "ceo_a", "get", "company-ceo/attendance",
                    params={**dates(), "outlet_id": attendance["outlet_c"].id})
    assert response.status_code == 404


@pytest.mark.parametrize("actor", ["staff_a", "staff_b", "manager_a", "manager_b"])
def test_ceo_read_denied(attendance, actor):
    assert call(attendance, actor, "get", "company-ceo/attendance", params=dates()).status_code == 403


def test_leave_overlap_and_review(attendance):
    payload = {"start_date": "2026-11-01", "end_date": "2026-11-03", "leave_type": "sick", "reason": "Recovery"}
    first = call(attendance, "staff_a", "post", "staff/attendance/leaves", json=payload)
    assert first.status_code == 201
    leave_id = first.json()["data"]["id"]
    assert call(attendance, "staff_a", "post", "staff/attendance/leaves", json=payload).status_code == 409
    assert call(attendance, "manager_b", "post", f"manager/attendance/leaves/{leave_id}/review",
                json={"decision": "approved", "note": "Accepted"}).status_code == 404
    assert call(attendance, "manager_a", "post", f"manager/attendance/leaves/{leave_id}/review",
                json={"decision": "approved", "note": "Accepted"}).status_code == 200
    assert call(attendance, "manager_a", "post", f"manager/attendance/leaves/{leave_id}/review",
                json={"decision": "rejected", "note": "Changed"}).status_code == 409


@pytest.mark.parametrize("start,end", [("2026-11-02", "2026-11-01"), ("2026-01-01", "2027-12-31")])
def test_invalid_leave_range(attendance, start, end):
    assert call(attendance, "staff_a", "post", "staff/attendance/leaves",
                json={"start_date": start, "end_date": end, "leave_type": "sick", "reason": "Recovery"}).status_code == 422


@pytest.mark.parametrize("actor", ["manager_a", "manager_b", "ceo_a"])
def test_only_staff_request_leave(attendance, actor):
    assert call(attendance, actor, "post", "staff/attendance/leaves",
                json={"start_date": "2026-10-01", "end_date": "2026-10-02",
                      "leave_type": "sick", "reason": "Recovery"}).status_code == 403


def test_correction_review_preserves_audit_flags(attendance):
    row = record(attendance)
    changed = (row.clock_in + timedelta(minutes=10)).isoformat()
    response = call(attendance, "staff_a", "post", "staff/attendance/corrections",
                    json={"record_id": row.id, "requested_clock_in": changed, "reason": "Missed punch"})
    assert response.status_code == 201, response.text
    request_id = response.json()["data"]["id"]
    assert call(attendance, "staff_a", "post", "staff/attendance/corrections",
                json={"record_id": row.id, "requested_clock_in": changed, "reason": "Missed punch"}).status_code == 409
    assert call(attendance, "manager_b", "post", f"manager/attendance/corrections/{request_id}/review",
                json={"decision": "approved", "note": "Verified"}).status_code == 404
    assert call(attendance, "manager_a", "post", f"manager/attendance/corrections/{request_id}/review",
                json={"decision": "approved", "note": "Verified"}).status_code == 200
    attendance["db"].refresh(row)
    assert row.clock_in.isoformat() == changed
    assert "manager_corrected" in row.flags


@pytest.mark.parametrize("actor,target", [("staff_b", "staff_a"), ("staff_a", "staff_b"), ("staff_a", "staff_c")])
def test_correction_other_staff_record_denied(attendance, actor, target):
    row = record(attendance, target)
    response = call(attendance, actor, "post", "staff/attendance/corrections",
                    json={"record_id": row.id, "requested_clock_out": datetime.utcnow().isoformat(),
                          "reason": "Missed punch"})
    assert response.status_code == 404


@pytest.mark.parametrize("actor", ["staff_a", "staff_b", "ceo_a"])
def test_only_manager_review_leave(attendance, actor):
    assert call(attendance, actor, "post", "manager/attendance/leaves/1/review",
                json={"decision": "approved", "note": "Accepted"}).status_code == 403


@pytest.mark.parametrize("actor", ["staff_a", "staff_b", "ceo_a"])
def test_only_manager_review_correction(attendance, actor):
    assert call(attendance, actor, "post", "manager/attendance/corrections/1/review",
                json={"decision": "approved", "note": "Accepted"}).status_code == 403


def test_payroll_aggregation_and_export(attendance):
    row = record(attendance)
    attendance["db"].add(LeaveRequest(company_id=row.company_id, outlet_id=row.outlet_id,
        staff_id=row.staff_id, start_date=date(2026, 10, 1), end_date=date(2026, 10, 2),
        leave_type="sick", reason="Recovery", status="approved"))
    attendance["db"].commit()
    summary = call(attendance, "manager_a", "get", "manager/attendance/payroll", params=dates())
    assert summary.status_code == 200, summary.text
    assert summary.json()["data"]["summary"][0]["approved_leave_days"] == 2
    assert summary.json()["data"]["summary"][0]["days_present"] == 1
    exported = call(attendance, "manager_a", "get", "manager/attendance/payroll/export", params=dates())
    assert exported.status_code == 200
    assert f"{row.staff_id},1," in exported.text
    assert call(attendance, "manager_b", "get", "manager/attendance/payroll", params=dates()).json()["data"]["summary"] == []


@pytest.mark.parametrize("path", [
    "manager/attendance", "manager/attendance/payroll", "manager/attendance/payroll/export",
    "company-ceo/attendance", "company-ceo/attendance/payroll",
])
def test_invalid_date_ranges(attendance, path):
    actor = "ceo_a" if path.startswith("company-ceo") else "manager_a"
    assert call(attendance, actor, "get", path,
                params={"start": "2026-10-03", "end": "2026-10-01"}).status_code == 422
