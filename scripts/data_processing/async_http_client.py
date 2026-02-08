#!/usr/bin/env python3
"""
Async HTTP Client with Exponential Backoff
==========================================

Async version of HTTPRetryClient using aiohttp for concurrent downloads.
Provides robust HTTP request handling with exponential backoff retry logic.

Features:
- Async/await pattern for non-blocking I/O
- Exponential backoff with jitter to prevent thundering herd
- Configurable retry parameters (max_retries, backoff_multiplier, max_delay)
- Connection pooling with configurable limits
- Automatic backoff reset on successful requests
"""

import asyncio
import random
from typing import Dict, Optional, Tuple

import aiohttp
from aiohttp import ClientError, ClientTimeout


class AsyncHTTPClient:
    """Async HTTP client with exponential backoff retry logic"""

    def __init__(
        self,
        max_retries: int = 5,
        initial_backoff: float = 1.0,
        max_backoff: float = 120.0,
        backoff_multiplier: float = 2.0,
        timeout: int = 30,
        connector_limit: int = 10,
        user_agent: str = None
    ):
        """
        Initialize async HTTP client

        Args:
            max_retries: Maximum retry attempts per request
            initial_backoff: Initial backoff delay in seconds
            max_backoff: Maximum backoff delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
            timeout: Request timeout in seconds
            connector_limit: Maximum concurrent connections
            user_agent: User-Agent header to use
        """
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        self.timeout = ClientTimeout(total=timeout)
        self.connector_limit = connector_limit
        self.user_agent = user_agent or 'Fiscaliza/1.0 (https://fiscaliza.pt; open-source parliamentary data)'

        # State
        self._current_backoff = initial_backoff
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session (thread-safe)"""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=self.connector_limit,
                        limit_per_host=self.connector_limit
                    )
                    self._session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=self.timeout,
                        headers={'User-Agent': self.user_agent}
                    )
        return self._session

    def _reset_backoff(self):
        """Reset backoff delay to initial value on successful request"""
        self._current_backoff = self.initial_backoff

    def _get_next_backoff_delay(self) -> float:
        """Calculate next backoff delay with exponential increase and jitter"""
        # Add jitter (+-25% random variation) to prevent thundering herd
        jitter = random.uniform(0.75, 1.25)
        delay = self._current_backoff * jitter

        # Increase for next time
        self._current_backoff = min(
            self._current_backoff * self.backoff_multiplier,
            self.max_backoff
        )

        return delay

    def _should_retry(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry"""
        # Retry on network/timeout errors
        return isinstance(exception, (
            asyncio.TimeoutError,
            ClientError,
            aiohttp.ServerDisconnectedError,
            aiohttp.ClientConnectorError,
            aiohttp.ClientPayloadError,
            ConnectionResetError,
            ConnectionError
        ))

    async def get(self, url: str, **kwargs) -> Tuple[bytes, Dict]:
        """
        Make async GET request with retry logic

        Returns:
            Tuple of (content bytes, headers dict)
        """
        session = await self._get_session()
        retries = 0
        last_exception = None

        while retries <= self.max_retries:
            try:
                async with session.get(url, **kwargs) as response:
                    response.raise_for_status()
                    content = await response.read()
                    headers = dict(response.headers)

                    # Success! Reset backoff delay
                    self._reset_backoff()
                    return content, headers

            except aiohttp.ClientResponseError as e:
                # HTTP errors (4xx, 5xx) - don't retry most, but retry 5xx
                if e.status >= 500 and retries < self.max_retries:
                    retries += 1
                    delay = self._get_next_backoff_delay()
                    await asyncio.sleep(delay)
                    last_exception = e
                    continue
                raise

            except Exception as e:
                if not self._should_retry(e) or retries >= self.max_retries:
                    raise

                retries += 1
                delay = self._get_next_backoff_delay()
                last_exception = e
                await asyncio.sleep(delay)

        # Should not reach here, but raise last exception if we do
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Max retries exceeded for {url}")

    async def head(self, url: str, **kwargs) -> Dict:
        """Make async HEAD request with retry logic"""
        session = await self._get_session()
        retries = 0

        while retries <= self.max_retries:
            try:
                async with session.head(url, **kwargs) as response:
                    response.raise_for_status()
                    self._reset_backoff()
                    return dict(response.headers)

            except Exception as e:
                if not self._should_retry(e) or retries >= self.max_retries:
                    raise

                retries += 1
                delay = self._get_next_backoff_delay()
                await asyncio.sleep(delay)

        raise RuntimeError(f"Max retries exceeded for HEAD {url}")

    async def get_metadata(self, url: str, **kwargs) -> Dict[str, Optional[str]]:
        """Get HTTP metadata using HEAD request with retry logic"""
        try:
            headers = await self.head(url, **kwargs)
            return {
                'last_modified': headers.get('Last-Modified'),
                'content_length': headers.get('Content-Length'),
                'etag': headers.get('ETag'),
                'content_type': headers.get('Content-Type')
            }
        except Exception:
            # If HEAD fails, return empty metadata but don't fail
            return {
                'last_modified': None,
                'content_length': None,
                'etag': None,
                'content_type': None
            }

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            # Give the connection pool time to clean up
            await asyncio.sleep(0.1)


# Module-level client for convenience
_default_client: Optional[AsyncHTTPClient] = None


async def get_default_client() -> AsyncHTTPClient:
    """Get global default async HTTP client"""
    global _default_client
    if _default_client is None:
        _default_client = AsyncHTTPClient()
    return _default_client


async def close_default_client():
    """Close the global default client"""
    global _default_client
    if _default_client:
        await _default_client.close()
        _default_client = None
