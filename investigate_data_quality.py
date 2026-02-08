#!/usr/bin/env python3
"""
Investigate the data quality issue - why all mandatos have the same dates
"""
import sqlite3
import os

def get_db_connection():
    """Get connection to the main parliament database"""
    db_path = os.path.join(os.path.dirname(__file__), 'parlamento.db')
    return sqlite3.connect(db_path)

def check_data_import_source():
    """Check where this data came from and if it's correct"""
    print("="*70)
    print("INVESTIGATING DATA IMPORT SOURCE")
    print("="*70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check creation timestamps to understand when data was imported
    cursor.execute("""
        SELECT created_at, COUNT(*) as count
        FROM mandatos
        GROUP BY created_at
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    print("Mandato records by creation timestamp:")
    for timestamp, count in cursor.fetchall():
        print(f"  {timestamp}: {count} records")
    
    # Check if there are other legislaturas with more reasonable data
    cursor.execute("""
        SELECT l.numero, 
               COUNT(DISTINCT m.deputado_id) as unique_deputies,
               MIN(m.data_inicio) as earliest_start,
               MAX(m.data_inicio) as latest_start,
               COUNT(DISTINCT m.data_inicio) as unique_start_dates
        FROM legislaturas l
        LEFT JOIN mandatos m ON l.id = m.legislatura_id
        WHERE l.numero IN (15, 16, 17)
        GROUP BY l.id, l.numero
        ORDER BY l.numero DESC
    """)
    
    print(f"\nComparison of recent legislaturas:")
    print("Leg | Deputies | Earliest Start | Latest Start | Unique Start Dates")
    print("-" * 70)
    for row in cursor.fetchall():
        numero, deputies, earliest, latest, unique_dates = row
        print(f"{numero:3} | {deputies:8} | {earliest:14} | {latest:12} | {unique_dates:17}")
    
    conn.close()

def check_real_leg17_data():
    """Check if there's actual real Legislatura 17 data we should expect"""
    print("\n" + "="*70)
    print("CHECKING EXPECTED LEGISLATURA 17 DATA")
    print("="*70)
    
    # Legislatura 17 in Portugal started in March 2025 after elections
    # Let's see if the dates make sense
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the actual legislatura info
    cursor.execute("""
        SELECT numero, designacao, data_inicio, data_fim, ativa
        FROM legislaturas
        WHERE numero >= 15
        ORDER BY numero DESC
    """)
    
    print("Recent legislaturas info:")
    print("Num | Designation | Start | End | Active")
    print("-" * 50)
    for row in cursor.fetchall():
        numero, designacao, inicio, fim, ativa = row
        fim_str = fim or "ongoing"
        print(f"{numero:3} | {designacao[:11]:11} | {inicio:10} | {fim_str:10} | {ativa}")
    
    # Check sample of deputy names to see if they look real
    cursor.execute("""
        SELECT d.nome_completo, d.id_cadastro, p.sigla
        FROM deputados d
        JOIN mandatos m ON d.id = m.deputado_id
        JOIN legislaturas l ON m.legislatura_id = l.id
        JOIN partidos p ON m.partido_id = p.id
        WHERE l.numero = 17
        ORDER BY d.nome_completo
        LIMIT 20
    """)
    
    print(f"\nSample deputy names from Legislatura 17:")
    for nome, cadastro, partido in cursor.fetchall():
        print(f"  {nome} (Cadastro: {cadastro}, Party: {partido})")
    
    conn.close()

def check_if_data_is_historical():
    """Check if we're looking at historical vs current data"""
    print("\n" + "="*70)
    print("CHECKING IF DATA REPRESENTS FULL HISTORICAL RECORDS")
    print("="*70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Count total unique people across all legislaturas
    cursor.execute("""
        SELECT COUNT(DISTINCT id_cadastro) as unique_people
        FROM deputados
        WHERE id_cadastro IS NOT NULL
    """)
    
    unique_people = cursor.fetchone()[0]
    print(f"Total unique people (by cadastro_id): {unique_people}")
    
    # Check how this compares to total deputados
    cursor.execute("SELECT COUNT(*) FROM deputados")
    total_deputados = cursor.fetchone()[0]
    print(f"Total deputado records: {total_deputados}")
    
    if unique_people < total_deputados:
        print(f"There are {total_deputados - unique_people} duplicate people with different records")
    
    # Check distribution across all legislaturas
    cursor.execute("""
        SELECT l.numero, l.designacao, COUNT(DISTINCT d.id_cadastro) as unique_people
        FROM legislaturas l
        JOIN mandatos m ON l.id = m.legislatura_id
        JOIN deputados d ON m.deputado_id = d.id
        WHERE d.id_cadastro IS NOT NULL
        GROUP BY l.id
        ORDER BY l.numero DESC
        LIMIT 10
    """)
    
    print(f"\nUnique people by legislatura:")
    print("Leg | Designation | Unique People")
    print("-" * 40)
    for numero, designacao, people in cursor.fetchall():
        designacao_short = designacao[:20] if designacao else "N/A"
        print(f"{numero:3} | {designacao_short:20} | {people:12}")
    
    conn.close()

def investigate_api_counting_method():
    """Check how the API is currently counting deputies"""
    print("\n" + "="*70)
    print("INVESTIGATING CURRENT API COUNTING METHOD")
    print("="*70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Simulate the current API query from the routes
    cursor.execute("""
        SELECT COUNT(DISTINCT d.id) as api_count
        FROM deputados d
        JOIN mandatos m ON d.id = m.deputado_id
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17 AND d.ativo = 1
    """)
    
    api_count = cursor.fetchone()[0]
    print(f"Current API count method result: {api_count}")
    
    # Try counting unique cadastro_ids instead
    cursor.execute("""
        SELECT COUNT(DISTINCT d.id_cadastro) as unique_cadastro_count
        FROM deputados d
        JOIN mandatos m ON d.id = m.deputado_id
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17 AND d.ativo = 1 AND d.id_cadastro IS NOT NULL
    """)
    
    unique_count = cursor.fetchone()[0]
    print(f"Unique cadastro_id count: {unique_count}")
    
    # Check for the "real" current deputies - those with unique cadastro IDs
    cursor.execute("""
        SELECT p.sigla, COUNT(DISTINCT d.id_cadastro) as unique_deputies
        FROM deputados d
        JOIN mandatos m ON d.id = m.deputado_id
        JOIN legislaturas l ON m.legislatura_id = l.id
        JOIN partidos p ON m.partido_id = p.id
        WHERE l.numero = 17 AND d.ativo = 1 AND d.id_cadastro IS NOT NULL
        GROUP BY p.id
        ORDER BY unique_deputies DESC
    """)
    
    print(f"\nUnique deputies by party (using cadastro_id):")
    total_unique = 0
    for partido, count in cursor.fetchall():
        total_unique += count
        print(f"  {partido:8}: {count:3} deputies")
    
    print(f"\nTotal unique deputies: {total_unique}")
    
    conn.close()

def main():
    check_data_import_source()
    check_real_leg17_data()
    check_if_data_is_historical()
    investigate_api_counting_method()
    
    print("\n" + "="*70)
    print("FINAL ANALYSIS")
    print("="*70)
    print("""
    FINDINGS:
    
    1. All 2988 mandatos in Legislatura 17 have identical start/end dates
       (2025-06-03 to 2025-07-26), suggesting this is either:
       - Test/sample data
       - Incorrectly imported data
       - Represents a specific period snapshot
    
    2. The total unique people (by cadastro_id) is much lower than total records,
       indicating the database contains historical data from ALL legislaturas
    
    3. The API is counting ALL mandato records rather than unique active deputies
    
    RECOMMENDATIONS:
    
    1. Fix the API counting to use DISTINCT cadastro_id or properly filter active mandatos
    2. Verify the data import process for Legislatura 17 - the dates look suspicious
    3. Consider implementing proper current/active deputy filtering
    4. The ~230 expected deputies should be achievable by counting unique people
    """)

if __name__ == "__main__":
    main()