#!/usr/bin/env python3
"""
Cleanup Duplicate Import Status Records
========================================

This script removes duplicate records from import_status table before adding
a unique constraint on (file_name, category, legislatura).

Duplicate selection strategy:
- Keep the record with the most complete data
- Prefer: has file_hash > has file_path > latest updated_at > lowest id

Run this BEFORE applying the UniqueConstraint migration.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import datetime
from sqlalchemy import func
from database.connection import DatabaseSession
from database.models import ImportStatus


def find_duplicate_groups(db_session):
    """Find all (file_name, category, legislatura) combinations with duplicates."""
    return (
        db_session.query(
            ImportStatus.file_name,
            ImportStatus.category,
            ImportStatus.legislatura,
            func.count(ImportStatus.id).label("count"),
        )
        .group_by(
            ImportStatus.file_name,
            ImportStatus.category,
            ImportStatus.legislatura,
        )
        .having(func.count(ImportStatus.id) > 1)
        .all()
    )


def score_record(record: ImportStatus) -> tuple:
    """
    Score a record for keeping. Higher score = better record to keep.
    Returns tuple for comparison: (has_hash, has_path, has_size, updated_at, -id)
    """
    return (
        1 if record.file_hash else 0,  # Prefer records with file hash
        1 if record.file_path else 0,  # Prefer records with file path
        1 if record.file_size else 0,  # Prefer records with file size
        record.updated_at or datetime.min,  # Prefer more recently updated
        -record.id,  # Prefer lower id (oldest) as tiebreaker
    )


def cleanup_duplicates(dry_run: bool = True):
    """
    Clean up duplicate import_status records.

    Args:
        dry_run: If True, only report what would be deleted without making changes.
    """
    with DatabaseSession() as db:
        duplicate_groups = find_duplicate_groups(db)

        if not duplicate_groups:
            print("No duplicates found. Database is clean.")
            return 0

        total_duplicates = sum(g.count - 1 for g in duplicate_groups)
        print(f"Found {len(duplicate_groups)} duplicate groups with {total_duplicates} records to remove")
        print()

        records_to_delete = []

        for group in duplicate_groups:
            # Get all records in this duplicate group
            records = (
                db.query(ImportStatus)
                .filter_by(
                    file_name=group.file_name,
                    category=group.category,
                    legislatura=group.legislatura,
                )
                .all()
            )

            # Score and sort records - best first
            scored_records = [(score_record(r), r) for r in records]
            scored_records.sort(reverse=True)

            # Keep the best record, mark others for deletion
            keeper = scored_records[0][1]
            duplicates = [sr[1] for sr in scored_records[1:]]

            # If keeper doesn't have the latest URL, update it
            latest_url_record = max(records, key=lambda r: r.updated_at or datetime.min)
            if keeper.file_url != latest_url_record.file_url:
                print(f"  Updating URL for keeper {keeper.id}: {keeper.file_name}")
                if not dry_run:
                    keeper.file_url = latest_url_record.file_url
                    keeper.updated_at = datetime.now()

            for dup in duplicates:
                records_to_delete.append(dup)
                print(f"  {'Would delete' if dry_run else 'Deleting'}: id={dup.id} | {dup.file_name[:40]}... | {dup.category} | {dup.legislatura}")

        print()
        print(f"{'Would delete' if dry_run else 'Deleted'} {len(records_to_delete)} duplicate records")

        if not dry_run:
            for record in records_to_delete:
                db.delete(record)
            db.commit()
            print("Changes committed to database.")
        else:
            print("\nDry run complete. Run with --execute to apply changes.")

        return len(records_to_delete)


def verify_no_duplicates():
    """Verify that no duplicates remain after cleanup."""
    with DatabaseSession() as db:
        duplicate_groups = find_duplicate_groups(db)
        if duplicate_groups:
            print(f"ERROR: Still found {len(duplicate_groups)} duplicate groups!")
            return False
        else:
            print("SUCCESS: No duplicates found. Safe to add UniqueConstraint.")
            return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup duplicate import_status records")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete duplicates (default is dry-run)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify no duplicates exist",
    )
    args = parser.parse_args()

    if args.verify:
        success = verify_no_duplicates()
        sys.exit(0 if success else 1)
    else:
        deleted = cleanup_duplicates(dry_run=not args.execute)
        if args.execute:
            verify_no_duplicates()
