"""
Unit tests for DataValidationUtils class
========================================

Tests for data validation and conversion utilities used across the parliament data import system.
"""

import unittest
from scripts.data_processing.mappers.common_utilities import DataValidationUtils


class TestDataValidationUtils(unittest.TestCase):
    """Test suite for DataValidationUtils functionality"""

    def test_safe_int_convert_integer_strings(self):
        """Test safe_int_convert with valid integer strings"""
        # Regular integer strings
        self.assertEqual(DataValidationUtils.safe_int_convert("123"), 123)
        self.assertEqual(DataValidationUtils.safe_int_convert("0"), 0)
        self.assertEqual(DataValidationUtils.safe_int_convert("999"), 999)
        
        # Integer strings with whitespace
        self.assertEqual(DataValidationUtils.safe_int_convert("  123  "), 123)
        self.assertEqual(DataValidationUtils.safe_int_convert("\t456\n"), 456)
        
        # Negative integers
        self.assertEqual(DataValidationUtils.safe_int_convert("-123"), -123)
        self.assertEqual(DataValidationUtils.safe_int_convert("  -456  "), -456)

    def test_safe_int_convert_float_strings(self):
        """Test safe_int_convert with float strings (the main bug fix)"""
        # The problematic case that caused the warning
        self.assertEqual(DataValidationUtils.safe_int_convert("211.0"), 211)
        
        # Other float cases that should convert to integers
        self.assertEqual(DataValidationUtils.safe_int_convert("123.0"), 123)
        self.assertEqual(DataValidationUtils.safe_int_convert("0.0"), 0)
        self.assertEqual(DataValidationUtils.safe_int_convert("-456.0"), -456)
        
        # Float strings with whitespace
        self.assertEqual(DataValidationUtils.safe_int_convert("  789.0  "), 789)
        self.assertEqual(DataValidationUtils.safe_int_convert("\t-123.0\n"), -123)
        
        # Float strings that truncate to integers
        self.assertEqual(DataValidationUtils.safe_int_convert("123.9"), 123)
        self.assertEqual(DataValidationUtils.safe_int_convert("456.1"), 456)
        self.assertEqual(DataValidationUtils.safe_int_convert("-789.7"), -789)

    def test_safe_int_convert_none_and_empty(self):
        """Test safe_int_convert with None and empty values"""
        self.assertIsNone(DataValidationUtils.safe_int_convert(None))
        self.assertIsNone(DataValidationUtils.safe_int_convert(""))
        self.assertIsNone(DataValidationUtils.safe_int_convert("   "))
        self.assertIsNone(DataValidationUtils.safe_int_convert("\t\n"))

    def test_safe_int_convert_invalid_values(self):
        """Test safe_int_convert with invalid values that should return None"""
        # Non-numeric strings
        self.assertIsNone(DataValidationUtils.safe_int_convert("abc"))
        self.assertIsNone(DataValidationUtils.safe_int_convert("123abc"))
        self.assertIsNone(DataValidationUtils.safe_int_convert("abc123"))
        
        # Mixed invalid formats
        self.assertIsNone(DataValidationUtils.safe_int_convert("12.34.56"))
        self.assertIsNone(DataValidationUtils.safe_int_convert("--123"))
        self.assertIsNone(DataValidationUtils.safe_int_convert("12-34"))
        
        # Special characters
        self.assertIsNone(DataValidationUtils.safe_int_convert("!@#$"))
        self.assertIsNone(DataValidationUtils.safe_int_convert("NaN"))
        self.assertIsNone(DataValidationUtils.safe_int_convert("Infinity"))

    def test_safe_int_convert_edge_cases(self):
        """Test safe_int_convert with edge cases"""
        # Large numbers
        self.assertEqual(DataValidationUtils.safe_int_convert("999999999"), 999999999)
        self.assertEqual(DataValidationUtils.safe_int_convert("999999999.0"), 999999999)
        
        # Scientific notation (should convert successfully)
        self.assertEqual(DataValidationUtils.safe_int_convert("1e5"), 100000)
        self.assertEqual(DataValidationUtils.safe_int_convert("2.5e3"), 2500)
        
        # Hexadecimal (should fail gracefully)
        self.assertIsNone(DataValidationUtils.safe_int_convert("0xFF"))
        self.assertIsNone(DataValidationUtils.safe_int_convert("0x123"))

    def test_safe_int_convert_real_world_scenarios(self):
        """Test safe_int_convert with real-world scenarios from parliament data"""
        # GP ID scenarios (the original problem)
        gp_ids = ["211.0", "45.0", "123.0", "1.0", "999.0"]
        expected = [211, 45, 123, 1, 999]
        
        for gp_id, expected_val in zip(gp_ids, expected):
            with self.subTest(gp_id=gp_id):
                self.assertEqual(DataValidationUtils.safe_int_convert(gp_id), expected_val)
        
        # Deputy ID scenarios
        deputy_ids = ["12345", "67890.0", "  111.0  ", "999"]
        expected_deputy = [12345, 67890, 111, 999]
        
        for dep_id, expected_val in zip(deputy_ids, expected_deputy):
            with self.subTest(deputy_id=dep_id):
                self.assertEqual(DataValidationUtils.safe_int_convert(dep_id), expected_val)
        
        # Commission ID scenarios
        commission_ids = ["1.0", "2.0", "10.0", "25.0"]
        expected_commission = [1, 2, 10, 25]
        
        for comm_id, expected_val in zip(commission_ids, expected_commission):
            with self.subTest(commission_id=comm_id):
                self.assertEqual(DataValidationUtils.safe_int_convert(comm_id), expected_val)

    def test_safe_int_convert_preserves_precision_loss_behavior(self):
        """Test that float truncation behavior is documented and consistent"""
        # Document that we truncate, not round
        self.assertEqual(DataValidationUtils.safe_int_convert("123.9"), 123)  # truncates, not rounds to 124
        self.assertEqual(DataValidationUtils.safe_int_convert("456.1"), 456)  # truncates
        self.assertEqual(DataValidationUtils.safe_int_convert("789.99"), 789)  # truncates
        
        # Negative truncation
        self.assertEqual(DataValidationUtils.safe_int_convert("-123.9"), -123)  # truncates toward zero
        self.assertEqual(DataValidationUtils.safe_int_convert("-456.1"), -456)  # truncates toward zero


if __name__ == '__main__':
    unittest.main()