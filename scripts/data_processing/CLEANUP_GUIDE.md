# Database Cleanup Guide

This guide explains the different cleanup options available for the Parliament Data Import system.

## Cleanup Options

### 1. Standard Cleanup (--cleanup)
**Preserves ImportStatus and resets to 'discovered'**

```bash
python scripts/data_processing/database_driven_importer.py --cleanup
```

**What it does:**
- ✅ **Preserves** ImportStatus table with all discovery data
- ✅ **Resets** all ImportStatus records to 'discovered' status
- ✅ **Clears** processing timestamps, error messages, and retry counters
- ❌ **Drops** all other data tables (deputados, legislaturas, etc.)
- ❌ **Keeps** alembic_version table for migrations

**Use this when:**
- You want to reprocess all files with updated mappers
- You've fixed schema issues and need to reimport data
- You want to test the import process without losing discovery data
- You need to clear all imported data but keep file discovery history

### 2. Full Cleanup (--full-cleanup)
**Drops everything including ImportStatus**

```bash
python scripts/data_processing/database_driven_importer.py --full-cleanup
```

**What it does:**
- ❌ **Drops** ImportStatus table (loses all discovery data)
- ❌ **Drops** all other data tables 
- ✅ **Keeps** alembic_version table for migrations

**Use this when:**
- You want a completely fresh start
- You need to change discovery logic or file patterns
- You're switching to a different data source
- You want to clean up test data completely

## SQL-Only Reset

For resetting ImportStatus records without dropping other tables:

```bash
mysql -u username -p database_name < scripts/data_processing/reset_import_status.sql
```

Or execute the SQL directly:

```sql
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
```

## Workflow Examples

### Reprocessing After Mapper Updates
```bash
# 1. Standard cleanup (preserves discovery data)
python scripts/data_processing/database_driven_importer.py --cleanup

# 2. Run import processing
python scripts/data_processing/database_driven_importer.py --limit 50

# 3. Or use orchestrator for full pipeline
python scripts/data_processing/pipeline_orchestrator.py
```

### Fresh Start After Discovery Changes
```bash
# 1. Full cleanup (drops everything)
python scripts/data_processing/database_driven_importer.py --full-cleanup

# 2. Run discovery to find files again
python scripts/data_processing/discovery_service.py --save-to-db

# 3. Run import processing
python scripts/data_processing/database_driven_importer.py
```

### Testing Specific File Types
```bash
# 1. Reset just to clear processed status
mysql -u username -p database_name < scripts/data_processing/reset_import_status.sql

# 2. Process specific file types
python scripts/data_processing/database_driven_importer.py --file-types XML --limit 10
```

## Status Check

Check current import status distribution:

```bash
python scripts/data_processing/database_driven_importer.py --status
```

Or use SQL:

```sql
SELECT 
    status,
    COUNT(*) as count,
    file_type,
    COUNT(DISTINCT category) as categories
FROM import_status 
GROUP BY status, file_type
ORDER BY count DESC;
```

## Safety Notes

- ⚠️ Always backup your database before cleanup operations
- ⚠️ Standard cleanup preserves discovery metadata (file URLs, categories, etc.)
- ⚠️ Full cleanup requires running discovery again to find files
- ⚠️ Both cleanup options require explicit confirmation ("yes")
- ✅ alembic_version table is always preserved for database migrations

## Recovery

If you accidentally run full cleanup:

1. **Restore from backup** (if available)
2. **Or re-run discovery:**
   ```bash
   python scripts/data_processing/discovery_service.py --save-to-db
   ```
3. **Then process files:**
   ```bash
   python scripts/data_processing/database_driven_importer.py
   ```