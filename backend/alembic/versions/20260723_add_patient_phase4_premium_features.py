"""add patient phase4 premium features

Revision ID: 20260723_add_patient_phase4_premium_features
Revises: 20260724_add_patient_b2c_phase3_loyalty_growth
Create Date: 2026-07-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260723_add_patient_phase4_premium_features"
down_revision = "20260724_add_patient_b2c_phase3_loyalty_growth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_vault_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient_profiles.id"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("document_label", sa.String(length=150), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_patient_vault_documents_patient_id", "patient_vault_documents", ["patient_id"])
    op.create_index("ix_patient_vault_documents_created_at", "patient_vault_documents", ["created_at"])

    op.create_table(
        "patient_wearable_syncs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient_profiles.id"), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="connected"),
        sa.Column("last_synced_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_patient_wearable_syncs_patient_id", "patient_wearable_syncs", ["patient_id"])
    op.create_index("ix_patient_wearable_syncs_provider", "patient_wearable_syncs", ["provider"])

    op.create_table(
        "patient_second_opinion_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient_profiles.id"), nullable=False),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("daily_entries_module.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Pending Payment"),
        sa.Column("payment_reference", sa.String(length=120), nullable=True),
        sa.Column("specialist_panel", sa.String(length=120), nullable=False, server_default="Senior Specialist Panel"),
        sa.Column("premium_amount", sa.Integer(), nullable=False, server_default=sa.text("999")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_patient_second_opinion_requests_patient_id", "patient_second_opinion_requests", ["patient_id"])
    op.create_index("ix_patient_second_opinion_requests_report_id", "patient_second_opinion_requests", ["report_id"])
    op.create_index("ix_patient_second_opinion_requests_status", "patient_second_opinion_requests", ["status"])

    op.create_table(
        "patient_emergency_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient_profiles.id"), nullable=False),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("daily_entries_module.id"), nullable=True),
        sa.Column("alert_type", sa.String(length=60), nullable=False),
        sa.Column("triggered_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("delivery_channels", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("doctor_notified", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_patient_emergency_alerts_patient_id", "patient_emergency_alerts", ["patient_id"])
    op.create_index("ix_patient_emergency_alerts_report_id", "patient_emergency_alerts", ["report_id"])
    op.create_index("ix_patient_emergency_alerts_alert_type", "patient_emergency_alerts", ["alert_type"])
    op.create_index("ix_patient_emergency_alerts_triggered_at", "patient_emergency_alerts", ["triggered_at"])


def downgrade() -> None:
    op.drop_index("ix_patient_emergency_alerts_triggered_at", table_name="patient_emergency_alerts")
    op.drop_index("ix_patient_emergency_alerts_alert_type", table_name="patient_emergency_alerts")
    op.drop_index("ix_patient_emergency_alerts_report_id", table_name="patient_emergency_alerts")
    op.drop_index("ix_patient_emergency_alerts_patient_id", table_name="patient_emergency_alerts")
    op.drop_table("patient_emergency_alerts")

    op.drop_index("ix_patient_second_opinion_requests_status", table_name="patient_second_opinion_requests")
    op.drop_index("ix_patient_second_opinion_requests_report_id", table_name="patient_second_opinion_requests")
    op.drop_index("ix_patient_second_opinion_requests_patient_id", table_name="patient_second_opinion_requests")
    op.drop_table("patient_second_opinion_requests")

    op.drop_index("ix_patient_wearable_syncs_provider", table_name="patient_wearable_syncs")
    op.drop_index("ix_patient_wearable_syncs_patient_id", table_name="patient_wearable_syncs")
    op.drop_table("patient_wearable_syncs")

    op.drop_index("ix_patient_vault_documents_created_at", table_name="patient_vault_documents")
    op.drop_index("ix_patient_vault_documents_patient_id", table_name="patient_vault_documents")
    op.drop_table("patient_vault_documents")
