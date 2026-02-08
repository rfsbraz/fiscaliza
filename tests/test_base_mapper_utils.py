"""
Unit tests for base mapper utility methods
=========================================

Tests for common utility methods in the enhanced base mapper,
particularly focusing on the _safe_int method that handles
various input formats including problematic float strings.
"""

import unittest
from unittest.mock import Mock
import sys
import os

# Add the project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.data_processing.mappers.enhanced_base_mapper import XMLProcessingMixin


class TestBaseMappperUtils(unittest.TestCase):
    """Test base mapper utility methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mapper = XMLProcessingMixin()
    
    def test_safe_int_with_integers(self):
        """Test _safe_int with integer inputs"""
        # Test regular integers
        self.assertEqual(self.mapper._safe_int(123), 123)
        self.assertEqual(self.mapper._safe_int(0), 0)
        self.assertEqual(self.mapper._safe_int(-456), -456)
    
    def test_safe_int_with_floats(self):
        """Test _safe_int with float inputs"""
        # Test regular floats
        self.assertEqual(self.mapper._safe_int(123.0), 123)
        self.assertEqual(self.mapper._safe_int(7890.0), 7890)
        self.assertEqual(self.mapper._safe_int(-456.0), -456)
        
        # Test floats with decimals (should truncate)
        self.assertEqual(self.mapper._safe_int(123.7), 123)
        self.assertEqual(self.mapper._safe_int(999.99), 999)
    
    def test_safe_int_with_string_numbers(self):
        """Test _safe_int with string number inputs"""
        # Test regular integer strings
        self.assertEqual(self.mapper._safe_int("123"), 123)
        self.assertEqual(self.mapper._safe_int("0"), 0)
        self.assertEqual(self.mapper._safe_int("-456"), -456)
        
        # Test string integers with whitespace
        self.assertEqual(self.mapper._safe_int("  123  "), 123)
        self.assertEqual(self.mapper._safe_int("\t789\n"), 789)
    
    def test_safe_int_with_float_strings(self):
        """Test _safe_int with float string inputs (the problematic case)"""
        # Test float strings - the original problem case
        self.assertEqual(self.mapper._safe_int("7890.0"), 7890)
        self.assertEqual(self.mapper._safe_int("123.0"), 123)
        self.assertEqual(self.mapper._safe_int("0.0"), 0)
        self.assertEqual(self.mapper._safe_int("-456.0"), -456)
        
        # Test float strings with decimals (should truncate)
        self.assertEqual(self.mapper._safe_int("123.7"), 123)
        self.assertEqual(self.mapper._safe_int("999.99"), 999)
        
        # Test float strings with whitespace
        self.assertEqual(self.mapper._safe_int("  7890.0  "), 7890)
        self.assertEqual(self.mapper._safe_int("\t123.0\n"), 123)
    
    def test_safe_int_with_none_and_empty(self):
        """Test _safe_int with None and empty inputs"""
        # Test None
        self.assertIsNone(self.mapper._safe_int(None))
        
        # Test empty string
        self.assertIsNone(self.mapper._safe_int(""))
        
        # Test whitespace-only string
        self.assertIsNone(self.mapper._safe_int("   "))
        self.assertIsNone(self.mapper._safe_int("\t\n"))
    
    def test_safe_int_with_invalid_inputs(self):
        """Test _safe_int with invalid inputs"""
        # Test invalid string formats
        self.assertIsNone(self.mapper._safe_int("abc"))
        self.assertIsNone(self.mapper._safe_int("12.34.56"))
        self.assertIsNone(self.mapper._safe_int("not_a_number"))
        self.assertIsNone(self.mapper._safe_int("123abc"))
        
        # Test other invalid types
        self.assertIsNone(self.mapper._safe_int(["123"]))
        self.assertIsNone(self.mapper._safe_int({"value": 123}))
        self.assertIsNone(self.mapper._safe_int(object()))
    
    def test_safe_int_edge_cases(self):
        """Test _safe_int with edge cases"""
        # Test very large numbers
        large_num = "999999999999999"
        self.assertEqual(self.mapper._safe_int(large_num), 999999999999999)
        
        # Test scientific notation (should fail gracefully)
        self.assertIsNone(self.mapper._safe_int("1e5"))
        self.assertIsNone(self.mapper._safe_int("1.23e4"))
        
        # Test numbers with leading zeros
        self.assertEqual(self.mapper._safe_int("00123"), 123)
        self.assertEqual(self.mapper._safe_int("0007890.0"), 7890)


class TestBiographicalMapperIntegration(unittest.TestCase):
    """Integration tests for biographical mapper with fixed int conversion"""
    
    def test_problematic_case_from_error_log(self):
        """Test the specific case that caused the original error"""
        mapper = XMLProcessingMixin()
        
        # This was the exact value that caused the error:
        # "invalid literal for int() with base 10: '7890.0'"
        result = mapper._safe_int("7890.0")
        self.assertEqual(result, 7890)
        
        # Test similar problematic cases
        test_cases = [
            ("1234.0", 1234),
            ("567.0", 567), 
            ("0.0", 0),
            ("999.0", 999),
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = mapper._safe_int(input_val)
                self.assertEqual(result, expected)


if __name__ == '__main__':
    # Create test directory if it doesn't exist
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    unittest.main()