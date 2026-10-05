"""use uuid and add full_name

Revision ID: b8f912c34567
Revises: 7a8291bc4321
Create Date: 2026-10-05 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8f912c34567'
down_revision: Union[str, Sequence[str], None] = '7a8291bc4321'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Recreate tables to use UUID primary/foreign keys and add full_name to users."""
    op.execute("DROP TABLE IF EXISTS watchlist CASCADE")
    op.execute("DROP TABLE IF EXISTS reviews CASCADE")
    op.execute("DROP TABLE IF EXISTS films CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")

    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('full_name', sa.String(length=100), server_default='', nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='user', nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. films
    op.create_table(
        'films',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('director', sa.String(length=100), nullable=False),
        sa.Column('release_year', sa.Integer(), nullable=False),
        sa.Column('genre', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_films_title', 'films', ['title'], unique=False)
    op.create_index('ix_films_genre', 'films', ['genre'], unique=False)
    op.create_index('ix_films_release_year', 'films', ['release_year'], unique=False)

    # 3. reviews
    op.create_table(
        'reviews',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('film_id', sa.Uuid(), sa.ForeignKey('films.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review', sa.Text(), nullable=False),
        sa.Column('reviewer_display_name', sa.String(length=50), server_default='Anonymous Critic', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_reviews_film_id', 'reviews', ['film_id'], unique=False)
    op.create_index('ix_reviews_user_id', 'reviews', ['user_id'], unique=False)

    # 4. watchlist
    op.create_table(
        'watchlist',
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('film_id', sa.Uuid(), sa.ForeignKey('films.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_watchlist_film_id', 'watchlist', ['film_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('watchlist')
    op.drop_table('reviews')
    op.drop_table('films')
    op.drop_table('users')
