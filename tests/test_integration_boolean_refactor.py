"""
Integration test for boolean value refactoring
==============================================

Tests that the PerguntasRequerimentosMapper correctly uses the refactored
_get_boolean_value method from the base mapper class.
"""

import unittest
import xml.etree.ElementTree as ET
from unittest.mock import Mock
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.data_processing.mappers.perguntas_requerimentos import PerguntasRequerimentosMapper


class TestBooleanRefactoringIntegration(unittest.TestCase):
    """Integration tests for boolean value refactoring"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock session
        self.mock_session = Mock()
        self.mapper = PerguntasRequerimentosMapper(self.mock_session)
    
    def test_mapper_inherits_boolean_method(self):
        """Test that mapper has access to _get_boolean_value method"""
        # The method should be available from the base class
        self.assertTrue(hasattr(self.mapper, '_get_boolean_value'))
        self.assertTrue(callable(getattr(self.mapper, '_get_boolean_value')))
    
    def test_boolean_method_works_in_mapper_context(self):
        """Test that the boolean method works correctly within mapper context"""
        # Create test XML
        root = ET.Element("destinatario")
        devolvido_elem = ET.SubElement(root, "devolvido")
        devolvido_elem.text = "true"
        
        prorrogado_elem = ET.SubElement(root, "prorrogado")
        prorrogado_elem.text = "false"
        
        reenviado_elem = ET.SubElement(root, "reenviado")
        reenviado_elem.text = "sim"
        
        retirado_elem = ET.SubElement(root, "retirado")
        retirado_elem.text = "não"
        
        # Test method calls in mapper context
        self.assertTrue(self.mapper._get_boolean_value(root, "devolvido"))
        self.assertFalse(self.mapper._get_boolean_value(root, "prorrogado"))
        self.assertTrue(self.mapper._get_boolean_value(root, "reenviado"))
        self.assertFalse(self.mapper._get_boolean_value(root, "retirado"))
    
    def test_method_handles_missing_elements(self):
        """Test that method handles missing XML elements properly"""
        root = ET.Element("destinatario")
        
        # Should return None for missing elements
        self.assertIsNone(self.mapper._get_boolean_value(root, "nonexistent"))
    
    def test_base_methods_still_available(self):
        """Test that other base methods are still available"""
        # Test that other base methods are still accessible
        self.assertTrue(hasattr(self.mapper, '_get_text_value'))
        self.assertTrue(hasattr(self.mapper, '_get_int_value'))
        self.assertTrue(callable(getattr(self.mapper, '_get_text_value')))
        self.assertTrue(callable(getattr(self.mapper, '_get_int_value')))
    
    def test_method_signature_compatibility(self):
        """Test that the refactored method has the expected signature"""
        import inspect
        
        # Get the method signature
        sig = inspect.signature(self.mapper._get_boolean_value)
        params = list(sig.parameters.keys())
        
        # Should have 'parent' and 'tag_name' parameters (self is not shown in bound methods)
        self.assertEqual(len(params), 2)  # parent, tag_name
        self.assertIn('parent', params)
        self.assertIn('tag_name', params)
        
        # Return annotation should indicate Optional[bool]
        return_annotation = sig.return_annotation
        # Check if it's Optional[bool] or similar
        self.assertIn('bool', str(return_annotation))


if __name__ == '__main__':
    unittest.main()