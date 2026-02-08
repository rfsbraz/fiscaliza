"""
Aurora Serverless v2 Database Connection Manager
==============================================

Handles connections to Aurora MySQL from Lambda functions with:
- AWS Secrets Manager integration
- Connection pooling for Lambda
- Automatic retry logic
- Health monitoring
"""

import os
import json
import logging
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager
import boto3
import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)


class AuroraConnectionManager:
    """Manages Aurora database connections for Lambda functions"""
    
    def __init__(self):
        self._connection = None
        self._connection_params = None
        self._secrets_client = boto3.client('secretsmanager')
        self._last_connection_time = 0
        self.connection_timeout = 300  # 5 minutes
        
    def _get_connection_params(self) -> Dict[str, Any]:
        """Get Aurora connection parameters from AWS Secrets Manager"""
        if self._connection_params:
            return self._connection_params
            
        secret_arn = os.environ.get('DATABASE_HOST_SECRET_ARN')
        if not secret_arn:
            raise ValueError("DATABASE_HOST_SECRET_ARN environment variable not set")
        
        try:
            logger.info("Retrieving Aurora credentials from Secrets Manager")
            response = self._secrets_client.get_secret_value(SecretId=secret_arn)
            secret_data = json.loads(response['SecretString'])
            
            self._connection_params = {
                'host': secret_data['host'],
                'port': secret_data.get('port', 3306),
                'user': secret_data['username'],
                'password': secret_data['password'],
                'database': os.environ.get('DATABASE_NAME', 'parliament'),
                'charset': 'utf8mb4',
                'cursorclass': DictCursor,
                'autocommit': True,
                'connect_timeout': 10,
                'read_timeout': 30,
                'write_timeout': 30,
                # Connection pooling settings for Lambda
                'max_allowed_packet': 1024 * 1024 * 16,  # 16MB
            }
            
            logger.info(f"Aurora connection configured for host: {self._connection_params['host']}")
            return self._connection_params
            
        except Exception as e:
            logger.error(f"Failed to retrieve Aurora credentials: {e}")
            raise
    
    def _is_connection_valid(self) -> bool:
        """Check if current connection is still valid"""
        if not self._connection:
            return False
            
        # Check connection age
        if time.time() - self._last_connection_time > self.connection_timeout:
            logger.info("Connection expired, will reconnect")
            return False
            
        try:
            # Ping the connection
            self._connection.ping(reconnect=False)
            return True
        except Exception as e:
            logger.warning(f"Connection ping failed: {e}")
            return False
    
    def get_connection(self) -> pymysql.Connection:
        """Get a valid Aurora database connection"""
        if self._is_connection_valid():
            return self._connection
            
        # Close existing connection if any
        if self._connection:
            try:
                self._connection.close()
            except:
                pass
        
        # Create new connection
        params = self._get_connection_params()
        
        for attempt in range(3):
            try:
                logger.info(f"Connecting to Aurora (attempt {attempt + 1}/3)")
                self._connection = pymysql.connect(**params)
                self._last_connection_time = time.time()
                
                # Test the connection
                with self._connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                
                logger.info("Aurora connection established successfully")
                return self._connection
                
            except Exception as e:
                logger.error(f"Aurora connection attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # Last attempt
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursors"""
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            yield cursor
        except Exception as e:
            # Log the error but don't rollback (autocommit is on)
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params=None) -> list:
        """Execute a SELECT query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params=None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_cursor() as cursor:
            affected_rows = cursor.execute(query, params)
            return affected_rows
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on Aurora connection"""
        try:
            start_time = time.time()
            
            with self.get_cursor() as cursor:
                # Test basic connectivity
                cursor.execute("SELECT VERSION() as version, NOW() as current_time")
                result = cursor.fetchone()
                
                # Test database access
                cursor.execute("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = %s", 
                             (os.environ.get('DATABASE_NAME', 'parliament'),))
                table_info = cursor.fetchone()
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'mysql_version': result['version'],
                'server_time': result['current_time'].isoformat(),
                'database_tables': table_info['table_count'],
                'connection_age_seconds': int(time.time() - self._last_connection_time)
            }
            
        except Exception as e:
            logger.error(f"Aurora health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }
    
    def close(self):
        """Close the database connection"""
        if self._connection:
            try:
                self._connection.close()
                logger.info("Aurora connection closed")
            except:
                pass
            finally:
                self._connection = None


# Global connection manager instance (reused across Lambda invocations)
aurora_db = AuroraConnectionManager()


def get_database_connection():
    """Get the global Aurora database connection"""
    return aurora_db


# Compatibility function for existing SQLite code
def get_db_connection():
    """Legacy compatibility function - returns Aurora connection"""
    return aurora_db.get_connection()


# Context manager for transactions (if needed)
@contextmanager  
def database_transaction():
    """Context manager for explicit transactions"""
    connection = aurora_db.get_connection()
    
    # Disable autocommit for transaction
    connection.autocommit(False)
    
    try:
        yield connection
        connection.commit()
        logger.debug("Transaction committed")
    except Exception as e:
        connection.rollback() 
        logger.error(f"Transaction rolled back: {e}")
        raise
    finally:
        # Re-enable autocommit
        connection.autocommit(True)