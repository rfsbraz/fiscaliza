#!/usr/bin/env python
"""
Clean all data from the database to prepare for a fresh import
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from database.connection import DatabaseSession
from database.models import Base
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_all_data():
    """Delete all data from the database using TRUNCATE CASCADE"""

    with DatabaseSession() as session:
        try:
            logger.info("Starting database cleanup...")

            # Get all table names from the metadata
            table_names = [table.name for table in Base.metadata.sorted_tables]

            # Reverse order so children come before parents
            table_names_reversed = list(reversed(table_names))

            logger.info(f"Found {len(table_names)} tables to clean")

            # Use TRUNCATE CASCADE to handle FK dependencies automatically
            # This is PostgreSQL specific but much faster and handles all dependencies
            for table_name in table_names_reversed:
                try:
                    # Check if table has data
                    result = session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                    count = result.scalar()

                    if count > 0:
                        logger.info(f"Truncating {table_name} ({count} records)...")
                        session.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                    else:
                        logger.info(f"  {table_name} is already empty")
                except Exception as e:
                    logger.warning(f"  Could not truncate {table_name}: {e}")

            session.commit()
            logger.info("Database cleanup completed successfully!")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            session.rollback()
            raise

if __name__ == "__main__":
    response = input("WARNING: This will delete ALL data from the database. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        clean_all_data()
    else:
        logger.info("Cleanup cancelled.")
