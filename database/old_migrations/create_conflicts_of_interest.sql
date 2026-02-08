-- Create conflicts_of_interest table
CREATE TABLE IF NOT EXISTS conflicts_of_interest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    legislatura TEXT NOT NULL,
    full_name TEXT,
    marital_status TEXT,
    spouse_name TEXT,
    matrimonial_regime TEXT,
    exclusivity TEXT,
    dgf_number TEXT,
    import_source TEXT DEFAULT 'registo_interesses',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(record_id, legislatura, import_source)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_conflicts_of_interest_record_id ON conflicts_of_interest(record_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_of_interest_legislatura ON conflicts_of_interest(legislatura);
CREATE INDEX IF NOT EXISTS idx_conflicts_of_interest_full_name ON conflicts_of_interest(full_name);
CREATE INDEX IF NOT EXISTS idx_conflicts_of_interest_exclusivity ON conflicts_of_interest(exclusivity);