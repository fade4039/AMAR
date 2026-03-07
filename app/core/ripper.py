"""Core asset ripper for Apple Music content.

Downloads artwork, editorial content, metadata, and video preview frames
from the Apple Music API. All operations use publicly available API data only.
"""

import asyncio
import re
from pathlib import Path
from typing import Any, Callable, Optional

import aiofiles

from app.api.apple_music import AppleMusicClient
from app.config import AMARConfig, STOREFRONTS
from app.core.utils import clean_filename, convert_ms, ensure_dir


class ProgressCallback:
    """Simple callback interface for progress reporting."""

    def __init__(self):
        self.on_progress: Optional[Callable] = None  # (task_id, progress, status, detail)
        self.on_log: Optional[Callable] = None  # (level, message)
        self.on_complete: Optional[Callable] = None  # (task_id, result)
        self.on_error: Optional[Callable] = None  # (task_id, error)

    def progress(self, task_id: str, progress: float, status: str, detail: str = ""):
        if self.on_progress:
            self.on_progress(task_id, progress, status, detail)

    def log(self, level: str, message: str):
        if self.on_log:
            self.on_log(level, message)

    def complete(self, task_id: str, result: dict):
        if self.on_complete:
            self.on_complete(task_id, result)

    def error(self, task_id: str, error: str):
        if self.on_error:
            self.on_error(task_id, error)


