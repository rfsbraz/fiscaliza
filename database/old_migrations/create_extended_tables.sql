-- Extended tables for new entity types from parliament data

-- Deputies extended information
CREATE TABLE IF NOT EXISTS deputies_extended (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    cadastro_id TEXT,
    nome_parlamentar TEXT,
    nome_completo TEXT,
    legislatura TEXT,
    circulo_id TEXT,
    circulo_descricao TEXT,
    import_source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Initiatives extended information
CREATE TABLE IF NOT EXISTS initiatives_extended (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    numero TEXT,
    tipo TEXT,
    tipo_descricao TEXT,
    legislatura TEXT,
    sessao TEXT,
    titulo TEXT,
    deputy_id TEXT,
    import_source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deputy_id) REFERENCES deputies_extended(source_id)
);

-- Interventions extended information
CREATE TABLE IF NOT EXISTS interventions_extended (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    titulo TEXT,
    assunto TEXT,
    data_publicacao TEXT,
    tipo_publicacao TEXT,
    legislatura TEXT,
    sessao TEXT,
    numero TEXT,
    tipo_intervencao TEXT,
    paginas_dar TEXT,
    deputy_id TEXT,
    import_source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deputy_id) REFERENCES deputies_extended(source_id)
);

-- Commissions extended information
CREATE TABLE IF NOT EXISTS commissions_extended (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    nome TEXT,
    legislatura TEXT,
    import_source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Deputy-Commission relationships
CREATE TABLE IF NOT EXISTS deputy_commissions_extended (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deputy_id TEXT NOT NULL,
    commission_id TEXT NOT NULL,
    situacao TEXT,
    legislatura TEXT,
    import_source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deputy_id) REFERENCES deputies_extended(source_id),
    FOREIGN KEY (commission_id) REFERENCES commissions_extended(source_id),
    UNIQUE(deputy_id, commission_id, legislatura)
);

-- Biographical records table
CREATE TABLE IF NOT EXISTS biographical_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cadastro_id INTEGER UNIQUE NOT NULL,
    nome_completo TEXT,
    data_nascimento TEXT,
    sexo TEXT,
    profissao TEXT,
    import_source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Academic qualifications table
CREATE TABLE IF NOT EXISTS qualifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    cadastro_id INTEGER NOT NULL,
    descricao TEXT,
    tipo_id TEXT,
    estado TEXT,
    import_source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cadastro_id) REFERENCES biographical_records(cadastro_id)
);

-- Previous positions/functions table  
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    cadastro_id INTEGER NOT NULL,
    descricao TEXT,
    ordem TEXT,
    antiga TEXT,
    import_source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cadastro_id) REFERENCES biographical_records(cadastro_id)
);

-- Decorations/honors table
CREATE TABLE IF NOT EXISTS decorations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    cadastro_id INTEGER NOT NULL,
    descricao TEXT,
    ordem TEXT,
    import_source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cadastro_id) REFERENCES biographical_records(cadastro_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_deputies_extended_cadastro ON deputies_extended(cadastro_id);
CREATE INDEX IF NOT EXISTS idx_deputies_extended_legislatura ON deputies_extended(legislatura);
CREATE INDEX IF NOT EXISTS idx_initiatives_extended_deputy ON initiatives_extended(deputy_id);
CREATE INDEX IF NOT EXISTS idx_initiatives_extended_legislatura ON initiatives_extended(legislatura);
CREATE INDEX IF NOT EXISTS idx_interventions_extended_deputy ON interventions_extended(deputy_id);
CREATE INDEX IF NOT EXISTS idx_interventions_extended_legislatura ON interventions_extended(legislatura);
CREATE INDEX IF NOT EXISTS idx_commissions_extended_legislatura ON commissions_extended(legislatura);
CREATE INDEX IF NOT EXISTS idx_deputy_commissions_deputy ON deputy_commissions_extended(deputy_id);
CREATE INDEX IF NOT EXISTS idx_deputy_commissions_commission ON deputy_commissions_extended(commission_id);
CREATE INDEX IF NOT EXISTS idx_biographical_records_cadastro ON biographical_records(cadastro_id);
CREATE INDEX IF NOT EXISTS idx_qualifications_cadastro ON qualifications(cadastro_id);
CREATE INDEX IF NOT EXISTS idx_positions_cadastro ON positions(cadastro_id);
CREATE INDEX IF NOT EXISTS idx_decorations_cadastro ON decorations(cadastro_id);