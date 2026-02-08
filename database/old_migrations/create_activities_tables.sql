-- Create activities tables for parliamentary activities data

-- Main activities table
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL UNIQUE,
    tipo TEXT,
    desc_tipo TEXT,
    assunto TEXT,
    legislatura TEXT,
    sessao TEXT,
    numero TEXT,
    data_entrada DATE,
    data_agendamento_debate DATE,
    orgao_exterior TEXT,
    observacoes TEXT,
    tipo_autor TEXT,
    import_source TEXT DEFAULT 'atividades',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Activity votes table
CREATE TABLE IF NOT EXISTS activity_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL,
    vote_id TEXT,
    resultado TEXT,
    reuniao TEXT,
    unanime TEXT,
    data_votacao DATE,
    descricao TEXT,
    import_source TEXT DEFAULT 'atividades',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
);

-- Activity participants table (authors, elected officials, guests)
CREATE TABLE IF NOT EXISTS activity_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL,
    nome TEXT,
    cargo TEXT,
    pais TEXT,
    honra TEXT,
    tipo_participacao TEXT, -- 'autor_gp', 'eleito', 'convidado'
    import_source TEXT DEFAULT 'atividades',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
);

-- Activity publications table
CREATE TABLE IF NOT EXISTS activity_publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL,
    pub_nr TEXT,
    pub_tipo TEXT,
    pub_data DATE,
    url_diario TEXT,
    legislatura TEXT,
    import_source TEXT DEFAULT 'atividades',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_activities_tipo ON activities(tipo);
CREATE INDEX IF NOT EXISTS idx_activities_legislatura ON activities(legislatura);
CREATE INDEX IF NOT EXISTS idx_activities_data_entrada ON activities(data_entrada);
CREATE INDEX IF NOT EXISTS idx_activities_orgao_exterior ON activities(orgao_exterior);

CREATE INDEX IF NOT EXISTS idx_activity_votes_activity_id ON activity_votes(activity_id);
CREATE INDEX IF NOT EXISTS idx_activity_votes_data_votacao ON activity_votes(data_votacao);
CREATE INDEX IF NOT EXISTS idx_activity_votes_resultado ON activity_votes(resultado);

CREATE INDEX IF NOT EXISTS idx_activity_participants_activity_id ON activity_participants(activity_id);
CREATE INDEX IF NOT EXISTS idx_activity_participants_nome ON activity_participants(nome);
CREATE INDEX IF NOT EXISTS idx_activity_participants_tipo ON activity_participants(tipo_participacao);

CREATE INDEX IF NOT EXISTS idx_activity_publications_activity_id ON activity_publications(activity_id);
CREATE INDEX IF NOT EXISTS idx_activity_publications_tipo ON activity_publications(pub_tipo);