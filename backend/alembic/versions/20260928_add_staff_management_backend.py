"""Add staff management user fields and self-service requests.

Revision ID: 20260928_add_staff_management_backend
Revises: 20260928_outlet_management
Create Date: 2026-09-28 15:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260928_add_staff_management_backend"
down_revision: Union[str, Sequence[str], None] = "20260928_outlet_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USER_STAFF_COLUMNS = (
    sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("staff_role", sa.String(length=40), nullable=True),
    sa.Column("employee_code", sa.String(length=40), nullable=True),
    sa.Column("manager_id", sa.Integer(), sa.ForeignKey("users.id", name="fk_users_manager_id_users"), nullable=True),
    sa.Column("staff_assigned_at", sa.DateTime(), nullable=True),
    sa.Column("staff_assigned_by", sa.Integer(), sa.ForeignKey("users.id", name="fk_users_staff_assigned_by_users"), nullable=True),
    sa.Column("alternate_phone", sa.String(length=32), nullable=True),
    sa.Column("blood_group", sa.String(length=10), nullable=True),
    sa.Column("marital_status", sa.String(length=32), nullable=True),
    sa.Column("current_address", sa.Text(), nullable=True),
    sa.Column("permanent_address", sa.Text(), nullable=True),
    sa.Column("emergency_contact_relation", sa.String(length=100), nullable=True),
    sa.Column("aadhaar_number", sa.String(length=32), nullable=True),
    sa.Column("pan_number", sa.String(length=16), nullable=True),
    sa.Column("voter_id", sa.String(length=32), nullable=True),
    sa.Column("driving_license", sa.String(length=32), nullable=True),
    sa.Column("passport_number", sa.String(length=32), nullable=True),
    sa.Column("bank_account_name", sa.String(length=255), nullable=True),
    sa.Column("bank_account_number", sa.String(length=34), nullable=True),
    sa.Column("ifsc_code", sa.String(length=11), nullable=True),
    sa.Column("bank_name", sa.String(length=255), nullable=True),
    sa.Column("branch_name", sa.String(length=255), nullable=True),
    sa.Column("upi_id", sa.String(length=100), nullable=True),
    sa.Column("experience_years", sa.Float(), nullable=True),
    sa.Column("previous_employer", sa.String(length=255), nullable=True),
    sa.Column("skills", sa.JSON(), nullable=True),
    sa.Column("joining_date", sa.Date(), nullable=True),
    sa.Column("employment_type", sa.String(length=20), nullable=True),
    sa.Column("probation_end_date", sa.Date(), nullable=True),
    sa.Column("salary_type", sa.String(length=20), nullable=True),
    sa.Column("monthly_salary", sa.DECIMAL(12, 2), nullable=True),
    sa.Column("daily_wage", sa.DECIMAL(12, 2), nullable=True),
    sa.Column("hourly_rate", sa.DECIMAL(12, 2), nullable=True),
    sa.Column("shift_preference", sa.String(length=100), nullable=True),
    sa.Column("weekly_off_day", sa.String(length=20), nullable=True),
    sa.Column("pf_applicable", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("esi_applicable", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("tds_applicable", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("deactivated_at", sa.DateTime(), nullable=True),
    sa.Column("deactivated_reason", sa.Text(), nullable=True),
    sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", name="fk_users_created_by_users"), nullable=True),
    sa.Column("updated_at", sa.DateTime(), nullable=True),
    sa.Column("deleted_at", sa.DateTime(), nullable=True),
    sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
)


def _add_missing_columns(table_name: str, columns: Sequence[sa.Column]) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    missing = [column for column in columns if column.name not in existing]
    if missing:
        with op.batch_alter_table(table_name) as batch_op:
            for column in missing:
                batch_op.add_column(column)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _add_missing_columns("users", USER_STAFF_COLUMNS)

    inspector = sa.inspect(bind)
    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_company_outlet_staff" not in user_indexes:
        op.create_index("ix_users_company_outlet_staff", "users", ["company_id", "outlet_id", "is_staff"], unique=False)
    if "uq_users_staff_phone_active" not in user_indexes:
        op.create_index(
            "uq_users_staff_phone_active",
            "users",
            ["phone"],
            unique=True,
            sqlite_where=sa.text("is_staff = 1 AND is_deleted = 0"),
            postgresql_where=sa.text("is_staff AND NOT is_deleted"),
        )
    if "uq_users_staff_outlet_employee_code" not in user_indexes:
        op.create_index(
            "uq_users_staff_outlet_employee_code",
            "users",
            ["outlet_id", "employee_code"],
            unique=True,
            sqlite_where=sa.text("is_staff = 1 AND is_deleted = 0 AND employee_code IS NOT NULL"),
            postgresql_where=sa.text("is_staff AND NOT is_deleted AND employee_code IS NOT NULL"),
        )
    if "uq_users_staff_aadhaar_active" not in user_indexes:
        op.create_index(
            "uq_users_staff_aadhaar_active",
            "users",
            ["aadhaar_number"],
            unique=True,
            sqlite_where=sa.text("is_staff = 1 AND is_deleted = 0 AND aadhaar_number IS NOT NULL"),
            postgresql_where=sa.text("is_staff AND NOT is_deleted AND aadhaar_number IS NOT NULL"),
        )

    if not inspector.has_table("staff_requests"):
        op.create_table(
            "staff_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("staff_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
            sa.Column("type", sa.String(length=40), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_staff_requests_staff_id", "staff_requests", ["staff_id"], unique=False)
        op.create_index("ix_staff_requests_company_outlet_status", "staff_requests", ["company_id", "outlet_id", "status"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("staff_requests"):
        request_indexes = {index["name"] for index in inspector.get_indexes("staff_requests")}
        if "ix_staff_requests_company_outlet_status" in request_indexes:
            op.drop_index("ix_staff_requests_company_outlet_status", table_name="staff_requests")
        if "ix_staff_requests_staff_id" in request_indexes:
            op.drop_index("ix_staff_requests_staff_id", table_name="staff_requests")
        op.drop_table("staff_requests")

    inspector = sa.inspect(bind)
    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    for index_name in (
        "uq_users_staff_aadhaar_active",
        "uq_users_staff_outlet_employee_code",
        "uq_users_staff_phone_active",
        "ix_users_company_outlet_staff",
    ):
        if index_name in user_indexes:
            op.drop_index(index_name, table_name="users")

    existing = {column["name"] for column in inspector.get_columns("users")}
    for column_name in reversed([column.name for column in USER_STAFF_COLUMNS]):
        if column_name in existing:
            with op.batch_alter_table("users") as batch_op:
                batch_op.drop_column(column_name)
