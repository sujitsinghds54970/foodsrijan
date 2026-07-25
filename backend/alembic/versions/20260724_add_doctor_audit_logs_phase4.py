"""add doctor audit logs phase4

Revision ID: 20260724_add_doctor_audit_logs_phase4
Revises: 20260723_add_doctor_portal_phase3_ai_engagement
Create Date: 2026-07-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260724_add_doctor_audit_logs_phase4"
down_revision = "20260723_add_doctor_portal_phase3_ai_engagement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctor_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column("event_meta", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_doctor_audit_logs_id", "doctor_audit_logs", ["id"], unique=False)
    op.create_index("ix_doctor_audit_logs_doctor_id", "doctor_audit_logs", ["doctor_id"], unique=False)
    op.create_index("ix_doctor_audit_logs_user_id", "doctor_audit_logs", ["user_id"], unique=False)
    op.create_index("ix_doctor_audit_logs_action", "doctor_audit_logs", ["action"], unique=False)
    op.create_index("ix_doctor_audit_logs_entity_id", "doctor_audit_logs", ["entity_id"], unique=False)
    op.create_index("ix_doctor_audit_logs_created_at", "doctor_audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_doctor_audit_logs_created_at", table_name="doctor_audit_logs")
    op.drop_index("ix_doctor_audit_logs_entity_id", table_name="doctor_audit_logs")
    op.drop_index("ix_doctor_audit_logs_action", table_name="doctor_audit_logs")
    op.drop_index("ix_doctor_audit_logs_user_id", table_name="doctor_audit_logs")
    op.drop_index("ix_doctor_audit_logs_doctor_id", table_name="doctor_audit_logs")
    op.drop_index("ix_doctor_audit_logs_id", table_name="doctor_audit_logs")
    op.drop_table("doctor_audit_logs")
