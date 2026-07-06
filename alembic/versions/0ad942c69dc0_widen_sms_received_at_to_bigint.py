"""widen sms received_at to bigint

Revision ID: 0ad942c69dc0
Revises: 07e4d3956e63
Create Date: 2026-07-06 23:03:43.722500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ad942c69dc0'
down_revision: Union[str, Sequence[str], None] = '07e4d3956e63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
