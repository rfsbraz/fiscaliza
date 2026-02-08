#!/usr/bin/env python3
"""
Implementação Completa de Relacionamentos - Parlamento Português
Script para adicionar TODOS os relacionamentos faltantes identificados na análise
"""

import sqlite3
import xml.etree.ElementTree as ET
import os
import glob
from datetime import datetime, date
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

class ImplementadorRelacionamentos:
    def __init__(self, db_path='parlamento.db'):
        self.db_path = db_path
        self.stats = defaultdict(int)
        self.errors = []
        
    def log_progress(self, message: str):
        """Log com timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{timestamp} {message}")
    
    def clean_xml_content(self, content: bytes) -> bytes:
        """Limpar conteúdo XML removendo BOM Unicode"""
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
        elif content.startswith(b'\xff\xfe'):
            content = content[2:]
        elif content.startswith(b'\xfe\xff'):
            content = content[2:]
        return content
    
    def safe_int(self, value) -> Optional[int]:
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
    
    def criar_schema_relacionamentos(self):
        """Criar todas as novas tabelas e campos de relacionamento"""
        self.log_progress("Criando schema de relacionamentos...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Tabela de Seções Parlamentares
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS secoes_parlamentares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_externo INTEGER UNIQUE,
                nome TEXT NOT NULL,
                descricao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 2. Tabela de Temas Parlamentares
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS temas_parlamentares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_externo INTEGER UNIQUE,
                nome TEXT NOT NULL,
                descricao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 3. Tabela de Debates Parlamentares
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS debates_parlamentares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_externo INTEGER UNIQUE,
                titulo TEXT,
                sumario TEXT,
                data_debate DATE,
                legislatura_id INTEGER REFERENCES legislaturas(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 4. Tabela de Atividades Parlamentares (expandida)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS atividades_parlamentares_detalhadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_externo INTEGER UNIQUE,
                tipo TEXT,
                titulo TEXT,
                data_atividade DATE,
                legislatura_id INTEGER REFERENCES legislaturas(id),
                debate_id INTEGER REFERENCES debates_parlamentares(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 5. Tabela de Publicações Diário da República
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS publicacoes_diario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero INTEGER,
                tipo TEXT,
                data_publicacao DATE,
                url_diario TEXT,
                paginas TEXT,
                legislatura TEXT,
                sessao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 6. Adicionar campos de relacionamento às tabelas existentes
            
            # agenda_parlamentar: relacionamentos com seções e temas
            try:
                cursor.execute("ALTER TABLE agenda_parlamentar ADD COLUMN secao_parlamentar_id INTEGER REFERENCES secoes_parlamentares(id)")
            except sqlite3.OperationalError:
                pass  # Campo já existe
                
            try:
                cursor.execute("ALTER TABLE agenda_parlamentar ADD COLUMN tema_parlamentar_id INTEGER REFERENCES temas_parlamentares(id)")
            except sqlite3.OperationalError:
                pass
            
            # intervencoes: relacionamentos com atividades, debates e publicações
            try:
                cursor.execute("ALTER TABLE intervencoes ADD COLUMN atividade_parlamentar_id INTEGER REFERENCES atividades_parlamentares_detalhadas(id)")
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute("ALTER TABLE intervencoes ADD COLUMN debate_parlamentar_id INTEGER REFERENCES debates_parlamentares(id)")
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute("ALTER TABLE intervencoes ADD COLUMN publicacao_diario_id INTEGER REFERENCES publicacoes_diario(id)")
            except sqlite3.OperationalError:
                pass
            
            # iniciativas_legislativas: auto-relacionamento
            try:
                cursor.execute("ALTER TABLE iniciativas_legislativas ADD COLUMN iniciativa_origem_id INTEGER REFERENCES iniciativas_legislativas(id)")
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute("ALTER TABLE iniciativas_legislativas ADD COLUMN tipo_relacionamento TEXT")
            except sqlite3.OperationalError:
                pass
            
            # peticoes: relacionamento com iniciativas
            try:
                cursor.execute("ALTER TABLE peticoes ADD COLUMN iniciativa_gerada_id INTEGER REFERENCES iniciativas_legislativas(id)")
            except sqlite3.OperationalError:
                pass
            
            conn.commit()
            self.log_progress("Schema de relacionamentos criado com sucesso!")
            
        except Exception as e:
            self.errors.append(f"Erro ao criar schema: {str(e)}")
            conn.rollback()
        finally:
            conn.close()
    
    def popular_secoes_temas_parlamentares(self):
        """Popular tabelas de seções e temas a partir dos dados de agenda"""
        self.log_progress("Populando seções e temas parlamentares...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        base_path = "parliament_data_final"
        pattern = f"{base_path}/BoletimInformativo/**/*.xml"
        arquivos = glob.glob(pattern, recursive=True)
        
        secoes_map = {}
        temas_map = {}
        
        for arquivo in arquivos:
            try:
                with open(arquivo, 'rb') as f:
                    content = self.clean_xml_content(f.read())
                root = ET.fromstring(content.decode('utf-8'))
                
                for agenda_item in root.findall('.//AgendaParlamentar'):
                    # Processar seções
                    section_id_elem = agenda_item.find('SectionId')
                    section_elem = agenda_item.find('Section')
                    if section_id_elem is not None and section_elem is not None:
                        sec_id = self.safe_int(section_id_elem.text)
                        sec_nome = section_elem.text
                        if sec_id and sec_nome:
                            secoes_map[sec_id] = sec_nome
                    
                    # Processar temas
                    theme_id_elem = agenda_item.find('ThemeId')
                    theme_elem = agenda_item.find('Theme')
                    if theme_id_elem is not None and theme_elem is not None:
                        tema_id = self.safe_int(theme_id_elem.text)
                        tema_nome = theme_elem.text
                        if tema_id and tema_nome:
                            temas_map[tema_id] = tema_nome
            
            except Exception as e:
                self.errors.append(f"Erro ao processar {arquivo}: {str(e)}")
                continue
        
        # Inserir seções
        for sec_id, sec_nome in secoes_map.items():
            cursor.execute("""
            INSERT OR REPLACE INTO secoes_parlamentares (id_externo, nome)
            VALUES (?, ?)
            """, (sec_id, sec_nome))
            self.stats['secoes'] += 1
        
        # Inserir temas
        for tema_id, tema_nome in temas_map.items():
            cursor.execute("""
            INSERT OR REPLACE INTO temas_parlamentares (id_externo, nome)
            VALUES (?, ?)
            """, (tema_id, tema_nome))
            self.stats['temas'] += 1
        
        conn.commit()
        conn.close()
        
        self.log_progress(f"Seções criadas: {self.stats['secoes']}")
        self.log_progress(f"Temas criados: {self.stats['temas']}")
    
    def popular_debates_atividades(self):
        """Popular debates e atividades parlamentares a partir das intervenções"""
        self.log_progress("Populando debates e atividades parlamentares...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        base_path = "parliament_data_final"
        pattern = f"{base_path}/Intervencoes/**/*.xml"
        arquivos = glob.glob(pattern, recursive=True)
        
        debates_map = {}
        atividades_map = {}
        
        for arquivo in arquivos:
            try:
                with open(arquivo, 'rb') as f:
                    content = self.clean_xml_content(f.read())
                root = ET.fromstring(content.decode('utf-8'))
                
                for intervencao in root.findall('.//DadosPesquisaIntervencoesOut'):
                    # Processar debates
                    id_debate_elem = intervencao.find('IdDebate')
                    sumario_elem = intervencao.find('Sumario')
                    data_elem = intervencao.find('DataReuniaoPlenaria')
                    legislatura_elem = intervencao.find('Legislatura')
                    
                    if id_debate_elem is not None:
                        debate_id = self.safe_int(id_debate_elem.text)
                        sumario = sumario_elem.text if sumario_elem is not None else None
                        data_debate = data_elem.text if data_elem is not None else None
                        legislatura = legislatura_elem.text if legislatura_elem is not None else 'XVII'
                        
                        if debate_id and debate_id not in debates_map:
                            debates_map[debate_id] = {
                                'sumario': sumario,
                                'data': data_debate,
                                'legislatura': legislatura
                            }
                    
                    # Processar atividades
                    atividade_id_elem = intervencao.find('ActividadeId')
                    if atividade_id_elem is not None:
                        ativ_id = self.safe_int(atividade_id_elem.text)
                        if ativ_id and ativ_id not in atividades_map:
                            atividades_map[ativ_id] = {
                                'tipo': 'Atividade Parlamentar',
                                'titulo': sumario[:100] if sumario else f'Atividade {ativ_id}',
                                'data': data_debate,
                                'legislatura': legislatura,
                                'debate_id': debate_id
                            }
            
            except Exception as e:
                self.errors.append(f"Erro ao processar {arquivo}: {str(e)}")
                continue
        
        # Inserir debates
        for debate_id, debate_info in debates_map.items():
            # Buscar legislatura_id
            cursor.execute("SELECT id FROM legislaturas WHERE numero = ?", (self.roman_to_int(debate_info['legislatura']),))
            leg_result = cursor.fetchone()
            legislatura_id = leg_result[0] if leg_result else 17
            
            cursor.execute("""
            INSERT OR REPLACE INTO debates_parlamentares (id_externo, sumario, data_debate, legislatura_id)
            VALUES (?, ?, ?, ?)
            """, (
                debate_id,
                debate_info['sumario'][:500] if debate_info['sumario'] else None,
                self.parse_date(debate_info['data']),
                legislatura_id
            ))
            self.stats['debates'] += 1
        
        # Inserir atividades
        for ativ_id, ativ_info in atividades_map.items():
            cursor.execute("SELECT id FROM legislaturas WHERE numero = ?", (self.roman_to_int(ativ_info['legislatura']),))
            leg_result = cursor.fetchone()
            legislatura_id = leg_result[0] if leg_result else 17
            
            # Buscar debate_id
            debate_db_id = None
            if ativ_info['debate_id']:
                cursor.execute("SELECT id FROM debates_parlamentares WHERE id_externo = ?", (ativ_info['debate_id'],))
                debate_result = cursor.fetchone()
                debate_db_id = debate_result[0] if debate_result else None
            
            cursor.execute("""
            INSERT OR REPLACE INTO atividades_parlamentares_detalhadas 
            (id_externo, tipo, titulo, data_atividade, legislatura_id, debate_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ativ_id,
                ativ_info['tipo'],
                ativ_info['titulo'][:200],
                self.parse_date(ativ_info['data']),
                legislatura_id,
                debate_db_id
            ))
            self.stats['atividades'] += 1
        
        conn.commit()
        conn.close()
        
        self.log_progress(f"Debates criados: {self.stats['debates']}")
        self.log_progress(f"Atividades criadas: {self.stats['atividades']}")
    
    def popular_publicacoes(self):
        """Popular publicações do Diário da República"""
        self.log_progress("Populando publicações do Diário da República...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        base_path = "parliament_data_final"
        pattern = f"{base_path}/Intervencoes/**/*.xml"
        arquivos = glob.glob(pattern, recursive=True)
        
        publicacoes_map = {}
        
        for arquivo in arquivos[:10]:  # Processar alguns arquivos para teste
            try:
                with open(arquivo, 'rb') as f:
                    content = self.clean_xml_content(f.read())
                root = ET.fromstring(content.decode('utf-8'))
                
                for intervencao in root.findall('.//DadosPesquisaIntervencoesOut'):
                    publicacao_elem = intervencao.find('Publicacao')
                    if publicacao_elem is not None:
                        pub_data = publicacao_elem.find('pt_gov_ar_objectos_PublicacoesOut')
                        if pub_data is not None:
                            pub_nr_elem = pub_data.find('pubNr')
                            pub_tipo_elem = pub_data.find('pubTipo')
                            pub_dt_elem = pub_data.find('pubdt')
                            url_elem = pub_data.find('URLDiario')
                            pag_elem = pub_data.find('pag')
                            pub_leg_elem = pub_data.find('pubLeg')
                            pub_sl_elem = pub_data.find('pubSL')
                            
                            if pub_nr_elem is not None and pub_tipo_elem is not None:
                                pub_key = f"{pub_nr_elem.text}_{pub_tipo_elem.text}_{pub_dt_elem.text if pub_dt_elem is not None else ''}"
                                
                                if pub_key not in publicacoes_map:
                                    paginas = None
                                    if pag_elem is not None:
                                        pag_strings = [p.text for p in pag_elem.findall('string') if p.text]
                                        paginas = ', '.join(pag_strings) if pag_strings else None
                                    
                                    publicacoes_map[pub_key] = {
                                        'numero': self.safe_int(pub_nr_elem.text),
                                        'tipo': pub_tipo_elem.text,
                                        'data': pub_dt_elem.text if pub_dt_elem is not None else None,
                                        'url': url_elem.text if url_elem is not None else None,
                                        'paginas': paginas,
                                        'legislatura': pub_leg_elem.text if pub_leg_elem is not None else None,
                                        'sessao': pub_sl_elem.text if pub_sl_elem is not None else None
                                    }
            except Exception as e:
                self.errors.append(f"Erro ao processar publicações {arquivo}: {str(e)}")
                continue
        
        # Inserir publicações
        for pub_info in publicacoes_map.values():
            cursor.execute("""
            INSERT OR REPLACE INTO publicacoes_diario 
            (numero, tipo, data_publicacao, url_diario, paginas, legislatura, sessao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pub_info['numero'],
                pub_info['tipo'],
                self.parse_date(pub_info['data']),
                pub_info['url'],
                pub_info['paginas'],
                pub_info['legislatura'],
                pub_info['sessao']
            ))
            self.stats['publicacoes'] += 1
        
        conn.commit()
        conn.close()
        
        self.log_progress(f"Publicações criadas: {self.stats['publicacoes']}")
    
    def conectar_relacionamentos(self):
        """Conectar todos os relacionamentos criados"""
        self.log_progress("Conectando relacionamentos...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Conectar agenda com seções e temas
        cursor.execute("""
        UPDATE agenda_parlamentar 
        SET secao_parlamentar_id = (
            SELECT s.id FROM secoes_parlamentares s 
            WHERE s.id_externo = agenda_parlamentar.secao_id
        )
        WHERE agenda_parlamentar.secao_id IS NOT NULL
        """)
        self.stats['agenda_secoes_conectadas'] = cursor.rowcount
        
        cursor.execute("""
        UPDATE agenda_parlamentar 
        SET tema_parlamentar_id = (
            SELECT t.id FROM temas_parlamentares t 
            WHERE t.id_externo = agenda_parlamentar.tema_id
        )
        WHERE agenda_parlamentar.tema_id IS NOT NULL
        """)
        self.stats['agenda_temas_conectados'] = cursor.rowcount
        
        # 2. Conectar intervenções com debates e atividades (usando dados XML)
        self.conectar_intervencoes_xml(cursor)
        
        # 3. Detectar auto-relacionamentos em iniciativas
        self.detectar_iniciativas_relacionadas(cursor)
        
        conn.commit()  
        conn.close()
        
        self.log_progress(f"Agenda-Seções conectadas: {self.stats['agenda_secoes_conectadas']}")
        self.log_progress(f"Agenda-Temas conectados: {self.stats['agenda_temas_conectados']}")
    
    def conectar_intervencoes_xml(self, cursor):
        """Conectar intervenções usando dados XML originais"""
        base_path = "parliament_data_final"
        pattern = f"{base_path}/Intervencoes/**/*.xml"
        arquivos = glob.glob(pattern, recursive=True)
        
        for arquivo in arquivos:
            try:
                with open(arquivo, 'rb') as f:
                    content = self.clean_xml_content(f.read())
                root = ET.fromstring(content.decode('utf-8'))
                
                for intervencao in root.findall('.//DadosPesquisaIntervencoesOut'):
                    id_externo_elem = intervencao.find('Id')
                    id_debate_elem = intervencao.find('IdDebate')
                    atividade_id_elem = intervencao.find('ActividadeId')
                    
                    if id_externo_elem is not None:
                        id_externo = self.safe_int(id_externo_elem.text)
                        
                        # Conectar com debate
                        if id_debate_elem is not None:
                            debate_externo = self.safe_int(id_debate_elem.text)
                            cursor.execute("""
                            UPDATE intervencoes 
                            SET debate_parlamentar_id = (
                                SELECT id FROM debates_parlamentares WHERE id_externo = ?
                            )
                            WHERE id_externo = ?
                            """, (debate_externo, id_externo))
                            
                            if cursor.rowcount > 0:
                                self.stats['intervencoes_debates_conectadas'] += 1
                        
                        # Conectar com atividade
                        if atividade_id_elem is not None:
                            atividade_externo = self.safe_int(atividade_id_elem.text)
                            cursor.execute("""
                            UPDATE intervencoes 
                            SET atividade_parlamentar_id = (
                                SELECT id FROM atividades_parlamentares_detalhadas WHERE id_externo = ?
                            )
                            WHERE id_externo = ?
                            """, (atividade_externo, id_externo))
                            
                            if cursor.rowcount > 0:
                                self.stats['intervencoes_atividades_conectadas'] += 1
            
            except Exception as e:
                self.errors.append(f"Erro ao conectar intervenções {arquivo}: {str(e)}")
                continue
    
    def detectar_iniciativas_relacionadas(self, cursor):
        """Detectar relacionamentos hierárquicos entre iniciativas"""
        # Buscar iniciativas com palavras-chave que indicam relacionamento
        cursor.execute("""
        SELECT id, titulo, numero, tipo FROM iniciativas_legislativas 
        WHERE LOWER(titulo) LIKE '%substitutiv%' 
           OR LOWER(titulo) LIKE '%altera%' 
           OR LOWER(titulo) LIKE '%emenda%'
           OR LOWER(titulo) LIKE '%modific%'
        """)
        
        iniciativas_dependentes = cursor.fetchall()
        
        for iniciativa in iniciativas_dependentes:
            id_iniciativa, titulo, numero, tipo = iniciativa
            
            # Tentar encontrar iniciativa original por padrões no título
            palavras_busca = []
            if 'altera' in titulo.lower():
                # Extrair possíveis referências a outras leis
                import re
                refs = re.findall(r'lei n\.?\s*(\d+)', titulo.lower())
                palavras_busca.extend(refs)
            
            # Buscar iniciativas similares por número ou palavras-chave
            if palavras_busca:
                for ref in palavras_busca:
                    cursor.execute("""
                    SELECT id FROM iniciativas_legislativas 
                    WHERE numero = ? AND id != ?
                    LIMIT 1
                    """, (int(ref), id_iniciativa))
                    
                    origem = cursor.fetchone()
                    if origem:
                        cursor.execute("""
                        UPDATE iniciativas_legislativas 
                        SET iniciativa_origem_id = ?, tipo_relacionamento = 'alteracao'
                        WHERE id = ?
                        """, (origem[0], id_iniciativa))
                        self.stats['iniciativas_relacionadas'] += 1
                        break
    
    def roman_to_int(self, roman: str) -> int:
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
    
    def parse_date(self, date_str: str) -> Optional[date]:
        """Converter string de data para objeto date"""
        if not date_str or date_str.strip() == '':
            return None
        
        date_str = date_str.strip()
        
        try:
            if '-' in date_str and len(date_str) >= 10:
                return datetime.strptime(date_str[:10], '%Y-%m-%d').date()
        except ValueError:
            pass
        
        return None
    
    def verificar_relacionamentos_finais(self):
        """Verificar estatísticas finais dos relacionamentos"""
        self.log_progress("Verificando relacionamentos finais...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        verificacoes = [
            ("Seções Parlamentares", "SELECT COUNT(*) FROM secoes_parlamentares"),
            ("Temas Parlamentares", "SELECT COUNT(*) FROM temas_parlamentares"),
            ("Debates Parlamentares", "SELECT COUNT(*) FROM debates_parlamentares"),
            ("Atividades Detalhadas", "SELECT COUNT(*) FROM atividades_parlamentares_detalhadas"),
            ("Publicações Diário", "SELECT COUNT(*) FROM publicacoes_diario"),
            ("Agenda com Seções", "SELECT COUNT(*) FROM agenda_parlamentar WHERE secao_parlamentar_id IS NOT NULL"),
            ("Agenda com Temas", "SELECT COUNT(*) FROM agenda_parlamentar WHERE tema_parlamentar_id IS NOT NULL"),
            ("Intervenções com Debates", "SELECT COUNT(*) FROM intervencoes WHERE debate_parlamentar_id IS NOT NULL"),
            ("Intervenções com Atividades", "SELECT COUNT(*) FROM intervencoes WHERE atividade_parlamentar_id IS NOT NULL"),
            ("Iniciativas Relacionadas", "SELECT COUNT(*) FROM iniciativas_legislativas WHERE iniciativa_origem_id IS NOT NULL")
        ]
        
        print("\nESTATÍSTICAS FINAIS DOS RELACIONAMENTOS:")
        print("=" * 60)
        
        for nome, query in verificacoes:
            try:
                cursor.execute(query)
                count = cursor.fetchone()[0]
                print(f"  {nome}: {count:,}")
            except Exception as e:
                print(f"  {nome}: ERRO - {str(e)}")
        
        conn.close()
    
    def executar_implementacao_completa(self):
        """Executar implementação completa de todos os relacionamentos"""
        self.log_progress("INICIANDO IMPLEMENTAÇÃO COMPLETA DE RELACIONAMENTOS")
        print("=" * 70)
        
        try:
            # Fase 1: Criar schema
            self.criar_schema_relacionamentos()
            
            # Fase 2: Popular tabelas de lookup
            self.popular_secoes_temas_parlamentares()
            
            # Fase 3: Popular tabelas de relacionamento
            self.popular_debates_atividades()
            self.popular_publicacoes()
            
            # Fase 4: Conectar relacionamentos
            self.conectar_relacionamentos()
            
            # Fase 5: Verificar resultados
            self.verificar_relacionamentos_finais()
            
            self.log_progress("IMPLEMENTAÇÃO COMPLETA CONCLUÍDA COM SUCESSO!")
            
            if self.errors:
                print(f"\nErros encontrados: {len(self.errors)}")
                for error in self.errors[-5:]:  # Mostrar últimos 5 erros
                    print(f"  - {error}")
            
        except Exception as e:
            self.log_progress(f"ERRO CRÍTICO: {str(e)}")
            raise

def main():
    print("IMPLEMENTAÇÃO COMPLETA DE RELACIONAMENTOS - PARLAMENTO PORTUGUÊS")
    print("=" * 70)
    print("Este script implementará TODOS os relacionamentos identificados:")
    print("- Seções e Temas Parlamentares")
    print("- Debates e Atividades")
    print("- Publicações do Diário da República")
    print("- Auto-relacionamentos de Iniciativas")
    print("- Conexões entre Intervenções e contexto")
    print()
    
    implementador = ImplementadorRelacionamentos()
    implementador.executar_implementacao_completa()

if __name__ == "__main__":
    main()