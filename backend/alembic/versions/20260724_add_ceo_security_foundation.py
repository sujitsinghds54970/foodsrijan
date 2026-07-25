"""add ceo security foundation

Revision ID: 20260724_add_ceo_security_foundation
Revises: 20260723_add_patient_phase4_premium_features
Create Date: 2026-07-24 18:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260724_add_ceo_security_foundation"
down_revision = "20260723_add_patient_phase4_premium_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ceo_security_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("webauthn_user_handle", sa.String(length=255), nullable=True),
        sa.Column("webauthn_registration_challenge", sa.String(length=255), nullable=True),
        sa.Column("webauthn_registration_origin", sa.String(length=255), nullable=True),
        sa.Column("webauthn_registration_expires_at", sa.DateTime(), nullable=True),
        sa.Column("totp_secret", sa.String(length=255), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_otp_sent_at", sa.DateTime(), nullable=True),
        sa.Column("last_otp_verified_at", sa.DateTime(), nullable=True),
        sa.Column("behavioral_baseline", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("behavioral_last_deviation", sa.Float(), nullable=True),
        sa.Column("behavioral_step_up_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("webauthn_user_handle"),
    )
    op.create_index("ix_ceo_security_profiles_id", "ceo_security_profiles", ["id"], unique=False)
    op.create_index("ix_ceo_security_profiles_user_id", "ceo_security_profiles", ["user_id"], unique=False)

    op.create_table(
        "ceo_webauthn_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("security_profile_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.String(length=512), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("attestation_object", sa.Text(), nullable=True),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transports", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("device_label", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["security_profile_id"], ["ceo_security_profiles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_id"),
    )
    op.create_index("ix_ceo_webauthn_credentials_id", "ceo_webauthn_credentials", ["id"], unique=False)
    op.create_index("ix_ceo_webauthn_credentials_security_profile_id", "ceo_webauthn_credentials", ["security_profile_id"], unique=False)
    op.create_index("ix_ceo_webauthn_credentials_user_id", "ceo_webauthn_credentials", ["user_id"], unique=False)
    op.create_index("ix_ceo_webauthn_credentials_credential_id", "ceo_webauthn_credentials", ["credential_id"], unique=False)

    op.create_table(
        "ceo_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("http_method", sa.String(length=16), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("request_meta", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("previous_signature", sa.String(length=128), nullable=True),
        sa.Column("signature", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signature"),
    )
    op.create_index("ix_ceo_audit_logs_id", "ceo_audit_logs", ["id"], unique=False)
    op.create_index("ix_ceo_audit_logs_user_id", "ceo_audit_logs", ["user_id"], unique=False)
    op.create_index("ix_ceo_audit_logs_action", "ceo_audit_logs", ["action"], unique=False)
    op.create_index("ix_ceo_audit_logs_endpoint", "ceo_audit_logs", ["endpoint"], unique=False)
    op.create_index("ix_ceo_audit_logs_created_at", "ceo_audit_logs", ["created_at"], unique=False)

    op.create_table(
        "ceo_break_glass_grants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("approver_1_id", sa.Integer(), nullable=False),
        sa.Column("approver_2_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("temp_auth_token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approver_1_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approver_2_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("temp_auth_token_hash"),
    )
    op.create_index("ix_ceo_break_glass_grants_id", "ceo_break_glass_grants", ["id"], unique=False)
    op.create_index("ix_ceo_break_glass_grants_user_id", "ceo_break_glass_grants", ["user_id"], unique=False)
    op.create_index("ix_ceo_break_glass_grants_approver_1_id", "ceo_break_glass_grants", ["approver_1_id"], unique=False)
    op.create_index("ix_ceo_break_glass_grants_approver_2_id", "ceo_break_glass_grants", ["approver_2_id"], unique=False)
    op.create_index("ix_ceo_break_glass_grants_expires_at", "ceo_break_glass_grants", ["expires_at"], unique=False)
    op.create_index("ix_ceo_break_glass_grants_created_at", "ceo_break_glass_grants", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ceo_break_glass_grants_created_at", table_name="ceo_break_glass_grants")
    op.drop_index("ix_ceo_break_glass_grants_expires_at", table_name="ceo_break_glass_grants")
    op.drop_index("ix_ceo_break_glass_grants_approver_2_id", table_name="ceo_break_glass_grants")
    op.drop_index("ix_ceo_break_glass_grants_approver_1_id", table_name="ceo_break_glass_grants")
    op.drop_index("ix_ceo_break_glass_grants_user_id", table_name="ceo_break_glass_grants")
    op.drop_index("ix_ceo_break_glass_grants_id", table_name="ceo_break_glass_grants")
    op.drop_table("ceo_break_glass_grants")

    op.drop_index("ix_ceo_audit_logs_created_at", table_name="ceo_audit_logs")
    op.drop_index("ix_ceo_audit_logs_endpoint", table_name="ceo_audit_logs")
    op.drop_index("ix_ceo_audit_logs_action", table_name="ceo_audit_logs")
    op.drop_index("ix_ceo_audit_logs_user_id", table_name="ceo_audit_logs")
    op.drop_index("ix_ceo_audit_logs_id", table_name="ceo_audit_logs")
    op.drop_table("ceo_audit_logs")

    op.drop_index("ix_ceo_webauthn_credentials_credential_id", table_name="ceo_webauthn_credentials")
    op.drop_index("ix_ceo_webauthn_credentials_user_id", table_name="ceo_webauthn_credentials")
    op.drop_index("ix_ceo_webauthn_credentials_security_profile_id", table_name="ceo_webauthn_credentials")
    op.drop_index("ix_ceo_webauthn_credentials_id", table_name="ceo_webauthn_credentials")
    op.drop_table("ceo_webauthn_credentials")

    op.drop_index("ix_ceo_security_profiles_user_id", table_name="ceo_security_profiles")
    op.drop_index("ix_ceo_security_profiles_id", table_name="ceo_security_profiles")
    op.drop_table("ceo_security_profiles")