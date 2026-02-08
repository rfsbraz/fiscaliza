#!/usr/bin/env python3
"""
Database-Driven Parliament Data Importer
=========================================

A database-driven importer that processes files based on ImportStatus table records.
Works with the discovery service and download manager to process files on-demand.

Features:
- Database-driven processing (no directory scanning)
- On-demand file downloading during import
- HTTP HEAD request change detection
- Integration with pipeline orchestrator
- Maintains all existing mapper functionality
"""

import hashlib
import logging
import os
import signal
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, List, Optional

import requests
from http_retry_utils import safe_request_get
from requests.exceptions import ConnectTimeout, ReadTimeout, ConnectionError, Timeout
from sqlalchemy.exc import OperationalError
import psycopg2.errors

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from database.connection import DatabaseSession
from database.models import ImportStatus
from scripts.data_processing.mappers import (
    AgendaParlamentarMapper,
    AtividadeDeputadosMapper,
    AtividadesMapper,
    ComposicaoOrgaosMapper,
    CooperacaoMapper,
    DelegacaoEventualMapper,
    DelegacaoPermanenteMapper,
    DiplomasAprovadosMapper,
    GruposAmizadeMapper,
    InformacaoBaseMapper,
    InitiativasMapper,
    IntervencoesMapper,
    OrcamentoEstadoMapper,
    PerguntasRequerimentosMapper,
    PeticoesMapper,
    RegistoBiograficoMapper,
    RegistoInteressesMapper,
    ReunioesNacionaisMapper,
)
from scripts.data_processing.mappers.enhanced_base_mapper import SchemaError
from scripts.data_processing.file_type_resolver import FileTypeResolver

# Configure logging with Unicode-safe console handler
from utils.unicode_safe_logging import UnicodeSafeHandler

# Initialize logger (will be configured in main() for CLI usage)
logger = logging.getLogger(__name__)


# Constants for transient error retry
MAX_TRANSIENT_RETRIES = 3
TRANSIENT_RETRY_DELAY = 0.5  # Base delay in seconds (will use exponential backoff)


def is_transient_db_error(exception: Exception) -> bool:
    """Check if a database error is transient and should be retried.

    Transient errors include deadlocks and serialization failures which
    can be resolved by retrying the operation with a fresh session.
    """
    if isinstance(exception, OperationalError):
        orig = getattr(exception, 'orig', None)
        if orig is not None:
            # Check for PostgreSQL transient errors
            return isinstance(orig, (
                psycopg2.errors.DeadlockDetected,
                psycopg2.errors.SerializationFailure,
            ))
    return False


