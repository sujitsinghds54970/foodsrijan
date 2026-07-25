"""add patient b2c phase3 loyalty growth tables

Revision ID: 20260724_add_patient_b2c_phase3_loyalty_growth
Revises: 20260724_add_patient_b2c_phase2_ai_engagement
Create Date: 2026-07-24 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260724_add_patient_b2c_phase3_loyalty_growth"
down_revision = "20260724_add_patient_b2c_phase2_ai_engagement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_loyalty_rewards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transaction_type", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_loyalty_rewards_id", "patient_loyalty_rewards", ["id"], unique=False)
    op.create_index("ix_patient_loyalty_rewards_patient_id", "patient_loyalty_rewards", ["patient_id"], unique=False)
    op.create_index("ix_patient_loyalty_rewards_transaction_type", "patient_loyalty_rewards", ["transaction_type"], unique=False)
    op.create_index("ix_patient_loyalty_rewards_created_at", "patient_loyalty_rewards", ["created_at"], unique=False)

    op.create_table(
        "patient_referrals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("referrer_id", sa.Integer(), nullable=False),
        sa.Column("referee_id", sa.Integer(), nullable=False),
        sa.Column("bonus_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["referrer_id"], ["patient_profiles.id"]),
        sa.ForeignKeyConstraint(["referee_id"], ["patient_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_referrals_id", "patient_referrals", ["id"], unique=False)
    op.create_index("ix_patient_referrals_referrer_id", "patient_referrals", ["referrer_id"], unique=False)
    op.create_index("ix_patient_referrals_referee_id", "patient_referrals", ["referee_id"], unique=False)
    op.create_index("ix_patient_referrals_created_at", "patient_referrals", ["created_at"], unique=False)

    op.create_table(
        "patient_health_goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("goal_type", sa.String(length=300), nullable=False),
        sa.Column("target_date", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="In Progress"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_health_goals_id", "patient_health_goals", ["id"], unique=False)
    op.create_index("ix_patient_health_goals_patient_id", "patient_health_goals", ["patient_id"], unique=False)
    op.create_index("ix_patient_health_goals_goal_type", "patient_health_goals", ["goal_type"], unique=False)
    op.create_index("ix_patient_health_goals_target_date", "patient_health_goals", ["target_date"], unique=False)
    op.create_index("ix_patient_health_goals_status", "patient_health_goals", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_patient_health_goals_status", table_name="patient_health_goals")
    op.drop_index("ix_patient_health_goals_target_date", table_name="patient_health_goals")
    op.drop_index("ix_patient_health_goals_goal_type", table_name="patient_health_goals")
    op.drop_index("ix_patient_health_goals_patient_id", table_name="patient_health_goals")
    op.drop_index("ix_patient_health_goals_id", table_name="patient_health_goals")
    op.drop_table("patient_health_goals")

    op.drop_index("ix_patient_referrals_created_at", table_name="patient_referrals")
    op.drop_index("ix_patient_referrals_referee_id", table_name="patient_referrals")
    op.drop_index("ix_patient_referrals_referrer_id", table_name="patient_referrals")
    op.drop_index("ix_patient_referrals_id", table_name="patient_referrals")
    op.drop_table("patient_referrals")

    op.drop_index("ix_patient_loyalty_rewards_created_at", table_name="patient_loyalty_rewards")
    op.drop_index("ix_patient_loyalty_rewards_transaction_type", table_name="patient_loyalty_rewards")
    op.drop_index("ix_patient_loyalty_rewards_patient_id", table_name="patient_loyalty_rewards")
    op.drop_index("ix_patient_loyalty_rewards_id", table_name="patient_loyalty_rewards")
    op.drop_table("patient_loyalty_rewards")
