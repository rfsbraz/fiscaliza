"""
Integration test for GP ID conversion bug fix
===========================================

Tests specifically for the "Invalid GP ID format: 211.0" bug that was causing
GP records to be skipped during import.
"""

import unittest
from unittest.mock import Mock, patch
from scripts.data_processing.mappers.common_utilities import DataValidationUtils


class TestGPIDConversionBugFix(unittest.TestCase):
    """Test suite for the GP ID conversion bug fix"""

    def test_gp_id_format_211_0_bug_fix(self):
        """Test the specific GP ID format that was causing the warning"""
        # This was the exact value causing "Invalid GP ID format: 211.0"
        problematic_value = "211.0"
        result = DataValidationUtils.safe_int_convert(problematic_value)
        
        # Should convert successfully to integer 211
        self.assertEqual(result, 211)
        self.assertIsInstance(result, int)

    def test_various_gp_id_formats_from_xml(self):
        """Test various GP ID formats that might appear in XML data"""
        test_cases = [
            # (input_value, expected_output)
            ("211.0", 211),      # The original problematic case
            ("45.0", 45),        # Other float formats
            ("123.0", 123),
            ("1.0", 1),
            ("999.0", 999),
            ("0.0", 0),
            # Regular integer formats (should still work)
            ("211", 211),
            ("45", 45),
            ("123", 123),
            # With whitespace (real XML parsing scenarios)
            ("  211.0  ", 211),
            ("\t45.0\n", 45),
            ("   123   ", 123),
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input_value=input_val):
                result = DataValidationUtils.safe_int_convert(input_val)
                self.assertEqual(result, expected)
                self.assertIsInstance(result, int)

    def test_gp_record_creation_would_succeed(self):
        """Test that GP record creation logic would now succeed"""
        # Simulate the scenario in composicao_orgaos.py
        gp_data = {
            'gp_id': '211.0',
            'gp_sigla': 'PS',
            'gp_dt_inicio': '2023-01-01',
            'gp_dt_fim': None
        }
        
        # This is the exact conversion that was failing
        gp_id_int = DataValidationUtils.safe_int_convert(gp_data['gp_id'])
        
        # Verify the conversion succeeds
        self.assertIsNotNone(gp_id_int)
        self.assertEqual(gp_id_int, 211)
        
        # Verify the boolean check that determines if record is created
        # In the original code: if gp_id_int: (this would now be True)
        self.assertTrue(bool(gp_id_int))

    def test_edge_cases_that_should_still_fail(self):
        """Test that invalid formats still fail gracefully"""
        invalid_cases = [
            "abc.0",        # Non-numeric
            "211.0.0",      # Multiple decimals
            "211.abc",      # Non-numeric decimal part
            "",             # Empty string
            None,           # None value
            "NaN",          # Not a number
            "Infinity",     # Infinity
        ]
        
        for invalid_val in invalid_cases:
            with self.subTest(invalid_value=invalid_val):
                result = DataValidationUtils.safe_int_convert(invalid_val)
                self.assertIsNone(result)

    def test_warning_elimination(self):
        """Test that the warning should no longer be triggered"""
        # Simulate the exact scenario that was causing the warning
        test_gp_ids = ["211.0", "45.0", "123.0", "1.0", "999.0"]
        
        successful_conversions = 0
        failed_conversions = 0
        
        for gp_id in test_gp_ids:
            result = DataValidationUtils.safe_int_convert(gp_id)
            if result is not None:
                successful_conversions += 1
            else:
                failed_conversions += 1
        
        # All should succeed now
        self.assertEqual(successful_conversions, 5)
        self.assertEqual(failed_conversions, 0)

    def test_backward_compatibility(self):
        """Test that the fix doesn't break existing integer string handling"""
        # These should continue to work exactly as before
        integer_strings = ["1", "123", "999", "0", "-123", "  456  "]
        expected_values = [1, 123, 999, 0, -123, 456]
        
        for input_str, expected in zip(integer_strings, expected_values):
            with self.subTest(input_string=input_str):
                result = DataValidationUtils.safe_int_convert(input_str)
                self.assertEqual(result, expected)

    def test_data_loss_prevention(self):
        """Test that this fix prevents data loss in GP records"""
        # Before the fix: GP ID "211.0" -> None -> record skipped -> data loss
        # After the fix: GP ID "211.0" -> 211 -> record created -> no data loss
        
        problematic_gp_id = "211.0"
        converted_id = DataValidationUtils.safe_int_convert(problematic_gp_id)
        
        # This conversion should succeed, preventing data loss
        self.assertIsNotNone(converted_id)
        self.assertEqual(converted_id, 211)
        
        # Verify this would pass the validation check in the mapper
        # Original code: if gp_id_int: (create record) else: (log warning + skip)
        validation_passes = bool(converted_id)
        self.assertTrue(validation_passes, 
                       "GP record should be created, not skipped due to conversion failure")


if __name__ == '__main__':
    unittest.main()