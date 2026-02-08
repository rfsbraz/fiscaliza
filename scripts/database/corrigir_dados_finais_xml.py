#!/usr/bin/env python3
"""
Correção Final dos Dados XML - Parlamento Português
Script para corrigir importação de Agenda, Petições, Comissões e Intervenções
usando as estruturas XML reais descobertas na análise
"""

import sqlite3
import xml.etree.ElementTree as ET
import os
import glob
from datetime import datetime, date, time
import re
from typing import Dict, List, Optional

def clean_xml_content(content: bytes) -> bytes:
    """Limpar conteúdo XML removendo BOM Unicode"""
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    elif content.startswith(b'\xff\xfe'):
        content = content[2:]  
    elif content.startswith(b'\xfe\xff'):
        content = content[2:]
    return content

def parse_date(date_str: str) -> Optional[date]:
    """Converter string de data para objeto date"""
    if not date_str or date_str.strip() == '':
        return None
    
    date_str = date_str.strip()
    
    try:
        if '-' in date_str and len(date_str) >= 10:
            return datetime.strptime(date_str[:10], '%Y-%m-%d').date()
    except ValueError:
        pass
        
    try:
        if 'T' in date_str:
            return datetime.strptime(date_str.split('T')[0], '%Y-%m-%d').date()
    except ValueError:
        pass
    
    return None

def parse_time(time_str: str) -> Optional[time]:
    """Converter string de hora para objeto time"""
    if not time_str or time_str.strip() == '':
        return None
        
    time_str = time_str.strip()
    
    try:
        if len(time_str) >= 8:
            return datetime.strptime(time_str[:8], '%H:%M:%S').time()
    except ValueError:
        pass
        
    try:
        if len(time_str) >= 5:
            return datetime.strptime(time_str[:5], '%H:%M').time()
    except ValueError:
        pass
    
    return None

def safe_int(value) -> Optional[int]:
    """Converter para int de forma segura"""
    if value is None or value == '':
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if value == '':
                return None
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None

def roman_to_int(roman: str) -> int:
    """Converter numeração romana para inteiro"""
    if not roman or roman.strip() == '':
        return 17
    
    roman_map = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
        'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17, 'XVIII': 18,
        'CONSTITUINTE': 0
    }
    
    roman = roman.strip().upper()
    return roman_map.get(roman, 17)

