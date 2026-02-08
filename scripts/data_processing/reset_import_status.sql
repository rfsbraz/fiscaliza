-- Reset ImportStatus Records to 'discovered' Status
-- =====================================================
-- 
-- This script resets all ImportStatus records to 'discovered' status,
-- allowing them to be reprocessed by the database importer.
-- Useful for reprocessing files after fixing mappers or schema issues.
--
-- Usage:
--   mysql -u username -p database_name < reset_import_status.sql
--
-- Or in MySQL CLI:
--   source /path/to/reset_import_status.sql

-- Show current status distribution before reset
SELECT 
    'BEFORE RESET' as phase,
    status,
    COUNT(*) as count,
    MIN(updated_at) as oldest_update,
    MAX(updated_at) as newest_update
FROM import_status 
GROUP BY status
ORDER BY count DESC;

-- Reset all ImportStatus records to discovered state
UPDATE import_status 
SET 
    status = 'discovered',
    processing_started_at = NULL,
    processing_completed_at = NULL,
    error_message = NULL,
    records_imported = 0,
    error_count = 0,
    retry_at = NULL,
    updated_at = NOW()
WHERE status != 'discovered';

-- Show results after reset
SELECT 
    'AFTER RESET' as phase,
    status,
    COUNT(*) as count,
    MIN(updated_at) as oldest_update,
    MAX(updated_at) as newest_update
FROM import_status 
GROUP BY status
ORDER BY count DESC;

-- Show summary statistics
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN status = 'discovered' THEN 1 END) as discovered_records,
    COUNT(CASE WHEN status != 'discovered' THEN 1 END) as other_status_records,
    MIN(created_at) as oldest_discovery,
    MAX(created_at) as newest_discovery,
    COUNT(DISTINCT file_type) as file_types,
    COUNT(DISTINCT category) as categories,
    COUNT(DISTINCT legislatura) as legislaturas
FROM import_status;

-- Show file type distribution
SELECT 
    file_type,
    COUNT(*) as count,
    COUNT(DISTINCT category) as categories
FROM import_status 
GROUP BY file_type
ORDER BY count DESC;