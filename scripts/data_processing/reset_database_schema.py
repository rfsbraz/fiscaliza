#!/usr/bin/env python3
"""
Reset database schema for UUID migration.
Drops all tables and recreates from models.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from sqlalchemy import text, inspect
from database.connection import get_engine
from database.models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reset_schema(create_tables=True):
    """Drop all tables and optionally recreate from models."""
    engine = get_engine()

    logger.info("Connecting to database...")

    with engine.connect() as conn:
        # Get inspector to list all tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Found {len(existing_tables)} existing tables")

        # Drop alembic_version first if exists
        if 'alembic_version' in existing_tables:
            logger.info("Dropping alembic_version table...")
            conn.execute(text("DROP TABLE alembic_version CASCADE"))
            conn.commit()

        # Drop all tables using SQLAlchemy metadata
        logger.info("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped")

        # Enable UUID extension for PostgreSQL/Aurora
        logger.info("Enabling uuid-ossp extension...")
        try:
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            conn.commit()
            logger.info("uuid-ossp extension enabled")
        except Exception as e:
            logger.warning(f"Could not enable uuid-ossp (may already exist): {e}")

    if create_tables:
        # Create all tables from models (bypasses alembic autogenerate issues with custom types)
        logger.info("Creating all tables from models...")
        Base.metadata.create_all(bind=engine)

        # Verify table count
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()
        logger.info(f"Created {len(new_tables)} tables")
    else:
        inspector = inspect(engine)
        remaining_tables = inspector.get_table_names()
        logger.info(f"Remaining tables: {len(remaining_tables)}")


if __name__ == "__main__":
    response = input("WARNING: This will DROP ALL TABLES. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        reset_schema(create_tables=False)
        print("\nTables dropped! Now run:")
        print("  1. alembic revision --autogenerate -m 'Initial schema with UUID primary keys'")
        print("  2. alembic upgrade head")
    else:
        logger.info("Reset cancelled.")
