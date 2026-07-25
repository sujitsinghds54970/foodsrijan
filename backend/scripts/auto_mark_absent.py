from datetime import datetime, date

from app.database import SessionLocal
from app.models.hr import (
    StaffProfile,
    StaffAttendanceLog,
    DirectorAttendanceType,
    StaffAttendanceStatus,
    DirectorStaffStatus,
)


def run() -> int:
    db = SessionLocal()
    today = date.today()
    created = 0
    try:
        active_staff = db.query(StaffProfile).filter(
            StaffProfile.is_active.is_(True),
            StaffProfile.status == DirectorStaffStatus.ACTIVE,
        ).all()

        for staff in active_staff:
            existing = db.query(StaffAttendanceLog).filter(
                StaffAttendanceLog.staff_profile_id == staff.id,
                StaffAttendanceLog.date == today,
            ).first()

            if existing and existing.clock_in_time is not None:
                continue

            if existing and existing.status == StaffAttendanceStatus.APPROVED_LEAVE:
                continue

            if existing:
                existing.attendance_type = DirectorAttendanceType.ABSENT
                existing.status = StaffAttendanceStatus.ABSENT
                existing.task_status = existing.task_status or "Pending"
                created += 1
                continue

            db.add(
                StaffAttendanceLog(
                    staff_profile_id=staff.id,
                    branch_id=staff.branch_id,
                    date=today,
                    attendance_date=datetime.combine(today, datetime.min.time()),
                    attendance_type=DirectorAttendanceType.ABSENT,
                    status=StaffAttendanceStatus.ABSENT,
                    task_status="Pending",
                )
            )
            created += 1

        db.commit()
        return created
    finally:
        db.close()


if __name__ == "__main__":
    inserted = run()
    print(f"Auto-mark absent completed. Inserted rows: {inserted}")
