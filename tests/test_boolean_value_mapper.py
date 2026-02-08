"""
Unit tests for _get_boolean_value method in EnhancedSchemaMapper
==============================================================

Tests the boolean value extraction functionality that handles various 
boolean representations from XML elements, including Portuguese language support.
"""

import unittest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.data_processing.mappers.enhanced_base_mapper import XMLProcessingMixin


class TestBooleanValueMapper(unittest.TestCase):
    """Test cases for _get_boolean_value method"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a concrete implementation of the mixin for testing
        class TestMapper(XMLProcessingMixin):
            pass
        
        self.mapper = TestMapper()
    
    def _create_xml_element(self, tag_name: str, text_value: str) -> ET.Element:
        """Helper to create XML element with given tag and text"""
        root = ET.Element("root")
        child = ET.SubElement(root, tag_name)
        child.text = text_value
        return root
    
    def test_true_values_english(self):
        """Test English true value representations"""
        test_cases = [
            ("true", True),
            ("True", True), 
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("Yes", True),
            ("YES", True)
        ]
        
        for text_value, expected in test_cases:
            with self.subTest(text_value=text_value):
                parent = self._create_xml_element("test_field", text_value)
                result = self.mapper._get_boolean_value(parent, "test_field")
                self.assertEqual(result, expected, f"Failed for input: '{text_value}'")
    
    def test_true_values_portuguese(self):
        """Test Portuguese true value representations"""
        test_cases = [
            ("sim", True),
            ("Sim", True),
            ("SIM", True)
        ]
        
        for text_value, expected in test_cases:
            with self.subTest(text_value=text_value):
                parent = self._create_xml_element("test_field", text_value)
                result = self.mapper._get_boolean_value(parent, "test_field")
                self.assertEqual(result, expected, f"Failed for input: '{text_value}'")
    
    def test_false_values_english(self):
        """Test English false value representations"""
        test_cases = [
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("No", False),
            ("NO", False)
        ]
        
        for text_value, expected in test_cases:
            with self.subTest(text_value=text_value):
                parent = self._create_xml_element("test_field", text_value)
                result = self.mapper._get_boolean_value(parent, "test_field")
                self.assertEqual(result, expected, f"Failed for input: '{text_value}'")
    
    def test_false_values_portuguese(self):
        """Test Portuguese false value representations"""
        test_cases = [
            ("não", False),
            ("Não", False),
            ("NÃO", False),
            ("nao", False),  # Without accent
            ("Nao", False),
            ("NAO", False)
        ]
        
        for text_value, expected in test_cases:
            with self.subTest(text_value=text_value):
                parent = self._create_xml_element("test_field", text_value)
                result = self.mapper._get_boolean_value(parent, "test_field")
                self.assertEqual(result, expected, f"Failed for input: '{text_value}'")
    
    def test_whitespace_handling(self):
        """Test that whitespace is properly stripped"""
        test_cases = [
            ("  true  ", True),
            ("\ttrue\t", True),
            ("\nfalse\n", False),
            ("  sim  ", True),
            ("  não  ", False)
        ]
        
        for text_value, expected in test_cases:
            with self.subTest(text_value=repr(text_value)):
                parent = self._create_xml_element("test_field", text_value)
                result = self.mapper._get_boolean_value(parent, "test_field")
                self.assertEqual(result, expected, f"Failed for input: {repr(text_value)}")
    
    def test_none_values(self):
        """Test cases that should return None"""
        # Test with non-existent element
        root = ET.Element("root")
        result = self.mapper._get_boolean_value(root, "nonexistent")
        self.assertIsNone(result)
        
        # Test with empty element
        child = ET.SubElement(root, "empty_field")
        result = self.mapper._get_boolean_value(root, "empty_field")
        self.assertIsNone(result)
        
        # Test with None parent
        result = self.mapper._get_boolean_value(None, "test_field")
        self.assertIsNone(result)
    
    @patch('scripts.data_processing.mappers.enhanced_base_mapper.logger')
    def test_unrecognized_values_with_logging(self, mock_logger):
        """Test unrecognized values log warning and return None"""
        unrecognized_values = [
            "maybe",
            "perhaps", 
            "2",
            "true_but_not_really",
            "falso",  # Spanish, not Portuguese
            "vrai",   # French
            "random_text"
        ]
        
        for text_value in unrecognized_values:
            with self.subTest(text_value=text_value):
                parent = self._create_xml_element("test_field", text_value)
                result = self.mapper._get_boolean_value(parent, "test_field")
                
                # Should return None for unrecognized values
                self.assertIsNone(result, f"Should return None for: '{text_value}'")
                
                # Should log a warning
                mock_logger.warning.assert_called()
                warning_call = mock_logger.warning.call_args[0][0]
                self.assertIn(text_value, warning_call)
                self.assertIn("test_field", warning_call)
                mock_logger.reset_mock()
    
    def test_case_insensitive_processing(self):
        """Test that processing is case insensitive"""
        test_cases = [
            ("TrUe", True),
            ("fAlSe", False),
            ("YeS", True),
            ("nO", False),
            ("SiM", True),
            ("NãO", False)
        ]
        
        for text_value, expected in test_cases:
            with self.subTest(text_value=text_value):
                parent = self._create_xml_element("test_field", text_value)
                result = self.mapper._get_boolean_value(parent, "test_field")
                self.assertEqual(result, expected, f"Failed for mixed case: '{text_value}'")
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        # Empty string
        parent = self._create_xml_element("test_field", "")
        result = self.mapper._get_boolean_value(parent, "test_field")
        self.assertIsNone(result)
        
        # Only whitespace
        parent = self._create_xml_element("test_field", "   ")
        result = self.mapper._get_boolean_value(parent, "test_field")
        self.assertIsNone(result)
        
        # Numbers that shouldn't be recognized as boolean
        parent = self._create_xml_element("test_field", "2")
        result = self.mapper._get_boolean_value(parent, "test_field")
        self.assertIsNone(result)
        
        parent = self._create_xml_element("test_field", "-1")
        result = self.mapper._get_boolean_value(parent, "test_field")
        self.assertIsNone(result)

    def test_xml_structure_variations(self):
        """Test with different XML structures"""
        # Test with nested elements
        root = ET.Element("root")
        child = ET.SubElement(root, "parent")
        grandchild = ET.SubElement(child, "boolean_field")
        grandchild.text = "true"
        
        # Should find the element
        result = self.mapper._get_boolean_value(child, "boolean_field")
        self.assertTrue(result)
        
        # Should not find element in wrong parent
        result = self.mapper._get_boolean_value(root, "boolean_field")
        self.assertIsNone(result)
    
    def test_return_type_consistency(self):
        """Test that return types are consistent"""
        # True case
        parent = self._create_xml_element("test_field", "true")
        result = self.mapper._get_boolean_value(parent, "test_field")
        self.assertIs(type(result), bool)
        self.assertTrue(result)
        
        # False case  
        parent = self._create_xml_element("test_field", "false")
        result = self.mapper._get_boolean_value(parent, "test_field")
        self.assertIs(type(result), bool)
        self.assertFalse(result)
        
        # None case
        result = self.mapper._get_boolean_value(None, "test_field")
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()