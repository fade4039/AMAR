"""Async file downloader with chunked writes and progress reporting."""

import os
from typing import Callable, Optional

import aiofiles

from ..api.client import AsyncAppleMusicClient


class AsyncDownloader:
    """Downloads files asynchronously with chunked streaming and progress callbacks."""

    def __init__(self, client: AsyncAppleMusicClient, chunk_size: int = 65536):
        self._client = client
        self._chunk_size = chunk_size

    async def download_file(
        self,
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Download a file in chunks without loading it entirely into memory.

        Args:
            url: URL to download
            dest_path: Local filesystem path to write the file
            progress_callback: Optional callback(downloaded_bytes, total_bytes)
        """
        await self._client._ensure_session()
        await self._client._rate_limiter.acquire()

        async with self._client._session.get(url) as resp:
            resp.raise_for_status()
            total = resp.content_length or 0
            downloaded = 0

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            async with aiofiles.open(dest_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(self._chunk_size):
                    await f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(downloaded, total)

    async def download_file_cdn(
        self,
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Download a file from a CDN URL without API authorization headers.

        Apple's CDN rejects requests with Authorization headers (HTTP 400).
        Use this for M3U8-resolved video files, artwork, and preview images.

        Args:
            url: CDN URL to download
            dest_path: Local filesystem path to write the file
            progress_callback: Optional callback(downloaded_bytes, total_bytes)
        """
        await self._client._ensure_session()

        async with self._client._cdn_session.get(url) as resp:
            resp.raise_for_status()
            total = resp.content_length or 0
            downloaded = 0

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            async with aiofiles.open(dest_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(self._chunk_size):
                    await f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(downloaded, total)

    async def download_bytes(
        self,
        url: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bytes:
        """Download a URL and return the content as bytes.

        Use this for small files (artwork, thumbnails). For large files
        (videos), use download_file() instead.
        """
        return await self._client.download_raw(url, progress_callback)
