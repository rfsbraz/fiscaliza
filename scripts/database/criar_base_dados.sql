-- Script para criação da base de dados do Parlamento Português
-- Versão: 1.0
-- Data: 28 de Julho de 2025

-- Habilitar chaves estrangeiras
PRAGMA foreign_keys = ON;

-- Tabela de Legislaturas
CREATE TABLE IF NOT EXISTS legislaturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero VARCHAR(10) NOT NULL UNIQUE,
    designacao VARCHAR(100) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE,
    ativa BOOLEAN DEFAULT FALSE,
    observacoes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Partidos
CREATE TABLE IF NOT EXISTS partidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sigla VARCHAR(20) NOT NULL UNIQUE,
    designacao_completa VARCHAR(200) NOT NULL,
    data_constituicao DATE,
    cor_representativa VARCHAR(7),
    ideologia VARCHAR(50),
    ativo BOOLEAN DEFAULT TRUE,
    observacoes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Círculos Eleitorais
CREATE TABLE IF NOT EXISTS circulos_eleitorais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    designacao VARCHAR(100) NOT NULL UNIQUE,
    tipo VARCHAR(20) DEFAULT 'territorial',
    distrito VARCHAR(50),
    regiao VARCHAR(50),
    num_mandatos INTEGER DEFAULT 0,
    observacoes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Deputados
CREATE TABLE IF NOT EXISTS deputados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo VARCHAR(200) NOT NULL,
    nome_principal VARCHAR(100) NOT NULL,
    sexo CHAR(1) CHECK (sexo IN ('M', 'F')),
    data_nascimento DATE,
    profissao VARCHAR(100),
    habilitacoes_literarias VARCHAR(200),
    url_foto VARCHAR(500),
    email VARCHAR(100),
    observacoes TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Mandatos (relação deputado-partido-círculo-legislatura)
CREATE TABLE IF NOT EXISTS mandatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deputado_id INTEGER NOT NULL,
    partido_id INTEGER NOT NULL,
    circulo_eleitoral_id INTEGER NOT NULL,
    legislatura_id INTEGER NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE,
    ativo BOOLEAN DEFAULT TRUE,
    observacoes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deputado_id) REFERENCES deputados(id),
    FOREIGN KEY (partido_id) REFERENCES partidos(id),
    FOREIGN KEY (circulo_eleitoral_id) REFERENCES circulos_eleitorais(id),
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas(id),
    UNIQUE(deputado_id, legislatura_id)
);

-- Tabela de Agenda Parlamentar
CREATE TABLE IF NOT EXISTS agenda_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo VARCHAR(500) NOT NULL,
    descricao TEXT,
    data_evento DATE NOT NULL,
    hora_inicio TIME,
    hora_fim TIME,
    local VARCHAR(200),
    tipo_evento VARCHAR(50),
    estado VARCHAR(20) DEFAULT 'agendado',
    observacoes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Índices para otimização de consultas
CREATE INDEX IF NOT EXISTS idx_deputados_nome ON deputados(nome_principal);
CREATE INDEX IF NOT EXISTS idx_deputados_ativo ON deputados(ativo);
CREATE INDEX IF NOT EXISTS idx_partidos_sigla ON partidos(sigla);
CREATE INDEX IF NOT EXISTS idx_partidos_ativo ON partidos(ativo);
CREATE INDEX IF NOT EXISTS idx_mandatos_deputado ON mandatos(deputado_id);
CREATE INDEX IF NOT EXISTS idx_mandatos_partido ON mandatos(partido_id);
CREATE INDEX IF NOT EXISTS idx_mandatos_circulo ON mandatos(circulo_eleitoral_id);
CREATE INDEX IF NOT EXISTS idx_mandatos_legislatura ON mandatos(legislatura_id);
CREATE INDEX IF NOT EXISTS idx_mandatos_ativo ON mandatos(ativo);
CREATE INDEX IF NOT EXISTS idx_agenda_data ON agenda_eventos(data_evento);
CREATE INDEX IF NOT EXISTS idx_agenda_tipo ON agenda_eventos(tipo_evento);

-- Inserir legislatura atual
INSERT OR IGNORE INTO legislaturas (numero, designacao, data_inicio, ativa) 
VALUES ('XVII', 'XVII Legislatura', '2025-06-03', TRUE);

-- Logs de criação
-- Base de dados criada com sucesso!