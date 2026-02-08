#!/usr/bin/env python3
"""
DEPRECATED: Async Parliament Data Pipeline Orchestrator
========================================================

This module has been superseded by the unified pipeline orchestration in:
- scripts/data_processing/pipeline_runner.py  (core module)
- ops/pipeline.py                              (CLI interface)

Please use the unified interface instead:

    ops pipeline run                    # Full pipeline with Rich UI (local)
    ops pipeline run --database prod    # Against production database
    ops pipeline run --ecs              # Run on ECS Fargate
    ops pipeline discover               # Discovery only
    ops pipeline import                 # Import only

This file is kept for backward compatibility but will be removed in a future version.

Original description:
--------------------
Orchestrates the complete parliament data pipeline with async/parallel processing:
1. Discovery Service - Finds and catalogs file URLs (runs in thread pool)
2. Async Download Manager - Downloads files concurrently (3-5 parallel)
3. Parallel Import Processor - Processes files in parallel (4-8 workers)

Features:
- Rich terminal UI with live progress tracking
- Detailed worker status showing each active download/import
- Rate limiting for discovery and downloads
- Graceful shutdown handling
"""

import warnings
warnings.warn(
    "async_pipeline_orchestrator.py is deprecated. Use 'ops pipeline run' instead.",
    DeprecationWarning,
    stacklevel=2
)

import argparse
import asyncio
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from database.connection import DatabaseSession
from database.models import ImportStatus
from scripts.data_processing.discovery_service import DiscoveryService
from scripts.data_processing.async_download_manager import AsyncDownloadManager, DownloadResult
from scripts.data_processing.parallel_import_processor import ParallelImportProcessor, ImportResult


@dataclass
class DownloadInfo:
    """Information about a downloaded file"""
    file_name: str
    file_size: int
    timestamp: str
    status_id: int


@dataclass
class ActiveWorker:
    """Tracks an active worker (download or import)"""
    worker_id: int
    file_name: str
    category: str
    started_at: datetime
    status: str = "working"  # working, complete, error

    @property
    def elapsed_seconds(self) -> int:
        return int((datetime.now() - self.started_at).total_seconds())

    @property
    def elapsed_display(self) -> str:
        secs = self.elapsed_seconds
        if secs < 60:
            return f"{secs}s"
        mins = secs // 60
        secs = secs % 60
        return f"{mins}m{secs}s"


