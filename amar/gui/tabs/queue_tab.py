"""Queue page - Apple HIG card layout."""

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


class QueueTab(ttk.Frame):
    """Queue management page with treeview, controls, and async processing."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, padding=20, **kwargs)
        self._app = app
        self._processing = False
        self._cancelled = False
        self._current_task: Optional[asyncio.Future] = None

        self._build_ui()
        self._apply_tree_tag_colors()
        self._app.queue_manager.on_change(self._refresh_tree)

    def _build_ui(self):
        # Page title
        self._title_var = tk.StringVar(value="Queue (0 items)")
        ttk.Label(self, textvariable=self._title_var, style="Title1.TLabel").pack(anchor=tk.W, pady=(0, 16))

        # --- Queue List Card ---
        list_card = ttk.LabelFrame(self, text="Download Queue", padding=12)
        list_card.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        columns = [
            ("status", "Status", 90),
            ("name", "Name", 320),
            ("type", "Type", 100),
            ("progress", "Progress", 80),
        ]

        col_ids = [c[0] for c in columns]
        self._tree = ttk.Treeview(list_card, columns=col_ids, show="headings", selectmode="extended")

        for col_id, heading, width in columns:
            self._tree.heading(col_id, text=heading, anchor=tk.W)
            self._tree.column(col_id, width=width, minwidth=40, anchor=tk.W)

        scrollbar = ttk.Scrollbar(list_card, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Options Card ---
        opts_card = ttk.LabelFrame(self, text="Options", padding=12)
        opts_card.pack(fill=tk.X, pady=(0, 12))

        opts_row = ttk.Frame(opts_card)
        opts_row.pack(fill=tk.X)

        self._info_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts_row, text="Info only (no media files)", variable=self._info_only).pack(side=tk.LEFT, padx=(0, 20))

        self._sf_mode = tk.StringVar(value="current")
        ttk.Radiobutton(opts_row, text="Current storefront only", variable=self._sf_mode, value="current").pack(side=tk.LEFT, padx=(0, 16))
        ttk.Radiobutton(opts_row, text="All storefronts (~130)", variable=self._sf_mode, value="all").pack(side=tk.LEFT)

        # --- Action buttons ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 12))

        self._process_btn = ttk.Button(btn_frame, text="Process Queue", command=self._start_processing)
        self._process_btn.pack(side=tk.LEFT, padx=(0, 8))

        self._cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self._cancel_processing, style="Danger.TButton", state=tk.DISABLED)
        self._cancel_btn.pack(side=tk.LEFT, padx=(0, 16))

        ttk.Button(btn_frame, text="Remove Selected", command=self._remove_selected, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Clear Completed", command=self._clear_completed, style="Secondary.TButton").pack(side=tk.LEFT)

        # --- Progress Card ---
        prog_card = ttk.LabelFrame(self, text="Progress", padding=12)
        prog_card.pack(fill=tk.X)

        self._overall_progress = LabeledProgress(prog_card, "Overall Queue Progress")
        self._overall_progress.pack(fill=tk.X, pady=(0, 8))

        self._current_progress = LabeledProgress(prog_card, "Current Item")
        self._current_progress.pack(fill=tk.X, pady=(0, 8))

        self._file_progress = LabeledProgress(prog_card, "File Download")
        self._file_progress.pack(fill=tk.X)

    def _apply_tree_tag_colors(self) -> None:
        theme = self._app.theme
        self._tree.tag_configure("complete", foreground=theme.success)
        self._tree.tag_configure("error", foreground=theme.error)
        self._tree.tag_configure("downloading", foreground=theme.accent)
        self._tree.tag_configure("cancelled", foreground=theme.warning)

    def apply_theme(self, theme) -> None:
        self._apply_tree_tag_colors()

    def _make_file_progress_cb(self):
        def _cb(downloaded: int, total: int):
            if total > 0:
                pct = (downloaded / total) * 100
                label = f"{downloaded / 1024:.0f} KB / {total / 1024:.0f} KB"
                self._app.schedule_on_gui(self._file_progress.set_progress, pct, label)
        return _cb

    def _refresh_tree(self) -> None:
        selected_ids = set()
        for item_id in self._tree.selection():
            values = self._tree.item(item_id, "values")
            if values:
                selected_ids.add(values[1])

        for item in self._tree.get_children():
            self._tree.delete(item)

        qm = self._app.queue_manager
        for qi in qm.items:
            pct_str = f"{int(qi.progress)}%" if qi.status == "downloading" else qi.status_icon
            tag = qi.status if qi.status in ("complete", "error", "downloading", "cancelled") else ""
            self._tree.insert(
                "", tk.END,
                values=(qi.status_icon, qi.name, qi.display_type, pct_str),
                tags=(tag,) if tag else (),
                iid=qi.id,
            )

        self._title_var.set(f"Queue ({qm.total_count} items)")

    def _remove_selected(self) -> None:
        selection = self._tree.selection()
        if not selection:
            self._app.log("No items selected to remove", "WARNING")
            return
        for item_id in selection:
            self._app.queue_manager.remove(item_id)
        self._app.log(f"Removed {len(selection)} items from queue", "INFO")

    def _clear_completed(self) -> None:
        removed = self._app.queue_manager.clear_completed()
        if removed:
            self._app.log(f"Cleared {removed} completed items from queue", "INFO")
        else:
            self._app.log("No completed items to clear", "INFO")

    def _start_processing(self) -> None:
        qm = self._app.queue_manager
        if not qm.pending_items:
            self._app.log("No pending items in queue", "WARNING")
            return
        if not self._app.config.save_path:
            self._app.log("No save location set. Configure it in Settings.", "ERROR")
            return

        self._processing = True
        self._cancelled = False
        self._process_btn.configure(state=tk.DISABLED)
        self._cancel_btn.configure(state=tk.NORMAL)
        self._overall_progress.reset()
        self._current_progress.reset()
        self._file_progress.reset()
        self._current_task = self._app.run_async(self._process_queue())

    def _cancel_processing(self) -> None:
        self._cancelled = True
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
        self._app.log("Queue processing cancelled", "WARNING")
        self._finish_processing()

    def _finish_processing(self) -> None:
        self._processing = False
        self._app.schedule_on_gui(self._process_btn.configure, state=tk.NORMAL)
        self._app.schedule_on_gui(self._cancel_btn.configure, state=tk.DISABLED)

    async def _process_queue(self) -> None:
        log = self._app.make_log_callback()
        qm = self._app.queue_manager
        pending = qm.pending_items
        total = len(pending)

        try:
            for idx, qi in enumerate(pending):
                if self._cancelled:
                    qm.update_status(qi.id, "cancelled")
                    continue

                pct = (idx / total) * 100
                self._app.schedule_on_gui(self._overall_progress.set_progress, pct, f"Item {idx + 1}/{total}: {qi.name}")

                qm.update_status(qi.id, "downloading", progress=0)
                self._app.schedule_on_gui(self._current_progress.set_label, f"Downloading: {qi.name}")
                self._app.schedule_on_gui(self._current_progress.reset)
                self._app.schedule_on_gui(self._file_progress.reset)

                try:
                    await self._process_single_item(qi, log)
                    qm.update_status(qi.id, "complete", progress=100)
                    log(f"Completed: {qi.name}", "SUCCESS")
                except TokenExpiredError as e:
                    qm.update_status(qi.id, "error", error=str(e))
                    log(f"Token expired — stopping queue: {e}", "ERROR")
                    for remaining in pending[idx + 1:]:
                        qm.update_status(remaining.id, "cancelled")
                    break
                except asyncio.CancelledError:
                    qm.update_status(qi.id, "cancelled")
                    raise
                except Exception as e:
                    qm.update_status(qi.id, "error", error=str(e))
                    log(f"Error processing {qi.name}: {e}", "ERROR")

            self._app.schedule_on_gui(self._overall_progress.set_progress, 100, "Queue processing complete!")
            if not self._cancelled:
                log("Queue processing finished", "SUCCESS")

        except asyncio.CancelledError:
            log("Queue processing cancelled", "WARNING")
        except Exception as e:
            log(f"Queue processing failed: {e}", "ERROR")
        finally:
            self._finish_processing()

    async def _process_single_item(self, qi, log) -> None:
        client = self._app.client
        config = self._app.config
        info_only = self._info_only.get()
        file_cb = self._make_file_progress_cb()

        if self._sf_mode.get() == "all":
            try:
                data = await client.get("/v1/storefronts", cache_ttl=3600)
                storefronts = [item["id"].lower() for item in data.get("data", []) if item.get("id")]
                if not storefronts:
                    storefronts = list(COUNTRY_CODES.keys())
            except Exception:
                storefronts = list(COUNTRY_CODES.keys())
        else:
            storefronts = [config.storefront]

        parsed = parse_apple_music_url(qi.url) if qi.url else None
        if parsed and parsed.storefront in storefronts:
            storefronts.remove(parsed.storefront)
            storefronts = [parsed.storefront] + storefronts

        total_sf = len(storefronts)
        qm = self._app.queue_manager

        for sf_idx, sf in enumerate(storefronts):
            if self._cancelled:
                break

            sf_pct = (sf_idx / total_sf) * 100
            qm.update_progress(qi.id, sf_pct)
            self._app.schedule_on_gui(self._current_progress.set_progress, sf_pct, f"Storefront {sf_idx + 1}/{total_sf}: {sf.upper()}")

            if qi.item_type == "artist":
                artist_ripper = ArtistRipper(client, config)
                self._app.schedule_on_gui(self._file_progress.reset)
                await artist_ripper.rip(qi.item_id, sf, info_only, log, progress_callback=file_cb)

                if not self._cancelled:
                    try:
                        video_ids = await artist_ripper.get_music_video_ids(qi.item_id, sf)
                        if video_ids:
                            log(f"Found {len(video_ids)} music videos for {qi.name}", "INFO")
                            video_ripper = MusicVideoRipper(client, config)
                            for vid in video_ids:
                                if self._cancelled:
                                    break
                                self._app.schedule_on_gui(self._file_progress.reset)
                                try:
                                    await video_ripper.rip(vid, sf, info_only, log, progress_callback=file_cb)
                                except Exception as e:
                                    log(f"Error downloading music video {vid}: {e}", "ERROR")
                    except TokenExpiredError:
                        raise
                    except Exception as e:
                        log(f"Error fetching music videos: {e}", "ERROR")

                if not self._cancelled:
                    try:
                        album_ids = await artist_ripper.get_album_ids(qi.item_id, sf)
                        if album_ids:
                            log(f"Found {len(album_ids)} albums for {qi.name}", "INFO")
                            album_ripper = AlbumRipper(client, config)
                            for aid in album_ids:
                                if self._cancelled:
                                    break
                                self._app.schedule_on_gui(self._file_progress.reset)
                                try:
                                    await album_ripper.rip(aid, sf, info_only, log, progress_callback=file_cb)
                                except Exception as e:
                                    log(f"Error downloading album {aid}: {e}", "ERROR")
                    except TokenExpiredError:
                        raise
                    except Exception as e:
                        log(f"Error fetching albums: {e}", "ERROR")

            elif qi.item_type == "album":
                album_ripper = AlbumRipper(client, config)
                self._app.schedule_on_gui(self._file_progress.reset)
                await album_ripper.rip(qi.item_id, sf, info_only, log, progress_callback=file_cb)

            elif qi.item_type == "music-video":
                video_ripper = MusicVideoRipper(client, config)
                self._app.schedule_on_gui(self._file_progress.reset)
                await video_ripper.rip(qi.item_id, sf, info_only, log, progress_callback=file_cb)

        qm.update_progress(qi.id, 100)
