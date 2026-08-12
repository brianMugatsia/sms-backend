"""add deleted column to sms_cache

Revision ID: 21b5d749ebab
Revises: d848a7f57242
Create Date: 2026-07-24 00:57:24.330726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '21b5d749ebab'
down_revision: Union[str, Sequence[str], None] = 'd848a7f57242'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check existing columns and indexes
    existing_columns = [c['name'] for c in inspector.get_columns('sms_cache')]
    existing_indexes = [i['name'] for i in inspector.get_indexes('sms_cache')]

    # Add 'deleted' column if missing
    if 'deleted' not in existing_columns:
        op.add_column(
            'sms_cache',
            sa.Column('deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    # Safely create index on 'deleted'
    if 'ix_sms_cache_deleted' not in existing_indexes:
        op.create_index(op.f('ix_sms_cache_deleted'), 'sms_cache', ['deleted'], unique=False)

    # Safely create index on 'device_id'
    if 'ix_sms_cache_device_id' not in existing_indexes:
        op.create_index(op.f('ix_sms_cache_device_id'), 'sms_cache', ['device_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    existing_columns = [c['name'] for c in inspector.get_columns('sms_cache')]
    existing_indexes = [i['name'] for i in inspector.get_indexes('sms_cache')]

    if 'ix_sms_cache_device_id' in existing_indexes:
        op.drop_index(op.f('ix_sms_cache_device_id'), table_name='sms_cache')

    if 'ix_sms_cache_deleted' in existing_indexes:
        op.drop_index(op.f('ix_sms_cache_deleted'), table_name='sms_cache')

    if 'deleted' in existing_columns:
        op.drop_column('sms_cache', 'deleted')