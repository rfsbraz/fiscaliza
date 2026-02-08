#!/usr/bin/env python3
"""
Pipeline Logging Configuration
==============================

Provides structured logging for the parliament data pipeline that works well
in both interactive (local) and non-interactive (ECS/CloudWatch) environments.

Features:
- JSON format for CloudWatch Logs Insights queries
- Periodic progress summaries
- Structured metadata for filtering
- Automatic environment detection

CloudWatch Logs Insights example queries:
-----------------------------------------
# Find all errors:
fields @timestamp, level, message, file_name, error
| filter level = "ERROR"
| sort @timestamp desc

# Track import progress:
fields @timestamp, stage, completed, total, records_imported
| filter event_type = "progress"
| sort @timestamp asc

# Get summary statistics:
fields @timestamp, succeeded, failed, total_records
| filter event_type = "summary"
"""

import json
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, Optional


def is_interactive() -> bool:
    """Detect if running in interactive mode (TTY) vs ECS/CI."""
    # Check if stdout is a TTY
    if not sys.stdout.isatty():
        return False

    # Check for ECS environment indicators
    if os.getenv('AWS_EXECUTION_ENV'):
        return False
    if os.getenv('ECS_CONTAINER_METADATA_URI'):
        return False
    if os.getenv('ECS_CONTAINER_METADATA_URI_V4'):
        return False

    # Check for CI environments
    if os.getenv('CI'):
        return False
    if os.getenv('GITHUB_ACTIONS'):
        return False

    return True


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured CloudWatch logging."""

    def __init__(self, extra_fields: Dict[str, Any] = None):
        super().__init__()
        self.extra_fields = extra_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add extra fields from the log record
        if hasattr(record, 'event_type'):
            log_entry['event_type'] = record.event_type
        if hasattr(record, 'stage'):
            log_entry['stage'] = record.stage
        if hasattr(record, 'file_name'):
            log_entry['file_name'] = record.file_name
        if hasattr(record, 'category'):
            log_entry['category'] = record.category
        if hasattr(record, 'records_imported'):
            log_entry['records_imported'] = record.records_imported
        if hasattr(record, 'error'):
            log_entry['error'] = record.error
        if hasattr(record, 'duration_seconds'):
            log_entry['duration_seconds'] = record.duration_seconds

        # Add stats if present
        if hasattr(record, 'stats'):
            log_entry['stats'] = record.stats

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add configured extra fields
        log_entry.update(self.extra_fields)

        return json.dumps(log_entry, default=str)


class ConsoleProgressFormatter(logging.Formatter):
    """Human-readable formatter for console output with progress tracking."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Format based on event type
        if hasattr(record, 'event_type'):
            if record.event_type == 'progress':
                stage = getattr(record, 'stage', 'unknown')
                completed = getattr(record, 'completed', 0)
                total = getattr(record, 'total', 0)
                records = getattr(record, 'records_imported', 0)
                return f"[{timestamp}] PROGRESS | {stage}: {completed}/{total} | Records: {records:,}"

            elif record.event_type == 'file_complete':
                file_name = getattr(record, 'file_name', 'unknown')
                records = getattr(record, 'records_imported', 0)
                duration = getattr(record, 'duration_seconds', 0)
                return f"[{timestamp}] OK | {file_name} | {records} records | {duration:.1f}s"

            elif record.event_type == 'file_error':
                file_name = getattr(record, 'file_name', 'unknown')
                error = getattr(record, 'error', 'unknown error')
                return f"[{timestamp}] ERROR | {file_name} | {error}"

            elif record.event_type == 'summary':
                stats = getattr(record, 'stats', {})
                succeeded = stats.get('succeeded', 0)
                failed = stats.get('failed', 0)
                records = stats.get('total_records', 0)
                duration = stats.get('duration_seconds', 0)
                return (f"[{timestamp}] SUMMARY | "
                       f"Succeeded: {succeeded} | Failed: {failed} | "
                       f"Records: {records:,} | Duration: {duration:.0f}s")

        # Default format
        level_colors = {
            'DEBUG': '',
            'INFO': '',
            'WARNING': 'WARN',
            'ERROR': 'ERROR',
            'CRITICAL': 'CRIT',
        }
        level = level_colors.get(record.levelname, record.levelname)
        return f"[{timestamp}] {level} | {record.getMessage()}"


