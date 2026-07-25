"""add daily entry module

Revision ID: add_daily_entry_module
Revises: 3f1a2b4c5d6e
Create Date: 2026-05-07 07:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import DECIMAL

# revision identifiers, used by Alembic.
revision = 'add_daily_entry_module'
down_revision = '3f1a2b4c5d6e'
branch_labels = None
depends_on = None


def upgrade():
    # Create daily_entries_module table
    op.create_table(
        'daily_entries_module',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('auto_patient_id', sa.String(length=50), nullable=False),
        sa.Column('auto_entry_datetime', sa.DateTime(), nullable=False),
        sa.Column('patient_name', sa.String(length=200), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('mobile', sa.String(length=15), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('referred_doctor', sa.String(length=200), nullable=True),
        sa.Column('test_name', sa.String(length=500), nullable=False),
        sa.Column('report_pdf_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('fee_amount', DECIMAL(10, 2), nullable=False),
        sa.Column('tax_percent', sa.Float(), nullable=True),
        sa.Column('total_amount', DECIMAL(10, 2), nullable=False),
        sa.Column('payment_method', sa.String(length=20), nullable=False),
        sa.Column('is_paid', sa.Boolean(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], )
    )
    op.create_index(op.f('ix_daily_entries_module_id'), 'daily_entries_module', ['id'], unique=False)
    op.create_index(op.f('ix_daily_entries_module_branch_id'), 'daily_entries_module', ['branch_id'], unique=False)
    op.create_index(op.f('ix_daily_entries_module_auto_patient_id'), 'daily_entries_module', ['auto_patient_id'], unique=True)
    op.create_index(op.f('ix_daily_entries_module_patient_name'), 'daily_entries_module', ['patient_name'], unique=False)
    op.create_index(op.f('ix_daily_entries_module_referred_doctor'), 'daily_entries_module', ['referred_doctor'], unique=False)
    op.create_index(op.f('ix_daily_entries_module_test_name'), 'daily_entries_module', ['test_name'], unique=False)

    # Create daily_expenses_module table
    op.create_table(
        'daily_expenses_module',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('entry_date', sa.DateTime(), nullable=False),
        sa.Column('expense_item', sa.String(length=200), nullable=False),
        sa.Column('cost', DECIMAL(10, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], )
    )
    op.create_index(op.f('ix_daily_expenses_module_id'), 'daily_expenses_module', ['id'], unique=False)
    op.create_index(op.f('ix_daily_expenses_module_branch_id'), 'daily_expenses_module', ['branch_id'], unique=False)
    op.create_index(op.f('ix_daily_expenses_module_entry_date'), 'daily_expenses_module', ['entry_date'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_daily_expenses_module_entry_date'), table_name='daily_expenses_module')
    op.drop_index(op.f('ix_daily_expenses_module_branch_id'), table_name='daily_expenses_module')
    op.drop_index(op.f('ix_daily_expenses_module_id'), table_name='daily_expenses_module')
    op.drop_table('daily_expenses_module')
    
    op.drop_index(op.f('ix_daily_entries_module_test_name'), table_name='daily_entries_module')
    op.drop_index(op.f('ix_daily_entries_module_referred_doctor'), table_name='daily_entries_module')
    op.drop_index(op.f('ix_daily_entries_module_patient_name'), table_name='daily_entries_module')
    op.drop_index(op.f('ix_daily_entries_module_auto_patient_id'), table_name='daily_entries_module')
    op.drop_index(op.f('ix_daily_entries_module_branch_id'), table_name='daily_entries_module')
    op.drop_index(op.f('ix_daily_entries_module_id'), table_name='daily_entries_module')
    op.drop_table('daily_entries_module')
