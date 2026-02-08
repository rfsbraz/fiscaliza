-- Fix agenda_parlamentar unique constraint to allow same id_externo across different legislaturas
-- Drop the old unique constraint and create a composite one

BEGIN TRANSACTION;

-- Create new table with correct constraint
CREATE TABLE agenda_parlamentar_new (
    id INTEGER PRIMARY KEY,
    id_externo INTEGER,
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
    secao_parlamentar_id INTEGER REFERENCES secoes_parlamentares(id),
    tema_parlamentar_id INTEGER REFERENCES temas_parlamentares(id),
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
    UNIQUE (id_externo, legislatura_id)
);

-- Copy existing data
INSERT INTO agenda_parlamentar_new SELECT * FROM agenda_parlamentar;

-- Drop old table
DROP TABLE agenda_parlamentar;

-- Rename new table
ALTER TABLE agenda_parlamentar_new RENAME TO agenda_parlamentar;

-- Recreate indexes
CREATE INDEX idx_agenda_data ON agenda_parlamentar(data_evento);
CREATE INDEX idx_agenda_legislatura_data ON agenda_parlamentar(legislatura_id, data_evento);
CREATE INDEX idx_agenda_grupo ON agenda_parlamentar(grupo_parlamentar);

COMMIT;