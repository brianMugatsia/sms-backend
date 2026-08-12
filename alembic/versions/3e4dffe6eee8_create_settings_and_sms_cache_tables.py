"""create settings and sms_cache tables

Revision ID: 3e4dffe6eee8
Revises: 21b5d749ebab
Create Date: 2026-08-12 13:46:02.294841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e4dffe6eee8'
down_revision: Union[str, Sequence[str], None] = '21b5d749ebab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # --- Operations on 'settings' table ---
    if 'settings' in tables:
        unique_constraints = [c['name'] for c in inspector.get_unique_constraints('settings')]
        if 'settings_device_id_key' in unique_constraints:
            op.drop_constraint('settings_device_id_key', 'settings', type_='unique')

        settings_indexes = [i['name'] for i in inspector.get_indexes('settings')]
        if 'ix_settings_device_id' in settings_indexes:
            op.drop_index('ix_settings_device_id', table_name='settings')

        settings_indexes_updated = [i['name'] for i in inspector.get_indexes('settings')]
        if 'ix_settings_device_id' not in settings_indexes_updated:
            op.create_index(op.f('ix_settings_device_id'), 'settings', ['device_id'], unique=True)

    # --- Operations on 'sms_cache' table ---
    if 'sms_cache' in tables:
        sms_cache_indexes = [i['name'] for i in inspector.get_indexes('sms_cache')]
        if 'idx_sms_device_deleted_timestamp' in sms_cache_indexes:
            op.drop_index('idx_sms_device_deleted_timestamp', table_name='sms_cache')

        sms_cache_indexes_updated = [i['name'] for i in inspector.get_indexes('sms_cache')]
        if 'idx_sms_device_deleted_timestamp' not in sms_cache_indexes_updated:
            op.create_index('idx_sms_device_deleted_timestamp', 'sms_cache', ['device_id', 'deleted', 'timestamp'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'sms_cache' in tables:
        sms_cache_indexes = [i['name'] for i in inspector.get_indexes('sms_cache')]
        if 'idx_sms_device_deleted_timestamp' in sms_cache_indexes:
            op.drop_index('idx_sms_device_deleted_timestamp', table_name='sms_cache')

        sms_cache_indexes_updated = [i['name'] for i in inspector.get_indexes('sms_cache')]
        if 'idx_sms_device_deleted_timestamp' not in sms_cache_indexes_updated:
            op.create_index(
                op.f('idx_sms_device_deleted_timestamp'),
                'sms_cache',
                ['device_id', 'deleted', sa.literal_column('timestamp DESC')],
                unique=False
            )

    if 'settings' in tables:
        settings_indexes = [i['name'] for i in inspector.get_indexes('settings')]
        if 'ix_settings_device_id' in settings_indexes:
            op.drop_index('ix_settings_device_id', table_name='settings')

        settings_indexes_updated = [i['name'] for i in inspector.get_indexes('settings')]
        if 'ix_settings_device_id' not in settings_indexes_updated:
            op.create_index(op.f('ix_settings_device_id'), 'settings', ['device_id'], unique=False)

        unique_constraints = [c['name'] for c in inspector.get_unique_constraints('settings')]
        if 'settings_device_id_key' not in unique_constraints:
            op.create_unique_constraint(
                op.f('settings_device_id_key'),
                'settings',
                ['device_id'],
                postgresql_nulls_not_distinct=False
            )