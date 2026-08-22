"""add doctor portal phase3 ai engagement

Revision ID: 20260723_add_doctor_portal_phase3_ai_engagement
Revises: 20260723_add_doctor_portal_phase2
Create Date: 2026-07-23 19:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260723_add_doctor_portal_phase3_ai_engagement"
down_revision = "20260723_add_doctor_portal_phase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctor_loyalty_rewards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False, server_default="Silver"),
        sa.Column("benefits", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["doctor_id"], ["staff.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_doctor_loyalty_rewards_id", "doctor_loyalty_rewards", ["id"], unique=False)
    op.create_index("ix_doctor_loyalty_rewards_doctor_id", "doctor_loyalty_rewards", ["doctor_id"], unique=False)
    op.create_index("ix_doctor_loyalty_rewards_tier", "doctor_loyalty_rewards", ["tier"], unique=False)

    op.create_table(
        "doctor_cme_courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("duration", sa.String(length=60), nullable=False),
        sa.Column("link", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_doctor_cme_courses_id", "doctor_cme_courses", ["id"], unique=False)
    op.create_index("ix_doctor_cme_courses_is_active", "doctor_cme_courses", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_table("doctor_cme_courses")
    op.drop_table("doctor_loyalty_rewards")
