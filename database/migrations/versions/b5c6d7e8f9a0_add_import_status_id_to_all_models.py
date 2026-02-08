"""Add import_status_id to all models for data provenance tracking

Revision ID: b5c6d7e8f9a0
Revises: a1b2c3d4e5f6
Create Date: 2026-01-04

This migration adds import_status_id foreign key column to ALL tables
(except import_status itself and alembic_version) to enable data
provenance tracking - knowing which import file created each record.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'b5c6d7e8f9a0'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables to exclude from import tracking (they don't need source tracking)
EXCLUDE_TABLES = {
    'import_status',           # The source table itself
    'alembic_version',         # Alembic metadata
}

# PostgreSQL max identifier length
MAX_IDENTIFIER_LENGTH = 63


def get_index_name(table_name: str) -> str:
    """Generate a valid index name, truncating if necessary.

    PostgreSQL has a max identifier length of 63 characters.
    Format: ix_{table_name}_imp_status (shortened suffix for long tables)
    """
    suffix = '_import_status_id'
    prefix = 'ix_'

    full_name = f'{prefix}{table_name}{suffix}'

    if len(full_name) <= MAX_IDENTIFIER_LENGTH:
        return full_name

    # Use shortened suffix for long table names
    short_suffix = '_imp_st_id'
    short_name = f'{prefix}{table_name}{short_suffix}'

    if len(short_name) <= MAX_IDENTIFIER_LENGTH:
        return short_name

    # Truncate table name if still too long
    max_table_len = MAX_IDENTIFIER_LENGTH - len(prefix) - len(short_suffix)
    truncated_table = table_name[:max_table_len]
    return f'{prefix}{truncated_table}{short_suffix}'


def get_all_tables():
    """Get all table names from the database, excluding system tables."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    return [t for t in tables if t not in EXCLUDE_TABLES]


def upgrade() -> None:
    """Add import_status_id column to all tables.

    Uses a two-phase approach to avoid deadlocks:
    1. First pass: Add columns without FK constraints
    2. Second pass: Add indexes
    3. Third pass: Add FK constraints
    """
    tables = get_all_tables()
    tables_modified = []

    # Phase 1: Add columns without FK constraint
    print("Phase 1: Adding columns...")
    for table_name in tables:
        connection = op.get_bind()
        inspector = sa.inspect(connection)
        columns = [col['name'] for col in inspector.get_columns(table_name)]

        if 'import_status_id' not in columns:
            print(f"  Adding column to {table_name}")
            op.add_column(
                table_name,
                sa.Column(
                    'import_status_id',
                    UUID(as_uuid=True),
                    nullable=True,
                    comment='Reference to import batch that created/updated this record'
                )
            )
            tables_modified.append(table_name)
        else:
            print(f"  Skipping {table_name} - column already exists")

    # Phase 2: Add indexes (after all columns exist)
    print("Phase 2: Creating indexes...")
    for table_name in tables_modified:
        index_name = get_index_name(table_name)
        print(f"  Creating index on {table_name}")
        try:
            op.create_index(
                index_name,
                table_name,
                ['import_status_id'],
                unique=False
            )
        except Exception as e:
            print(f"  Warning: Could not create index on {table_name}: {e}")

    # Phase 3: Add FK constraints
    print("Phase 3: Adding foreign key constraints...")
    for table_name in tables_modified:
        fk_name = f'fk_{table_name[:40]}_import_status'
        print(f"  Adding FK to {table_name}")
        try:
            op.create_foreign_key(
                fk_name,
                table_name,
                'import_status',
                ['import_status_id'],
                ['id'],
                ondelete='SET NULL'
            )
        except Exception as e:
            print(f"  Warning: Could not add FK to {table_name}: {e}")

    print(f"Migration complete: Modified {len(tables_modified)} tables")


def downgrade() -> None:
    """Remove import_status_id column from all tables."""
    tables = get_all_tables()

    for table_name in tables:
        # Check if column exists
        connection = op.get_bind()
        inspector = sa.inspect(connection)
        columns = [col['name'] for col in inspector.get_columns(table_name)]

        if 'import_status_id' in columns:
            print(f"Removing import_status_id from {table_name}")

            # Drop FK constraint first
            fk_name = f'fk_{table_name[:40]}_import_status'
            try:
                op.drop_constraint(fk_name, table_name, type_='foreignkey')
            except Exception:
                pass  # FK might not exist

            # Drop the index
            try:
                index_name = get_index_name(table_name)
                op.drop_index(index_name, table_name=table_name)
            except Exception:
                pass  # Index might not exist

            # Drop the column
            op.drop_column(table_name, 'import_status_id')

    print(f"Downgrade complete: Removed import_status_id from {len(tables)} tables")
