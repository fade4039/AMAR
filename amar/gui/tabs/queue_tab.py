"""Queue tab - manage and process download queue."""

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
    """Queue management tab with treeview, controls, and async processing."""

    def __init__(self, parent: ttk.Notebook, app: "AMARApp"):  # noqa: F821
        super().__init__(parent, padding=15)
        self._app = app
        self._processing = False
        self._cancelled = False
        self._current_task: Optional[asyncio.Future] = None

        self._build_ui()
        self._apply_tree_tag_colors()

        # Register as observer to refresh treeview on queue changes
        self._app.queue_manager.on_change(self._refresh_tree)

    def _build_ui(self):
        # --- Header ---
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        self._title_var = tk.StringVar(value="Queue (0 items)")
        ttk.Label(
            header_frame, textvariable=self._title_var,
            style="Heading.TLabel",
        ).pack(side=tk.LEFT)

        # --- Queue Treeview ---
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = [
            ("status", "Status", 90),
            ("name", "Name", 320),
            ("type", "Type", 100),
            ("progress", "Progress", 80),
        ]

        col_ids = [c[0] for c in columns]
        self._tree = ttk.Treeview(
            tree_frame,
            columns=col_ids,
            show="headings",
            selectmode="extended",
        )

        for col_id, heading, width in columns:
            self._tree.heading(col_id, text=heading, anchor=tk.W)
            self._tree.column(col_id, width=width, minwidth=40, anchor=tk.W)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Options Row ---
        opts_frame = ttk.Frame(self)
        opts_frame.pack(fill=tk.X, pady=(0, 10))

        self._info_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts_frame, text="Info only (no media files)", variable=self._info_only
        ).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(opts_frame, text="Storefronts:").pack(side=tk.LEFT, padx=(0, 5))
        self._sf_mode = tk.StringVar(value="current")
        ttk.Radiobutton(
            opts_frame, text="Current only", variable=self._sf_mode, value="current"
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            opts_frame, text="All (~130)", variable=self._sf_mode, value="all"
        ).pack(side=tk.LEFT)

        # --- Buttons ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self._process_btn = ttk.Button(
            btn_frame, text="Process Queue", command=self._start_processing
        )
        self._process_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._cancel_btn = ttk.Button(
            btn_frame, text="Cancel", command=self._cancel_processing,
            style="Danger.TButton", state=tk.DISABLED,
        )
        self._cancel_btn.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Button(
            btn_frame, text="Remove Selected", command=self._remove_selected,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            btn_frame, text="Clear Completed", command=self._clear_completed,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT)

        # --- Progress ---
        prog_frame = ttk.LabelFrame(self, text="Progress", padding=10)
        prog_frame.pack(fill=tk.X)

        self._overall_progress = LabeledProgress(prog_frame, "Overall Queue Progress")
        self._overall_progress.pack(fill=tk.X, pady=(0, 5))

        self._current_progress = LabeledProgress(prog_frame, "Current Item")
        self._current_progress.pack(fill=tk.X, pady=(0, 5))

        self._file_progress = LabeledProgress(prog_frame, "File Download")
        self._file_progress.pack(fill=tk.X)

    def _apply_tree_tag_colors(self) -> None:
        """Apply theme-aware colors to treeview status tags."""
        theme = self._app.theme
        self._tree.tag_configure("complete", foreground=theme.success)
        self._tree.tag_configure("error", foreground=theme.error)
        self._tree.tag_configure("downloading", foreground=theme.accent)
        self._tree.tag_configure("cancelled", foreground=theme.warning)

    def apply_theme(self, theme) -> None:
        """Re-apply theme colors (called on theme toggle)."""
        self._apply_tree_tag_colors()

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

    def _refresh_tree(self) -> None:
        """Rebuild the treeview from the queue manager's items."""
        # Remember selection
        selected_ids = set()
        for item_id in self._tree.selection():
            values = self._tree.item(item_id, "values")
            if values:
                selected_ids.add(values[1])  # name column as identifier

        # Clear and rebuild
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
        """Remove selected items from the queue."""
        selection = self._tree.selection()
        if not selection:
            self._app.log("No items selected to remove", "WARNING")
            return

        for item_id in selection:
            self._app.queue_manager.remove(item_id)

        self._app.log(f"Removed {len(selection)} items from queue", "INFO")

    def _clear_completed(self) -> None:
        """Remove completed, errored, and cancelled items."""
        removed = self._app.queue_manager.clear_completed()
        if removed:
            self._app.log(f"Cleared {removed} completed items from queue", "INFO")
        else:
            self._app.log("No completed items to clear", "INFO")

    def _start_processing(self) -> None:
        """Start processing pending queue items."""
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
        """Cancel the current queue processing."""
        self._cancelled = True
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
        self._app.log("Queue processing cancelled", "WARNING")
        self._finish_processing()

    def _finish_processing(self) -> None:
        """Reset UI after processing completes."""
        self._processing = False
        self._app.schedule_on_gui(self._process_btn.configure, state=tk.NORMAL)
        self._app.schedule_on_gui(self._cancel_btn.configure, state=tk.DISABLED)

    async def _process_queue(self) -> None:
        """Process all pending items in the queue sequentially."""
        log = self._app.make_log_callback()
        client = self._app.client
        config = self._app.config
        qm = self._app.queue_manager

        pending = qm.pending_items
        total = len(pending)

        try:
            for idx, qi in enumerate(pending):
                if self._cancelled:
                    qm.update_status(qi.id, "cancelled")
                    continue

                # Update overall progress
                pct = (idx / total) * 100
                self._app.schedule_on_gui(
                    self._overall_progress.set_progress, pct,
                    f"Item {idx + 1}/{total}: {qi.name}",
                )

                # Mark as downloading
                qm.update_status(qi.id, "downloading", progress=0)
                self._app.schedule_on_gui(
                    self._current_progress.set_label, f"Downloading: {qi.name}"
                )
                self._app.schedule_on_gui(self._current_progress.reset)
                self._app.schedule_on_gui(self._file_progress.reset)

                try:
                    await self._process_single_item(qi, log)
                    qm.update_status(qi.id, "complete", progress=100)
                    log(f"Completed: {qi.name}", "SUCCESS")
                except TokenExpiredError as e:
                    qm.update_status(qi.id, "error", error=str(e))
                    log(f"Token expired — stopping queue: {e}", "ERROR")
                    # Cancel remaining items
                    for remaining in pending[idx + 1:]:
                        qm.update_status(remaining.id, "cancelled")
                    break
                except asyncio.CancelledError:
                    qm.update_status(qi.id, "cancelled")
                    raise
                except Exception as e:
                    qm.update_status(qi.id, "error", error=str(e))
                    log(f"Error processing {qi.name}: {e}", "ERROR")

            # Final progress
            self._app.schedule_on_gui(
                self._overall_progress.set_progress, 100, "Queue processing complete!"
            )
            if not self._cancelled:
                log("Queue processing finished", "SUCCESS")

        except asyncio.CancelledError:
            log("Queue processing cancelled", "WARNING")
        except Exception as e:
            log(f"Queue processing failed: {e}", "ERROR")
        finally:
            self._finish_processing()

    async def _process_single_item(self, qi, log) -> None:
        """Process a single queue item (download its assets)."""
        client = self._app.client
        config = self._app.config
        info_only = self._info_only.get()
        file_cb = self._make_file_progress_cb()

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
        else:
            storefronts = [config.storefront]

        # Try to extract storefront from URL if available
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
            self._app.schedule_on_gui(
                self._current_progress.set_progress, sf_pct,
                f"Storefront {sf_idx + 1}/{total_sf}: {sf.upper()}"
            )

            if qi.item_type == "artist":
                artist_ripper = ArtistRipper(client, config)
                self._app.schedule_on_gui(self._file_progress.reset)
                await artist_ripper.rip(qi.item_id, sf, info_only, log, progress_callback=file_cb)

                # Include music videos
                if not self._cancelled:
                    video_ids = await artist_ripper.get_music_video_ids(qi.item_id, sf)
                    if video_ids:
                        log(f"Found {len(video_ids)} music videos for {qi.name}", "INFO")
                        video_ripper = MusicVideoRipper(client, config)
                        for vid in video_ids:
                            if self._cancelled:
                                break
                            self._app.schedule_on_gui(self._file_progress.reset)
                            await video_ripper.rip(vid, sf, info_only, log, progress_callback=file_cb)

                # Include albums
                if not self._cancelled:
                    album_ids = await artist_ripper.get_album_ids(qi.item_id, sf)
                    if album_ids:
                        log(f"Found {len(album_ids)} albums for {qi.name}", "INFO")
                        album_ripper = AlbumRipper(client, config)
                        for aid in album_ids:
                            if self._cancelled:
                                break
                            self._app.schedule_on_gui(self._file_progress.reset)
                            await album_ripper.rip(aid, sf, info_only, log, progress_callback=file_cb)

            elif qi.item_type == "album":
                album_ripper = AlbumRipper(client, config)
                self._app.schedule_on_gui(self._file_progress.reset)
                await album_ripper.rip(qi.item_id, sf, info_only, log, progress_callback=file_cb)

            elif qi.item_type == "music-video":
                video_ripper = MusicVideoRipper(client, config)
                self._app.schedule_on_gui(self._file_progress.reset)
                await video_ripper.rip(qi.item_id, sf, info_only, log, progress_callback=file_cb)

        qm.update_progress(qi.id, 100)
