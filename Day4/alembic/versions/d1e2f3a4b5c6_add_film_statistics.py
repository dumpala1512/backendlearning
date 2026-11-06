"""add film statistics (total_reviews, average_rating)

Revision ID: d1e2f3a4b5c6
Revises: c9a1b2d3e4f5
Create Date: 2026-10-12 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c9a1b2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add total_reviews and average_rating columns to films table."""
    op.add_column(
        'films',
        sa.Column('total_reviews', sa.Integer(), server_default='0', nullable=False),
    )
    op.add_column(
        'films',
        sa.Column('average_rating', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Remove total_reviews and average_rating columns from films table."""
    op.drop_column('films', 'average_rating')
    op.drop_column('films', 'total_reviews')
