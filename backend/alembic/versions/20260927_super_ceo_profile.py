"""Add Super CEO profile and parent company foundation.

Revision ID: 20260927_super_ceo_profile
Revises: 20260926_extend_company_model
Create Date: 2026-09-27 14:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260927_super_ceo_profile"
down_revision: Union[str, Sequence[str], None] = "20260926_extend_company_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USER_PROFILE_COLUMNS = (
    sa.Column("display_name", sa.String(length=150), nullable=True),
    sa.Column("bio", sa.Text(), nullable=True),
    sa.Column("profile_photo_url", sa.String(length=2048), nullable=True),
    sa.Column("cover_photo_url", sa.String(length=2048), nullable=True),
    sa.Column("date_of_birth", sa.Date(), nullable=True),
    sa.Column("gender", sa.String(length=32), nullable=True),
    sa.Column("location_city", sa.String(length=120), nullable=True),
    sa.Column("location_state", sa.String(length=120), nullable=True),
    sa.Column("location_country", sa.String(length=120), nullable=True),
    sa.Column("timezone", sa.String(length=64), nullable=True),
    sa.Column("emergency_contact_name", sa.String(length=150), nullable=True),
    sa.Column("emergency_contact_phone", sa.String(length=32), nullable=True),
    sa.Column("assistant_name", sa.String(length=150), nullable=True),
    sa.Column("assistant_email", sa.String(length=254), nullable=True),
    sa.Column("assistant_phone", sa.String(length=32), nullable=True),
    sa.Column("preferred_contact_method", sa.String(length=20), nullable=True),
    sa.Column("qualifications", sa.JSON(), nullable=True),
    sa.Column("certifications", sa.JSON(), nullable=True),
    sa.Column("achievements", sa.JSON(), nullable=True),
    sa.Column("preferences", sa.JSON(), nullable=True),
    sa.Column("recovery_email", sa.String(length=254), nullable=True),
    sa.Column("recovery_phone", sa.String(length=32), nullable=True),
)

PARENT_COMPANY_COLUMNS = (
    sa.Column("banner_url", sa.String(length=2048), nullable=True),
    sa.Column("accent_color", sa.String(length=7), nullable=True),
    sa.Column("display_font", sa.String(length=100), nullable=True),
    sa.Column("body_font", sa.String(length=100), nullable=True),
    sa.Column("ios_app_url", sa.String(length=2048), nullable=True),
    sa.Column("android_app_url", sa.String(length=2048), nullable=True),
    sa.Column("whatsapp_business_number", sa.String(length=32), nullable=True),
    sa.Column("last_funding_round_date", sa.Date(), nullable=True),
    sa.Column("total_funding_raised", sa.DECIMAL(precision=18, scale=2), nullable=True),
    sa.Column("is_parent", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("profile_draft", sa.JSON(), nullable=True),
    sa.Column("published_at", sa.DateTime(), nullable=True),
    sa.Column(
        "published_by",
        sa.Integer(),
        sa.ForeignKey("users.id", name="fk_companies_published_by_users"),
        nullable=True,
    ),
)


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    company_columns = {column["name"] for column in inspector.get_columns("companies")}

    if missing := [column for column in USER_PROFILE_COLUMNS if column.name not in user_columns]:
        with op.batch_alter_table("users") as batch_op:
            for column in missing:
                batch_op.add_column(column)

    if missing := [column for column in PARENT_COMPANY_COLUMNS if column.name not in company_columns]:
        with op.batch_alter_table("companies") as batch_op:
            for column in missing:
                batch_op.add_column(column)

    company_indexes = {index["name"] for index in sa.inspect(connection).get_indexes("companies")}
    if "ix_companies_is_parent" not in company_indexes:
        op.create_index("ix_companies_is_parent", "companies", ["is_parent"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    company_indexes = {index["name"] for index in sa.inspect(connection).get_indexes("companies")}
    if "ix_companies_is_parent" in company_indexes:
        op.drop_index("ix_companies_is_parent", table_name="companies")

    company_columns = {column["name"] for column in sa.inspect(connection).get_columns("companies")}
    with op.batch_alter_table("companies") as batch_op:
        for column in reversed(PARENT_COMPANY_COLUMNS):
            if column.name in company_columns:
                batch_op.drop_column(column.name)

    user_columns = {column["name"] for column in sa.inspect(connection).get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        for column in reversed(USER_PROFILE_COLUMNS):
            if column.name in user_columns:
                batch_op.drop_column(column.name)
