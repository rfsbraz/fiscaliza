#!/usr/bin/env python3
"""
Parallel Import Processor
=========================

Processes downloaded XML files in parallel using ProcessPoolExecutor.
Each worker process creates its own database session for isolation.

Features:
- ProcessPoolExecutor for CPU-bound XML parsing (bypasses GIL)
- Isolated database sessions per worker process
- Transaction-per-file model preserved
- Configurable worker count (respects connection pool limits)
"""

import asyncio
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Callable, List, Optional, Any


@dataclass
class ImportResult:
    """Result of an import operation"""
    status_id: int
    file_name: str
    file_path: str
    category: str
    success: bool
    records_imported: int = 0
    error_message: Optional[str] = None
    processing_duration: float = 0.0
    was_skipped: bool = False  # For permanently skipped files (corrupted data)


def _process_single_file(
    status_id: int,
    file_path: str,
    file_name: str,
    category: str
) -> ImportResult:
    """
    Process a single file in a separate process.

    This is the worker function that runs in ProcessPoolExecutor.

    CRITICAL: This function must:
    1. Create its own database session (sessions are not picklable)
    2. Handle its own transaction (commit/rollback)
    3. Return a serializable result (dataclass)
    """
    import sys
    import os
    import logging
    import threading

    # Add project root to path (needed for process isolation)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, '..', '..')
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    logger = logging.getLogger(__name__)
    pid = os.getpid()
    tid = threading.current_thread().name

    start_time = time.time()
    logger.debug(f"[IMPORT] Starting {file_name} (pid={pid}, thread={tid}, status_id={status_id})")

    try:
        # Import inside function to avoid pickling issues
        from database.connection import DatabaseSession
        from database.models import ImportStatus
        from scripts.data_processing.database_driven_importer import DatabaseDrivenImporter

        with DatabaseSession() as db_session:
            # Get the record fresh in this process
            record = db_session.get(ImportStatus, status_id)

            if not record:
                logger.warning(f"[IMPORT] Record not found: status_id={status_id}, file={file_name}")
                return ImportResult(
                    status_id=status_id,
                    file_name=file_name,
                    file_path=file_path,
                    category=category,
                    success=False,
                    error_message="Record not found in database"
                )

            # Create importer instance (each process gets its own)
            importer = DatabaseDrivenImporter(quiet=True, orchestrator_mode=True)

            # Process the file
            success = importer._process_single_import(db_session, record, strict_mode=False)

            duration = time.time() - start_time

            # Check if it was skipped vs failed
            was_skipped = record.status == 'skipped'

            if not success:
                # CRITICAL: The error handler in _process_single_import uses a FRESH session
                # to update error_message. Our `record` is stale - we need to refresh it!
                logger.debug(f"[IMPORT] Failed {file_name}: record.error_message before refresh = {record.error_message!r}")
                try:
                    db_session.expire(record)
                    db_session.refresh(record)
                    logger.debug(f"[IMPORT] Failed {file_name}: record.error_message after refresh = {record.error_message!r}")
                except Exception as refresh_err:
                    logger.warning(f"[IMPORT] Could not refresh record for {file_name}: {refresh_err}")

            return ImportResult(
                status_id=status_id,
                file_name=file_name,
                file_path=file_path,
                category=category,
                success=success,
                records_imported=record.records_imported or 0,
                processing_duration=duration,
                error_message=record.error_message if not success else None,
                was_skipped=was_skipped
            )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[IMPORT] Exception processing {file_name} (pid={pid}, thread={tid}): {type(e).__name__}: {e}")
        logger.debug(f"[IMPORT] Full traceback:\n{error_details}")
        return ImportResult(
            status_id=status_id,
            file_name=file_name,
            file_path=file_path,
            category=category,
            success=False,
            error_message=f"{str(e)}\n{error_details}",
            processing_duration=time.time() - start_time
        )


class ParallelImportProcessor:
    """
    Manages parallel import processing using ProcessPoolExecutor.

    Why ProcessPoolExecutor instead of async:
    1. XML parsing is CPU-bound (lxml/ElementTree)
    2. Python GIL prevents true parallelism with threads
    3. Separate processes bypass GIL for actual parallel processing
    4. Database connections are created fresh per process
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize parallel import processor

        Args:
            max_workers: Maximum parallel workers.
                         Limited to avoid overwhelming the database connection pool.
                         pool_size=8, max_overflow=12 means 20 total connections.
                         Reserve some for orchestrator/monitoring.
        """
        # Limit workers to avoid overwhelming the database connection pool
        self.max_workers = min(max_workers, 8)
        self._executor: Optional[ProcessPoolExecutor] = None
        self._running = False
        self._active_imports = 0  # Track active import count

    @property
    def active_imports(self) -> int:
        """Number of currently active import workers"""
        return self._active_imports

    async def start(self):
        """Start the process pool"""
        self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
        self._running = True

    async def stop(self):
        """Stop the process pool gracefully"""
        self._running = False
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=False)
            self._executor = None

    async def process_file(
        self,
        status_id: int,
        file_path: str,
        file_name: str,
        category: str
    ) -> ImportResult:
        """
        Process a single file in the process pool

        Args:
            status_id: ImportStatus.id from database
            file_path: Path to the downloaded file
            file_name: Original file name
            category: Import category

        Returns:
            ImportResult with success/failure info
        """
        if not self._executor:
            raise RuntimeError("ParallelImportProcessor not started. Call start() first.")

        loop = asyncio.get_event_loop()
        self._active_imports += 1

        try:
            result = await loop.run_in_executor(
                self._executor,
                _process_single_file,
                status_id,
                file_path,
                file_name,
                category
            )
            return result
        finally:
            self._active_imports -= 1

    async def process_batch(
        self,
        files: List[dict],
        progress_callback: Callable[[ImportResult], None] = None
    ) -> List[ImportResult]:
        """
        Process multiple files in parallel

        Args:
            files: List of dicts with keys: status_id, file_path, file_name, category
            progress_callback: Optional callback called after each file completes

        Returns:
            List of ImportResult objects
        """
        if not self._executor:
            raise RuntimeError("ParallelImportProcessor not started. Call start() first.")

        loop = asyncio.get_event_loop()

        # Create futures for all files
        futures = []
        for file_info in files:
            self._active_imports += 1
            future = loop.run_in_executor(
                self._executor,
                _process_single_file,
                file_info['status_id'],
                file_info['file_path'],
                file_info['file_name'],
                file_info['category']
            )
            futures.append((file_info, future))

        results = []

        # Gather results as they complete
        for file_info, future in futures:
            try:
                result = await future
                results.append(result)
                if progress_callback:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(result)
                    else:
                        progress_callback(result)
            except Exception as e:
                # Create error result for failed futures
                result = ImportResult(
                    status_id=file_info['status_id'],
                    file_name=file_info['file_name'],
                    file_path=file_info['file_path'],
                    category=file_info['category'],
                    success=False,
                    error_message=str(e)
                )
                results.append(result)
                if progress_callback:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(result)
                    else:
                        progress_callback(result)
            finally:
                self._active_imports -= 1

        return results
