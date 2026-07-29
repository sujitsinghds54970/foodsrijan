"""add OTP authentication system

Revision ID: add_otp_authentication
Revises: 20260727_add_branch_lis_westgard_rules
Create Date: 2026-07-29 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_otp_authentication"
down_revision = "20260727_add_branch_lis_westgard_rules"
branch_labels = None
depends_on = None


def upgrade():
    # Create OTP Requests table
    op.create_table(
        'otp_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('identifier', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('otp_code', sa.String(length=6), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_otp_requests_identifier', 'identifier'),
        sa.Index('ix_otp_requests_is_used', 'is_used'),
        sa.Index('ix_otp_requests_is_active', 'is_active'),
    )


def downgrade():
    op.drop_table('otp_requests')
