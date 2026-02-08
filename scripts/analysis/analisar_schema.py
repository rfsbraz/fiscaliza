#!/usr/bin/env python3
"""
Análise do Schema do Banco de Dados - Parlamento Português
Script para identificar relacionamentos existentes e faltantes
"""

import sqlite3
from collections import defaultdict

def analisar_schema():
    conn = sqlite3.connect('parlamento.db')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print('DATABASE TABLES AND THEIR RELATIONSHIPS')
    print('=' * 60)
    
    table_info = {}
    
    for table in tables:
        cursor.execute(f'PRAGMA table_info({table})')
        columns = cursor.fetchall()
        
        foreign_keys = []
        primary_keys = []
        all_columns = []
        
        for col in columns:
            col_name, col_type = col[1], col[2]
            is_pk = col[5] == 1
            all_columns.append((col_name, col_type))
            
            if is_pk:
                primary_keys.append(col_name)
            if col_name.endswith('_id') and col_name != 'id':
                foreign_keys.append(col_name)
        
        # Show record counts
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        
        table_info[table] = {
            'columns': all_columns,
            'primary_keys': primary_keys,
            'foreign_keys': foreign_keys,
            'count': count
        }
        
        print(f'\n{table.upper()}:')
        print(f'  PK: {primary_keys}')
        print(f'  FKs: {foreign_keys}')
        print(f'  Records: {count:,}')
    
    # Analyze potential missing relationships
    print('\n\nPOTENTIAL MISSING RELATIONSHIPS')
    print('=' * 60)
    
    # Check for patterns that suggest missing relationships
    missing_relationships = []
    
    # 1. Agenda events could be linked to legislative initiatives
    if 'agenda_parlamentar' in table_info and 'iniciativas_legislativas' in table_info:
        agenda_count = table_info['agenda_parlamentar']['count']
        iniciativas_count = table_info['iniciativas_legislativas']['count']
        if agenda_count > 0 and iniciativas_count > 0:
            missing_relationships.append({
                'type': '1-to-many',
                'from': 'iniciativas_legislativas',
                'to': 'agenda_parlamentar',
                'field': 'iniciativa_id',
                'description': 'Legislative initiatives can appear on multiple agenda items'
            })
    
    # 2. Interventions could be linked to agenda items
    if 'intervencoes' in table_info and 'agenda_parlamentar' in table_info:
        missing_relationships.append({
            'type': '1-to-many', 
            'from': 'agenda_parlamentar',
            'to': 'intervencoes',
            'field': 'agenda_item_id',
            'description': 'Parliamentary speeches occur during specific agenda items'
        })
    
    # 3. Interventions could be linked to legislative initiatives
    if 'intervencoes' in table_info and 'iniciativas_legislativas' in table_info:
        missing_relationships.append({
            'type': '1-to-many',
            'from': 'iniciativas_legislativas', 
            'to': 'intervencoes',
            'field': 'iniciativa_id',
            'description': 'Speeches can be about specific legislative initiatives'
        })
    
    # 4. Petitions could be linked to legislative initiatives
    if 'peticoes' in table_info and 'iniciativas_legislativas' in table_info:
        missing_relationships.append({
            'type': '1-to-many',
            'from': 'peticoes',
            'to': 'iniciativas_legislativas', 
            'field': 'peticao_id',
            'description': 'Petitions can generate legislative initiatives'
        })
    
    # 5. Committee meetings/agenda items
    if 'comissoes' in table_info and 'agenda_parlamentar' in table_info:
        missing_relationships.append({
            'type': '1-to-many',
            'from': 'comissoes',
            'to': 'agenda_parlamentar',
            'field': 'comissao_id', 
            'description': 'Committee meetings appear on parliamentary agenda'
        })
    
    # 6. Legislative initiatives could have multiple versions/amendments
    if 'iniciativas_legislativas' in table_info:
        missing_relationships.append({
            'type': '1-to-many (self)',
            'from': 'iniciativas_legislativas',
            'to': 'iniciativas_legislativas',
            'field': 'iniciativa_pai_id',
            'description': 'Amendments and substitutive texts reference original initiatives'
        })
    
    # 7. Deputies voting records (if we had voting data)
    missing_relationships.append({
        'type': '1-to-many (missing table)',
        'from': 'deputados + iniciativas_legislativas',
        'to': 'votacoes (missing)',
        'field': 'deputado_id, iniciativa_id, voto',
        'description': 'Individual deputy votes on legislative initiatives'
    })
    
    # 8. Session/plenary meetings
    missing_relationships.append({
        'type': '1-to-many (missing table)',
        'from': 'legislaturas',
        'to': 'sessoes_plenarias (missing)',
        'field': 'sessao_plenaria_id',
        'description': 'Formal plenary sessions where interventions and votes occur'
    })
    
    # Display missing relationships
    for i, rel in enumerate(missing_relationships, 1):
        print(f'{i}. {rel["from"]} -> {rel["to"]} ({rel["type"]})')
        print(f'   Field: {rel["field"]}')
        print(f'   Description: {rel["description"]}')
        print()
    
    # Analyze existing data for relationship validation
    print('\nDATA VALIDATION FOR RELATIONSHIPS')
    print('=' * 60)
    
    # Check if interventions have sessions/activities
    if 'intervencoes' in table_info:
        cursor.execute('SELECT COUNT(*) FROM intervencoes WHERE atividade_id IS NOT NULL')
        with_activity = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM intervencoes WHERE sessao_plenaria_id IS NOT NULL')
        with_session = cursor.fetchone()[0]
        total_int = table_info['intervencoes']['count']
        
        print(f'Interventions with activity_id: {with_activity:,}/{total_int:,} ({with_activity/total_int*100:.1f}%)')
        print(f'Interventions with session_id: {with_session:,}/{total_int:,} ({with_session/total_int*100:.1f}%)')
    
    # Check mandate-deputy relationships
    if 'mandatos' in table_info and 'deputados' in table_info:
        cursor.execute('''
        SELECT COUNT(DISTINCT d.id) as deputies_with_mandates, 
               (SELECT COUNT(*) FROM deputados) as total_deputies
        FROM deputados d 
        JOIN mandatos m ON d.id = m.deputado_id
        ''')
        result = cursor.fetchone()
        print(f'Deputies with mandates: {result[0]:,}/{result[1]:,} ({result[0]/result[1]*100:.1f}%)')
    
    # Check initiative-author relationships  
    if 'autores_iniciativas' in table_info and 'iniciativas_legislativas' in table_info:
        cursor.execute('''
        SELECT COUNT(DISTINCT i.id) as initiatives_with_authors,
               (SELECT COUNT(*) FROM iniciativas_legislativas) as total_initiatives
        FROM iniciativas_legislativas i
        JOIN autores_iniciativas a ON i.id = a.iniciativa_id
        ''')
        result = cursor.fetchone()
        print(f'Initiatives with authors: {result[0]:,}/{result[1]:,} ({result[0]/result[1]*100:.1f}%)')
    
    conn.close()

if __name__ == "__main__":
    analisar_schema()