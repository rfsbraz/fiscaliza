#!/usr/bin/env python3
"""
Investigation script for Portuguese Parliament deputy count discrepancy
Analyzes why ~3000 deputies are being counted instead of expected ~230
"""
import sqlite3
import os
from collections import defaultdict, Counter

def get_db_connection():
    """Get connection to the main parliament database"""
    db_path = os.path.join(os.path.dirname(__file__), 'parlamento.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return None
    return sqlite3.connect(db_path)

def analyze_deputados_table():
    """Analyze the deputados table structure and data"""
    print("="*60)
    print("1. ANALYZING DEPUTADOS TABLE")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Get total count of deputados
    cursor.execute("SELECT COUNT(*) FROM deputados")
    total_deputados = cursor.fetchone()[0]
    print(f"Total deputies in deputados table: {total_deputados}")
    
    # Get active vs inactive
    cursor.execute("SELECT ativo, COUNT(*) FROM deputados GROUP BY ativo")
    for row in cursor.fetchall():
        status = "Active" if row[0] else "Inactive"
        print(f"  {status}: {row[1]}")
    
    # Check for duplicates by name
    cursor.execute("""
        SELECT nome_completo, COUNT(*) as count 
        FROM deputados 
        GROUP BY nome_completo 
        HAVING COUNT(*) > 1 
        ORDER BY count DESC
        LIMIT 10
    """)
    
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"\nFound {len(duplicates)} deputies with duplicate names:")
        for name, count in duplicates:
            print(f"  {name}: {count} records")
    else:
        print("\nNo duplicate names found in deputados table")
    
    # Check for duplicates by id_cadastro
    cursor.execute("""
        SELECT id_cadastro, COUNT(*) as count 
        FROM deputados 
        WHERE id_cadastro IS NOT NULL
        GROUP BY id_cadastro 
        HAVING COUNT(*) > 1 
        ORDER BY count DESC
        LIMIT 10
    """)
    
    cadastro_duplicates = cursor.fetchall()
    if cadastro_duplicates:
        print(f"\nFound {len(cadastro_duplicates)} deputies with duplicate cadastro IDs:")
        for cadastro_id, count in cadastro_duplicates:
            print(f"  Cadastro ID {cadastro_id}: {count} records")
    else:
        print("\nNo duplicate cadastro IDs found")
    
    conn.close()

def analyze_mandatos_table():
    """Analyze the mandatos table and its relationship to deputados"""
    print("\n" + "="*60)
    print("2. ANALYZING MANDATOS TABLE")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Get total mandatos
    cursor.execute("SELECT COUNT(*) FROM mandatos")
    total_mandatos = cursor.fetchone()[0]
    print(f"Total mandatos: {total_mandatos}")
    
    # Get mandatos by legislatura
    cursor.execute("""
        SELECT l.numero, l.designacao, COUNT(m.id) as mandatos_count
        FROM legislaturas l
        LEFT JOIN mandatos m ON l.id = m.legislatura_id
        GROUP BY l.id, l.numero
        ORDER BY l.numero DESC
    """)
    
    print("\nMandatos by legislatura:")
    for numero, designacao, count in cursor.fetchall():
        print(f"  Legislatura {numero} ({designacao}): {count} mandatos")
    
    # Focus on legislatura 17
    cursor.execute("""
        SELECT COUNT(*) 
        FROM mandatos m 
        JOIN legislaturas l ON m.legislatura_id = l.id 
        WHERE l.numero = 17
    """)
    leg17_mandatos = cursor.fetchone()[0]
    print(f"\nLegislatura 17 specifically: {leg17_mandatos} mandatos")
    
    # Check if deputies have multiple mandatos in same legislatura
    cursor.execute("""
        SELECT m.deputado_id, d.nome_completo, COUNT(m.id) as mandatos_count
        FROM mandatos m
        JOIN deputados d ON m.deputado_id = d.id
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17
        GROUP BY m.deputado_id
        HAVING COUNT(m.id) > 1
        ORDER BY mandatos_count DESC
        LIMIT 10
    """)
    
    multiple_mandatos = cursor.fetchall()
    if multiple_mandatos:
        print(f"\nDeputies with multiple mandatos in Legislatura 17:")
        for dep_id, name, count in multiple_mandatos:
            print(f"  {name} (ID: {dep_id}): {count} mandatos")
        
        # Get details for first deputy with multiple mandatos
        first_deputy_id = multiple_mandatos[0][0]
        cursor.execute("""
            SELECT m.id, m.data_inicio, m.data_fim, m.ativo, p.sigla as partido, c.designacao as circulo
            FROM mandatos m
            JOIN legislaturas l ON m.legislatura_id = l.id
            JOIN partidos p ON m.partido_id = p.id
            JOIN circulos_eleitorais c ON m.circulo_id = c.id
            WHERE m.deputado_id = ? AND l.numero = 17
            ORDER BY m.data_inicio
        """, (first_deputy_id,))
        
        print(f"\n  Details for {multiple_mandatos[0][1]}:")
        for row in cursor.fetchall():
            mandato_id, inicio, fim, ativo, partido, circulo = row
            print(f"    Mandato {mandato_id}: {inicio} to {fim or 'ongoing'}, {partido}, {circulo}, Active: {ativo}")
    else:
        print("\nNo deputies have multiple mandatos in Legislatura 17")
    
    conn.close()

