#!/usr/bin/env python3
"""
Adicionar Tabelas Especializadas - Parlamento Português
Script para adicionar as 7 tabelas especializadas em falta
"""

import sqlite3
import os

def adicionar_tabelas_especializadas():
    """Adicionar as 7 tabelas especializadas em falta"""
    
    db_path = 'parlamento.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Adicionando tabelas especializadas...")
        
        # 1. Tabela de Comissões
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comissoes (
            id INTEGER PRIMARY KEY,
            id_externo INTEGER UNIQUE,
            legislatura_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            sigla TEXT,
            tipo TEXT CHECK (tipo IN ('permanente', 'eventual', 'sub_comissao')),
            data_constituicao DATE,
            data_extincao DATE,
            presidente TEXT,
            vice_presidente TEXT,
            secretario TEXT,
            competencias TEXT,
            ativa BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id)
        )
        """)
        
        # 2. Tabela de Membros de Comissões
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS membros_comissoes (
            id INTEGER PRIMARY KEY,
            comissao_id INTEGER NOT NULL,
            deputado_id INTEGER NOT NULL,
            cargo TEXT CHECK (cargo IN ('presidente', 'vice_presidente', 'secretario', 'membro')),
            data_inicio DATE NOT NULL,
            data_fim DATE,
            titular BOOLEAN DEFAULT TRUE,
            observacoes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (comissao_id) REFERENCES comissoes (id),
            FOREIGN KEY (deputado_id) REFERENCES deputados (id),
            UNIQUE(comissao_id, deputado_id, data_inicio)
        )
        """)
        
        # 3. Tabela de Petições
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS peticoes (
            id INTEGER PRIMARY KEY,
            id_externo INTEGER UNIQUE,
            legislatura_id INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            tipo TEXT,
            titulo TEXT NOT NULL,
            data_entrada DATE NOT NULL,
            data_admissao DATE,
            primeiro_peticionario TEXT,
            numero_subscritores INTEGER DEFAULT 0,
            objeto TEXT,
            comissao_id INTEGER,
            estado TEXT DEFAULT 'entrada' CHECK (estado IN ('entrada', 'admitida', 'rejeitada', 'processamento', 'concluida')),
            resultado TEXT,
            observacoes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
            FOREIGN KEY (comissao_id) REFERENCES comissoes (id),
            UNIQUE(numero, legislatura_id)
        )
        """)
        
        # 4. Tabela de Delegações
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS delegacoes (
            id INTEGER PRIMARY KEY,
            legislatura_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            pais_destino TEXT,
            organizacao TEXT,
            data_inicio DATE,
            data_fim DATE,
            objetivo TEXT,
            tipo TEXT CHECK (tipo IN ('oficial', 'trabalho', 'cortesia', 'protocolar')),
            estado TEXT DEFAULT 'planeada' CHECK (estado IN ('planeada', 'em_curso', 'concluida', 'cancelada')),
            relatorio_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id)
        )
        """)
        
        # 5. Tabela de Membros de Delegações
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS membros_delegacoes (
            id INTEGER PRIMARY KEY,
            delegacao_id INTEGER NOT NULL,
            deputado_id INTEGER NOT NULL,
            cargo TEXT CHECK (cargo IN ('chefe', 'vice_chefe', 'membro')),
            observacoes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (delegacao_id) REFERENCES delegacoes (id),
            FOREIGN KEY (deputado_id) REFERENCES deputados (id),
            UNIQUE(delegacao_id, deputado_id)
        )
        """)
        
        # 6. Tabela de Audições
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audicoes (
            id INTEGER PRIMARY KEY,
            id_externo INTEGER UNIQUE,
            legislatura_id INTEGER NOT NULL,
            comissao_id INTEGER,
            data_audicao DATE NOT NULL,
            hora_inicio TIME,
            hora_fim TIME,
            titulo TEXT NOT NULL,
            tipo TEXT CHECK (tipo IN ('parlamentar', 'publica', 'especialista', 'governamental')),
            entidade_ouvida TEXT,
            representante TEXT,
            assunto TEXT,
            local_evento TEXT,
            estado TEXT DEFAULT 'agendada' CHECK (estado IN ('agendada', 'realizada', 'cancelada')),
            ata_url TEXT,
            video_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
            FOREIGN KEY (comissao_id) REFERENCES comissoes (id)
        )
        """)
        
        # 7. Tabela de Perguntas e Requerimentos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS perguntas_requerimentos (
            id INTEGER PRIMARY KEY,
            id_externo INTEGER UNIQUE,
            legislatura_id INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('pergunta', 'requerimento', 'interpelacao')),
            modalidade TEXT,
            deputado_id INTEGER NOT NULL,
            partido_id INTEGER,
            data_apresentacao DATE NOT NULL,
            data_resposta DATE,
            titulo TEXT NOT NULL,
            destinatario TEXT,
            assunto TEXT,
            texto_pergunta TEXT,
            texto_resposta TEXT,
            estado TEXT DEFAULT 'apresentada' CHECK (estado IN ('apresentada', 'respondida', 'sem_resposta', 'retirada')),
            url_documento TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
            FOREIGN KEY (deputado_id) REFERENCES deputados (id),
            FOREIGN KEY (partido_id) REFERENCES partidos (id),
            UNIQUE(numero, tipo, legislatura_id)
        )
        """)
        
        print("Tabelas especializadas criadas:")
        print("  - comissoes")
        print("  - membros_comissoes") 
        print("  - peticoes")
        print("  - delegacoes")
        print("  - membros_delegacoes")
        print("  - audicoes")
        print("  - perguntas_requerimentos")
        
        # Criar índices para as novas tabelas
        print("\nCriando indices para tabelas especializadas...")
        
        indices_especializados = [
            "CREATE INDEX IF NOT EXISTS idx_comissoes_legislatura ON comissoes(legislatura_id)",
            "CREATE INDEX IF NOT EXISTS idx_comissoes_ativa ON comissoes(ativa)",
            "CREATE INDEX IF NOT EXISTS idx_membros_comissoes_deputado ON membros_comissoes(deputado_id)",
            "CREATE INDEX IF NOT EXISTS idx_membros_comissoes_comissao ON membros_comissoes(comissao_id)",
            "CREATE INDEX IF NOT EXISTS idx_peticoes_legislatura ON peticoes(legislatura_id)",
            "CREATE INDEX IF NOT EXISTS idx_peticoes_estado ON peticoes(estado)",
            "CREATE INDEX IF NOT EXISTS idx_peticoes_data ON peticoes(data_entrada)",
            "CREATE INDEX IF NOT EXISTS idx_delegacoes_legislatura ON delegacoes(legislatura_id)",
            "CREATE INDEX IF NOT EXISTS idx_delegacoes_data ON delegacoes(data_inicio)",
            "CREATE INDEX IF NOT EXISTS idx_membros_delegacoes_deputado ON membros_delegacoes(deputado_id)",
            "CREATE INDEX IF NOT EXISTS idx_audicoes_legislatura ON audicoes(legislatura_id)",
            "CREATE INDEX IF NOT EXISTS idx_audicoes_comissao ON audicoes(comissao_id)",
            "CREATE INDEX IF NOT EXISTS idx_audicoes_data ON audicoes(data_audicao)",
            "CREATE INDEX IF NOT EXISTS idx_perguntas_legislatura ON perguntas_requerimentos(legislatura_id)",
            "CREATE INDEX IF NOT EXISTS idx_perguntas_deputado ON perguntas_requerimentos(deputado_id)",
            "CREATE INDEX IF NOT EXISTS idx_perguntas_tipo ON perguntas_requerimentos(tipo)",
            "CREATE INDEX IF NOT EXISTS idx_perguntas_data ON perguntas_requerimentos(data_apresentacao)"
        ]
        
        for indice in indices_especializados:
            cursor.execute(indice)
        
        print(f"  {len(indices_especializados)} indices criados")
        
        # Criar views especializadas
        print("\nCriando views especializadas...")
        
        # View para composição de comissões
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS v_composicao_comissoes AS
        SELECT 
            c.nome as comissao_nome,
            c.sigla as comissao_sigla,
            d.nome as deputado_nome,
            p.sigla as partido_sigla,
            mc.cargo,
            mc.titular,
            mc.data_inicio,
            mc.data_fim,
            l.designacao as legislatura
        FROM comissoes c
        JOIN membros_comissoes mc ON c.id = mc.comissao_id
        JOIN deputados d ON mc.deputado_id = d.id
        JOIN mandatos m ON d.id = m.deputado_id AND m.ativo = TRUE
        JOIN partidos p ON m.partido_id = p.id
        JOIN legislaturas l ON c.legislatura_id = l.id
        WHERE c.ativa = TRUE
        ORDER BY c.nome, mc.cargo, d.nome
        """)
        
        # View para atividade das comissões
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS v_atividade_comissoes AS
        SELECT 
            c.id as comissao_id,
            c.nome as comissao_nome,
            COUNT(DISTINCT mc.deputado_id) as total_membros,
            COUNT(DISTINCT a.id) as total_audicoes,
            COUNT(DISTINCT p.id) as total_peticoes,
            MAX(a.data_audicao) as ultima_audicao,
            l.designacao as legislatura
        FROM comissoes c
        LEFT JOIN membros_comissoes mc ON c.id = mc.comissao_id AND mc.data_fim IS NULL
        LEFT JOIN audicoes a ON c.id = a.comissao_id
        LEFT JOIN peticoes p ON c.id = p.comissao_id
        JOIN legislaturas l ON c.legislatura_id = l.id
        WHERE c.ativa = TRUE
        GROUP BY c.id, c.nome, l.designacao
        ORDER BY c.nome
        """)
        
        print("  Views especializadas criadas")
        
        conn.commit()
        
        # Verificar resultado final
        print("\nVerificando implementacao final...")
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        total_tabelas = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
        total_views = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
        total_indices = cursor.fetchone()[0]
        
        print(f"Resultados finais:")
        print(f"  Total de tabelas: {total_tabelas}")
        print(f"  Total de views: {total_views}")
        print(f"  Total de indices: {total_indices}")
        
        conn.close()
        
        print("\nTABELAS ESPECIALIZADAS ADICIONADAS COM SUCESSO!")
        return True
        
    except sqlite3.Error as e:
        print(f"Erro ao adicionar tabelas especializadas: {e}")
        return False

if __name__ == "__main__":
    adicionar_tabelas_especializadas()