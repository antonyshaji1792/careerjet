"""add profile_picture_path to user_profile

Revision ID: f3a7b8c2e9d4
Revises: d91bdb1fdcb6
Create Date: 2026-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a7b8c2e9d4'
down_revision = 'd91bdb1fdcb6'
branch_labels = None
depends_on = None


def upgrade():
    # Add profile_picture_path column to user_profile
    op.add_column('user_profile', sa.Column('profile_picture_path', sa.String(length=255), nullable=True))


def downgrade():
    # Remove profile_picture_path column
    op.drop_column('user_profile', 'profile_picture_path')
