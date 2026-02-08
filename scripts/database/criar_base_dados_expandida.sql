-- =====================================================
-- ESQUEMA EXPANDIDO DA BASE DE DADOS - PARLAMENTO PORTUGUÊS
-- Versão 2.0 - Esquema Relacional Completo
-- Autor: Manus AI
-- Data: 25 de julho de 2025
-- =====================================================

-- Ativar foreign keys
PRAGMA foreign_keys = ON;

-- =====================================================
-- TABELAS PRINCIPAIS
-- =====================================================

-- Tabela de legislaturas
CREATE TABLE IF NOT EXISTS legislaturas (
    id INTEGER PRIMARY KEY,
    numero INTEGER NOT NULL UNIQUE,
    designacao TEXT NOT NULL,
    data_inicio DATE,
    data_fim DATE,
    ativa BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de partidos (expandida)
CREATE TABLE IF NOT EXISTS partidos (
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
);

-- Tabela de círculos eleitorais (expandida)
CREATE TABLE IF NOT EXISTS circulos_eleitorais (
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
);

-- Tabela de deputados (expandida)
CREATE TABLE IF NOT EXISTS deputados (
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
);

-- Tabela de mandatos (mantida compatível)
CREATE TABLE IF NOT EXISTS mandatos (
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
);

-- =====================================================
-- TABELAS DE ATIVIDADE PARLAMENTAR
-- =====================================================

-- Tabela de sessões plenárias
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
);

-- Tabela central de atividades parlamentares
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
);

-- Tabela de intervenções
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
);

-- Tabela de iniciativas legislativas
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
);

-- Tabela de autores de iniciativas
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
);

-- =====================================================
-- TABELAS DE AGENDA E EVENTOS
-- =====================================================

-- Tabela de agenda parlamentar
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
);

-- Tabela de eventos de iniciativas
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
);

-- =====================================================
-- TABELAS DE VOTAÇÕES (PREPARAÇÃO FUTURA)
-- =====================================================

-- Tabela de votações
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
);

-- Tabela de votos individuais
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
);

-- =====================================================
-- TABELAS DE ANÁLISE E MÉTRICAS
-- =====================================================

-- Tabela de métricas dos deputados
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
);

-- =====================================================
-- ÍNDICES PARA OTIMIZAÇÃO
-- =====================================================

-- Índices para consultas por deputado
CREATE INDEX IF NOT EXISTS idx_mandatos_deputado_legislatura ON mandatos(deputado_id, legislatura_id);
CREATE INDEX IF NOT EXISTS idx_intervencoes_deputado_data ON intervencoes(deputado_id, data_intervencao);
CREATE INDEX IF NOT EXISTS idx_votos_individuais_deputado ON votos_individuais(deputado_id, votacao_id);

-- Índices para consultas por partido
CREATE INDEX IF NOT EXISTS idx_mandatos_partido_legislatura ON mandatos(partido_id, legislatura_id);
CREATE INDEX IF NOT EXISTS idx_autores_iniciativas_partido ON autores_iniciativas(partido_id, iniciativa_id);

-- Índices temporais
CREATE INDEX IF NOT EXISTS idx_agenda_data ON agenda_parlamentar(data_evento);
CREATE INDEX IF NOT EXISTS idx_atividades_data ON atividades_parlamentares(data_atividade);
CREATE INDEX IF NOT EXISTS idx_votacoes_data ON votacoes(data_votacao);
CREATE INDEX IF NOT EXISTS idx_intervencoes_data ON intervencoes(data_intervencao);

-- Índices para relações
CREATE INDEX IF NOT EXISTS idx_intervencoes_atividade ON intervencoes(atividade_id);
CREATE INDEX IF NOT EXISTS idx_eventos_iniciativa ON eventos_iniciativas(iniciativa_id, data_evento);
CREATE INDEX IF NOT EXISTS idx_atividades_legislatura ON atividades_parlamentares(legislatura_id);
CREATE INDEX IF NOT EXISTS idx_iniciativas_legislatura ON iniciativas_legislativas(legislatura_id);

-- Índices para consultas de agenda
CREATE INDEX IF NOT EXISTS idx_agenda_legislatura_data ON agenda_parlamentar(legislatura_id, data_evento);
CREATE INDEX IF NOT EXISTS idx_agenda_grupo ON agenda_parlamentar(grupo_parlamentar);

-- =====================================================
-- DADOS INICIAIS
-- =====================================================

-- Inserir legislatura atual
INSERT OR IGNORE INTO legislaturas (numero, designacao, ativa) 
VALUES (17, 'XVII Legislatura', TRUE);

-- =====================================================
-- VIEWS PARA CONSULTAS COMUNS
-- =====================================================

-- View para deputados com informação completa
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
JOIN legislaturas l ON m.legislatura_id = l.id;

-- View para atividade dos deputados
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
GROUP BY d.id, d.nome, p.sigla;

-- View para agenda diária
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
ORDER BY a.data_evento, a.hora_inicio;

-- =====================================================
-- TRIGGERS PARA MANUTENÇÃO AUTOMÁTICA
-- =====================================================

-- Trigger para atualizar timestamp de updated_at
CREATE TRIGGER IF NOT EXISTS update_deputados_timestamp 
    AFTER UPDATE ON deputados
BEGIN
    UPDATE deputados SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_partidos_timestamp 
    AFTER UPDATE ON partidos
BEGIN
    UPDATE partidos SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_mandatos_timestamp 
    AFTER UPDATE ON mandatos
BEGIN
    UPDATE mandatos SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- =====================================================
-- COMENTÁRIOS FINAIS
-- =====================================================

-- Este esquema expandido fornece:
-- 1. Compatibilidade com o sistema existente
-- 2. Estrutura para navegação hierárquica (Partido → Deputados → Atividades)
-- 3. Suporte para agenda diária e votações
-- 4. Métricas e análises avançadas
-- 5. Extensibilidade para futuras funcionalidades

-- Para migrar dados existentes, executar:
-- 1. Este script em nova base de dados
-- 2. Script de migração dos dados atuais
-- 3. Script de importação dos novos dados XML

