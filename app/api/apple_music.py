"""Apple Music API client following Apple's official API documentation.

Reference: https://developer.apple.com/documentation/applemusicapi/
"""

import asyncio
import time
from typing import Any, Optional

import aiohttp

from app.config import AMARConfig, STOREFRONTS

API_BASE = "https://api.music.apple.com/v1"


class TokenExpiredError(Exception):
    pass


class RateLimitError(Exception):
    pass


class AppleMusicClient:
    """Async client for the Apple Music API with rate limiting, caching, and retry."""

    def __init__(self, config: AMARConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._cdn_session: Optional[aiohttp.ClientSession] = None
        self._cache: dict[str, tuple[float, Any]] = {}
        self._rate_tokens = config.rate_limit
        self._rate_last = time.monotonic()
        self._rate_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=self.config.max_concurrency, ssl=False)
            self._session = aiohttp.ClientSession(
                connector=connector,
                headers=self.config.api_headers,
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def _get_cdn_session(self) -> aiohttp.ClientSession:
        if self._cdn_session is None or self._cdn_session.closed:
            connector = aiohttp.TCPConnector(limit=self.config.max_concurrency, ssl=False)
            self._cdn_session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=120),
            )
        return self._cdn_session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
        if self._cdn_session and not self._cdn_session.closed:
            await self._cdn_session.close()

    async def _rate_limit(self):
        async with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._rate_last
            self._rate_tokens = min(
                self.config.rate_limit,
                self._rate_tokens + elapsed * self.config.rate_limit,
            )
            self._rate_last = now
            if self._rate_tokens < 1:
                wait = (1 - self._rate_tokens) / self.config.rate_limit
                await asyncio.sleep(wait)
                self._rate_tokens = 0
            else:
                self._rate_tokens -= 1

    def _cache_key(self, url: str, params: Optional[dict]) -> str:
        p = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
        return f"{url}?{p}"

    def _cache_get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            ts, data = self._cache[key]
            if time.monotonic() - ts < self.config.cache_ttl:
                return data
            del self._cache[key]
        return None

    async def get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make an authenticated GET request to the Apple Music API."""
        url = f"{API_BASE}{path}"
        cache_key = self._cache_key(url, params)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        await self._rate_limit()
        session = await self._get_session()

        for attempt in range(self.config.retry_max + 1):
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status == 401:
                        raise TokenExpiredError("Apple Music token expired or invalid")
                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 2))
                        await asyncio.sleep(retry_after)
                        continue
                    if resp.status >= 500:
                        if attempt < self.config.retry_max:
                            await asyncio.sleep(2 ** attempt)
                            continue
                    resp.raise_for_status()
                    data = await resp.json()
                    self._cache[cache_key] = (time.monotonic(), data)
                    return data
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt < self.config.retry_max:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        raise RateLimitError("Max retries exceeded due to rate limiting")

    async def get_text(self, url: str) -> str:
        """GET raw text from a URL (for M3U8 playlists etc.)."""
        await self._rate_limit()
        session = await self._get_session()
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def download_cdn(self, url: str, dest: str, progress_cb=None) -> str:
        """Download a file from Apple's CDN (no auth headers)."""
        import aiofiles

        session = await self._get_cdn_session()
        async with session.get(url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            async with aiofiles.open(dest, "wb") as f:
                async for chunk in resp.content.iter_chunked(self.config.chunk_size):
                    await f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total > 0:
                        await progress_cb(downloaded, total)
        return dest

    async def download_bytes(self, url: str) -> bytes:
        """Download raw bytes from a URL."""
        session = await self._get_cdn_session()
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.read()

    # ── Catalog endpoints (Apple Music API) ──

    async def search(
        self, term: str, storefront: Optional[str] = None,
        types: Optional[list[str]] = None, limit: int = 25, offset: int = 0,
    ) -> dict:
        """Search the Apple Music catalog.

        Ref: https://developer.apple.com/documentation/applemusicapi/search_for_catalog_resources
        """
        sf = storefront or self.config.storefront
        search_types = types or ["songs", "albums", "artists", "music-videos", "playlists"]
        return await self.get(f"/catalog/{sf}/search", {
            "term": term,
            "types": ",".join(search_types),
            "limit": str(limit),
            "offset": str(offset),
        })

    async def get_artist(self, artist_id: str, storefront: Optional[str] = None) -> dict:
        """Get artist details.

        Ref: https://developer.apple.com/documentation/applemusicapi/get_a_catalog_artist
        """
        sf = storefront or self.config.storefront
        return await self.get(
            f"/catalog/{sf}/artists/{artist_id}",
            {"include": "albums,music-videos,playlists", "views": "featured-albums,full-albums,appears-on-albums,similar-artists"},
        )

    async def get_artist_albums(
        self, artist_id: str, storefront: Optional[str] = None,
        limit: int = 100, offset: int = 0,
    ) -> dict:
        sf = storefront or self.config.storefront
        return await self.get(f"/catalog/{sf}/artists/{artist_id}/albums", {
            "limit": str(limit), "offset": str(offset),
        })

    async def get_artist_music_videos(
        self, artist_id: str, storefront: Optional[str] = None,
        limit: int = 100, offset: int = 0,
    ) -> dict:
        sf = storefront or self.config.storefront
        return await self.get(f"/catalog/{sf}/artists/{artist_id}/music-videos", {
            "limit": str(limit), "offset": str(offset),
        })

    async def get_album(self, album_id: str, storefront: Optional[str] = None) -> dict:
        """Get album details with tracks.

        Ref: https://developer.apple.com/documentation/applemusicapi/get_a_catalog_album
        """
        sf = storefront or self.config.storefront
        return await self.get(f"/catalog/{sf}/albums/{album_id}", {
            "include": "tracks,artists",
        })

    async def get_song(self, song_id: str, storefront: Optional[str] = None) -> dict:
        """Get song details.

        Ref: https://developer.apple.com/documentation/applemusicapi/get_a_catalog_song
        """
        sf = storefront or self.config.storefront
        return await self.get(f"/catalog/{sf}/songs/{song_id}", {
            "include": "albums,artists",
        })

    async def get_music_video(self, video_id: str, storefront: Optional[str] = None) -> dict:
        """Get music video details.

        Ref: https://developer.apple.com/documentation/applemusicapi/get_a_catalog_music_video
        """
        sf = storefront or self.config.storefront
        return await self.get(f"/catalog/{sf}/music-videos/{video_id}", {
            "include": "albums,artists",
        })

    async def get_playlist(self, playlist_id: str, storefront: Optional[str] = None) -> dict:
        """Get playlist details.

        Ref: https://developer.apple.com/documentation/applemusicapi/get_a_catalog_playlist
        """
        sf = storefront or self.config.storefront
        return await self.get(f"/catalog/{sf}/playlists/{playlist_id}", {
            "include": "tracks,curator",
        })

    async def get_station(self, station_id: str, storefront: Optional[str] = None) -> dict:
        """Get radio station details."""
        sf = storefront or self.config.storefront
        return await self.get(f"/catalog/{sf}/stations/{station_id}")

    async def get_charts(
        self, storefront: Optional[str] = None,
        types: Optional[list[str]] = None, limit: int = 50,
    ) -> dict:
        """Get catalog charts.

        Ref: https://developer.apple.com/documentation/applemusicapi/get_catalog_charts
        """
        sf = storefront or self.config.storefront
        chart_types = types or ["songs", "albums", "music-videos", "playlists"]
        return await self.get(f"/catalog/{sf}/charts", {
            "types": ",".join(chart_types),
            "limit": str(limit),
        })

    async def get_multiple_artists(
        self, ids: list[str], storefront: Optional[str] = None,
    ) -> dict:
        sf = storefront or self.config.storefront
        return await self.get(f"/catalog/{sf}/artists", {"ids": ",".join(ids)})

    async def get_multiple_albums(
        self, ids: list[str], storefront: Optional[str] = None,
    ) -> dict:
        sf = storefront or self.config.storefront
        return await self.get(f"/catalog/{sf}/albums", {"ids": ",".join(ids)})

    async def get_curator(self, curator_id: str, storefront: Optional[str] = None) -> dict:
        """Get curator details.

        Ref: https://developer.apple.com/documentation/applemusicapi/get_a_catalog_curator
        """
        sf = storefront or self.config.storefront
        return await self.get(f"/catalog/{sf}/curators/{curator_id}")

    async def get_search_suggestions(
        self, term: str, storefront: Optional[str] = None,
        types: Optional[list[str]] = None,
    ) -> dict:
        """Get search suggestions/hints.

        Ref: https://developer.apple.com/documentation/applemusicapi/get_catalog_search_suggestions
        """
        sf = storefront or self.config.storefront
        search_types = types or ["songs", "albums", "artists"]
        return await self.get(f"/catalog/{sf}/search/suggestions", {
            "term": term,
            "types": ",".join(search_types),
            "limit": "10",
        })

    # ── Pagination helper ──

    async def collect_all(self, initial_path: str, params: Optional[dict] = None) -> list:
        """Follow pagination to collect all results from an endpoint."""
        results = []
        data = await self.get(initial_path, params)
        while data:
            if "data" in data:
                results.extend(data["data"])
            next_url = data.get("next")
            if not next_url:
                break
            data = await self.get(next_url)
        return results

    # ── Utility: resolve artwork URL ──

    @staticmethod
    def artwork_url(artwork: dict, width: int = 3000, height: int = 3000) -> Optional[str]:
        """Build a full artwork URL from an Apple Music artwork object.

        Apple returns artwork URLs with {w} and {h} placeholders.
        Ref: https://developer.apple.com/documentation/applemusicapi/artwork
        """
        url = artwork.get("url")
        if not url:
            return None
        return url.replace("{w}", str(width)).replace("{h}", str(height))

    @staticmethod
    def editorial_artwork_urls(attrs: dict, width: int = 3000, height: int = 3000) -> dict[str, str]:
        """Extract all editorial artwork URLs from resource attributes."""
        urls = {}
        for key in ("artwork", "editorialArtwork", "editorialVideo"):
            obj = attrs.get(key)
            if not obj:
                continue
            if isinstance(obj, dict):
                if "url" in obj:
                    urls[key] = AppleMusicClient.artwork_url(obj, width, height)
                else:
                    for sub_key, sub_obj in obj.items():
                        if isinstance(sub_obj, dict) and "url" in sub_obj:
                            urls[f"{key}.{sub_key}"] = AppleMusicClient.artwork_url(sub_obj, width, height)
        return urls
