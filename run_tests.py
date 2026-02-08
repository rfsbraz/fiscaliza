#!/usr/bin/env python3
"""
Test Runner for Parliament Data Processing
=========================================

Simple test runner for the parliament data processing unit tests.
"""

import unittest
import sys
import os

# Add the project root to path
sys.path.append(os.path.dirname(__file__))

if __name__ == '__main__':
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)