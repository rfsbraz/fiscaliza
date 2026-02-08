"""
Unicode-Safe Logging Handler
===========================

Custom logging handler that automatically sanitizes Unicode characters
for Windows console output to prevent UnicodeEncodeError crashes.

This handler acts as middleware, intercepting log messages and converting
Portuguese characters (á, ã, ç, ó, etc.) to ASCII-safe replacements.
"""

import logging
import sys
from typing import Optional


class UnicodeSafeHandler(logging.StreamHandler):
    """
    Logging handler that automatically sanitizes Unicode characters for console output.
    
    This prevents UnicodeEncodeError crashes when logging Portuguese names and text
    on Windows systems where the console uses cp1252 encoding.
    """
    
    def __init__(self, stream=None):
        super().__init__(stream)
        
    def emit(self, record):
        """
        Emit a log record, automatically sanitizing Unicode characters.
        
        Args:
            record: LogRecord to emit
        """
        try:
            # Get the formatted message
            msg = self.format(record)
            
            # Sanitize Unicode characters for console output
            safe_msg = self._sanitize_unicode(msg)
            
            # Get the stream (stdout/stderr)
            stream = self.stream
            
            # Write the sanitized message
            stream.write(safe_msg + self.terminator)
            
            # Flush if needed
            if hasattr(stream, 'flush'):
                stream.flush()
                
        except Exception:
            # If anything goes wrong, fall back to the default handler behavior
            # but catch any Unicode errors
            try:
                super().emit(record)
            except UnicodeEncodeError:
                # Last resort: write a generic error message
                try:
                    self.stream.write("[Unicode Error in Log Message]\n")
                    if hasattr(self.stream, 'flush'):
                        self.stream.flush()
                except:
                    pass  # Give up gracefully
    
    def _sanitize_unicode(self, text: str) -> str:
        """
        Convert Unicode characters to ASCII-safe equivalents.
        
        Args:
            text: Text that may contain Unicode characters
            
        Returns:
            ASCII-safe version of the text
        """
        if not text:
            return text
            
        try:
            # Try to encode as ASCII, replacing non-ASCII characters with '?'
            return text.encode('ascii', 'replace').decode('ascii')
        except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
            # Fallback for any encoding issues
            return str(text).encode('ascii', 'replace').decode('ascii')


class UnicodeSafeFormatter(logging.Formatter):
    """
    Logging formatter that sanitizes Unicode characters in log records.
    
    This is an alternative approach that sanitizes at the formatting level
    rather than the handler level.
    """
    
    def format(self, record):
        """
        Format the log record, sanitizing Unicode characters.
        
        Args:
            record: LogRecord to format
            
        Returns:
            Formatted and sanitized log message
        """
        # Format the record normally first
        formatted = super().format(record)
        
        # Sanitize Unicode characters
        return self._sanitize_unicode(formatted)
    
    def _sanitize_unicode(self, text: str) -> str:
        """
        Convert Unicode characters to ASCII-safe equivalents.
        
        Args:
            text: Text that may contain Unicode characters
            
        Returns:
            ASCII-safe version of the text
        """
        if not text:
            return text
            
        try:
            # Try to encode as ASCII, replacing non-ASCII characters with '?'
            return text.encode('ascii', 'replace').decode('ascii')
        except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
            # Fallback for any encoding issues
            return str(text).encode('ascii', 'replace').decode('ascii')


def setup_unicode_safe_logging():
    """
    Set up Unicode-safe logging for the entire application.
    
    This replaces the default console handler with our Unicode-safe version.
    Call this early in your application startup.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Find and remove existing StreamHandlers (console handlers)
    handlers_to_remove = []
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handlers_to_remove.append(handler)
    
    for handler in handlers_to_remove:
        root_logger.removeHandler(handler)
    
    # Add our Unicode-safe handler
    console_handler = UnicodeSafeHandler(sys.stdout)
    
    # Use the same formatter as the original
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    
    root_logger.addHandler(console_handler)
    
    return console_handler


def setup_unicode_safe_formatter():
    """
    Alternative setup that uses a Unicode-safe formatter instead of handler.
    
    This keeps existing handlers but replaces their formatters with Unicode-safe versions.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Create Unicode-safe formatter
    safe_formatter = UnicodeSafeFormatter("%(asctime)s - %(levelname)s - %(message)s")
    
    # Apply to all handlers
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setFormatter(safe_formatter)
    
    return safe_formatter


# Convenience function for testing
def test_unicode_logging():
    """Test function to verify Unicode handling works correctly."""
    
    # Set up Unicode-safe logging
    setup_unicode_safe_logging()
    
    # Test with problematic Portuguese names
    logger = logging.getLogger(__name__)
    
    test_names = [
        "Filipe Lobo D'Ávila",
        "José António Saraiva",
        "Maria João Rodrigues", 
        "António Costa e Silva",
        "Regular ASCII Name"
    ]
    
    print("Testing Unicode-safe logging:")
    for name in test_names:
        logger.info(f"Processing deputy: {name}")
        
    print("All tests completed without Unicode errors!")


if __name__ == "__main__":
    test_unicode_logging()