"""Download tab - URL input, content detection, download controls, progress."""

import asyncio
import tkinter as tk
from tkinter import ttk
from typing import Optional

from ...api.client import TokenExpiredError
from ...config import COUNTRY_CODES
from ...core.album import AlbumRipper
from ...core.artist import ArtistRipper
from ...core.music_video import MusicVideoRipper
from ...core.radio_station import RadioStationRipper
from ...utils import parse_apple_music_url
from ..widgets.progress import LabeledProgress


class DownloadTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, app: "AMARApp"):  # noqa: F821
        super().__init__(parent, padding=15)
        self._app = app
        self._current_task: Optional[asyncio.Future] = None
        self._cancelled = False

        self._build_ui()

    def _build_ui(self):
        # --- URL Input ---
        url_frame = ttk.LabelFrame(self, text="Apple Music URL", padding=10)
        url_frame.pack(fill=tk.X, pady=(0, 5))

        input_row = ttk.Frame(url_frame)
        input_row.pack(fill=tk.X)

        self._url_var = tk.StringVar()
        self._url_entry = ttk.Entry(input_row, textvariable=self._url_var, font=("Consolas", 10))
        self._url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self._url_var.trace_add("write", self._on_url_change)

        ttk.Button(input_row, text="Paste", command=self._paste_url, style="Secondary.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(input_row, text="Clear", command=self._clear_url, style="Secondary.TButton").pack(side=tk.LEFT, padx=2)

        self._detect_var = tk.StringVar(value="Enter a URL to begin")
        ttk.Label(url_frame, textvariable=self._detect_var, style="Secondary.TLabel").pack(
            anchor=tk.W, pady=(5, 0)
        )

        # --- Options ---
        opts_frame = ttk.LabelFrame(self, text="Options", padding=10)
        opts_frame.pack(fill=tk.X, pady=5)

        row1 = ttk.Frame(opts_frame)
        row1.pack(fill=tk.X)

        self._info_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text="Info only (no media files)", variable=self._info_only).pack(
            side=tk.LEFT, padx=(0, 20)
        )

        self._include_albums = tk.BooleanVar(value=True)
        self._albums_cb = ttk.Checkbutton(row1, text="Include albums", variable=self._include_albums)
        self._albums_cb.pack(side=tk.LEFT, padx=(0, 20))

        self._include_videos = tk.BooleanVar(value=True)
        self._videos_cb = ttk.Checkbutton(row1, text="Include music videos", variable=self._include_videos)
        self._videos_cb.pack(side=tk.LEFT)

        # --- Storefront Selection ---
        sf_frame = ttk.LabelFrame(self, text="Storefronts", padding=10)
        sf_frame.pack(fill=tk.X, pady=5)

        self._sf_mode = tk.StringVar(value="current")
        ttk.Radiobutton(sf_frame, text="Current storefront only", variable=self._sf_mode, value="current").pack(
            anchor=tk.W
        )
        ttk.Radiobutton(sf_frame, text="All storefronts (~130)", variable=self._sf_mode, value="all").pack(
            anchor=tk.W
        )

        # --- Buttons ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)

        self._start_btn = ttk.Button(
            btn_frame, text="Start Download", command=self._start_download
        )
        self._start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self._cancel_btn = ttk.Button(
            btn_frame, text="Cancel", command=self._cancel_download,
            style="Danger.TButton", state=tk.DISABLED,
        )
        self._cancel_btn.pack(side=tk.LEFT)

        # --- Progress ---
        prog_frame = ttk.LabelFrame(self, text="Progress", padding=10)
        prog_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self._overall_progress = LabeledProgress(prog_frame, "Overall Progress")
        self._overall_progress.pack(fill=tk.X, pady=(0, 5))

        self._current_progress = LabeledProgress(prog_frame, "Current Item")
        self._current_progress.pack(fill=tk.X, pady=(0, 5))

        self._file_progress = LabeledProgress(prog_frame, "File Download")
        self._file_progress.pack(fill=tk.X)

    def set_url(self, url: str) -> None:
        """Set the URL entry (called from other tabs)."""
        self._url_var.set(url)

    def _paste_url(self):
        try:
            text = self._url_entry.clipboard_get()
            self._url_var.set(text.strip())
        except tk.TclError:
            pass

    def _clear_url(self):
        self._url_var.set("")

    def _on_url_change(self, *_):
        url = self._url_var.get().strip()
        parsed = parse_apple_music_url(url)
        if parsed:
            self._detect_var.set(
                f"Detected: {parsed.content_type} | ID: {parsed.item_id} | "
                f"Storefront: {parsed.storefront.upper()}"
            )
            # Show/hide artist-specific options
            is_artist = parsed.content_type == "artist"
            state = tk.NORMAL if is_artist else tk.DISABLED
            self._albums_cb.configure(state=state)
            self._videos_cb.configure(state=state)
        else:
            self._detect_var.set("Enter a valid Apple Music URL")

    def _make_file_progress_cb(self):
        """Create a progress callback for file downloads (called from async thread)."""
        def _cb(downloaded: int, total: int):
            if total > 0:
                pct = (downloaded / total) * 100
                dl_kb = downloaded / 1024
                total_kb = total / 1024
                label = f"{dl_kb:.0f} KB / {total_kb:.0f} KB"
                self._app.schedule_on_gui(
                    self._file_progress.set_progress, pct, label
                )
        return _cb

    def _start_download(self):
        url = self._url_var.get().strip()
        parsed = parse_apple_music_url(url)
        if not parsed:
            self._app.log("Invalid Apple Music URL", "ERROR")
            return

        if not self._app.config.save_path:
            self._app.log("No save location set. Configure it in Settings.", "ERROR")
            return

        self._start_btn.configure(state=tk.DISABLED)
        self._cancel_btn.configure(state=tk.NORMAL)
        self._cancelled = False
        self._overall_progress.reset()
        self._current_progress.reset()
        self._file_progress.reset()

        self._current_task = self._app.run_async(self._run_download(parsed))

    def _cancel_download(self):
        self._cancelled = True
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
        self._app.log("Download cancelled by user", "WARNING")
        self._finish_download()

    def _finish_download(self):
        self._app.schedule_on_gui(self._start_btn.configure, state=tk.NORMAL)
        self._app.schedule_on_gui(self._cancel_btn.configure, state=tk.DISABLED)

    async def _run_download(self, parsed):
        log = self._app.make_log_callback()
        client = self._app.client
        config = self._app.config
        file_cb = self._make_file_progress_cb()

        try:
            # Determine storefronts
            if self._sf_mode.get() == "all":
                try:
                    data = await client.get("/v1/storefronts", cache_ttl=3600)
                    storefronts = [
                        item["id"].lower() for item in data.get("data", []) if item.get("id")
                    ]
                    if not storefronts:
                        storefronts = list(COUNTRY_CODES.keys())
                except Exception:
                    storefronts = list(COUNTRY_CODES.keys())
                # Put the detected storefront first
                if parsed.storefront in storefronts:
                    storefronts.remove(parsed.storefront)
                storefronts = [parsed.storefront] + storefronts
            else:
                storefronts = [parsed.storefront]

            info_only = self._info_only.get()
            total = len(storefronts)

            artist_ripper = ArtistRipper(client, config)
            album_ripper = AlbumRipper(client, config)
            video_ripper = MusicVideoRipper(client, config)
            station_ripper = RadioStationRipper(client, config)

            for idx, sf in enumerate(storefronts):
                if self._cancelled:
                    break

                pct = (idx / total) * 100
                self._app.schedule_on_gui(
                    self._overall_progress.set_progress,
                    pct,
                    f"Storefront {idx + 1}/{total}: {sf.upper()} - {COUNTRY_CODES.get(sf, sf)}",
                )

                try:
                    if parsed.content_type == "artist":
                        # Phase 1: Artist page assets
                        self._app.schedule_on_gui(
                            self._current_progress.set_label, "Downloading artist assets..."
                        )
                        self._app.schedule_on_gui(self._file_progress.reset)
                        await artist_ripper.rip(parsed.item_id, sf, info_only, log, progress_callback=file_cb)

                        # Phase 2: Music videos
                        if self._include_videos.get() and not self._cancelled:
                            try:
                                self._app.schedule_on_gui(
                                    self._current_progress.set_label, "Fetching music video list..."
                                )
                                video_ids = await artist_ripper.get_music_video_ids(parsed.item_id, sf)
                                log(f"Found {len(video_ids)} music videos", "INFO")
                                for vi, vid in enumerate(video_ids):
                                    if self._cancelled:
                                        break
                                    self._app.schedule_on_gui(
                                        self._current_progress.set_progress,
                                        (vi / max(len(video_ids), 1)) * 100,
                                        f"Music video {vi + 1}/{len(video_ids)}",
                                    )
                                    self._app.schedule_on_gui(self._file_progress.reset)
                                    try:
                                        await video_ripper.rip(vid, sf, info_only, log, progress_callback=file_cb)
                                    except Exception as e:
                                        log(f"Error downloading music video {vid}: {e}", "ERROR")
                            except TokenExpiredError:
                                raise
                            except Exception as e:
                                log(f"Error fetching music videos: {e}", "ERROR")

                        # Phase 3: Albums
                        if self._include_albums.get() and not self._cancelled:
                            try:
                                self._app.schedule_on_gui(
                                    self._current_progress.set_label, "Fetching album list..."
                                )
                                album_ids = await artist_ripper.get_album_ids(parsed.item_id, sf)
                                log(f"Found {len(album_ids)} albums", "INFO")
                                for ai, aid in enumerate(album_ids):
                                    if self._cancelled:
                                        break
                                    self._app.schedule_on_gui(
                                        self._current_progress.set_progress,
                                        (ai / max(len(album_ids), 1)) * 100,
                                        f"Album {ai + 1}/{len(album_ids)}",
                                    )
                                    self._app.schedule_on_gui(self._file_progress.reset)
                                    try:
                                        await album_ripper.rip(aid, sf, info_only, log, progress_callback=file_cb)
                                    except Exception as e:
                                        log(f"Error downloading album {aid}: {e}", "ERROR")
                            except TokenExpiredError:
                                raise
                            except Exception as e:
                                log(f"Error fetching albums: {e}", "ERROR")

                    elif parsed.content_type == "album":
                        self._app.schedule_on_gui(
                            self._current_progress.set_label, "Downloading album assets..."
                        )
                        self._app.schedule_on_gui(self._file_progress.reset)
                        await album_ripper.rip(parsed.item_id, sf, info_only, log, progress_callback=file_cb)

                    elif parsed.content_type == "music-video":
                        self._app.schedule_on_gui(
                            self._current_progress.set_label, "Downloading music video assets..."
                        )
                        self._app.schedule_on_gui(self._file_progress.reset)
                        await video_ripper.rip(parsed.item_id, sf, info_only, log, progress_callback=file_cb)

                    elif parsed.content_type == "station":
                        self._app.schedule_on_gui(
                            self._current_progress.set_label, "Downloading station assets..."
                        )
                        self._app.schedule_on_gui(self._file_progress.reset)
                        await station_ripper.rip(parsed.item_id, sf, info_only, log, progress_callback=file_cb)

                except TokenExpiredError as e:
                    log(str(e), "ERROR")
                    break
                except Exception as e:
                    log(f"Error processing {sf}: {e}", "ERROR")

            self._app.schedule_on_gui(
                self._overall_progress.set_progress, 100, "Complete!"
            )
            if not self._cancelled:
                log("Download complete!", "SUCCESS")

        except asyncio.CancelledError:
            log("Download cancelled", "WARNING")
        except Exception as e:
            log(f"Download failed: {e}", "ERROR")
        finally:
            self._finish_download()
