"""
Unit tests for date parsing functionality
=========================================

Tests for date parsing utilities used across the parliament data import system.
"""

import unittest
from datetime import datetime
from scripts.data_processing.mappers.common_utilities import DataValidationUtils


class TestDateParsing(unittest.TestCase):
    """Test suite for date parsing functionality"""

    def test_parse_date_basic_formats(self):
        """Test parse_date with basic date formats"""
        test_cases = [
            # ISO format (YYYY-MM-DD)
            ("2023-12-25", datetime(2023, 12, 25)),
            ("2004-11-18", datetime(2004, 11, 18)),
            ("1999-01-01", datetime(1999, 1, 1)),
            
            # European format (DD-MM-YYYY)
            ("25-12-2023", datetime(2023, 12, 25)),
            ("18-11-2004", datetime(2004, 11, 18)),
            ("01-01-1999", datetime(1999, 1, 1)),
            
            # Slash formats
            ("2023/12/25", datetime(2023, 12, 25)),
            ("25/12/2023", datetime(2023, 12, 25)),
            ("18/11/2004", datetime(2004, 11, 18)),
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_string=date_str):
                result = DataValidationUtils.parse_date_flexible(date_str)
                self.assertEqual(result, expected)

    def test_parse_date_with_time(self):
        """Test parse_date with date and time formats"""
        test_cases = [
            # The problematic format that was failing
            ("18/11/2004 00:00:00", datetime(2004, 11, 18, 0, 0, 0)),
            ("25/12/2023 14:30:45", datetime(2023, 12, 25, 14, 30, 45)),
            ("01/01/2000 23:59:59", datetime(2000, 1, 1, 23, 59, 59)),
            
            # ISO with time
            ("2023-12-25T14:30:00", datetime(2023, 12, 25, 14, 30, 0)),
            ("2004-11-18T00:00:00", datetime(2004, 11, 18, 0, 0, 0)),
            
            # European with time
            ("25-12-2023 14:30:00", datetime(2023, 12, 25, 14, 30, 0)),
            ("18-11-2004 00:00:00", datetime(2004, 11, 18, 0, 0, 0)),
            
            # Year-first slash with time
            ("2004/11/18 00:00:00", datetime(2004, 11, 18, 0, 0, 0)),
            ("2023/12/25 14:30:00", datetime(2023, 12, 25, 14, 30, 0)),
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_string=date_str):
                result = DataValidationUtils.parse_date_flexible(date_str)
                self.assertEqual(result, expected)

    def test_parse_date_real_world_parliament_data(self):
        """Test parse_date with real-world formats from parliament XML files"""
        # These are actual date formats found in parliament data
        real_world_cases = [
            # The specific failing case from the log
            ("18/11/2004 00:00:00", datetime(2004, 11, 18, 0, 0, 0)),
            
            # Common parliament date formats
            ("01/01/2019 00:00:00", datetime(2019, 1, 1, 0, 0, 0)),
            ("31/12/2020 23:59:59", datetime(2020, 12, 31, 23, 59, 59)),
            ("15/06/2021 12:30:00", datetime(2021, 6, 15, 12, 30, 0)),
            
            # ISO formats from parliament data
            ("2019-01-01", datetime(2019, 1, 1)),
            ("2019-10-25", datetime(2019, 10, 25)),
            ("2020-12-31T23:59:59", datetime(2020, 12, 31, 23, 59, 59)),
            
            # European formats
            ("15-06-2021", datetime(2021, 6, 15)),
            ("01-01-2019 12:00:00", datetime(2019, 1, 1, 12, 0, 0)),
            
            # Mixed formats found in XIV_Legislatura XML
            ("23-10-2015", datetime(2015, 10, 23)),
            ("30-10-2017", datetime(2017, 10, 30)),
            ("2017-10-30", datetime(2017, 10, 30)),
            ("2013-10-23", datetime(2013, 10, 23)),
            ("2015-10-23", datetime(2015, 10, 23)),
            ("2019-10-24", datetime(2019, 10, 24)),
            
            # Partial date formats found in XML - now supported!
            ("2014-08", datetime(2014, 8, 1)),  # Year-month to first day of month
            ("2017-06", datetime(2017, 6, 1)),  # Year-month format
            ("2019-10", datetime(2019, 10, 1)), # Year-month format
            ("2008", datetime(2008, 1, 1)),     # Year-only to January 1st
            ("2009", datetime(2009, 1, 1)),     # Year-only format
            ("2011", datetime(2011, 1, 1)),     # Year-only format  
            ("2013", datetime(2013, 1, 1)),     # Year-only format
            ("2015", datetime(2015, 1, 1)),     # Year-only format
            ("2017", datetime(2017, 1, 1)),     # Year-only format
        ]
        
        for date_str, expected in real_world_cases:
            with self.subTest(date_string=date_str):
                result = DataValidationUtils.parse_date_flexible(date_str)
                if expected is None:
                    self.assertIsNone(result, f"Should have failed to parse: {date_str}")
                else:
                    self.assertIsNotNone(result, f"Failed to parse: {date_str}")
                    self.assertEqual(result, expected)

    def test_parse_date_invalid_formats(self):
        """Test parse_date with invalid date formats"""
        invalid_cases = [
            "",                    # Empty string
            None,                  # None value
            "invalid-date",        # Non-date string
            "32/13/2023",         # Invalid day/month
            "2023-13-01",         # Invalid month
            "31/02/2023",         # Invalid day for February
            "abc/def/ghij",       # Non-numeric
            "2023/12",            # Incomplete date
            "25-12",              # Incomplete date
            "2023-12-25 25:00:00", # Invalid hour
        ]
        
        for invalid_date in invalid_cases:
            with self.subTest(invalid_date=invalid_date):
                result = DataValidationUtils.parse_date_flexible(invalid_date)
                self.assertIsNone(result, f"Should have failed to parse: {invalid_date}")

    def test_parse_date_edge_cases(self):
        """Test parse_date with edge cases"""
        edge_cases = [
            # Leap year
            ("29/02/2020 00:00:00", datetime(2020, 2, 29, 0, 0, 0)),
            ("2020-02-29", datetime(2020, 2, 29)),
            
            # Year boundaries
            ("01/01/2000 00:00:00", datetime(2000, 1, 1, 0, 0, 0)),
            ("31/12/1999 23:59:59", datetime(1999, 12, 31, 23, 59, 59)),
            
            # Single digit day/month
            ("01/01/2023", datetime(2023, 1, 1)),
            ("1/1/2023", datetime(2023, 1, 1)),  # This format IS supported by strptime
            
            # With whitespace (should be handled by strip())
            ("  18/11/2004 00:00:00  ", datetime(2004, 11, 18, 0, 0, 0)),
            ("\t25/12/2023 14:30:00\n", datetime(2023, 12, 25, 14, 30, 0)),
        ]
        
        for date_str, expected in edge_cases:
            with self.subTest(date_string=date_str):
                result = DataValidationUtils.parse_date_flexible(date_str)
                if expected is None:
                    self.assertIsNone(result)
                else:
                    self.assertEqual(result, expected)

    def test_parse_date_format_precedence(self):
        """Test that date parsing handles format precedence correctly"""
        # Some dates could be ambiguous (01/02/2023 could be Jan 2 or Feb 1)
        # Test that our format ordering gives predictable results
        ambiguous_cases = [
            # This should be parsed as DD/MM/YYYY (European format comes first)
            ("01/02/2023", datetime(2023, 2, 1)),  # 1st February, not 2nd January
            ("12/01/2023", datetime(2023, 1, 12)), # 12th January
            
            # These are unambiguous
            ("25/12/2023", datetime(2023, 12, 25)), # Can only be 25th December
            ("13/01/2023", datetime(2023, 1, 13)),  # Can only be 13th January
        ]
        
        for date_str, expected in ambiguous_cases:
            with self.subTest(date_string=date_str):
                result = DataValidationUtils.parse_date_flexible(date_str)
                self.assertEqual(result, expected)

    def test_parse_date_warning_prevention(self):
        """Test that the problematic date format no longer generates warnings"""
        # The specific format that was causing warnings
        problematic_dates = [
            "18/11/2004 00:00:00",
            "01/01/2019 00:00:00", 
            "31/12/2020 23:59:59",
            "15/06/2021 12:30:00",
        ]
        
        for date_str in problematic_dates:
            with self.subTest(date_string=date_str):
                result = DataValidationUtils.parse_date_flexible(date_str)
                # Should successfully parse without warnings
                self.assertIsNotNone(result)
                self.assertIsInstance(result, datetime)

    def test_parse_date_year_and_partial_formats(self):
        """Test parsing of year-only and year-month formats from XML data"""
        partial_format_cases = [
            # Year-only formats (common in registo de interesses)
            ("2007", datetime(2007, 1, 1)),
            ("2008", datetime(2008, 1, 1)), 
            ("2009", datetime(2009, 1, 1)),
            ("2010", datetime(2010, 1, 1)),
            ("2011", datetime(2011, 1, 1)),
            ("2012", datetime(2012, 1, 1)),
            ("2013", datetime(2013, 1, 1)),
            ("2015", datetime(2015, 1, 1)),
            ("2017", datetime(2017, 1, 1)),
            
            # Year-month formats (appointment/activity start dates)
            ("2014-08", datetime(2014, 8, 1)),
            ("2017-06", datetime(2017, 6, 1)),
            ("2019-10", datetime(2019, 10, 1)),
            ("2015-07", datetime(2015, 7, 1)),
            ("2011-09", datetime(2011, 9, 1)),
            ("2018-03", datetime(2018, 3, 1)),
            ("2018-11", datetime(2018, 11, 1)),
            
            # Edge cases
            ("2020", datetime(2020, 1, 1)),    # Recent year
            ("1985", datetime(1985, 1, 1)),    # Old year 
            ("2020-01", datetime(2020, 1, 1)), # January
            ("2020-12", datetime(2020, 12, 1)), # December
        ]
        
        for date_str, expected in partial_format_cases:
            with self.subTest(date_string=date_str):
                result = DataValidationUtils.parse_date_flexible(date_str)
                self.assertIsNotNone(result, f"Failed to parse partial date: {date_str}")
                self.assertEqual(result, expected)

    def test_parse_date_performance(self):
        """Test that date parsing is reasonably fast for bulk operations"""
        import time
        
        # Test with a variety of date formats including new partial formats
        test_dates = [
            "18/11/2004 00:00:00",
            "2023-12-25",
            "25-12-2023",
            "2023/12/25",
            "25/12/2023 14:30:00",
            "2023-12-25T14:30:00",
            "2008",           # Year-only
            "2014-08",        # Year-month
        ] * 100  # 800 dates total
        
        start_time = time.time()
        successful_parses = 0
        
        for date_str in test_dates:
            result = DataValidationUtils.parse_date_flexible(date_str)
            if result is not None:
                successful_parses += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should parse all valid dates successfully
        self.assertEqual(successful_parses, 800)
        
        # Should complete reasonably quickly (less than 1 second for 800 dates)
        self.assertLess(duration, 1.0, f"Date parsing took too long: {duration:.3f}s")


if __name__ == '__main__':
    unittest.main()