def setup_pipeline_logging(
    name: str = 'pipeline',
    level: int = logging.INFO,
    force_json: bool = False,
    extra_fields: Dict[str, Any] = None
) -> logging.Logger:
    """
    Configure logging for the pipeline.

    Args:
        name: Logger name
        level: Logging level
        force_json: Force JSON output even in interactive mode
        extra_fields: Extra fields to include in every log entry

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Choose formatter based on environment
    if force_json or not is_interactive():
        handler.setFormatter(JsonFormatter(extra_fields))
    else:
        handler.setFormatter(ConsoleProgressFormatter())

    logger.addHandler(handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


@dataclass
class PipelineProgress:
    """Track pipeline progress for logging."""
    stage: str = "initializing"
    discovery_total: int = 0
    discovery_completed: int = 0
    download_total: int = 0
    download_completed: int = 0
    download_failed: int = 0
    import_total: int = 0
    import_completed: int = 0
    import_failed: int = 0
    import_skipped: int = 0
    total_records_imported: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_log_time: datetime = field(default_factory=datetime.now)

    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'stage': self.stage,
            'discovery': {'total': self.discovery_total, 'completed': self.discovery_completed},
            'download': {'total': self.download_total, 'completed': self.download_completed, 'failed': self.download_failed},
            'import': {'total': self.import_total, 'completed': self.import_completed, 'failed': self.import_failed, 'skipped': self.import_skipped},
            'total_records': self.total_records_imported,
            'elapsed_seconds': self.elapsed_seconds
        }


class ProgressLogger:
    """
    Logs progress at regular intervals.

    Usage:
        progress = ProgressLogger(logger, interval=30)
        progress.start()

        # Update stats as work progresses
        progress.stats.import_completed += 1
        progress.stats.total_records_imported += 100

        # Will automatically log every 30 seconds

        progress.stop()
        progress.log_summary()
    """

    def __init__(
        self,
        logger: logging.Logger,
        interval: float = 30.0,
        stats: PipelineProgress = None
    ):
        self.logger = logger
        self.interval = interval
        self.stats = stats or PipelineProgress()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self):
        """Start periodic progress logging."""
        self._running = True
        self._thread = threading.Thread(target=self._log_loop, daemon=True)
        self._thread.start()

        # Log initial start
        self.logger.info(
            "Pipeline started",
            extra={'event_type': 'start', 'stage': self.stats.stage}
        )

    def stop(self):
        """Stop periodic progress logging."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _log_loop(self):
        """Background loop for periodic logging."""
        while self._running:
            time.sleep(self.interval)
            if self._running:
                self.log_progress()

    def log_progress(self):
        """Log current progress."""
        with self._lock:
            stats = self.stats

            # Determine current stage and progress
            if stats.stage == 'discovery':
                completed = stats.discovery_completed
                total = stats.discovery_total or completed
            elif stats.stage == 'download':
                completed = stats.download_completed
                total = stats.download_total or completed
            elif stats.stage == 'import':
                completed = stats.import_completed
                total = stats.import_total or completed
            else:
                completed = stats.import_completed
                total = stats.import_total

            self.logger.info(
                f"{stats.stage}: {completed}/{total} completed, {stats.total_records_imported:,} records",
                extra={
                    'event_type': 'progress',
                    'stage': stats.stage,
                    'completed': completed,
                    'total': total,
                    'records_imported': stats.total_records_imported,
                    'stats': stats.to_dict()
                }
            )

    def log_file_complete(self, file_name: str, records: int, duration: float, category: str = None):
        """Log successful file completion."""
        with self._lock:
            self.stats.import_completed += 1
            self.stats.total_records_imported += records

        self.logger.info(
            f"Imported {file_name}: {records} records in {duration:.1f}s",
            extra={
                'event_type': 'file_complete',
                'file_name': file_name,
                'category': category,
                'records_imported': records,
                'duration_seconds': duration
            }
        )

    def log_file_error(self, file_name: str, error: str, category: str = None):
        """Log file processing error."""
        with self._lock:
            self.stats.import_failed += 1

        self.logger.error(
            f"Failed to import {file_name}: {error}",
            extra={
                'event_type': 'file_error',
                'file_name': file_name,
                'category': category,
                'error': error
            }
        )

    def log_file_skipped(self, file_name: str, reason: str = None):
        """Log skipped file."""
        with self._lock:
            self.stats.import_skipped += 1

        self.logger.info(
            f"Skipped {file_name}" + (f": {reason}" if reason else ""),
            extra={
                'event_type': 'file_skipped',
                'file_name': file_name,
                'reason': reason
            }
        )

    def log_summary(self):
        """Log final summary statistics."""
        stats = self.stats

        summary = {
            'succeeded': stats.import_completed,
            'failed': stats.import_failed,
            'skipped': stats.import_skipped,
            'total_records': stats.total_records_imported,
            'duration_seconds': stats.elapsed_seconds,
            'discovery_found': stats.discovery_completed,
            'download_completed': stats.download_completed,
            'download_failed': stats.download_failed
        }

        self.logger.info(
            f"Pipeline complete: {stats.import_completed} succeeded, {stats.import_failed} failed, "
            f"{stats.total_records_imported:,} records in {stats.elapsed_seconds:.0f}s",
            extra={
                'event_type': 'summary',
                'stats': summary
            }
        )

    def set_stage(self, stage: str):
        """Update current pipeline stage."""
        with self._lock:
            self.stats.stage = stage

        self.logger.info(
            f"Stage: {stage}",
            extra={'event_type': 'stage_change', 'stage': stage}
        )


# Convenience function for quick setup
def get_pipeline_logger(force_json: bool = None) -> logging.Logger:
    """
    Get a configured pipeline logger.

    Args:
        force_json: Force JSON output (None = auto-detect based on environment)
    """
    if force_json is None:
        force_json = not is_interactive()

    return setup_pipeline_logging(
        name='parliament.pipeline',
        force_json=force_json,
        extra_fields={'service': 'parliament-pipeline'}
    )
