"""add doctor portal phase2 communication analytics

Revision ID: 20260723_add_doctor_portal_phase2
Revises: 20260723_add_doctor_portal_foundation
Create Date: 2026-07-23 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260723_add_doctor_portal_phase2"
down_revision = "20260723_add_doctor_portal_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctor_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("receiver_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_doctor_messages_id", "doctor_messages", ["id"], unique=False)
    op.create_index("ix_doctor_messages_sender_id", "doctor_messages", ["sender_id"], unique=False)
    op.create_index("ix_doctor_messages_receiver_id", "doctor_messages", ["receiver_id"], unique=False)
    op.create_index("ix_doctor_messages_created_at", "doctor_messages", ["created_at"], unique=False)

    op.create_table(
        "doctor_referral_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("commission_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Pending"),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["doctor_id"], ["staff.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["doctor_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_doctor_referral_logs_id", "doctor_referral_logs", ["id"], unique=False)
    op.create_index("ix_doctor_referral_logs_doctor_id", "doctor_referral_logs", ["doctor_id"], unique=False)
    op.create_index("ix_doctor_referral_logs_patient_id", "doctor_referral_logs", ["patient_id"], unique=False)
    op.create_index("ix_doctor_referral_logs_order_id", "doctor_referral_logs", ["order_id"], unique=False)
    op.create_index("ix_doctor_referral_logs_status", "doctor_referral_logs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("doctor_referral_logs")
    op.drop_table("doctor_messages")
