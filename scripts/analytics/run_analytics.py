#!/usr/bin/env python3
"""
Simple Analytics Runner

A simple wrapper script for running analytics updates.
Perfect for integration with data import scripts or cron jobs.

Usage:
    python run_analytics.py                    # Quick update using Python calculations
    python run_analytics.py --full             # Full analytics recalculation
    python run_analytics.py --legislature 15   # Update specific legislature
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.connection import get_engine
from scripts.analytics.quick_update_analytics import QuickAnalyticsUpdater
from scripts.analytics.batch_analytics_processor import BatchAnalyticsProcessor


def run_quick_analytics(legislatura_id: int = None) -> bool:
    """Run quick analytics update using pure Python calculations."""
    try:
        print("Starting Quick Analytics Update...")
        engine = get_engine()
        updater = QuickAnalyticsUpdater(engine)
        
        # Test analytics system first
        if not updater.test_analytics_system():
            print("ERROR Analytics system not ready. Run migration first.")
            return False
        
        if legislatura_id:
            updated_count = updater.bulk_update_legislature(legislatura_id)
            print(f"OK Quick update completed: {updated_count} deputies updated in legislature {legislatura_id}")
        else:
            # Update recent changes for all legislatures
            with updater.Session() as session:
                from database.models import Legislaturas
                legislatures = session.query(Legislaturas.id).all()
                
                total_updated = 0
                for leg_id, in legislatures:
                    updated = updater.update_recent_changes(leg_id, hours=48)  # Last 48 hours
                    total_updated += updated
                
                print(f"OK Quick update completed: {total_updated} deputies updated across all legislatures")
        
        return True
        
    except Exception as e:
        print(f"Quick analytics update failed: {e}")
        return False


def run_full_analytics(legislatura_id: int = None) -> bool:
    """Run full analytics calculation."""
    try:
        print("Starting Full Analytics Calculation...")
        engine = get_engine()
        processor = BatchAnalyticsProcessor(engine, verbose=True)
        
        # Run full processing
        processor.process_all_analytics(legislatura_id=legislatura_id)
        
        print("Full analytics calculation completed!")
        return True
        
    except Exception as e:
        print(f"Full analytics calculation failed: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Simple Analytics Runner for Portuguese Parliament',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--full', '-f',
        action='store_true',
        help='Run full analytics calculation (slower but comprehensive)'
    )
    
    parser.add_argument(
        '--legislature', '-l',
        type=int,
        help='Specific legislature ID to process'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test database connection and analytics system availability'
    )
    
    args = parser.parse_args()
    
    start_time = datetime.now()
    print(f"Started at: {start_time}")
    print()
    
    try:
        # Test mode
        if args.test:
            engine = get_engine()
            updater = QuickAnalyticsUpdater(engine)
            
            print("Testing analytics system...")
            success = updater.test_analytics_system()
            
            if success:
                print("All tests passed! Analytics system is ready.")
                return
            else:
                print("Tests failed. Please check the system setup.")
                sys.exit(1)
        
        # Choose processing mode
        if args.full:
            success = run_full_analytics(args.legislature)
        else:
            success = run_quick_analytics(args.legislature)
        
        # Report results
        duration = datetime.now() - start_time
        print()
        print(f"Total duration: {duration}")
        
        if success:
            print("Analytics processing completed successfully!")
        else:
            print("Analytics processing failed!")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()