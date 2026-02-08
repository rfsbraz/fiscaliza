-- Fix comissoes unique constraint to allow same id_externo across different legislaturas
-- Drop the old unique constraint and create a composite one

BEGIN TRANSACTION;

-- Create new table with correct constraint
CREATE TABLE comissoes_new (
    id INTEGER PRIMARY KEY,
    id_externo INTEGER,
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
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
    UNIQUE (id_externo, legislatura_id)
);

-- Copy existing data
INSERT INTO comissoes_new SELECT * FROM comissoes;

-- Drop old table
DROP TABLE comissoes;

-- Rename new table
ALTER TABLE comissoes_new RENAME TO comissoes;

-- Recreate indexes
CREATE INDEX idx_comissoes_legislatura ON comissoes(legislatura_id);
CREATE INDEX idx_comissoes_ativa ON comissoes(ativa);

COMMIT;