"""Add canonical authority foundation.

Revision ID: 20260925_add_canonical_authority_foundation
Revises: 20260822_add_food_erp_foundation
Create Date: 2026-09-25 16:11:26.557000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260925_add_canonical_authority_foundation"
down_revision: Union[str, Sequence[str], None] = "20260822_add_food_erp_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("is_super_ceo", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )

    op.create_table(
        "profile_types",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_profile_types_id"), "profile_types", ["id"], unique=False)
    op.create_index(op.f("ix_profile_types_code"), "profile_types", ["code"], unique=True)

    op.create_table(
        "profile_memberships",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("profile_type_id", sa.Integer(), sa.ForeignKey("profile_types.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=True),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_profile_memberships_id"), "profile_memberships", ["id"], unique=False)
    op.create_index(op.f("ix_profile_memberships_user_id"), "profile_memberships", ["user_id"], unique=False)
    op.create_index(op.f("ix_profile_memberships_profile_type_id"), "profile_memberships", ["profile_type_id"], unique=False)
    op.create_index(op.f("ix_profile_memberships_company_id"), "profile_memberships", ["company_id"], unique=False)
    op.create_index(op.f("ix_profile_memberships_brand_id"), "profile_memberships", ["brand_id"], unique=False)
    op.create_index(op.f("ix_profile_memberships_branch_id"), "profile_memberships", ["branch_id"], unique=False)

    op.create_table(
        "role_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=True),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_role_assignments_id"), "role_assignments", ["id"], unique=False)
    op.create_index(op.f("ix_role_assignments_user_id"), "role_assignments", ["user_id"], unique=False)
    op.create_index(op.f("ix_role_assignments_role_id"), "role_assignments", ["role_id"], unique=False)
    op.create_index(op.f("ix_role_assignments_company_id"), "role_assignments", ["company_id"], unique=False)
    op.create_index(op.f("ix_role_assignments_brand_id"), "role_assignments", ["brand_id"], unique=False)
    op.create_index(op.f("ix_role_assignments_branch_id"), "role_assignments", ["branch_id"], unique=False)

    op.create_index(
        "uq_users_active_super_ceo",
        "users",
        ["is_super_ceo"],
        unique=True,
        sqlite_where=sa.text("is_super_ceo = 1 AND is_active = 1"),
        postgresql_where=sa.text("is_super_ceo AND is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_active_super_ceo", table_name="users")
    op.drop_table("role_assignments")
    op.drop_table("profile_memberships")
    op.drop_table("profile_types")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_super_ceo")
