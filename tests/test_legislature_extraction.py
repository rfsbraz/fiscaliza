"""
Unit tests for legislature extraction and conversion methods.

Tests the _extract_legislatura method and related functionality in enhanced_base_mapper.py
to ensure correct extraction from filenames, XML content, and directory paths.
"""

import unittest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.data_processing.mappers.enhanced_base_mapper import LegislatureHandlerMixin


class TestLegislatureExtraction(unittest.TestCase):
    """Test legislature extraction and conversion methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.handler = LegislatureHandlerMixin()
    
    def test_roman_to_number_mapping(self):
        """Test the ROMAN_TO_NUMBER mapping contains all expected values"""
        expected_mapping = {
            'CONSTITUINTE': 0, 'I': 1, 'IA': 1, 'IB': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
            'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11,
            'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17
        }
        self.assertEqual(self.handler.ROMAN_TO_NUMBER, expected_mapping)
    
    def test_number_to_roman_mapping(self):
        """Test the NUMBER_TO_ROMAN mapping is correctly derived"""
        expected_mapping = {
            0: 'CONSTITUINTE', 1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V',
            6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI',
            12: 'XII', 13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI', 17: 'XVII'
        }
        self.assertEqual(self.handler.NUMBER_TO_ROMAN, expected_mapping)
    
    def test_filename_extraction_roman_numerals(self):
        """Test extraction from filenames with roman numerals"""
        test_cases = [
            ('RegistoBiograficoI.xml', 'I'),
            ('RegistoBiograficoIA.xml', 'IA'),
            ('RegistoBiograficoIB.xml', 'IB'),
            ('RegistoBiograficoII.xml', 'II'),
            ('RegistoBiograficoIII.xml', 'III'),
            ('RegistoBiograficoIV.xml', 'IV'),
            ('RegistoBiograficoV.xml', 'V'),
            ('RegistoBiograficoVI.xml', 'VI'),
            ('RegistoBiograficoVII.xml', 'VII'),
            ('RegistoBiograficoVIII.xml', 'VIII'),
            ('RegistoBiograficoIX.xml', 'IX'),
            ('RegistoBiograficoX.xml', 'X'),
            ('RegistoBiograficoXI.xml', 'XI'),
            ('RegistoBiograficoXII.xml', 'XII'),
            ('RegistoBiograficoXIII.xml', 'XIII'),
            ('RegistoBiograficoXIV.xml', 'XIV'),
            ('RegistoBiograficoXV.xml', 'XV'),
            ('RegistoBiograficoXVI.xml', 'XVI'),
            ('RegistoBiograficoXVII.xml', 'XVII'),
            ('RegistoBiograficoCONSTITUINTE.xml', 'CONSTITUINTE'),
        ]
        
        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = self.handler._extract_legislatura(filename, None)
                self.assertEqual(result, expected)
    
    def test_filename_extraction_case_insensitive(self):
        """Test that filename extraction is case insensitive"""
        test_cases = [
            ('registobiograficoi.xml', 'I'),
            ('RegistoBiograficoii.xml', 'II'),
            ('REGISTOBIOGRAFICOIII.xml', 'III'),
            ('registobiograficoconstituinte.xml', 'CONSTITUINTE'),
        ]
        
        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = self.handler._extract_legislatura(filename, None)
                self.assertEqual(result, expected)
    
    def test_filename_extraction_edge_cases(self):
        """Test edge cases in filename extraction"""
        # Test that IX is matched correctly
        result = self.handler._extract_legislatura('FileIX.xml', None)
        self.assertEqual(result, 'IX')
        
        # Test that II is matched correctly  
        result = self.handler._extract_legislatura('FileII.xml', None)
        self.assertEqual(result, 'II')
        
        # Test that false matches like "ix" in "_suffix" are avoided
        from scripts.data_processing.mappers.enhanced_base_mapper import SchemaError
        with self.assertRaises(SchemaError):
            self.handler._extract_legislatura('FileI_suffix.xml', None)
    
    def test_directory_path_extraction(self):
        """Test extraction from directory paths"""
        test_cases = [
            ('/data/I_Legislatura/file.xml', 'I'),
            ('/data/IA_Legislatura/file.xml', 'IA'),
            ('/data/IB_Legislatura/file.xml', 'IB'),
            ('/data/II_Legislatura/file.xml', 'II'),
            ('C:\\data\\III_Legislatura\\file.xml', 'III'),
            ('/path/to/XVII_Legislatura/data.xml', 'XVII'),
            ('/some/path/CONSTITUINTE_Legislatura/file.xml', 'CONSTITUINTE'),
            # Test case insensitive
            ('/data/i_legislatura/file.xml', 'I'),
            ('/data/ia_legislatura/file.xml', 'IA'),
            ('/data/ib_legislatura/file.xml', 'IB'),
            ('/data/II_legislatura/file.xml', 'II'),
        ]
        
        for file_path, expected in test_cases:
            with self.subTest(file_path=file_path):
                result = self.handler._extract_legislatura(file_path, None)
                self.assertEqual(result, expected)
    
    def test_xml_content_extraction_numeric(self):
        """Test extraction from XML content with numeric values"""
        test_cases = [
            ('1', 'I'),
            ('2', 'II'),
            ('3', 'III'),
            ('9', 'IX'),
            ('10', 'X'),
            ('17', 'XVII'),
            ('0', 'CONSTITUINTE'),
        ]
        
        for xml_value, expected in test_cases:
            with self.subTest(xml_value=xml_value):
                # Create XML with Legislatura element
                xml_content = f'<root><Legislatura>{xml_value}</Legislatura></root>'
                xml_root = ET.fromstring(xml_content)
                
                result = self.handler._extract_legislatura('test.xml', xml_root)
                self.assertEqual(result, expected)
    
    def test_xml_content_extraction_roman(self):
        """Test extraction from XML content with roman numeral values"""
        test_cases = [
            ('I', 'I'),
            ('II', 'II'),
            ('XVII', 'XVII'),
            ('CONSTITUINTE', 'CONSTITUINTE'),
            # Test case insensitive
            ('i', 'I'),
            ('ii', 'II'),
            ('xvii', 'XVII'),
            # Test partial matches for CONSTITUINTE
            ('Cons', 'CONSTITUINTE'),
            ('CONS', 'CONSTITUINTE'),
            ('cons', 'CONSTITUINTE'),
        ]
        
        for xml_value, expected in test_cases:
            with self.subTest(xml_value=xml_value):
                xml_content = f'<root><Legislatura>{xml_value}</Legislatura></root>'
                xml_root = ET.fromstring(xml_content)
                
                result = self.handler._extract_legislatura('test.xml', xml_root)
                self.assertEqual(result, expected)
    
    def test_xml_content_different_patterns(self):
        """Test extraction from different XML element patterns"""
        xml_patterns = [
            'Legislatura',
            'LegDes',
            'IniLeg', 
            'leg',
            'Leg'
        ]
        
        for pattern in xml_patterns:
            with self.subTest(pattern=pattern):
                xml_content = f'<root><{pattern}>5</{pattern}></root>'
                xml_root = ET.fromstring(xml_content)
                
                result = self.handler._extract_legislatura('test.xml', xml_root)
                self.assertEqual(result, 'V')
    
    def test_xml_content_constituinte_partial_matches(self):
        """Test extraction with partial CONSTITUINTE matches from different XML patterns"""
        test_cases = [
            ('LegDes', 'Cons', 'CONSTITUINTE'),
            ('Legislatura', 'CONS', 'CONSTITUINTE'),
            ('IniLeg', 'cons', 'CONSTITUINTE'),
        ]
        
        for xml_pattern, xml_value, expected in test_cases:
            with self.subTest(xml_pattern=xml_pattern, xml_value=xml_value):
                xml_content = f'<root><{xml_pattern}>{xml_value}</{xml_pattern}></root>'
                xml_root = ET.fromstring(xml_content)
                
                result = self.handler._extract_legislatura('test.xml', xml_root)
                self.assertEqual(result, expected)
    
    def test_extraction_priority_order(self):
        """Test that extraction follows correct priority: filename > XML > directory"""
        # Filename should take priority over directory path
        file_path = '/data/II_Legislatura/RegistoBiograficoI.xml'
        result = self.handler._extract_legislatura(file_path, None)
        self.assertEqual(result, 'I')  # Should get I from filename, not II from directory
        
        # XML should take priority over directory path when filename has no match
        xml_content = '<root><Legislatura>3</Legislatura></root>'
        xml_root = ET.fromstring(xml_content)
        file_path = '/data/II_Legislatura/document.xml'
        result = self.handler._extract_legislatura(file_path, xml_root)
        self.assertEqual(result, 'III')  # Should get III from XML, not II from directory
    
    def test_extraction_fallback_chain(self):
        """Test the complete fallback chain when earlier methods fail"""
        # No filename match, no XML, should fall back to directory
        file_path = '/data/V_Legislatura/document.pdf'
        result = self.handler._extract_legislatura(file_path, None)
        self.assertEqual(result, 'V')
    
    def test_extraction_failure_cases(self):
        """Test cases where extraction should fail"""
        from scripts.data_processing.mappers.enhanced_base_mapper import SchemaError
        
        # No matches anywhere should raise SchemaError
        with self.assertRaises(SchemaError):
            self.handler._extract_legislatura('/some/random/path/file.txt', None)
        
        # Empty XML content should not match
        xml_content = '<root><Legislatura></Legislatura></root>'
        xml_root = ET.fromstring(xml_content)
        with self.assertRaises(SchemaError):
            self.handler._extract_legislatura('file.txt', xml_root)
    
    def test_xml_content_invalid_values(self):
        """Test XML content with invalid values falls back to other methods"""
        # Invalid numeric value should fall back
        xml_content = '<root><Legislatura>99</Legislatura></root>'
        xml_root = ET.fromstring(xml_content)
        file_path = '/data/II_Legislatura/file.xml'
        result = self.handler._extract_legislatura(file_path, xml_root)
        self.assertEqual(result, 'II')  # Should fall back to directory path
        
        # Invalid roman numeral should fall back
        xml_content = '<root><Legislatura>INVALID</Legislatura></root>'
        xml_root = ET.fromstring(xml_content)
        file_path = '/data/III_Legislatura/file.xml'
        result = self.handler._extract_legislatura(file_path, xml_root)
        self.assertEqual(result, 'III')  # Should fall back to directory path
    
    def test_complex_realistic_paths(self):
        """Test with realistic file paths from the parliament data"""
        test_cases = [
            ('E:\\parliament\\data\\I_Legislatura\\RegistoBiografico\\RegistoBiografico.xml', 'I'),
            ('C:\\Downloads\\XIV_Legislatura\\Atividades\\AtividadeDeputados.xml', 'XIV'),
            ('/var/data/parliament/XVII_Legislatura/Iniciativas/iniciativas.xml', 'XVII'),
            ('\\\\network\\share\\CONSTITUINTE_Legislatura\\dados\\file.xml', 'CONSTITUINTE'),
        ]
        
        for file_path, expected in test_cases:
            with self.subTest(file_path=file_path):
                result = self.handler._extract_legislatura(file_path, None)
                self.assertEqual(result, expected)
    
    def test_xml_whitespace_handling(self):
        """Test that XML content whitespace is properly handled"""
        # Test leading/trailing whitespace
        xml_content = '<root><Legislatura>  5  </Legislatura></root>'
        xml_root = ET.fromstring(xml_content)
        result = self.handler._extract_legislatura('test.xml', xml_root)
        self.assertEqual(result, 'V')
        
        # Test with newlines
        xml_content = '<root><Legislatura>\n17\n</Legislatura></root>'
        xml_root = ET.fromstring(xml_content)
        result = self.handler._extract_legislatura('test.xml', xml_root)
        self.assertEqual(result, 'XVII')
    
    def test_regex_word_boundaries(self):
        """Test that word boundaries work correctly to avoid partial matches"""
        from scripts.data_processing.mappers.enhanced_base_mapper import SchemaError
        
        # Should not match partial words
        with self.assertRaises(SchemaError):
            self.handler._extract_legislatura('SomeIXSuffix.xml', None)
        
        # Should match with proper delimiters
        result = self.handler._extract_legislatura('File_IX.xml', None)
        self.assertEqual(result, 'IX')


if __name__ == '__main__':
    unittest.main()