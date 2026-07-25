"""add patient b2c phase2 ai engagement tables

Revision ID: 20260724_add_patient_b2c_phase2_ai_engagement
Revises: 20260724_add_doctor_audit_logs_phase4
Create Date: 2026-07-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260724_add_patient_b2c_phase2_ai_engagement"
down_revision = "20260724_add_doctor_audit_logs_phase4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_report_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=False),
        sa.Column("abnormal_flags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["daily_entries_module.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_report_summaries_id", "patient_report_summaries", ["id"], unique=False)
    op.create_index("ix_patient_report_summaries_patient_id", "patient_report_summaries", ["patient_id"], unique=False)
    op.create_index("ix_patient_report_summaries_report_id", "patient_report_summaries", ["report_id"], unique=False)

    op.create_table(
        "patient_health_trends",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("biomarker", sa.String(length=120), nullable=False),
        sa.Column("value", sa.String(length=50), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("graph_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_health_trends_id", "patient_health_trends", ["id"], unique=False)
    op.create_index("ix_patient_health_trends_patient_id", "patient_health_trends", ["patient_id"], unique=False)
    op.create_index("ix_patient_health_trends_biomarker", "patient_health_trends", ["biomarker"], unique=False)
    op.create_index("ix_patient_health_trends_date", "patient_health_trends", ["date"], unique=False)

    op.create_table(
        "patient_health_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("last_calculated", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_health_scores_id", "patient_health_scores", ["id"], unique=False)
    op.create_index("ix_patient_health_scores_patient_id", "patient_health_scores", ["patient_id"], unique=False)
    op.create_index("ix_patient_health_scores_last_calculated", "patient_health_scores", ["last_calculated"], unique=False)

    op.create_table(
        "patient_followup_reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("test_name", sa.String(length=200), nullable=False),
        sa.Column("next_due_date", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_followup_reminders_id", "patient_followup_reminders", ["id"], unique=False)
    op.create_index("ix_patient_followup_reminders_patient_id", "patient_followup_reminders", ["patient_id"], unique=False)
    op.create_index("ix_patient_followup_reminders_test_name", "patient_followup_reminders", ["test_name"], unique=False)
    op.create_index("ix_patient_followup_reminders_next_due_date", "patient_followup_reminders", ["next_due_date"], unique=False)
    op.create_index("ix_patient_followup_reminders_status", "patient_followup_reminders", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_patient_followup_reminders_status", table_name="patient_followup_reminders")
    op.drop_index("ix_patient_followup_reminders_next_due_date", table_name="patient_followup_reminders")
    op.drop_index("ix_patient_followup_reminders_test_name", table_name="patient_followup_reminders")
    op.drop_index("ix_patient_followup_reminders_patient_id", table_name="patient_followup_reminders")
    op.drop_index("ix_patient_followup_reminders_id", table_name="patient_followup_reminders")
    op.drop_table("patient_followup_reminders")

    op.drop_index("ix_patient_health_scores_last_calculated", table_name="patient_health_scores")
    op.drop_index("ix_patient_health_scores_patient_id", table_name="patient_health_scores")
    op.drop_index("ix_patient_health_scores_id", table_name="patient_health_scores")
    op.drop_table("patient_health_scores")

    op.drop_index("ix_patient_health_trends_date", table_name="patient_health_trends")
    op.drop_index("ix_patient_health_trends_biomarker", table_name="patient_health_trends")
    op.drop_index("ix_patient_health_trends_patient_id", table_name="patient_health_trends")
    op.drop_index("ix_patient_health_trends_id", table_name="patient_health_trends")
    op.drop_table("patient_health_trends")

    op.drop_index("ix_patient_report_summaries_report_id", table_name="patient_report_summaries")
    op.drop_index("ix_patient_report_summaries_patient_id", table_name="patient_report_summaries")
    op.drop_index("ix_patient_report_summaries_id", table_name="patient_report_summaries")
    op.drop_table("patient_report_summaries")
