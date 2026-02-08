from flask import Blueprint, jsonify
import os
import sys
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# Version info for deployment tracking
APP_VERSION = "1.2.0-port-fix"
BUILD_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database.connection import get_database_url, create_database_engine
from sqlalchemy import text

health_bp = Blueprint('health', __name__)

@health_bp.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint that doesn't touch the database"""
    return jsonify({
        'status': 'pong',
        'service': 'parliament-backend',
        'environment': os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'local'),
        'version': APP_VERSION,
        'build_time': BUILD_TIME
    }), 200

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Lambda and container orchestration"""
    try:
        logger.info("=== HEALTH CHECK DEBUG START ===")
        logger.info("About to create database engine...")
        # Check database connectivity using the proper database connection
        engine = create_database_engine()
        logger.info("Database engine created successfully")
        logger.info("About to connect to database...")
        with engine.connect() as conn:
            # Test query that works with both PostgreSQL and SQLite
            result = conn.execute(text("SELECT 1 as test")).fetchone()
            db_status = "healthy" if result[0] == 1 else "unhealthy"
            
        db_url = get_database_url()
        db_type = "postgresql" if db_url.startswith("postgresql://") else "sqlite"
        
    except Exception as e:
        db_status = f"error: {str(e)}"
        db_type = "unknown"
    
    return jsonify({
        'status': 'healthy',
        'service': 'parliament-backend',
        'database': db_status,
        'database_type': db_type,
        'environment': os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'local'),
        'version': APP_VERSION,
        'build_time': BUILD_TIME
    }), 200

@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check for Lambda/ECS"""
    try:
        # Check if database is accessible and has data
        engine = create_database_engine()
        with engine.connect() as conn:
            # Try to query for deputies/deputados table
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM deputado")).fetchone()
                count = result[0] if result else 0
            except:
                # Try alternative table name
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM deputados")).fetchone()
                    count = result[0] if result else 0
                except:
                    # Database exists but tables might not be created yet
                    return jsonify({
                        'status': 'not_ready',
                        'reason': 'database_tables_missing'
                    }), 503
        
        if count == 0:
            return jsonify({
                'status': 'ready',  # Ready but empty is still ready
                'reason': 'database_empty_but_accessible',
                'deputies_count': count
            }), 200
        
        return jsonify({
            'status': 'ready',
            'deputies_count': count
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'reason': str(e)
        }), 503