#!/usr/bin/env python3
"""
Correção Final das Legislaturas - Parlamento Português
Script para corrigir a atribuição de legislaturas usando os dados XML reais
"""

import sqlite3
import xml.etree.ElementTree as ET
import os
import glob
from datetime import datetime, date

def clean_xml_content(content: bytes) -> bytes:
    """Limpar conteúdo XML removendo BOM Unicode"""
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    elif content.startswith(b'\xff\xfe'):
        content = content[2:]  
    elif content.startswith(b'\xfe\xff'):
        content = content[2:]
    return content

def parse_date(date_str: str) -> date:
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

def safe_int(value) -> int:
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

def corrigir_legislaturas_iniciativas():
    """Corrigir legislaturas das iniciativas usando dados XML reais"""
    
    print("CORRIGINDO LEGISLATURAS DAS INICIATIVAS...")
    
    db_path = 'parlamento.db'
    base_path = "parliament_data_final"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Limpar e recriar dados
    cursor.execute("DELETE FROM iniciativas_legislativas")
    cursor.execute("DELETE FROM autores_iniciativas")
    
    total_iniciativas = 0
    total_autores = 0
    
    # Buscar todos os arquivos de iniciativas
    pattern = f"{base_path}/Iniciativas/**/*.xml"
    arquivos = glob.glob(pattern, recursive=True)
    
    print(f"Processando {len(arquivos)} arquivos de iniciativas...")
    
    for i, arquivo in enumerate(arquivos):
        print(f"[{i+1}/{len(arquivos)}] {os.path.basename(arquivo)}")
        
        try:
            with open(arquivo, 'rb') as f:
                content = clean_xml_content(f.read())
            
            root = ET.fromstring(content.decode('utf-8'))
            
            # Buscar iniciativas com estrutura XML real
            for iniciativa in root.findall('.//Pt_gov_ar_objectos_iniciativas_DetalhePesquisaIniciativasOut'):
                try:
                    # Extrair dados da iniciativa
                    ini_nr = iniciativa.find('IniNr')
                    ini_tipo = iniciativa.find('IniTipo')
                    ini_desc_tipo = iniciativa.find('IniDescTipo')
                    ini_titulo = iniciativa.find('IniTitulo')
                    ini_id = iniciativa.find('IniId')
                    ini_leg = iniciativa.find('IniLeg')  # ESTE É O CAMPO CORRETO!
                    data_inicio_leg = iniciativa.find('DataInicioleg')
                    ini_sel = iniciativa.find('IniSel')
                    
                    numero = ini_nr.text if ini_nr is not None else None
                    tipo = ini_tipo.text if ini_tipo is not None else None
                    tipo_descricao = ini_desc_tipo.text if ini_desc_tipo is not None else None
                    titulo = ini_titulo.text if ini_titulo is not None else None
                    id_externo = ini_id.text if ini_id is not None else None
                    legislatura_sigla = ini_leg.text if ini_leg is not None else 'XVII'  # USAR DADOS XML!
                    data_apresentacao = data_inicio_leg.text if data_inicio_leg is not None else None
                    sessao = ini_sel.text if ini_sel is not None else None
                    
                    if numero and tipo and titulo and legislatura_sigla:
                        # Buscar ou criar legislatura usando dados XML
                        legislatura_id = get_or_create_legislatura(cursor, legislatura_sigla)
                        
                        # Inserir iniciativa
                        cursor.execute("""
                        INSERT OR REPLACE INTO iniciativas_legislativas 
                        (id_externo, numero, tipo, tipo_descricao, titulo, data_apresentacao, sessao, legislatura_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            safe_int(id_externo),
                            safe_int(numero),
                            tipo,
                            tipo_descricao,
                            titulo,
                            parse_date(data_apresentacao),
                            safe_int(sessao),
                            legislatura_id
                        ))
                        
                        iniciativa_db_id = cursor.lastrowid
                        if cursor.rowcount == 0:  # Se foi substituição, buscar ID
                            cursor.execute("SELECT id FROM iniciativas_legislativas WHERE id_externo = ?", (safe_int(id_externo),))
                            result = cursor.fetchone()
                            if result:
                                iniciativa_db_id = result[0]
                        
                        total_iniciativas += 1
                        
                        # Processar autores deputados
                        autores_deputados = iniciativa.find('IniAutorDeputados')
                        if autores_deputados is not None:
                            ordem = 1
                            for autor in autores_deputados.findall('pt_gov_ar_objectos_iniciativas_AutoresDeputadosOut'):
                                id_cadastro_elem = autor.find('idCadastro')
                                
                                if id_cadastro_elem is not None:
                                    id_cadastro = id_cadastro_elem.text
                                    
                                    # Buscar deputado
                                    cursor.execute("SELECT id FROM deputados WHERE id_cadastro = ?", (safe_int(id_cadastro),))
                                    dep_result = cursor.fetchone()
                                    
                                    if dep_result:
                                        cursor.execute("""
                                        INSERT OR REPLACE INTO autores_iniciativas 
                                        (iniciativa_id, deputado_id, tipo_autor, ordem)
                                        VALUES (?, ?, ?, ?)
                                        """, (iniciativa_db_id, dep_result[0], 'principal', ordem))
                                        total_autores += 1
                                        ordem += 1
                        
                        # Processar autores grupos parlamentares
                        autores_gps = iniciativa.find('IniAutorGruposParlamentares')
                        if autores_gps is not None:
                            for autor_gp in autores_gps.findall('pt_gov_ar_objectos_AutoresGruposParlamentaresOut'):
                                gp_elem = autor_gp.find('GP')
                                
                                if gp_elem is not None:
                                    gp = gp_elem.text
                                    
                                    # Buscar partido
                                    cursor.execute("SELECT id FROM partidos WHERE sigla = ?", (gp,))
                                    partido_result = cursor.fetchone()
                                    
                                    if partido_result:
                                        cursor.execute("""
                                        INSERT OR REPLACE INTO autores_iniciativas 
                                        (iniciativa_id, partido_id, tipo_autor, ordem)
                                        VALUES (?, ?, ?, ?)
                                        """, (iniciativa_db_id, partido_result[0], 'apresentante', 1))
                                        total_autores += 1
                
                except Exception as e:
                    print(f"  Erro iniciativa individual: {str(e)}")
                    continue
        
        except Exception as e:
            print(f"  Erro no arquivo: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\nCORRECAO CONCLUIDA:")
    print(f"  Iniciativas: {total_iniciativas}")
    print(f"  Autores: {total_autores}")

def verificar_distribuicao_final():
    """Verificar distribuição final das iniciativas por legislatura"""
    
    print("\nVERIFICANDO DISTRIBUICAO FINAL...")
    
    db_path = 'parlamento.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar distribuição por legislatura
    cursor.execute("""
    SELECT l.designacao, COUNT(i.id) as total
    FROM legislaturas l
    LEFT JOIN iniciativas_legislativas i ON l.id = i.legislatura_id
    GROUP BY l.id, l.designacao
    ORDER BY l.numero DESC
    """)
    
    print("\nINICIATIVAS POR LEGISLATURA:")
    total_geral = 0
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} iniciativas")
        total_geral += row[1]
    
    print(f"\nTOTAL GERAL: {total_geral} iniciativas")
    
    # Mostrar algumas iniciativas da XVII legislatura
    print(f"\nEXEMPLOS DA XVII LEGISLATURA:")
    cursor.execute("""
    SELECT i.numero, i.tipo, i.titulo, l.designacao
    FROM iniciativas_legislativas i
    JOIN legislaturas l ON i.legislatura_id = l.id
    WHERE l.numero = 17
    ORDER BY i.numero
    LIMIT 5
    """)
    
    for row in cursor.fetchall():
        print(f"  N° {row[0]} - {row[1]} - {row[3]}: {row[2][:60]}...")
    
    conn.close()

def main():
    """Função principal"""
    print("CORRECAO FINAL DAS LEGISLATURAS")
    print("=" * 50)
    
    # Corrigir legislaturas usando dados XML reais
    corrigir_legislaturas_iniciativas()
    
    # Verificar distribuição final
    verificar_distribuicao_final()
    
    print("\n✅ CORRECAO FINAL CONCLUIDA!")

if __name__ == "__main__":
    main()