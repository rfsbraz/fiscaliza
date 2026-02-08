#!/usr/bin/env python3
"""
Create the parliament database on MySQL server.
This script connects to MySQL server without specifying a database.
"""

import os
from sqlalchemy import create_engine, text
from database.connection import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD

def create_database():
    """Create the parliament database."""
    # Connect to MySQL server without specifying database
    server_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
    
    engine = create_engine(server_url)
    connection = engine.connect()

    try:
        connection.execute(text('CREATE DATABASE parliament CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
        print('Database "parliament" created successfully')
    except Exception as e:
        if "database exists" in str(e).lower():
            print('Database "parliament" already exists')
        else:
            print(f'Error creating database: {e}')
    finally:
        connection.close()

def drop_database():
    """Drop the parliament database."""
    # Connect to MySQL server without specifying database
    server_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
    
    engine = create_engine(server_url)
    connection = engine.connect()

    try:
        connection.execute(text('DROP DATABASE IF EXISTS parliament'))
        print('Database "parliament" dropped successfully')
    except Exception as e:
        print(f'Error dropping database: {e}')
    finally:
        connection.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        drop_database()
    else:
        create_database()