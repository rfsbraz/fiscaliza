#\!/usr/bin/env python3
"""
Test Script for Database-Driven Parliamentary Analytics System
"""

import sys
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

class AnalyticsSystemTester:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.test_results = []
        
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_name}: {details}")
        self.test_results.append({'test': test_name, 'passed': passed, 'details': details})
        
    def test_stored_procedures_exist(self):
        print("\n=== Testing Stored Procedures ===")
        with self.engine.connect() as conn:
            procedures = ['CalculateActivityScore', 'PopulateInitialAnalytics']
            for proc in procedures:
                try:
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM information_schema.ROUTINES "
                        "WHERE ROUTINE_SCHEMA = DATABASE() AND ROUTINE_NAME = :proc_name"
                    ), {"proc_name": proc})
                    exists = result.scalar() > 0
                    self.log_test_result(f"Stored Procedure {proc} exists", exists, f"Found: {exists}")
                except Exception as e:
                    self.log_test_result(f"Stored Procedure {proc} check", False, f"Error: {str(e)}")
                    
    def test_analytics_tables_structure(self):
        print("
=== Testing Analytics Tables Structure ===")
        with self.engine.connect() as conn:
            try:
                deputy_count = conn.execute(text("SELECT COUNT(*) FROM deputy_analytics")).scalar()
                self.log_test_result("deputy_analytics table accessible", True, f"Found {deputy_count} records")
                
                if deputy_count > 0:
                    sample = conn.execute(text(
                        "SELECT activity_score, total_initiatives FROM deputy_analytics LIMIT 1"
                    )).first()
                    self.log_test_result("Required columns exist", sample is not None, 
                                       f"Sample: activity_score={sample[0]}, initiatives={sample[1]}")
            except Exception as e:
                self.log_test_result("Analytics table structure", False, f"Error: {str(e)}")
                
    def test_initial_data_population(self):
        print("
=== Testing Initial Data Population ===")
        with self.engine.connect() as conn:
            try:
                deputy_count = conn.execute(text("SELECT COUNT(*) FROM deputados")).scalar()
                analytics_count = conn.execute(text("SELECT COUNT(*) FROM deputy_analytics")).scalar()
                coverage = (analytics_count / deputy_count * 100) if deputy_count > 0 else 0
                self.log_test_result("Analytics coverage of deputies", coverage >= 50, 
                                   f"{analytics_count}/{deputy_count} deputies ({coverage:.1f}%)")
            except Exception as e:
                self.log_test_result("Initial data population", False, f"Error: {str(e)}")
                
    def run_all_tests(self):
        print("=" * 60)
        print("DATABASE-DRIVEN PARLIAMENTARY ANALYTICS SYSTEM TEST")
        print("=" * 60)
        print(f"Started at: {datetime.now()}")
        
        self.test_stored_procedures_exist()
        self.test_analytics_tables_structure()  
        self.test_initial_data_population()
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("
" + "=" * 60)
        print("TEST SUMMARY REPORT")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Overall System Status: {'OPERATIONAL' if success_rate >= 80 else 'NEEDS ATTENTION'}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_analytics_system.py <database_url>")
        sys.exit(1)
        
    database_url = sys.argv[1]
    tester = AnalyticsSystemTester(database_url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()
