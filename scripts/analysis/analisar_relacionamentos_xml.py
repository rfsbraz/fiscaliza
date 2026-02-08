#!/usr/bin/env python3
"""
Análise de Relacionamentos nos Dados XML - Parlamento Português
Script para identificar relacionamentos implícitos nos dados XML
"""

import sqlite3
import xml.etree.ElementTree as ET
import os
import glob
from collections import defaultdict

def clean_xml_content(content: bytes) -> bytes:
    """Limpar conteúdo XML removendo BOM Unicode"""
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    elif content.startswith(b'\xff\xfe'):
        content = content[2:]
    elif content.startswith(b'\xfe\xff'):  
        content = content[2:]
    return content

def analisar_relacionamentos_xml():
    print('ANÁLISE DE RELACIONAMENTOS NOS DADOS XML')
    print('=' * 60)
    
    base_path = "parliament_data_final"
    relacionamentos_encontrados = defaultdict(set)
    
    # 1. Analisar Intervenções para encontrar relacionamentos
    print('\n1. ANALISANDO INTERVENÇÕES...')
    pattern = f"{base_path}/Intervencoes/**/*.xml"
    arquivos_intervencoes = glob.glob(pattern, recursive=True)
    
    atividades_encontradas = set()
    debates_encontrados = set()
    
    for arquivo in arquivos_intervencoes[:3]:  # Analisar alguns arquivos
        print(f'   Analisando: {os.path.basename(arquivo)}')
        try:
            with open(arquivo, 'rb') as f:
                content = clean_xml_content(f.read())
            root = ET.fromstring(content.decode('utf-8'))
            
            for intervencao in root.findall('.//DadosPesquisaIntervencoesOut'):
                # Buscar relacionamentos com atividades
                atividade_id_elem = intervencao.find('ActividadeId')
                if atividade_id_elem is not None:
                    atividades_encontradas.add(atividade_id_elem.text)
                
                # Buscar relacionamentos com debates
                id_debate_elem = intervencao.find('IdDebate')
                if id_debate_elem is not None:
                    debates_encontrados.add(id_debate_elem.text)
                
                # Buscar relacionamentos com publicações
                publicacao_elem = intervencao.find('Publicacao')
                if publicacao_elem is not None:
                    pub_data = publicacao_elem.find('pt_gov_ar_objectos_PublicacoesOut')
                    if pub_data is not None:
                        relacionamentos_encontrados['intervencoes_publicacoes'].add('publicacao_id')
        
        except Exception as e:
            print(f'   Erro: {str(e)}')
            continue
    
    print(f'   Atividades únicas encontradas: {len(atividades_encontradas)}')
    print(f'   Debates únicos encontrados: {len(debates_encontrados)}')
    
    # 2. Analisar Agenda para encontrar relacionamentos
    print('\n2. ANALISANDO AGENDA PARLAMENTAR...')
    pattern = f"{base_path}/BoletimInformativo/**/*.xml"
    arquivos_agenda = glob.glob(pattern, recursive=True)
    
    secoes_encontradas = set()
    temas_encontrados = set()
    
    for arquivo in arquivos_agenda[:3]:
        print(f'   Analisando: {os.path.basename(arquivo)}')
        try:
            with open(arquivo, 'rb') as f:
                content = clean_xml_content(f.read())
            root = ET.fromstring(content.decode('utf-8'))
            
            for agenda_item in root.findall('.//AgendaParlamentar'):
                # Buscar seções
                section_id_elem = agenda_item.find('SectionId')
                section_elem = agenda_item.find('Section')
                if section_id_elem is not None and section_elem is not None:
                    secoes_encontradas.add((section_id_elem.text, section_elem.text))
                
                # Buscar temas
                theme_id_elem = agenda_item.find('ThemeId')
                theme_elem = agenda_item.find('Theme')  
                if theme_id_elem is not None and theme_elem is not None:
                    temas_encontrados.add((theme_id_elem.text, theme_elem.text))
        
        except Exception as e:
            print(f'   Erro: {str(e)}')
            continue
    
    print(f'   Seções únicas encontradas: {len(secoes_encontradas)}')
    print(f'   Temas únicos encontrados: {len(temas_encontrados)}')
    
    # 3. Analisar Iniciativas para relacionamentos internos
    print('\n3. ANALISANDO INICIATIVAS LEGISLATIVAS...')
    pattern = f"{base_path}/Iniciativas/**/*.xml"
    arquivos_iniciativas = glob.glob(pattern, recursive=True)
    
    tipos_iniciativas = defaultdict(int)
    iniciativas_com_substitutivos = 0
    
    for arquivo in arquivos_iniciativas[:3]:
        print(f'   Analisando: {os.path.basename(arquivo)}')
        try:
            with open(arquivo, 'rb') as f:
                content = clean_xml_content(f.read())
            root = ET.fromstring(content.decode('utf-8'))
            
            for iniciativa in root.findall('.//Pt_gov_ar_objectos_iniciativas_DetalhePesquisaIniciativasOut'):
                # Analisar tipos
                ini_tipo_elem = iniciativa.find('IniTipo')
                if ini_tipo_elem is not None:
                    tipos_iniciativas[ini_tipo_elem.text] += 1
                
                # Buscar títulos que indicam relacionamentos
                ini_titulo_elem = iniciativa.find('IniTitulo')
                if ini_titulo_elem is not None:
                    titulo = ini_titulo_elem.text.lower()
                    if 'substitutiv' in titulo or 'altera' in titulo or 'emenda' in titulo:
                        iniciativas_com_substitutivos += 1
        
        except Exception as e:
            print(f'   Erro: {str(e)}')
            continue
    
    print(f'   Tipos de iniciativas encontrados: {dict(tipos_iniciativas)}')
    print(f'   Iniciativas com indicação de relacionamento: {iniciativas_com_substitutivos}')
    
    # 4. Verificar dados atuais no banco
    print('\n4. VERIFICAÇÃO DOS DADOS ATUAIS NO BANCO...')
    conn = sqlite3.connect('parlamento.db')
    cursor = conn.cursor()
    
    # Verificar se temos IDs externos que poderiam ser relacionados
    cursor.execute('SELECT COUNT(DISTINCT id_externo) FROM intervencoes WHERE id_externo IS NOT NULL')
    int_com_id_externo = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT id_externo) FROM agenda_parlamentar WHERE id_externo IS NOT NULL')
    agenda_com_id_externo = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT id_externo) FROM iniciativas_legislativas WHERE id_externo IS NOT NULL')
    init_com_id_externo = cursor.fetchone()[0]
    
    print(f'   Intervenções com ID externo: {int_com_id_externo:,}')
    print(f'   Agenda com ID externo: {agenda_com_id_externo:,}')
    print(f'   Iniciativas com ID externo: {init_com_id_externo:,}')
    
    # Verificar overlaps temporais
    cursor.execute('''
    SELECT COUNT(*) as overlaps FROM intervencoes i 
    JOIN agenda_parlamentar a ON date(i.data_intervencao) = date(a.data_evento)
    AND i.legislatura_id = a.legislatura_id
    ''')
    overlaps = cursor.fetchone()[0]
    print(f'   Sobreposições data intervenções/agenda: {overlaps:,}')
    
    conn.close()
    
    # 5. Recomendações de relacionamentos
    print('\n5. RECOMENDAÇÕES DE RELACIONAMENTOS A IMPLEMENTAR')
    print('=' * 60)
    
    recomendacoes = [
        {
            'tabela': 'agenda_parlamentar',
            'novo_campo': 'secao_id (FK)',
            'tipo': 'Lookup table',
            'descricao': f'Criar tabela secoes_parlamentares com {len(secoes_encontradas)} seções encontradas',
            'sql': '''
            CREATE TABLE secoes_parlamentares (
                id INTEGER PRIMARY KEY,
                id_externo INTEGER UNIQUE,
                nome TEXT NOT NULL,
                descricao TEXT
            );
            ALTER TABLE agenda_parlamentar ADD COLUMN secao_id INTEGER REFERENCES secoes_parlamentares(id);
            '''
        },
        {
            'tabela': 'agenda_parlamentar', 
            'novo_campo': 'tema_id (FK)',
            'tipo': 'Lookup table',
            'descricao': f'Criar tabela temas_parlamentares com {len(temas_encontrados)} temas encontrados',
            'sql': '''
            CREATE TABLE temas_parlamentares (
                id INTEGER PRIMARY KEY,
                id_externo INTEGER UNIQUE, 
                nome TEXT NOT NULL,
                descricao TEXT
            );
            ALTER TABLE agenda_parlamentar ADD COLUMN tema_id INTEGER REFERENCES temas_parlamentares(id);
            '''
        },
        {
            'tabela': 'intervencoes',
            'novo_campo': 'atividade_id (FK)',
            'tipo': 'Many-to-One',
            'descricao': f'Relacionar com {len(atividades_encontradas)} atividades parlamentares únicas',
            'sql': '''
            ALTER TABLE intervencoes ADD COLUMN atividade_parlamentar_id INTEGER;
            -- Popular com base nos dados XML ActividadeId
            '''
        },
        {
            'tabela': 'intervencoes',
            'novo_campo': 'debate_id (FK)', 
            'tipo': 'Many-to-One',
            'descricao': f'Criar tabela debates com {len(debates_encontrados)} debates únicos',
            'sql': '''
            CREATE TABLE debates_parlamentares (
                id INTEGER PRIMARY KEY,
                id_externo INTEGER UNIQUE,
                titulo TEXT,
                data_debate DATE,
                legislatura_id INTEGER REFERENCES legislaturas(id)
            );
            ALTER TABLE intervencoes ADD COLUMN debate_id INTEGER REFERENCES debates_parlamentares(id);
            '''
        },
        {
            'tabela': 'iniciativas_legislativas',
            'novo_campo': 'iniciativa_origem_id (FK)',
            'tipo': 'Self-referencing',
            'descricao': f'Relacionamento hierárquico para {iniciativas_com_substitutivos} iniciativas relacionadas',
            'sql': '''
            ALTER TABLE iniciativas_legislativas ADD COLUMN iniciativa_origem_id INTEGER REFERENCES iniciativas_legislativas(id);
            -- Identificar através de análise textual dos títulos
            '''
        },
        {
            'tabela': 'publicacoes_diario',
            'novo_campo': 'Tabela nova',
            'tipo': 'One-to-Many',
            'descricao': 'Relacionar intervenções com publicações no Diário da República',
            'sql': '''
            CREATE TABLE publicacoes_diario (
                id INTEGER PRIMARY KEY,
                numero INTEGER,
                tipo TEXT,
                data_publicacao DATE,
                url_diario TEXT,
                paginas TEXT
            );
            ALTER TABLE intervencoes ADD COLUMN publicacao_id INTEGER REFERENCES publicacoes_diario(id);
            '''
        }
    ]
    
    for i, rec in enumerate(recomendacoes, 1):
        print(f'{i}. {rec["tabela"]}.{rec["novo_campo"]} ({rec["tipo"]})')
        print(f'   {rec["descricao"]}')
        print(f'   SQL: {rec["sql"].strip()}')
        print()

if __name__ == "__main__":
    analisar_relacionamentos_xml()