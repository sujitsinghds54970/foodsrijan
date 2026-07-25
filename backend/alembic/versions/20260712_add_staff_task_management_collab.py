"""add enterprise staff task management and collaboration tables

Revision ID: 20260712_add_staff_task_management_collab
Revises: 20260712_add_payroll_management_suite
Create Date: 2026-07-12 07:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260712_add_staff_task_management_collab"
down_revision = "20260712_add_payroll_management_suite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())
    task_columns = {col["name"] for col in inspector.get_columns("staff_tasks")} if "staff_tasks" in existing_tables else set()

    if "assigned_by" not in task_columns:
        op.add_column("staff_tasks", sa.Column("assigned_by", sa.Integer(), nullable=True))
    if "assigned_to" not in task_columns:
        op.add_column("staff_tasks", sa.Column("assigned_to", sa.Integer(), nullable=True))
    if "title" not in task_columns:
        op.add_column("staff_tasks", sa.Column("title", sa.String(length=255), nullable=True))
    if "due_date" not in task_columns:
        op.add_column("staff_tasks", sa.Column("due_date", sa.DateTime(), nullable=True))
    if "completed_at" not in task_columns:
        op.add_column("staff_tasks", sa.Column("completed_at", sa.DateTime(), nullable=True))

    # SQLite cannot add foreign key constraints with ALTER TABLE in-place.
    # The columns are still added and validated in app logic.

    if "task_comments" not in existing_tables:
        op.create_table(
            "task_comments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("task_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["task_id"], ["staff_tasks.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_task_comments_id", "task_comments", ["id"], unique=False)

    if "task_attachments" not in existing_tables:
        op.create_table(
            "task_attachments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("task_id", sa.Integer(), nullable=False),
            sa.Column("file_url", sa.String(), nullable=False),
            sa.Column("uploaded_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["task_id"], ["staff_tasks.id"]),
            sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_task_attachments_id", "task_attachments", ["id"], unique=False)

    op.execute("UPDATE staff_tasks SET title = task_name WHERE title IS NULL")
    op.execute("UPDATE staff_tasks SET due_date = deadline WHERE due_date IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())

    if "task_attachments" in existing_tables:
        attachment_indexes = {idx["name"] for idx in inspector.get_indexes("task_attachments")}
        if "ix_task_attachments_id" in attachment_indexes:
            op.drop_index("ix_task_attachments_id", table_name="task_attachments")
        op.drop_table("task_attachments")

    if "task_comments" in existing_tables:
        comment_indexes = {idx["name"] for idx in inspector.get_indexes("task_comments")}
        if "ix_task_comments_id" in comment_indexes:
            op.drop_index("ix_task_comments_id", table_name="task_comments")
        op.drop_table("task_comments")

    if "staff_tasks" in existing_tables:
        task_columns = {col["name"] for col in inspector.get_columns("staff_tasks")}

        if "completed_at" in task_columns:
            op.drop_column("staff_tasks", "completed_at")
        if "due_date" in task_columns:
            op.drop_column("staff_tasks", "due_date")
        if "title" in task_columns:
            op.drop_column("staff_tasks", "title")
        if "assigned_to" in task_columns:
            op.drop_column("staff_tasks", "assigned_to")
        if "assigned_by" in task_columns:
            op.drop_column("staff_tasks", "assigned_by")
