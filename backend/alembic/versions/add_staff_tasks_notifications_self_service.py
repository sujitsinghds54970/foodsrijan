"""add staff tasks and notifications for self service

Revision ID: add_staff_tasks_notifications_self_service
Revises: add_staff_module_phase_features
Create Date: 2026-07-11 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_staff_tasks_notifications_self_service"
down_revision = "add_staff_module_phase_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("staff_profile_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Pending"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="Medium"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_staff_tasks_id", "staff_tasks", ["id"])

    op.create_table(
        "staff_notifications",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("staff_profile_id", sa.Integer(), sa.ForeignKey("staff_profiles.id"), nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("link", sa.String(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_staff_notifications_id", "staff_notifications", ["id"])


def downgrade() -> None:
    op.drop_index("ix_staff_notifications_id", table_name="staff_notifications")
    op.drop_table("staff_notifications")

    op.drop_index("ix_staff_tasks_id", table_name="staff_tasks")
    op.drop_table("staff_tasks")
