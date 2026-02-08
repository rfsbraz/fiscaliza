#!/usr/bin/env python3
"""
Quick Analytics Update Script

This script provides fast analytics updates for specific deputies or small data changes.
Perfect for running after individual data imports or when only certain deputies need updates.

Usage:
    python quick_update_analytics.py --deputy 123                    # Update specific deputy
    python quick_update_analytics.py --legislature 15 --recent      # Update recent changes only
    python quick_update_analytics.py --legislature 15 --all         # Update all deputies in legislature
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
from typing import Optional, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.models import Deputado, IniciativaParlamentar, IniciativaAutorDeputado
from database.connection import get_engine


class QuickAnalyticsUpdater:
    """Fast analytics updater for targeted updates."""
    
    def __init__(self, engine):
        self.engine = engine
        self.Session = sessionmaker(bind=engine)
    
    def update_deputy_analytics(self, deputado_id: int, legislatura_id: Optional[int] = None) -> bool:
        """
        Update analytics for a specific deputy using pure Python calculations.
        
        Args:
            deputado_id: Deputy ID to update
            legislatura_id: Optional legislature ID (will be determined if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.Session() as session:
                # Get legislature ID if not provided
                if not legislatura_id:
                    deputy = session.query(Deputado).filter(Deputado.id == deputado_id).first()
                    if not deputy:
                        print(f"ERROR Deputy with ID {deputado_id} not found")
                        return False
                    legislatura_id = deputy.legislatura_id
                
                # Import the analytics calculator
                from scripts.analytics.calculate_analytics import AnalyticsCalculator
                
                # Create calculator and update this specific deputy
                calculator = AnalyticsCalculator(self.engine, verbose=False)
                
                # Get deputy data
                deputy_data = {
                    'id': deputado_id,
                    'nome': deputy.nome if 'deputy' in locals() else f'Deputy {deputado_id}',
                    'partido_id': getattr(deputy, 'partido_id', None) if 'deputy' in locals() else None,
                    'legislatura_id': legislatura_id
                }
                
                # Process analytics for this deputy
                calculator._calculate_deputy_analytics([deputy_data], legislatura_id, force_refresh=True)
                
                print(f"OK Updated analytics for deputy {deputado_id} in legislature {legislatura_id}")
                return True
                
        except Exception as e:
            print(f"ERROR Error updating deputy {deputado_id}: {e}")
            return False
    
    def update_recent_changes(self, legislatura_id: int, hours: int = 24) -> int:
        """
        Update analytics for deputies with recent activity changes.
        
        Args:
            legislatura_id: Legislature ID to check
            hours: Number of hours to look back for changes
            
        Returns:
            Number of deputies updated
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        updated_count = 0
        
        with self.Session() as session:
            # Find deputies with recent attendance changes
            recent_attendance = session.execute(text("""
                SELECT DISTINCT ma.dep_id
                FROM meeting_attendances ma
                JOIN deputados d ON ma.dep_id = d.id
                WHERE d.legislatura_id = :leg_id
                AND ma.dt_reuniao >= :cutoff
            """), {"leg_id": legislatura_id, "cutoff": cutoff_time}).fetchall()
            
            # Find deputies with recent initiative changes using SQLAlchemy ORM
            from sqlalchemy import func
            recent_initiatives = session.query(
                Deputado.id.label('dep_id')
            ).join(
                IniciativaAutorDeputado, Deputado.id_cadastro == IniciativaAutorDeputado.id_cadastro
            ).join(
                IniciativaParlamentar, IniciativaAutorDeputado.iniciativa_id == IniciativaParlamentar.id
            ).filter(
                IniciativaParlamentar.legislatura_id == legislatura_id,
                IniciativaParlamentar.data_inicio_leg >= cutoff_time
            ).distinct().all()
            
            # Find deputies with recent intervention changes
            recent_interventions = session.execute(text("""
                SELECT DISTINCT id.deputado_id as dep_id
                FROM intervencao_deputados id
                JOIN intervencoes i ON id.intervencao_id = i.id
                WHERE i.legislatura_id = :leg_id
                AND i.data >= :cutoff
            """), {"leg_id": legislatura_id, "cutoff": cutoff_time}).fetchall()
            
            # Combine all deputy IDs
            all_deputy_ids = set()
            for result_set in [recent_attendance, recent_initiatives, recent_interventions]:
                all_deputy_ids.update([row[0] for row in result_set])
            
            print(f"Found {len(all_deputy_ids)} deputies with recent changes in the last {hours} hours")
            
            # Update each deputy
            for deputy_id in all_deputy_ids:
                if self.update_deputy_analytics(deputy_id, legislatura_id):
                    updated_count += 1
        
        return updated_count
    
    def bulk_update_legislature(self, legislatura_id: int) -> int:
        """
        Update analytics for all deputies in a legislature using Python calculations.
        
        Args:
            legislatura_id: Legislature ID to update
            
        Returns:
            Number of deputies updated
        """
        try:
            # Import the analytics calculator
            from scripts.analytics.calculate_analytics import AnalyticsCalculator
            
            # Create calculator and process entire legislature
            calculator = AnalyticsCalculator(self.engine, verbose=True)
            
            print(f"Updating analytics for legislature {legislatura_id} using Python calculations...")
            
            # Process all analytics for this legislature
            calculator.calculate_all_analytics(legislatura_id=legislatura_id, force_refresh=True)
            
            # Count deputies processed
            with self.Session() as session:
                deputy_count = session.query(Deputado.id).filter(
                    Deputado.legislatura_id == legislatura_id
                ).count()
            
            print(f"Completed bulk update for {deputy_count} deputies in legislature {legislatura_id}")
            return deputy_count
            
        except Exception as e:
            print(f"ERROR Bulk update failed for legislature {legislatura_id}: {e}")
            return 0
    
    def test_analytics_system(self) -> bool:
        """Test if the Python analytics system is ready to work."""
        try:
            with self.Session() as session:
                # Check if analytics tables exist
                analytics_tables = [
                    'deputy_analytics', 'attendance_analytics', 'initiative_analytics',
                    'deputy_timeline', 'data_quality_metrics'
                ]
                
                for table in analytics_tables:
                    try:
                        session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    except Exception:
                        print(f"ERROR Analytics table '{table}' not found")
                        print("   Run the analytics migration first:")
                        print("   alembic upgrade head")
                        return False
                
                print("OK Python analytics system is ready")
                print("   - All analytics tables exist")
                print("   - No stored procedures required")
                print("   - Pure Python calculations")
                return True
                
        except Exception as e:
            print(f"ERROR Error testing analytics system: {e}")
            return False


def main():
    """Main entry point for quick analytics updates."""
    parser = argparse.ArgumentParser(
        description='Quick Analytics Update for Portuguese Parliament',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--deputy', '-d',
        type=int,
        help='Specific deputy ID to update'
    )
    
    parser.add_argument(
        '--legislature', '-l',
        type=int,
        help='Legislature ID to process'
    )
    
    parser.add_argument(
        '--recent', '-r',
        action='store_true',
        help='Update only deputies with recent changes (last 24 hours)'
    )
    
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Hours to look back for recent changes (default: 24)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Update all deputies in the specified legislature'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test if the analytics system is available'
    )
    
    args = parser.parse_args()
    
    if not any([args.deputy, args.legislature, args.test]):
        parser.error("Must specify --deputy, --legislature, or --test")
    
    try:
        # Get database connection
        engine = get_engine()
        
        # Create updater instance
        updater = QuickAnalyticsUpdater(engine)
        
        # Test mode
        if args.test:
            success = updater.test_analytics_system()
            sys.exit(0 if success else 1)
        
        # Single deputy update
        if args.deputy:
            success = updater.update_deputy_analytics(args.deputy, args.legislature)
            if success:
                print("✅ Deputy analytics update completed!")
            else:
                print("❌ Deputy analytics update failed!")
                sys.exit(1)
            return
        
        # Legislature-based updates
        if args.legislature:
            if args.recent:
                updated_count = updater.update_recent_changes(args.legislature, args.hours)
                print(f"✅ Updated analytics for {updated_count} deputies with recent changes")
            elif args.all:
                updated_count = updater.bulk_update_legislature(args.legislature)
                print(f"✅ Updated analytics for {updated_count} deputies in legislature {args.legislature}")
            else:
                print("❌ Must specify --recent or --all when using --legislature")
                sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error during quick analytics update: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()