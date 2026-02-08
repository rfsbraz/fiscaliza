#!/usr/bin/env python3
"""
Unified Pipeline Runner
=======================

Core orchestration module for the parliament data pipeline.
Provides both local execution (with Rich UI) and ECS execution support.

This module is designed to be used by:
- ops/pipeline.py (CLI interface)
- Direct Python imports

Usage:
    # Via ops CLI (recommended):
    ops pipeline run --local
    ops pipeline run --ecs

    # Direct invocation:
    python -m scripts.data_processing.pipeline_runner --local
"""

import asyncio
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

# Add project root and scripts/data_processing to path for imports
# (data_processing modules use relative imports like 'from http_retry_utils import ...')
_project_root = Path(__file__).parent.parent.parent
_data_processing_dir = Path(__file__).parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_data_processing_dir))

# Load .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required in production

import logging

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def configure_logging_for_rich_ui():
    """
    Configure logging to suppress console output when Rich UI is active.

    This prevents log messages from polluting the Rich terminal UI.
    Logs are still written to files via error logging.
    """
    # Suppress all console logging from the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.CRITICAL)

    # Remove all handlers that write to stdout/stderr
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            root_logger.removeHandler(handler)

    # Also suppress specific module loggers that might be pre-configured
    for logger_name in [
        'scripts.data_processing',
        'scripts.data_processing.mappers',
        'scripts.data_processing.database_driven_importer',
        'database',
        'database.connection',
        'sqlalchemy',
        'urllib3',
        'aiohttp',
    ]:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        logging.getLogger(logger_name).propagate = False


# =============================================================================
# Database Environment Configuration
# =============================================================================

@dataclass
class DatabaseConfig:
    """Database configuration container."""
    host: str = "localhost"
    port: str = "5432"
    database: str = "parliament"
    user: str = "parluser"
    password: str = ""
    sslmode: str = "disable"
    environment: str = "local"  # local, prod, custom

    @property
    def display_name(self) -> str:
        """Human-readable environment name."""
        if self.environment == "prod":
            return f"prod ({self.host})"
        elif self.environment == "local":
            return f"local ({self.host}:{self.port})"
        return f"custom ({self.host}:{self.port})"


