#!/usr/bin/env python3
"""
Async Download Manager
======================

Manages concurrent downloads with semaphore-based rate limiting.
Uses asyncio for non-blocking I/O with configurable concurrency.

Features:
- Semaphore-based concurrency control (3-5 concurrent downloads)
- Rate limiting with minimum delay between requests
- Progress callbacks for UI updates
- Hash calculation for file integrity
- Atomic file writes
"""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Any

import aiofiles

from scripts.data_processing.async_http_client import AsyncHTTPClient


@dataclass
class DownloadResult:
    """Result of a download operation"""
    status_id: int
    file_name: str
    file_path: Optional[Path]
    file_size: int
    file_hash: Optional[str]
    success: bool
    error_message: Optional[str] = None
    is_not_found: bool = False  # For 404 errors that need recrawl
    skipped_existing: bool = False  # File already existed on disk


class AsyncDownloadManager:
    """Manages concurrent downloads with rate limiting"""

    def __init__(
        self,
        max_concurrent: int = 5,
        rate_limit_delay: float = 0.3,
        downloads_dir: Path = None
    ):
        """
        Initialize async download manager

        Args:
            max_concurrent: Maximum concurrent downloads (default: 5)
            rate_limit_delay: Minimum delay between requests in seconds (default: 0.3)
            downloads_dir: Directory to save downloaded files
        """
        self.max_concurrent = max_concurrent
        self.rate_limit_delay = rate_limit_delay

        # Downloads directory
        if downloads_dir is None:
            script_dir = Path(__file__).parent
            self.downloads_dir = script_dir / "data" / "downloads"
        else:
            self.downloads_dir = downloads_dir
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        # Concurrency controls
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._rate_limiter = asyncio.Lock()
        self._last_request_time = 0.0

        # HTTP client
        self._http_client = AsyncHTTPClient(
            max_retries=5,
            initial_backoff=1.0,
            max_backoff=120.0,
            backoff_multiplier=2.0,
            timeout=30,
            connector_limit=max_concurrent + 2  # Slightly more than concurrent limit
        )

        # State tracking
        self._running = False
        self._active_downloads = 0  # Track how many downloads are in progress

    @property
    def active_downloads(self) -> int:
        """Number of currently active downloads"""
        return self._active_downloads

    def _get_deterministic_path(self, import_record: Any) -> Path:
        """
        Get deterministic file path based on category/legislatura/filename.

        This ensures files can be found after database wipes, avoiding
        unnecessary re-downloads of already existing files.

        Structure: downloads_dir/{category}/{legislatura}/{file_name}
        """
        # Sanitize category and legislatura for filesystem
        category = (import_record.category or "unknown").replace(" ", "_").replace("/", "_")
        legislatura = (import_record.legislatura or "unknown").replace(" ", "_").replace("/", "_")

        # Create subdirectory path
        subdir = self.downloads_dir / category / legislatura
        subdir.mkdir(parents=True, exist_ok=True)

        return subdir / import_record.file_name

    def check_existing_file(self, import_record: Any) -> Optional[Path]:
        """
        Check if file already exists on disk.

        Returns the file path if it exists and has content, None otherwise.
        """
        file_path = self._get_deterministic_path(import_record)

        if file_path.exists() and file_path.stat().st_size > 0:
            return file_path

        return None

    async def _rate_limit(self):
        """Ensure minimum delay between requests"""
        async with self._rate_limiter:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    async def download_file(self, import_record: Any) -> DownloadResult:
        """
        Download a single file with semaphore limiting

        Args:
            import_record: ImportStatus database record with file_url, id, file_name,
                          category, legislatura

        Returns:
            DownloadResult with success/failure info
        """
        # Check if file already exists (before acquiring semaphore for efficiency)
        existing_path = self.check_existing_file(import_record)
        if existing_path:
            # File exists, calculate hash from existing file and skip download
            try:
                file_size = existing_path.stat().st_size
                with open(existing_path, 'rb') as f:
                    file_hash = hashlib.sha1(f.read()).hexdigest()

                return DownloadResult(
                    status_id=import_record.id,
                    file_name=import_record.file_name,
                    file_path=existing_path,
                    file_size=file_size,
                    file_hash=file_hash,
                    success=True,
                    skipped_existing=True
                )
            except Exception:
                # If we can't read the existing file, try re-downloading
                pass

        async with self._semaphore:
            self._active_downloads += 1
            try:
                # Apply rate limiting
                await self._rate_limit()

                # Download file content
                content, headers = await self._http_client.get(import_record.file_url)

                # Calculate hash
                file_hash = hashlib.sha1(content).hexdigest()

                # Save to disk using deterministic path (category/legislatura/filename)
                file_path = self._get_deterministic_path(import_record)

                # Write file atomically (write to temp, then rename)
                temp_path = file_path.with_suffix('.tmp')
                async with aiofiles.open(temp_path, 'wb') as f:
                    await f.write(content)

                # Rename to final path (atomic on most systems)
                temp_path.rename(file_path)

                return DownloadResult(
                    status_id=import_record.id,
                    file_name=import_record.file_name,
                    file_path=file_path,
                    file_size=len(content),
                    file_hash=file_hash,
                    success=True
                )

            except Exception as e:
                error_str = str(e).lower()
                is_not_found = (
                    '404' in error_str or
                    'not found' in error_str or
                    'no such file' in error_str
                )

                return DownloadResult(
                    status_id=import_record.id,
                    file_name=import_record.file_name,
                    file_path=None,
                    file_size=0,
                    file_hash=None,
                    success=False,
                    error_message=str(e),
                    is_not_found=is_not_found
                )
            finally:
                self._active_downloads -= 1

    async def download_batch(
        self,
        records: List[Any],
        progress_callback: Callable[[DownloadResult], None] = None
    ) -> List[DownloadResult]:
        """
        Download multiple files concurrently

        Args:
            records: List of ImportStatus records to download
            progress_callback: Optional async callback called after each download

        Returns:
            List of DownloadResult objects
        """
        # Create tasks for all downloads
        tasks = [self.download_file(record) for record in records]
        results = []

        # Process as they complete
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(result)
                else:
                    progress_callback(result)

        return results

    async def start(self):
        """Start the download manager"""
        self._running = True

    async def stop(self):
        """Stop the download manager and cleanup"""
        self._running = False
        await self._http_client.close()

    async def close(self):
        """Alias for stop() for consistency"""
        await self.stop()
