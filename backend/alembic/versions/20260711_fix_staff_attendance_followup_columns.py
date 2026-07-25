"""follow-up columns for attendance overhaul

Revision ID: 20260711_fix_staff_attendance_followup_columns
Revises: add_staff_attendance_leave_management
Create Date: 2026-07-11 19:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_fix_staff_attendance_followup_columns"
down_revision = "add_staff_attendance_leave_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    branch_columns = {col["name"] for col in inspector.get_columns("branches")}
    if "latitude" not in branch_columns:
        op.add_column("branches", sa.Column("latitude", sa.Float(), nullable=True))
    if "longitude" not in branch_columns:
        op.add_column("branches", sa.Column("longitude", sa.Float(), nullable=True))

    attendance_columns = {col["name"] for col in inspector.get_columns("staff_attendance_logs")}
    if "task" not in attendance_columns:
        op.add_column("staff_attendance_logs", sa.Column("task", sa.Text(), nullable=True))
    if "task_status" not in attendance_columns:
        op.add_column("staff_attendance_logs", sa.Column("task_status", sa.String(length=40), nullable=True))
    if "staff_note" not in attendance_columns:
        op.add_column("staff_attendance_logs", sa.Column("staff_note", sa.Text(), nullable=True))
    if "is_remote" not in attendance_columns:
        op.add_column("staff_attendance_logs", sa.Column("is_remote", sa.Boolean(), nullable=True))
    if "distance_from_branch_meters" not in attendance_columns:
        op.add_column("staff_attendance_logs", sa.Column("distance_from_branch_meters", sa.Float(), nullable=True))

    op.execute("UPDATE staff_attendance_logs SET task_status = 'Pending' WHERE task_status IS NULL")
    op.execute("UPDATE staff_attendance_logs SET is_remote = 0 WHERE is_remote IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    attendance_columns = {col["name"] for col in inspector.get_columns("staff_attendance_logs")}
    if "distance_from_branch_meters" in attendance_columns:
        op.drop_column("staff_attendance_logs", "distance_from_branch_meters")
    if "is_remote" in attendance_columns:
        op.drop_column("staff_attendance_logs", "is_remote")
    if "staff_note" in attendance_columns:
        op.drop_column("staff_attendance_logs", "staff_note")
    if "task_status" in attendance_columns:
        op.drop_column("staff_attendance_logs", "task_status")
    if "task" in attendance_columns:
        op.drop_column("staff_attendance_logs", "task")

    branch_columns = {col["name"] for col in inspector.get_columns("branches")}
    if "longitude" in branch_columns:
        op.drop_column("branches", "longitude")
    if "latitude" in branch_columns:
        op.drop_column("branches", "latitude")
