-- Fix unique constraint on atividades_parlamentares_detalhadas
-- Allow same id_externo for different activity types

-- Create new table with correct constraint
CREATE TABLE atividades_parlamentares_detalhadas_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_externo INTEGER,
    tipo TEXT,
    titulo TEXT,
    data_atividade DATE,
    legislatura_id INTEGER REFERENCES legislaturas(id),
    debate_id INTEGER REFERENCES debates_parlamentares(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_externo, tipo)  -- Composite unique constraint
);

-- Copy existing data
INSERT INTO atividades_parlamentares_detalhadas_new 
SELECT * FROM atividades_parlamentares_detalhadas;

-- Drop old table and rename new one
DROP TABLE atividades_parlamentares_detalhadas;
ALTER TABLE atividades_parlamentares_detalhadas_new 
RENAME TO atividades_parlamentares_detalhadas;

-- Recreate indexes if any existed
CREATE INDEX IF NOT EXISTS idx_atividades_legislatura 
ON atividades_parlamentares_detalhadas(legislatura_id);

CREATE INDEX IF NOT EXISTS idx_atividades_tipo 
ON atividades_parlamentares_detalhadas(tipo);

CREATE INDEX IF NOT EXISTS idx_atividades_data 
ON atividades_parlamentares_detalhadas(data_atividade);