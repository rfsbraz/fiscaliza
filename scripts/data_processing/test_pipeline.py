#!/usr/bin/env python3
"""
Test script for the separated download/import pipeline system
============================================================

This script demonstrates the complete pipeline workflow:
1. Discovery service finds and catalogs files
2. Pipeline orchestrator shows the UI with pending files
3. Files are processed automatically with live logs

Usage:
    python test_pipeline.py --legislature XVII
"""

import argparse
import os
import sys
import time

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from database.connection import DatabaseSession
from database.models import ImportStatus
from scripts.data_processing.discovery_service import DiscoveryService
from scripts.data_processing.pipeline_orchestrator import PipelineOrchestrator


def cleanup_test_data():
    """Clean up any existing test data"""
    print("Cleaning up existing test data...")
    
    with DatabaseSession() as db_session:
        # Delete existing ImportStatus records for clean test
        deleted_count = db_session.query(ImportStatus).delete()
        db_session.commit()
        print(f"Deleted {deleted_count} existing ImportStatus records")


def run_discovery_demo(legislature: str = "XVII", limit_sections: int = 3):
    """Run discovery service to populate the database"""
    print(f"\n=== DISCOVERY PHASE ===")
    print(f"Discovering files for legislature {legislature}...")
    
    discovery_service = DiscoveryService(rate_limit_delay=0.8)  # Slower for demo
    
    # Get recursos links
    recursos_links = discovery_service._extract_recursos_links()
    if not recursos_links:
        print("ERROR: No recursos links found")
        return False
    
    print(f"Found {len(recursos_links)} sections, processing first {limit_sections} for demo...")
    
    with DatabaseSession() as db_session:
        discovered_count = 0
        
        # Process only first few sections for demo
        for i, link_info in enumerate(recursos_links[:limit_sections], 1):
            section_name = link_info['section_name']
            section_url = link_info['url']
            
            print(f"\n[{i}/{limit_sections}] Processing section: {section_name}")
            
            section_count = discovery_service._discover_section_files(
                db_session, section_url, section_name, legislature
            )
            discovered_count += section_count
            
            print(f"Section complete: {section_count} files discovered")
            time.sleep(0.5)  # Brief pause for readability
        
        db_session.commit()
        
    print(f"\nDiscovery complete: {discovered_count} files cataloged")
    return discovered_count > 0


def show_discovered_files():
    """Show what files were discovered"""
    print(f"\n=== DISCOVERED FILES ===")
    
    with DatabaseSession() as db_session:
        files = db_session.query(ImportStatus).filter(
            ImportStatus.status == 'discovered'
        ).all()
        
        if not files:
            print("No files discovered")
            return
        
        print(f"Found {len(files)} files ready for processing:")
        for i, file_record in enumerate(files[:10], 1):  # Show first 10
            print(f"{i:2d}. {file_record.file_name} ({file_record.category}) - {file_record.legislatura}")
        
        if len(files) > 10:
            print(f"... and {len(files) - 10} more files")


def run_pipeline_demo():
    """Run the pipeline orchestrator with UI"""
    print(f"\n=== PIPELINE ORCHESTRATION ===")
    print("Starting pipeline orchestrator with Rich UI...")
    print("The UI will show:")
    print("- Top Left: Pipeline statistics")
    print("- Bottom Left: Downloaded files with sizes")
    print("- Top Right: Pending files waiting for processing")  
    print("- Bottom Right: Live processing activity logs")
    print("\nPress Ctrl+C to stop gracefully\n")
    
    time.sleep(2)  # Give user time to read
    
    # Create orchestrator with moderate rate limits for demo
    orchestrator = PipelineOrchestrator(
        discovery_rate_limit=1.0,  # Slower discovery for demo visibility
        download_rate_limit=0.5    # Faster downloads for demo
    )
    
    try:
        # Run pipeline (will continue until Ctrl+C)
        orchestrator.start_pipeline()
    except KeyboardInterrupt:
        print("\nDemo completed!")
        orchestrator.stop_pipeline()


def main():
    """Main demo script"""
    parser = argparse.ArgumentParser(description="Test Parliament Data Pipeline")
    parser.add_argument('--legislature', type=str, default='XVII',
                       help='Legislature to discover (default: XVII)')
    parser.add_argument('--skip-discovery', action='store_true',
                       help='Skip discovery and use existing data')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up test data before starting')
    parser.add_argument('--limit-sections', type=int, default=3,
                       help='Limit number of sections to discover (default: 3)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("PARLIAMENT DATA PIPELINE - DEMONSTRATION")
    print("=" * 60)
    
    # Optional cleanup
    if args.cleanup:
        cleanup_test_data()
    
    # Discovery phase
    if not args.skip_discovery:
        success = run_discovery_demo(args.legislature, args.limit_sections)
        if not success:
            print("Discovery failed, exiting")
            return
    
    # Show discovered files
    show_discovered_files()
    
    # Pipeline phase
    input("\nPress Enter to start the pipeline orchestrator...")
    run_pipeline_demo()


if __name__ == "__main__":
    main()