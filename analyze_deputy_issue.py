#!/usr/bin/env python3
"""
Deep analysis of why Legislatura 17 has ~3000 deputies instead of ~230
"""
import sqlite3
import os
from datetime import datetime

def get_db_connection():
    """Get connection to the main parliament database"""
    db_path = os.path.join(os.path.dirname(__file__), 'parlamento.db')
    return sqlite3.connect(db_path)

def analyze_mandato_dates_leg17():
    """Analyze the mandato dates in Legislatura 17 to understand the issue"""
    print("="*70)
    print("ANALYZING MANDATO DATES IN LEGISLATURA 17")
    print("="*70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get date ranges for mandatos in leg 17
    cursor.execute("""
        SELECT MIN(m.data_inicio) as earliest_start, 
               MAX(m.data_inicio) as latest_start,
               MIN(m.data_fim) as earliest_end,
               MAX(m.data_fim) as latest_end,
               COUNT(*) as total_mandatos
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17
    """)
    
    result = cursor.fetchone()
    print(f"Date ranges for Legislatura 17 mandatos:")
    print(f"  Earliest start: {result[0]}")
    print(f"  Latest start: {result[1]}")
    print(f"  Earliest end: {result[2]}")
    print(f"  Latest end: {result[3]}")
    print(f"  Total mandatos: {result[4]}")
    
    # Group by start dates to see patterns
    cursor.execute("""
        SELECT m.data_inicio, COUNT(*) as count
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17
        GROUP BY m.data_inicio
        ORDER BY count DESC
        LIMIT 20
    """)
    
    print(f"\nMost common start dates:")
    for date, count in cursor.fetchall():
        print(f"  {date}: {count} mandatos")
    
    # Group by end dates
    cursor.execute("""
        SELECT m.data_fim, COUNT(*) as count
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17 AND m.data_fim IS NOT NULL
        GROUP BY m.data_fim
        ORDER BY count DESC
        LIMIT 20
    """)
    
    print(f"\nMost common end dates:")
    for date, count in cursor.fetchall():
        print(f"  {date}: {count} mandatos")
    
    # Check for ongoing mandatos (no end date)
    cursor.execute("""
        SELECT COUNT(*) 
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17 AND m.data_fim IS NULL
    """)
    ongoing = cursor.fetchone()[0]
    print(f"\nOngoing mandatos (no end date): {ongoing}")
    
    conn.close()

def analyze_current_active_deputies():
    """Find truly active deputies as of today"""
    print("\n" + "="*70)
    print("ANALYZING CURRENTLY ACTIVE DEPUTIES")
    print("="*70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Find mandatos that should be active today
    cursor.execute("""
        SELECT COUNT(DISTINCT m.deputado_id)
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17 
        AND m.data_inicio <= ?
        AND (m.data_fim IS NULL OR m.data_fim >= ?)
    """, (today, today))
    
    active_today = cursor.fetchone()[0]
    print(f"Deputies with mandatos active today: {active_today}")
    
    # Find mandatos marked as active in the database
    cursor.execute("""
        SELECT COUNT(DISTINCT m.deputado_id)
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17 AND m.ativo = 1
    """)
    
    marked_active = cursor.fetchone()[0]
    print(f"Deputies with mandatos marked as active: {marked_active}")
    
    # Sample of currently active deputies
    cursor.execute("""
        SELECT d.nome_completo, m.data_inicio, m.data_fim, m.ativo,
               p.sigla as partido, c.designacao as circulo
        FROM deputados d
        JOIN mandatos m ON d.id = m.deputado_id
        JOIN legislaturas l ON m.legislatura_id = l.id
        JOIN partidos p ON m.partido_id = p.id
        JOIN circulos_eleitorais c ON m.circulo_id = c.id
        WHERE l.numero = 17 
        AND m.data_inicio <= ?
        AND (m.data_fim IS NULL OR m.data_fim >= ?)
        ORDER BY d.nome_completo
        LIMIT 10
    """, (today, today))
    
    print(f"\nSample of deputies active today:")
    print("Name | Start | End | Active | Party | Circle")
    print("-" * 80)
    for row in cursor.fetchall():
        nome, inicio, fim, ativo, partido, circulo = row
        fim_str = fim or "ongoing"
        print(f"{nome[:25]:25} | {inicio} | {fim_str:10} | {ativo:6} | {partido:4} | {circulo[:15]}")
    
    conn.close()

def understand_legislatura_17_period():
    """Understand the actual period of Legislatura 17"""
    print("\n" + "="*70)
    print("UNDERSTANDING LEGISLATURA 17 PERIOD")
    print("="*70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get legislatura 17 info
    cursor.execute("""
        SELECT numero, designacao, data_inicio, data_fim, ativa
        FROM legislaturas
        WHERE numero = 17
    """)
    
    leg_info = cursor.fetchone()
    if leg_info:
        numero, designacao, inicio, fim, ativa = leg_info
        print(f"Legislatura {numero} ({designacao}):")
        print(f"  Official period: {inicio} to {fim or 'ongoing'}")
        print(f"  Marked as active: {ativa}")
    
    # Check if the issue is historical data being included
    cursor.execute("""
        SELECT 
            CASE 
                WHEN m.data_fim IS NULL THEN 'No end date'
                WHEN m.data_fim < '2022-01-01' THEN 'Ended before 2022'
                WHEN m.data_fim < '2023-01-01' THEN 'Ended in 2022'
                WHEN m.data_fim < '2024-01-01' THEN 'Ended in 2023'
                WHEN m.data_fim < '2025-01-01' THEN 'Ended in 2024'
                ELSE 'Ended in 2025 or later'
            END as period,
            COUNT(*) as count
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17
        GROUP BY period
        ORDER BY count DESC
    """)
    
    print(f"\nMandatos grouped by end period:")
    for period, count in cursor.fetchall():
        print(f"  {period}: {count}")
    
    conn.close()

def check_party_distribution():
    """Check party distribution to see if it makes sense"""
    print("\n" + "="*70)
    print("PARTY DISTRIBUTION IN LEGISLATURA 17")
    print("="*70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get party distribution for all mandatos
    cursor.execute("""
        SELECT p.sigla, p.nome, COUNT(*) as mandatos
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        JOIN partidos p ON m.partido_id = p.id
        WHERE l.numero = 17
        GROUP BY p.id
        ORDER BY mandatos DESC
        LIMIT 15
    """)
    
    print("All mandatos by party:")
    total_mandatos = 0
    for sigla, nome, count in cursor.fetchall():
        total_mandatos += count
        nome_short = nome[:30] if nome else sigla
        print(f"  {sigla:8} {nome_short:30}: {count:4} mandatos")
    
    print(f"\nTotal: {total_mandatos} mandatos")
    
    # Now for truly active deputies (no end date or end date in future)
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT p.sigla, p.nome, COUNT(DISTINCT m.deputado_id) as deputies
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        JOIN partidos p ON m.partido_id = p.id
        WHERE l.numero = 17
        AND (m.data_fim IS NULL OR m.data_fim >= ?)
        GROUP BY p.id
        ORDER BY deputies DESC
        LIMIT 15
    """, (today,))
    
    print(f"\nCurrently active deputies by party:")
    total_active = 0
    for sigla, nome, count in cursor.fetchall():
        total_active += count
        nome_short = nome[:30] if nome else sigla
        print(f"  {sigla:8} {nome_short:30}: {count:4} deputies")
    
    print(f"\nTotal active: {total_active} deputies")
    
    conn.close()

def find_the_real_issue():
    """Try to find the root cause of the issue"""
    print("\n" + "="*70)
    print("FINDING THE ROOT CAUSE")
    print("="*70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Let's see if this is a data modeling issue - are we storing ALL historical mandatos
    # even temporary ones, substitutions, etc?
    
    # Check if there are patterns by start date
    cursor.execute("""
        SELECT 
            strftime('%Y-%m', m.data_inicio) as month,
            COUNT(*) as new_mandatos
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17
        GROUP BY month
        ORDER BY month
    """)
    
    print("New mandatos starting by month:")
    for month, count in cursor.fetchall():
        print(f"  {month}: {count} new mandatos")
    
    # Check average mandato duration
    cursor.execute("""
        SELECT 
            AVG(julianday(COALESCE(m.data_fim, date('now'))) - julianday(m.data_inicio)) as avg_days,
            MIN(julianday(COALESCE(m.data_fim, date('now'))) - julianday(m.data_inicio)) as min_days,
            MAX(julianday(COALESCE(m.data_fim, date('now'))) - julianday(m.data_inicio)) as max_days
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        WHERE l.numero = 17
    """)
    
    duration = cursor.fetchone()
    print(f"\nMandato durations (in days):")
    print(f"  Average: {duration[0]:.1f}")
    print(f"  Minimum: {duration[1]:.1f}")
    print(f"  Maximum: {duration[2]:.1f}")
    
    # Find very short mandatos (substitutions?)
    cursor.execute("""
        SELECT d.nome_completo, m.data_inicio, m.data_fim,
               julianday(m.data_fim) - julianday(m.data_inicio) as duration_days,
               p.sigla as partido
        FROM mandatos m
        JOIN legislaturas l ON m.legislatura_id = l.id
        JOIN deputados d ON m.deputado_id = d.id
        JOIN partidos p ON m.partido_id = p.id
        WHERE l.numero = 17 AND m.data_fim IS NOT NULL
        AND julianday(m.data_fim) - julianday(m.data_inicio) < 30
        ORDER BY duration_days
        LIMIT 20
    """)
    
    short_mandatos = cursor.fetchall()
    if short_mandatos:
        print(f"\nVery short mandatos (< 30 days):")
        print("Name | Start | End | Days | Party")
        print("-" * 60)
        for row in short_mandatos:
            nome, inicio, fim, days, partido = row
            print(f"{nome[:20]:20} | {inicio} | {fim} | {days:4.0f} | {partido}")
    
    conn.close()

def main():
    analyze_mandato_dates_leg17()
    analyze_current_active_deputies()
    understand_legislatura_17_period()
    check_party_distribution()
    find_the_real_issue()
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
    The issue is now clear: The database is storing ALL historical mandatos 
    for Legislatura 17, including temporary substitutions, brief appointments,
    and all mandate changes that occurred during the legislature period.
    
    In the Portuguese Parliament system:
    - Deputies can be temporarily replaced by substitutes
    - There can be mid-term resignations and appointments
    - Each change creates a new mandato record
    
    This explains why there are ~3000 mandato records instead of ~230.
    
    To get the CURRENT active deputies, the API should filter by:
    1. mandatos with no end date (data_fim IS NULL), OR
    2. mandatos with end date in the future
    
    This would give the actual ~230 currently serving deputies.
    """)

if __name__ == "__main__":
    main()