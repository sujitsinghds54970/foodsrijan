"""replace daily ops password with staff toggle

Revision ID: 20260711_replace_daily_ops_password_with_staff_toggle
Revises: 08e1282c63ce
Create Date: 2026-07-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260711_replace_daily_ops_password_with_staff_toggle"
down_revision: Union[str, Sequence[str], None] = "08e1282c63ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    branch_cols = _get_columns("branches")
    if "daily_ops_password_hash" in branch_cols:
        op.drop_column("branches", "daily_ops_password_hash")
    if "daily_ops_enabled_for_staff" in branch_cols:
        op.drop_column("branches", "daily_ops_enabled_for_staff")

    staff_cols = _get_columns("staff_profiles")
    if "can_access_daily_ops" not in staff_cols:
        op.add_column(
            "staff_profiles",
            sa.Column("can_access_daily_ops", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )


def downgrade() -> None:
    staff_cols = _get_columns("staff_profiles")
    if "can_access_daily_ops" in staff_cols:
        op.drop_column("staff_profiles", "can_access_daily_ops")

    branch_cols = _get_columns("branches")
    if "daily_ops_password_hash" not in branch_cols:
        op.add_column("branches", sa.Column("daily_ops_password_hash", sa.String(length=255), nullable=True))
    if "daily_ops_enabled_for_staff" not in branch_cols:
        op.add_column(
            "branches",
            sa.Column("daily_ops_enabled_for_staff", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )
