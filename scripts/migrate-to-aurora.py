#!/usr/bin/env python3
"""
Portuguese Parliament SQLite to Aurora Migration Script
=====================================================

This script migrates your 3GB SQLite database to Aurora Serverless v2 MySQL,
with comprehensive testing and rollback capabilities.

Usage:
    python migrate-to-aurora.py --environment prod --action migrate
    python migrate-to-aurora.py --environment test --action validate
    python migrate-to-aurora.py --environment test --action rollback
"""

import os
import sys
import sqlite3
import argparse
import logging
import json
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import boto3
import pymysql
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'aurora-migration-{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AuroraMigrator:
    """Handles SQLite to Aurora migration with testing and rollback capabilities"""
    
    def __init__(self, environment: str = "test"):
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.sqlite_path = self.project_root / "parlamento.db"
        
        # AWS clients
        self.rds_client = boto3.client('rds')
        self.secrets_client = boto3.client('secretsmanager')
        
        # Migration tracking
        self.migration_id = f"migration-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.backup_created = False
        
    def create_pre_migration_snapshot(self) -> str:
        """Create Aurora snapshot before migration"""
        cluster_id = f"parliament-{self.environment}-aurora"
        snapshot_id = f"{cluster_id}-pre-migration-{self.migration_id}"
        
        logger.info(f"Creating pre-migration snapshot: {snapshot_id}")
        
        try:
            response = self.rds_client.create_db_cluster_snapshot(
                DBClusterSnapshotIdentifier=snapshot_id,
                DBClusterIdentifier=cluster_id,
                Tags=[
                    {'Key': 'Purpose', 'Value': 'Pre-migration backup'},
                    {'Key': 'Environment', 'Value': self.environment},
                    {'Key': 'MigrationId', 'Value': self.migration_id}
                ]
            )
            
            # Wait for snapshot to complete
            logger.info("Waiting for snapshot to complete...")
            waiter = self.rds_client.get_waiter('db_cluster_snapshot_completed')
            waiter.wait(
                DBClusterSnapshotIdentifier=snapshot_id,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 40}  # 20 minutes max
            )
            
            logger.info(f"Snapshot created successfully: {snapshot_id}")
            self.backup_created = True
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            raise
    
    def get_aurora_connection_info(self) -> Dict[str, str]:
        """Get Aurora connection details from AWS"""
        cluster_id = f"parliament-{self.environment}-aurora"
        
        try:
            # Get cluster endpoint
            response = self.rds_client.describe_db_clusters(
                DBClusterIdentifier=cluster_id
            )
            cluster = response['DBClusters'][0]
            endpoint = cluster['Endpoint']
            
            # Get master user secret
            secret_arn = cluster['MasterUserSecret']['SecretArn']
            secret_response = self.secrets_client.get_secret_value(
                SecretId=secret_arn
            )
            secret_data = json.loads(secret_response['SecretString'])
            
            return {
                'host': endpoint,
                'port': 3306,
                'username': secret_data['username'],
                'password': secret_data['password'],
                'database': 'parliament'
            }
            
        except Exception as e:
            logger.error(f"Failed to get Aurora connection info: {e}")
            raise
    
    def test_aurora_connection(self) -> bool:
        """Test connection to Aurora cluster"""
        try:
            conn_info = self.get_aurora_connection_info()
            connection = pymysql.connect(
                host=conn_info['host'],
                port=conn_info['port'],
                user=conn_info['username'],
                password=conn_info['password'],
                database=conn_info['database'],
                connect_timeout=10
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                logger.info(f"Aurora connection successful. Version: {version}")
            
            connection.close()
            return True
            
        except Exception as e:
            logger.error(f"Aurora connection failed: {e}")
            return False
    
    def analyze_sqlite_schema(self) -> Dict[str, Any]:
        """Analyze SQLite database schema and data"""
        if not self.sqlite_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {self.sqlite_path}")
        
        logger.info("Analyzing SQLite database...")
        
        conn = sqlite3.connect(str(self.sqlite_path))
        conn.row_factory = sqlite3.Row
        
        analysis = {
            'tables': {},
            'total_rows': 0,
            'file_size_mb': self.sqlite_path.stat().st_size / (1024 * 1024),
            'schema_hash': None
        }
        
        # Get all tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        
        schema_content = ""
        
        for table_row in tables:
            table_name = table_row[0]
            
            # Get table schema
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            create_sql = cursor.fetchone()[0]
            schema_content += create_sql + "\\n"
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            analysis['tables'][table_name] = {
                'row_count': row_count,
                'columns': [{'name': col[1], 'type': col[2], 'not_null': col[3], 'pk': col[5]} for col in columns],
                'create_sql': create_sql
            }
            
            analysis['total_rows'] += row_count
        
        # Create schema hash for validation
        analysis['schema_hash'] = hashlib.md5(schema_content.encode()).hexdigest()
        
        conn.close()
        
        logger.info(f"SQLite Analysis Complete:")
        logger.info(f"  - Tables: {len(analysis['tables'])}")
        logger.info(f"  - Total rows: {analysis['total_rows']:,}")
        logger.info(f"  - File size: {analysis['file_size_mb']:.1f} MB")
        
        return analysis
    
    def convert_sqlite_to_mysql_schema(self, sqlite_analysis: Dict[str, Any]) -> str:
        """Convert SQLite schema to MySQL-compatible schema"""
        logger.info("Converting SQLite schema to MySQL...")
        
        mysql_schema = "-- MySQL Schema converted from SQLite\\n"
        mysql_schema += f"-- Generated: {datetime.now().isoformat()}\\n"
        mysql_schema += f"-- Migration ID: {self.migration_id}\\n\\n"
        
        # Type mapping
        type_mapping = {
            'INTEGER': 'BIGINT',
            'TEXT': 'TEXT',
            'REAL': 'DOUBLE',
            'BLOB': 'LONGBLOB',
            'NUMERIC': 'DECIMAL(20,10)',
            'VARCHAR': 'VARCHAR',
            'DATETIME': 'DATETIME',
            'DATE': 'DATE',
            'TIME': 'TIME'
        }
        
        for table_name, table_info in sqlite_analysis['tables'].items():
            mysql_schema += f"-- Table: {table_name}\\n"
            mysql_schema += f"DROP TABLE IF EXISTS `{table_name}`;\\n"
            mysql_schema += f"CREATE TABLE `{table_name}` (\\n"
            
            column_definitions = []
            primary_keys = []
            
            for col in table_info['columns']:
                col_name = col['name']
                col_type = col['type'].upper()
                
                # Map SQLite type to MySQL type
                mysql_type = type_mapping.get(col_type, 'TEXT')
                
                # Handle special cases
                if 'VARCHAR(' in col_type:
                    mysql_type = col_type
                elif col_type == 'INTEGER' and col['pk']:
                    mysql_type = 'BIGINT AUTO_INCREMENT'
                
                col_def = f"  `{col_name}` {mysql_type}"
                
                if col['not_null']:
                    col_def += " NOT NULL"
                
                column_definitions.append(col_def)
                
                if col['pk']:
                    primary_keys.append(f"`{col_name}`")
            
            mysql_schema += ",\\n".join(column_definitions)
            
            if primary_keys:
                mysql_schema += f",\\n  PRIMARY KEY ({', '.join(primary_keys)})"
            
            mysql_schema += "\\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\\n\\n"
        
        return mysql_schema
    
    def create_mysql_schema(self, schema_sql: str) -> bool:
        """Create MySQL schema in Aurora"""
        try:
            conn_info = self.get_aurora_connection_info()
            connection = pymysql.connect(
                host=conn_info['host'],
                port=conn_info['port'],
                user=conn_info['username'],
                password=conn_info['password'],
                database=conn_info['database']
            )
            
            logger.info("Creating MySQL schema in Aurora...")
            
            # Execute schema creation
            with connection.cursor() as cursor:
                # Split and execute each statement
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                
                for statement in tqdm(statements, desc="Creating tables"):
                    if statement:
                        cursor.execute(statement)
            
            connection.commit()
            connection.close()
            
            logger.info("MySQL schema created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create MySQL schema: {e}")
            return False
    
    def migrate_table_data(self, table_name: str, batch_size: int = 1000) -> bool:
        """Migrate data for a single table"""
        logger.info(f"Migrating table: {table_name}")
        
        try:
            # SQLite connection
            sqlite_conn = sqlite3.connect(str(self.sqlite_path))
            sqlite_conn.row_factory = sqlite3.Row
            
            # Aurora connection
            conn_info = self.get_aurora_connection_info()
            mysql_conn = pymysql.connect(
                host=conn_info['host'],
                port=conn_info['port'],
                user=conn_info['username'],
                password=conn_info['password'],
                database=conn_info['database']
            )
            
            # Get total row count
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = sqlite_cursor.fetchone()[0]
            
            if total_rows == 0:
                logger.info(f"Table {table_name} is empty, skipping")
                return True
            
            # Get column names
            sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in sqlite_cursor.fetchall()]
            
            # Prepare INSERT statement
            placeholders = ', '.join(['%s'] * len(columns))
            insert_sql = f"INSERT INTO `{table_name}` (`{'`, `'.join(columns)}`) VALUES ({placeholders})"
            
            # Migrate data in batches
            offset = 0
            mysql_cursor = mysql_conn.cursor()
            
            with tqdm(total=total_rows, desc=f"Migrating {table_name}") as pbar:
                while offset < total_rows:
                    # Fetch batch from SQLite
                    sqlite_cursor.execute(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
                    rows = sqlite_cursor.fetchall()
                    
                    if not rows:
                        break
                    
                    # Convert rows to tuples
                    batch_data = [tuple(row) for row in rows]
                    
                    # Insert batch into MySQL
                    mysql_cursor.executemany(insert_sql, batch_data)
                    mysql_conn.commit()
                    
                    offset += len(rows)
                    pbar.update(len(rows))
            
            sqlite_conn.close()
            mysql_conn.close()
            
            logger.info(f"Successfully migrated {total_rows:,} rows for table {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate table {table_name}: {e}")
            return False
    
    def validate_migration(self, sqlite_analysis: Dict[str, Any]) -> bool:
        """Validate that migration completed successfully"""
        logger.info("Validating migration...")
        
        try:
            conn_info = self.get_aurora_connection_info()
            connection = pymysql.connect(
                host=conn_info['host'],
                port=conn_info['port'],
                user=conn_info['username'],
                password=conn_info['password'],
                database=conn_info['database']
            )
            
            validation_passed = True
            
            with connection.cursor() as cursor:
                for table_name, table_info in sqlite_analysis['tables'].items():
                    # Check row count
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    mysql_count = cursor.fetchone()[0]
                    sqlite_count = table_info['row_count']
                    
                    if mysql_count != sqlite_count:
                        logger.error(f"Row count mismatch for {table_name}: SQLite={sqlite_count}, MySQL={mysql_count}")
                        validation_passed = False
                    else:
                        logger.info(f"✓ {table_name}: {mysql_count:,} rows")
            
            connection.close()
            
            if validation_passed:
                logger.info("🎉 Migration validation PASSED!")
            else:
                logger.error("❌ Migration validation FAILED!")
            
            return validation_passed
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    def rollback_from_snapshot(self, snapshot_id: str) -> bool:
        """Rollback Aurora cluster from snapshot"""
        logger.warning(f"Rolling back Aurora cluster from snapshot: {snapshot_id}")
        
        try:
            cluster_id = f"parliament-{self.environment}-aurora"
            temp_cluster_id = f"{cluster_id}-rollback-temp"
            
            # Create new cluster from snapshot
            logger.info("Creating new cluster from snapshot...")
            self.rds_client.restore_db_cluster_from_snapshot(
                DBClusterIdentifier=temp_cluster_id,
                SnapshotIdentifier=snapshot_id,
                Engine='aurora-mysql'
            )
            
            # Wait for cluster to be available
            logger.info("Waiting for rollback cluster to be ready...")
            waiter = self.rds_client.get_waiter('db_cluster_available')
            waiter.wait(DBClusterIdentifier=temp_cluster_id)
            
            logger.warning("Rollback cluster created. Manual intervention required to complete rollback.")
            logger.warning("Steps to complete rollback:")
            logger.warning(f"1. Update Lambda environment to point to: {temp_cluster_id}")
            logger.warning(f"2. Delete failed cluster: {cluster_id}")
            logger.warning(f"3. Rename {temp_cluster_id} to {cluster_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Migrate SQLite to Aurora Serverless v2')
    parser.add_argument('--environment', choices=['dev', 'test', 'prod'], default='test',
                       help='Environment to migrate')
    parser.add_argument('--action', choices=['analyze', 'migrate', 'validate', 'rollback'], 
                       required=True, help='Action to perform')
    parser.add_argument('--snapshot-id', help='Snapshot ID for rollback')
    parser.add_argument('--batch-size', type=int, default=1000, 
                       help='Batch size for data migration')
    
    args = parser.parse_args()
    
    migrator = AuroraMigrator(args.environment)
    
    try:
        if args.action == 'analyze':
            analysis = migrator.analyze_sqlite_schema()
            print(json.dumps(analysis, indent=2))
            
        elif args.action == 'migrate':
            # Full migration process
            logger.info("Starting full migration process...")
            
            # Step 1: Test Aurora connection
            if not migrator.test_aurora_connection():
                logger.error("Cannot connect to Aurora. Please check your infrastructure.")
                sys.exit(1)
            
            # Step 2: Create pre-migration snapshot
            snapshot_id = migrator.create_pre_migration_snapshot()
            
            # Step 3: Analyze SQLite
            analysis = migrator.analyze_sqlite_schema()
            
            # Step 4: Convert schema
            mysql_schema = migrator.convert_sqlite_to_mysql_schema(analysis)
            
            # Step 5: Create MySQL schema
            if not migrator.create_mysql_schema(mysql_schema):
                logger.error("Schema creation failed")
                sys.exit(1)
            
            # Step 6: Migrate data
            success = True
            for table_name in analysis['tables'].keys():
                if not migrator.migrate_table_data(table_name, args.batch_size):
                    success = False
                    break
            
            if not success:
                logger.error("Data migration failed. Consider rollback.")
                sys.exit(1)
            
            # Step 7: Validate migration
            if migrator.validate_migration(analysis):
                logger.info("🎉 Migration completed successfully!")
                logger.info(f"Snapshot for rollback: {snapshot_id}")
            else:
                logger.error("Migration validation failed")
                sys.exit(1)
                
        elif args.action == 'validate':
            analysis = migrator.analyze_sqlite_schema()
            migrator.validate_migration(analysis)
            
        elif args.action == 'rollback':
            if not args.snapshot_id:
                logger.error("--snapshot-id required for rollback")
                sys.exit(1)
            migrator.rollback_from_snapshot(args.snapshot_id)
    
    except KeyboardInterrupt:
        logger.warning("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()