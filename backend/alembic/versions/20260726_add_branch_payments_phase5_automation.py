"""add branch payments phase 5 automation tables

Revision ID: 20260726_add_branch_payments_phase5_automation
Revises: 20260724_add_ceo_security_foundation
Create Date: 2026-07-26 23:14:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260726_add_branch_payments_phase5_automation"
down_revision: Union[str, Sequence[str], None] = "20260724_add_ceo_security_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("triggered_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("run_type", sa.String(), nullable=True),
        sa.Column("total_transactions", sa.Integer(), nullable=True),
        sa.Column("reconciled_count", sa.Integer(), nullable=True),
        sa.Column("pending_count", sa.Integer(), nullable=True),
        sa.Column("discrepancy_count", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "payment_reminders",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True),
        sa.Column("reminder_type", sa.String(), nullable=True),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("payment_reminders")
    op.drop_table("reconciliation_logs")
