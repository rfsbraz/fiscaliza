#!/usr/bin/env python3
"""
SQLite to MySQL SQL Dump Converter
==================================

Converts SQLite database to MySQL-compatible SQL dump for manual import.
Use this as an alternative to the direct migration script.
"""

import sqlite3
import sys
import argparse
from pathlib import Path
from datetime import datetime

def convert_sqlite_to_mysql_dump(sqlite_path: str, output_path: str):
    """Convert SQLite database to MySQL SQL dump"""
    
    if not Path(sqlite_path).exists():
        print(f"Error: SQLite database not found: {sqlite_path}")
        sys.exit(1)
    
    print(f"Converting {sqlite_path} to MySQL dump: {output_path}")
    
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"-- MySQL dump converted from SQLite\n")
        f.write(f"-- Generated at: {datetime.now().isoformat()}\n")
        f.write(f"-- Source: {sqlite_path}\n\n")
        f.write("SET FOREIGN_KEY_CHECKS=0;\n")
        f.write("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n\n")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(tables)} tables to convert")
        
        for table_name in tables:
            print(f"Processing table: {table_name}")
            
            # Get table schema
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            create_sql = cursor.fetchone()[0]
            
            # Convert schema to MySQL
            mysql_schema = convert_schema_to_mysql(create_sql, table_name)
            f.write(f"\n-- Table: {table_name}\n")
            f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")
            f.write(mysql_schema + "\n\n")
            
            # Export data
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            if rows:
                # Get column names
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                
                f.write(f"INSERT INTO `{table_name}` (`{'`, `'.join(columns)}`) VALUES\n")
                
                for i, row in enumerate(rows):
                    # Convert row values to MySQL format
                    values = []
                    for value in row:
                        if value is None:
                            values.append("NULL")
                        elif isinstance(value, str):
                            # Escape string values
                            escaped = value.replace("'", "''").replace("\\", "\\\\")
                            values.append(f"'{escaped}'")
                        else:
                            values.append(str(value))
                    
                    if i < len(rows) - 1:
                        f.write(f"({', '.join(values)}),\n")
                    else:
                        f.write(f"({', '.join(values)});\n")
                
                print(f"  Exported {len(rows):,} rows")
            else:
                print(f"  Table {table_name} is empty")
        
        f.write("\nSET FOREIGN_KEY_CHECKS=1;\n")
        f.write("-- End of dump\n")
    
    conn.close()
    print(f"Conversion complete: {output_path}")

def convert_schema_to_mysql(sqlite_sql: str, table_name: str) -> str:
    """Convert SQLite CREATE TABLE to MySQL format"""
    
    # Basic type conversions
    mysql_sql = sqlite_sql.replace("INTEGER", "BIGINT")
    mysql_sql = mysql_sql.replace("REAL", "DOUBLE")
    mysql_sql = mysql_sql.replace("BLOB", "LONGBLOB")
    mysql_sql = mysql_sql.replace("NUMERIC", "DECIMAL(20,10)")
    
    # Add MySQL-specific settings
    mysql_sql = mysql_sql.replace(f"CREATE TABLE {table_name}", f"CREATE TABLE `{table_name}`")
    mysql_sql += " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    
    return mysql_sql

def main():
    parser = argparse.ArgumentParser(description='Convert SQLite to MySQL dump')
    parser.add_argument('sqlite_path', help='Path to SQLite database')
    parser.add_argument('--output', '-o', default='mysql_dump.sql', help='Output SQL file')
    
    args = parser.parse_args()
    
    convert_sqlite_to_mysql_dump(args.sqlite_path, args.output)

if __name__ == "__main__":
    main()