class AssetRipper:
    """Downloads assets (artwork, metadata, editorial content) from Apple Music."""

    def __init__(self, client: AppleMusicClient, config: AMARConfig,
                 callback: Optional[ProgressCallback] = None):
        self.client = client
        self.config = config
        self.cb = callback or ProgressCallback()

    async def _download_artwork(self, url: str, dest: Path, label: str):
        try:
            await self.client.download_cdn(str(url), str(dest))
            self.cb.log("success", f"Downloaded {label}")
        except Exception as e:
            self.cb.log("warning", f"Failed to download {label}: {e}")

    async def _save_text(self, content: str, dest: Path):
        async with aiofiles.open(str(dest), "w", encoding="utf-8") as f:
            await f.write(content)

    async def _resolve_m3u8(self, url: str) -> Optional[str]:
        try:
            text = await self.client.get_text(url)
            lines = text.strip().splitlines()
            best_url = None
            best_bw = 0
            for i, line in enumerate(lines):
                if line.startswith("#EXT-X-STREAM-INF"):
                    bw_match = re.search(r"BANDWIDTH=(\d+)", line)
                    bw = int(bw_match.group(1)) if bw_match else 0
                    if bw > best_bw and i + 1 < len(lines):
                        best_bw = bw
                        candidate = lines[i + 1].strip()
                        if not candidate.startswith("#"):
                            best_url = candidate
            return best_url
        except Exception:
            return None

    # ── Artist ──

    async def rip_artist(self, artist_id: str, storefront: str, task_id: str) -> dict:
        data = await self.client.get_artist(artist_id, storefront)
        artist = data["data"][0]
        attrs = artist["attributes"]
        name = clean_filename(attrs.get("name", "Unknown Artist"))
        base = ensure_dir(Path(self.config.save_path) / name / f"[{storefront.upper()}]")

        files_downloaded = 0
        result = {"name": attrs.get("name"), "type": "artist", "files": []}

        self.cb.progress(task_id, 0.1, "downloading", f"Processing artist: {attrs.get('name')}")

        if self.config.download_artwork:
            artwork = attrs.get("artwork")
            if artwork and artwork.get("url"):
                url = self.client.artwork_url(artwork, self.config.artwork_size, self.config.artwork_size)
                dest = base / f"{name} - Artwork.{'png' if 'png' in url else 'jpg'}"
                await self._download_artwork(url, dest, "artist artwork")
                result["files"].append(str(dest))
                files_downloaded += 1

        self.cb.progress(task_id, 0.3, "downloading", "Checking editorial content...")

        if self.config.download_editorial:
            edit_art = attrs.get("editorialArtwork", {})
            for key, art_obj in edit_art.items():
                if isinstance(art_obj, dict) and art_obj.get("url"):
                    url = self.client.artwork_url(art_obj, self.config.artwork_size, self.config.artwork_size)
                    ext = "png" if "png" in url else "jpg"
                    dest = base / f"{name} - Editorial {clean_filename(key)}.{ext}"
                    await self._download_artwork(url, dest, f"editorial artwork ({key})")
                    result["files"].append(str(dest))
                    files_downloaded += 1

        self.cb.progress(task_id, 0.5, "downloading", "Checking editorial videos...")

        if self.config.download_videos:
            edit_vid = attrs.get("editorialVideo", {})
            for key, vid_obj in edit_vid.items():
                if isinstance(vid_obj, dict):
                    hls_url = vid_obj.get("hlsUrl") or vid_obj.get("video")
                    preview_url = vid_obj.get("previewFrame", {}).get("url")
                    if hls_url:
                        resolved = await self._resolve_m3u8(hls_url)
                        if resolved:
                            dest = base / f"{name} - Editorial Video {clean_filename(key)}.ts"
                            try:
                                await self.client.download_cdn(resolved, str(dest))
                                result["files"].append(str(dest))
                                files_downloaded += 1
                                self.cb.log("success", f"Downloaded editorial video ({key})")
                            except Exception as e:
                                self.cb.log("warning", f"Failed to download video: {e}")
                    if preview_url:
                        url = self.client.artwork_url(
                            {"url": preview_url}, self.config.artwork_size, self.config.artwork_size
                        )
                        if url:
                            dest = base / f"{name} - Video Preview {clean_filename(key)}.jpg"
                            await self._download_artwork(url, dest, f"video preview ({key})")
                            result["files"].append(str(dest))
                            files_downloaded += 1

        self.cb.progress(task_id, 0.7, "downloading", "Saving metadata...")

        if self.config.download_artwork:
            try:
                ext_data = await self.client.get(
                    f"/catalog/{storefront}/artists/{artist_id}",
                    {"extend": "artistBio,bornOrFormed,editorialArtwork,editorialVideo,isGroup,origin,heroArt"},
                )
                ext_attrs = ext_data["data"][0].get("attributes", {})
                hero = ext_attrs.get("heroArt")
                if hero and hero.get("url"):
                    url = self.client.artwork_url(hero, 4000, 1600)
                    dest = base / f"{name} - Hero.{'png' if 'png' in url else 'jpg'}"
                    await self._download_artwork(url, dest, "hero artwork")
                    result["files"].append(str(dest))
                    files_downloaded += 1
                attrs.update(ext_attrs)
            except Exception:
                pass

        if self.config.download_metadata:
            info_lines = [
                f"Artist: {attrs.get('name', 'N/A')}",
                f"Genre: {', '.join(attrs.get('genreNames', []))}",
                f"Origin: {attrs.get('origin', 'N/A')}",
                f"Born/Formed: {attrs.get('bornOrFormed', 'N/A')}",
                f"Is Group: {attrs.get('isGroup', 'N/A')}",
                f"URL: {attrs.get('url', 'N/A')}",
                f"Apple Music ID: {artist_id}",
                "",
            ]
            bio = attrs.get("artistBio") or attrs.get("editorialNotes", {}).get("standard", "")
            if bio:
                bio_clean = re.sub(r"<[^>]+>", "", bio)
                info_lines.append(f"Biography:\n{bio_clean}")
            await self._save_text("\n".join(info_lines), base / "INFO.txt")
            result["files"].append(str(base / "INFO.txt"))

        self.cb.progress(task_id, 1.0, "complete", f"Done - {files_downloaded} files downloaded")
        result["total_files"] = files_downloaded
        return result

    # ── Album ──

    async def rip_album(self, album_id: str, storefront: str, task_id: str) -> dict:
        data = await self.client.get_album(album_id, storefront)
        album = data["data"][0]
        attrs = album["attributes"]

        artist_name = clean_filename(attrs.get("artistName", "Unknown Artist"))
        album_name = clean_filename(attrs.get("name", "Unknown Album"))
        base = ensure_dir(
            Path(self.config.save_path) / artist_name / album_name / f"[{storefront.upper()}]"
        )

        files_downloaded = 0
        result = {"name": attrs.get("name"), "artist": attrs.get("artistName"), "type": "album", "files": []}

        self.cb.progress(task_id, 0.1, "downloading", f"Processing album: {attrs.get('name')}")

        if self.config.download_artwork:
            artwork = attrs.get("artwork")
            if artwork and artwork.get("url"):
                url = self.client.artwork_url(artwork, self.config.artwork_size, self.config.artwork_size)
                ext = "png" if "png" in url else "jpg"
                dest = base / f"{album_name} - Cover.{ext}"
                await self._download_artwork(url, dest, "cover artwork")
                result["files"].append(str(dest))
                files_downloaded += 1

        self.cb.progress(task_id, 0.3, "downloading", "Checking editorial content...")

        if self.config.download_editorial:
            try:
                ext_data = await self.client.get(
                    f"/catalog/{storefront}/albums/{album_id}",
                    {"extend": "editorialArtwork,editorialVideo"},
                )
                ext_attrs = ext_data["data"][0].get("attributes", {})
                edit_art = ext_attrs.get("editorialArtwork", {})
                for key, art_obj in edit_art.items():
                    if isinstance(art_obj, dict) and art_obj.get("url"):
                        url = self.client.artwork_url(art_obj, self.config.artwork_size, self.config.artwork_size)
                        ext = "png" if "png" in url else "jpg"
                        dest = base / f"{album_name} - Editorial {clean_filename(key)}.{ext}"
                        await self._download_artwork(url, dest, f"editorial artwork ({key})")
                        result["files"].append(str(dest))
                        files_downloaded += 1

                if self.config.download_videos:
                    edit_vid = ext_attrs.get("editorialVideo", {})
                    for key, vid_obj in edit_vid.items():
                        if isinstance(vid_obj, dict):
                            hls_url = vid_obj.get("hlsUrl") or vid_obj.get("video")
                            preview_url = vid_obj.get("previewFrame", {}).get("url")
                            if hls_url:
                                resolved = await self._resolve_m3u8(hls_url)
                                if resolved:
                                    dest = base / f"{album_name} - Editorial Video {clean_filename(key)}.ts"
                                    try:
                                        await self.client.download_cdn(resolved, str(dest))
                                        result["files"].append(str(dest))
                                        files_downloaded += 1
                                    except Exception:
                                        pass
                            if preview_url:
                                url = self.client.artwork_url(
                                    {"url": preview_url}, self.config.artwork_size, self.config.artwork_size
                                )
                                if url:
                                    dest = base / f"{album_name} - Preview {clean_filename(key)}.jpg"
                                    await self._download_artwork(url, dest, f"video preview ({key})")
                                    result["files"].append(str(dest))
                                    files_downloaded += 1
            except Exception:
                pass

        self.cb.progress(task_id, 0.7, "downloading", "Saving metadata...")

        if self.config.download_metadata:
            tracks = album.get("relationships", {}).get("tracks", {}).get("data", [])
            info_lines = [
                f"Album: {attrs.get('name', 'N/A')}",
                f"Artist: {attrs.get('artistName', 'N/A')}",
                f"Genre: {', '.join(attrs.get('genreNames', []))}",
                f"Release Date: {attrs.get('releaseDate', 'N/A')}",
                f"Record Label: {attrs.get('recordLabel', 'N/A')}",
                f"Copyright: {attrs.get('copyright', 'N/A')}",
                f"UPC: {attrs.get('upc', 'N/A')}",
                f"Track Count: {attrs.get('trackCount', 'N/A')}",
                f"Is Single: {attrs.get('isSingle', False)}",
                f"Is Complete: {attrs.get('isComplete', False)}",
                f"Content Rating: {attrs.get('contentRating', 'N/A')}",
                f"URL: {attrs.get('url', 'N/A')}",
                f"Apple Music ID: {album_id}",
                "",
            ]
            notes = attrs.get("editorialNotes", {})
            if notes.get("standard"):
                clean = re.sub(r"<[^>]+>", "", notes["standard"])
                info_lines.append(f"Editorial Notes:\n{clean}\n")
            if notes.get("short"):
                info_lines.append(f"Short Notes: {notes['short']}\n")
            if tracks:
                info_lines.append("=" * 60)
                info_lines.append("TRACK LISTING")
                info_lines.append("=" * 60)
                for t in tracks:
                    ta = t.get("attributes", {})
                    duration = convert_ms(ta.get("durationInMillis", 0))
                    disc = ta.get("discNumber", 1)
                    track_num = ta.get("trackNumber", "?")
                    info_lines.append(f"  {disc}-{track_num:>2}. {ta.get('name', '?')} [{duration}]")
                    composer = ta.get("composerName", "")
                    if composer:
                        info_lines.append(f"        Composer: {composer}")
                    isrc = ta.get("isrc", "")
                    if isrc:
                        info_lines.append(f"        ISRC: {isrc}")
            await self._save_text("\n".join(info_lines), base / "INFO.txt")
            result["files"].append(str(base / "INFO.txt"))

        self.cb.progress(task_id, 1.0, "complete", f"Done - {files_downloaded} files downloaded")
        result["total_files"] = files_downloaded
        return result

    # ── Music Video ──

    async def rip_music_video(self, video_id: str, storefront: str, task_id: str) -> dict:
        data = await self.client.get_music_video(video_id, storefront)
        video = data["data"][0]
        attrs = video["attributes"]

        artist_name = clean_filename(attrs.get("artistName", "Unknown"))
        video_name = clean_filename(attrs.get("name", "Unknown Video"))
        base = ensure_dir(
            Path(self.config.save_path) / artist_name / "Music Videos" / f"[{storefront.upper()}]"
        )

        files_downloaded = 0
        result = {"name": attrs.get("name"), "artist": attrs.get("artistName"), "type": "music-video", "files": []}

        self.cb.progress(task_id, 0.2, "downloading", f"Processing: {attrs.get('name')}")

        if self.config.download_artwork:
            artwork = attrs.get("artwork")
            if artwork and artwork.get("url"):
                url = self.client.artwork_url(artwork, self.config.artwork_size, self.config.artwork_size)
                dest = base / f"{video_name} - Preview.jpg"
                await self._download_artwork(url, dest, "video preview frame")
                result["files"].append(str(dest))
                files_downloaded += 1

        self.cb.progress(task_id, 0.5, "downloading", "Checking video previews...")

        previews = attrs.get("previews", [])
        if self.config.download_videos and previews:
            for i, preview in enumerate(previews):
                preview_url = preview.get("hlsUrl") or preview.get("url")
                if preview_url and preview_url.endswith(".m3u8"):
                    resolved = await self._resolve_m3u8(preview_url)
                    if resolved:
                        dest = base / f"{video_name} - Preview {i+1}.ts"
                        try:
                            await self.client.download_cdn(resolved, str(dest))
                            result["files"].append(str(dest))
                            files_downloaded += 1
                        except Exception:
                            pass
                elif preview_url:
                    dest = base / f"{video_name} - Preview {i+1}.mp4"
                    try:
                        await self.client.download_cdn(preview_url, str(dest))
                        result["files"].append(str(dest))
                        files_downloaded += 1
                    except Exception:
                        pass

        if self.config.download_metadata:
            info_lines = [
                f"Music Video: {attrs.get('name', 'N/A')}",
                f"Artist: {attrs.get('artistName', 'N/A')}",
                f"Genre: {', '.join(attrs.get('genreNames', []))}",
                f"Release Date: {attrs.get('releaseDate', 'N/A')}",
                f"Duration: {convert_ms(attrs.get('durationInMillis', 0))}",
                f"Has HDR: {attrs.get('hasHDR', False)}",
                f"Has 4K: {attrs.get('has4K', False)}",
                f"Content Rating: {attrs.get('contentRating', 'N/A')}",
                f"URL: {attrs.get('url', 'N/A')}",
                f"Apple Music ID: {video_id}",
            ]
            await self._save_text("\n".join(info_lines), base / f"{video_name} - INFO.txt")
            result["files"].append(str(base / f"{video_name} - INFO.txt"))

        self.cb.progress(task_id, 1.0, "complete", f"Done - {files_downloaded} files")
        result["total_files"] = files_downloaded
        return result

    # ── Playlist ──

    async def rip_playlist(self, playlist_id: str, storefront: str, task_id: str) -> dict:
        data = await self.client.get_playlist(playlist_id, storefront)
        playlist = data["data"][0]
        attrs = playlist["attributes"]

        pl_name = clean_filename(attrs.get("name", "Unknown Playlist"))
        curator = clean_filename(attrs.get("curatorName", "Apple Music"))
        base = ensure_dir(
            Path(self.config.save_path) / "Playlists" / curator / pl_name / f"[{storefront.upper()}]"
        )

        files_downloaded = 0
        result = {"name": attrs.get("name"), "curator": attrs.get("curatorName"), "type": "playlist", "files": []}

        self.cb.progress(task_id, 0.2, "downloading", f"Processing playlist: {pl_name}")

        if self.config.download_artwork:
            artwork = attrs.get("artwork")
            if artwork and artwork.get("url"):
                url = self.client.artwork_url(artwork, self.config.artwork_size, self.config.artwork_size)
                ext = "png" if "png" in url else "jpg"
                dest = base / f"{pl_name} - Artwork.{ext}"
                await self._download_artwork(url, dest, "playlist artwork")
                result["files"].append(str(dest))
                files_downloaded += 1

        self.cb.progress(task_id, 0.5, "downloading", "Saving track listing...")

        if self.config.download_metadata:
            tracks = playlist.get("relationships", {}).get("tracks", {}).get("data", [])
            description = attrs.get("description", {})
            info_lines = [
                f"Playlist: {attrs.get('name', 'N/A')}",
                f"Curator: {attrs.get('curatorName', 'N/A')}",
                f"Last Modified: {attrs.get('lastModifiedDate', 'N/A')}",
                f"URL: {attrs.get('url', 'N/A')}",
                f"Apple Music ID: {playlist_id}",
                "",
            ]
            if description.get("standard"):
                clean = re.sub(r"<[^>]+>", "", description["standard"])
                info_lines.append(f"Description:\n{clean}\n")
            if tracks:
                info_lines.append("=" * 60)
                info_lines.append(f"TRACKS ({len(tracks)})")
                info_lines.append("=" * 60)
                for i, t in enumerate(tracks, 1):
                    ta = t.get("attributes", {})
                    duration = convert_ms(ta.get("durationInMillis", 0))
                    info_lines.append(
                        f"  {i:>3}. {ta.get('artistName', '?')} - {ta.get('name', '?')} [{duration}]"
                    )
            await self._save_text("\n".join(info_lines), base / "INFO.txt")
            result["files"].append(str(base / "INFO.txt"))

        self.cb.progress(task_id, 1.0, "complete", f"Done - {files_downloaded} files")
        result["total_files"] = files_downloaded
        return result

    # ── Station ──

    async def rip_station(self, station_id: str, storefront: str, task_id: str) -> dict:
        data = await self.client.get_station(station_id, storefront)
        station = data["data"][0]
        attrs = station["attributes"]

        station_name = clean_filename(attrs.get("name", "Unknown Station"))
        base = ensure_dir(
            Path(self.config.save_path) / "Stations" / station_name / f"[{storefront.upper()}]"
        )

        files_downloaded = 0
        result = {"name": attrs.get("name"), "type": "station", "files": []}

        if self.config.download_artwork:
            artwork = attrs.get("artwork")
            if artwork and artwork.get("url"):
                url = self.client.artwork_url(artwork, self.config.artwork_size, self.config.artwork_size)
                dest = base / f"{station_name} - Artwork.jpg"
                await self._download_artwork(url, dest, "station artwork")
                result["files"].append(str(dest))
                files_downloaded += 1

        if self.config.download_metadata:
            info_lines = [
                f"Station: {attrs.get('name', 'N/A')}",
                f"URL: {attrs.get('url', 'N/A')}",
                f"Apple Music ID: {station_id}",
            ]
            notes = attrs.get("editorialNotes", {})
            if notes.get("standard"):
                clean = re.sub(r"<[^>]+>", "", notes["standard"])
                info_lines.append(f"\nDescription:\n{clean}")
            await self._save_text("\n".join(info_lines), base / f"{station_name} - INFO.txt")
            result["files"].append(str(base / f"{station_name} - INFO.txt"))

        self.cb.progress(task_id, 1.0, "complete", f"Done - {files_downloaded} files")
        result["total_files"] = files_downloaded
        return result

    # ── Song ──

    async def rip_song(self, song_id: str, storefront: str, task_id: str) -> dict:
        data = await self.client.get_song(song_id, storefront)
        song = data["data"][0]
        attrs = song["attributes"]

        artist_name = clean_filename(attrs.get("artistName", "Unknown"))
        song_name = clean_filename(attrs.get("name", "Unknown Song"))
        album_name = clean_filename(attrs.get("albumName", "Single"))
        base = ensure_dir(
            Path(self.config.save_path) / artist_name / album_name / f"[{storefront.upper()}]"
        )

        files_downloaded = 0
        result = {"name": attrs.get("name"), "artist": attrs.get("artistName"), "type": "song", "files": []}

        if self.config.download_artwork:
            artwork = attrs.get("artwork")
            if artwork and artwork.get("url"):
                url = self.client.artwork_url(artwork, self.config.artwork_size, self.config.artwork_size)
                dest = base / f"{song_name} - Artwork.jpg"
                await self._download_artwork(url, dest, "song artwork")
                result["files"].append(str(dest))
                files_downloaded += 1

        if self.config.download_metadata:
            info_lines = [
                f"Song: {attrs.get('name', 'N/A')}",
                f"Artist: {attrs.get('artistName', 'N/A')}",
                f"Album: {attrs.get('albumName', 'N/A')}",
                f"Genre: {', '.join(attrs.get('genreNames', []))}",
                f"Duration: {convert_ms(attrs.get('durationInMillis', 0))}",
                f"Release Date: {attrs.get('releaseDate', 'N/A')}",
                f"Disc Number: {attrs.get('discNumber', 'N/A')}",
                f"Track Number: {attrs.get('trackNumber', 'N/A')}",
                f"ISRC: {attrs.get('isrc', 'N/A')}",
                f"Composer: {attrs.get('composerName', 'N/A')}",
                f"Content Rating: {attrs.get('contentRating', 'N/A')}",
                f"URL: {attrs.get('url', 'N/A')}",
                f"Apple Music ID: {song_id}",
            ]
            await self._save_text("\n".join(info_lines), base / f"{song_name} - INFO.txt")
            result["files"].append(str(base / f"{song_name} - INFO.txt"))

        self.cb.progress(task_id, 1.0, "complete", f"Done - {files_downloaded} files")
        result["total_files"] = files_downloaded
        return result

    # ── Batch: Full artist rip ──

    async def rip_artist_full(self, artist_id: str, storefront: str, task_id: str) -> dict:
        result = await self.rip_artist(artist_id, storefront, task_id)
        all_files = list(result.get("files", []))

        self.cb.progress(task_id, 0.2, "downloading", "Fetching artist albums...")
        try:
            albums_data = await self.client.collect_all(
                f"/catalog/{storefront}/artists/{artist_id}/albums", {"limit": "100"},
            )
            total_items = len(albums_data)
            for i, album in enumerate(albums_data):
                sub_task = f"{task_id}_album_{album['id']}"
                progress = 0.2 + (0.6 * (i / max(total_items, 1)))
                self.cb.progress(
                    task_id, progress, "downloading",
                    f"Album {i+1}/{total_items}: {album.get('attributes', {}).get('name', '?')}",
                )
                try:
                    album_result = await self.rip_album(album["id"], storefront, sub_task)
                    all_files.extend(album_result.get("files", []))
                except Exception as e:
                    self.cb.log("warning", f"Failed album {album['id']}: {e}")
        except Exception as e:
            self.cb.log("warning", f"Failed to fetch albums: {e}")

        self.cb.progress(task_id, 0.85, "downloading", "Fetching music videos...")
        try:
            videos_data = await self.client.collect_all(
                f"/catalog/{storefront}/artists/{artist_id}/music-videos", {"limit": "100"},
            )
            for vid in videos_data:
                sub_task = f"{task_id}_mv_{vid['id']}"
                try:
                    mv_result = await self.rip_music_video(vid["id"], storefront, sub_task)
                    all_files.extend(mv_result.get("files", []))
                except Exception as e:
                    self.cb.log("warning", f"Failed video {vid['id']}: {e}")
        except Exception as e:
            self.cb.log("warning", f"Failed to fetch videos: {e}")

        result["files"] = all_files
        result["total_files"] = len(all_files)
        self.cb.progress(task_id, 1.0, "complete", f"Full artist rip done - {len(all_files)} files")
        return result

    # ── Multi-storefront ──

    async def rip_all_storefronts(self, resource_type: str, resource_id: str, task_id: str) -> dict:
        all_files = []
        storefronts = list(STOREFRONTS.keys())
        total = len(storefronts)

        for i, sf in enumerate(storefronts):
            self.cb.progress(
                task_id, i / total, "downloading",
                f"Storefront {i+1}/{total}: {STOREFRONTS[sf]} ({sf.upper()})",
            )
            sub_task = f"{task_id}_{sf}"
            try:
                result = await self._rip_by_type(resource_type, resource_id, sf, sub_task)
                all_files.extend(result.get("files", []))
            except Exception as e:
                self.cb.log("warning", f"Failed {sf.upper()}: {e}")

        self.cb.progress(task_id, 1.0, "complete", f"All storefronts done - {len(all_files)} files")
        return {"type": resource_type, "id": resource_id, "files": all_files, "total_files": len(all_files)}

    async def _rip_by_type(self, resource_type: str, resource_id: str, storefront: str, task_id: str) -> dict:
        rippers = {
            "artist": self.rip_artist,
            "album": self.rip_album,
            "music-video": self.rip_music_video,
            "playlist": self.rip_playlist,
            "station": self.rip_station,
            "song": self.rip_song,
        }
        ripper = rippers.get(resource_type)
        if not ripper:
            raise ValueError(f"Unknown resource type: {resource_type}")
        return await ripper(resource_id, storefront, task_id)
