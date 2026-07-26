"""add branch lis phase 3/4 feature tables

Revision ID: 20260727_add_branch_lis_phase34_features
Revises: 20260727_add_branch_lis_command_center
Create Date: 2026-07-27 00:46:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260727_add_branch_lis_phase34_features"
down_revision: Union[str, Sequence[str], None] = "20260727_add_branch_lis_command_center"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "branch_lis_proficiency_test_runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("program_name", sa.String(length=160), nullable=False),
        sa.Column("cycle_name", sa.String(length=120), nullable=False),
        sa.Column("department", sa.String(length=80), nullable=False),
        sa.Column("participation_status", sa.String(length=30), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_branch_lis_proficiency_test_runs_id", "branch_lis_proficiency_test_runs", ["id"], unique=False)
    op.create_index("ix_branch_lis_proficiency_test_runs_branch_id", "branch_lis_proficiency_test_runs", ["branch_id"], unique=False)

    op.create_table(
        "branch_lis_report_archive",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("branch_lis_order_queue.id"), nullable=False),
        sa.Column("sample_id", sa.Integer(), sa.ForeignKey("branch_lis_samples.id"), nullable=True),
        sa.Column("report_number", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template_name", sa.String(length=160), nullable=False),
        sa.Column("signed_by", sa.String(length=160), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("channels_json", sa.JSON(), nullable=True),
        sa.Column("report_payload_json", sa.JSON(), nullable=True),
        sa.Column("report_pdf_base64", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_branch_lis_report_archive_id", "branch_lis_report_archive", ["id"], unique=False)
    op.create_index("ix_branch_lis_report_archive_branch_id", "branch_lis_report_archive", ["branch_id"], unique=False)
    op.create_index("ix_branch_lis_report_archive_order_id", "branch_lis_report_archive", ["order_id"], unique=False)
    op.create_index("ix_branch_lis_report_archive_sample_id", "branch_lis_report_archive", ["sample_id"], unique=False)
    op.create_index("ix_branch_lis_report_archive_report_number", "branch_lis_report_archive", ["report_number"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_branch_lis_report_archive_report_number", table_name="branch_lis_report_archive")
    op.drop_index("ix_branch_lis_report_archive_sample_id", table_name="branch_lis_report_archive")
    op.drop_index("ix_branch_lis_report_archive_order_id", table_name="branch_lis_report_archive")
    op.drop_index("ix_branch_lis_report_archive_branch_id", table_name="branch_lis_report_archive")
    op.drop_index("ix_branch_lis_report_archive_id", table_name="branch_lis_report_archive")
    op.drop_table("branch_lis_report_archive")

    op.drop_index("ix_branch_lis_proficiency_test_runs_branch_id", table_name="branch_lis_proficiency_test_runs")
    op.drop_index("ix_branch_lis_proficiency_test_runs_id", table_name="branch_lis_proficiency_test_runs")
    op.drop_table("branch_lis_proficiency_test_runs")

