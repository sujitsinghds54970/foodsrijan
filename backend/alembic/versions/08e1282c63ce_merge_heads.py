"""merge heads

Revision ID: 08e1282c63ce
Revises: add_accounts_finance_module, add_branch_overview_profile_fields
Create Date: 2026-07-09 02:06:46.057953

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08e1282c63ce'
down_revision: Union[str, Sequence[str], None] = ('add_accounts_finance_module', 'add_branch_overview_profile_fields')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
