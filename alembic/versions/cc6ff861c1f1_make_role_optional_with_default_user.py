"""make role optional with default user

Revision ID: cc6ff861c1f1
Revises: c1f151c62ca9
Create Date: 2026-06-25 23:31:56.480933
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cc6ff861c1f1'
down_revision: Union[str, Sequence[str], None] = 'c1f151c62ca9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'users',
        'role',
        existing_type=sa.String(length=50),
        nullable=True,
        server_default='user'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'users',
        'role',
        existing_type=sa.String(length=50),
        nullable=False,
        server_default=None
    )
