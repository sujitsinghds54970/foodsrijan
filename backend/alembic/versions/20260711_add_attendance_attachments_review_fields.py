"""add attachments and review fields to staff attendance logs

Revision ID: 20260711_add_attendance_attachments_review_fields
Revises: 20260711_fix_staff_attendance_followup_columns
Create Date: 2026-07-11 22:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_add_attendance_attachments_review_fields"
down_revision = "20260711_fix_staff_attendance_followup_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    attendance_columns = {col["name"] for col in inspector.get_columns("staff_attendance_logs")}

    if "attachments" not in attendance_columns:
        op.add_column("staff_attendance_logs", sa.Column("attachments", sa.JSON(), nullable=True))
    if "hr_remark" not in attendance_columns:
        op.add_column("staff_attendance_logs", sa.Column("hr_remark", sa.Text(), nullable=True))
    if "dispute_resolved" not in attendance_columns:
        op.add_column("staff_attendance_logs", sa.Column("dispute_resolved", sa.Boolean(), nullable=True))

    op.execute("UPDATE staff_attendance_logs SET dispute_resolved = 0 WHERE dispute_resolved IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    attendance_columns = {col["name"] for col in inspector.get_columns("staff_attendance_logs")}

    if "dispute_resolved" in attendance_columns:
        op.drop_column("staff_attendance_logs", "dispute_resolved")
    if "hr_remark" in attendance_columns:
        op.drop_column("staff_attendance_logs", "hr_remark")
    if "attachments" in attendance_columns:
        op.drop_column("staff_attendance_logs", "attachments")
