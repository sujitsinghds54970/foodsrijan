"""add payroll management suite

Revision ID: 20260712_add_payroll_management_suite
Revises: 20260711_add_attendance_attachments_review_fields
Create Date: 2026-07-12 00:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260712_add_payroll_management_suite"
down_revision = "20260711_add_attendance_attachments_review_fields"
branch_labels = None
depends_on = None


payroll_run_status_enum = sa.Enum("Draft", "Ready", "Approved", "Locked", name="payrollrunstatus")
advance_status_enum = sa.Enum("Pending", "Approved", "Rejected", "Disbursed", name="advancestatus")
reimbursement_status_enum = sa.Enum("Pending", "Approved", "Rejected", "Paid", name="reimbursementstatus")
payroll_dispute_status_enum = sa.Enum("Open", "Resolved", name="payrolldisputestatus")


def upgrade() -> None:
    bind = op.get_bind()
    payroll_run_status_enum.create(bind, checkfirst=True)
    advance_status_enum.create(bind, checkfirst=True)
    reimbursement_status_enum.create(bind, checkfirst=True)
    payroll_dispute_status_enum.create(bind, checkfirst=True)

    with op.batch_alter_table("branch_bank_details") as batch_op:
        batch_op.add_column(sa.Column("current_balance", sa.DECIMAL(14, 2), nullable=False, server_default="0"))

    op.create_table(
        "earning_heads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("is_fixed", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("taxable", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "salary_grades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role", sa.String(length=120), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=False),
        sa.Column("base_salary", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("min_salary", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("max_salary", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_salary_grades_role", "salary_grades", ["role"])
    op.create_index("ix_salary_grades_grade_level", "salary_grades", ["grade_level"])

    op.create_table(
        "staff_salary_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False, unique=True),
        sa.Column("grade_id", sa.Integer(), sa.ForeignKey("salary_grades.id"), nullable=False),
        sa.Column("bank_account_number", sa.String(length=64), nullable=True),
        sa.Column("ifsc", sa.String(length=20), nullable=True),
        sa.Column("upi_id", sa.String(length=100), nullable=True),
        sa.Column("date_of_joining", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_staff_salary_configs_staff_id", "staff_salary_configs", ["staff_id"])

    op.create_table(
        "payroll_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("status", payroll_run_status_enum, nullable=False, server_default="Draft"),
        sa.Column("total_gross_pay", sa.DECIMAL(14, 2), nullable=False, server_default="0"),
        sa.Column("total_deductions", sa.DECIMAL(14, 2), nullable=False, server_default="0"),
        sa.Column("total_net_pay", sa.DECIMAL(14, 2), nullable=False, server_default="0"),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_payroll_runs_branch_id", "payroll_runs", ["branch_id"])
    op.create_index("ix_payroll_runs_month", "payroll_runs", ["month"])
    op.create_index("ix_payroll_runs_year", "payroll_runs", ["year"])

    op.create_table(
        "payroll_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payroll_run_id", sa.Integer(), sa.ForeignKey("payroll_runs.id"), nullable=False),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False),
        sa.Column("base_salary", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("overtime_hours", sa.DECIMAL(8, 2), nullable=False, server_default="0"),
        sa.Column("lop_days", sa.DECIMAL(8, 2), nullable=False, server_default="0"),
        sa.Column("incentive_amount", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("reimbursement_amount", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("total_deductions", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("net_pay", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_payroll_transactions_payroll_run_id", "payroll_transactions", ["payroll_run_id"])
    op.create_index("ix_payroll_transactions_staff_id", "payroll_transactions", ["staff_id"])

    op.create_table(
        "advance_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False),
        sa.Column("amount", sa.DECIMAL(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("tenure_months", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("repaid_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", advance_status_enum, nullable=False, server_default="Pending"),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_advance_requests_staff_id", "advance_requests", ["staff_id"])

    op.create_table(
        "reimbursement_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("amount", sa.DECIMAL(12, 2), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=True),
        sa.Column("status", reimbursement_status_enum, nullable=False, server_default="Pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_reimbursement_claims_staff_id", "reimbursement_claims", ["staff_id"])

    op.create_table(
        "payroll_locks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payroll_run_id", sa.Integer(), sa.ForeignKey("payroll_runs.id"), nullable=False),
        sa.Column("unlocked_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("unlock_reason", sa.Text(), nullable=True),
        sa.Column("unlocked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_payroll_locks_payroll_run_id", "payroll_locks", ["payroll_run_id"])

    op.create_table(
        "staff_tax_declarations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False, unique=True),
        sa.Column("declaration_year", sa.Integer(), nullable=False),
        sa.Column("section_80c", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("medical", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("rent_allowance", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_staff_tax_declarations_staff_id", "staff_tax_declarations", ["staff_id"])

    op.create_table(
        "payroll_disputes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payroll_transaction_id", sa.Integer(), sa.ForeignKey("payroll_transactions.id"), nullable=False),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", payroll_dispute_status_enum, nullable=False, server_default="Open"),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_payroll_disputes_payroll_transaction_id", "payroll_disputes", ["payroll_transaction_id"])
    op.create_index("ix_payroll_disputes_staff_id", "payroll_disputes", ["staff_id"])


def downgrade() -> None:
    op.drop_index("ix_payroll_disputes_staff_id", table_name="payroll_disputes")
    op.drop_index("ix_payroll_disputes_payroll_transaction_id", table_name="payroll_disputes")
    op.drop_table("payroll_disputes")

    op.drop_index("ix_staff_tax_declarations_staff_id", table_name="staff_tax_declarations")
    op.drop_table("staff_tax_declarations")

    op.drop_index("ix_payroll_locks_payroll_run_id", table_name="payroll_locks")
    op.drop_table("payroll_locks")

    op.drop_index("ix_reimbursement_claims_staff_id", table_name="reimbursement_claims")
    op.drop_table("reimbursement_claims")

    op.drop_index("ix_advance_requests_staff_id", table_name="advance_requests")
    op.drop_table("advance_requests")

    op.drop_index("ix_payroll_transactions_staff_id", table_name="payroll_transactions")
    op.drop_index("ix_payroll_transactions_payroll_run_id", table_name="payroll_transactions")
    op.drop_table("payroll_transactions")

    op.drop_index("ix_payroll_runs_year", table_name="payroll_runs")
    op.drop_index("ix_payroll_runs_month", table_name="payroll_runs")
    op.drop_index("ix_payroll_runs_branch_id", table_name="payroll_runs")
    op.drop_table("payroll_runs")

    op.drop_index("ix_staff_salary_configs_staff_id", table_name="staff_salary_configs")
    op.drop_table("staff_salary_configs")

    op.drop_index("ix_salary_grades_grade_level", table_name="salary_grades")
    op.drop_index("ix_salary_grades_role", table_name="salary_grades")
    op.drop_table("salary_grades")

    op.drop_table("earning_heads")

    with op.batch_alter_table("branch_bank_details") as batch_op:
        batch_op.drop_column("current_balance")

    bind = op.get_bind()
    payroll_dispute_status_enum.drop(bind, checkfirst=True)
    reimbursement_status_enum.drop(bind, checkfirst=True)
    advance_status_enum.drop(bind, checkfirst=True)
    payroll_run_status_enum.drop(bind, checkfirst=True)
