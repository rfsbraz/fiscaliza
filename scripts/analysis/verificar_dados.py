#!/usr/bin/env python3
import sqlite3

def verificar_dados():
    """Verifica os dados importados na base de dados"""
    conn = sqlite3.connect('/home/ubuntu/parlamento.db')
    cursor = conn.cursor()
    
    print("=== Verificação dos Dados Importados ===\n")
    
    # Total de deputados
    cursor.execute("SELECT COUNT(*) FROM deputados")
    total_deputados = cursor.fetchone()[0]
    print(f"Total de deputados: {total_deputados}")
    
    # Total de partidos
    cursor.execute("SELECT COUNT(*) FROM partidos")
    total_partidos = cursor.fetchone()[0]
    print(f"Total de partidos: {total_partidos}")
    
    # Total de mandatos
    cursor.execute("SELECT COUNT(*) FROM mandatos")
    total_mandatos = cursor.fetchone()[0]
    print(f"Total de mandatos: {total_mandatos}")
    
    # Total de círculos eleitorais
    cursor.execute("SELECT COUNT(*) FROM circulos_eleitorais")
    total_circulos = cursor.fetchone()[0]
    print(f"Total de círculos eleitorais: {total_circulos}")
    
    print("\n=== Deputados por Partido ===")
    cursor.execute("""
        SELECT p.sigla, p.designacao_completa, COUNT(m.id) as num_deputados 
        FROM partidos p 
        LEFT JOIN mandatos m ON p.id = m.partido_id 
        GROUP BY p.sigla, p.designacao_completa 
        ORDER BY num_deputados DESC
    """)
    
    for row in cursor.fetchall():
        sigla, designacao, num_deputados = row
        print(f"  {sigla}: {num_deputados} deputados - {designacao}")
    
    print("\n=== Alguns Deputados (amostra) ===")
    cursor.execute("""
        SELECT d.nome_parlamentar, d.nome_completo, p.sigla, c.designacao
        FROM deputados d
        LEFT JOIN mandatos m ON d.id = m.deputado_id
        LEFT JOIN partidos p ON m.partido_id = p.id
        LEFT JOIN circulos_eleitorais c ON m.circulo_eleitoral_id = c.id
        LIMIT 10
    """)
    
    for row in cursor.fetchall():
        nome_parl, nome_completo, partido, circulo = row
        print(f"  {nome_parl or nome_completo} ({partido}) - {circulo}")
    
    conn.close()

if __name__ == "__main__":
    verificar_dados()

