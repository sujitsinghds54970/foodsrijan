"""add accounts finance module tables

Revision ID: add_accounts_finance_module
Revises: add_inventory_management_v2
Create Date: 2026-07-08 12:45:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "add_accounts_finance_module"
down_revision = "add_inventory_management_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "branch_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("opening_balance", sa.DECIMAL(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("current_balance", sa.DECIMAL(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_branch_accounts_id", "branch_accounts", ["id"], unique=False)
    op.create_index("ix_branch_accounts_branch_id", "branch_accounts", ["branch_id"], unique=False)

    op.create_table(
        "finance_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference_id", sa.String(length=120), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("payment_method", sa.String(length=30), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finance_transactions_id", "finance_transactions", ["id"], unique=False)
    op.create_index("ix_finance_transactions_branch_id", "finance_transactions", ["branch_id"], unique=False)
    op.create_index("ix_finance_transactions_date", "finance_transactions", ["date"], unique=False)
    op.create_index("ix_finance_transactions_type", "finance_transactions", ["type"], unique=False)
    op.create_index("ix_finance_transactions_reference_id", "finance_transactions", ["reference_id"], unique=False)
    op.create_index("ix_finance_transactions_category", "finance_transactions", ["category"], unique=False)

    op.create_table(
        "finance_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(length=50), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("patient_name", sa.String(length=200), nullable=True),
        sa.Column("date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("total_amount", sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column("tax_amount", sa.DECIMAL(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("gst_rate", sa.DECIMAL(precision=5, scale=2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("pdf_url", sa.String(length=500), nullable=True),
        sa.Column("reference_id", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finance_invoices_id", "finance_invoices", ["id"], unique=False)
    op.create_index("ix_finance_invoices_invoice_number", "finance_invoices", ["invoice_number"], unique=True)
    op.create_index("ix_finance_invoices_branch_id", "finance_invoices", ["branch_id"], unique=False)
    op.create_index("ix_finance_invoices_patient_id", "finance_invoices", ["patient_id"], unique=False)
    op.create_index("ix_finance_invoices_date", "finance_invoices", ["date"], unique=False)
    op.create_index("ix_finance_invoices_status", "finance_invoices", ["status"], unique=False)
    op.create_index("ix_finance_invoices_reference_id", "finance_invoices", ["reference_id"], unique=False)

    op.create_table(
        "finance_expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("attachment_url", sa.String(length=500), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=True),
        sa.Column("reference_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finance_expenses_id", "finance_expenses", ["id"], unique=False)
    op.create_index("ix_finance_expenses_branch_id", "finance_expenses", ["branch_id"], unique=False)
    op.create_index("ix_finance_expenses_date", "finance_expenses", ["date"], unique=False)
    op.create_index("ix_finance_expenses_category", "finance_expenses", ["category"], unique=False)
    op.create_index("ix_finance_expenses_status", "finance_expenses", ["status"], unique=False)
    op.create_index("ix_finance_expenses_reference_id", "finance_expenses", ["reference_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_finance_expenses_reference_id", table_name="finance_expenses")
    op.drop_index("ix_finance_expenses_status", table_name="finance_expenses")
    op.drop_index("ix_finance_expenses_category", table_name="finance_expenses")
    op.drop_index("ix_finance_expenses_date", table_name="finance_expenses")
    op.drop_index("ix_finance_expenses_branch_id", table_name="finance_expenses")
    op.drop_index("ix_finance_expenses_id", table_name="finance_expenses")
    op.drop_table("finance_expenses")

    op.drop_index("ix_finance_invoices_reference_id", table_name="finance_invoices")
    op.drop_index("ix_finance_invoices_status", table_name="finance_invoices")
    op.drop_index("ix_finance_invoices_date", table_name="finance_invoices")
    op.drop_index("ix_finance_invoices_patient_id", table_name="finance_invoices")
    op.drop_index("ix_finance_invoices_branch_id", table_name="finance_invoices")
    op.drop_index("ix_finance_invoices_invoice_number", table_name="finance_invoices")
    op.drop_index("ix_finance_invoices_id", table_name="finance_invoices")
    op.drop_table("finance_invoices")

    op.drop_index("ix_finance_transactions_category", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_reference_id", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_type", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_date", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_branch_id", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_id", table_name="finance_transactions")
    op.drop_table("finance_transactions")

    op.drop_index("ix_branch_accounts_branch_id", table_name="branch_accounts")
    op.drop_index("ix_branch_accounts_id", table_name="branch_accounts")
    op.drop_table("branch_accounts")
