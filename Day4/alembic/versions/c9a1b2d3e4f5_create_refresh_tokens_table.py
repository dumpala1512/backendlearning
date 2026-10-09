"""create refresh_tokens table

Revision ID: c9a1b2d3e4f5
Revises: 7a8291bc4321
Create Date: 2026-10-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9a1b2d3e4f5'
down_revision: Union[str, Sequence[str], None] = 'b8f912c34567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop refresh_tokens table if present since refresh tokens are stateless."""
    op.execute("DROP TABLE IF EXISTS refresh_tokens CASCADE")


def downgrade() -> None:
    """No-op downgrade."""
    pass
