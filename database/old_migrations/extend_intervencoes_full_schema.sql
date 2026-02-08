-- Extend intervencoes table to handle all XML fields from parliamentary intervention data
-- This migration adds comprehensive support for all fields found in the XML structure

-- Add new columns to intervencoes table
ALTER TABLE intervencoes ADD COLUMN legislatura_numero INTEGER;
ALTER TABLE intervencoes ADD COLUMN id_debate INTEGER;
ALTER TABLE intervencoes ADD COLUMN sessao_numero TEXT;
ALTER TABLE intervencoes ADD COLUMN debate_titulo TEXT;

-- Government members related fields
ALTER TABLE intervencoes ADD COLUMN membro_governo_nome TEXT;
ALTER TABLE intervencoes ADD COLUMN membro_governo_cargo TEXT;
ALTER TABLE intervencoes ADD COLUMN governo_designacao TEXT;

-- Guest/invited participants
ALTER TABLE intervencoes ADD COLUMN convidado_nome TEXT;
ALTER TABLE intervencoes ADD COLUMN convidado_cargo TEXT;

-- Parliamentary group information
ALTER TABLE intervencoes ADD COLUMN grupo_parlamentar TEXT;

-- Publication details (already have some, extending)
ALTER TABLE intervencoes ADD COLUMN publicacao_tipo TEXT;
ALTER TABLE intervencoes ADD COLUMN publicacao_numero TEXT;
ALTER TABLE intervencoes ADD COLUMN publicacao_serie_legislatura TEXT;
ALTER TABLE intervencoes ADD COLUMN publicacao_suplemento TEXT;
ALTER TABLE intervencoes ADD COLUMN publicacao_data DATE;
ALTER TABLE intervencoes ADD COLUMN publicacao_id_interno INTEGER;

-- Related activities and initiatives
ALTER TABLE intervencoes ADD COLUMN atividades_relacionadas_ids TEXT; -- JSON array of IDs
ALTER TABLE intervencoes ADD COLUMN atividades_relacionadas_tipos TEXT; -- JSON array of types
ALTER TABLE intervencoes ADD COLUMN iniciativas_ids TEXT; -- JSON array of initiative IDs
ALTER TABLE intervencoes ADD COLUMN iniciativas_tipos TEXT; -- JSON array of initiative types
ALTER TABLE intervencoes ADD COLUMN iniciativas_fases TEXT; -- JSON array of initiative phases

-- Audio/video enhanced fields
ALTER TABLE intervencoes ADD COLUMN audiovisual_tipo_intervencao TEXT;

-- Deputy identification enhancement
ALTER TABLE intervencoes ADD COLUMN deputado_id_cadastro INTEGER;
ALTER TABLE intervencoes ADD COLUMN deputado_nome_completo TEXT;

-- Create indexes for new fields
CREATE INDEX IF NOT EXISTS idx_intervencoes_legislatura_numero ON intervencoes(legislatura_numero);
CREATE INDEX IF NOT EXISTS idx_intervencoes_id_debate ON intervencoes(id_debate);
CREATE INDEX IF NOT EXISTS idx_intervencoes_membro_governo ON intervencoes(membro_governo_nome);
CREATE INDEX IF NOT EXISTS idx_intervencoes_grupo_parlamentar ON intervencoes(grupo_parlamentar);
CREATE INDEX IF NOT EXISTS idx_intervencoes_publicacao_data ON intervencoes(publicacao_data);
CREATE INDEX IF NOT EXISTS idx_intervencoes_deputado_cadastro ON intervencoes(deputado_id_cadastro);

-- Update trigger to handle updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_intervencoes_timestamp 
    AFTER UPDATE ON intervencoes
    FOR EACH ROW
BEGIN
    UPDATE intervencoes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;