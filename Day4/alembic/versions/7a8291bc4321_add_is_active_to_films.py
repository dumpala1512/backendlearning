"""add is_active to films

Revision ID: 7a8291bc4321
Revises: 4d1668473519
Create Date: 2026-10-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8291bc4321'
down_revision: Union[str, Sequence[str], None] = '4d1668473519'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add is_active column."""
    op.add_column(
        'films',
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema to remove is_active column."""
    op.drop_column('films', 'is_active')