def get_or_create_legislatura(cursor: sqlite3.Cursor, sigla: str) -> int:
    """Buscar ou criar legislatura"""
    numero = roman_to_int(sigla)
    
    cursor.execute("SELECT id FROM legislaturas WHERE numero = ?", (numero,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # Criar nova legislatura
    cursor.execute("""
    INSERT INTO legislaturas (numero, designacao, ativa)
    VALUES (?, ?, ?)
    """, (numero, f"{sigla} Legislatura", sigla == 'XVII'))
    
    return cursor.lastrowid

def corrigir_agenda_parlamentar():
    """Corrigir importação da agenda parlamentar usando estrutura XML real"""
    
    print("CORRIGINDO AGENDA PARLAMENTAR...")
    
    db_path = 'parlamento.db'
    base_path = "parliament_data_final"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Limpar dados existentes
    cursor.execute("DELETE FROM agenda_parlamentar")
    
    total_agenda = 0
    
    # Buscar arquivos de BoletimInformativo (Agenda)
    pattern = f"{base_path}/BoletimInformativo/**/*.xml"
    arquivos = glob.glob(pattern, recursive=True)
    
    print(f"Processando {len(arquivos)} arquivos de agenda...")
    
    for i, arquivo in enumerate(arquivos):
        print(f"[{i+1}/{len(arquivos)}] {os.path.basename(arquivo)}")
        
        try:
            with open(arquivo, 'rb') as f:
                content = clean_xml_content(f.read())
            
            root = ET.fromstring(content.decode('utf-8'))
            
            # Extrair legislatura do nome do arquivo
            filename = os.path.basename(arquivo)
            leg_match = re.search(r'(XVII|XVI|XV|XIV|XIII|XII|XI|X{0,3}I{0,3}V?|CONSTITUINTE)', filename)
            legislatura_sigla = leg_match.group(1) if leg_match else 'XVII'
            legislatura_id = get_or_create_legislatura(cursor, legislatura_sigla)
            
            # Buscar eventos usando estrutura real: ArrayOfAgendaParlamentar/AgendaParlamentar
            for agenda_item in root.findall('.//AgendaParlamentar'):
                try:
                    # Extrair campos conforme estrutura XML real
                    title_elem = agenda_item.find('Title')
                    event_start_date_elem = agenda_item.find('EventStartDate')
                    event_end_date_elem = agenda_item.find('EventEndDate')
                    internet_text_elem = agenda_item.find('InternetText')
                    
                    titulo = title_elem.text if title_elem is not None else None
                    data_inicio = event_start_date_elem.text if event_start_date_elem is not None else None
                    data_fim = event_end_date_elem.text if event_end_date_elem is not None else None
                    descricao = internet_text_elem.text if internet_text_elem is not None else None
                    
                    if titulo and len(titulo.strip()) > 3:
                        cursor.execute("""
                        INSERT INTO agenda_parlamentar 
                        (titulo, data_evento, data_fim_evento, descricao, legislatura_id)
                        VALUES (?, ?, ?, ?, ?)
                        """, (
                            titulo[:500],
                            parse_date(data_inicio) if data_inicio else date.today(),
                            parse_date(data_fim) if data_fim else None,
                            descricao[:1000] if descricao else None,
                            legislatura_id
                        ))
                        total_agenda += 1
                
                except Exception as e:
                    print(f"    Erro ao processar item de agenda: {str(e)}")
                    continue
        
        except Exception as e:
            print(f"    Erro no arquivo: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"AGENDA: {total_agenda} eventos importados")

def corrigir_peticoes():
    """Corrigir importação de petições usando estrutura XML real"""
    
    print("CORRIGINDO PETICOES...")
    
    db_path = 'parlamento.db'
    base_path = "parliament_data_final"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Limpar dados existentes
    cursor.execute("DELETE FROM peticoes")
    
    total_peticoes = 0
    
    # Buscar arquivos de petições
    pattern = f"{base_path}/Peticoes/**/*.xml"
    arquivos = glob.glob(pattern, recursive=True)
    
    if not arquivos:
        # Tentar outros padrões
        pattern = f"{base_path}/**/Peticoes*.xml"
        arquivos = glob.glob(pattern, recursive=True)
    
    print(f"Processando {len(arquivos)} arquivos de petições...")
    
    for i, arquivo in enumerate(arquivos):
        print(f"[{i+1}/{len(arquivos)}] {os.path.basename(arquivo)}")
        
        try:
            with open(arquivo, 'rb') as f:
                content = clean_xml_content(f.read())
            
            root = ET.fromstring(content.decode('utf-8'))
            
            # Extrair legislatura do nome do arquivo
            filename = os.path.basename(arquivo)
            leg_match = re.search(r'(XVII|XVI|XV|XIV|XIII|XII|XI|X{0,3}I{0,3}V?|CONSTITUINTE)', filename)
            legislatura_sigla = leg_match.group(1) if leg_match else 'XVII'
            legislatura_id = get_or_create_legislatura(cursor, legislatura_sigla)
            
            # Buscar petições usando estrutura real: ArrayOfPeticaoOut/PeticaoOut
            for peticao in root.findall('.//PeticaoOut'):
                try:
                    # Extrair campos conforme estrutura XML real
                    pet_nr_elem = peticao.find('PetNr')
                    pet_assunto_elem = peticao.find('PetAssunto')
                    pet_data_entrada_elem = peticao.find('PetDataEntrada')
                    pet_id_elem = peticao.find('PetId')
                    
                    numero = pet_nr_elem.text if pet_nr_elem is not None else None
                    titulo = pet_assunto_elem.text if pet_assunto_elem is not None else None
                    data_entrada = pet_data_entrada_elem.text if pet_data_entrada_elem is not None else None
                    id_externo = pet_id_elem.text if pet_id_elem is not None else None
                    
                    # Só inserir se temos os campos obrigatórios
                    if titulo and len(titulo.strip()) > 3:
                        cursor.execute("""
                        INSERT INTO peticoes 
                        (numero, titulo, data_entrada, id_externo, legislatura_id)
                        VALUES (?, ?, ?, ?, ?)
                        """, (
                            safe_int(numero),
                            titulo[:500],
                            parse_date(data_entrada) if data_entrada else date.today(),
                            safe_int(id_externo),
                            legislatura_id
                        ))
                        total_peticoes += 1
                
                except Exception as e:
                    print(f"    Erro ao processar petição: {str(e)}")
                    continue
        
        except Exception as e:
            print(f"    Erro no arquivo: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"PETICOES: {total_peticoes} importadas")

def corrigir_composicao_orgaos():
    """Corrigir importação de composição de órgãos com membros"""
    
    print("CORRIGINDO COMPOSICAO DE ORGAOS...")
    
    db_path = 'parlamento.db'
    base_path = "parliament_data_final"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Limpar dados existentes
    cursor.execute("DELETE FROM comissoes")
    cursor.execute("DELETE FROM membros_comissoes")
    
    total_comissoes = 0
    total_membros = 0
    
    # Buscar arquivos de composição de órgãos
    pattern = f"{base_path}/ComposicaoOrgaos/**/*.xml"
    arquivos = glob.glob(pattern, recursive=True)
    
    print(f"Processando {len(arquivos)} arquivos de composição...")
    
    for i, arquivo in enumerate(arquivos):
        print(f"[{i+1}/{len(arquivos)}] {os.path.basename(arquivo)}")
        
        try:
            with open(arquivo, 'rb') as f:
                content = clean_xml_content(f.read())
            
            root = ET.fromstring(content.decode('utf-8'))
            
            # Extrair legislatura do nome do arquivo
            filename = os.path.basename(arquivo)
            leg_match = re.search(r'(XVII|XVI|XV|XIV|XIII|XII|XI|X{0,3}I{0,3}V?|CONSTITUINTE)', filename)
            legislatura_sigla = leg_match.group(1) if leg_match else 'XVII'
            legislatura_id = get_or_create_legislatura(cursor, legislatura_sigla)
            
            # Buscar órgãos/comissões usando estrutura real
            for orgao in root.findall('.//OrgaoOut'):
                try:
                    # Extrair informações do órgão
                    id_elem = orgao.find('Id')
                    nome_elem = orgao.find('Nome')
                    sigla_elem = orgao.find('Sigla')
                    tipo_elem = orgao.find('Tipo')
                    
                    id_externo = id_elem.text if id_elem is not None else None
                    nome = nome_elem.text if nome_elem is not None else None
                    sigla = sigla_elem.text if sigla_elem is not None else None
                    tipo = tipo_elem.text if tipo_elem is not None else None
                    
                    if nome and len(nome.strip()) > 3:
                        cursor.execute("""
                        INSERT INTO comissoes 
                        (id_externo, nome, sigla, tipo, legislatura_id, ativa)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            safe_int(id_externo),
                            nome[:200],
                            sigla[:20] if sigla else None,
                            tipo[:100] if tipo else None,
                            legislatura_id,
                            True
                        ))
                        
                        comissao_id = cursor.lastrowid
                        total_comissoes += 1
                        
                        # Buscar membros do órgão
                        membros_elem = orgao.find('Membros')
                        if membros_elem is not None:
                            for membro in membros_elem.findall('.//MembroOut'):
                                try:
                                    dep_id_elem = membro.find('DeputadoId')
                                    cargo_elem = membro.find('Cargo')
                                    data_inicio_elem = membro.find('DataInicio')
                                    data_fim_elem = membro.find('DataFim')
                                    
                                    deputado_cad_id = dep_id_elem.text if dep_id_elem is not None else None
                                    cargo = cargo_elem.text if cargo_elem is not None else None
                                    data_inicio = data_inicio_elem.text if data_inicio_elem is not None else None
                                    data_fim = data_fim_elem.text if data_fim_elem is not None else None
                                    
                                    if deputado_cad_id:
                                        # Buscar deputado
                                        cursor.execute("SELECT id FROM deputados WHERE id_cadastro = ?", (safe_int(deputado_cad_id),))
                                        dep_result = cursor.fetchone()
                                        
                                        if dep_result:
                                            cursor.execute("""
                                            INSERT INTO membros_comissoes 
                                            (comissao_id, deputado_id, cargo, data_inicio, data_fim)
                                            VALUES (?, ?, ?, ?, ?)
                                            """, (
                                                comissao_id,
                                                dep_result[0],
                                                cargo[:100] if cargo else 'Membro',
                                                parse_date(data_inicio) if data_inicio else date.today(),
                                                parse_date(data_fim) if data_fim else None
                                            ))
                                            total_membros += 1
                                
                                except Exception as e:
                                    continue
                
                except Exception as e:
                    print(f"    Erro ao processar órgão: {str(e)}")
                    continue
        
        except Exception as e:
            print(f"    Erro no arquivo: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"COMISSOES: {total_comissoes} importadas")
    print(f"MEMBROS: {total_membros} importados")

def corrigir_intervencoes():
    """Corrigir importação de intervenções usando estrutura XML real"""
    
    print("CORRIGINDO INTERVENCOES...")
    
    db_path = 'parlamento.db'
    base_path = "parliament_data_final"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Limpar dados existentes
    cursor.execute("DELETE FROM intervencoes")
    
    total_intervencoes = 0
    
    # Buscar arquivos de intervenções
    pattern = f"{base_path}/Intervencoes/**/*.xml"
    arquivos = glob.glob(pattern, recursive=True)
    
    print(f"Processando {len(arquivos)} arquivos de intervenções...")
    
    for i, arquivo in enumerate(arquivos):
        print(f"[{i+1}/{len(arquivos)}] {os.path.basename(arquivo)}")
        
        try:
            with open(arquivo, 'rb') as f:
                content = clean_xml_content(f.read())
            
            root = ET.fromstring(content.decode('utf-8'))
            
            # Extrair legislatura do nome do arquivo
            filename = os.path.basename(arquivo)
            leg_match = re.search(r'(XVII|XVI|XV|XIV|XIII|XII|XI|X{0,3}I{0,3}V?|CONSTITUINTE)', filename)
            legislatura_sigla = leg_match.group(1) if leg_match else 'XVII'
            legislatura_id = get_or_create_legislatura(cursor, legislatura_sigla)
            
            # Buscar intervenções usando diferentes estruturas possíveis
            intervencoes_elements = (
                root.findall('.//IntervencoesOut') +
                root.findall('.//pt_gov_ar_objectos_IntervencoesOut') +
                root.findall('.//Intervencao')
            )
            
            for intervencao in intervencoes_elements:
                try:
                    # Tentar extrair campos usando diferentes nomes possíveis
                    id_elem = (intervencao.find('Id') or 
                              intervencao.find('id') or
                              intervencao.find('IntervencaoId'))
                    
                    deputado_elem = (intervencao.find('DeputadoId') or 
                                   intervencao.find('deputadoId') or
                                   intervencao.find('idCadastro'))
                    
                    data_elem = (intervencao.find('Data') or
                               intervencao.find('data') or
                               intervencao.find('dataReuniaoPlenaria'))
                    
                    tipo_elem = (intervencao.find('TipoIntervencao') or
                               intervencao.find('tipo') or
                               intervencao.find('Tipo'))
                    
                    sumario_elem = (intervencao.find('Sumario') or
                                  intervencao.find('sumario') or
                                  intervencao.find('Texto'))
                    
                    if deputado_elem is not None and data_elem is not None:
                        id_externo = id_elem.text if id_elem is not None else None
                        deputado_cad_id = deputado_elem.text
                        data_intervencao = data_elem.text
                        tipo_intervencao = tipo_elem.text if tipo_elem is not None else 'discurso'
                        sumario = sumario_elem.text if sumario_elem is not None else None
                        
                        # Buscar deputado
                        cursor.execute("SELECT id FROM deputados WHERE id_cadastro = ?", (safe_int(deputado_cad_id),))
                        dep_result = cursor.fetchone()
                        
                        if dep_result:
                            cursor.execute("""
                            INSERT INTO intervencoes 
                            (id_externo, deputado_id, data_intervencao, tipo_intervencao, sumario, legislatura_id)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                safe_int(id_externo),
                                dep_result[0],
                                parse_date(data_intervencao),
                                tipo_intervencao[:50],
                                sumario[:1000] if sumario else None,
                                legislatura_id
                            ))
                            total_intervencoes += 1
                
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"    Erro no arquivo: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"INTERVENCOES: {total_intervencoes} importadas")

def verificar_dados_finais():
    """Verificar dados finais após todas as correções"""
    
    print("\nVERIFICANDO DADOS FINAIS...")
    
    db_path = 'parlamento.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tabelas_verificar = [
        'legislaturas', 'partidos', 'circulos_eleitorais', 'deputados', 'mandatos',
        'iniciativas_legislativas', 'autores_iniciativas', 'intervencoes', 
        'agenda_parlamentar', 'comissoes', 'membros_comissoes', 'peticoes'
    ]
    
    print("\nCONTAGENS FINAIS:")
    for tabela in tabelas_verificar:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
            count = cursor.fetchone()[0]
            print(f"  {tabela}: {count:,} registos")
        except Exception as e:
            print(f"  {tabela}: ERRO - {str(e)}")
    
    # Mostrar distribuição por legislatura
    print(f"\nINICIATIVAS POR LEGISLATURA:")
    try:
        cursor.execute("""
        SELECT l.designacao, COUNT(i.id)
        FROM legislaturas l
        LEFT JOIN iniciativas_legislativas i ON l.id = i.legislatura_id
        GROUP BY l.id, l.designacao
        ORDER BY l.numero DESC
        """)
        
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]:,} iniciativas")
    except Exception as e:
        print(f"  Erro ao verificar iniciativas por legislatura: {str(e)}")
    
    conn.close()

def main():
    """Função principal"""
    print("CORRECAO FINAL DOS DADOS XML")
    print("=" * 60)
    
    # Executar todas as correções usando estruturas XML reais
    corrigir_agenda_parlamentar()
    print()
    
    corrigir_peticoes()
    print()
    
    corrigir_composicao_orgaos()
    print()
    
    corrigir_intervencoes()
    print()
    
    # Verificar resultado final
    verificar_dados_finais()
    
    print("\nCORRECAO FINAL DE TODOS OS DADOS CONCLUIDA!")

if __name__ == "__main__":
    main()