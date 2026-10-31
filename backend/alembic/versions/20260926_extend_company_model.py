"""Extend companies and add company CEO assignment fields.

Revision ID: 20260926_extend_company_model
Revises: 20260925_add_theme_system
Create Date: 2026-09-26 18:51:20.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260926_extend_company_model"
down_revision: Union[str, Sequence[str], None] = "20260925_add_theme_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COMPANY_COLUMNS = (
    sa.Column("tagline", sa.String(length=255), nullable=True),
    sa.Column("logo_url", sa.String(length=2048), nullable=True),
    sa.Column("favicon_url", sa.String(length=2048), nullable=True),
    sa.Column("primary_color", sa.String(length=7), nullable=True),
    sa.Column("secondary_color", sa.String(length=7), nullable=True),
    sa.Column("founded_date", sa.Date(), nullable=True),
    sa.Column("legal_name", sa.String(length=255), nullable=True),
    sa.Column("registration_number", sa.String(length=100), nullable=True),
    sa.Column("gstin", sa.String(length=15), nullable=True),
    sa.Column("pan_number", sa.String(length=10), nullable=True),
    sa.Column("fssai_license", sa.String(length=14), nullable=True),
    sa.Column("cin_number", sa.String(length=21), nullable=True),
    sa.Column("registered_address", sa.Text(), nullable=True),
    sa.Column("corporate_address", sa.Text(), nullable=True),
    sa.Column("bank_account_name", sa.String(length=255), nullable=True),
    sa.Column("bank_account_number", sa.String(length=100), nullable=True),
    sa.Column("ifsc_code", sa.String(length=11), nullable=True),
    sa.Column("bank_name", sa.String(length=255), nullable=True),
    sa.Column("annual_revenue_range", sa.String(length=20), nullable=True),
    sa.Column("funding_stage", sa.String(length=40), nullable=True),
    sa.Column("headquarters_city", sa.String(length=120), nullable=True),
    sa.Column("headquarters_state", sa.String(length=120), nullable=True),
    sa.Column("headquarters_country", sa.String(length=120), nullable=True),
    sa.Column("headquarters_pincode", sa.String(length=20), nullable=True),
    sa.Column("operating_regions", sa.JSON(), nullable=True),
    sa.Column("number_of_branches", sa.Integer(), nullable=True),
    sa.Column("website_url", sa.String(length=2048), nullable=True),
    sa.Column("linkedin_url", sa.String(length=2048), nullable=True),
    sa.Column("instagram_url", sa.String(length=2048), nullable=True),
    sa.Column("facebook_url", sa.String(length=2048), nullable=True),
    sa.Column("twitter_url", sa.String(length=2048), nullable=True),
    sa.Column("youtube_url", sa.String(length=2048), nullable=True),
    sa.Column("mobile_app_url", sa.String(length=2048), nullable=True),
    sa.Column("support_email", sa.String(length=254), nullable=True),
    sa.Column("support_phone", sa.String(length=32), nullable=True),
    sa.Column("business_domain", sa.String(length=64), nullable=True),
    sa.Column("sub_domains", sa.JSON(), nullable=True),
    sa.Column("target_market", sa.String(length=16), nullable=True),
    sa.Column("employee_count_estimate", sa.String(length=32), nullable=True),
    sa.Column("business_description", sa.Text(), nullable=True),
    sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
    sa.Column("onboarding_status", sa.String(length=20), nullable=False, server_default="pending"),
    sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", name="fk_companies_created_by_users"), nullable=True),
    sa.Column("deleted_at", sa.DateTime(), nullable=True),
    sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("metadata", sa.JSON(), nullable=True),
)

USER_COLUMNS = (
    sa.Column("is_company_ceo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("ceo_assigned_at", sa.DateTime(), nullable=True),
    sa.Column("ceo_assigned_by", sa.Integer(), sa.ForeignKey("users.id", name="fk_users_ceo_assigned_by_users"), nullable=True),
    sa.Column("password_changed_at", sa.DateTime(), nullable=True),
    sa.Column("force_password_change", sa.Boolean(), nullable=False, server_default=sa.text("0")),
)


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    company_columns = {column["name"] for column in inspector.get_columns("companies")}
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if missing := [column for column in COMPANY_COLUMNS if column.name not in company_columns]:
        with op.batch_alter_table("companies") as batch_op:
            for column in missing:
                batch_op.add_column(column)
    if missing := [column for column in USER_COLUMNS if column.name not in user_columns]:
        with op.batch_alter_table("users") as batch_op:
            for column in missing:
                batch_op.add_column(column)

    op.execute(
        "UPDATE companies SET status = CASE WHEN is_active THEN 'active' ELSE 'inactive' END"
    )
    company_indexes = {index["name"] for index in sa.inspect(connection).get_indexes("companies")}
    user_indexes = {index["name"] for index in sa.inspect(connection).get_indexes("users")}
    for name, table, columns, unique in (
        ("uq_companies_legal_name", "companies", ["legal_name"], True),
        ("uq_companies_registration_number", "companies", ["registration_number"], True),
        ("uq_companies_gstin", "companies", ["gstin"], True),
        ("uq_companies_pan_number", "companies", ["pan_number"], True),
        ("ix_companies_status", "companies", ["status"], False),
        ("ix_companies_is_deleted", "companies", ["is_deleted"], False),
        ("ix_companies_business_domain", "companies", ["business_domain"], False),
        ("ix_companies_created_by", "companies", ["created_by"], False),
    ):
        if name not in company_indexes:
            op.create_index(name, table, columns, unique=unique)
    for name, columns in (
        ("ix_users_is_company_ceo", ["is_company_ceo"]),
        ("ix_users_company_id_ceo", ["company_id", "is_company_ceo"]),
    ):
        if name not in user_indexes:
            op.create_index(name, "users", columns, unique=False)
    if not sa.inspect(connection).has_table("rate_limit_entries"):
        op.create_table(
            "rate_limit_entries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("action", sa.String(length=50), nullable=False),
            sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("was_allowed", sa.Boolean(), nullable=False),
        )
    rate_limit_indexes = {index["name"] for index in sa.inspect(connection).get_indexes("rate_limit_entries")}
    for name, columns in (
        ("ix_rate_limit_entries_occurred_at", ["occurred_at"]),
        ("ix_rate_limit_actor_action_time", ["actor_id", "action", "occurred_at"]),
    ):
        if name not in rate_limit_indexes:
            op.create_index(name, "rate_limit_entries", columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_rate_limit_actor_action_time", table_name="rate_limit_entries")
    op.drop_index("ix_rate_limit_entries_occurred_at", table_name="rate_limit_entries")
    op.drop_table("rate_limit_entries")
    op.drop_index("ix_users_company_id_ceo", table_name="users")
    op.drop_index("ix_users_is_company_ceo", table_name="users")
    op.drop_index("ix_companies_created_by", table_name="companies")
    op.drop_index("ix_companies_business_domain", table_name="companies")
    op.drop_index("ix_companies_is_deleted", table_name="companies")
    op.drop_index("ix_companies_status", table_name="companies")
    op.drop_index("uq_companies_pan_number", table_name="companies")
    op.drop_index("uq_companies_gstin", table_name="companies")
    op.drop_index("uq_companies_registration_number", table_name="companies")
    op.drop_index("uq_companies_legal_name", table_name="companies")

    with op.batch_alter_table("users") as batch_op:
        for column in reversed(USER_COLUMNS):
            batch_op.drop_column(column.name)
    with op.batch_alter_table("companies") as batch_op:
        for column in reversed(COMPANY_COLUMNS):
            batch_op.drop_column(column.name)
