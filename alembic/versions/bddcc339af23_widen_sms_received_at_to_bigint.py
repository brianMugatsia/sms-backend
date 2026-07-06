"""widen sms received_at to bigint

Revision ID: bddcc339af23
Revises: 0ad942c69dc0
Create Date: 2026-07-06 23:03:56.657588

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bddcc339af23'
down_revision: Union[str, Sequence[str], None] = '0ad942c69dc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


"""widen sms received_at to bigint

Revision ID: bddcc339af23
Revises: 0ad942c69dc0
Create Date: 2026-07-06 23:03:56.657588

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bddcc339af23'
down_revision: Union[str, Sequence[str], None] = '0ad942c69dc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'sms',
        'received_at',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'sms',
        'received_at',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