class ChangeDetectionService:
    """Service for detecting file changes using HTTP HEAD requests"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Fiscaliza/1.0 (https://fiscaliza.pt; open-source parliamentary data)'
        })
    
    def check_for_changes(self, import_record: ImportStatus) -> bool:
        """Check if a file has changed since last discovery/download"""
        try:
            response = self.session.head(import_record.file_url, timeout=10)
            response.raise_for_status()
            
            # Compare Last-Modified
            if 'Last-Modified' in response.headers:
                from email.utils import parsedate_to_datetime
                try:
                    server_modified = parsedate_to_datetime(response.headers['Last-Modified'])
                    if import_record.last_modified and server_modified != import_record.last_modified:
                        return True
                except:
                    pass
            
            # Compare Content-Length
            if 'Content-Length' in response.headers:
                try:
                    server_length = int(response.headers['Content-Length'])
                    if import_record.content_length and server_length != import_record.content_length:
                        return True
                except:
                    pass
            
            # Compare ETag
            if 'ETag' in response.headers:
                server_etag = response.headers['ETag']
                if import_record.etag and server_etag != import_record.etag:
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Change detection error for {import_record.file_name}: {e}")
            return False  # Assume no change on error
    
    def update_metadata(self, import_record: ImportStatus) -> bool:
        """Update HTTP metadata for an import record"""
        try:
            response = self.session.head(import_record.file_url, timeout=10)
            response.raise_for_status()
            
            updated = False
            
            # Update Last-Modified
            if 'Last-Modified' in response.headers:
                from email.utils import parsedate_to_datetime
                try:
                    server_modified = parsedate_to_datetime(response.headers['Last-Modified'])
                    if server_modified != import_record.last_modified:
                        import_record.last_modified = server_modified
                        updated = True
                except:
                    pass
            
            # Update Content-Length
            if 'Content-Length' in response.headers:
                try:
                    server_length = int(response.headers['Content-Length'])
                    if server_length != import_record.content_length:
                        import_record.content_length = server_length
                        updated = True
                except:
                    pass
            
            # Update ETag
            if 'ETag' in response.headers:
                server_etag = response.headers['ETag']
                if server_etag != import_record.etag:
                    import_record.etag = server_etag
                    updated = True
            
            if updated:
                import_record.updated_at = datetime.now()
            
            return updated
            
        except Exception as e:
            logger.debug(f"Metadata update error for {import_record.file_name}: {e}")
            return False


class DatabaseDrivenImporter:
    """Main database-driven importer class"""
    
    # Import order respecting foreign key dependencies (same as unified_importer)
    IMPORT_ORDER = [
        "atividade_deputados",
        "atividades", 
        "composicao_orgaos",
        "informacao_base",
        "registo_biografico",
        "agenda_parlamentar",
        "orcamento_estado",
        "iniciativas",
        "intervencoes",
        "peticoes",
        "perguntas_requerimentos",
        "diplomas_aprovados",
        "cooperacao",
        "delegacao_eventual",
        "delegacao_permanente",
        "registo_interesses",
        "grupos_amizade",
        "reunioes_visitas",
    ]
    
    def __init__(self, allowed_file_types: List[str] = None, quiet: bool = False, orchestrator_mode: bool = False):
        self.file_type_resolver = FileTypeResolver()
        self.change_detection = ChangeDetectionService()
        self.allowed_file_types = allowed_file_types or ['XML']  # Default to XML only
        self.shutdown_requested = False
        self.quiet = quiet  # Suppress console output when True
        self.orchestrator_mode = orchestrator_mode  # Modify behavior for orchestrator integration
        
        # Configure logging for standalone mode
        if not self.orchestrator_mode and not self.quiet:
            self._setup_console_logging()
        
        # Retry configuration for exponential backoff
        self.min_retry_delay = 300  # 5 minutes minimum
        self.max_retry_delay = 86400  # 24 hours maximum
        self.retry_backoff_factor = 2.0  # Double delay each time
        
        # Schema mappers registry (same as unified_importer)
        self.schema_mappers = {
            "registo_biografico": RegistoBiograficoMapper,
            "iniciativas": InitiativasMapper,
            "intervencoes": IntervencoesMapper,
            "registo_interesses": RegistoInteressesMapper,
            "atividade_deputados": AtividadeDeputadosMapper,
            "agenda_parlamentar": AgendaParlamentarMapper,
            "atividades": AtividadesMapper,
            "composicao_orgaos": ComposicaoOrgaosMapper,
            "cooperacao": CooperacaoMapper,
            "delegacao_eventual": DelegacaoEventualMapper,
            "delegacao_permanente": DelegacaoPermanenteMapper,
            "grupos_amizade": GruposAmizadeMapper,
            "informacao_base": InformacaoBaseMapper,
            "peticoes": PeticoesMapper,
            "perguntas_requerimentos": PerguntasRequerimentosMapper,
            "diplomas_aprovados": DiplomasAprovadosMapper,
            "orcamento_estado": OrcamentoEstadoMapper,
            "reunioes_visitas": ReunioesNacionaisMapper,
            # Note: DAR (Diário da Assembleia da República) intentionally excluded for now
        }
    
    def _setup_console_logging(self):
        """Setup console logging for standalone mode.

        Uses structured JSON logging when running in non-interactive environments
        (ECS, CI/CD) for CloudWatch Logs Insights compatibility.
        """
        # Only configure if not already configured
        if not logger.handlers:
            try:
                from scripts.data_processing.pipeline_logging import is_interactive, JsonFormatter

                if is_interactive():
                    # Interactive mode: human-readable logs
                    logging.basicConfig(
                        level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s",
                        handlers=[
                            logging.FileHandler("database_driven_importer.log", encoding="utf-8"),
                            UnicodeSafeHandler(),  # Console handler with Unicode safety
                        ],
                    )
                    logger.info("Database-driven importer logging configured for standalone mode")
                else:
                    # Non-interactive mode (ECS/CI): structured JSON logging
                    handler = logging.StreamHandler(sys.stdout)
                    handler.setFormatter(JsonFormatter(extra_fields={
                        'service': 'parliament-importer',
                        'component': 'database_driven_importer'
                    }))
                    logger.addHandler(handler)
                    logger.setLevel(logging.INFO)
                    logger.propagate = False
                    logger.info("Database-driven importer logging configured for ECS/CloudWatch mode")
            except ImportError:
                # Fallback if pipeline_logging not available
                logging.basicConfig(
                    level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s",
                    handlers=[
                        logging.FileHandler("database_driven_importer.log", encoding="utf-8"),
                        UnicodeSafeHandler(),
                    ],
                )
                logger.info("Database-driven importer logging configured (fallback mode)")
    
    def _print(self, *args, **kwargs):
        """Print only if not in quiet mode"""
        if not self.quiet:
            print(*args, **kwargs)
    
    def set_shutdown_requested(self, value: bool):
        """Set shutdown request flag (for orchestrator integration)"""
        self.shutdown_requested = value
    
    def is_running(self) -> bool:
        """Check if importer should continue running"""
        return not self.shutdown_requested
    
    def get_import_statistics(self) -> Dict[str, int]:
        """Get import statistics for orchestrator integration"""
        with DatabaseSession() as db_session:
            from sqlalchemy import func
            
            # Query import statistics based on allowed file types
            query = db_session.query(ImportStatus)
            if self.allowed_file_types:
                query = query.filter(ImportStatus.file_type.in_(self.allowed_file_types))
            
            # Count by status
            completed = query.filter(ImportStatus.status == 'completed').count()
            failed = query.filter(ImportStatus.status.in_(['import_error', 'failed'])).count()
            skipped = query.filter(ImportStatus.status == 'skipped').count()
            pending = query.filter(ImportStatus.status.in_(['pending', 'discovered', 'download_pending'])).count()

            # Sum total records imported
            total_records = (
                query.filter(ImportStatus.status == 'completed')
                .with_entities(func.coalesce(func.sum(ImportStatus.records_imported), 0))
                .scalar() or 0
            )

            return {
                'completed': completed,
                'failed': failed,
                'skipped': skipped,
                'pending': pending,
                'total_records': total_records
            }
    
    def _calculate_retry_time(self, error_count: int) -> datetime:
        """Calculate next retry time using exponential backoff"""
        # Calculate delay: min_delay * (backoff_factor ^ (error_count - 1))
        delay_seconds = self.min_retry_delay * (self.retry_backoff_factor ** (error_count - 1))
        
        # Cap at maximum delay
        delay_seconds = min(delay_seconds, self.max_retry_delay)
        
        # Add some jitter (±10%) to avoid thundering herd
        import random
        jitter = random.uniform(-0.1, 0.1)
        delay_seconds = delay_seconds * (1 + jitter)
        
        return datetime.now() + timedelta(seconds=int(delay_seconds))

    def _is_permanent_error(self, error_msg: str) -> bool:
        """
        Check if an error is permanent (unrecoverable) and should skip the file.

        Permanent errors are those where retrying won't help because the source
        data itself is corrupted or malformed.
        """
        error_lower = error_msg.lower()

        # XML parsing errors indicating corrupted source data
        permanent_patterns = [
            'not well-formed',
            'invalid token',
            'syntax error',
            'encoding declaration',
            'undefined entity',
            'mismatched tag',
            'unclosed token',
            'junk after document element',
            'xml declaration not at start',
            'duplicate attribute',
            # Binary/encoding corruption indicators
            'codec can\'t decode',
            'invalid continuation byte',
            'invalid start byte',
            # Source data issues
            'corrupted',
            'binary data',
        ]

        return any(pattern in error_lower for pattern in permanent_patterns)

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self._print(f"\n>> Received shutdown signal ({signal.Signals(signum).name})")
            self._print("   Finishing current file processing and shutting down gracefully...")
            self._print("   Press Ctrl+C again to force shutdown (not recommended)")
            self.shutdown_requested = True
        
        # Handle both SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
    
    def process_pending_imports(self, 
                               file_type_filter: str = None,
                               legislatura_filter: str = None,
                               limit: int = None,
                               force_reimport: bool = False,
                               strict_mode: bool = False) -> Dict[str, int]:
        """Process all pending imports from the database"""
        stats = {
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'skipped': 0,
            'total_records': 0
        }
        
        self._print(f">> Starting database-driven import processing...")
        logger.info("Starting database-driven import processing")
        if not self.orchestrator_mode:
            self._print("   Press Ctrl+C to shutdown gracefully after current file completes")
        
        # Setup signal handlers for graceful shutdown (only in standalone mode)
        if not self.orchestrator_mode:
            self._setup_signal_handlers()
        
        # Show active file type filter
        if self.allowed_file_types:
            file_types_str = ", ".join(self.allowed_file_types)
            self._print(f"   Processing file types: {file_types_str}")
        else:
            self._print(f"   Processing all file types")
        
        if file_type_filter:
            self._print(f"   Additional category filter: {file_type_filter}")
        if legislatura_filter:
            self._print(f"   Filtering for legislatura: {legislatura_filter}")
        
        # Use a session only for querying files to process (not for processing them)
        with DatabaseSession() as db_session:
            # Build query for files to process
            query = db_session.query(ImportStatus)

            if not force_reimport:
                # Only process files that haven't been completed or are ready for retry
                current_time = datetime.now()
                query = query.filter(
                    (ImportStatus.status.in_(['discovered', 'download_pending', 'pending'])) |
                    (ImportStatus.status == 'import_error') &
                    ((ImportStatus.retry_at.is_(None)) | (ImportStatus.retry_at <= current_time))
                )

            # Apply class-level file type filter
            if self.allowed_file_types:
                query = query.filter(ImportStatus.file_type.in_(self.allowed_file_types))

            if file_type_filter:
                # Legacy filter support - map file type filter to category patterns
                category_pattern = self._get_category_pattern(file_type_filter)
                if category_pattern:
                    query = query.filter(ImportStatus.category.like(f"%{category_pattern}%"))

            if legislatura_filter:
                query = query.filter(ImportStatus.legislatura == legislatura_filter)

            # Order by import dependency order - get IDs only to avoid session issues
            files_to_process = query.all()

            # Sort by import order
            if not file_type_filter:
                files_to_process = self._sort_by_import_order(files_to_process)

            if limit:
                files_to_process = files_to_process[:limit]

            # Extract just the IDs and file names for processing
            file_ids_and_names = [(record.id, record.file_name) for record in files_to_process]

        # From here on, each file gets its own fresh session (outside the query session)
        total_files = len(file_ids_and_names)
        self._print(f"   Found {total_files} files to process")
        logger.info(f"Found {total_files} files to process")

        if not file_ids_and_names:
            self._print("   No files found matching criteria")
            logger.info("No files found matching criteria")
            return stats

        # Process each file with its own session for isolation
        # This ensures that one file's errors (e.g., deadlock) don't cascade to other files
        for i, (record_id, file_name) in enumerate(file_ids_and_names, 1):
            # Check for graceful shutdown request
            if self.shutdown_requested:
                self._print(f"\n>> Shutdown requested. Stopping after processing {i-1}/{total_files} files.")
                break

            self._print(f"\n[{i}/{total_files}] Processing: {file_name}")
            logger.info(f"Processing file {i}/{total_files}: {file_name}")

            # Each file gets its own session with retry for transient errors
            success = self._import_single_file_with_retry(record_id, file_name, strict_mode, stats)

            if not success and strict_mode:
                self._print("   Strict mode: Stopping on error")
                logger.warning("Strict mode: Stopping on error")
                break
        
        self._print(f"\n>> Processing complete:")
        self._print(f"   Succeeded: {stats['succeeded']}")
        self._print(f"   Failed: {stats['failed']}")
        self._print(f"   Total records imported: {stats['total_records']}")
        
        logger.info(f"Processing complete: {stats['succeeded']} succeeded, {stats['failed']} failed, {stats['total_records']} total records imported")
        
        return stats

    def _import_single_file_with_retry(
        self, record_id, file_name: str, strict_mode: bool, stats: Dict
    ) -> bool:
        """Process a single file with per-file session and retry for transient errors.

        This method creates a fresh database session for each attempt, ensuring that
        transient errors like deadlocks don't corrupt the session for subsequent files.

        Args:
            record_id: UUID of the ImportStatus record
            file_name: Name of the file being processed (for logging)
            strict_mode: Whether to stop on first error
            stats: Stats dictionary to update

        Returns:
            True if file was processed successfully, False otherwise
        """
        last_error = None

        for attempt in range(MAX_TRANSIENT_RETRIES):
            try:
                # Create a FRESH session for each attempt
                with DatabaseSession() as db_session:
                    # Re-fetch the import record with the fresh session
                    import_record = db_session.query(ImportStatus).filter(
                        ImportStatus.id == record_id
                    ).first()

                    if not import_record:
                        logger.warning(f"Import record with ID {record_id} not found, skipping")
                        return False

                    success = self._process_single_import(db_session, import_record, strict_mode)

                    # Store attributes before potential session issues
                    records_imported = import_record.records_imported or 0
                    error_message = import_record.error_message or 'Unknown error'

                    if success:
                        stats['succeeded'] += 1
                        stats['total_records'] += records_imported
                        self._print(f"   Success: {records_imported} records imported")
                        logger.info(f"Successfully processed {file_name}: {records_imported} records imported")
                    else:
                        stats['failed'] += 1
                        self._print(f"   Failed: {error_message}")
                        logger.error(f"Failed to process {file_name}: {error_message}")

                    stats['processed'] += 1
                    return success

            except OperationalError as e:
                last_error = e
                if is_transient_db_error(e) and attempt < MAX_TRANSIENT_RETRIES - 1:
                    # Transient error - retry with backoff
                    delay = TRANSIENT_RETRY_DELAY * (2 ** attempt)
                    self._print(f"   Transient error (attempt {attempt + 1}/{MAX_TRANSIENT_RETRIES}), retrying in {delay:.1f}s...")
                    logger.warning(f"Transient DB error for {file_name} (attempt {attempt + 1}): {e}, retrying...")
                    time.sleep(delay)
                    continue
                else:
                    # Non-transient or exhausted retries
                    break

            except Exception as e:
                last_error = e
                break

        # All retries exhausted or non-transient error
        stats['failed'] += 1
        stats['processed'] += 1
        error_msg = str(last_error) if last_error else 'Unknown error'
        self._print(f"   Failed after retries: {error_msg}")
        logger.error(f"Failed to process {file_name} after {MAX_TRANSIENT_RETRIES} attempts: {error_msg}")

        # Try to update import status with error in a fresh session
        try:
            with DatabaseSession() as db_session:
                import_record = db_session.query(ImportStatus).filter(
                    ImportStatus.id == record_id
                ).first()
                if import_record:
                    import_record.status = 'import_error'
                    import_record.error_message = f"Processing error after {MAX_TRANSIENT_RETRIES} retries: {error_msg}"
                    import_record.error_count = (import_record.error_count or 0) + 1
                    import_record.retry_at = self._calculate_retry_time(import_record.error_count)
                    import_record.processing_completed_at = datetime.now()
                    import_record.updated_at = datetime.now()
                    db_session.commit()
        except Exception as status_error:
            logger.error(f"Failed to update error status for {file_name}: {status_error}")

        return False

    def _process_single_import(self, db_session, import_record: ImportStatus, strict_mode: bool = False) -> bool:
        """Process a single import record"""
        try:
            # Check for shutdown request before starting
            if self.shutdown_requested:
                self._print(f"     Shutdown requested, skipping file")
                return False
            
            # Skip DAR files for now (too complex)
            if import_record.category and "diário" in import_record.category.lower():
                self._print(f"     Skipping DAR file (not implemented yet): {import_record.file_name}")
                import_record.status = 'skipped_dar'
                import_record.error_message = "DAR files temporarily skipped - not implemented yet"
                import_record.updated_at = datetime.now()
                db_session.commit()
                # Refresh object after commit to keep it attached to session
                db_session.refresh(import_record)
                return True  # Return success to continue processing other files
            
            # Reset status from import_error to pending if retrying
            if import_record.status == 'import_error':
                self._print(f"     Retrying after error (attempt {import_record.error_count + 1})")
                import_record.status = 'pending'
                import_record.retry_at = None  # Clear retry timestamp
                
            # Check if we need to download the file
            if not self._has_file_content(import_record):
                self._print(f"     Downloading file...")
                logger.info(f"Downloading file: {import_record.file_name}")
                success = self._download_file(import_record)
                if not success:
                    logger.error(f"Failed to download file: {import_record.file_name}")
                    return False
            
            # Check for changes if not forced
            if import_record.status == 'completed':
                if not self.change_detection.check_for_changes(import_record):
                    self._print(f"     No changes detected, skipping")
                    return True
                else:
                    self._print(f"     Changes detected, reprocessing")
            
            # Update status to processing
            import_record.status = 'processing'
            import_record.processing_started_at = datetime.now()
            import_record.updated_at = datetime.now()
            db_session.commit()
            # Refresh object after commit to keep it attached to session
            db_session.refresh(import_record)
            
            # Check for shutdown request after committing processing status
            if self.shutdown_requested:
                self._print(f"     Shutdown requested during processing, reverting to pending status")
                import_record.status = 'pending'
                import_record.processing_started_at = None
                import_record.updated_at = datetime.now()
                db_session.commit()
                # Refresh object after commit to keep it attached to session
                db_session.refresh(import_record)
                return False
            
            # Resolve file type if not set
            if not import_record.category or import_record.category == 'Unknown':
                file_type = self.file_type_resolver.resolve_file_type(import_record.file_name)
                if file_type:
                    import_record.category = file_type.replace('_', ' ').title()
            
            # Get mapper for this file type
            mapper_key = self._get_mapper_key(import_record.category, import_record.file_name)
            if not mapper_key or mapper_key not in self.schema_mappers:
                error_msg = f"No mapper available for category: {import_record.category}"
                logger.error(f"No mapper available for category '{import_record.category}' in file: {import_record.file_name}")
                import_record.status = 'import_error'
                import_record.error_message = error_msg
                import_record.error_count = (import_record.error_count or 0) + 1
                import_record.retry_at = self._calculate_retry_time(import_record.error_count)
                import_record.processing_completed_at = datetime.now()
                if import_record.processing_started_at:
                    import_record.processing_duration_seconds = (import_record.processing_completed_at - import_record.processing_started_at).total_seconds()
                import_record.updated_at = datetime.now()

                # Explicitly flush the error record updates to the database
                db_session.flush()
                return False

            # Parse XML content
            try:
                xml_content = self._get_file_content(import_record)
                xml_root = self._parse_xml_with_bom_handling(xml_content)
                
                file_info = {
                    "file_path": import_record.file_name,  # Use file name since we don't have local path
                    "file_type": mapper_key,
                    "file_hash": import_record.file_hash,
                    "skip_video_processing": True,  # Skip video processing for performance
                }
                
            except Exception as e:
                error_msg = f"XML parsing error: {str(e)}"
                logger.error(f"XML parsing error for {import_record.file_name}: {error_msg}")

                # Check if this is a permanent error (corrupted source data)
                if self._is_permanent_error(str(e)):
                    import_record.status = 'skipped'
                    import_record.error_message = f"Permanently skipped - corrupted source data: {str(e)}"
                    self._print(f"        SKIPPED: Corrupted source data (will not retry)")
                    logger.warning(f"Permanently skipping {import_record.file_name} - corrupted source data")
                else:
                    import_record.status = 'import_error'
                    import_record.error_message = error_msg
                    import_record.error_count = (import_record.error_count or 0) + 1
                    import_record.retry_at = self._calculate_retry_time(import_record.error_count)

                import_record.processing_completed_at = datetime.now()
                if import_record.processing_started_at:
                    import_record.processing_duration_seconds = (import_record.processing_completed_at - import_record.processing_started_at).total_seconds()
                return False

            # Process with mapper using the same session for transaction-per-file
            try:
                mapper_class = self.schema_mappers[mapper_key]
                # Pass import_record to mapper for data provenance tracking
                mapper = mapper_class(db_session, import_status_record=import_record)

                # Log transaction state before mapper
                logger.debug(f"[MAPPER] Before mapper for {import_record.file_name}: session.is_active={db_session.is_active}")

                results = mapper.validate_and_map(xml_root, file_info, strict_mode)

                # CRITICAL: Check if the transaction is still valid after mapper processing
                # Mappers may catch exceptions internally without re-raising, which can leave
                # the transaction in a failed state. This check prevents InFailedSqlTransaction errors.
                try:
                    # Try a minimal operation to detect if transaction is aborted
                    db_session.connection()
                    logger.debug(f"[MAPPER] After mapper for {import_record.file_name}: transaction valid")
                except Exception as conn_error:
                    # Transaction is in a failed state - treat as error
                    logger.error(f"[MAPPER] Transaction INVALID after mapper for {import_record.file_name}: {conn_error}")
                    raise RuntimeError(f"Transaction aborted during processing (mapper swallowed error): {conn_error}")

                # Update import record with results
                import_record.status = 'completed'
                import_record.processing_completed_at = datetime.now()
                if import_record.processing_started_at:
                    import_record.processing_duration_seconds = (import_record.processing_completed_at - import_record.processing_started_at).total_seconds()
                import_record.records_imported = results.get('records_imported', 0)

                # Clear all error-related fields on successful completion
                import_record.error_message = None
                import_record.error_count = 0
                import_record.retry_at = None
                
                # Store any validation warnings (not errors) if present
                if results.get('errors'):
                    import_record.error_message = "; ".join(results.get('errors', []))
                
                import_record.updated_at = datetime.now()
                
                # Commit the entire transaction (mapper data + import status) together
                db_session.commit()
                # Refresh object after commit to keep it attached to session
                db_session.refresh(import_record)
                
                return True
                    
            except SchemaError as e:
                # Log detailed exception info for diagnostics
                record_id = import_record.id
                file_name = import_record.file_name
                logger.error(f"[EXCEPTION] SchemaError in {file_name}: {type(e).__name__}: {e}")
                logger.debug(f"[EXCEPTION] Session state before rollback: is_active={db_session.is_active}")

                # Try to rollback, but connection may be corrupted
                try:
                    db_session.rollback()
                    logger.debug(f"[EXCEPTION] Rollback succeeded for {file_name}")
                except Exception as rb_err:
                    logger.warning(f"[EXCEPTION] Rollback failed for {file_name}: {rb_err}")

                # CRITICAL: Use a fresh session for status update
                # This prevents cascade failures from corrupted connections
                error_msg = f"Schema coverage violation - unmapped fields detected: {str(e)}"
                logger.error(f"Schema error for {file_name}: {error_msg}")
                logger.debug(f"[EXCEPTION] Creating fresh session for status update of {file_name}")

                try:
                    with DatabaseSession() as status_session:
                        fresh_record = status_session.query(ImportStatus).filter(
                            ImportStatus.id == record_id
                        ).first()
                        if fresh_record:
                            fresh_record.status = 'import_error'
                            fresh_record.error_message = error_msg
                            fresh_record.error_count = (fresh_record.error_count or 0) + 1
                            fresh_record.retry_at = self._calculate_retry_time(fresh_record.error_count)
                            fresh_record.processing_completed_at = datetime.now()
                            if fresh_record.processing_started_at:
                                fresh_record.processing_duration_seconds = (
                                    fresh_record.processing_completed_at -
                                    fresh_record.processing_started_at
                                ).total_seconds()
                            fresh_record.updated_at = datetime.now()
                            status_session.commit()
                        else:
                            logger.error(f"Could not find import record {record_id} for status update")
                except Exception as status_error:
                    logger.error(f"Failed to update error status for {record_id}: {status_error}")

                return False

            except Exception as e:
                # Log detailed exception info for diagnostics
                record_id = import_record.id
                file_name = import_record.file_name
                logger.error(f"[EXCEPTION] Processing error in {file_name}: {type(e).__name__}: {e}")
                logger.debug(f"[EXCEPTION] Session state before rollback: is_active={db_session.is_active}")

                # Try to rollback, but connection may be corrupted (deadlock, etc.)
                try:
                    db_session.rollback()
                    logger.debug(f"[EXCEPTION] Rollback succeeded for {file_name}")
                except Exception as rb_err:
                    logger.warning(f"[EXCEPTION] Rollback failed for {file_name}: {rb_err}")

                # CRITICAL: Use a fresh session for status update
                # The current session's connection may be in FAILED state after deadlock
                # This prevents cascade failures where InFailedSqlTransaction errors
                # propagate to subsequent import operations
                error_msg = f"Processing error: {str(e)}"
                logger.debug(f"[EXCEPTION] Creating fresh session for status update of {file_name}")

                try:
                    with DatabaseSession() as status_session:
                        fresh_record = status_session.query(ImportStatus).filter(
                            ImportStatus.id == record_id
                        ).first()
                        if fresh_record:
                            fresh_record.status = 'import_error'
                            fresh_record.error_message = error_msg
                            fresh_record.error_count = (fresh_record.error_count or 0) + 1
                            fresh_record.retry_at = self._calculate_retry_time(fresh_record.error_count)
                            fresh_record.processing_completed_at = datetime.now()
                            if fresh_record.processing_started_at:
                                fresh_record.processing_duration_seconds = (
                                    fresh_record.processing_completed_at -
                                    fresh_record.processing_started_at
                                ).total_seconds()
                            fresh_record.updated_at = datetime.now()
                            status_session.commit()
                        else:
                            logger.error(f"Could not find import record {record_id} for status update")
                except Exception as status_error:
                    logger.error(f"Failed to update error status for {record_id}: {status_error}")

                return False

        except Exception as e:
            # Log detailed exception info for diagnostics
            record_id = import_record.id
            file_name = import_record.file_name
            logger.error(f"[EXCEPTION] Outer handler caught exception in {file_name}: {type(e).__name__}: {e}")
            logger.debug(f"[EXCEPTION] Session state before rollback: is_active={db_session.is_active}")

            # Try to rollback, but connection may be corrupted
            try:
                db_session.rollback()
                logger.debug(f"[EXCEPTION] Rollback succeeded for {file_name}")
            except Exception as rb_err:
                logger.warning(f"[EXCEPTION] Rollback failed for {file_name}: {rb_err}")

            # CRITICAL: Use a fresh session for status update
            # This prevents cascade failures from corrupted connections
            error_msg = f"Unexpected error: {str(e)}"
            logger.debug(f"[EXCEPTION] Creating fresh session for status update of {file_name}")

            try:
                with DatabaseSession() as status_session:
                    fresh_record = status_session.query(ImportStatus).filter(
                        ImportStatus.id == record_id
                    ).first()
                    if fresh_record:
                        fresh_record.status = 'import_error'
                        fresh_record.error_message = error_msg
                        fresh_record.error_count = (fresh_record.error_count or 0) + 1
                        fresh_record.retry_at = self._calculate_retry_time(fresh_record.error_count)
                        fresh_record.processing_completed_at = datetime.now()
                        if fresh_record.processing_started_at:
                            fresh_record.processing_duration_seconds = (
                                fresh_record.processing_completed_at -
                                fresh_record.processing_started_at
                            ).total_seconds()
                        fresh_record.updated_at = datetime.now()
                        status_session.commit()
                    else:
                        logger.error(f"Could not find import record {record_id} for status update")
            except Exception as status_error:
                logger.error(f"Failed to update error status for {record_id}: {status_error}")

            return False
    
    def _download_file(self, import_record: ImportStatus) -> bool:
        """Download file content and save to file system"""
        try:
            self._print(f"        Downloading from: {import_record.file_url}")
            
            response = safe_request_get(import_record.file_url)
            response.raise_for_status()
            
            # Calculate file hash
            file_hash = hashlib.sha1(response.content).hexdigest()
            
            # Create downloads directory structure
            downloads_dir = os.path.join(os.path.dirname(__file__), "data", "downloads")
            os.makedirs(downloads_dir, exist_ok=True)
            
            # Create category-specific subdirectory
            if import_record.category:
                category_dir = os.path.join(downloads_dir, import_record.category.replace(' ', '_').replace('/', '_'))
                os.makedirs(category_dir, exist_ok=True)
            else:
                category_dir = downloads_dir
            
            # Generate unique filename with hash to avoid collisions
            base_name = os.path.splitext(import_record.file_name)[0]
            extension = os.path.splitext(import_record.file_name)[1] or '.xml'
            file_name = f"{base_name}_{file_hash[:8]}{extension}"
            file_path = os.path.join(category_dir, file_name)
            
            # Save file to disk
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Store file metadata
            import_record.file_hash = file_hash
            import_record.file_size = len(response.content)
            import_record.file_path = file_path
            import_record.status = 'pending'
            
            self._print(f"        Downloaded {len(response.content):,} bytes")
            self._print(f"        Saved to: {file_path}")
            logger.info(f"Saved downloaded file to: {file_path}")
            return True
            
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            import_record.status = 'import_error'
            import_record.error_message = error_msg
            import_record.error_count = (import_record.error_count or 0) + 1
            self._print(f"        Download failed: {error_msg}")
            logger.error(f"Download failed for {import_record.file_name}: {error_msg}")
            return False
    
    def _has_file_content(self, import_record: ImportStatus) -> bool:
        """Check if file content is available"""
        # Check if file exists on disk
        if import_record.file_path and os.path.exists(import_record.file_path):
            return True
        # Check if content is in memory (for backward compatibility)
        return hasattr(import_record, '_temp_content') and import_record._temp_content
    
    def _get_file_content(self, import_record: ImportStatus) -> bytes:
        """Get file content for processing"""
        # Try to read from disk first
        if import_record.file_path and os.path.exists(import_record.file_path):
            with open(import_record.file_path, 'rb') as f:
                return f.read()
        
        # Fall back to memory content (for backward compatibility)
        if hasattr(import_record, '_temp_content'):
            return import_record._temp_content
        
        # Last resort: re-download (this shouldn't happen in normal operation)
        response = safe_request_get(import_record.file_url)
        response.raise_for_status()
        return response.content
    
    def _parse_xml_with_bom_handling(self, content: bytes) -> ET.Element:
        """Parse XML content with intelligent Portuguese-aware encoding detection"""
        import re
        
        # Remove BOM if present
        original_content = content
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
        elif content.startswith(b'\xfe\xff'):
            content = content[2:]
        elif content.startswith(b'\xff\xfe'):
            content = content[2:]
        
        # Remove non-ASCII characters before '<'
        while content and content[0:1] != b'<' and content[0] > 127:
            content = content[1:]
        
        # Portuguese character patterns for validation
        portuguese_chars = ['ã', 'ç', 'é', 'í', 'ó', 'ú', 'à', 'è', 'ò', 'â', 'ê', 'ô', 'õ', 'ñ']
        portuguese_names = ['joão', 'josé', 'maria', 'antónio', 'gonçalves', 'fernandes', 'rodrigues', 'pereira']
        
        def _validate_portuguese_text(text: str) -> float:
            """Score text quality based on Portuguese patterns (0.0-1.0)"""
            if not text:
                return 0.0
                
            text_lower = text.lower()
            score = 0.0
            
            # Check for proper Portuguese characters (positive score)
            portuguese_count = sum(1 for char in portuguese_chars if char in text_lower)
            score += min(portuguese_count * 0.1, 0.5)
            
            # Check for common Portuguese names/words (positive score) 
            name_count = sum(1 for name in portuguese_names if name in text_lower)
            score += min(name_count * 0.1, 0.3)
            
            # Penalize corruption patterns (negative score)
            corruption_patterns = [
                r'[a-zA-Z]��[a-zA-Z]',  # Double-encoding corruption like Jo��o
                r'\?\?+',                # Multiple question marks
                r'[a-zA-Z]\?[a-zA-Z]',  # Single corruption like Jo?o  
            ]
            
            for pattern in corruption_patterns:
                corruption_count = len(re.findall(pattern, text))
                score -= corruption_count * 0.2
            
            return max(0.0, min(1.0, score))
        
        def _detect_double_encoding(content_bytes: bytes) -> bytes:
            """Detect and fix common double-encoding issues"""
            # Try to detect UTF-8 bytes incorrectly decoded as Windows-1252 then re-encoded
            try:
                # Decode as UTF-8 first
                utf8_text = content_bytes.decode('utf-8')
                
                # Check if this looks like double-encoded UTF-8
                # Common pattern: UTF-8 → Windows-1252 → UTF-8
                if '��' in utf8_text:  # Common double-encoding signature
                    # Try reverse: UTF-8 → Latin-1 → UTF-8 (fix double encoding)
                    try:
                        # Get the original UTF-8 bytes
                        latin1_bytes = utf8_text.encode('latin-1') 
                        fixed_text = latin1_bytes.decode('utf-8')
                        
                        # Validate this looks more like Portuguese
                        if _validate_portuguese_text(fixed_text) > _validate_portuguese_text(utf8_text):
                            logger.info("Detected and corrected double-encoding corruption")
                            return latin1_bytes
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        pass
                        
                return content_bytes
            except UnicodeDecodeError:
                return content_bytes
        
        # Fix double-encoding if detected
        content = _detect_double_encoding(content)
        
        # Encoding strategies with Portuguese validation
        encoding_strategies = [
            ('utf-8', 'UTF-8 with Portuguese validation'),
            ('windows-1252', 'Windows-1252 (Portuguese legacy)'),
            ('iso-8859-1', 'ISO-8859-1 (Latin-1)'),
            ('iso-8859-15', 'ISO-8859-15 (Latin-9)'),
            ('utf-16', 'UTF-16'),
        ]
        
        best_result = None
        best_score = -1.0
        
        for encoding, description in encoding_strategies:
            try:
                decoded_content = content.decode(encoding)
                
                # Parse XML to ensure it's valid
                xml_root = ET.fromstring(decoded_content)
                
                # Get a sample of text for Portuguese validation
                sample_text = decoded_content[:2000]  # First 2KB for quick validation
                portuguese_score = _validate_portuguese_text(sample_text)
                
                logger.debug(f"Encoding {encoding}: Portuguese score = {portuguese_score:.2f}")
                
                if portuguese_score > best_score:
                    best_result = xml_root
                    best_score = portuguese_score
                    best_encoding = encoding
                    
                # If we get a very high score, use it immediately
                if portuguese_score > 0.8:
                    logger.info(f"High-confidence encoding detected: {encoding} (score: {portuguese_score:.2f})")
                    return xml_root
                    
            except (UnicodeDecodeError, ET.ParseError) as e:
                logger.debug(f"Encoding {encoding} failed: {e}")
                continue
        
        # Use the best result found
        if best_result is not None:
            logger.info(f"Selected encoding: {best_encoding} (Portuguese score: {best_score:.2f})")
            return best_result
        
        # Fallback - force decode with errors='replace' if nothing worked
        logger.warning("All encoding strategies failed, using UTF-8 with error replacement")
        try:
            decoded_content = content.decode('utf-8', errors='replace')
            return ET.fromstring(decoded_content)
        except ET.ParseError:
            # Last resort - try latin-1 which can decode any byte sequence
            decoded_content = content.decode('latin-1')
            return ET.fromstring(decoded_content)
    
    def _get_category_pattern(self, file_type_filter: str) -> Optional[str]:
        """Map file type filter to category pattern.

        Note: Categories in the database are stored WITHOUT accents,
        so patterns must match the unaccented form.
        """
        mapping = {
            'biografico': 'Registo Biografico',
            'iniciativas': 'Iniciativas',
            'intervencoes': 'Intervencoes',
            'interesses': 'Registo',
            'deputados': 'Atividade Deputado',
            'agenda': 'Agenda',
            'atividades': 'Atividades',
            'orgaos': 'Composicao',
            'cooperacao': 'Cooperacao',
            'delegacao': 'Delegac',  # Matches both "Delegacoes Eventuais" and "Delegacoes Permanentes"
            'informacao': 'Informacao',
            'peticoes': 'Peticoes',
            'perguntas': 'Perguntas',
            'diplomas': 'Diplomas',
            'orcamento': 'O E',
            'reunioes': 'Reunioes',
        }
        return mapping.get(file_type_filter.lower())
    
    def _get_mapper_key(self, category: str, filename: str = None) -> Optional[str]:
        """Map category to mapper key, with filename-based disambiguation"""
        if not category:
            return None
            
        category_lower = category.lower()
        
        # Handle "Registo Biografico" category disambiguation using filename
        if ('registo' in category_lower and ('biográfico' in category_lower or 'biografico' in category_lower)) or \
           'registo biografico' in category_lower or 'registo biográfico' in category_lower:
            # Disambiguate using filename - RegistoInteresses files should use interest mapper
            if filename and 'RegistoInteresses' in filename:
                return 'registo_interesses'
            return 'registo_biografico'
        elif 'iniciativas' in category_lower:
            return 'iniciativas'
        elif 'intervenções' in category_lower or 'intervencoes' in category_lower:
            return 'intervencoes'
        elif 'registo' in category_lower and 'interesse' in category_lower:
            return 'registo_interesses'
        elif 'atividade' in category_lower and 'deputado' in category_lower:
            return 'atividade_deputados'
        elif 'agenda' in category_lower:
            return 'agenda_parlamentar'
        elif 'atividades' in category_lower:
            return 'atividades'
        elif 'composição' in category_lower or 'composicao' in category_lower:
            return 'composicao_orgaos'
        elif 'cooperação' in category_lower or 'cooperacao' in category_lower:
            return 'cooperacao'
        elif ('delegação' in category_lower or 'delegacao' in category_lower or 'delegacoes' in category_lower) and ('eventual' in category_lower or 'eventuais' in category_lower):
            return 'delegacao_eventual'
        elif ('delegação' in category_lower or 'delegacao' in category_lower or 'delegacoes' in category_lower) and ('permanente' in category_lower or 'permanentes' in category_lower):
            return 'delegacao_permanente'
        elif 'informação' in category_lower or 'informacao' in category_lower:
            return 'informacao_base'
        elif 'petições' in category_lower or 'peticoes' in category_lower:
            return 'peticoes'
        elif 'perguntas' in category_lower:
            return 'perguntas_requerimentos'
        elif 'diplomas' in category_lower:
            return 'diplomas_aprovados'
        elif 'orçamento' in category_lower or 'orcamento' in category_lower:
            return 'orcamento_estado'
        elif category_lower in ['o e', 'oe', 'o_e', 'orçamento do estado', 'orcamento do estado']:
            return 'orcamento_estado'
        elif 'reuniões' in category_lower or 'reunioes' in category_lower:
            return 'reunioes_visitas'
        elif 'grupos' in category_lower and 'amizade' in category_lower:
            return 'grupos_amizade'
        elif category_lower in ['g p a', 'gpa']:
            return 'grupos_amizade'
        
        # Log unmapped categories for debugging
        logger.warning(f"No mapper key found for category: '{category}' (normalized: '{category_lower}')")
        return None
    
    def _sort_by_import_order(self, import_records: List[ImportStatus]) -> List[ImportStatus]:
        """Sort import records by dependency order with deterministic secondary sorting"""
        def get_sort_key(record):
            mapper_key = self._get_mapper_key(record.category, record.file_name)
            if mapper_key in self.IMPORT_ORDER:
                order_index = self.IMPORT_ORDER.index(mapper_key)
            else:
                order_index = len(self.IMPORT_ORDER)  # Put unknown types at the end
            # Secondary sort by category, legislatura, file_name for deterministic ordering
            return (order_index, record.category or '', record.legislatura or '', record.file_name or '')

        return sorted(import_records, key=get_sort_key)

    def cleanup_database(self):
        """Truncate all tables except ImportStatus and alembic_version, reset ImportStatus to 'discovered'"""
        try:
            logger.info("Starting database cleanup...")

            from sqlalchemy import text
            from database.connection import get_engine

            # Use centralized database connection
            engine = get_engine()
            connection = engine.connect()

            try:
                # Disable foreign key constraints for PostgreSQL
                connection.execute(text("SET session_replication_role = replica"))

                # Get all table names (PostgreSQL syntax)
                result = connection.execute(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                ))
                tables = [row[0] for row in result.fetchall()]

                logger.info(f"Found {len(tables)} tables")

                # Reset ImportStatus instead of dropping it
                if 'import_status' in tables:
                    logger.info("Resetting ImportStatus records to 'discovered' status...")
                    
                    # Count records before reset
                    count_result = connection.execute(text("SELECT COUNT(*) FROM import_status"))
                    total_records = count_result.fetchone()[0]
                    
                    # Reset all ImportStatus records to discovered state
                    reset_query = text("""
                        UPDATE import_status
                        SET
                            status = 'discovered',
                            processing_started_at = NULL,
                            processing_completed_at = NULL,
                            processing_duration_seconds = NULL,
                            error_message = NULL,
                            records_imported = 0,
                            error_count = 0,
                            retry_at = NULL,
                            updated_at = NOW()
                        WHERE status != 'discovered'
                    """)
                    
                    reset_result = connection.execute(reset_query)
                    reset_count = reset_result.rowcount
                    
                    logger.info(f"Reset {reset_count} ImportStatus records out of {total_records} total records to 'discovered' status")

                # Truncate all other tables except ImportStatus and alembic_version
                tables_to_preserve = {'import_status', 'alembic_version'}
                tables_to_truncate = [table for table in tables if table not in tables_to_preserve]
                
                logger.info(f"Truncating {len(tables_to_truncate)} tables (preserving ImportStatus and alembic_version)")

                for table_name in tables_to_truncate:
                    try:
                        # Use TRUNCATE CASCADE for PostgreSQL to handle foreign keys
                        connection.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                        logger.info(f"Truncated table: {table_name}")
                    except Exception as e:
                        # If truncate fails, try delete
                        logger.warning(f"Truncate failed for {table_name}, using DELETE: {e}")
                        connection.execute(text(f"DELETE FROM {table_name}"))
                        logger.info(f"Deleted all records from table: {table_name}")

                # Re-enable foreign key constraints for PostgreSQL
                connection.execute(text("SET session_replication_role = DEFAULT"))

                connection.commit()
                logger.info(
                    f"Database cleanup completed successfully. Truncated {len(tables_to_truncate)} tables, preserved and reset ImportStatus"
                )

            finally:
                connection.close()

        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            raise

    def show_status(self):
        """Show import status summary"""
        from sqlalchemy import case, func
        from database.connection import DatabaseSession
        from database.models import ImportStatus

        with DatabaseSession() as session:
            # Overall status summary
            status_summary = (
                session.query(
                    ImportStatus.status,
                    func.count().label("count"),
                    func.coalesce(func.sum(ImportStatus.records_imported), 0).label(
                        "total_imported"
                    ),
                )
                .group_by(ImportStatus.status)
                .order_by(func.count().desc())
                .all()
            )

            print("\\n" + "=" * 80)
            print("IMPORT STATUS SUMMARY")
            print("=" * 80)

            for status, count, imported in status_summary:
                print(f"{status.upper():20} {count:>8} files    {imported:>10} records")

            # File type breakdown
            file_type_summary = (
                session.query(
                    ImportStatus.file_type,
                    func.count().label("count"),
                    func.sum(
                        case((ImportStatus.status == "completed", 1), else_=0)
                    ).label("completed"),
                )
                .group_by(ImportStatus.file_type)
                .order_by(func.count().desc())
                .all()
            )

            print("\\n" + "-" * 80)
            print("FILE TYPE BREAKDOWN")
            print("-" * 80)

            for file_type, total, completed in file_type_summary:
                completion_rate = (completed / total * 100) if total > 0 else 0
                print(
                    f"{file_type:25} {total:>6} total    {completed:>6} done    {completion_rate:>5.1f}%"
                )

            # Enhanced statistics for retries and errors
            error_summary = (
                session.query(
                    func.count(case((ImportStatus.error_count > 0, 1))).label("files_with_errors"),
                    func.avg(case((ImportStatus.error_count > 0, ImportStatus.error_count))).label("avg_error_count"),
                    func.max(ImportStatus.error_count).label("max_error_count"),
                    func.count(case((ImportStatus.retry_at.isnot(None), 1))).label("files_pending_retry")
                )
                .first()
            )

            print("\\n" + "-" * 80)
            print("ERROR AND RETRY STATISTICS")
            print("-" * 80)
            
            print(f"Files with errors:     {error_summary.files_with_errors:>6}")
            print(f"Files pending retry:   {error_summary.files_pending_retry:>6}")
            print(f"Average error count:   {error_summary.avg_error_count:>6.1f}" if error_summary.avg_error_count else "Average error count:      0.0")
            print(f"Maximum error count:   {error_summary.max_error_count:>6}")


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database-Driven Parliament Data Importer")
    parser.add_argument('--file-type', type=str, help='Import only specific file type (legacy)')
    parser.add_argument('--file-types', nargs='*', 
                       choices=['XML', 'JSON', 'PDF', 'Archive', 'XSD'], 
                       default=['XML'],
                       help='File types to process (default: XML only)')
    parser.add_argument('--all-file-types', action='store_true',
                       help='Process all file types (overrides --file-types)')
    parser.add_argument('--legislatura', type=str, help='Import only specific legislatura')
    parser.add_argument('--limit', type=int, help='Limit number of files to process')
    parser.add_argument('--force-reimport', action='store_true',
                       help='Force reimport of completed files')
    parser.add_argument('--strict-mode', action='store_true',
                       help='Exit on first error')
    parser.add_argument('--watch', action='store_true',
                       help='Continuous mode: wait for new files instead of exiting')
    parser.add_argument('--watch-interval', type=int, default=10,
                       help='Seconds between checks for new files in watch mode (default: 10)')
    parser.add_argument('--log-level', type=str,
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       default='INFO',
                       help='Set logging level (default: INFO)')
    parser.add_argument('--status', action='store_true',
                       help='Show import status summary')
    parser.add_argument('--cleanup', action='store_true',
                       help='Drop all data tables (preserves ImportStatus and resets to "discovered")')
    parser.add_argument('--full-cleanup', action='store_true',
                       help='Drop ALL tables including ImportStatus (original cleanup behavior)')
    
    args = parser.parse_args()
    
    # Determine file types to process
    if args.all_file_types:
        allowed_file_types = None  # Process all file types
    elif args.file_type:  # Legacy support
        allowed_file_types = [args.file_type.upper()]
    else:
        allowed_file_types = args.file_types
    
    # Configure logging level for CLI usage
    log_level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(log_level)
    
    # Also update any existing handlers
    for handler in logging.getLogger().handlers:
        handler.setLevel(log_level)
    
    # Create and run importer with file type filter
    importer = DatabaseDrivenImporter(allowed_file_types=allowed_file_types)
    
    # Handle status, cleanup, and full-cleanup commands
    if args.status:
        importer.show_status()
        return
    elif args.cleanup:
        # Confirm cleanup action (preserves ImportStatus)
        print("WARNING: This will drop all data tables but preserve ImportStatus records!")
        print("All ImportStatus records will be reset to 'discovered' status for reprocessing.")
        confirmation = input("Are you sure you want to continue? (yes/no): ")
        if confirmation.lower() == "yes":
            importer.cleanup_database()
            print("Database cleanup completed successfully.")
        else:
            print("Cleanup cancelled.")
        return
    elif args.full_cleanup:
        # Confirm full cleanup action (drops everything)
        print("WARNING: This will drop ALL database tables including ImportStatus!")
        print("You will need to run discovery again to find files.")
        confirmation = input("Are you sure you want to continue? (yes/no): ")
        if confirmation.lower() == "yes":
            importer.full_cleanup_database()
            print("Full database cleanup completed successfully.")
        else:
            print("Full cleanup cancelled.")
        return
    
    if args.watch:
        # Continuous mode - watch for new files
        print(f">> Starting continuous import mode...")
        print(f"   File types: {', '.join(allowed_file_types) if allowed_file_types else 'ALL'}")
        if args.legislatura:
            print(f"   Legislature filter: {args.legislatura}")
        print(f"   Check interval: {args.watch_interval} seconds")
        print(f"   Press Ctrl+C to stop")
        
        import time
        import signal
        
        # Handle graceful shutdown
        def signal_handler(signum, frame):
            print(f"\n>> Received shutdown signal. Finishing current processing...")
            importer.set_shutdown_requested(True)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        total_stats = {'succeeded': 0, 'failed': 0, 'total_records': 0, 'processed': 0}
        
        try:
            while importer.is_running():
                # Process pending files
                stats = importer.process_pending_imports(
                    file_type_filter=args.file_type if args.file_type else None,
                    legislatura_filter=args.legislatura,
                    limit=args.limit,
                    force_reimport=args.force_reimport,
                    strict_mode=args.strict_mode
                )
                
                # Accumulate stats
                if stats['processed'] > 0:
                    total_stats['succeeded'] += stats['succeeded']
                    total_stats['failed'] += stats['failed'] 
                    total_stats['total_records'] += stats['total_records']
                    total_stats['processed'] += stats['processed']
                    
                    print(f">> Batch complete: {stats['succeeded']} successes, {stats['failed']} failures, {stats['total_records']} records")
                    print(f">> Session totals: {total_stats['succeeded']} successes, {total_stats['failed']} failures, {total_stats['total_records']} records")
                else:
                    print(f">> No pending files found, waiting {args.watch_interval} seconds...")
                
                # Wait before next check
                time.sleep(args.watch_interval)
                
        except KeyboardInterrupt:
            print(f"\n>> Keyboard interrupt received")
        finally:
            print(f"\n>> Watch mode completed:")
            print(f"   >> Total successes: {total_stats['succeeded']}")
            print(f"   >> Total failures: {total_stats['failed']}")
            print(f"   >> Total records imported: {total_stats['total_records']}")
    else:
        # Single run mode (original behavior)
        stats = importer.process_pending_imports(
            file_type_filter=args.file_type if args.file_type else None,  # Legacy support only
            legislatura_filter=args.legislatura,
            limit=args.limit,
            force_reimport=args.force_reimport,
            strict_mode=args.strict_mode
        )
        
        print(f"\n>> Import completed with {stats['succeeded']} successes, {stats['failed']} failures")


if __name__ == "__main__":
    main()