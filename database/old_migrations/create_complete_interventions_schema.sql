-- Complete normalized schema for parliamentary interventions
-- Based on actual XML structure analysis

-- Drop existing intervencoes table to recreate with proper structure
DROP TABLE IF EXISTS intervencoes;

-- Main interventions table
CREATE TABLE intervencoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_externo INTEGER NOT NULL UNIQUE, -- XML Id field
    legislatura_numero TEXT NOT NULL, -- XML Legislatura field
    sessao_numero TEXT, -- XML Sessao field
    tipo_intervencao TEXT NOT NULL, -- XML TipoIntervencao field
    data_reuniao_plenaria DATE NOT NULL, -- XML DataReuniaoPlenaria field
    qualidade TEXT, -- XML Qualidade field (Deputado, P.A.R., etc.)
    fase_sessao TEXT, -- XML FaseSessao field
    sumario TEXT, -- XML Sumario field  
    resumo TEXT, -- XML Resumo field
    atividade_id INTEGER, -- XML ActividadeId field
    id_debate INTEGER, -- XML IdDebate field
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Publications table (normalized from XML Publicacao element)
CREATE TABLE intervencoes_publicacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intervencao_id INTEGER NOT NULL,
    pub_numero TEXT, -- pubNr
    pub_tipo TEXT, -- pubTipo (e.g., "DAR I série")
    pub_tp TEXT, -- pubTp (e.g., "D")
    pub_legislatura TEXT, -- pubLeg
    pub_serie_legislatura TEXT, -- pubSL  
    pub_data DATE, -- pubdt
    paginas TEXT, -- pag/string content
    id_interno INTEGER, -- idInt
    url_diario TEXT, -- URLDiario
    FOREIGN KEY (intervencao_id) REFERENCES intervencoes(id) ON DELETE CASCADE
);

-- Deputies table for interventions (normalized from XML Deputados element)
CREATE TABLE intervencoes_deputados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intervencao_id INTEGER NOT NULL,
    id_cadastro INTEGER, -- idCadastro
    nome TEXT, -- nome
    grupo_parlamentar TEXT, -- GP
    FOREIGN KEY (intervencao_id) REFERENCES intervencoes(id) ON DELETE CASCADE
);

-- Government members table (normalized from XML MembrosGoverno element)
CREATE TABLE intervencoes_membros_governo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intervencao_id INTEGER NOT NULL,
    nome TEXT,
    cargo TEXT,
    governo TEXT,
    FOREIGN KEY (intervencao_id) REFERENCES intervencoes(id) ON DELETE CASCADE
);

-- Invited guests table (normalized from XML Convidados element)
CREATE TABLE intervencoes_convidados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intervencao_id INTEGER NOT NULL,
    nome TEXT,
    cargo TEXT,
    FOREIGN KEY (intervencao_id) REFERENCES intervencoes(id) ON DELETE CASCADE
);

-- Related activities table (normalized from XML ActividadesRelacionadas element)
CREATE TABLE intervencoes_atividades_relacionadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intervencao_id INTEGER NOT NULL,
    atividade_id INTEGER, -- id field
    tipo TEXT, -- tipo field
    FOREIGN KEY (intervencao_id) REFERENCES intervencoes(id) ON DELETE CASCADE
);

-- Initiatives table (normalized from XML Iniciativas element)
CREATE TABLE intervencoes_iniciativas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intervencao_id INTEGER NOT NULL,
    iniciativa_id INTEGER, -- id field
    tipo TEXT, -- tipo field
    fase TEXT, -- fase field
    FOREIGN KEY (intervencao_id) REFERENCES intervencoes(id) ON DELETE CASCADE
);

-- Audiovisual data table (for video/audio content)
CREATE TABLE intervencoes_audiovisual (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intervencao_id INTEGER NOT NULL,
    url_video TEXT,
    thumbnail_url TEXT,
    duracao TEXT,
    assunto TEXT,
    tipo_intervencao TEXT,
    FOREIGN KEY (intervencao_id) REFERENCES intervencoes(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_intervencoes_legislatura ON intervencoes(legislatura_numero);
CREATE INDEX idx_intervencoes_data ON intervencoes(data_reuniao_plenaria);
CREATE INDEX idx_intervencoes_tipo ON intervencoes(tipo_intervencao);
CREATE INDEX idx_intervencoes_atividade ON intervencoes(atividade_id);
CREATE INDEX idx_intervencoes_debate ON intervencoes(id_debate);

CREATE INDEX idx_publicacoes_intervencao ON intervencoes_publicacoes(intervencao_id);
CREATE INDEX idx_deputados_intervencao ON intervencoes_deputados(intervencao_id);
CREATE INDEX idx_deputados_cadastro ON intervencoes_deputados(id_cadastro);
CREATE INDEX idx_governo_intervencao ON intervencoes_membros_governo(intervencao_id);
CREATE INDEX idx_convidados_intervencao ON intervencoes_convidados(intervencao_id);
CREATE INDEX idx_atividades_rel_intervencao ON intervencoes_atividades_relacionadas(intervencao_id);
CREATE INDEX idx_iniciativas_intervencao ON intervencoes_iniciativas(intervencao_id);
CREATE INDEX idx_audiovisual_intervencao ON intervencoes_audiovisual(intervencao_id);

-- Create update trigger
CREATE TRIGGER update_intervencoes_timestamp 
    AFTER UPDATE ON intervencoes
    FOR EACH ROW
BEGIN
    UPDATE intervencoes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;