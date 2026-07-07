"""add branch bank details table

Revision ID: add_branch_bank_details
Revises: add_daily_entry_module
Create Date: 2026-07-06 01:44:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'add_branch_bank_details'
down_revision = 'add_daily_entry_module'
branch_labels = None
depends_on = None


def upgrade():
    # Create branch_bank_details table
    op.create_table(
        'branch_bank_details',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('account_holder_name', sa.String(length=255), nullable=False),
        sa.Column('account_number', sa.String(length=50), nullable=False),
        sa.Column('ifsc_code', sa.String(length=20), nullable=False),
        sa.Column('bank_name', sa.String(length=255), nullable=False),
        sa.Column('upi_id', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
        sa.UniqueConstraint('branch_id')
    )
    
    # Create indexes
    op.create_index('ix_branch_bank_details_id', 'branch_bank_details', ['id'])
    op.create_index('ix_branch_bank_details_upi_id', 'branch_bank_details', ['upi_id'])


def downgrade():
    op.drop_index('ix_branch_bank_details_upi_id', table_name='branch_bank_details')
    op.drop_index('ix_branch_bank_details_id', table_name='branch_bank_details')
    op.drop_table('branch_bank_details')
