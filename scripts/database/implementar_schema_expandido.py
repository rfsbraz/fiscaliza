#!/usr/bin/env python3
"""
Implementação do Schema Expandido - Parlamento Português
Script para migrar da estrutura básica (6 tabelas) para o schema expandido (22 tabelas)
"""

import sqlite3
import os
import sys
from datetime import datetime

class ImplementadorSchemaExpandido:
    def __init__(self, db_path='parlamento.db'):
        self.db_path = db_path
        self.backup_path = f"parlamento_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
    def fazer_backup(self):
        """Criar backup da base de dados atual"""
        if os.path.exists(self.db_path):
            import shutil
            shutil.copy2(self.db_path, self.backup_path)
            print(f"Backup criado: {self.backup_path}")
            return True
        else:
            print(f"Base de dados nao existe: {self.db_path}")
            return False
    
    def verificar_estrutura_atual(self):
        """Verificar estrutura atual da base de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Listar tabelas existentes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tabelas_existentes = [row[0] for row in cursor.fetchall()]
            
            print(f"Tabelas existentes ({len(tabelas_existentes)}):")
            for tabela in sorted(tabelas_existentes):
                cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                count = cursor.fetchone()[0]
                print(f"  - {tabela}: {count} registos")
            
            conn.close()
            return tabelas_existentes
            
        except sqlite3.Error as e:
            print(f"Erro ao verificar estrutura: {e}")
            return []
    
    def criar_schema_expandido(self):
        """Criar todas as tabelas do schema expandido"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ativar foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            print("Criando schema expandido...")
            
            # 1. Atualizar tabela de legislaturas
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS legislaturas_new (
                id INTEGER PRIMARY KEY,
                numero INTEGER NOT NULL UNIQUE,
                designacao TEXT NOT NULL,
                data_inicio DATE,
                data_fim DATE,
                ativa BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 2. Atualizar tabela de partidos
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS partidos_new (
                id INTEGER PRIMARY KEY,
                sigla TEXT NOT NULL,
                nome TEXT NOT NULL,
                designacao_completa TEXT,
                cor_hex TEXT,
                ativo BOOLEAN DEFAULT TRUE,
                data_fundacao DATE,
                ideologia TEXT,
                lider_parlamentar TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sigla)
            )
            """)
            
            # 3. Atualizar tabela de círculos eleitorais
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS circulos_eleitorais_new (
                id INTEGER PRIMARY KEY,
                designacao TEXT NOT NULL UNIQUE,
                codigo TEXT,
                regiao TEXT,
                distrito TEXT,
                num_deputados INTEGER DEFAULT 0,
                populacao INTEGER,
                area_km2 REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 4. Atualizar tabela de deputados
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS deputados_new (
                id INTEGER PRIMARY KEY,
                id_cadastro INTEGER NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                nome_completo TEXT,
                profissao TEXT,
                data_nascimento DATE,
                naturalidade TEXT,
                habilitacoes_academicas TEXT,
                biografia TEXT,
                foto_url TEXT,
                email TEXT,
                telefone TEXT,
                gabinete TEXT,
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 5. Atualizar tabela de mandatos
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS mandatos_new (
                id INTEGER PRIMARY KEY,
                deputado_id INTEGER NOT NULL,
                partido_id INTEGER NOT NULL,
                circulo_id INTEGER NOT NULL,
                legislatura_id INTEGER NOT NULL,
                data_inicio DATE NOT NULL,
                data_fim DATE,
                ativo BOOLEAN DEFAULT TRUE,
                posicao_lista INTEGER,
                votos_obtidos INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deputado_id) REFERENCES deputados (id),
                FOREIGN KEY (partido_id) REFERENCES partidos (id),
                FOREIGN KEY (circulo_id) REFERENCES circulos_eleitorais (id),
                FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
                UNIQUE(deputado_id, legislatura_id)
            )
            """)
            
            # 6. Criar tabelas de atividade parlamentar
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessoes_plenarias (
                id INTEGER PRIMARY KEY,
                legislatura_id INTEGER NOT NULL,
                numero_sessao INTEGER NOT NULL,
                data_sessao DATE NOT NULL,
                hora_inicio TIME,
                hora_fim TIME,
                tipo_sessao TEXT CHECK (tipo_sessao IN ('ordinaria', 'extraordinaria', 'solene')),
                estado TEXT DEFAULT 'agendada' CHECK (estado IN ('agendada', 'em_curso', 'concluida', 'cancelada')),
                ordem_trabalhos TEXT,
                resumo TEXT,
                presidente_sessao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
                UNIQUE(legislatura_id, numero_sessao, data_sessao)
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS atividades_parlamentares (
                id INTEGER PRIMARY KEY,
                id_externo INTEGER,
                legislatura_id INTEGER NOT NULL,
                sessao_plenaria_id INTEGER,
                tipo_atividade TEXT NOT NULL CHECK (tipo_atividade IN ('debate', 'votacao', 'audiencia', 'interpelacao', 'leitura', 'voto')),
                titulo TEXT NOT NULL,
                descricao TEXT,
                data_atividade DATE NOT NULL,
                hora_inicio TIME,
                hora_fim TIME,
                fase_sessao TEXT,
                estado TEXT DEFAULT 'agendada' CHECK (estado IN ('agendada', 'em_curso', 'concluida', 'cancelada')),
                resultado TEXT,
                observacoes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
                FOREIGN KEY (sessao_plenaria_id) REFERENCES sessoes_plenarias (id)
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS intervencoes (
                id INTEGER PRIMARY KEY,
                id_externo INTEGER UNIQUE,
                deputado_id INTEGER NOT NULL,
                atividade_id INTEGER,
                sessao_plenaria_id INTEGER,
                legislatura_id INTEGER NOT NULL,
                tipo_intervencao TEXT NOT NULL,
                data_intervencao DATE NOT NULL,
                qualidade TEXT,
                sumario TEXT,
                resumo TEXT,
                fase_sessao TEXT,
                duracao_segundos INTEGER,
                url_video TEXT,
                url_diario TEXT,
                pagina_diario TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deputado_id) REFERENCES deputados (id),
                FOREIGN KEY (atividade_id) REFERENCES atividades_parlamentares (id),
                FOREIGN KEY (sessao_plenaria_id) REFERENCES sessoes_plenarias (id),
                FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id)
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS iniciativas_legislativas (
                id INTEGER PRIMARY KEY,
                id_externo INTEGER UNIQUE,
                numero INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                tipo_descricao TEXT,
                legislatura_id INTEGER NOT NULL,
                sessao INTEGER,
                titulo TEXT NOT NULL,
                data_apresentacao DATE,
                texto_substituto BOOLEAN DEFAULT FALSE,
                url_texto TEXT,
                estado TEXT,
                resultado TEXT,
                observacoes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
                UNIQUE(numero, tipo, legislatura_id)
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS autores_iniciativas (
                id INTEGER PRIMARY KEY,
                iniciativa_id INTEGER NOT NULL,
                deputado_id INTEGER,
                partido_id INTEGER,
                tipo_autor TEXT CHECK (tipo_autor IN ('principal', 'subscritor', 'apresentante')),
                ordem INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_legislativas (id),
                FOREIGN KEY (deputado_id) REFERENCES deputados (id),
                FOREIGN KEY (partido_id) REFERENCES partidos (id),
                CHECK ((deputado_id IS NOT NULL) OR (partido_id IS NOT NULL))
            )
            """)
            
            # 7. Tabelas de agenda
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS agenda_parlamentar (
                id INTEGER PRIMARY KEY,
                id_externo INTEGER UNIQUE,
                legislatura_id INTEGER NOT NULL,
                secao_id INTEGER,
                secao_nome TEXT,
                tema_id INTEGER,
                tema_nome TEXT,
                grupo_parlamentar TEXT,
                data_evento DATE NOT NULL,
                hora_inicio TIME,
                hora_fim TIME,
                evento_dia_inteiro BOOLEAN DEFAULT FALSE,
                titulo TEXT NOT NULL,
                subtitulo TEXT,
                descricao TEXT,
                local_evento TEXT,
                link_externo TEXT,
                pos_plenario BOOLEAN DEFAULT FALSE,
                estado TEXT DEFAULT 'agendado' CHECK (estado IN ('agendado', 'em_curso', 'concluido', 'cancelado')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id)
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS eventos_iniciativas (
                id INTEGER PRIMARY KEY,
                iniciativa_id INTEGER NOT NULL,
                data_evento DATE NOT NULL,
                tipo_evento TEXT NOT NULL,
                descricao_evento TEXT,
                fase TEXT,
                resultado TEXT,
                observacoes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_legislativas (id)
            )
            """)
            
            # 8. Tabelas de votações
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS votacoes (
                id INTEGER PRIMARY KEY,
                iniciativa_id INTEGER,
                atividade_id INTEGER,
                sessao_plenaria_id INTEGER NOT NULL,
                legislatura_id INTEGER NOT NULL,
                numero_votacao INTEGER,
                data_votacao DATE NOT NULL,
                hora_votacao TIME,
                tipo_votacao TEXT CHECK (tipo_votacao IN ('nominal', 'secreta', 'por_divisao')),
                objeto_votacao TEXT NOT NULL,
                resultado TEXT CHECK (resultado IN ('aprovada', 'rejeitada', 'retirada')),
                votos_favor INTEGER DEFAULT 0,
                votos_contra INTEGER DEFAULT 0,
                abstencoes INTEGER DEFAULT 0,
                ausencias INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_legislativas (id),
                FOREIGN KEY (atividade_id) REFERENCES atividades_parlamentares (id),
                FOREIGN KEY (sessao_plenaria_id) REFERENCES sessoes_plenarias (id),
                FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id)
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS votos_individuais (
                id INTEGER PRIMARY KEY,
                votacao_id INTEGER NOT NULL,
                deputado_id INTEGER NOT NULL,
                voto TEXT NOT NULL CHECK (voto IN ('favor', 'contra', 'abstencao', 'ausente')),
                justificacao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (votacao_id) REFERENCES votacoes (id),
                FOREIGN KEY (deputado_id) REFERENCES deputados (id),
                UNIQUE(votacao_id, deputado_id)
            )
            """)
            
            # 9. Tabela de métricas
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS metricas_deputados (
                id INTEGER PRIMARY KEY,
                deputado_id INTEGER NOT NULL,
                legislatura_id INTEGER NOT NULL,
                periodo_inicio DATE NOT NULL,
                periodo_fim DATE NOT NULL,
                total_intervencoes INTEGER DEFAULT 0,
                total_iniciativas INTEGER DEFAULT 0,
                total_votacoes_participadas INTEGER DEFAULT 0,
                taxa_assiduidade REAL DEFAULT 0.0,
                tempo_total_intervencoes INTEGER DEFAULT 0,
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deputado_id) REFERENCES deputados (id),
                FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
                UNIQUE(deputado_id, legislatura_id, periodo_inicio, periodo_fim)
            )
            """)
            
            conn.commit()
            print("Schema expandido criado com sucesso")
            
            return True
            
        except sqlite3.Error as e:
            print(f"Erro ao criar schema expandido: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()
    
    def migrar_dados_existentes(self):
        """Migrar dados das tabelas antigas para as novas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("Migrando dados existentes...")
            
            # Verificar se existem dados para migrar
            tabelas_basicas = ['legislaturas', 'partidos', 'circulos_eleitorais', 'deputados', 'mandatos']
            dados_para_migrar = {}
            
            for tabela in tabelas_basicas:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                    count = cursor.fetchone()[0]
                    dados_para_migrar[tabela] = count
                    print(f"  {tabela}: {count} registos")
                except sqlite3.Error:
                    dados_para_migrar[tabela] = 0
                    print(f"  {tabela}: tabela nao existe")
            
            # Migrar legislaturas
            if dados_para_migrar.get('legislaturas', 0) > 0:
                cursor.execute("""
                INSERT INTO legislaturas_new (id, numero, designacao, data_inicio, data_fim, ativa, created_at, updated_at)
                SELECT id, CAST(REPLACE(numero, 'XVII', '17') AS INTEGER), designacao, 
                       data_inicio, data_fim, ativa, created_at, updated_at
                FROM legislaturas
                """)
                print("  Legislaturas migradas")
            
            # Migrar partidos
            if dados_para_migrar.get('partidos', 0) > 0:
                cursor.execute("""
                INSERT INTO partidos_new (id, sigla, nome, designacao_completa, cor_hex, ativo, 
                                        data_fundacao, ideologia, created_at, updated_at)
                SELECT id, sigla, designacao_completa, designacao_completa, cor_representativa, ativo,
                       data_constituicao, ideologia, created_at, updated_at
                FROM partidos
                """)
                print("  Partidos migrados")
            
            # Migrar círculos eleitorais
            if dados_para_migrar.get('circulos_eleitorais', 0) > 0:
                cursor.execute("""
                INSERT INTO circulos_eleitorais_new (id, designacao, regiao, distrito, num_deputados, created_at, updated_at)
                SELECT id, designacao, regiao, distrito, num_mandatos, created_at, updated_at
                FROM circulos_eleitorais
                """)
                print("  Circulos eleitorais migrados")
            
            # Migrar deputados
            if dados_para_migrar.get('deputados', 0) > 0:
                cursor.execute("""
                INSERT INTO deputados_new (id, id_cadastro, nome, nome_completo, profissao, data_nascimento,
                                         habilitacoes_academicas, foto_url, email, ativo, created_at, updated_at)
                SELECT id, id, nome_principal, nome_completo, profissao, data_nascimento,
                       habilitacoes_literarias, url_foto, email, ativo, created_at, updated_at
                FROM deputados
                """)
                print("  Deputados migrados")
            
            # Migrar mandatos
            if dados_para_migrar.get('mandatos', 0) > 0:
                cursor.execute("""
                INSERT INTO mandatos_new (id, deputado_id, partido_id, circulo_id, legislatura_id,
                                        data_inicio, data_fim, ativo, created_at, updated_at)
                SELECT id, deputado_id, partido_id, circulo_eleitoral_id, legislatura_id,
                       data_inicio, data_fim, ativo, created_at, updated_at
                FROM mandatos
                """)
                print("  Mandatos migrados")
            
            conn.commit()
            print("Migracao de dados concluida")
            
            return True
            
        except sqlite3.Error as e:
            print(f"Erro na migracao de dados: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()
    
    def substituir_tabelas_antigas(self):
        """Substituir tabelas antigas pelas novas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("Substituindo tabelas antigas...")
            
            # Desativar foreign keys temporariamente
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            tabelas_para_substituir = [
                'legislaturas', 'partidos', 'circulos_eleitorais', 'deputados', 'mandatos'
            ]
            
            for tabela in tabelas_para_substituir:
                # Verificar se tabela antiga existe
                cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{tabela}'
                """)
                
                if cursor.fetchone():
                    # Remover tabela antiga
                    cursor.execute(f"DROP TABLE IF EXISTS {tabela}")
                    print(f"  Removida tabela antiga: {tabela}")
                
                # Renomear tabela nova
                cursor.execute(f"ALTER TABLE {tabela}_new RENAME TO {tabela}")
                print(f"  Ativada nova tabela: {tabela}")
            
            # Reativar foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            conn.commit()
            print("Substituicao de tabelas concluida")
            
            return True
            
        except sqlite3.Error as e:
            print(f"Erro na substituicao de tabelas: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()
    
    def criar_indices(self):
        """Criar índices para otimização"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("Criando indices...")
            
            indices = [
                # Índices para consultas por deputado
                "CREATE INDEX IF NOT EXISTS idx_mandatos_deputado_legislatura ON mandatos(deputado_id, legislatura_id)",
                "CREATE INDEX IF NOT EXISTS idx_intervencoes_deputado_data ON intervencoes(deputado_id, data_intervencao)",
                "CREATE INDEX IF NOT EXISTS idx_votos_individuais_deputado ON votos_individuais(deputado_id, votacao_id)",
                
                # Índices para consultas por partido
                "CREATE INDEX IF NOT EXISTS idx_mandatos_partido_legislatura ON mandatos(partido_id, legislatura_id)",
                "CREATE INDEX IF NOT EXISTS idx_autores_iniciativas_partido ON autores_iniciativas(partido_id, iniciativa_id)",
                
                # Índices temporais
                "CREATE INDEX IF NOT EXISTS idx_agenda_data ON agenda_parlamentar(data_evento)",
                "CREATE INDEX IF NOT EXISTS idx_atividades_data ON atividades_parlamentares(data_atividade)",
                "CREATE INDEX IF NOT EXISTS idx_votacoes_data ON votacoes(data_votacao)",
                "CREATE INDEX IF NOT EXISTS idx_intervencoes_data ON intervencoes(data_intervencao)",
                
                # Índices para relações
                "CREATE INDEX IF NOT EXISTS idx_intervencoes_atividade ON intervencoes(atividade_id)",
                "CREATE INDEX IF NOT EXISTS idx_eventos_iniciativa ON eventos_iniciativas(iniciativa_id, data_evento)",
                "CREATE INDEX IF NOT EXISTS idx_atividades_legislatura ON atividades_parlamentares(legislatura_id)",
                "CREATE INDEX IF NOT EXISTS idx_iniciativas_legislatura ON iniciativas_legislativas(legislatura_id)",
                
                # Índices para consultas de agenda
                "CREATE INDEX IF NOT EXISTS idx_agenda_legislatura_data ON agenda_parlamentar(legislatura_id, data_evento)",
                "CREATE INDEX IF NOT EXISTS idx_agenda_grupo ON agenda_parlamentar(grupo_parlamentar)"
            ]
            
            for indice in indices:
                cursor.execute(indice)
            
            conn.commit()
            print(f"{len(indices)} indices criados")
            
            return True
            
        except sqlite3.Error as e:
            print(f"Erro ao criar indices: {e}")
            return False
            
        finally:
            conn.close()
    
    def criar_views(self):
        """Criar views para consultas comuns"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("Criando views...")
            
            # View para deputados completos
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_deputados_completos AS
            SELECT 
                d.id,
                d.id_cadastro,
                d.nome,
                d.profissao,
                p.sigla as partido_sigla,
                p.nome as partido_nome,
                ce.designacao as circulo,
                l.designacao as legislatura,
                m.ativo as mandato_ativo
            FROM deputados d
            JOIN mandatos m ON d.id = m.deputado_id
            JOIN partidos p ON m.partido_id = p.id
            JOIN circulos_eleitorais ce ON m.circulo_id = ce.id
            JOIN legislaturas l ON m.legislatura_id = l.id
            """)
            
            # View para atividade dos deputados
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_atividade_deputados AS
            SELECT 
                d.id as deputado_id,
                d.nome as deputado_nome,
                p.sigla as partido_sigla,
                COUNT(i.id) as total_intervencoes,
                COUNT(DISTINCT DATE(i.data_intervencao)) as dias_atividade,
                MAX(i.data_intervencao) as ultima_intervencao
            FROM deputados d
            LEFT JOIN mandatos m ON d.id = m.deputado_id AND m.ativo = TRUE
            LEFT JOIN partidos p ON m.partido_id = p.id
            LEFT JOIN intervencoes i ON d.id = i.deputado_id
            GROUP BY d.id, d.nome, p.sigla
            """)
            
            # View para agenda diária
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_agenda_diaria AS
            SELECT 
                a.data_evento,
                a.titulo,
                a.descricao,
                a.hora_inicio,
                a.hora_fim,
                a.grupo_parlamentar,
                a.local_evento,
                a.estado,
                l.designacao as legislatura
            FROM agenda_parlamentar a
            JOIN legislaturas l ON a.legislatura_id = l.id
            ORDER BY a.data_evento, a.hora_inicio
            """)
            
            conn.commit()
            print("Views criadas")
            
            return True
            
        except sqlite3.Error as e:
            print(f"Erro ao criar views: {e}")
            return False
            
        finally:
            conn.close()
    
    def criar_triggers(self):
        """Criar triggers para manutenção automática"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("Criando triggers...")
            
            # Triggers para atualizar timestamp
            triggers = [
                """
                CREATE TRIGGER IF NOT EXISTS update_deputados_timestamp 
                    AFTER UPDATE ON deputados
                BEGIN
                    UPDATE deputados SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
                """,
                """
                CREATE TRIGGER IF NOT EXISTS update_partidos_timestamp 
                    AFTER UPDATE ON partidos
                BEGIN
                    UPDATE partidos SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
                """,
                """
                CREATE TRIGGER IF NOT EXISTS update_mandatos_timestamp 
                    AFTER UPDATE ON mandatos
                BEGIN
                    UPDATE mandatos SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
                """
            ]
            
            for trigger in triggers:
                cursor.execute(trigger)
            
            conn.commit()
            print(f"{len(triggers)} triggers criados")
            
            return True
            
        except sqlite3.Error as e:
            print(f"Erro ao criar triggers: {e}")
            return False
            
        finally:
            conn.close()
    
    def verificar_implementacao(self):
        """Verificar se a implementação foi bem-sucedida"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("Verificando implementacao...")
            
            # Contar tabelas
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            total_tabelas = cursor.fetchone()[0]
            
            # Contar views
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
            total_views = cursor.fetchone()[0]
            
            # Contar triggers
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'")
            total_triggers = cursor.fetchone()[0]
            
            # Contar índices
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
            total_indices = cursor.fetchone()[0]
            
            print(f"Resultados da implementacao:")
            print(f"  Tabelas: {total_tabelas}")
            print(f"  Views: {total_views}")
            print(f"  Triggers: {total_triggers}")
            print(f"  Indices: {total_indices}")
            
            # Verificar integridade das foreign keys
            cursor.execute("PRAGMA foreign_key_check")
            fk_errors = cursor.fetchall()
            
            if fk_errors:
                print(f"Encontrados {len(fk_errors)} erros de foreign key")
                for error in fk_errors:
                    print(f"    {error}")
            else:
                print("Integridade referencial verificada")
            
            conn.close()
            return total_tabelas >= 15  # Esperamos pelo menos 15 tabelas
            
        except sqlite3.Error as e:
            print(f"Erro na verificacao: {e}")
            return False
    
    def executar_implementacao_completa(self):
        """Executar implementação completa do schema expandido"""
        print("INICIANDO IMPLEMENTACAO DO SCHEMA EXPANDIDO")
        print("=" * 60)
        
        # Passo 1: Fazer backup
        if not self.fazer_backup():
            print("Falha no backup - implementacao cancelada")
            return False
        
        # Passo 2: Verificar estrutura atual
        tabelas_existentes = self.verificar_estrutura_atual()
        
        # Passo 3: Criar schema expandido
        if not self.criar_schema_expandido():
            print("Falha na criacao do schema - implementacao cancelada")
            return False
        
        # Passo 4: Migrar dados existentes (se houver)
        if tabelas_existentes:
            if not self.migrar_dados_existentes():
                print("Falha na migracao de dados")
                return False
            
            # Passo 5: Substituir tabelas antigas
            if not self.substituir_tabelas_antigas():
                print("Falha na substituicao de tabelas")
                return False
        else:
            # Se não há tabelas existentes, renomear as novas tabelas
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = OFF")
                
                tabelas_para_renomear = [
                    'legislaturas', 'partidos', 'circulos_eleitorais', 'deputados', 'mandatos'
                ]
                
                for tabela in tabelas_para_renomear:
                    try:
                        cursor.execute(f"ALTER TABLE {tabela}_new RENAME TO {tabela}")
                        print(f"  Ativada nova tabela: {tabela}")
                    except sqlite3.Error:
                        pass  # Tabela pode não existir
                
                cursor.execute("PRAGMA foreign_keys = ON")
                conn.commit()
                conn.close()
                print("Tabelas ativadas")
            except sqlite3.Error as e:
                print(f"Erro ao ativar tabelas: {e}")
                return False
        
        # Passo 6: Criar índices
        if not self.criar_indices():
            print("Falha na criacao de indices")
            return False
        
        # Passo 7: Criar views
        if not self.criar_views():
            print("Falha na criacao de views")
            return False
        
        # Passo 8: Criar triggers
        if not self.criar_triggers():
            print("Falha na criacao de triggers")
            return False
        
        # Passo 9: Verificar implementação
        if not self.verificar_implementacao():
            print("Verificacao falhou")
            return False
        
        print("=" * 60)
        print("IMPLEMENTACAO DO SCHEMA EXPANDIDO CONCLUIDA COM SUCESSO!")
        print(f"Backup disponivel em: {self.backup_path}")
        
        return True

def main():
    """Função principal"""
    implementador = ImplementadorSchemaExpandido()
    sucesso = implementador.executar_implementacao_completa()
    
    if sucesso:
        print("\nSchema expandido implementado com sucesso!")
        print("Próximos passos:")
        print("1. Atualizar modelos SQLAlchemy")
        print("2. Criar importadores de XML")
        print("3. Importar dados dos arquivos XML")
        sys.exit(0)
    else:
        print("\nImplementacao falhou!")
        sys.exit(1)

if __name__ == "__main__":
    main()