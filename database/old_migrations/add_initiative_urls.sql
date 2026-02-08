-- Add URL columns to initiatives table
-- Migration: add_initiative_urls.sql

-- Add URL fields to iniciativas_legislativas table
ALTER TABLE iniciativas_legislativas 
ADD COLUMN id_externo_ini INTEGER;

ALTER TABLE iniciativas_legislativas 
ADD COLUMN url_documento TEXT;

ALTER TABLE iniciativas_legislativas 
ADD COLUMN url_debates TEXT;

ALTER TABLE iniciativas_legislativas 
ADD COLUMN url_oficial TEXT;

ALTER TABLE iniciativas_legislativas 
ADD COLUMN id_publicacao INTEGER;

ALTER TABLE iniciativas_legislativas 
ADD COLUMN url_diario TEXT;

-- Create index for faster lookups by external ID
CREATE INDEX IF NOT EXISTS idx_iniciativas_id_externo_ini ON iniciativas_legislativas(id_externo_ini);

-- Add comments for documentation
UPDATE iniciativas_legislativas SET 
    url_documento = 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=' || COALESCE(id_externo_ini, id_externo)
WHERE id_externo_ini IS NOT NULL OR id_externo IS NOT NULL;