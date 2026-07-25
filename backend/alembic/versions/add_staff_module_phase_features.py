"""add staff module phase features

Revision ID: add_staff_module_phase_features
Revises: 08e1282c63ce
Create Date: 2026-07-09 05:40:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_staff_module_phase_features"
down_revision = "08e1282c63ce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staff_salary_details", sa.Column("hra", sa.DECIMAL(12, 2), nullable=True))

    op.create_table(
        "staff_salary_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("staff_profile_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("basic_salary", sa.DECIMAL(12, 2), nullable=True),
        sa.Column("hra", sa.DECIMAL(12, 2), nullable=True),
        sa.Column("allowances", sa.DECIMAL(12, 2), nullable=True),
        sa.Column("deductions", sa.DECIMAL(12, 2), nullable=True),
        sa.Column("net_pay", sa.DECIMAL(12, 2), nullable=True),
        sa.Column("generated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_staff_salary_records_id", "staff_salary_records", ["id"])

    op.create_table(
        "staff_weekly_rosters",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("staff_profile_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("week_start_date", sa.DateTime(), nullable=False),
        sa.Column("week_end_date", sa.DateTime(), nullable=False),
        sa.Column("schedule_json", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_staff_weekly_rosters_id", "staff_weekly_rosters", ["id"])


def downgrade() -> None:
    op.drop_index("ix_staff_weekly_rosters_id", table_name="staff_weekly_rosters")
    op.drop_table("staff_weekly_rosters")

    op.drop_index("ix_staff_salary_records_id", table_name="staff_salary_records")
    op.drop_table("staff_salary_records")

    op.drop_column("staff_salary_details", "hra")
