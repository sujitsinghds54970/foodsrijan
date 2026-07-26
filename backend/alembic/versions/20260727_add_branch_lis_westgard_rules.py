"""add branch lis westgard rules table

Revision ID: 20260727_add_branch_lis_westgard_rules
Revises: 20260727_add_branch_lis_phase34_features
Create Date: 2026-07-27 02:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260727_add_branch_lis_westgard_rules"
down_revision: Union[str, Sequence[str], None] = "20260727_add_branch_lis_phase34_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "branch_lis_westgard_rules",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("rule_code", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("branch_id", "rule_code", name="uq_branch_lis_westgard_rule_code"),
    )
    op.create_index("ix_branch_lis_westgard_rules_id", "branch_lis_westgard_rules", ["id"], unique=False)
    op.create_index("ix_branch_lis_westgard_rules_branch_id", "branch_lis_westgard_rules", ["branch_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_branch_lis_westgard_rules_branch_id", table_name="branch_lis_westgard_rules")
    op.drop_index("ix_branch_lis_westgard_rules_id", table_name="branch_lis_westgard_rules")
    op.drop_table("branch_lis_westgard_rules")
