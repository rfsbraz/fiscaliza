#!/usr/bin/env python3
"""
Main entry point for the Parliament Data Analysis application.
"""

import os
import sys

# Add the app directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, 'app')
sys.path.insert(0, app_dir)

from app.main import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)