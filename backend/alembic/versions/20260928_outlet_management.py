"""Add outlet management fields, manager fields, and login attempt ledger.

Revision ID: 20260928_outlet_management
Revises: 20260927_super_ceo_profile
Create Date: 2026-09-28 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260928_outlet_management"
down_revision: Union[str, Sequence[str], None] = "20260927_super_ceo_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BRANCH_OUTLET_COLUMNS = (
    sa.Column("slug", sa.String(length=120), nullable=True),
    sa.Column("code", sa.String(length=20), nullable=True),
    sa.Column("outlet_type", sa.String(length=32), nullable=True),
    sa.Column("status", sa.String(length=32), nullable=True, server_default="active"),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("opening_date", sa.Date(), nullable=True),
    sa.Column("cover_photo_url", sa.String(length=2048), nullable=True),
    sa.Column("address_line_1", sa.String(length=255), nullable=True),
    sa.Column("address_line_2", sa.String(length=255), nullable=True),
    sa.Column("country", sa.String(length=2), nullable=True),
    sa.Column("region", sa.String(length=32), nullable=True),
    sa.Column("timezone", sa.String(length=64), nullable=True),
    sa.Column("opening_time", sa.String(length=5), nullable=True),
    sa.Column("closing_time", sa.String(length=5), nullable=True),
    sa.Column("operating_days", sa.JSON(), nullable=True),
    sa.Column("seating_capacity", sa.Integer(), nullable=True),
    sa.Column("kitchen_capacity", sa.Integer(), nullable=True),
    sa.Column("is_delivery_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("is_dine_in_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("is_takeaway_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("delivery_radius_km", sa.Float(), nullable=True),
    sa.Column("fssai_license", sa.String(length=14), nullable=True),
    sa.Column("gstin", sa.String(length=15), nullable=True),
    sa.Column("trade_license", sa.String(length=100), nullable=True),
    sa.Column("fire_safety_certificate", sa.String(length=100), nullable=True),
    sa.Column("health_permit", sa.String(length=100), nullable=True),
    sa.Column("license_expiry_date", sa.Date(), nullable=True),
    sa.Column("rent_amount", sa.DECIMAL(precision=14, scale=2), nullable=True),
    sa.Column("security_deposit", sa.DECIMAL(precision=14, scale=2), nullable=True),
    sa.Column("lease_start_date", sa.Date(), nullable=True),
    sa.Column("lease_end_date", sa.Date(), nullable=True),
    sa.Column("bank_account_name", sa.String(length=255), nullable=True),
    sa.Column("bank_account_number", sa.String(length=34), nullable=True),
    sa.Column("ifsc_code", sa.String(length=11), nullable=True),
    sa.Column("bank_name", sa.String(length=255), nullable=True),
    sa.Column("branch_name", sa.String(length=255), nullable=True),
    sa.Column("upi_id", sa.String(length=100), nullable=True),
    sa.Column("cost_center_code", sa.String(length=50), nullable=True),
    sa.Column("manager_contact_email", sa.String(length=254), nullable=True),
    sa.Column("manager_contact_phone", sa.String(length=32), nullable=True),
    sa.Column("outlet_email", sa.String(length=254), nullable=True),
    sa.Column("outlet_phone", sa.String(length=32), nullable=True),
    sa.Column("google_maps_url", sa.String(length=2048), nullable=True),
    sa.Column("swiggy_store_id", sa.String(length=64), nullable=True),
    sa.Column("zomato_store_id", sa.String(length=64), nullable=True),
    sa.Column(
        "created_by",
        sa.Integer(),
        sa.ForeignKey("users.id", name="fk_branches_created_by_users"),
        nullable=True,
    ),
    sa.Column("deleted_at", sa.DateTime(), nullable=True),
    sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("metadata", sa.JSON(), nullable=True),
)

USER_MANAGER_COLUMNS = (
    sa.Column("is_outlet_manager", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column(
        "outlet_id",
        sa.Integer(),
        sa.ForeignKey("branches.id", name="fk_users_outlet_id_branches"),
        nullable=True,
    ),
    sa.Column("manager_assigned_at", sa.DateTime(), nullable=True),
    sa.Column(
        "manager_assigned_by",
        sa.Integer(),
        sa.ForeignKey("users.id", name="fk_users_manager_assigned_by_users"),
        nullable=True,
    ),
    sa.Column("manager_photo_url", sa.String(length=2048), nullable=True),
    sa.Column("manager_address", sa.Text(), nullable=True),
    sa.Column("manager_bank_account_name", sa.String(length=255), nullable=True),
    sa.Column("manager_bank_account_number", sa.String(length=34), nullable=True),
    sa.Column("manager_ifsc_code", sa.String(length=11), nullable=True),
    sa.Column("manager_bank_name", sa.String(length=255), nullable=True),
)


def _add_missing_columns(op, inspector, table_name, columns):
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    missing = [column for column in columns if column.name not in existing]
    if missing:
        with op.batch_alter_table(table_name) as batch_op:
            for column in missing:
                batch_op.add_column(column)


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    _add_missing_columns(op, inspector, "branches", BRANCH_OUTLET_COLUMNS)
    _add_missing_columns(op, inspector, "users", USER_MANAGER_COLUMNS)

    inspector = sa.inspect(connection)
    branch_indexes = {index["name"] for index in inspector.get_indexes("branches")}
    if "uq_branches_company_code" not in branch_indexes:
        op.create_index("uq_branches_company_code", "branches", ["company_id", "code"], unique=True)
    if "uq_branches_company_slug" not in branch_indexes:
        op.create_index("uq_branches_company_slug", "branches", ["company_id", "slug"], unique=True)
    if "uq_branches_gstin" not in branch_indexes:
        op.create_index("uq_branches_gstin", "branches", ["gstin"], unique=True)
    if "ix_branches_company_status" not in branch_indexes:
        op.create_index("ix_branches_company_status", "branches", ["company_id", "status"], unique=False)
    if "ix_branches_is_deleted" not in branch_indexes:
        op.create_index("ix_branches_is_deleted", "branches", ["is_deleted"], unique=False)

    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_outlet_id" not in user_indexes:
        op.create_index("ix_users_outlet_id", "users", ["outlet_id"], unique=False)
    if "ix_users_company_outlet_manager" not in user_indexes:
        op.create_index("ix_users_company_outlet_manager", "users", ["company_id", "is_outlet_manager"], unique=False)
    if "uq_users_active_outlet_manager" not in user_indexes:
        op.create_index(
            "uq_users_active_outlet_manager",
            "users",
            ["outlet_id"],
            unique=True,
            sqlite_where=sa.text("is_outlet_manager = 1 AND is_active = 1"),
            postgresql_where=sa.text("is_outlet_manager AND is_active"),
        )

    if not inspector.has_table("login_attempts"):
        op.create_table(
            "login_attempts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("subject_hash", sa.String(length=64), nullable=False),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("was_successful", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_login_attempts_occurred_at", "login_attempts", ["occurred_at"], unique=False)
        op.create_index(
            "ix_login_attempts_subject_time", "login_attempts", ["subject_hash", "occurred_at"], unique=False
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if inspector.has_table("login_attempts"):
        op.drop_table("login_attempts")

    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    for name in ("uq_users_active_outlet_manager", "ix_users_company_outlet_manager", "ix_users_outlet_id"):
        if name in user_indexes:
            op.drop_index(name, table_name="users")

    branch_indexes = {index["name"] for index in inspector.get_indexes("branches")}
    for name in (
        "ix_branches_is_deleted",
        "ix_branches_company_status",
        "uq_branches_gstin",
        "uq_branches_company_slug",
        "uq_branches_company_code",
    ):
        if name in branch_indexes:
            op.drop_index(name, table_name="branches")

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        for column in reversed(USER_MANAGER_COLUMNS):
            if column.name in user_columns:
                batch_op.drop_column(column.name)

    branch_columns = {column["name"] for column in inspector.get_columns("branches")}
    with op.batch_alter_table("branches") as batch_op:
        for column in reversed(BRANCH_OUTLET_COLUMNS):
            if column.name in branch_columns:
                batch_op.drop_column(column.name)
