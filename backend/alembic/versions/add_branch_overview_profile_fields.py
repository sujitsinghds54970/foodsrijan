"""add branch overview profile fields

Revision ID: add_branch_overview_profile_fields
Revises: add_director_staff_management
Create Date: 2026-07-09 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_branch_overview_profile_fields"
down_revision = "add_director_staff_management"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("branches", sa.Column("director_photo_url", sa.Text(), nullable=True))
    op.add_column("branches", sa.Column("director_age", sa.String(length=50), nullable=True))
    op.add_column("branches", sa.Column("director_credentials_username", sa.String(length=100), nullable=True))
    op.add_column("branches", sa.Column("director_credentials_password", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("branches", "director_credentials_password")
    op.drop_column("branches", "director_credentials_username")
    op.drop_column("branches", "director_age")
    op.drop_column("branches", "director_photo_url")
