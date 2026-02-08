-- Create tables for AgendaParlamentar based on XSD schema analysis
-- Generated from AgendaParlamentar.xsd schema

-- Main parliamentary agenda events table
CREATE TABLE IF NOT EXISTS agenda_parlamentar (
    id INTEGER PRIMARY KEY,
    source_id INTEGER, -- Original Id from XML
    parliament_group_id INTEGER,
    section_id INTEGER,
    theme_id INTEGER,
    
    -- Event details
    title TEXT,
    subtitle TEXT,
    section TEXT,
    theme TEXT,
    
    -- Dates and times
    event_start_date TEXT, -- Will be converted to proper date format
    event_start_time TEXT,
    event_end_date TEXT,
    event_end_time TEXT,
    all_day_event BOOLEAN DEFAULT FALSE,
    
    -- Content
    internet_text TEXT, -- HTML content describing the event
    local TEXT, -- Location
    link TEXT, -- External link
    
    -- Parliamentary context
    leg_des TEXT, -- Legislature designation (XVII, XVI, etc.)
    org_des TEXT, -- Organization description
    reu_numero TEXT, -- Meeting number
    sel_numero TEXT, -- Selection number
    
    -- Ordering and flags
    order_value INTEGER,
    post_plenary BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    import_source TEXT, -- Track which file this came from
    import_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (parliament_group_id) REFERENCES parliament_groups(id)
);

-- Parliamentary groups lookup table (extracted from ParlamentGroup IDs)
CREATE TABLE IF NOT EXISTS parliament_groups (
    id INTEGER PRIMARY KEY,
    source_id INTEGER UNIQUE, -- Original ParlamentGroup ID from XML
    name TEXT,
    short_name TEXT, -- PS, IL, PCP, etc.
    legislatura TEXT,
    
    -- Metadata
    first_seen_date DATETIME,
    last_seen_date DATETIME,
    import_source TEXT
);

-- Anexos (attachments) for events
CREATE TABLE IF NOT EXISTS agenda_anexos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agenda_id INTEGER NOT NULL,
    anexo_type TEXT, -- 'comissao_permanente' or 'plenario'
    
    -- Anexo details from XSD
    source_id TEXT, -- idField from XSD
    tipo_documento TEXT, -- tipoDocumentoField
    titulo TEXT, -- tituloField  
    url TEXT, -- uRLField
    
    -- Metadata
    import_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (agenda_id) REFERENCES agenda_parlamentar(id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_agenda_parlament_group ON agenda_parlamentar(parliament_group_id);
CREATE INDEX IF NOT EXISTS idx_agenda_event_date ON agenda_parlamentar(event_start_date);
CREATE INDEX IF NOT EXISTS idx_agenda_legislatura ON agenda_parlamentar(leg_des);
CREATE INDEX IF NOT EXISTS idx_agenda_source_id ON agenda_parlamentar(source_id);

CREATE INDEX IF NOT EXISTS idx_parliament_groups_source ON parliament_groups(source_id);
CREATE INDEX IF NOT EXISTS idx_parliament_groups_name ON parliament_groups(short_name);

CREATE INDEX IF NOT EXISTS idx_anexos_agenda ON agenda_anexos(agenda_id);
CREATE INDEX IF NOT EXISTS idx_anexos_type ON agenda_anexos(anexo_type);