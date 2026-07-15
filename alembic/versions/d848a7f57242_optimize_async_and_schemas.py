"""optimize_async_and_schemas

Revision ID: d848a7f57242
Revises: b51e00bffc73
Create Date: 2026-07-15 13:05:19.769435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'd848a7f57242'
down_revision: Union[str, Sequence[str], None] = 'b51e00bffc73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Kept clean to preserve the existing users, devices, and sms tables 
    # while synchronizing code changes safely.
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Kept clean to ensure no schema regressions or accidental adjustments occur.
    pass