"""add_daily_ops_access_control_fields

Revision ID: 9f3aed9dfac2
Revises: 20260711_fix_staff_attendance_followup_columns
Create Date: 2026-07-11 19:11:41.147822

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f3aed9dfac2'
down_revision: Union[str, Sequence[str], None] = '20260711_fix_staff_attendance_followup_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("branches")}

    if "daily_ops_password_hash" not in existing_columns:
        op.add_column("branches", sa.Column("daily_ops_password_hash", sa.String(length=255), nullable=True))

    if "daily_ops_enabled_for_staff" not in existing_columns:
        op.add_column(
            "branches",
            sa.Column("daily_ops_enabled_for_staff", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )
        op.execute(sa.text("UPDATE branches SET daily_ops_enabled_for_staff = 0 WHERE daily_ops_enabled_for_staff IS NULL"))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("branches")}

    if "daily_ops_enabled_for_staff" in existing_columns:
        op.drop_column("branches", "daily_ops_enabled_for_staff")

    if "daily_ops_password_hash" in existing_columns:
        op.drop_column("branches", "daily_ops_password_hash")
