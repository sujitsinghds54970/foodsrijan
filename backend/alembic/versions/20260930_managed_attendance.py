"""Add tenant-scoped managed attendance, shifts, leave and correction ledger.

Revision ID: 20260930_managed_attendance
Revises: 20260928_add_staff_management_backend
"""
from alembic import op
import sqlalchemy as sa
from app.models.attendance import (
    AttendanceCorrectionRequest, AttendanceRecord, LeaveRequest,
    OutletGeoFence, Shift, StaffShiftAssignment,
)

revision = "20260930_managed_attendance"
down_revision = "20260928_add_staff_management_backend"
branch_labels = None
depends_on = None

TABLES = (
    Shift.__table__, OutletGeoFence.__table__, AttendanceRecord.__table__,
    StaffShiftAssignment.__table__, LeaveRequest.__table__,
    AttendanceCorrectionRequest.__table__,
)


def upgrade():
    for table in TABLES:
        op.create_table(
            table.name,
            *(column.copy() for column in table.columns),
            *(sa.UniqueConstraint(*(column.name for column in constraint.columns), name=constraint.name)
              for constraint in table.constraints if isinstance(constraint, sa.UniqueConstraint)),
            *(sa.CheckConstraint(str(constraint.sqltext), name=constraint.name)
              for constraint in table.constraints if isinstance(constraint, sa.CheckConstraint)),
        )
        for index in table.indexes:
            op.create_index(index.name, table.name, [column.name for column in index.columns], unique=index.unique)


def downgrade():
    for table in reversed(TABLES):
        op.drop_table(table.name)
