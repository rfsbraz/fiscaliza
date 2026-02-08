#!/usr/bin/env python3
"""
Parliament Data Pipeline Orchestrator
====================================

Orchestrates the complete parliament data pipeline with parallel processing:
1. Discovery Service - Finds and catalogs file URLs
2. Download Manager - Downloads files on-demand
3. Import Processor - Processes downloaded files

Features:
- Rich terminal UI with live progress tracking
- Shared queue management between services
- Rate limiting for discovery and downloads
- Parallel execution with proper coordination
- Real-time status updates and statistics
"""

import argparse
import asyncio
import contextlib
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, List, Optional

import requests
from rich.console import Console
from http_retry_utils import HTTPRetryClient
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress, TaskID, BarColumn, TextColumn, TimeElapsedColumn, 
    SpinnerColumn, MofNCompleteColumn
)
from rich.table import Table
from rich.text import Text

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from database.connection import DatabaseSession
from database.models import ImportStatus
from scripts.data_processing.discovery_service import DiscoveryService


@dataclass
class DownloadInfo:
    """Information about a downloaded file"""
    file_name: str
    file_size: int
    timestamp: str
    status_id: int

@dataclass
class PipelineStats:
    """Pipeline statistics for UI display"""
    discovery_total: int = 0
    discovery_completed: int = 0
    discovery_running: bool = False
    discovery_status: str = "Waiting"
    download_queue_size: int = 0
    download_completed: int = 0
    download_failed: int = 0
    import_queue_size: int = 0
    import_completed: int = 0
    import_failed: int = 0
    import_skipped: int = 0  # Files permanently skipped due to corrupted source data
    total_records_imported: int = 0
    start_time: Optional[datetime] = None
    recent_messages: List[str] = None
    downloaded_files: List[DownloadInfo] = None
    stop_on_error: bool = False
    error_occurred: bool = False
    pinned_errors: List[str] = None  # Errors that stay visible at top of activity log
    # Current file being processed
    current_file: Optional[str] = None
    current_file_category: Optional[str] = None
    current_file_started: Optional[datetime] = None
    current_file_is_retry: bool = False

    def __post_init__(self):
        if self.recent_messages is None:
            self.recent_messages = []
        if self.downloaded_files is None:
            self.downloaded_files = []
        if self.pinned_errors is None:
            self.pinned_errors = []
        # Initialize thread-safe attributes upfront to avoid race conditions
        self._message_lock = threading.Lock()
        self._message_buffer = {}
        self._last_summary_time = datetime.now()
        self._last_debug_time = datetime.now()

    def add_message(self, message: str, priority: str = 'normal'):
        """Add a message to recent messages with priority-based filtering"""

        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"{timestamp} - {message}"

        with self._message_lock:
            # Pin error messages so they stay visible even when idle messages come in
            if priority == 'error':
                self.pinned_errors.append(formatted_message)
                if len(self.pinned_errors) > 5:  # Keep last 5 errors pinned
                    self.pinned_errors.pop(0)

            # Handle high priority messages immediately
            if priority in ['high', 'error', 'success']:
                self.recent_messages.append(formatted_message)
                if len(self.recent_messages) > 10:
                    self.recent_messages.pop(0)
                return
            
            # For normal/verbose messages, use buffering to reduce flashing
            current_time = datetime.now()
            
            # Group similar messages
            message_key = self._get_message_key(message)
            if message_key not in self._message_buffer:
                self._message_buffer[message_key] = {
                    'count': 0,
                    'first_time': current_time,
                    'last_message': message
                }
            
            self._message_buffer[message_key]['count'] += 1
            self._message_buffer[message_key]['last_message'] = message
            
            # Flush buffer every 3 seconds or when it gets full
            time_since_summary = (current_time - self._last_summary_time).total_seconds()
            if time_since_summary >= 3.0 or len(self._message_buffer) >= 5:
                self._flush_message_buffer()
                self._last_summary_time = current_time
    
    def _get_message_key(self, message: str) -> str:
        """Extract key from message for grouping similar messages"""
        if 'Downloaded:' in message:
            return 'downloads'
        elif 'Processing:' in message:
            return 'processing'
        elif 'SUCCESS:' in message:
            return 'successes'
        elif 'FAILED:' in message or 'ERROR:' in message:
            return 'failures'
        else:
            return 'other'
    
    def _flush_message_buffer(self):
        """Flush buffered messages as summary"""
        if not self._message_buffer:
            return
            
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        for key, info in self._message_buffer.items():
            if info['count'] == 1:
                # Single message, show as-is
                formatted_message = f"{timestamp} - {info['last_message']}"
            else:
                # Multiple messages, show summary
                if key == 'downloads':
                    formatted_message = f"{timestamp} - Downloaded {info['count']} files"
                elif key == 'processing':
                    formatted_message = f"{timestamp} - Processed {info['count']} files"
                elif key == 'successes':
                    formatted_message = f"{timestamp} - {info['count']} files imported successfully"
                elif key == 'failures':
                    formatted_message = f"{timestamp} - {info['count']} files failed processing"
                else:
                    formatted_message = f"{timestamp} - {info['count']} operations completed"
            
            self.recent_messages.append(formatted_message)
            if len(self.recent_messages) > 10:
                self.recent_messages.pop(0)
        
        # Clear buffer
        self._message_buffer.clear()
    
    def add_download(self, file_name: str, file_size: int, status_id: int):
        """Add a downloaded file to the list (keep last 15)"""
        download_info = DownloadInfo(
            file_name=file_name,
            file_size=file_size,
            timestamp=datetime.now().strftime('%H:%M:%S'),
            status_id=status_id
        )
        self.downloaded_files.append(download_info)
        if len(self.downloaded_files) > 15:
            self.downloaded_files.pop(0)
    
    @property
    def elapsed_time(self) -> str:
        if not self.start_time:
            return "00:00:00"
        elapsed = datetime.now() - self.start_time
        total_seconds = int(elapsed.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class DownloadManager:
    """Manages file downloads from URLs in the database"""
    
    def __init__(self, rate_limit_delay: float = 0.3, allowed_file_types: List[str] = None):
        self.rate_limit_delay = rate_limit_delay
        self.allowed_file_types = allowed_file_types or ['XML']  # Default to XML only
        # Use HTTP retry client for robust downloads
        self.http_client = HTTPRetryClient(
            max_retries=5,
            initial_backoff=1.0,
            max_backoff=120.0,
            backoff_multiplier=2.0,
            timeout=30,
            user_agent='Fiscaliza/1.0 (https://fiscaliza.pt; open-source parliamentary data)'
        )
        self.running = False
        
        # Create downloads directory relative to this script's location
        script_dir = Path(__file__).parent
        self.downloads_dir = script_dir / "data" / "downloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
    
    @contextlib.contextmanager
    def _capture_console(self, stats: PipelineStats):
        """Context manager to capture console output from HTTP retry utils"""
        import sys
        import io
        import contextlib
        
        # Capture stdout
        old_stdout = sys.stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            yield
        finally:
            # Restore stdout
            sys.stdout = old_stdout
            
            # Process captured output
            output = captured_output.getvalue()
            if output.strip():
                # Split into lines and send important ones to stats
                lines = output.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line:
                        # Skip verbose HTTP retry messages, only keep important ones
                        if any(marker in line for marker in ['ERROR:', 'Max retries', 'Last error:']):
                            stats.add_message(f"Download error: {line.split('ERROR:')[-1].strip()}", priority='error')
                        elif 'SUCCESS: Resetting exponential backoff' in line:
                            # Don't spam this, it's too verbose
                            pass
                        elif 'Retrying in' in line:
                            # Suppress retry spam, just note retries are happening
                            pass
        
    def start(self, download_queue: Queue, stats: PipelineStats, console: Console):
        """Start download processing"""
        self.running = True
        
        while self.running:
            try:
                # Use a fresh database session for each iteration to avoid stale data
                with DatabaseSession() as db_session:
                    # Get files that need downloading (filtered by file type)
                    query = db_session.query(ImportStatus).filter(
                        ImportStatus.status.in_(['discovered', 'download_pending'])
                    )
                    
                    # Apply file type filter
                    if self.allowed_file_types:
                        query = query.filter(ImportStatus.file_type.in_(self.allowed_file_types))

                    # Deterministic ordering for reproducibility
                    files_to_download = query.order_by(
                        ImportStatus.category,
                        ImportStatus.legislatura,
                        ImportStatus.file_name
                    ).limit(10).all()
                    
                    if not files_to_download:
                        time.sleep(1)
                        continue
                    
                    # Log when we start processing downloads
                    stats.add_message(f"Download manager: found {len(files_to_download)} files to download", priority='normal')
                    
                    for import_record in files_to_download:
                        if not self.running:
                            break
                            
                        try:
                            # Update status to downloading
                            import_record.status = 'downloading'
                            db_session.commit()
                            
                            # Download file content with retry logic
                            response = self.http_client.get(import_record.file_url)
                            
                            # Calculate file hash
                            import hashlib
                            file_hash = hashlib.sha1(response.content).hexdigest()
                            
                            # Save file to disk using ImportStatus ID as identifier
                            file_extension = Path(import_record.file_name).suffix or '.xml'
                            local_filename = f"{import_record.id}_{import_record.file_name}"
                            local_file_path = self.downloads_dir / local_filename
                            
                            # Write file to disk
                            with open(local_file_path, 'wb') as f:
                                f.write(response.content)
                            
                            # Update import record
                            import_record.file_path = str(local_file_path)
                            import_record.file_hash = file_hash
                            import_record.file_size = len(response.content)
                            import_record.status = 'pending'  # Ready for import
                            import_record.updated_at = datetime.now()
                            
                            db_session.commit()
                            
                            # Add to import queue
                            download_queue.put(import_record.id)
                            
                            # Add to download tracking and message log
                            stats.add_download(import_record.file_name, import_record.file_size, import_record.id)
                            stats.add_message(f"Downloaded: {import_record.file_name} ({import_record.file_size:,} bytes)", priority='normal')
                            
                        except Exception as e:
                            # Check if this is a 404/not found error that should trigger recrawl
                            error_str = str(e).lower()
                            is_not_found_error = (
                                '404' in error_str or 
                                'not found' in error_str or 
                                'file not found' in error_str or
                                'no such file' in error_str or
                                hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 404
                            )
                            
                            if is_not_found_error:
                                import_record.status = 'recrawl'
                                import_record.error_message = f"File not found, marked for recrawl: {str(e)}"
                                stats.add_message(f"File not found, marking for recrawl: {import_record.file_name}", priority='high')
                            else:
                                import_record.status = 'failed'
                                import_record.error_message = f"Download error: {str(e)}"
                                stats.add_message(f"Download failed: {import_record.file_name} - {str(e)}", priority='error')
                                stats.error_occurred = True

                            db_session.commit()
                        
                        # Rate limiting
                        time.sleep(self.rate_limit_delay)
                        
            except Exception as e:
                stats.add_message(f"Download manager error: {str(e)}", priority='error')
                stats.error_occurred = True
                time.sleep(1)

    def stop(self):
        """Stop download processing"""
        self.running = False


class ImportProcessor:
    """Processes downloaded files for import"""
    
    def __init__(self, allowed_file_types: List[str] = None):
        self.running = False
        self.allowed_file_types = allowed_file_types or ['XML']  # Default to XML only
        # Use the database-driven importer instead
        from scripts.data_processing.database_driven_importer import DatabaseDrivenImporter
        self.importer = DatabaseDrivenImporter(allowed_file_types=self.allowed_file_types, quiet=True, orchestrator_mode=True)
    
    def start(self, download_queue: Queue, stats: PipelineStats, console: Console):
        """Start import processing"""
        self.running = True
        
        while self.running:
            try:
                # Use a fresh database session for each iteration
                with DatabaseSession() as db_session:
                    # First, check download queue for priority files
                    record_id = None
                    from_queue = False
                    
                    try:
                        record_id = download_queue.get(timeout=0.5)
                        from_queue = True
                    except Empty:
                        # If no files in download queue, check for any pending or errored files (filtered by file type)
                        # Include import_error so errored files get reprocessed in the predefined order
                        query = db_session.query(ImportStatus).filter(
                            ImportStatus.status.in_(['pending', 'import_error'])
                        )
                        
                        # Apply file type filter
                        if self.allowed_file_types:
                            query = query.filter(ImportStatus.file_type.in_(self.allowed_file_types))

                        # Deterministic ordering for reproducibility
                        pending_files = query.order_by(
                            ImportStatus.category,
                            ImportStatus.legislatura,
                            ImportStatus.file_name
                        ).limit(1).all()
                        
                        if pending_files:
                            record_id = pending_files[0].id
                            from_queue = False
                        else:
                            time.sleep(1)
                            continue
                        
                    # Get the import record
                    import_record = db_session.get(ImportStatus, record_id)
                    if not import_record or import_record.status not in ['pending', 'discovered', 'download_pending', 'import_error']:
                        continue

                    # Check if this is a retry
                    is_retry = import_record.status == 'import_error'

                    # Track current file being processed
                    stats.current_file = import_record.file_name
                    stats.current_file_category = import_record.category
                    stats.current_file_started = datetime.now()
                    stats.current_file_is_retry = is_retry

                    try:
                        if is_retry:
                            stats.add_message(f"RETRY: {import_record.file_name} (attempt {(import_record.error_count or 0) + 1})", priority='high')
                        else:
                            stats.add_message(f"Processing: {import_record.file_name}", priority='normal')

                        # Use the actual database-driven importer (now in quiet mode)
                        success = self.importer._process_single_import(db_session, import_record, strict_mode=False)
                        
                        if success:
                            stats.add_message(f"SUCCESS: {import_record.file_name} ({import_record.records_imported or 0} records)", priority='success')
                            # Commit successful import to database
                            db_session.commit()
                        elif import_record.status == 'skipped':
                            # Permanently skipped files (corrupted source) - not a real error
                            error_msg = import_record.error_message or "Corrupted source data"
                            stats.add_message(f"SKIPPED: {import_record.file_name}", priority='warning')
                            stats.add_message(f"  Reason: {error_msg}", priority='warning')
                            # Commit skipped status to database (don't set error_occurred)
                            db_session.commit()
                        else:
                            error_msg = import_record.error_message or "Unknown error"
                            stats.add_message(f"FAILED: {import_record.file_name}", priority='error')
                            stats.add_message(f"  Error: {error_msg}", priority='error')
                            stats.error_occurred = True
                            # Commit failed import status to database
                            db_session.commit()

                    except Exception as e:
                        error_msg = str(e)
                        stats.add_message(f"ERROR: {import_record.file_name}", priority='error')
                        stats.add_message(f"  Exception: {error_msg}", priority='error')
                        stats.error_occurred = True
                        
                        # Update record status if not already updated
                        if import_record.status not in ['completed', 'import_error']:
                            import_record.status = 'import_error'
                            import_record.error_message = str(e)
                            import_record.error_count = (import_record.error_count or 0) + 1
                            import_record.processing_completed_at = datetime.now()
                            try:
                                db_session.commit()
                            except Exception:
                                db_session.rollback()
                        
                    finally:
                        # Clear current file tracking
                        stats.current_file = None
                        stats.current_file_category = None
                        stats.current_file_started = None
                        stats.current_file_is_retry = False

                        # Only mark task done if it came from download queue
                        if from_queue:
                            try:
                                download_queue.task_done()
                            except ValueError:
                                pass  # Ignore if task_done called more times than get
                        
            except Exception as e:
                stats.add_message(f"Import processor error: {str(e)}", priority='error')
                stats.error_occurred = True
                time.sleep(1)

    def stop(self):
        """Stop import processing"""
        self.running = False
        # Also signal the database importer to stop
        if hasattr(self, 'importer'):
            self.importer.set_shutdown_requested(True)


class PipelineOrchestrator:
    """Main orchestrator for the parliament data pipeline"""

    def __init__(self, discovery_rate_limit: float = 0.5, download_rate_limit: float = 0.3,
                 allowed_file_types: List[str] = None, stop_on_error: bool = False,
                 download_only: bool = False, import_only: bool = False):
        self.console = Console()
        self.stats = PipelineStats()
        self.stats.stop_on_error = stop_on_error
        self.download_only = download_only
        self.import_only = import_only
        self.allowed_file_types = allowed_file_types or ['XML']  # Default to XML only
        
        # Initialize services with file type filters
        self.discovery_service = DiscoveryService(rate_limit_delay=discovery_rate_limit, quiet=True)
        self.download_manager = DownloadManager(rate_limit_delay=download_rate_limit, 
                                              allowed_file_types=self.allowed_file_types)
        self.import_processor = ImportProcessor(allowed_file_types=self.allowed_file_types)
        
        # Shared queues
        self.download_queue = Queue()
        
        # Threading
        self.threads = []
        self.running = False
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                if unit == 'B':
                    return f"{size_bytes} {unit}"
                else:
                    return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        
        return f"{size_bytes:.1f} TB"
    
    def _get_pending_files(self, limit: int = 10) -> List:
        """Get pending files from ImportStatus table (filtered by file type)"""
        try:
            with DatabaseSession() as db_session:
                query = db_session.query(ImportStatus).filter(
                    ImportStatus.status.in_(['discovered', 'download_pending', 'pending', 'recrawl', 'import_error'])
                )
                
                # Apply file type filter
                if self.allowed_file_types:
                    query = query.filter(ImportStatus.file_type.in_(self.allowed_file_types))

                # Deterministic ordering for reproducibility
                pending_files = query.order_by(
                    ImportStatus.category,
                    ImportStatus.legislatura,
                    ImportStatus.file_name
                ).limit(limit).all()
                
                return pending_files
        except Exception as e:
            self.stats.add_message(f"Error getting pending files: {str(e)}", priority='error')
            self.stats.error_occurred = True
            return []
        
    def create_ui_layout(self) -> Layout:
        """Create Rich layout for the UI"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=2)
        )
        
        # Split left panel into discovery (top), stats (middle) and downloads (bottom)
        layout["left"].split_column(
            Layout(name="discovery", ratio=1),
            Layout(name="stats", ratio=1),
            Layout(name="downloads", minimum_size=8, ratio=1)  # Fixed minimum height
        )
        
        # Split right panel into pending files (top) and activity log (bottom)
        layout["right"].split_column(
            Layout(name="pending", ratio=1),
            Layout(name="activity", ratio=1)
        )
        
        return layout
        
    def update_layout(self, layout: Layout):
        """Update the Rich layout with current data"""
        # Header with file type filter information
        file_types_info = ", ".join(self.allowed_file_types) if self.allowed_file_types else "ALL"
        header_text = f"Parliament Data Pipeline Orchestrator - Runtime: {self.stats.elapsed_time} | File Types: {file_types_info}"
        
        layout["header"].update(
            Panel(
                header_text,
                style="bold blue"
            )
        )
        
        # Discovery Service Status Panel
        discovery_text = f"""Discovery Service

The discovery service is the first stage of the parliament data pipeline. It crawls the official Parliament website (parlamento.pt) to find and catalog all available data files.

🔍 Current Operation:
• Status: {self.stats.discovery_status}
• Files Found: {self.stats.discovery_completed}
• Running: {'Yes' if self.stats.discovery_running else 'No'}

🌐 Process:
• Navigates parliament sections systematically
• Extracts file URLs, categories, and legislatures  
• Uses tiered discovery with context preservation
• Stores metadata for download and processing
• HTTP retry logic handles connection issues

The service respects rate limits and uses exponential backoff to avoid overwhelming parliament servers while ensuring comprehensive data discovery."""

        discovery_panel = Panel(
            discovery_text,
            title="Discovery Service Status",
            border_style="yellow"
        )
        layout["discovery"].update(discovery_panel)
        
        # Stats table
        stats_table = Table(title="Pipeline Statistics", show_header=True)
        stats_table.add_column("Stage", style="cyan")
        stats_table.add_column("Status", justify="right")
        
        stats_table.add_row(
            "Discovery",
            f"{self.stats.discovery_completed} files cataloged"
        )
        stats_table.add_row(
            "Downloads",
            f"OK: {self.stats.download_completed} | ERR: {self.stats.download_failed} | PENDING: {self.stats.download_queue_size}"
        )
        skipped_display = f" | SKIP: {self.stats.import_skipped}" if self.stats.import_skipped > 0 else ""
        stats_table.add_row(
            "Imports",
            f"OK: {self.stats.import_completed} | ERR: {self.stats.import_failed}{skipped_display} | PENDING: {self.stats.import_queue_size}"
        )
        stats_table.add_row(
            "Records",
            f"{self.stats.total_records_imported:,} total imported"
        )

        # Current file being processed
        if self.stats.current_file:
            elapsed = ""
            if self.stats.current_file_started:
                elapsed_secs = (datetime.now() - self.stats.current_file_started).total_seconds()
                elapsed = f" ({int(elapsed_secs)}s)"
            retry_indicator = "[yellow]RETRY[/yellow] " if self.stats.current_file_is_retry else ""
            file_display = self.stats.current_file
            if len(file_display) > 30:
                file_display = file_display[:27] + "..."
            stats_table.add_row(
                "[bold]Processing[/bold]",
                f"{retry_indicator}{file_display}{elapsed}"
            )
        else:
            stats_table.add_row(
                "Processing",
                "[dim]Idle[/dim]"
            )

        layout["stats"].update(Panel(stats_table, border_style="green"))
        
        # Downloaded files tracking with stable panel updates
        downloads_count = len(self.stats.downloaded_files) if self.stats.downloaded_files else 0
        
        # Only update downloads panel if there are actual downloads to show
        if downloads_count > 0:
            downloads_table = Table(show_header=True, header_style="bold magenta")
            downloads_table.add_column("Time", style="dim", width=8)
            downloads_table.add_column("File", style="cyan", width=25)
            downloads_table.add_column("Size", justify="right", width=10)
            downloads_table.add_column("ID", justify="right", width=6)
            
            # Show last 10 downloads
            for download in self.stats.downloaded_files[-10:]:
                file_display = download.file_name
                if len(file_display) > 22:
                    file_display = file_display[:19] + "..."
                
                # Format file size
                size_str = self._format_file_size(download.file_size)
                
                downloads_table.add_row(
                    download.timestamp,
                    file_display,
                    size_str,
                    str(download.status_id)
                )
            
            downloads_panel = Panel(downloads_table, title=f"Downloaded Files ({downloads_count})", border_style="blue")
            layout["downloads"].update(downloads_panel)
            self._downloads_panel_set = 'files'
        else:
            # Only update the panel when it hasn't been set yet or when transitioning from files to no files
            if not hasattr(self, '_downloads_panel_set') or self._downloads_panel_set != 'empty':
                # Create a stable empty table to maintain consistent height
                empty_table = Table(show_header=True, header_style="bold magenta")
                empty_table.add_column("Time", style="dim", width=8)
                empty_table.add_column("File", style="cyan", width=25)
                empty_table.add_column("Size", justify="right", width=10)
                empty_table.add_column("ID", justify="right", width=6)
                
                # Add a single row with waiting message
                empty_table.add_row("--:--:--", "Waiting for downloads...", "--", "--")
                
                downloads_panel = Panel(
                    empty_table, 
                    title="Downloaded Files", 
                    border_style="blue"
                )
                layout["downloads"].update(downloads_panel)
                self._downloads_panel_set = 'empty'
        
        # Pending files for processing
        pending_files = self._get_pending_files(12)
        if pending_files:
            pending_table = Table(show_header=True, header_style="bold green")
            pending_table.add_column("Status", style="yellow", width=12)
            pending_table.add_column("File", style="cyan", width=25)
            pending_table.add_column("Category", style="magenta", width=30)
            pending_table.add_column("Legislature", width=15)
            
            for file_record in pending_files:
                file_display = file_record.file_name
                if len(file_display) > 22:
                    file_display = file_display[:19] + "..."
                    
                category_display = file_record.category or "Unknown"
                if len(category_display) > 27:
                    category_display = category_display[:24] + "..."
                
                # Color code status
                status_display = file_record.status
                if file_record.status == 'discovered':
                    status_display = "[blue]discovered[/blue]"
                elif file_record.status == 'download_pending':
                    status_display = "[yellow]dl_pending[/yellow]"
                elif file_record.status == 'pending':
                    status_display = "[green]ready[/green]"
                elif file_record.status == 'recrawl':
                    status_display = "[orange]recrawl[/orange]"
                elif file_record.status == 'import_error':
                    status_display = "[red]error[/red]"
                elif file_record.status == 'skipped':
                    status_display = "[dim]skipped[/dim]"

                pending_table.add_row(
                    status_display,
                    file_display,
                    category_display,
                    file_record.legislatura or "N/A"
                )
                
            pending_panel = Panel(pending_table, title=f"Files Ready for Processing ({len(pending_files)})", border_style="green")
        else:
            pending_panel = Panel("No pending files found", title="Files Ready for Processing", border_style="green")
            
        layout["pending"].update(pending_panel)

        # Recent activity log with pinned errors at top
        activity_lines = []

        # Show pinned errors at the top (in red, always visible)
        if self.stats.pinned_errors:
            activity_lines.append("[bold red]━━━ ERRORS (pinned) ━━━[/bold red]")
            for error in self.stats.pinned_errors:
                activity_lines.append(f"[red]{error}[/red]")
            activity_lines.append("[dim]━━━━━━━━━━━━━━━━━━━━━━[/dim]")

        # Show recent messages below
        if self.stats.recent_messages:
            # Calculate how many recent messages we can show (leave room for pinned errors)
            pinned_count = len(self.stats.pinned_errors) + 2 if self.stats.pinned_errors else 0
            max_recent = max(3, 10 - pinned_count)  # At least 3 recent messages
            activity_lines.extend(self.stats.recent_messages[-max_recent:])
        elif not self.stats.pinned_errors:
            activity_lines.append("Waiting for activity...")

        messages_text = "\n".join(activity_lines)

        activity_panel = Panel(
            messages_text,
            title="Processing Activity Log",
            border_style="red" if self.stats.pinned_errors else "yellow"
        )
        layout["activity"].update(activity_panel)
        
        # Footer
        layout["footer"].update(
            Panel(
                "Press Ctrl+C to stop gracefully",
                style="dim"
            )
        )
    
    def run_discovery(self, legislature_filter: str = None, category_filter: str = None):
        """Run discovery in background thread"""
        try:
            self.stats.discovery_running = True
            self.stats.discovery_status = "Starting up..."
            self.stats.add_message("Discovery service starting up...", priority='high')
            
            # Add intermediate status updates
            self.stats.discovery_status = "Connecting to parliament website..."
            self.stats.add_message("Connecting to parliament data portal...", priority='high')
            
            # Discovery service now runs in quiet mode to prevent UI interference
            discovered_count = self.discovery_service.discover_all_files(
                legislature_filter=legislature_filter,
                category_filter=category_filter
            )
            
            self.stats.discovery_completed = discovered_count
            self.stats.discovery_status = "Completed"
            self.stats.add_message(f"Discovery completed - {discovered_count} files cataloged", priority='high')
            
            # Trigger download manager check if files were discovered
            if discovered_count > 0:
                self.stats.add_message("Files ready for download - download manager will start processing...", priority='high')
            else:
                self.stats.add_message("No new files discovered - download manager waiting...", priority='normal')
            
        except Exception as e:
            self.stats.discovery_status = f"Error: {str(e)}"
            self.stats.add_message(f"Discovery error: {str(e)}", priority='error')
            self.stats.error_occurred = True
            # Print the full error for debugging
            import traceback
            error_details = traceback.format_exc()
            self.stats.add_message(f"Full error details: {error_details}", priority='error')
        finally:
            self.stats.discovery_running = False
    
    def start_pipeline(self, legislature_filter: str = None, category_filter: str = None):
        """Start the complete pipeline"""
        self.stats.start_time = datetime.now()
        self.running = True
        
        # Add initial startup messages
        file_types_str = ", ".join(self.allowed_file_types) if self.allowed_file_types else "ALL"
        mode_info = " (download-only mode)" if self.download_only else ""
        self.stats.add_message(f"🚀 Pipeline started{mode_info} - Processing: {file_types_str}", priority='high')
        if self.stats.stop_on_error:
            self.stats.add_message("⚠️ Stop-on-error enabled", priority='high')
        if legislature_filter:
            self.stats.add_message(f"📋 Legislature filter: {legislature_filter}", priority='high')
        if category_filter:
            self.stats.add_message(f"📂 Category filter: {category_filter}", priority='high')

        # Add service startup messages before UI starts
        if not self.import_only:
            self.stats.add_message("🔍 Starting discovery service...", priority='high')
            self.stats.add_message("⬇️ Starting download manager...", priority='high')
        else:
            self.stats.add_message("⏭️ Discovery & download skipped (import-only mode)", priority='high')
        if not self.download_only:
            self.stats.add_message("⚙️ Starting import processor...", priority='high')
        else:
            self.stats.add_message("⏭️ Import processor skipped (download-only mode)", priority='high')
        
        # Create UI layout
        layout = self.create_ui_layout()
        
        # Initialize layout with current data immediately to prevent flashing
        self.update_layout(layout)
        
        try:
            with Live(layout, refresh_per_second=1, screen=True):
                
                # Start discovery in background thread (unless import-only mode)
                if not self.import_only:
                    discovery_thread = threading.Thread(
                        target=self.run_discovery,
                        args=(legislature_filter, category_filter)
                    )
                    discovery_thread.daemon = True
                    discovery_thread.start()
                    self.threads.append(discovery_thread)

                    # Start download manager
                    download_thread = threading.Thread(
                        target=self.download_manager.start,
                        args=(self.download_queue, self.stats, self.console)
                    )
                    download_thread.daemon = True
                    download_thread.start()
                    self.threads.append(download_thread)

                # Start import processor (unless download-only mode)
                if not self.download_only:
                    import_thread = threading.Thread(
                        target=self.import_processor.start,
                        args=(self.download_queue, self.stats, self.console)
                    )
                    import_thread.daemon = True
                    import_thread.start()
                    self.threads.append(import_thread)

                # Main UI update loop
                error_paused = False
                while self.running:
                    # Check for stop-on-error condition
                    if self.stats.stop_on_error and self.stats.error_occurred and not error_paused:
                        self.stats.add_message("🛑 Error occurred - pipeline paused (--stop-on-error)", priority='error')
                        self.stats.add_message("   Review the activity log above, then press Ctrl+C to exit", priority='error')
                        # Stop processing but keep UI running so user can read the error
                        self.stop_processing()
                        error_paused = True
                        # Don't break - keep UI running

                    # Force flush buffered messages periodically
                    if hasattr(self.stats, '_message_buffer') and self.stats._message_buffer:
                        self.stats._flush_message_buffer()

                    self.update_layout(layout)
                    time.sleep(1.0)  # Slower updates to reduce flashing
                    
                    # Update all statistics from database (filtered by file type)
                    with DatabaseSession() as db_session:
                        # Base query with file type filter
                        base_query = db_session.query(ImportStatus)
                        if self.allowed_file_types:
                            base_query = base_query.filter(ImportStatus.file_type.in_(self.allowed_file_types))
                        
                        # Update queue sizes
                        self.stats.download_queue_size = base_query.filter(
                            ImportStatus.status.in_(['discovered', 'download_pending'])
                        ).count()
                        
                        self.stats.import_queue_size = base_query.filter(
                            ImportStatus.status.in_(['pending', 'import_error'])
                        ).count()
                        
                        # Update completion statistics
                        # Download completed: files that have been successfully downloaded and are ready for import or imported
                        self.stats.download_completed = base_query.filter(
                            ImportStatus.status.in_(['pending', 'processing', 'completed'])
                        ).count()
                        
                        # Download failed: files that failed download or need recrawling
                        self.stats.download_failed = base_query.filter(
                            ImportStatus.status.in_(['failed', 'recrawl'])
                        ).count()
                        
                        # Import completed: files that have been successfully imported
                        self.stats.import_completed = base_query.filter(
                            ImportStatus.status == 'completed'
                        ).count()
                        
                        # Import failed: files that failed during import processing
                        self.stats.import_failed = base_query.filter(
                            ImportStatus.status.in_(['import_error', 'schema_mismatch'])
                        ).count()

                        # Import skipped: files permanently skipped (corrupted source data)
                        self.stats.import_skipped = base_query.filter(
                            ImportStatus.status == 'skipped'
                        ).count()

                        # Update total records imported
                        completed_records = base_query.filter(
                            ImportStatus.status == 'completed',
                            ImportStatus.records_imported.isnot(None)
                        ).all()
                        self.stats.total_records_imported = sum(
                            record.records_imported or 0 for record in completed_records
                        )
                        
                        # Update discovery count
                        self.stats.discovery_completed = base_query.filter(
                            ImportStatus.status.in_([
                                'discovered', 'download_pending', 'downloading',
                                'pending', 'processing', 'completed', 'failed',
                                'import_error', 'schema_mismatch', 'recrawl', 'skipped'
                            ])
                        ).count()
                    
        except KeyboardInterrupt:
            self.console.print("\n🛑 Shutdown requested...")
            self.stop_pipeline()
    
    def stop_processing(self):
        """Stop processing components but keep UI running for error review"""
        self.download_manager.stop()
        self.import_processor.stop()
        # Don't set self.running = False - keep UI alive

    def stop_pipeline(self):
        """Stop all pipeline components including UI"""
        self.running = False
        self.download_manager.stop()
        self.import_processor.stop()

        # Wait for threads to complete
        for thread in self.threads:
            thread.join(timeout=2)

        self.console.print("✅ Pipeline stopped gracefully")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Parliament Data Pipeline Orchestrator")
    parser.add_argument('--legislature', type=str,
                       help='Filter by legislature (e.g., XVII, 17, Constituinte)')
    parser.add_argument('--category', type=str,
                       help='Filter by category (e.g., "Atividade Deputado")')
    parser.add_argument('--discovery-rate-limit', type=float, default=0.5,
                       help='Discovery rate limit delay (default: 0.5s)')
    parser.add_argument('--download-rate-limit', type=float, default=0.3,
                       help='Download rate limit delay (default: 0.3s)')
    parser.add_argument('--file-types', nargs='*', 
                       choices=['XML', 'JSON', 'PDF', 'Archive', 'XSD'], 
                       default=['XML'],
                       help='File types to process (default: XML only)')
    parser.add_argument('--all-file-types', action='store_true',
                       help='Process all file types (overrides --file-types)')
    parser.add_argument('--stop-on-error', action='store_true',
                       help='Stop the pipeline when an error occurs')
    parser.add_argument('--download-only', action='store_true',
                       help='Only run discovery and download, skip import processing')
    parser.add_argument('--retry-failed', action='store_true',
                       help='Reset import_error status to pending before starting (retry failed imports)')
    parser.add_argument('--import-only', action='store_true',
                       help='Only run import processing, skip discovery and download (use existing files)')

    args = parser.parse_args()

    # Reset failed imports if requested
    if args.retry_failed:
        with DatabaseSession() as db_session:
            from sqlalchemy import update
            result = db_session.execute(
                update(ImportStatus)
                .where(ImportStatus.status == 'import_error')
                .values(status='pending', error_message=None)
            )
            db_session.commit()
            print(f"Reset {result.rowcount} failed imports to pending status")
    
    # Determine file types to process
    if args.all_file_types:
        allowed_file_types = None  # Process all file types
    else:
        allowed_file_types = args.file_types
    
    # Create and start orchestrator
    orchestrator = PipelineOrchestrator(
        discovery_rate_limit=args.discovery_rate_limit,
        download_rate_limit=args.download_rate_limit,
        allowed_file_types=allowed_file_types,
        stop_on_error=args.stop_on_error,
        download_only=args.download_only,
        import_only=args.import_only
    )
    
    try:
        orchestrator.start_pipeline(
            legislature_filter=args.legislature,
            category_filter=args.category
        )
    except KeyboardInterrupt:
        orchestrator.stop_pipeline()


if __name__ == "__main__":
    main()