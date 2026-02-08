#!/usr/bin/env python3
"""
Script to check corrupted files in the import status table.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from database.connection import get_session
from database.models import ImportStatus


def main():
    """Check and display corrupted files."""
    session = get_session()
    
    try:
        # Query for corrupted files
        corrupted_files = session.query(ImportStatus).filter(
            ImportStatus.status == 'corrupted'
        ).order_by(ImportStatus.processing_completed_at.desc()).all()
        
        if not corrupted_files:
            print("No corrupted files found in import status.")
            return
        
        print(f"\nFound {len(corrupted_files)} corrupted files:")
        print("=" * 80)
        
        for file_record in corrupted_files:
            print(f"File: {file_record.file_name}")
            print(f"Path: {file_record.file_path}")
            print(f"Category: {file_record.category}")
            print(f"Legislatura: {file_record.legislatura or 'N/A'}")
            print(f"Error: {file_record.error_message}")
            print(f"Size: {file_record.file_size or 'Unknown'} bytes")
            print(f"Detected: {file_record.processing_completed_at}")
            print("-" * 80)
        
        # Summary by category
        print("\nCorrupted files by category:")
        categories = {}
        for file_record in corrupted_files:
            cat = file_record.category
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        for category, count in sorted(categories.items()):
            print(f"  {category}: {count} files")
            
    finally:
        session.close()


if __name__ == "__main__":
    main()