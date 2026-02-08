"""
Common Utilities for Parliament Data Mappers
===========================================

Shared utility functions and constants used across all schema mappers.
Eliminates code duplication for common operations like date parsing,
string cleaning, and data validation.
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ParliamentConstants:
    """Constants used across parliament data processing"""
    
    # Legislature mappings
    ROMAN_TO_NUMBER = {
        'CONSTITUINTE': 0, 'I': 1, 'IA': 1, 'IB': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11,
        'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17
    }
    
    # Create NUMBER_TO_ROMAN mapping, preferring main periods over sub-periods  
    NUMBER_TO_ROMAN = {
        0: 'CONSTITUINTE', 1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V',
        6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI',
        12: 'XII', 13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI', 17: 'XVII'
    }
    
    # Common date formats found in Parliament XML files
    DATE_FORMATS = [
        "%Y-%m-%d",     # 2023-12-25
        "%d-%m-%Y",     # 25-12-2023
        "%Y/%m/%d",     # 2023/12/25
        "%d/%m/%Y",     # 25/12/2023
        "%Y-%m-%dT%H:%M:%S",  # 2023-12-25T14:30:00
        "%d-%m-%Y %H:%M:%S",  # 25-12-2023 14:30:00
        "%d/%m/%Y %H:%M:%S",  # 18/11/2004 00:00:00
        "%Y/%m/%d %H:%M:%S",  # 2004/11/18 00:00:00
        "%d/%m/%Y",     # Single digit support: 1/1/2023
        "%Y-%m",        # 2014-08 (year-month)
        "%Y",           # 2008 (year-only)
    ]
    
    # Common regex patterns
    LEGISLATURE_PATTERN = r'(XVII|XVI|XV|XIV|XIII|XII|XI|IX|VIII|VII|VI|IV|III|II|IB|IA|CONSTITUINTE|X|V|I)'
    CLEAN_TEXT_PATTERN = r'\s+'


class DataValidationUtils:
    """Utilities for data validation and cleaning"""
    
    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """Clean and normalize text data"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(ParliamentConstants.CLEAN_TEXT_PATTERN, ' ', text.strip())
        return cleaned
    
    @staticmethod
    def parse_date_flexible(date_str: Optional[str]) -> Optional[datetime]:
        """Parse date with flexible format detection"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        if not date_str:
            return None
        
        for date_format in ParliamentConstants.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, date_format)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    @staticmethod
    def safe_int_convert(value: Optional[str]) -> Optional[int]:
        """Safely convert string to integer, handling float strings like '211.0'"""
        if not value:
            return None
        
        try:
            # First try direct int conversion
            return int(value.strip())
        except ValueError:
            try:
                # If that fails, try float conversion then int (handles "211.0" -> 211)
                float_val = float(value.strip())
                # Check for infinity and NaN
                if float_val == float('inf') or float_val == float('-inf') or float_val != float_val:
                    return None
                return int(float_val)
            except (ValueError, AttributeError, OverflowError):
                return None
        except AttributeError:
            return None
    
    @staticmethod
    def safe_float_convert(value: Optional[str]) -> Optional[float]:
        """Safely convert string to float"""
        if not value:
            return None
        
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """Validate that required fields are present and non-empty"""
        missing_fields = []
        
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        return missing_fields


class LegislatureUtils:
    """Utilities for legislature handling"""
    
    @staticmethod
    def extract_from_filename(filename: str) -> Optional[str]:
        """Extract legislature from filename"""
        match = re.search(ParliamentConstants.LEGISLATURE_PATTERN, filename)
        return match.group(1) if match else None
    
    @staticmethod
    def convert_number_to_roman(number: int) -> str:
        """Convert numeric legislature to roman numeral"""
        return ParliamentConstants.NUMBER_TO_ROMAN.get(number, "XVII")
    
    @staticmethod
    def convert_roman_to_number(roman: str) -> int:
        """Convert roman numeral legislature to number"""
        return ParliamentConstants.ROMAN_TO_NUMBER.get(roman.upper(), 17)


class XMLPathUtils:
    """Utilities for XML path manipulation"""
    
    @staticmethod
    def normalize_xpath(xpath: str) -> str:
        """Normalize XPath for consistent field mapping"""
        # Remove namespace prefixes for consistency
        normalized = re.sub(r'\{[^}]*\}', '', xpath)
        return normalized
    
    @staticmethod
    def extract_field_paths(element, prefix: str = "") -> List[str]:
        """Extract all field paths from XML element"""
        paths = []
        current_path = f"{prefix}.{element.tag}" if prefix else element.tag
        paths.append(current_path)
        
        for child in element:
            paths.extend(XMLPathUtils.extract_field_paths(child, current_path))
        
        return paths


class ErrorHandlingUtils:
    """Utilities for consistent error handling"""
    
    @staticmethod
    def create_error_context(file_path: str, record_id: Optional[str] = None) -> str:
        """Create consistent error context string"""
        context = f"File: {file_path}"
        if record_id:
            context += f", Record ID: {record_id}"
        return context
    
    @staticmethod
    def log_processing_error(error: Exception, context: str) -> str:
        """Log processing error with consistent format"""
        error_msg = f"Processing error in {context}: {str(error)}"
        logger.error(error_msg)
        return error_msg
    
    @staticmethod
    def create_validation_error(missing_fields: List[str], context: str) -> str:
        """Create validation error message"""
        fields_str = ", ".join(missing_fields)
        error_msg = f"Missing required fields in {context}: {fields_str}"
        return error_msg


class PerformanceUtils:
    """Utilities for performance optimization"""
    
    @staticmethod
    def batch_process(items: List[Any], batch_size: int = 1000):
        """Generator for batch processing large datasets"""
        for i in range(0, len(items), batch_size):
            yield items[i:i + batch_size]
    
    @staticmethod
    def log_progress(current: int, total: int, step: int = 1000) -> None:
        """Log processing progress at intervals"""
        if current % step == 0:
            percentage = (current / total) * 100
            logger.info(f"Processing progress: {current}/{total} ({percentage:.1f}%)")
    
    @staticmethod
    def safe_text_for_logging(text: Optional[str]) -> str:
        """
        Convert text to ASCII-safe format for logging to avoid Unicode encoding errors.
        
        On Windows systems, the console often uses cp1252 encoding which can't handle
        Portuguese characters like ã, ç, ó, etc. This function converts such characters
        to replacement characters (usually ?) to prevent logging crashes.
        
        Args:
            text: The text that may contain Unicode characters
            
        Returns:
            ASCII-safe version of the text suitable for logging
        """
        if not text:
            return 'Unknown'
        
        try:
            # Try to encode as ASCII, replacing non-ASCII characters
            return text.encode('ascii', 'replace').decode('ascii')
        except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
            # Fallback for any encoding issues
            return 'Unknown'


# Convenience functions for backward compatibility
def clean_text(text: Optional[str]) -> str:
    """Backward compatibility wrapper"""
    return DataValidationUtils.clean_text(text)

def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Backward compatibility wrapper"""
    return DataValidationUtils.parse_date_flexible(date_str)

def safe_int(value: Optional[str]) -> Optional[int]:
    """Backward compatibility wrapper"""
    return DataValidationUtils.safe_int_convert(value)

def safe_log_text(text: Optional[str]) -> str:
    """Backward compatibility wrapper for Unicode-safe logging"""
    if not text:
        return 'Unknown'
    
    try:
        # Try to encode as ASCII, replacing non-ASCII characters
        return text.encode('ascii', 'replace').decode('ascii')
    except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
        # Fallback for any encoding issues
        return 'Unknown'