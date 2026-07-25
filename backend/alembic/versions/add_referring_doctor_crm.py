"""add referring doctor crm tables

Revision ID: add_referring_doctor_crm
Revises: add_daily_entry_module
Create Date: 2026-07-08 02:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "add_referring_doctor_crm"
down_revision = "add_daily_entry_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referring_doctors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("mobile", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("specialization", sa.String(length=100), nullable=True),
        sa.Column("degree", sa.String(length=120), nullable=True),
        sa.Column("hospital_clinic_affiliation", sa.String(length=255), nullable=True),
        sa.Column("years_of_experience", sa.Integer(), nullable=True),
        sa.Column("bank_account_number", sa.String(length=100), nullable=True),
        sa.Column("ifsc_code", sa.String(length=30), nullable=True),
        sa.Column("upi_id", sa.String(length=120), nullable=True),
        sa.Column("commission_percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("portal_username", sa.String(length=120), nullable=True),
        sa.Column("portal_password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referring_doctors_id", "referring_doctors", ["id"], unique=False)
    op.create_index("ix_referring_doctors_branch_id", "referring_doctors", ["branch_id"], unique=False)
    op.create_index("ix_referring_doctors_full_name", "referring_doctors", ["full_name"], unique=False)
    op.create_index("ix_referring_doctors_mobile", "referring_doctors", ["mobile"], unique=False)
    op.create_index("ix_referring_doctors_email", "referring_doctors", ["email"], unique=False)
    op.create_index("ix_referring_doctors_city", "referring_doctors", ["city"], unique=False)
    op.create_index("ix_referring_doctors_specialization", "referring_doctors", ["specialization"], unique=False)
    op.create_index("ix_referring_doctors_portal_username", "referring_doctors", ["portal_username"], unique=True)

    op.create_table(
        "referral_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("patient_name", sa.String(length=200), nullable=False),
        sa.Column("patient_mobile", sa.String(length=20), nullable=True),
        sa.Column("referred_on", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("revenue_amount", sa.DECIMAL(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("report_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("report_due_date", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["referring_doctors.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referral_logs_id", "referral_logs", ["id"], unique=False)
    op.create_index("ix_referral_logs_branch_id", "referral_logs", ["branch_id"], unique=False)
    op.create_index("ix_referral_logs_doctor_id", "referral_logs", ["doctor_id"], unique=False)
    op.create_index("ix_referral_logs_referred_on", "referral_logs", ["referred_on"], unique=False)

    op.create_table(
        "doctor_share_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["referring_doctors.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_doctor_share_links_id", "doctor_share_links", ["id"], unique=False)
    op.create_index("ix_doctor_share_links_branch_id", "doctor_share_links", ["branch_id"], unique=False)
    op.create_index("ix_doctor_share_links_doctor_id", "doctor_share_links", ["doctor_id"], unique=False)
    op.create_index("ix_doctor_share_links_token", "doctor_share_links", ["token"], unique=True)
    op.create_index("ix_doctor_share_links_expires_at", "doctor_share_links", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_doctor_share_links_expires_at", table_name="doctor_share_links")
    op.drop_index("ix_doctor_share_links_token", table_name="doctor_share_links")
    op.drop_index("ix_doctor_share_links_doctor_id", table_name="doctor_share_links")
    op.drop_index("ix_doctor_share_links_branch_id", table_name="doctor_share_links")
    op.drop_index("ix_doctor_share_links_id", table_name="doctor_share_links")
    op.drop_table("doctor_share_links")

    op.drop_index("ix_referral_logs_referred_on", table_name="referral_logs")
    op.drop_index("ix_referral_logs_doctor_id", table_name="referral_logs")
    op.drop_index("ix_referral_logs_branch_id", table_name="referral_logs")
    op.drop_index("ix_referral_logs_id", table_name="referral_logs")
    op.drop_table("referral_logs")

    op.drop_index("ix_referring_doctors_portal_username", table_name="referring_doctors")
    op.drop_index("ix_referring_doctors_specialization", table_name="referring_doctors")
    op.drop_index("ix_referring_doctors_city", table_name="referring_doctors")
    op.drop_index("ix_referring_doctors_email", table_name="referring_doctors")
    op.drop_index("ix_referring_doctors_mobile", table_name="referring_doctors")
    op.drop_index("ix_referring_doctors_full_name", table_name="referring_doctors")
    op.drop_index("ix_referring_doctors_branch_id", table_name="referring_doctors")
    op.drop_index("ix_referring_doctors_id", table_name="referring_doctors")
    op.drop_table("referring_doctors")
