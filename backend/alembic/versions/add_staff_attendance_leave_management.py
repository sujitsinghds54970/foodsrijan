"""add advanced staff attendance and leave management

Revision ID: add_staff_attendance_leave_management
Revises: add_staff_tasks_notifications_self_service
Create Date: 2026-07-11 11:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_staff_attendance_leave_management"
down_revision = "add_staff_tasks_notifications_self_service"
branch_labels = None
depends_on = None


def upgrade() -> None:
    staff_attendance_status_enum = sa.Enum(
        "present",
        "late",
        "absent",
        "approved_leave",
        "work_from_home",
        name="staffattendancestatus",
    )
    attendance_dispute_status_enum = sa.Enum("open", "resolved", name="attendancedisputestatus")
    linked_device_type_enum = sa.Enum("biometric", "rfid", "mobile", name="linkeddevicetype")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    staff_attendance_status_enum.create(bind, checkfirst=True)
    attendance_dispute_status_enum.create(bind, checkfirst=True)
    linked_device_type_enum.create(bind, checkfirst=True)

    existing_columns = {col["name"] for col in inspector.get_columns("staff_attendance_logs")}

    if "date" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("date", sa.Date(), nullable=True))
    if "status" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("status", staff_attendance_status_enum, nullable=True))
    if "location_lat" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("location_lat", sa.Float(), nullable=True))
    if "location_lng" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("location_lng", sa.Float(), nullable=True))
    if "selfie_url" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("selfie_url", sa.String(), nullable=True))
    if "work_mode" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("work_mode", sa.String(length=30), nullable=True))
    if "wfh_reason" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("wfh_reason", sa.Text(), nullable=True))
    if "task" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("task", sa.Text(), nullable=True))
    if "task_status" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("task_status", sa.String(length=40), nullable=True))
    if "staff_note" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("staff_note", sa.Text(), nullable=True))
    if "is_remote" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("is_remote", sa.Boolean(), nullable=True))
    if "distance_from_branch_meters" not in existing_columns:
        op.add_column("staff_attendance_logs", sa.Column("distance_from_branch_meters", sa.Float(), nullable=True))

    op.execute("UPDATE staff_attendance_logs SET date = DATE(attendance_date) WHERE date IS NULL")
    op.execute("UPDATE staff_attendance_logs SET status = 'approved_leave' WHERE attendance_type = 'leave'")
    op.execute("UPDATE staff_attendance_logs SET status = 'absent' WHERE attendance_type = 'absent' AND status IS NULL")
    op.execute("UPDATE staff_attendance_logs SET status = 'present' WHERE status IS NULL")
    op.execute("UPDATE staff_attendance_logs SET work_mode = 'onsite' WHERE work_mode IS NULL")
    op.execute("UPDATE staff_attendance_logs SET task_status = 'Pending' WHERE task_status IS NULL")
    op.execute("UPDATE staff_attendance_logs SET is_remote = 0 WHERE is_remote IS NULL")

    branch_columns = {col["name"] for col in inspector.get_columns("branches")}
    if "latitude" not in branch_columns:
        op.add_column("branches", sa.Column("latitude", sa.Float(), nullable=True))
    if "longitude" not in branch_columns:
        op.add_column("branches", sa.Column("longitude", sa.Float(), nullable=True))

    leave_columns = {col["name"] for col in inspector.get_columns("staff_leave_requests")}
    if "start_time" not in leave_columns:
        op.add_column("staff_leave_requests", sa.Column("start_time", sa.DateTime(), nullable=True))
    if "end_time" not in leave_columns:
        op.add_column("staff_leave_requests", sa.Column("end_time", sa.DateTime(), nullable=True))
    if "duration_days" not in leave_columns:
        op.add_column("staff_leave_requests", sa.Column("duration_days", sa.Float(), nullable=True))
    if "duration_hours" not in leave_columns:
        op.add_column("staff_leave_requests", sa.Column("duration_hours", sa.Float(), nullable=True))
    if "attachments" not in leave_columns:
        op.add_column("staff_leave_requests", sa.Column("attachments", sa.String(), nullable=True))
    if "approved_by" not in leave_columns:
        op.add_column("staff_leave_requests", sa.Column("approved_by", sa.Integer(), nullable=True))
    if "approval_date" not in leave_columns:
        op.add_column("staff_leave_requests", sa.Column("approval_date", sa.DateTime(), nullable=True))

    existing_fks = {fk.get("name") for fk in inspector.get_foreign_keys("staff_leave_requests")}
    if bind.dialect.name != "sqlite" and "fk_staff_leave_requests_approved_by_users" not in existing_fks:
        op.create_foreign_key(
            "fk_staff_leave_requests_approved_by_users",
            "staff_leave_requests",
            "users",
            ["approved_by"],
            ["id"],
        )

    op.execute("UPDATE staff_leave_requests SET duration_days = total_days WHERE duration_days IS NULL")
    op.execute("UPDATE staff_leave_requests SET duration_hours = 0 WHERE duration_hours IS NULL")

    table_names = set(inspector.get_table_names())
    if "attendance_disputes" not in table_names:
        op.create_table(
            "attendance_disputes",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("staff_profile_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False),
            sa.Column("attendance_date", sa.Date(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("status", attendance_dispute_status_enum, nullable=False, server_default="open"),
            sa.Column("resolution_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_attendance_disputes_id", "attendance_disputes", ["id"])

    if "linked_devices" not in table_names:
        op.create_table(
            "linked_devices",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("staff_profile_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False),
            sa.Column("device_id", sa.String(length=120), nullable=False),
            sa.Column("device_type", linked_device_type_enum, nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_sync", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_linked_devices_id", "linked_devices", ["id"])


def downgrade() -> None:
    op.drop_index("ix_linked_devices_id", table_name="linked_devices")
    op.drop_table("linked_devices")

    op.drop_index("ix_attendance_disputes_id", table_name="attendance_disputes")
    op.drop_table("attendance_disputes")

    op.drop_constraint("fk_staff_leave_requests_approved_by_users", "staff_leave_requests", type_="foreignkey")
    op.drop_column("staff_leave_requests", "approval_date")
    op.drop_column("staff_leave_requests", "approved_by")
    op.drop_column("staff_leave_requests", "attachments")
    op.drop_column("staff_leave_requests", "duration_hours")
    op.drop_column("staff_leave_requests", "duration_days")
    op.drop_column("staff_leave_requests", "end_time")
    op.drop_column("staff_leave_requests", "start_time")

    op.drop_column("staff_attendance_logs", "wfh_reason")
    op.drop_column("staff_attendance_logs", "work_mode")
    op.drop_column("staff_attendance_logs", "distance_from_branch_meters")
    op.drop_column("staff_attendance_logs", "is_remote")
    op.drop_column("staff_attendance_logs", "staff_note")
    op.drop_column("staff_attendance_logs", "task_status")
    op.drop_column("staff_attendance_logs", "task")
    op.drop_column("staff_attendance_logs", "selfie_url")
    op.drop_column("staff_attendance_logs", "location_lng")
    op.drop_column("staff_attendance_logs", "location_lat")
    op.drop_column("staff_attendance_logs", "status")
    op.drop_column("staff_attendance_logs", "date")

    op.drop_column("branches", "longitude")
    op.drop_column("branches", "latitude")

    bind = op.get_bind()
    linked_device_type_enum = sa.Enum("biometric", "rfid", "mobile", name="linkeddevicetype")
    attendance_dispute_status_enum = sa.Enum("open", "resolved", name="attendancedisputestatus")
    staff_attendance_status_enum = sa.Enum(
        "present",
        "late",
        "absent",
        "approved_leave",
        "work_from_home",
        name="staffattendancestatus",
    )

    linked_device_type_enum.drop(bind, checkfirst=True)
    attendance_dispute_status_enum.drop(bind, checkfirst=True)
    staff_attendance_status_enum.drop(bind, checkfirst=True)