def analyze_unique_deputies_leg17():
    """Analyze unique deputies in legislatura 17"""
    print("\n" + "="*60)
    print("3. ANALYZING UNIQUE DEPUTIES IN LEGISLATURA 17")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Count unique deputies in legislatura 17
    cursor.execute("""
        SELECT COUNT(DISTINCT m.deputado_id)
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17
    """)
    unique_deputies = cursor.fetchone()[0]
    print(f"Unique deputies in Legislatura 17: {unique_deputies}")
    
    # Compare with total mandatos
    cursor.execute("""
        SELECT COUNT(m.id)
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17
    """)
    total_mandatos_17 = cursor.fetchone()[0]
    print(f"Total mandatos in Legislatura 17: {total_mandatos_17}")
    
    if unique_deputies != total_mandatos_17:
        print(f"DISCREPANCY: {total_mandatos_17 - unique_deputies} more mandatos than unique deputies")
    else:
        print("No discrepancy: Each deputy has exactly one mandato")
    
    conn.close()

def analyze_sample_deputies_leg17():
    """Get a sample of deputies from legislatura 17 to examine their structure"""
    print("\n" + "="*60)
    print("4. SAMPLE DEPUTIES FROM LEGISLATURA 17")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Get sample deputies with their mandato details
    cursor.execute("""
        SELECT d.id, d.id_cadastro, d.nome_completo, d.ativo as deputado_ativo,
               m.id as mandato_id, m.data_inicio, m.data_fim, m.ativo as mandato_ativo,
               p.sigla as partido, c.designacao as circulo
        FROM deputados d
        JOIN mandatos m ON d.id = m.deputado_id
        JOIN legislaturas l ON m.legislatura_id = l.id
        JOIN partidos p ON m.partido_id = p.id
        JOIN circulos_eleitorais c ON m.circulo_id = c.id
        WHERE l.numero = 17
        ORDER BY d.nome_completo
        LIMIT 10
    """)
    
    print("Sample of deputies in Legislatura 17:")
    print("ID | CadastroID | Name | Deputy Active | Mandato ID | Start | End | Mandato Active | Party | Circle")
    print("-" * 120)
    
    for row in cursor.fetchall():
        dep_id, cadastro_id, nome, dep_ativo, mandato_id, inicio, fim, mandato_ativo, partido, circulo = row
        fim_str = fim or "ongoing"
        print(f"{dep_id:3} | {cadastro_id:9} | {nome[:20]:20} | {dep_ativo:12} | {mandato_id:9} | {inicio:10} | {fim_str:8} | {mandato_ativo:13} | {partido:4} | {circulo[:15]}")
    
    conn.close()

def analyze_all_legislaturas_counts():
    """Analyze deputy counts across all legislaturas"""
    print("\n" + "="*60)
    print("5. DEPUTY COUNTS ACROSS ALL LEGISLATURAS")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Get counts for all legislaturas
    cursor.execute("""
        SELECT l.numero, l.designacao, 
               COUNT(DISTINCT m.deputado_id) as unique_deputies,
               COUNT(m.id) as total_mandatos
        FROM legislaturas l
        LEFT JOIN mandatos m ON l.id = m.legislatura_id
        GROUP BY l.id, l.numero
        ORDER BY l.numero DESC
    """)
    
    print("Legislatura | Designation | Unique Deputies | Total Mandatos | Difference")
    print("-" * 80)
    
    for numero, designacao, unique_deps, total_mandatos in cursor.fetchall():
        diff = total_mandatos - unique_deps if unique_deps and total_mandatos else 0
        designacao_short = designacao[:30] if designacao else "N/A"
        print(f"{numero:10} | {designacao_short:30} | {unique_deps:14} | {total_mandatos:13} | {diff:10}")
    
    conn.close()

def check_database_schema():
    """Check the database schema to understand relationships"""
    print("\n" + "="*60)
    print("6. DATABASE SCHEMA ANALYSIS")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Check deputados table schema
    cursor.execute("PRAGMA table_info(deputados)")
    print("Deputados table structure:")
    for row in cursor.fetchall():
        print(f"  {row[1]} {row[2]} {'NOT NULL' if row[3] else ''} {'PRIMARY KEY' if row[5] else ''}")
    
    # Check mandatos table schema
    cursor.execute("PRAGMA table_info(mandatos)")
    print("\nMandatos table structure:")
    for row in cursor.fetchall():
        print(f"  {row[1]} {row[2]} {'NOT NULL' if row[3] else ''} {'PRIMARY KEY' if row[5] else ''}")
    
    # Check for foreign key constraints
    cursor.execute("PRAGMA foreign_key_list(mandatos)")
    print("\nMandatos foreign keys:")
    for row in cursor.fetchall():
        print(f"  {row[3]} -> {row[2]}.{row[4]}")
    
    conn.close()

def investigate_source_data():
    """Check if there are multiple import sources causing duplicates"""
    print("\n" + "="*60)
    print("7. INVESTIGATING DATA SOURCES")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Check if there are different import sources or timestamps
    cursor.execute("""
        SELECT created_at, COUNT(*) as count
        FROM deputados
        GROUP BY DATE(created_at)
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    print("Deputy records by creation date:")
    for created_at, count in cursor.fetchall():
        print(f"  {created_at}: {count} records")
    
    # Check mandatos creation dates
    cursor.execute("""
        SELECT created_at, COUNT(*) as count
        FROM mandatos
        GROUP BY DATE(created_at)
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    print("\nMandato records by creation date:")
    for created_at, count in cursor.fetchall():
        print(f"  {created_at}: {count} records")
    
    conn.close()

def main():
    """Run all investigation functions"""
    print("Portuguese Parliament Deputy Count Investigation")
    print("=" * 60)
    
    analyze_deputados_table()
    analyze_mandatos_table()
    analyze_unique_deputies_leg17()
    analyze_sample_deputies_leg17()
    analyze_all_legislaturas_counts()
    check_database_schema()
    investigate_source_data()
    
    print("\n" + "="*60)
    print("INVESTIGATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()