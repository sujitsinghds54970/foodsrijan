"""add branch lis command center tables

Revision ID: 20260727_add_branch_lis_command_center
Revises: 20260726_add_branch_payments_phase5_automation
Create Date: 2026-07-27 00:12:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260727_add_branch_lis_command_center"
down_revision: Union[str, Sequence[str], None] = "20260726_add_branch_payments_phase5_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "branch_lis_test_catalog",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("test_code", sa.String(length=60), nullable=False),
        sa.Column("test_name", sa.String(length=200), nullable=False),
        sa.Column("department", sa.String(length=80), nullable=False),
        sa.Column("sample_type", sa.String(length=80), nullable=False),
        sa.Column("turnaround_minutes", sa.Integer(), nullable=False),
        sa.Column("normal_range_json", sa.JSON(), nullable=True),
        sa.Column("critical_threshold_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("branch_id", "test_code", name="uq_branch_lis_test_code"),
    )
    op.create_index("ix_branch_lis_test_catalog_id", "branch_lis_test_catalog", ["id"], unique=False)
    op.create_index("ix_branch_lis_test_catalog_branch_id", "branch_lis_test_catalog", ["branch_id"], unique=False)

    op.create_table(
        "branch_lis_test_panels",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("panel_name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("menu_items_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_branch_lis_test_panels_id", "branch_lis_test_panels", ["id"], unique=False)
    op.create_index("ix_branch_lis_test_panels_branch_id", "branch_lis_test_panels", ["branch_id"], unique=False)

    op.create_table(
        "branch_lis_order_queue",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("daily_entry_id", sa.Integer(), sa.ForeignKey("daily_entries_module.id"), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("order_number", sa.String(length=80), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("patient_name", sa.String(length=200), nullable=False),
        sa.Column("patient_code", sa.String(length=80), nullable=True),
        sa.Column("doctor_name", sa.String(length=200), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("expected_tat_minutes", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("menu_items_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("branch_id", "daily_entry_id", name="uq_branch_lis_daily_entry"),
    )
    op.create_index("ix_branch_lis_order_queue_id", "branch_lis_order_queue", ["id"], unique=False)
    op.create_index("ix_branch_lis_order_queue_branch_id", "branch_lis_order_queue", ["branch_id"], unique=False)
    op.create_index("ix_branch_lis_order_queue_daily_entry_id", "branch_lis_order_queue", ["daily_entry_id"], unique=False)
    op.create_index("ix_branch_lis_order_queue_patient_id", "branch_lis_order_queue", ["patient_id"], unique=False)
    op.create_index("ix_branch_lis_order_queue_patient_code", "branch_lis_order_queue", ["patient_code"], unique=False)
    op.create_index("ix_branch_lis_order_queue_order_number", "branch_lis_order_queue", ["order_number"], unique=True)

    op.create_table(
        "branch_lis_samples",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("branch_lis_order_queue.id"), nullable=False),
        sa.Column("sample_code", sa.String(length=80), nullable=False),
        sa.Column("barcode_value", sa.String(length=160), nullable=False),
        sa.Column("barcode_image_base64", sa.Text(), nullable=True),
        sa.Column("sample_type", sa.String(length=80), nullable=False),
        sa.Column("department", sa.String(length=80), nullable=False),
        sa.Column("analyzer_name", sa.String(length=120), nullable=True),
        sa.Column("storage_location", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("registered_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("reported_at", sa.DateTime(), nullable=True),
        sa.Column("expected_completion_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_branch_lis_samples_id", "branch_lis_samples", ["id"], unique=False)
    op.create_index("ix_branch_lis_samples_branch_id", "branch_lis_samples", ["branch_id"], unique=False)
    op.create_index("ix_branch_lis_samples_order_id", "branch_lis_samples", ["order_id"], unique=False)
    op.create_index("ix_branch_lis_samples_sample_code", "branch_lis_samples", ["sample_code"], unique=True)
    op.create_index("ix_branch_lis_samples_barcode_value", "branch_lis_samples", ["barcode_value"], unique=True)

    op.create_table(
        "branch_lis_worklists",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("worklist_code", sa.String(length=80), nullable=False),
        sa.Column("department", sa.String(length=80), nullable=False),
        sa.Column("analyzer_name", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("sample_ids_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_branch_lis_worklists_id", "branch_lis_worklists", ["id"], unique=False)
    op.create_index("ix_branch_lis_worklists_branch_id", "branch_lis_worklists", ["branch_id"], unique=False)
    op.create_index("ix_branch_lis_worklists_worklist_code", "branch_lis_worklists", ["worklist_code"], unique=True)

    op.create_table(
        "branch_lis_instrument_calibrations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("analyzer_name", sa.String(length=120), nullable=False),
        sa.Column("calibration_status", sa.String(length=30), nullable=False),
        sa.Column("calibrated_at", sa.DateTime(), nullable=True),
        sa.Column("next_due_at", sa.DateTime(), nullable=True),
        sa.Column("maintenance_notes", sa.Text(), nullable=True),
        sa.Column("maintenance_history_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_branch_lis_instrument_calibrations_id", "branch_lis_instrument_calibrations", ["id"], unique=False)
    op.create_index("ix_branch_lis_instrument_calibrations_branch_id", "branch_lis_instrument_calibrations", ["branch_id"], unique=False)
    op.create_index("ix_branch_lis_instrument_calibrations_analyzer_name", "branch_lis_instrument_calibrations", ["analyzer_name"], unique=False)

    op.create_table(
        "branch_lis_qc_results",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("sample_id", sa.Integer(), sa.ForeignKey("branch_lis_samples.id"), nullable=True),
        sa.Column("analyzer_name", sa.String(length=120), nullable=True),
        sa.Column("test_code", sa.String(length=60), nullable=True),
        sa.Column("qc_status", sa.String(length=30), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("hil_flag", sa.Boolean(), nullable=False),
        sa.Column("delta_check_flag", sa.Boolean(), nullable=False),
        sa.Column("critical_value_flag", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_branch_lis_qc_results_id", "branch_lis_qc_results", ["id"], unique=False)
    op.create_index("ix_branch_lis_qc_results_branch_id", "branch_lis_qc_results", ["branch_id"], unique=False)
    op.create_index("ix_branch_lis_qc_results_sample_id", "branch_lis_qc_results", ["sample_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_branch_lis_qc_results_sample_id", table_name="branch_lis_qc_results")
    op.drop_index("ix_branch_lis_qc_results_branch_id", table_name="branch_lis_qc_results")
    op.drop_index("ix_branch_lis_qc_results_id", table_name="branch_lis_qc_results")
    op.drop_table("branch_lis_qc_results")

    op.drop_index("ix_branch_lis_instrument_calibrations_analyzer_name", table_name="branch_lis_instrument_calibrations")
    op.drop_index("ix_branch_lis_instrument_calibrations_branch_id", table_name="branch_lis_instrument_calibrations")
    op.drop_index("ix_branch_lis_instrument_calibrations_id", table_name="branch_lis_instrument_calibrations")
    op.drop_table("branch_lis_instrument_calibrations")

    op.drop_index("ix_branch_lis_worklists_worklist_code", table_name="branch_lis_worklists")
    op.drop_index("ix_branch_lis_worklists_branch_id", table_name="branch_lis_worklists")
    op.drop_index("ix_branch_lis_worklists_id", table_name="branch_lis_worklists")
    op.drop_table("branch_lis_worklists")

    op.drop_index("ix_branch_lis_samples_barcode_value", table_name="branch_lis_samples")
    op.drop_index("ix_branch_lis_samples_sample_code", table_name="branch_lis_samples")
    op.drop_index("ix_branch_lis_samples_order_id", table_name="branch_lis_samples")
    op.drop_index("ix_branch_lis_samples_branch_id", table_name="branch_lis_samples")
    op.drop_index("ix_branch_lis_samples_id", table_name="branch_lis_samples")
    op.drop_table("branch_lis_samples")

    op.drop_index("ix_branch_lis_order_queue_order_number", table_name="branch_lis_order_queue")
    op.drop_index("ix_branch_lis_order_queue_patient_code", table_name="branch_lis_order_queue")
    op.drop_index("ix_branch_lis_order_queue_patient_id", table_name="branch_lis_order_queue")
    op.drop_index("ix_branch_lis_order_queue_daily_entry_id", table_name="branch_lis_order_queue")
    op.drop_index("ix_branch_lis_order_queue_branch_id", table_name="branch_lis_order_queue")
    op.drop_index("ix_branch_lis_order_queue_id", table_name="branch_lis_order_queue")
    op.drop_table("branch_lis_order_queue")

    op.drop_index("ix_branch_lis_test_panels_branch_id", table_name="branch_lis_test_panels")
    op.drop_index("ix_branch_lis_test_panels_id", table_name="branch_lis_test_panels")
    op.drop_table("branch_lis_test_panels")

    op.drop_index("ix_branch_lis_test_catalog_branch_id", table_name="branch_lis_test_catalog")
    op.drop_index("ix_branch_lis_test_catalog_id", table_name="branch_lis_test_catalog")
    op.drop_table("branch_lis_test_catalog")