@dataclass
class AsyncPipelineStats:
    """Pipeline statistics for UI display - tracks concurrent operations"""
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
    import_skipped: int = 0
    total_records_imported: int = 0
    start_time: Optional[datetime] = None
    recent_messages: List[str] = None
    downloaded_files: List[DownloadInfo] = None
    stop_on_error: bool = False
    error_occurred: bool = False
    pinned_errors: List[str] = None
    last_full_error: str = ""  # Store complete error message for display
    # Detailed worker tracking
    active_downloads: Dict[int, ActiveWorker] = None  # worker_id -> ActiveWorker
    active_imports: Dict[int, ActiveWorker] = None  # worker_id -> ActiveWorker
    _next_download_id: int = 0
    _next_import_id: int = 0

    def __post_init__(self):
        if self.recent_messages is None:
            self.recent_messages = []
        if self.downloaded_files is None:
            self.downloaded_files = []
        if self.pinned_errors is None:
            self.pinned_errors = []
        if self.active_downloads is None:
            self.active_downloads = {}
        if self.active_imports is None:
            self.active_imports = {}
        self._message_lock = threading.Lock()
        self._message_buffer = {}
        self._last_summary_time = datetime.now()
        self._worker_lock = threading.Lock()

    def start_download(self, file_name: str, category: str = "") -> int:
        """Register a new download worker, returns worker_id"""
        with self._worker_lock:
            worker_id = self._next_download_id
            self._next_download_id += 1
            self.active_downloads[worker_id] = ActiveWorker(
                worker_id=worker_id,
                file_name=file_name,
                category=category,
                started_at=datetime.now()
            )
            return worker_id

    def end_download(self, worker_id: int, success: bool = True):
        """Remove a download worker"""
        with self._worker_lock:
            if worker_id in self.active_downloads:
                del self.active_downloads[worker_id]

    def start_import(self, file_name: str, category: str = "") -> int:
        """Register a new import worker, returns worker_id"""
        with self._worker_lock:
            worker_id = self._next_import_id
            self._next_import_id += 1
            self.active_imports[worker_id] = ActiveWorker(
                worker_id=worker_id,
                file_name=file_name,
                category=category,
                started_at=datetime.now()
            )
            return worker_id

    def end_import(self, worker_id: int, success: bool = True):
        """Remove an import worker"""
        with self._worker_lock:
            if worker_id in self.active_imports:
                del self.active_imports[worker_id]

    def add_message(self, message: str, priority: str = 'normal'):
        """Add a message to recent messages with priority-based filtering"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"{timestamp} - {message}"

        with self._message_lock:
            if priority == 'error':
                self.pinned_errors.append(formatted_message)
                if len(self.pinned_errors) > 5:
                    self.pinned_errors.pop(0)
                # Store full error for detailed display
                self.last_full_error = message

            if priority in ['high', 'error', 'success']:
                self.recent_messages.append(formatted_message)
                if len(self.recent_messages) > 10:
                    self.recent_messages.pop(0)
                return

            current_time = datetime.now()
            message_key = self._get_message_key(message)
            if message_key not in self._message_buffer:
                self._message_buffer[message_key] = {
                    'count': 0,
                    'first_time': current_time,
                    'last_message': message
                }

            self._message_buffer[message_key]['count'] += 1
            self._message_buffer[message_key]['last_message'] = message

            time_since_summary = (current_time - self._last_summary_time).total_seconds()
            if time_since_summary >= 3.0 or len(self._message_buffer) >= 5:
                self._flush_message_buffer()
                self._last_summary_time = current_time

    def _get_message_key(self, message: str) -> str:
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
        if not self._message_buffer:
            return

        timestamp = datetime.now().strftime('%H:%M:%S')

        for key, info in self._message_buffer.items():
            if info['count'] == 1:
                formatted_message = f"{timestamp} - {info['last_message']}"
            else:
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

        self._message_buffer.clear()

    def add_download(self, file_name: str, file_size: int, status_id: int):
        """Add a downloaded file to the list"""
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


class AsyncPipelineOrchestrator:
    """Main async orchestrator for the parliament data pipeline"""

    def __init__(
        self,
        discovery_rate_limit: float = 0.5,
        download_rate_limit: float = 0.3,
        max_concurrent_downloads: int = 5,
        max_concurrent_imports: int = 1,  # Hardcoded to 1 to prevent deadlocks on partidos/deputados
        allowed_file_types: List[str] = None,
        stop_on_error: bool = False,
        download_only: bool = False,
        import_only: bool = False,
        database_env: str = "auto"
    ):
        self.console = Console()
        self.stats = AsyncPipelineStats()
        self.stats.stop_on_error = stop_on_error
        self.download_only = download_only
        self.import_only = import_only
        self.allowed_file_types = allowed_file_types or ['XML']
        self.database_env = database_env  # Store database environment for UI display

        # Configuration
        self.discovery_rate_limit = discovery_rate_limit
        self.download_rate_limit = download_rate_limit
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_concurrent_imports = max_concurrent_imports

        # Components (initialized in start())
        self.discovery_service = DiscoveryService(rate_limit_delay=discovery_rate_limit, quiet=True)
        self._download_manager: Optional[AsyncDownloadManager] = None
        self._import_processor: Optional[ParallelImportProcessor] = None

        # Control
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._error_paused = False

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
        """Get pending files from ImportStatus table"""
        try:
            with DatabaseSession() as db_session:
                query = db_session.query(ImportStatus).filter(
                    ImportStatus.status.in_(['discovered', 'download_pending', 'pending', 'recrawl', 'import_error'])
                )
                if self.allowed_file_types:
                    query = query.filter(ImportStatus.file_type.in_(self.allowed_file_types))
                pending_files = query.order_by(
                    ImportStatus.category,
                    ImportStatus.legislatura,
                    ImportStatus.file_name
                ).limit(limit).all()
                return pending_files
        except Exception as e:
            self.stats.add_message(f"Error getting pending files: {str(e)}", priority='error')
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
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=3)
        )

        # Left: stats + active workers
        layout["left"].split_column(
            Layout(name="stats", size=12),
            Layout(name="workers", ratio=1)
        )

        # Right: pending + activity (activity gets more space for error details)
        layout["right"].split_column(
            Layout(name="pending", ratio=1),
            Layout(name="activity", ratio=2)  # More space for error messages
        )

        return layout

    def update_layout(self, layout: Layout):
        """Update the Rich layout with current data"""
        # Header
        file_types_info = ", ".join(self.allowed_file_types) if self.allowed_file_types else "ALL"
        mode_str = ""
        if self.download_only:
            mode_str = " | Mode: Download Only"
        elif self.import_only:
            mode_str = " | Mode: Import Only"

        # Add database environment indicator with color coding
        db_color = "green" if "prod" in self.database_env else "yellow" if "local" in self.database_env else "blue"
        header_text = f"Async Parliament Pipeline - Runtime: {self.stats.elapsed_time} | DB: [{db_color}]{self.database_env}[/{db_color}] | Files: {file_types_info}{mode_str}"

        layout["header"].update(Panel(header_text, style="bold blue"))

        # Stats table
        stats_table = Table(show_header=True, header_style="bold cyan", box=None)
        stats_table.add_column("Stage", style="cyan", width=12)
        stats_table.add_column("Status", justify="left")

        # Discovery
        disc_status = f"[green]Running[/green]" if self.stats.discovery_running else f"[dim]{self.stats.discovery_status}[/dim]"
        stats_table.add_row("Discovery", f"{disc_status} | {self.stats.discovery_completed} files found")

        # Downloads
        dl_active = len(self.stats.active_downloads)
        dl_color = "green" if dl_active > 0 else "dim"
        stats_table.add_row(
            "Downloads",
            f"[{dl_color}]{dl_active} active[/{dl_color}] | OK: {self.stats.download_completed} | ERR: {self.stats.download_failed} | Queue: {self.stats.download_queue_size}"
        )

        # Imports
        imp_active = len(self.stats.active_imports)
        imp_color = "green" if imp_active > 0 else "dim"
        skip_str = f" | SKIP: {self.stats.import_skipped}" if self.stats.import_skipped > 0 else ""
        stats_table.add_row(
            "Imports",
            f"[{imp_color}]{imp_active} active[/{imp_color}] | OK: {self.stats.import_completed} | ERR: {self.stats.import_failed}{skip_str} | Queue: {self.stats.import_queue_size}"
        )

        stats_table.add_row("Records", f"[bold]{self.stats.total_records_imported:,}[/bold] total imported")

        layout["stats"].update(Panel(stats_table, title="Pipeline Status", border_style="green"))

        # Active Workers panel - detailed view of each worker
        workers_table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        workers_table.add_column("Type", style="bold", width=4)
        workers_table.add_column("File", style="cyan", width=28)
        workers_table.add_column("Category", style="magenta", width=20)
        workers_table.add_column("Time", justify="right", width=6)

        # Add active downloads
        for worker_id, worker in sorted(self.stats.active_downloads.items()):
            file_display = worker.file_name
            if len(file_display) > 26:
                file_display = file_display[:23] + "..."
            cat_display = worker.category[:18] + ".." if len(worker.category) > 20 else worker.category
            workers_table.add_row(
                "[yellow]DL[/yellow]",
                file_display,
                cat_display or "-",
                f"[yellow]{worker.elapsed_display}[/yellow]"
            )

        # Add active imports
        for worker_id, worker in sorted(self.stats.active_imports.items()):
            file_display = worker.file_name
            if len(file_display) > 26:
                file_display = file_display[:23] + "..."
            cat_display = worker.category[:18] + ".." if len(worker.category) > 20 else worker.category
            workers_table.add_row(
                "[cyan]IMP[/cyan]",
                file_display,
                cat_display or "-",
                f"[cyan]{worker.elapsed_display}[/cyan]"
            )

        # If no active workers, show waiting message
        if not self.stats.active_downloads and not self.stats.active_imports:
            workers_table.add_row("[dim]--[/dim]", "[dim]Waiting for work...[/dim]", "", "")

        total_workers = len(self.stats.active_downloads) + len(self.stats.active_imports)
        layout["workers"].update(Panel(
            workers_table,
            title=f"Active Workers ({total_workers})",
            border_style="yellow" if total_workers > 0 else "dim"
        ))

        # Pending files
        pending_files = self._get_pending_files(15)
        if pending_files:
            pending_table = Table(show_header=True, header_style="bold green", box=None)
            pending_table.add_column("Status", style="yellow", width=10)
            pending_table.add_column("File", style="cyan", width=25)
            pending_table.add_column("Category", style="magenta", width=28)
            pending_table.add_column("Leg", width=8)

            for file_record in pending_files:
                file_display = file_record.file_name
                if len(file_display) > 23:
                    file_display = file_display[:20] + "..."

                category_display = file_record.category or "Unknown"
                if len(category_display) > 26:
                    category_display = category_display[:23] + "..."

                status_display = file_record.status
                if file_record.status == 'discovered':
                    status_display = "[blue]discover[/blue]"
                elif file_record.status == 'download_pending':
                    status_display = "[yellow]dl_pend[/yellow]"
                elif file_record.status == 'pending':
                    status_display = "[green]ready[/green]"
                elif file_record.status == 'recrawl':
                    status_display = "[orange3]recrawl[/orange3]"
                elif file_record.status == 'import_error':
                    status_display = "[red]error[/red]"
                elif file_record.status == 'skipped':
                    status_display = "[dim]skipped[/dim]"

                leg_display = file_record.legislatura or "-"
                if len(leg_display) > 8:
                    leg_display = leg_display[:6] + ".."

                pending_table.add_row(
                    status_display,
                    file_display,
                    category_display,
                    leg_display
                )

            layout["pending"].update(Panel(pending_table, title=f"Queue ({len(pending_files)}+)", border_style="green"))
        else:
            layout["pending"].update(Panel("[dim]No pending files[/dim]", title="Queue", border_style="dim"))

        # Activity log with pinned errors
        activity_lines = []

        # Show last full error at the top if available
        if self.stats.last_full_error:
            activity_lines.append("[bold red]LAST ERROR:[/bold red]")
            # Word-wrap long error messages (max ~120 chars per line for wider terminals)
            error_text = self.stats.last_full_error
            max_error_lines = 8  # Show up to 8 lines of error detail
            lines_added = 0
            while len(error_text) > 120 and lines_added < max_error_lines:
                # Find a good break point
                break_point = error_text.rfind(' ', 0, 120)
                if break_point == -1:
                    break_point = 120
                activity_lines.append(f"[red]{error_text[:break_point]}[/red]")
                error_text = error_text[break_point:].lstrip()
                lines_added += 1
            if error_text and lines_added < max_error_lines:
                activity_lines.append(f"[red]{error_text}[/red]")
            elif error_text:
                activity_lines.append(f"[red]... (truncated)[/red]")
            activity_lines.append("")

        if self.stats.recent_messages:
            max_recent = 5 if self.stats.last_full_error else 10
            for msg in self.stats.recent_messages[-max_recent:]:
                # Show full message without truncation for better debugging
                activity_lines.append(msg)
        elif not self.stats.last_full_error:
            activity_lines.append("[dim]Waiting for activity...[/dim]")

        layout["activity"].update(Panel(
            "\n".join(activity_lines),
            title="Activity Log",
            border_style="red" if self.stats.last_full_error else "blue"
        ))

        # Footer
        layout["footer"].update(Panel(
            f"Ctrl+C to stop | Max Downloads: {self.max_concurrent_downloads} | Max Imports: {self.max_concurrent_imports}",
            style="dim"
        ))

    async def _run_discovery(self, legislature_filter: str = None, category_filter: str = None):
        """Run discovery in thread pool (it's I/O bound but uses requests)"""
        try:
            self.stats.discovery_running = True
            self.stats.discovery_status = "Starting..."
            self.stats.add_message("Discovery service starting...", priority='high')

            loop = asyncio.get_event_loop()
            discovered_count = await loop.run_in_executor(
                None,  # Default thread pool
                self.discovery_service.discover_all_files,
                legislature_filter,
                category_filter
            )

            self.stats.discovery_completed = discovered_count
            self.stats.discovery_status = "Completed"
            self.stats.add_message(f"Discovery completed - {discovered_count} files", priority='high')

        except Exception as e:
            self.stats.discovery_status = f"Error"
            self.stats.add_message(f"Discovery error: {str(e)}", priority='error')
            self.stats.error_occurred = True
        finally:
            self.stats.discovery_running = False

    async def _download_worker(self):
        """Background worker for concurrent downloads"""
        while self._running and not self._error_paused:
            try:
                # Get files to download
                with DatabaseSession() as db_session:
                    query = db_session.query(ImportStatus).filter(
                        ImportStatus.status.in_(['discovered', 'download_pending'])
                    )
                    if self.allowed_file_types:
                        query = query.filter(ImportStatus.file_type.in_(self.allowed_file_types))

                    files_to_download = query.order_by(
                        ImportStatus.category,
                        ImportStatus.legislatura,
                        ImportStatus.file_name
                    ).limit(self.max_concurrent_downloads * 2).all()

                    if not files_to_download:
                        await asyncio.sleep(1)
                        continue

                    # Mark files as downloading and store info
                    file_infos = []
                    for record in files_to_download:
                        record.status = 'downloading'
                        file_infos.append({
                            'id': record.id,
                            'file_url': record.file_url,
                            'file_name': record.file_name,
                            'category': record.category or ""
                        })
                    db_session.commit()

                # Process downloads with worker tracking
                async def download_with_tracking(file_info):
                    worker_id = self.stats.start_download(file_info['file_name'], file_info['category'])
                    try:
                        class SimpleRecord:
                            def __init__(self, d):
                                self.id = d['id']
                                self.file_url = d['file_url']
                                self.file_name = d['file_name']

                        result = await self._download_manager.download_file(SimpleRecord(file_info))
                        return result, file_info
                    finally:
                        self.stats.end_download(worker_id)

                # Download all concurrently
                tasks = [download_with_tracking(f) for f in file_infos]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Update database with results
                with DatabaseSession() as db_session:
                    for item in results:
                        if isinstance(item, Exception):
                            continue
                        result, file_info = item

                        record = db_session.get(ImportStatus, result.status_id)
                        if not record:
                            continue

                        if result.success:
                            record.file_path = str(result.file_path)
                            record.file_hash = result.file_hash
                            record.file_size = result.file_size
                            record.status = 'pending'
                            record.updated_at = datetime.now()
                            self.stats.add_download(result.file_name, result.file_size, result.status_id)
                        else:
                            if result.is_not_found:
                                record.status = 'recrawl'
                                record.error_message = f"Not found: {result.error_message}"
                            else:
                                record.status = 'failed'
                                record.error_message = f"Download error: {result.error_message}"
                                self.stats.error_occurred = True

                    db_session.commit()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats.add_message(f"Download worker error: {str(e)}", priority='error')
                self.stats.error_occurred = True
                await asyncio.sleep(1)

    async def _import_worker(self):
        """Coordinator that spawns individual import workers with a shared queue"""
        # Create a queue for files to import
        import_queue = asyncio.Queue()

        async def single_worker(worker_num: int):
            """Individual worker that continuously processes files from queue"""
            while self._running and not self._error_paused:
                try:
                    # Get next file from queue (with timeout to check running status)
                    try:
                        file_info = await asyncio.wait_for(import_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue

                    # Process the file
                    worker_id = self.stats.start_import(file_info['file_name'], file_info['category'])
                    try:
                        result = await self._import_processor.process_file(
                            file_info['status_id'],
                            file_info['file_path'],
                            file_info['file_name'],
                            file_info['category']
                        )

                        # Update stats immediately
                        if result.success:
                            self.stats.import_completed += 1
                            self.stats.total_records_imported += result.records_imported
                            self.stats.add_message(f"SUCCESS: {result.file_name} ({result.records_imported} records)", priority='success')
                        elif result.was_skipped:
                            self.stats.import_skipped += 1
                        else:
                            self.stats.import_failed += 1
                            err_msg = result.error_message or "Unknown error"
                            self.stats.add_message(f"FAILED: {result.file_name} - {err_msg}", priority='error')
                            self.stats.error_occurred = True

                    except Exception as e:
                        self.stats.import_failed += 1
                        self.stats.add_message(f"Import exception: {str(e)}", priority='error')
                        self.stats.error_occurred = True
                    finally:
                        self.stats.end_import(worker_id)
                        import_queue.task_done()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.stats.add_message(f"Worker {worker_num} error: {str(e)}", priority='error')
                    await asyncio.sleep(0.5)

        async def queue_feeder():
            """Feeds files into the queue as workers become available"""
            while self._running and not self._error_paused:
                try:
                    # Only fetch more if queue is getting low
                    if import_queue.qsize() < self.max_concurrent_imports:
                        # Calculate how many to fetch
                        fetch_count = self.max_concurrent_imports - import_queue.qsize()

                        with DatabaseSession() as db_session:
                            query = db_session.query(ImportStatus).filter(
                                ImportStatus.status.in_(['pending', 'import_error'])
                            )
                            if self.allowed_file_types:
                                query = query.filter(ImportStatus.file_type.in_(self.allowed_file_types))

                            files_to_import = query.order_by(
                                ImportStatus.category,
                                ImportStatus.legislatura,
                                ImportStatus.file_name
                            ).limit(fetch_count).all()

                            if files_to_import:
                                # Mark files as processing and queue them
                                for record in files_to_import:
                                    record.status = 'processing'
                                    await import_queue.put({
                                        'status_id': record.id,
                                        'file_path': record.file_path,
                                        'file_name': record.file_name,
                                        'category': record.category or ""
                                    })
                                db_session.commit()

                    await asyncio.sleep(0.5)  # Check for more work periodically

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.stats.add_message(f"Queue feeder error: {str(e)}", priority='error')
                    await asyncio.sleep(1)

        # Start worker tasks and feeder
        workers = [asyncio.create_task(single_worker(i)) for i in range(self.max_concurrent_imports)]
        feeder = asyncio.create_task(queue_feeder())

        try:
            # Wait for all tasks (they run until cancelled)
            await asyncio.gather(feeder, *workers, return_exceptions=True)
        except asyncio.CancelledError:
            pass
        finally:
            # Cancel all tasks on shutdown
            feeder.cancel()
            for w in workers:
                w.cancel()

    async def _stats_updater(self):
        """Background task to update statistics from database"""
        while self._running:
            try:
                with DatabaseSession() as db_session:
                    base_query = db_session.query(ImportStatus)
                    if self.allowed_file_types:
                        base_query = base_query.filter(ImportStatus.file_type.in_(self.allowed_file_types))

                    self.stats.download_queue_size = base_query.filter(
                        ImportStatus.status.in_(['discovered', 'download_pending'])
                    ).count()

                    self.stats.import_queue_size = base_query.filter(
                        ImportStatus.status.in_(['pending', 'import_error'])
                    ).count()

                    self.stats.download_completed = base_query.filter(
                        ImportStatus.status.in_(['pending', 'processing', 'completed'])
                    ).count()

                    self.stats.download_failed = base_query.filter(
                        ImportStatus.status.in_(['failed', 'recrawl'])
                    ).count()

                    self.stats.import_completed = base_query.filter(
                        ImportStatus.status == 'completed'
                    ).count()

                    self.stats.import_failed = base_query.filter(
                        ImportStatus.status.in_(['import_error', 'schema_mismatch'])
                    ).count()

                    self.stats.import_skipped = base_query.filter(
                        ImportStatus.status == 'skipped'
                    ).count()

                    completed_records = base_query.filter(
                        ImportStatus.status == 'completed',
                        ImportStatus.records_imported.isnot(None)
                    ).all()
                    self.stats.total_records_imported = sum(
                        record.records_imported or 0 for record in completed_records
                    )

                    self.stats.discovery_completed = base_query.filter(
                        ImportStatus.status.in_([
                            'discovered', 'download_pending', 'downloading',
                            'pending', 'processing', 'completed', 'failed',
                            'import_error', 'schema_mismatch', 'recrawl', 'skipped'
                        ])
                    ).count()

                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(2)

    async def start_pipeline(self, legislature_filter: str = None, category_filter: str = None):
        """Start the async pipeline"""
        self.stats.start_time = datetime.now()
        self._running = True

        # Initialize components
        self._download_manager = AsyncDownloadManager(
            max_concurrent=self.max_concurrent_downloads,
            rate_limit_delay=self.download_rate_limit
        )
        await self._download_manager.start()

        self._import_processor = ParallelImportProcessor(
            max_workers=self.max_concurrent_imports
        )
        await self._import_processor.start()

        # Startup messages
        file_types_str = ", ".join(self.allowed_file_types) if self.allowed_file_types else "ALL"
        self.stats.add_message(f"Pipeline started - Files: {file_types_str}", priority='high')
        self.stats.add_message(f"Workers: {self.max_concurrent_downloads} DL / {self.max_concurrent_imports} IMP", priority='high')

        if self.stats.stop_on_error:
            self.stats.add_message("Stop-on-error enabled", priority='high')

        # Create UI layout
        layout = self.create_ui_layout()
        self.update_layout(layout)

        # Start background tasks
        tasks = []

        if not self.import_only:
            tasks.append(asyncio.create_task(self._run_discovery(legislature_filter, category_filter)))
            tasks.append(asyncio.create_task(self._download_worker()))

        if not self.download_only:
            tasks.append(asyncio.create_task(self._import_worker()))

        tasks.append(asyncio.create_task(self._stats_updater()))

        try:
            with Live(layout, refresh_per_second=2, screen=True):
                while self._running:
                    # Check stop-on-error
                    if self.stats.stop_on_error and self.stats.error_occurred and not self._error_paused:
                        self.stats.add_message("Error occurred - paused (--stop-on-error)", priority='error')
                        self._error_paused = True

                    # Flush message buffer
                    if hasattr(self.stats, '_message_buffer') and self.stats._message_buffer:
                        self.stats._flush_message_buffer()

                    self.update_layout(layout)
                    await asyncio.sleep(0.5)

        except KeyboardInterrupt:
            self.console.print("\nShutdown requested...")
        finally:
            self._running = False

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            await self._import_processor.stop()
            await self._download_manager.close()

            self.console.print("Pipeline stopped")


def setup_database_environment(env_choice: str) -> str:
    """
    Configure database environment variables based on user choice.

    Returns the environment name being used.
    """
    if env_choice == 'auto':
        # Check if we have AWS credentials/secret ARN configured
        if os.getenv('DATABASE_SECRET_ARN'):
            return 'prod (via DATABASE_SECRET_ARN)'
        elif os.getenv('DATABASE_URL'):
            return 'custom (via DATABASE_URL)'
        elif os.getenv('PG_PASSWORD'):
            # Check if it looks like a production host
            pg_host = os.getenv('PG_HOST', 'localhost')
            if 'rds.amazonaws.com' in pg_host:
                return f'prod ({pg_host})'
            return f'local ({pg_host}:{os.getenv("PG_PORT", "5432")})'
        else:
            raise RuntimeError(
                "No database configuration found. Use --database local or --database prod, "
                "or set DATABASE_URL, DATABASE_SECRET_ARN, or PG_PASSWORD environment variables."
            )

    elif env_choice == 'local':
        # Force use of local environment variables
        # Clear any AWS secret ARN that might be set
        if 'DATABASE_SECRET_ARN' in os.environ:
            del os.environ['DATABASE_SECRET_ARN']
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

        # Check that we have local config
        if not os.getenv('PG_PASSWORD'):
            raise RuntimeError(
                "Local database configuration requires PG_PASSWORD environment variable. "
                "Also set PG_HOST, PG_PORT, PG_USER, PG_DATABASE as needed."
            )

        # Set sslmode to disable for local connections
        os.environ['PG_SSLMODE'] = 'disable'
        return f"local ({os.getenv('PG_HOST', 'localhost')}:{os.getenv('PG_PORT', '5432')})"

    elif env_choice == 'prod':
        # Clear DATABASE_SECRET_ARN - we'll use PG_* vars with production host instead
        # This allows running locally against prod without AWS credentials
        if 'DATABASE_SECRET_ARN' in os.environ:
            del os.environ['DATABASE_SECRET_ARN']
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

        # Always get the production endpoint from terraform (overrides .env settings)
        try:
            import subprocess

            # Get the database endpoint from terraform
            result = subprocess.run(
                ['terraform', 'output', '-raw', 'database_endpoint'],
                cwd=os.path.join(os.path.dirname(__file__), '..', '..', 'terraform'),
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                endpoint = result.stdout.strip()
                # Parse host:port from endpoint
                if ':' in endpoint:
                    host, port = endpoint.rsplit(':', 1)
                    os.environ['PG_HOST'] = host
                    os.environ['PG_PORT'] = port
                else:
                    os.environ['PG_HOST'] = endpoint
                    os.environ['PG_PORT'] = '5432'

                os.environ['PG_SSLMODE'] = 'require'

                # Check if PROD_PG_PASSWORD is set (separate from local PG_PASSWORD)
                prod_password = os.getenv('PROD_PG_PASSWORD') or os.getenv('PG_PROD_PASSWORD')
                if prod_password:
                    os.environ['PG_PASSWORD'] = prod_password
                    return f"prod ({os.getenv('PG_HOST')})"

                # Prompt for password if not set
                print("\n" + "="*70)
                print("PRODUCTION DATABASE CONNECTION")
                print("="*70)
                print(f"Host: {os.getenv('PG_HOST')}")
                print(f"Port: {os.getenv('PG_PORT', '5432')}")
                print(f"User: {os.getenv('PG_USER', 'parluser')}")
                print(f"Database: {os.getenv('PG_DATABASE', 'parliament')}")
                print("-"*70)
                print("Production password not set.")
                print("Set PROD_PG_PASSWORD environment variable, or enter it now:")
                print("="*70)

                import getpass
                password = getpass.getpass("Production DB Password: ")
                if not password:
                    raise RuntimeError("Password required for production database access")

                os.environ['PG_PASSWORD'] = password
                return f"prod ({os.getenv('PG_HOST')})"

            else:
                raise RuntimeError(
                    "Could not get database endpoint from terraform outputs. "
                    "Run from project root or set PG_HOST manually."
                )
        except FileNotFoundError:
            raise RuntimeError(
                "terraform not available. Set PG_HOST, PG_PORT, and PROD_PG_PASSWORD manually."
            )

    else:
        raise ValueError(f"Unknown database environment: {env_choice}")


def main():
    """Main CLI interface - DEPRECATED"""
    # Show prominent deprecation warning
    print("\n" + "="*70)
    print("DEPRECATION WARNING")
    print("="*70)
    print("This script is deprecated. Please use the unified interface:")
    print("")
    print("  ops pipeline run                    # Full pipeline with Rich UI")
    print("  ops pipeline run --database prod    # Against production database")
    print("  ops pipeline run --ecs              # Run on ECS Fargate")
    print("")
    print("This script will continue running, but please migrate to 'ops pipeline'.")
    print("="*70 + "\n")

    parser = argparse.ArgumentParser(
        description="DEPRECATED: Async Parliament Data Pipeline. Use 'ops pipeline run' instead.",
        epilog="This script is deprecated. Use 'ops pipeline run' for the unified interface."
    )
    parser.add_argument('--database', '-d', type=str, choices=['local', 'prod', 'auto'], default='auto',
                       help='Database environment: local (uses PG_* env vars), prod (uses AWS Secrets Manager), auto (detect)')
    parser.add_argument('--legislature', type=str, help='Filter by legislature')
    parser.add_argument('--category', type=str, help='Filter by category')
    parser.add_argument('--discovery-rate-limit', type=float, default=0.5)
    parser.add_argument('--download-rate-limit', type=float, default=0.3)
    parser.add_argument('--max-downloads', type=int, default=5)
    parser.add_argument('--file-types', nargs='*', choices=['XML', 'JSON', 'PDF', 'Archive', 'XSD'], default=['XML'])
    parser.add_argument('--all-file-types', action='store_true')
    parser.add_argument('--stop-on-error', action='store_true')
    parser.add_argument('--download-only', action='store_true')
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--import-only', action='store_true')

    args = parser.parse_args()

    # Setup database environment before doing anything else
    try:
        db_env = setup_database_environment(args.database)
        print(f"Database: {db_env}")
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if args.retry_failed:
        with DatabaseSession() as db_session:
            from sqlalchemy import update
            result = db_session.execute(
                update(ImportStatus)
                .where(ImportStatus.status == 'import_error')
                .values(status='pending', error_message=None)
            )
            db_session.commit()
            print(f"Reset {result.rowcount} failed imports")

    allowed_file_types = None if args.all_file_types else args.file_types

    # NOTE: max_concurrent_imports=1 is hardcoded to prevent deadlocks
    # on partidos/deputados tables during concurrent upserts
    orchestrator = AsyncPipelineOrchestrator(
        discovery_rate_limit=args.discovery_rate_limit,
        download_rate_limit=args.download_rate_limit,
        max_concurrent_downloads=args.max_downloads,
        max_concurrent_imports=1,
        allowed_file_types=allowed_file_types,
        stop_on_error=args.stop_on_error,
        download_only=args.download_only,
        import_only=args.import_only,
        database_env=db_env
    )

    try:
        asyncio.run(orchestrator.start_pipeline(
            legislature_filter=args.legislature,
            category_filter=args.category
        ))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
