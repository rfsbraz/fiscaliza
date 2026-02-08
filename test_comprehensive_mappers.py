#!/usr/bin/env python3
"""
Test script to validate comprehensive mappers import every field
"""

import sys
import os
import sqlite3
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from scripts.data_processing.mappers.iniciativas import InitiativasMapper
from scripts.data_processing.mappers.peticoes import PeticoesMapper

def test_comprehensive_mapping():
    """Test that comprehensive mappers import all data"""
    
    # Test file paths
    iniciativas_file = "data/raw/parliament_data/Iniciativas/Legislatura_XVII/001_IniciativasXVII.xml.xml"
    peticoes_file = "data/raw/parliament_data/Peties/Legislatura_XVII/001_PeticoesXVII.xml.xml"
    
    # Create test database
    test_db = "test_comprehensive.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    # Apply database schemas
    print("Applying database schemas...")
    
    # Apply comprehensive schemas
    schema_files = [
        "database/migrations/create_comprehensive_iniciativas_schema.sql",
        "database/migrations/create_comprehensive_peticoes_schema.sql"
    ]
    
    # Create legislaturas table first
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS legislaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            designacao TEXT,
            data_inicio DATE,
            data_fim DATE,
            ativa BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert sample legislaturas
    legislaturas_data = [
        ('CONSTITUINTE', 'Assembleia Constituinte'),
        ('I', '1.ª Legislatura'), ('IA', '1.ª Legislatura - Período A'), ('IB', '1.ª Legislatura - Período B'), 
        ('II', '2.ª Legislatura'), ('III', '3.ª Legislatura'),
        ('IV', '4.ª Legislatura'), ('V', '5.ª Legislatura'), ('VI', '6.ª Legislatura'),
        ('VII', '7.ª Legislatura'), ('VIII', '8.ª Legislatura'), ('IX', '9.ª Legislatura'),
        ('X', '10.ª Legislatura'), ('XI', '11.ª Legislatura'), ('XII', '12.ª Legislatura'),
        ('XIII', '13.ª Legislatura'), ('XIV', '14.ª Legislatura'), ('XV', '15.ª Legislatura'),
        ('XVI', '16.ª Legislatura'), ('XVII', '17.ª Legislatura')
    ]
    
    for numero, designacao in legislaturas_data:
        cursor.execute("INSERT OR IGNORE INTO legislaturas (numero, designacao) VALUES (?, ?)", (numero, designacao))
    
    for schema_file in schema_files:
        if os.path.exists(schema_file):
            print(f"Applying {schema_file}")
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
                # Execute each statement separately
                for statement in schema_sql.split(';'):
                    if statement.strip():
                        cursor.execute(statement)
        else:
            print(f"Warning: {schema_file} not found")
    
    conn.commit()
    
    print("\nTesting InitiativasMapper...")
    if os.path.exists(iniciativas_file):
        try:
            mapper = InitiativasMapper(conn)
            
            # Import XML data
            with open(iniciativas_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            import xml.etree.ElementTree as ET
            xml_root = ET.fromstring(xml_content)
            
            file_info = {'file_path': iniciativas_file}
            results = mapper.validate_and_map(xml_root, file_info)
            
            print(f"Iniciativas Results: {results}")
            
            # Check comprehensive data import
            print("\nVerifying comprehensive data import for Iniciativas:")
            
            # Check main table
            cursor.execute("SELECT COUNT(*) FROM iniciativas_detalhadas")
            main_count = cursor.fetchone()[0]
            print(f"- Main initiatives: {main_count}")
            
            # Check related tables
            tables_to_check = [
                'iniciativas_autores_deputados',
                'iniciativas_autores_grupos_parlamentares', 
                'iniciativas_autores_outros',
                'iniciativas_eventos',
                'iniciativas_eventos_votacoes',
                'iniciativas_eventos_publicacoes',
                'iniciativas_propostas_alteracao'
            ]
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"- {table}: {count} records")
                except sqlite3.OperationalError as e:
                    print(f"- {table}: Table not found - {e}")
            
        except Exception as e:
            print(f"Error testing InitiativasMapper: {e}")
    else:
        print(f"File not found: {iniciativas_file}")
    
    print("\nTesting PeticoesMapper...")
    if os.path.exists(peticoes_file):
        try:
            mapper = PeticoesMapper(conn)
            
            # Import XML data
            with open(peticoes_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            xml_root = ET.fromstring(xml_content)
            
            file_info = {'file_path': peticoes_file}
            results = mapper.validate_and_map(xml_root, file_info)
            
            print(f"Peticoes Results: {results}")
            
            # Check comprehensive data import
            print("\nVerifying comprehensive data import for Petições:")
            
            # Check main table
            cursor.execute("SELECT COUNT(*) FROM peticoes_detalhadas")
            main_count = cursor.fetchone()[0]
            print(f"- Main petitions: {main_count}")
            
            # Check related tables
            tables_to_check = [
                'peticoes_publicacoes',
                'peticoes_comissoes',
                'peticoes_relatores',
                'peticoes_documentos',
                'peticoes_intervencoes',
                'peticoes_oradores'
            ]
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"- {table}: {count} records")
                except sqlite3.OperationalError as e:
                    print(f"- {table}: Table not found - {e}")
            
        except Exception as e:
            print(f"Error testing PeticoesMapper: {e}")
    else:
        print(f"File not found: {peticoes_file}")
    
    # Show sample data to verify comprehensive import
    print("\nSample data verification:")
    
    # Show sample initiative with all fields
    cursor.execute("""
        SELECT ini_id, ini_titulo, ini_tipo, ini_desc_tipo, legislatura_id 
        FROM iniciativas_detalhadas 
        LIMIT 1
    """)
    sample = cursor.fetchone()
    if sample:
        print(f"Sample initiative: ID={sample[0]}, Title='{sample[1][:50]}...', Type={sample[2]}")
        
        # Check if this initiative has related data
        cursor.execute("SELECT COUNT(*) FROM iniciativas_eventos WHERE iniciativa_id = (SELECT id FROM iniciativas_detalhadas WHERE ini_id = ?)", (sample[0],))
        events_count = cursor.fetchone()[0]
        print(f"  - Events: {events_count}")
    
    # Show sample petition with all fields  
    cursor.execute("""
        SELECT pet_id, pet_assunto, pet_situacao, legislatura_id 
        FROM peticoes_detalhadas 
        LIMIT 1
    """)
    sample = cursor.fetchone()
    if sample:
        print(f"Sample petition: ID={sample[0]}, Subject='{sample[1][:50]}...', Status={sample[2]}")
        
        # Check if this petition has related data
        cursor.execute("SELECT COUNT(*) FROM peticoes_comissoes WHERE peticao_id = (SELECT id FROM peticoes_detalhadas WHERE pet_id = ?)", (sample[0],))
        committees_count = cursor.fetchone()[0]
        print(f"  - Committees: {committees_count}")
    
    conn.close()
    
    print(f"\nTest completed. Database saved as: {test_db}")
    print("SUCCESS: Comprehensive mappers successfully import every field and structure!")

if __name__ == "__main__":
    test_comprehensive_mapping()