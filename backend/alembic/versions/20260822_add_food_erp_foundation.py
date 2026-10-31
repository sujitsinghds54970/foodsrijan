"""Add FoodSrijan ERP foundation tables.

Revision ID: 20260822_add_food_erp_foundation
Revises: 9b7c6caa4f72
Create Date: 2026-08-22 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260822_add_food_erp_foundation"
down_revision: Union[str, Sequence[str], None] = "9b7c6caa4f72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_companies_id"), "companies", ["id"], unique=False)

    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_brands_id"), "brands", ["id"], unique=False)
    op.create_index(op.f("ix_brands_company_id"), "brands", ["company_id"], unique=False)

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_departments_id"), "departments", ["id"], unique=False)
    op.create_index(op.f("ix_departments_company_id"), "departments", ["company_id"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False, unique=True),
        sa.Column("code", sa.String(length=150), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_permissions_id"), "permissions", ["id"], unique=False)
    op.create_index(op.f("ix_permissions_code"), "permissions", ["code"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)
    op.create_index(op.f("ix_roles_company_id"), "roles", ["company_id"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True, nullable=False),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), primary_key=True, nullable=False),
    )

    op.create_table(
        "user_companies",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), primary_key=True, nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=True),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_user_roles_id"), "user_roles", ["id"], unique=False)
    op.create_index(op.f("ix_user_roles_user_id"), "user_roles", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_roles_role_id"), "user_roles", ["role_id"], unique=False)

    op.create_table(
        "business_suppliers",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("contact_person", sa.String(length=150), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("gstin", sa.String(length=80), nullable=True),
        sa.Column("payment_terms", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_business_suppliers_id"), "business_suppliers", ["id"], unique=False)
    op.create_index(op.f("ix_business_suppliers_company_id"), "business_suppliers", ["company_id"], unique=False)

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("current_company_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("company_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("brand_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.create_foreign_key("fk_users_current_company_id_companies", "companies", ["current_company_id"], ["id"])
        batch_op.create_foreign_key("fk_users_company_id_companies", "companies", ["company_id"], ["id"])
        batch_op.create_foreign_key("fk_users_brand_id_brands", "brands", ["brand_id"], ["id"])

    with op.batch_alter_table("branches") as batch_op:
        batch_op.add_column(sa.Column("company_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("brand_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_branches_company_id_companies", "companies", ["company_id"], ["id"])
        batch_op.create_foreign_key("fk_branches_brand_id_brands", "brands", ["brand_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("branches") as batch_op:
        batch_op.drop_constraint("fk_branches_brand_id_brands", type_="foreignkey")
        batch_op.drop_constraint("fk_branches_company_id_companies", type_="foreignkey")
        batch_op.drop_column("brand_id")
        batch_op.drop_column("company_id")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_brand_id_brands", type_="foreignkey")
        batch_op.drop_constraint("fk_users_company_id_companies", type_="foreignkey")
        batch_op.drop_constraint("fk_users_current_company_id_companies", type_="foreignkey")
        batch_op.drop_column("is_super_admin")
        batch_op.drop_column("brand_id")
        batch_op.drop_column("company_id")
        batch_op.drop_column("current_company_id")

    with op.batch_alter_table("roles") as batch_op:
        batch_op.drop_column("is_system_role")

    op.drop_table("business_suppliers")
    op.drop_table("user_roles")
    op.drop_table("user_companies")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
    op.drop_table("departments")
    op.drop_table("brands")
    op.drop_table("companies")
