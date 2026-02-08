#!/usr/bin/env python3
"""
HTTP Retry Utilities with Exponential Backoff
============================================

Provides robust HTTP request handling with exponential backoff retry logic
for handling network timeouts and connection errors in parliament data processing.

Features:
- Exponential backoff with jitter to prevent thundering herd
- Configurable retry parameters (max_retries, backoff_multiplier, max_delay)
- Automatic backoff reset on successful requests
- Support for both GET and HEAD requests
- Graceful handling of different error types
- Thread-safe retry state management
"""

import random
import time
from threading import Lock
from typing import Dict, Optional

import requests
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout, Timeout


class HTTPRetryClient:
    """HTTP client with exponential backoff retry logic"""
    
    def __init__(
        self,
        max_retries: int = 5,
        initial_backoff: float = 1.0,
        max_backoff: float = 120.0,
        backoff_multiplier: float = 2.0,
        timeout: int = 30,
        user_agent: str = None
    ):
        """
        Initialize HTTP retry client
        
        Args:
            max_retries: Maximum retry attempts per request
            initial_backoff: Initial backoff delay in seconds
            max_backoff: Maximum backoff delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
            timeout: Request timeout in seconds
            user_agent: User-Agent header to use
        """
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        self.timeout = timeout
        
        # Thread-safe retry state
        self._current_backoff = initial_backoff
        self._backoff_lock = Lock()
        
        # Create session with default headers
        self.session = requests.Session()
        if user_agent:
            self.session.headers.update({'User-Agent': user_agent})
        else:
            self.session.headers.update({
                'User-Agent': 'Fiscaliza/1.0 (https://fiscaliza.pt; open-source parliamentary data)'
            })
    
    def _reset_backoff(self):
        """Reset backoff delay to initial value on successful request"""
        with self._backoff_lock:
            if self._current_backoff > self.initial_backoff:
                print(f"SUCCESS: Resetting exponential backoff (was {self._current_backoff:.1f}s)")
            self._current_backoff = self.initial_backoff
    
    def _get_next_backoff_delay(self) -> float:
        """Calculate next backoff delay with exponential increase and jitter"""
        with self._backoff_lock:
            # Add jitter (±25% random variation) to prevent thundering herd
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
        # Retry on network/timeout errors, but not on HTTP errors (4xx, 5xx)
        return isinstance(exception, (ConnectTimeout, ReadTimeout, ConnectionError, Timeout))
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic"""
        retries = 0
        indent = kwargs.pop('indent', '')
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        while retries <= self.max_retries:
            try:
                # Make the actual request
                if method.upper() == 'GET':
                    response = self.session.get(url, **kwargs)
                elif method.upper() == 'HEAD':
                    response = self.session.head(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                
                # Success! Reset backoff delay for future requests
                self._reset_backoff()
                return response
                
            except Exception as e:
                if not self._should_retry(e) or retries >= self.max_retries:
                    if retries >= self.max_retries:
                        print(f"{indent}ERROR: Max retries ({self.max_retries}) exceeded for URL: {url}")
                        print(f"{indent}Last error: {e}")
                    elif not self._should_retry(e):
                        print(f"{indent}HTTP ERROR (no retry): {e}")
                    raise
                
                retries += 1
                delay = self._get_next_backoff_delay()
                print(f"{indent}NETWORK ERROR (attempt {retries}/{self.max_retries}): {e}")
                print(f"{indent}Retrying in {delay:.1f} seconds with exponential backoff...")
                
                # Sleep with small intervals for more responsive interruption
                sleep_intervals = max(1, int(delay * 4))  # Check every 0.25 seconds
                for _ in range(sleep_intervals):
                    time.sleep(0.25)
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make GET request with retry logic"""
        return self._make_request('GET', url, **kwargs)
    
    def head(self, url: str, **kwargs) -> requests.Response:
        """Make HEAD request with retry logic"""
        return self._make_request('HEAD', url, **kwargs)
    
    def get_metadata(self, url: str, **kwargs) -> Dict[str, Optional[str]]:
        """Get HTTP metadata using HEAD request with retry logic"""
        try:
            response = self.head(url, **kwargs)
            return {
                'last_modified': response.headers.get('Last-Modified'),
                'content_length': response.headers.get('Content-Length'),
                'etag': response.headers.get('ETag'),
                'content_type': response.headers.get('Content-Type')
            }
        except Exception as e:
            # If HEAD fails, return empty metadata but don't fail the entire operation
            indent = kwargs.get('indent', '')
            print(f"{indent}WARN:  HTTP metadata error: {e}")
            return {
                'last_modified': None,
                'content_length': None,
                'etag': None,
                'content_type': None
            }


# Global default client instance
_default_client = None
_client_lock = Lock()


def get_default_client() -> HTTPRetryClient:
    """Get global default HTTP retry client (thread-safe singleton)"""
    global _default_client
    with _client_lock:
        if _default_client is None:
            _default_client = HTTPRetryClient()
        return _default_client


def safe_request_get(url: str, headers: Dict = None, timeout: int = 30, 
                    indent: str = "", **kwargs) -> requests.Response:
    """
    Make safe HTTP GET request with retry logic (backward compatibility function)
    
    This function provides compatibility with existing code that uses the
    safe_request_get pattern from unified_downloader.py
    """
    client = get_default_client()
    
    # Prepare request arguments
    request_kwargs = kwargs.copy()
    if headers:
        request_kwargs['headers'] = headers
    if timeout:
        request_kwargs['timeout'] = timeout
    if indent:
        request_kwargs['indent'] = indent
    
    return client.get(url, **request_kwargs)


def safe_request_head(url: str, headers: Dict = None, timeout: int = 30,
                     indent: str = "", **kwargs) -> requests.Response:
    """Make safe HTTP HEAD request with retry logic"""
    client = get_default_client()
    
    # Prepare request arguments
    request_kwargs = kwargs.copy()
    if headers:
        request_kwargs['headers'] = headers
    if timeout:
        request_kwargs['timeout'] = timeout
    if indent:
        request_kwargs['indent'] = indent
    
    return client.head(url, **request_kwargs)


def get_http_metadata(url: str, **kwargs) -> Dict[str, Optional[str]]:
    """Get HTTP metadata with retry logic"""
    client = get_default_client()
    return client.get_metadata(url, **kwargs)


# Export commonly used exception types for error handling
__all__ = [
    'HTTPRetryClient',
    'safe_request_get', 
    'safe_request_head',
    'get_http_metadata',
    'get_default_client',
    'ConnectTimeout',
    'ReadTimeout', 
    'ConnectionError',
    'Timeout'
]