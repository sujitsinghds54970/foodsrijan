"""add doctor portal foundation

Revision ID: 20260723_add_doctor_portal_foundation
Revises: 20260711_replace_daily_ops_password_with_staff_toggle, 20260712_add_staff_task_management_collab, 9f3aed9dfac2
Create Date: 2026-07-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260723_add_doctor_portal_foundation"
down_revision = (
    "20260711_replace_daily_ops_password_with_staff_toggle",
    "20260712_add_staff_task_management_collab",
    "9f3aed9dfac2",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("doctors", sa.Column("upi_id", sa.String(length=120), nullable=True))
    op.add_column("doctors", sa.Column("bank_account", sa.String(length=100), nullable=True))
    op.add_column("doctors", sa.Column("ifsc", sa.String(length=30), nullable=True))
    op.add_column("doctors", sa.Column("commission_percentage", sa.Float(), nullable=False, server_default="0"))
    op.add_column("doctors", sa.Column("loyalty_tier", sa.String(length=20), nullable=False, server_default="Silver"))
    op.add_column("patients", sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))

    op.create_table(
        "patient_search_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("query", sa.String(length=255), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_search_logs_id", "patient_search_logs", ["id"], unique=False)
    op.create_index("ix_patient_search_logs_doctor_id", "patient_search_logs", ["doctor_id"], unique=False)

    op.create_table(
        "doctor_test_panels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("panel_name", sa.String(length=200), nullable=False),
        sa.Column("test_ids", sa.JSON(), nullable=False),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_doctor_test_panels_id", "doctor_test_panels", ["id"], unique=False)
    op.create_index("ix_doctor_test_panels_doctor_id", "doctor_test_panels", ["doctor_id"], unique=False)

    op.create_table(
        "doctor_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("order_date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Draft"),
        sa.Column("test_ids", sa.JSON(), nullable=False),
        sa.Column("panel_ids", sa.JSON(), nullable=False),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("qr_token", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("qr_token"),
    )
    op.create_index("ix_doctor_orders_id", "doctor_orders", ["id"], unique=False)
    op.create_index("ix_doctor_orders_doctor_id", "doctor_orders", ["doctor_id"], unique=False)
    op.create_index("ix_doctor_orders_patient_id", "doctor_orders", ["patient_id"], unique=False)
    op.create_index("ix_doctor_orders_branch_id", "doctor_orders", ["branch_id"], unique=False)
    op.create_index("ix_doctor_orders_status", "doctor_orders", ["status"], unique=False)
    op.create_index("ix_doctor_orders_qr_token", "doctor_orders", ["qr_token"], unique=False)


def downgrade() -> None:
    op.drop_table("doctor_orders")
    op.drop_table("doctor_test_panels")
    op.drop_table("patient_search_logs")
    op.drop_column("patients", "tags")
    op.drop_column("doctors", "loyalty_tier")
    op.drop_column("doctors", "commission_percentage")
    op.drop_column("doctors", "ifsc")
    op.drop_column("doctors", "bank_account")
    op.drop_column("doctors", "upi_id")
