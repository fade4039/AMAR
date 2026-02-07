"""Async Apple Music API client with connection pooling, rate limiting, retry, and caching."""

import asyncio
import logging
from time import monotonic
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)

API_BASE = "https://amp-api.music.apple.com"


class APIError(Exception):
    """Raised when an API request fails after retries."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class TokenExpiredError(APIError):
    """Raised when the API returns 401 Unauthorized."""


class _CacheEntry:
    __slots__ = ("data", "expires_at")

    def __init__(self, data: Any, ttl: int):
        self.data = data
        self.expires_at = monotonic() + ttl

    def is_valid(self) -> bool:
        return monotonic() < self.expires_at


class AsyncRateLimiter:
    """Token-bucket rate limiter for async code."""

    def __init__(self, rate: float = 18.0, burst: int = 10):
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            if self._last_refill == 0.0:
                self._last_refill = now

            elapsed = now - self._last_refill
            self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
            self._last_refill = now

            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
                self._last_refill = asyncio.get_event_loop().time()
            else:
                self._tokens -= 1.0

    def adjust_rate(self, new_rate: float) -> None:
        """Dynamically adjust the rate (called when API headers hint at limits)."""
        self._rate = max(1.0, min(new_rate, 20.0))


class AsyncAppleMusicClient:
    """Async HTTP client for the Apple Music API.

    Features:
    - Connection pooling via aiohttp.TCPConnector
    - Token-bucket rate limiting (default 18 req/s)
    - Exponential backoff retry for 429 and 5xx errors
    - In-memory TTL cache for API responses
    """

    def __init__(self, config: "AMARConfig"):  # noqa: F821
        self._config = config
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._cdn_connector: Optional[aiohttp.TCPConnector] = None
        self._cdn_session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = AsyncRateLimiter(
            rate=config.rate_limit,
            burst=min(int(config.rate_limit), 10),
        )
        self._cache: Dict[str, _CacheEntry] = {}
        self._log_callback: Optional[Callable[[str, str], None]] = None

    def set_log_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set a callback for log messages: callback(message, level)."""
        self._log_callback = callback

    def _log(self, message: str, level: str = "INFO") -> None:
        logger.log(getattr(logging, level, logging.INFO), message)
        if self._log_callback:
            self._log_callback(message, level)

    async def _ensure_session(self) -> None:
        if self._session is None or self._session.closed:
            self._connector = aiohttp.TCPConnector(
                limit=self._config.max_concurrency,
                limit_per_host=self._config.max_concurrency,
                ttl_dns_cache=300,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                headers=self._config.api_headers,
                timeout=aiohttp.ClientTimeout(total=30, connect=10),
            )
        # CDN session: no auth headers, longer timeout for large video files
        if self._cdn_session is None or self._cdn_session.closed:
            self._cdn_connector = aiohttp.TCPConnector(
                limit=self._config.max_concurrency,
                limit_per_host=self._config.max_concurrency,
                ttl_dns_cache=300,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )
            self._cdn_session = aiohttp.ClientSession(
                connector=self._cdn_connector,
                timeout=aiohttp.ClientTimeout(total=120, connect=10),
            )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        if self._cdn_session and not self._cdn_session.closed:
            await self._cdn_session.close()
        self._session = None
        self._connector = None
        self._cdn_session = None
        self._cdn_connector = None
        self._cache.clear()

    async def __aenter__(self) -> "AsyncAppleMusicClient":
        await self._ensure_session()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    def _cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        if params:
            return f"{url}?{urlencode(sorted(params.items()))}"
        return url

    def _update_rate_from_headers(self, headers: Dict) -> None:
        """Dynamically adjust rate limit based on API response headers."""
        rate_header = headers.get("X-Rate-Limit", "")
        if "user-hour-rem" in rate_header:
            try:
                # Format: "user-hour-rem:1500"
                remaining = int(rate_header.split(":")[-1])
                if remaining < 200:
                    self._rate_limiter.adjust_rate(5.0)
                    self._log(f"Rate limit low ({remaining} remaining), throttling to 5 req/s", "WARNING")
                elif remaining < 500:
                    self._rate_limiter.adjust_rate(10.0)
            except (ValueError, IndexError):
                pass

    async def get(
        self,
        path: str,
        params: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ) -> Dict:
        """Make a GET request to the Apple Music API.

        Args:
            path: API path (e.g. '/v1/catalog/us/artists/123')
            params: Query parameters
            use_cache: Whether to use the response cache
            cache_ttl: Override the default cache TTL for this request

        Returns:
            Parsed JSON response as a dict

        Raises:
            APIError: On non-retryable errors or after max retries
            TokenExpiredError: On 401 Unauthorized
        """
        await self._ensure_session()

        if path.startswith("http"):
            url = path
        else:
            url = f"{API_BASE}{path}"

        cache_key = self._cache_key(url, params)
        if use_cache and cache_key in self._cache:
            entry = self._cache[cache_key]
            if entry.is_valid():
                return entry.data
            del self._cache[cache_key]

        ttl = cache_ttl or self._config.cache_ttl
        last_error = None

        for attempt in range(self._config.retry_max + 1):
            await self._rate_limiter.acquire()
            try:
                async with self._session.get(url, params=params) as resp:
                    self._update_rate_from_headers(resp.headers)

                    if resp.status == 200:
                        data = await resp.json()
                        if use_cache:
                            self._cache[cache_key] = _CacheEntry(data, ttl)
                        return data

                    elif resp.status == 401:
                        raise TokenExpiredError(
                            "Token expired or invalid (HTTP 401). Please refresh your token.",
                            status=401,
                        )

                    elif resp.status == 429:
                        retry_after = float(resp.headers.get("Retry-After", 2 ** attempt))
                        self._log(f"Rate limited (429). Waiting {retry_after:.1f}s...", "WARNING")
                        await asyncio.sleep(retry_after)
                        continue

                    elif resp.status >= 500:
                        wait = 2 ** attempt
                        self._log(f"Server error ({resp.status}). Retry in {wait}s...", "WARNING")
                        await asyncio.sleep(wait)
                        continue

                    else:
                        body = await resp.text()
                        raise APIError(f"HTTP {resp.status}: {body[:200]}", status=resp.status)

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self._config.retry_max:
                    wait = 2 ** attempt
                    self._log(f"Connection error: {e}. Retry in {wait}s...", "WARNING")
                    await asyncio.sleep(wait)
                    continue
                raise APIError(f"Connection failed after {self._config.retry_max + 1} attempts: {e}")

        raise APIError(f"Max retries exceeded for {url}: {last_error}")

    async def download_raw(
        self,
        url: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bytes:
        """Download raw bytes from a URL (for small files like artwork).

        For large files, use AsyncDownloader.download_chunked() instead.
        """
        await self._ensure_session()
        await self._rate_limiter.acquire()

        async with self._session.get(url) as resp:
            resp.raise_for_status()
            total = resp.content_length or 0
            chunks = []
            downloaded = 0

            async for chunk in resp.content.iter_chunked(self._config.chunk_size):
                chunks.append(chunk)
                downloaded += len(chunk)
                if progress_callback and total:
                    progress_callback(downloaded, total)

            return b"".join(chunks)

    async def get_text(self, url: str) -> str:
        """Fetch a URL and return the response body as text."""
        await self._ensure_session()
        await self._rate_limiter.acquire()

        async with self._session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

    # --- CDN methods (no Authorization headers) ---
    # The Apple Music CDN rejects requests with API auth headers (400 Bad Request).
    # These methods use a plain session for M3U8 playlists, video files, and artwork.

    async def get_text_cdn(self, url: str) -> str:
        """Fetch text from a CDN URL without API authorization headers."""
        await self._ensure_session()
        async with self._cdn_session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def download_cdn(
        self,
        url: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bytes:
        """Download raw bytes from a CDN URL without API authorization headers."""
        await self._ensure_session()
        async with self._cdn_session.get(url) as resp:
            resp.raise_for_status()
            total = resp.content_length or 0
            chunks = []
            downloaded = 0
            async for chunk in resp.content.iter_chunked(self._config.chunk_size):
                chunks.append(chunk)
                downloaded += len(chunk)
                if progress_callback and total:
                    progress_callback(downloaded, total)
            return b"".join(chunks)
