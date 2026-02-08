"""
Specific tests for the legislature extraction bug where "I Legislature" was creating "II".

This test file documents and tests the specific bug fix where regex patterns
were incorrectly matching partial strings like "ix" in "_suffix" filenames.
"""

import unittest
import xml.etree.ElementTree as ET
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.data_processing.mappers.enhanced_base_mapper import LegislatureHandlerMixin, SchemaError


class TestLegislatureBugFix(unittest.TestCase):
    """Test specific bug fixes in legislature extraction"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.handler = LegislatureHandlerMixin()
    
    def test_suffix_false_match_prevention(self):
        """Test that 'ix' in '_suffix' doesn't incorrectly match as 'IX'"""
        # This was the original bug - "FileI_suffix.xml" was matching "IX" 
        # because the regex found "ix" from "I_suffix" and treated it as "IX"
        
        with self.assertRaises(SchemaError):
            # Should NOT match IX from the "ix" in "_suffix"
            self.handler._extract_legislatura('FileI_suffix.xml', None)
        
        with self.assertRaises(SchemaError):
            # Should NOT match IX from random text
            self.handler._extract_legislatura('SomeRandomIXText.xml', None)
    
    def test_valid_legislature_contexts(self):
        """Test that valid legislature contexts still work correctly"""
        # These should work correctly
        valid_cases = [
            ('RegistoBiograficoI.xml', 'I'),
            ('RegistoBiograficoII.xml', 'II'),
            ('RegistoBiograficoIX.xml', 'IX'),
            ('FileI.xml', 'I'),
            ('FileII.xml', 'II'), 
            ('FileIX.xml', 'IX'),
            ('File_I.xml', 'I'),
            ('File_IX.xml', 'IX'),
            ('I_Legislature.xml', 'I'),
            ('IX_Legislature.xml', 'IX'),
            ('DataI.xml', 'I'),
            ('DataIX.xml', 'IX'),
        ]
        
        for filename, expected in valid_cases:
            with self.subTest(filename=filename):
                result = self.handler._extract_legislatura(filename, None)
                self.assertEqual(result, expected, 
                               f"Failed for {filename}: expected {expected}, got {result}")
    
    def test_xml_numeric_conversion_accuracy(self):
        """Test that XML numeric values convert to correct roman numerals"""
        # This tests the specific conversion that could cause I->II confusion
        conversion_cases = [
            ('1', 'I'),   # Should be I, not II
            ('2', 'II'),  # Should be II
            ('9', 'IX'),  # Should be IX, not I
            ('10', 'X'),  # Should be X
        ]
        
        for xml_value, expected_roman in conversion_cases:
            with self.subTest(xml_value=xml_value):
                xml_content = f'<root><Legislatura>{xml_value}</Legislatura></root>'
                xml_root = ET.fromstring(xml_content)
                
                result = self.handler._extract_legislatura('test.xml', xml_root)
                self.assertEqual(result, expected_roman,
                               f"XML value '{xml_value}' should convert to '{expected_roman}', got '{result}'")
    
    def test_directory_path_precedence(self):
        """Test that directory paths work correctly without filename interference"""
        # Test that directory-based extraction works when filename has no match
        test_cases = [
            ('/data/I_Legislatura/document.pdf', 'I'),
            ('/data/II_Legislatura/data.txt', 'II'),
            ('C:\\projects\\IX_Legislatura\\file.doc', 'IX'),
        ]
        
        for file_path, expected in test_cases:
            with self.subTest(file_path=file_path):
                result = self.handler._extract_legislatura(file_path, None)
                self.assertEqual(result, expected)
    
    def test_realistic_parliament_filenames(self):
        """Test with realistic parliament data filenames"""
        # These are based on actual parliament data file patterns
        realistic_cases = [
            ('RegistoBiograficoI.xml', 'I'),
            ('RegistoBiograficoVII.xml', 'VII'),
            ('RegistoBiograficoXIII.xml', 'XIII'),
            ('AtividadeDeputadosXVI.xml', 'XVI'),
            ('IniciativasXVII.xml', 'XVII'),
            ('IntervencoesII.xml', 'II'),
        ]
        
        for filename, expected in realistic_cases:
            with self.subTest(filename=filename):
                result = self.handler._extract_legislatura(filename, None)
                self.assertEqual(result, expected)
    
    def test_edge_case_prevention(self):
        """Test prevention of edge cases that could cause false matches"""
        # These should all fail to match (raise SchemaError) rather than 
        # returning incorrect legislature identifications
        false_positive_cases = [
            'mixedIXcontent.xml',      # Should not match IX
            'prefixIVsuffix.xml',      # Should not match IV  
            'textVIIIother.xml',       # Should not match VIII
            'beforeXIafter.xml',       # Should not match XI
            'randomXVcontent.xml',     # Should not match XV
        ]
        
        for filename in false_positive_cases:
            with self.subTest(filename=filename):
                with self.assertRaises(SchemaError,
                                     msg=f"Filename '{filename}' should not match any legislature"):
                    self.handler._extract_legislatura(filename, None)


if __name__ == '__main__':
    unittest.main()