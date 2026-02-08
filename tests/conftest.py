"""
Shared test fixtures for Fiscaliza test suite.
"""

import os
import sys
import pytest

# Ensure project root is in path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture
def app():
    """Create Flask test application."""
    from app.main import app as flask_app

    flask_app.config['TESTING'] = True
    flask_app.config['DEBUG'] = False

    yield flask_app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()