def get_terraform_output(output_name: str, terraform_dir: Optional[Path] = None) -> Optional[str]:
    """Get a terraform output value."""
    import subprocess

    if terraform_dir is None:
        terraform_dir = Path(__file__).parent.parent.parent / "terraform"

    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", output_name],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def setup_database_environment(env_choice: str) -> DatabaseConfig:
    """
    Configure database environment variables based on user choice.

    Args:
        env_choice: One of 'local', 'prod', 'auto'

    Returns:
        DatabaseConfig with the configured environment

    Raises:
        RuntimeError: If configuration cannot be determined
    """
    config = DatabaseConfig()

    if env_choice == 'auto':
        # Check if we have AWS credentials/secret ARN configured
        if os.getenv('DATABASE_SECRET_ARN'):
            config.environment = 'prod'
            return config
        elif os.getenv('DATABASE_URL'):
            config.environment = 'custom'
            return config
        elif os.getenv('PG_PASSWORD'):
            config.host = os.getenv('PG_HOST', 'localhost')
            config.port = os.getenv('PG_PORT', '5432')
            config.database = os.getenv('PG_DATABASE', 'parliament')
            config.user = os.getenv('PG_USER', 'parluser')
            config.password = os.getenv('PG_PASSWORD', '')
            config.sslmode = os.getenv('PG_SSLMODE', 'disable')

            if 'rds.amazonaws.com' in config.host:
                config.environment = 'prod'
            else:
                config.environment = 'local'
            return config
        else:
            raise RuntimeError(
                "No database configuration found. Use --database local or --database prod, "
                "or set DATABASE_URL, DATABASE_SECRET_ARN, or PG_* environment variables."
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

        config.host = os.getenv('PG_HOST', 'localhost')
        config.port = os.getenv('PG_PORT', '5432')
        config.database = os.getenv('PG_DATABASE', 'parliament')
        config.user = os.getenv('PG_USER', 'parluser')
        config.password = os.getenv('PG_PASSWORD', '')
        config.sslmode = 'disable'
        config.environment = 'local'
        return config

    elif env_choice == 'prod':
        # Clear DATABASE_SECRET_ARN - we'll use PG_* vars with production host instead
        if 'DATABASE_SECRET_ARN' in os.environ:
            del os.environ['DATABASE_SECRET_ARN']
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

        # Get the database endpoint from terraform
        endpoint = get_terraform_output('database_endpoint')
        if endpoint:
            # Parse host:port from endpoint
            if ':' in endpoint:
                host, port = endpoint.rsplit(':', 1)
            else:
                host = endpoint
                port = '5432'

            os.environ['PG_HOST'] = host
            os.environ['PG_PORT'] = port
            os.environ['PG_SSLMODE'] = 'require'

            config.host = host
            config.port = port
            config.sslmode = 'require'
            config.environment = 'prod'

            # Check if PROD_PG_PASSWORD is set
            prod_password = os.getenv('PROD_PG_PASSWORD') or os.getenv('PG_PROD_PASSWORD')
            if prod_password:
                os.environ['PG_PASSWORD'] = prod_password
                config.password = prod_password
                return config

            # Prompt for password if not set
            print("\n" + "="*70)
            print("PRODUCTION DATABASE CONNECTION")
            print("="*70)
            print(f"Host: {host}")
            print(f"Port: {port}")
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
            config.password = password
            return config
        else:
            raise RuntimeError(
                "Could not get database endpoint from terraform outputs. "
                "Run from project root or set PG_HOST manually."
            )

    else:
        raise ValueError(f"Unknown database environment: {env_choice}")


# =============================================================================
# Pipeline Statistics & UI
# =============================================================================

@dataclass
class ActiveWorker:
    """Tracks an active worker (download or import)."""
    worker_id: int
    file_name: str
    category: str
    started_at: datetime
    status: str = "working"

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
class PipelineStats:
    """Pipeline statistics for UI display."""
    discovery_total: int = 0
    discovery_completed: int = 0
    discovery_running: bool = False
    discovery_status: str = "Waiting"
    download_queue_size: int = 0
    download_completed: int = 0
    download_skipped: int = 0  # Files already on disk (skipped download)
    download_failed: int = 0
    import_queue_size: int = 0
    import_completed: int = 0
    import_failed: int = 0
    import_skipped: int = 0
    total_records_imported: int = 0
    start_time: Optional[datetime] = None
    recent_messages: List[str] = None
    stop_on_error: bool = False
    error_occurred: bool = False
    pinned_errors: List[str] = None
    last_full_error: str = ""
    active_downloads: Dict[int, ActiveWorker] = None
    active_imports: Dict[int, ActiveWorker] = None
    _next_download_id: int = 0
    _next_import_id: int = 0
    _error_log_file: Any = None  # File handle for error logging

    def __post_init__(self):
        if self.recent_messages is None:
            self.recent_messages = []
        if self.pinned_errors is None:
            self.pinned_errors = []
        if self.active_downloads is None:
            self.active_downloads = {}
        if self.active_imports is None:
            self.active_imports = {}
        self._message_lock = threading.Lock()
        self._worker_lock = threading.Lock()

    def setup_error_log(self, log_dir: Path = None):
        """Create a fresh error log file for this pipeline run."""
        if log_dir is None:
            log_dir = _project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"pipeline_errors_{timestamp}.log"
        self._error_log_file = open(log_path, 'w', encoding='utf-8')
        self._error_log_path = log_path

        # Write header
        self._error_log_file.write(f"Pipeline Error Log - Started {datetime.now().isoformat()}\n")
        self._error_log_file.write("=" * 80 + "\n\n")
        self._error_log_file.flush()

        return log_path

    def log_error(self, file_name: str, category: str, legislature: str, error_message: str):
        """Log an error to the error log file."""
        if self._error_log_file:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry = f"[{timestamp}] {category} | {legislature} | {file_name}\n  ERROR: {error_message}\n\n"
            self._error_log_file.write(entry)
            self._error_log_file.flush()

    def close_error_log(self):
        """Close the error log file and write summary."""
        if self._error_log_file:
            self._error_log_file.write("=" * 80 + "\n")
            self._error_log_file.write(f"Pipeline completed at {datetime.now().isoformat()}\n")
            self._error_log_file.write(f"Total errors: {self.import_failed}\n")
            self._error_log_file.write(f"Total records imported: {self.total_records_imported:,}\n")
            self._error_log_file.close()
            self._error_log_file = None

    def get_error_log_tail(self, lines: int = 15) -> List[str]:
        """Get the last N lines from the error log file."""
        if not hasattr(self, '_error_log_path') or not self._error_log_path:
            return ["[dim]No error log[/dim]"]

        try:
            with open(self._error_log_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                # Skip header lines (first 2)
                content_lines = all_lines[2:] if len(all_lines) > 2 else []
                if not content_lines:
                    return ["[dim]No errors yet[/dim]"]
                # Return last N lines, stripped
                return [line.rstrip() for line in content_lines[-lines:]]
        except Exception as e:
            return [f"[red]Error reading log: {e}[/red]"]

    def start_download(self, file_name: str, category: str = "") -> int:
        """Register a new download worker."""
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

    def end_download(self, worker_id: int):
        """Remove a download worker."""
        with self._worker_lock:
            if worker_id in self.active_downloads:
                del self.active_downloads[worker_id]

    def start_import(self, file_name: str, category: str = "") -> int:
        """Register a new import worker."""
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

    def end_import(self, worker_id: int):
        """Remove an import worker."""
        with self._worker_lock:
            if worker_id in self.active_imports:
                del self.active_imports[worker_id]

    def add_message(self, message: str, priority: str = 'normal'):
        """Add a message to recent messages."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted = f"{timestamp} - {message}"

        with self._message_lock:
            if priority == 'error':
                self.pinned_errors.append(formatted)
                if len(self.pinned_errors) > 5:
                    self.pinned_errors.pop(0)
                self.last_full_error = message

            if priority in ['high', 'error', 'success']:
                self.recent_messages.append(formatted)
                if len(self.recent_messages) > 10:
                    self.recent_messages.pop(0)

    @property
    def elapsed_time(self) -> str:
        if not self.start_time:
            return "00:00:00"
        elapsed = datetime.now() - self.start_time
        total_seconds = int(elapsed.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# =============================================================================
# Local Pipeline Runner (with Rich UI)
# =============================================================================

class LocalPipelineRunner:
    """
    Local pipeline runner with Rich terminal UI.

    Provides async orchestration of discovery, download, and import stages
    with real-time progress visualization.
    """

    def __init__(
        self,
        db_config: DatabaseConfig,
        discovery_rate_limit: float = 0.5,
        download_rate_limit: float = 0.3,
        max_concurrent_downloads: int = 5,
        max_concurrent_imports: int = 1,  # Temporarily 1 to test deadlock hypothesis
        allowed_file_types: List[str] = None,
        stop_on_error: bool = False,
        download_only: bool = False,
        import_only: bool = False
    ):
        if not HAS_RICH:
            raise RuntimeError("Rich library required for local pipeline. Install with: pip install rich")

        # Suppress console logging to prevent pollution of Rich UI
        configure_logging_for_rich_ui()

        self.console = Console()
        self.db_config = db_config
        self.stats = PipelineStats()
        self.stats.stop_on_error = stop_on_error
        self.download_only = download_only
        self.import_only = import_only
        self.allowed_file_types = allowed_file_types or ['XML']

        # Configuration
        self.discovery_rate_limit = discovery_rate_limit
        self.download_rate_limit = download_rate_limit
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_concurrent_imports = max_concurrent_imports

        # Components (initialized in start())
        self._discovery_service = None
        self._download_manager = None
        self._import_processor = None

        # Control
        self._running = False
        self._error_paused = False

    def _get_pending_files(self, limit: int = 10) -> List:
        """Get pending files from ImportStatus table."""
        try:
            from database.connection import DatabaseSession
            from database.models import ImportStatus

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
        """Create Rich layout for the UI."""
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

        layout["left"].split_column(
            Layout(name="stats", size=12),
            Layout(name="workers", ratio=1)
        )

        layout["right"].split_column(
            Layout(name="pending", ratio=1),
            Layout(name="activity", ratio=1),
            Layout(name="error_log", ratio=1)
        )

        return layout

    def update_layout(self, layout: Layout):
        """Update the Rich layout with current data."""
        # Header
        file_types_info = ", ".join(self.allowed_file_types) if self.allowed_file_types else "ALL"
        mode_str = ""
        if self.download_only:
            mode_str = " | Mode: Download Only"
        elif self.import_only:
            mode_str = " | Mode: Import Only"

        db_color = "green" if self.db_config.environment == "prod" else "yellow"
        header_text = f"Parliament Pipeline - Runtime: {self.stats.elapsed_time} | DB: [{db_color}]{self.db_config.display_name}[/{db_color}] | Files: {file_types_info}{mode_str}"

        layout["header"].update(Panel(header_text, style="bold blue"))

        # Stats table
        stats_table = Table(show_header=True, header_style="bold cyan", box=None)
        stats_table.add_column("Stage", style="cyan", width=12)
        stats_table.add_column("Status", justify="left")

        disc_status = f"[green]Running[/green]" if self.stats.discovery_running else f"[dim]{self.stats.discovery_status}[/dim]"
        stats_table.add_row("Discovery", f"{disc_status} | {self.stats.discovery_completed} files found")

        dl_active = len(self.stats.active_downloads)
        dl_color = "green" if dl_active > 0 else "dim"
        skip_dl_str = f" | SKIP: {self.stats.download_skipped}" if self.stats.download_skipped > 0 else ""
        stats_table.add_row(
            "Downloads",
            f"[{dl_color}]{dl_active} active[/{dl_color}] | OK: {self.stats.download_completed}{skip_dl_str} | ERR: {self.stats.download_failed} | Queue: {self.stats.download_queue_size}"
        )

        imp_active = len(self.stats.active_imports)
        imp_color = "green" if imp_active > 0 else "dim"
        skip_str = f" | SKIP: {self.stats.import_skipped}" if self.stats.import_skipped > 0 else ""
        stats_table.add_row(
            "Imports",
            f"[{imp_color}]{imp_active} active[/{imp_color}] | OK: {self.stats.import_completed} | ERR: {self.stats.import_failed}{skip_str} | Queue: {self.stats.import_queue_size}"
        )

        stats_table.add_row("Records", f"[bold]{self.stats.total_records_imported:,}[/bold] total imported")

        layout["stats"].update(Panel(stats_table, title="Pipeline Status", border_style="green"))

        # Active Workers
        workers_table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        workers_table.add_column("Type", style="bold", width=4)
        workers_table.add_column("File", style="cyan", width=28)
        workers_table.add_column("Category", style="magenta", width=20)
        workers_table.add_column("Time", justify="right", width=6)

        for worker_id, worker in sorted(self.stats.active_downloads.items()):
            file_display = worker.file_name[:23] + "..." if len(worker.file_name) > 26 else worker.file_name
            cat_display = worker.category[:18] + ".." if len(worker.category) > 20 else worker.category
            workers_table.add_row(
                "[yellow]DL[/yellow]",
                file_display,
                cat_display or "-",
                f"[yellow]{worker.elapsed_display}[/yellow]"
            )

        for worker_id, worker in sorted(self.stats.active_imports.items()):
            file_display = worker.file_name[:23] + "..." if len(worker.file_name) > 26 else worker.file_name
            cat_display = worker.category[:18] + ".." if len(worker.category) > 20 else worker.category
            workers_table.add_row(
                "[cyan]IMP[/cyan]",
                file_display,
                cat_display or "-",
                f"[cyan]{worker.elapsed_display}[/cyan]"
            )

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
                file_display = file_record.file_name[:20] + "..." if len(file_record.file_name) > 23 else file_record.file_name
                category_display = (file_record.category or "Unknown")[:23] + "..." if len(file_record.category or "Unknown") > 26 else (file_record.category or "Unknown")

                status_map = {
                    'discovered': "[blue]discover[/blue]",
                    'download_pending': "[yellow]dl_pend[/yellow]",
                    'pending': "[green]ready[/green]",
                    'recrawl': "[orange3]recrawl[/orange3]",
                    'import_error': "[red]error[/red]",
                    'skipped': "[dim]skipped[/dim]"
                }
                status_display = status_map.get(file_record.status, file_record.status)
                leg_display = (file_record.legislatura or "-")[:6] + ".." if len(file_record.legislatura or "-") > 8 else (file_record.legislatura or "-")

                pending_table.add_row(status_display, file_display, category_display, leg_display)

            layout["pending"].update(Panel(pending_table, title=f"Queue ({len(pending_files)}+)", border_style="green"))
        else:
            layout["pending"].update(Panel("[dim]No pending files[/dim]", title="Queue", border_style="dim"))

        # Activity log
        activity_lines = []
        if self.stats.last_full_error:
            activity_lines.append("[bold red]LAST ERROR:[/bold red]")
            error_text = self.stats.last_full_error
            # Truncate long error messages for display
            truncated = error_text[:200] + "..." if len(error_text) > 200 else error_text
            activity_lines.append(f"[red]{truncated}[/red]")
            activity_lines.append("")

        if self.stats.recent_messages:
            max_recent = 8
            for msg in self.stats.recent_messages[-max_recent:]:
                activity_lines.append(msg)
        elif not self.stats.last_full_error:
            activity_lines.append("[dim]Waiting for activity...[/dim]")

        layout["activity"].update(Panel(
            "\n".join(activity_lines),
            title="Activity",
            border_style="red" if self.stats.last_full_error else "blue"
        ))

        # Error log tail
        error_log_lines = self.stats.get_error_log_tail(12)
        error_count = self.stats.import_failed
        layout["error_log"].update(Panel(
            "\n".join(error_log_lines),
            title=f"Error Log ({error_count})",
            border_style="red" if error_count > 0 else "dim"
        ))

        # Footer
        layout["footer"].update(Panel(
            f"Ctrl+C to stop | Max Downloads: {self.max_concurrent_downloads} | Max Imports: {self.max_concurrent_imports}",
            style="dim"
        ))

    async def _run_discovery(self, legislature_filter: str = None, category_filter: str = None):
        """Run discovery in thread pool."""
        try:
            from scripts.data_processing.discovery_service import DiscoveryService

            self.stats.discovery_running = True
            self.stats.discovery_status = "Starting..."
            self.stats.add_message("Discovery service starting...", priority='high')

            self._discovery_service = DiscoveryService(rate_limit_delay=self.discovery_rate_limit, quiet=True)

            loop = asyncio.get_event_loop()
            discovered_count = await loop.run_in_executor(
                None,
                self._discovery_service.discover_all_files,
                legislature_filter,
                category_filter
            )

            self.stats.discovery_completed = discovered_count
            self.stats.discovery_status = "Completed"
            self.stats.add_message(f"Discovery completed - {discovered_count} files", priority='high')

        except Exception as e:
            self.stats.discovery_status = "Error"
            self.stats.add_message(f"Discovery error: {str(e)}", priority='error')
            self.stats.error_occurred = True
        finally:
            self.stats.discovery_running = False

    async def _download_worker(self):
        """Background worker for concurrent downloads."""
        from database.connection import DatabaseSession
        from database.models import ImportStatus
        from scripts.data_processing.async_download_manager import AsyncDownloadManager

        self._download_manager = AsyncDownloadManager(
            max_concurrent=self.max_concurrent_downloads,
            rate_limit_delay=self.download_rate_limit
        )
        await self._download_manager.start()

        while self._running and not self._error_paused:
            try:
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

                    file_infos = []
                    for record in files_to_download:
                        record.status = 'downloading'
                        file_infos.append({
                            'id': record.id,
                            'file_url': record.file_url,
                            'file_name': record.file_name,
                            'category': record.category or "",
                            'legislatura': record.legislatura or ""
                        })
                    db_session.commit()

                async def download_with_tracking(file_info):
                    worker_id = self.stats.start_download(file_info['file_name'], file_info['category'])
                    try:
                        class SimpleRecord:
                            def __init__(self, d):
                                self.id = d['id']
                                self.file_url = d['file_url']
                                self.file_name = d['file_name']
                                self.category = d.get('category', 'unknown')
                                self.legislatura = d.get('legislatura', 'unknown')

                        result = await self._download_manager.download_file(SimpleRecord(file_info))
                        return result, file_info
                    finally:
                        self.stats.end_download(worker_id)

                tasks = [download_with_tracking(f) for f in file_infos]
                results = await asyncio.gather(*tasks, return_exceptions=True)

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
                            if result.skipped_existing:
                                self.stats.download_skipped += 1
                            else:
                                self.stats.download_completed += 1
                        else:
                            if result.is_not_found:
                                record.status = 'recrawl'
                                record.error_message = f"Not found: {result.error_message}"
                            else:
                                record.status = 'failed'
                                record.error_message = f"Download error: {result.error_message}"
                                self.stats.error_occurred = True
                            self.stats.download_failed += 1

                    db_session.commit()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats.add_message(f"Download worker error: {str(e)}", priority='error')
                self.stats.error_occurred = True
                await asyncio.sleep(1)

        if self._download_manager:
            await self._download_manager.close()

    async def _import_worker(self):
        """Background worker for parallel imports."""
        from database.connection import DatabaseSession
        from database.models import ImportStatus
        from scripts.data_processing.parallel_import_processor import ParallelImportProcessor

        self._import_processor = ParallelImportProcessor(max_workers=self.max_concurrent_imports)
        await self._import_processor.start()

        import_queue = asyncio.Queue()

        async def single_worker(worker_num: int):
            while self._running and not self._error_paused:
                try:
                    try:
                        file_info = await asyncio.wait_for(import_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue

                    worker_id = self.stats.start_import(file_info['file_name'], file_info['category'])
                    try:
                        result = await self._import_processor.process_file(
                            file_info['status_id'],
                            file_info['file_path'],
                            file_info['file_name'],
                            file_info['category']
                        )

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
                            self.stats.log_error(
                                file_info['file_name'],
                                file_info['category'],
                                file_info['legislatura'],
                                err_msg
                            )
                            self.stats.error_occurred = True

                    except Exception as e:
                        self.stats.import_failed += 1
                        self.stats.add_message(f"Import exception: {str(e)}", priority='error')
                        self.stats.log_error(
                            file_info.get('file_name', 'unknown'),
                            file_info.get('category', ''),
                            file_info.get('legislatura', ''),
                            str(e)
                        )
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
            while self._running and not self._error_paused:
                try:
                    if import_queue.qsize() < self.max_concurrent_imports:
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
                                for record in files_to_import:
                                    record.status = 'processing'
                                    await import_queue.put({
                                        'status_id': record.id,
                                        'file_path': record.file_path,
                                        'file_name': record.file_name,
                                        'category': record.category or "",
                                        'legislatura': record.legislatura or ""
                                    })
                                db_session.commit()

                    await asyncio.sleep(0.5)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.stats.add_message(f"Queue feeder error: {str(e)}", priority='error')
                    await asyncio.sleep(1)

        workers = [asyncio.create_task(single_worker(i)) for i in range(self.max_concurrent_imports)]
        feeder = asyncio.create_task(queue_feeder())

        try:
            await asyncio.gather(feeder, *workers, return_exceptions=True)
        except asyncio.CancelledError:
            pass
        finally:
            feeder.cancel()
            for w in workers:
                w.cancel()
            if self._import_processor:
                await self._import_processor.stop()

    async def _stats_updater(self):
        """Background task to update statistics from database."""
        from database.connection import DatabaseSession
        from database.models import ImportStatus

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

                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(2)

    async def run(self, legislature_filter: str = None, category_filter: str = None):
        """Run the pipeline with Rich UI."""
        self.stats.start_time = datetime.now()
        self._running = True

        # Set up fresh error log for this run
        error_log_path = self.stats.setup_error_log()
        self.console.print(f"Error log: {error_log_path}")

        file_types_str = ", ".join(self.allowed_file_types) if self.allowed_file_types else "ALL"
        self.stats.add_message(f"Pipeline started - Files: {file_types_str}", priority='high')
        self.stats.add_message(f"Workers: {self.max_concurrent_downloads} DL / {self.max_concurrent_imports} IMP", priority='high')

        if self.stats.stop_on_error:
            self.stats.add_message("Stop-on-error enabled", priority='high')

        layout = self.create_ui_layout()
        self.update_layout(layout)

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
                    if self.stats.stop_on_error and self.stats.error_occurred and not self._error_paused:
                        self.stats.add_message("Error occurred - paused (--stop-on-error)", priority='error')
                        self._error_paused = True

                    self.update_layout(layout)
                    await asyncio.sleep(0.5)

        except KeyboardInterrupt:
            self.console.print("\nShutdown requested...")
        finally:
            self._running = False
            self.console.print("Cancelling tasks...")

            for task in tasks:
                task.cancel()

            # Wait for tasks with timeout to avoid hanging
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self.console.print("Some tasks did not stop cleanly (timeout)")

            # Close error log with summary
            self.stats.close_error_log()
            if hasattr(self.stats, '_error_log_path'):
                self.console.print(f"Errors logged to: {self.stats._error_log_path}")

            self.console.print("Pipeline stopped")


# =============================================================================
# Headless Pipeline Runner (for ECS/CloudWatch)
# =============================================================================

class HeadlessPipelineRunner:
    """
    Pipeline runner for non-interactive environments (ECS, CI/CD).

    Uses structured JSON logging instead of Rich UI for CloudWatch Logs Insights.
    """

    def __init__(
        self,
        db_config: DatabaseConfig,
        discovery_rate_limit: float = 0.5,
        download_rate_limit: float = 0.3,
        max_concurrent_downloads: int = 5,
        max_concurrent_imports: int = 1,  # Temporarily 1 to test deadlock hypothesis
        allowed_file_types: List[str] = None,
        stop_on_error: bool = False,
        download_only: bool = False,
        import_only: bool = False,
        log_interval: float = 30.0
    ):
        from scripts.data_processing.pipeline_logging import (
            setup_pipeline_logging,
            ProgressLogger,
            PipelineProgress
        )

        self.db_config = db_config
        self.allowed_file_types = allowed_file_types or ['XML']
        self.stop_on_error = stop_on_error
        self.download_only = download_only
        self.import_only = import_only
        self.log_interval = log_interval

        # Configuration
        self.discovery_rate_limit = discovery_rate_limit
        self.download_rate_limit = download_rate_limit
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_concurrent_imports = max_concurrent_imports

        # Setup structured logging
        self.logger = setup_pipeline_logging(
            name='parliament.pipeline',
            force_json=True,
            extra_fields={
                'service': 'parliament-pipeline',
                'database': db_config.environment
            }
        )

        # Progress tracking
        self.progress = ProgressLogger(
            self.logger,
            interval=log_interval,
            stats=PipelineProgress()
        )

        # Components
        self._discovery_service = None
        self._download_manager = None
        self._import_processor = None

        # Control
        self._running = False
        self._error_occurred = False

    async def _run_discovery(self, legislature_filter: str = None, category_filter: str = None):
        """Run discovery service."""
        from scripts.data_processing.discovery_service import DiscoveryService

        self.progress.set_stage('discovery')

        try:
            self._discovery_service = DiscoveryService(
                rate_limit_delay=self.discovery_rate_limit,
                quiet=True
            )

            loop = asyncio.get_event_loop()
            discovered_count = await loop.run_in_executor(
                None,
                self._discovery_service.discover_all_files,
                legislature_filter,
                category_filter
            )

            self.progress.stats.discovery_completed = discovered_count
            self.logger.info(f"Discovery completed: {discovered_count} files found")

        except Exception as e:
            self.logger.error(f"Discovery error: {e}", extra={'error': str(e)})
            self._error_occurred = True

    async def _download_worker(self):
        """Background worker for downloads."""
        from database.connection import DatabaseSession
        from database.models import ImportStatus
        from scripts.data_processing.async_download_manager import AsyncDownloadManager

        self.progress.set_stage('download')

        self._download_manager = AsyncDownloadManager(
            max_concurrent=self.max_concurrent_downloads,
            rate_limit_delay=self.download_rate_limit
        )
        await self._download_manager.start()

        while self._running:
            try:
                with DatabaseSession() as db_session:
                    query = db_session.query(ImportStatus).filter(
                        ImportStatus.status.in_(['discovered', 'download_pending'])
                    )
                    if self.allowed_file_types:
                        query = query.filter(ImportStatus.file_type.in_(self.allowed_file_types))

                    files = query.limit(self.max_concurrent_downloads * 2).all()

                    if not files:
                        await asyncio.sleep(1)
                        continue

                    # Update progress stats
                    self.progress.stats.download_total = query.count()

                    file_infos = []
                    for record in files:
                        record.status = 'downloading'
                        file_infos.append({
                            'id': record.id,
                            'file_url': record.file_url,
                            'file_name': record.file_name,
                            'category': record.category or "",
                            'legislatura': record.legislatura or ""
                        })
                    db_session.commit()

                # Download files
                for file_info in file_infos:
                    try:
                        class SimpleRecord:
                            def __init__(self, d):
                                self.id = d['id']
                                self.file_url = d['file_url']
                                self.file_name = d['file_name']
                                self.category = d.get('category', 'unknown')
                                self.legislatura = d.get('legislatura', 'unknown')

                        result = await self._download_manager.download_file(SimpleRecord(file_info))

                        with DatabaseSession() as db_session:
                            record = db_session.get(ImportStatus, result.status_id)
                            if record:
                                if result.success:
                                    record.file_path = str(result.file_path)
                                    record.file_hash = result.file_hash
                                    record.file_size = result.file_size
                                    record.status = 'pending'
                                    record.updated_at = datetime.now()
                                    if result.skipped_existing:
                                        self.progress.stats.download_skipped += 1
                                    else:
                                        self.progress.stats.download_completed += 1
                                else:
                                    record.status = 'failed' if not result.is_not_found else 'recrawl'
                                    record.error_message = result.error_message
                                    self.progress.stats.download_failed += 1
                                db_session.commit()

                    except Exception as e:
                        self.logger.error(f"Download error for {file_info['file_name']}: {e}")
                        self.progress.stats.download_failed += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Download worker error: {e}")
                await asyncio.sleep(1)

        if self._download_manager:
            await self._download_manager.close()

    async def _import_worker(self):
        """Background worker for imports."""
        from database.connection import DatabaseSession
        from database.models import ImportStatus
        from scripts.data_processing.parallel_import_processor import ParallelImportProcessor

        self.progress.set_stage('import')

        self._import_processor = ParallelImportProcessor(max_workers=self.max_concurrent_imports)
        await self._import_processor.start()

        while self._running:
            try:
                with DatabaseSession() as db_session:
                    query = db_session.query(ImportStatus).filter(
                        ImportStatus.status.in_(['pending', 'import_error'])
                    )
                    if self.allowed_file_types:
                        query = query.filter(ImportStatus.file_type.in_(self.allowed_file_types))

                    files = query.limit(self.max_concurrent_imports).all()

                    if not files:
                        await asyncio.sleep(1)
                        continue

                    # Update progress stats
                    self.progress.stats.import_total = query.count()

                    for record in files:
                        record.status = 'processing'
                    db_session.commit()

                    file_infos = [{
                        'status_id': r.id,
                        'file_path': r.file_path,
                        'file_name': r.file_name,
                        'category': r.category or ""
                    } for r in files]

                # Process files
                for file_info in file_infos:
                    start_time = datetime.now()
                    try:
                        result = await self._import_processor.process_file(
                            file_info['status_id'],
                            file_info['file_path'],
                            file_info['file_name'],
                            file_info['category']
                        )

                        duration = (datetime.now() - start_time).total_seconds()

                        if result.success:
                            self.progress.log_file_complete(
                                file_info['file_name'],
                                result.records_imported,
                                duration,
                                file_info['category']
                            )
                        elif result.was_skipped:
                            self.progress.log_file_skipped(file_info['file_name'])
                        else:
                            self.progress.log_file_error(
                                file_info['file_name'],
                                result.error_message or "Unknown error",
                                file_info['category']
                            )
                            if self.stop_on_error:
                                self._running = False
                                break

                    except Exception as e:
                        self.progress.log_file_error(
                            file_info['file_name'],
                            str(e),
                            file_info['category']
                        )
                        if self.stop_on_error:
                            self._running = False
                            break

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Import worker error: {e}")
                await asyncio.sleep(1)

        if self._import_processor:
            await self._import_processor.stop()

    async def run(self, legislature_filter: str = None, category_filter: str = None):
        """Run the pipeline with structured logging."""
        self._running = True

        # Start progress logger
        self.progress.start()

        self.logger.info(
            f"Pipeline starting: db={self.db_config.environment}, "
            f"downloads={self.max_concurrent_downloads}, imports={self.max_concurrent_imports}, "
            f"file_types={self.allowed_file_types}"
        )

        tasks = []

        try:
            if not self.import_only:
                # Run discovery first, then start download worker
                await self._run_discovery(legislature_filter, category_filter)
                tasks.append(asyncio.create_task(self._download_worker()))

            if not self.download_only:
                tasks.append(asyncio.create_task(self._import_worker()))

            # Wait for all tasks
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except KeyboardInterrupt:
            self.logger.info("Pipeline interrupted by user")
        except Exception as e:
            self.logger.error(f"Pipeline error: {e}", extra={'error': str(e)})
        finally:
            self._running = False

            # Cancel any remaining tasks
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            # Stop progress logger and log summary
            self.progress.stop()
            self.progress.log_summary()


# =============================================================================
# CLI Entry Point (for direct invocation)
# =============================================================================

def main():
    """Main CLI interface for direct invocation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Parliament Data Pipeline",
        epilog="For ops CLI integration, use: ops pipeline run --local"
    )
    parser.add_argument('--database', '-d', type=str, choices=['local', 'prod', 'auto'], default='auto',
                       help='Database environment')
    parser.add_argument('--legislature', type=str, help='Filter by legislature')
    parser.add_argument('--category', type=str, help='Filter by category')
    parser.add_argument('--discovery-rate-limit', type=float, default=0.5)
    parser.add_argument('--download-rate-limit', type=float, default=0.3)
    parser.add_argument('--max-downloads', type=int, default=5)
    parser.add_argument('--file-types', nargs='*', choices=['XML', 'JSON', 'PDF', 'Archive', 'XSD'], default=['XML'])
    parser.add_argument('--all-file-types', action='store_true')
    parser.add_argument('--stop-on-error', action='store_true')
    parser.add_argument('--download-only', action='store_true')
    parser.add_argument('--import-only', action='store_true')
    parser.add_argument('--retry-failed', action='store_true', help='Reset failed imports to pending')

    args = parser.parse_args()

    # Setup database environment
    try:
        db_config = setup_database_environment(args.database)
        print(f"Database: {db_config.display_name}")
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Handle retry-failed
    if args.retry_failed:
        from database.connection import DatabaseSession
        from database.models import ImportStatus
        from sqlalchemy import update

        with DatabaseSession() as db_session:
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
    runner = LocalPipelineRunner(
        db_config=db_config,
        discovery_rate_limit=args.discovery_rate_limit,
        download_rate_limit=args.download_rate_limit,
        max_concurrent_downloads=args.max_downloads,
        max_concurrent_imports=1,
        allowed_file_types=allowed_file_types,
        stop_on_error=args.stop_on_error,
        download_only=args.download_only,
        import_only=args.import_only
    )

    try:
        asyncio.run(runner.run(
            legislature_filter=args.legislature,
            category_filter=args.category
        ))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
