"""Custom SQLAlchemy types for cross-database compatibility."""

import uuid

from sqlalchemy import Uuid

# Use SQLAlchemy's built-in Uuid type (SQLAlchemy 2.0+)
# This provides:
# - Native UUID support for PostgreSQL
# - String(32) fallback for other databases
# - Proper alembic autogenerate detection
#
# This enables client-side UUID generation, eliminating the need
# for session.flush() to obtain primary key IDs after session.add().

# Re-export for backward compatibility
GUID = Uuid
