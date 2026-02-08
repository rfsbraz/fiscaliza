"""
Configuration settings for the Parliament Data Analysis application.
"""

import os
from database.connection import get_database_url

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database configuration
DATABASE_DIR = os.path.join(BASE_DIR, "database")

# Data paths
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "downloads")
CONFIG_DATA_DIR = os.path.join(DATA_DIR, "config")

# Log paths
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Flask configuration factory function to defer database URL resolution
def get_flask_config():
    """Get Flask configuration - no database connection during startup"""
    return {
        "SECRET_KEY": "asdf#FGSgvasgf$5$WGT",
        # Use SQLite as placeholder to prevent any AWS calls during startup
        "SQLALCHEMY_DATABASE_URI": "sqlite:///placeholder.db",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_pre_ping": True,
            "pool_recycle": -1,  # Disable connection recycling during startup
        },
        "PROPAGATE_EXCEPTIONS": True,
        "DEBUG": False,
        "TRAP_HTTP_EXCEPTIONS": True,
    }

# For backward compatibility, provide the config as a static dict
# but use lazy evaluation for database URL
class LazyFlaskConfig(dict):
    def __init__(self):
        super().__init__()
        self._config = None
    
    def __getitem__(self, key):
        if self._config is None:
            self._config = get_flask_config()
        return self._config[key]
    
    def update(self, other):
        if self._config is None:
            self._config = get_flask_config()
        self._config.update(other)
        super().update(self._config)
    
    def get(self, key, default=None):
        if self._config is None:
            self._config = get_flask_config()
        return self._config.get(key, default)

FLASK_CONFIG = LazyFlaskConfig()

# Parliament data paths
PARLIAMENT_DATA_DIR = os.path.join(BASE_DIR, 'scripts', 'data_processing', 'data', 'downloads')
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'scripts', 'data_processing', 'data', 'downloads')
