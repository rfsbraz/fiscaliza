-- Create import_status table for tracking file processing
CREATE TABLE IF NOT EXISTS import_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_url TEXT NOT NULL UNIQUE,
    file_path TEXT,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'JSON', 'XML', 'PDF', 'Archive'
    category TEXT NOT NULL,
    legislatura TEXT,
    sub_series TEXT, -- For DAR files
    session TEXT,    -- For DAR files
    number TEXT,     -- For DAR files
    file_hash TEXT,  -- SHA1 hash of file content
    file_size INTEGER,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed', 'schema_mismatch'
    schema_issues TEXT, -- JSON array of schema validation issues
    processing_started_at DATETIME,
    processing_completed_at DATETIME,
    error_message TEXT,
    records_imported INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_import_status_url ON import_status(file_url);
CREATE INDEX IF NOT EXISTS idx_import_status_hash ON import_status(file_hash);
CREATE INDEX IF NOT EXISTS idx_import_status_status ON import_status(status);
CREATE INDEX IF NOT EXISTS idx_import_status_category ON import_status(category);
CREATE INDEX IF NOT EXISTS idx_import_status_legislatura ON import_status(legislatura);

-- Create trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_import_status_timestamp 
    AFTER UPDATE ON import_status
    FOR EACH ROW
BEGIN
    UPDATE import_status SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;