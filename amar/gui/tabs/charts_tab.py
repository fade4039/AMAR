"""Charts tab - browse Apple Music charts with queue integration."""

import asyncio
import tkinter as tk
from tkinter import ttk
from typing import Optional

from ...core.charts import get_charts
from ..widgets.results_view import ResultsView


class ChartsTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, app: "AMARApp"):  # noqa: F821
        super().__init__(parent, padding=15)
        self._app = app
        self._task: Optional[asyncio.Future] = None

        self._build_ui()

    def _build_ui(self):
        # Controls row
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(ctrl_frame, text="Chart Type:").pack(side=tk.LEFT, padx=(0, 5))
        self._type_var = tk.StringVar(value="Both")
        type_combo = ttk.Combobox(
            ctrl_frame,
            textvariable=self._type_var,
            values=["Songs", "Albums", "Both", "Music Videos"],
            state="readonly",
            width=15,
        )
        type_combo.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(ctrl_frame, text="Limit:").pack(side=tk.LEFT, padx=(0, 5))
        self._limit_var = tk.StringVar(value="20")
        limit_combo = ttk.Combobox(
            ctrl_frame,
            textvariable=self._limit_var,
            values=["10", "20", "50"],
            state="readonly",
            width=5,
        )
        limit_combo.pack(side=tk.LEFT, padx=(0, 15))

        self._refresh_btn = ttk.Button(ctrl_frame, text="Refresh", command=self._do_refresh)
        self._refresh_btn.pack(side=tk.LEFT)

        # Status
        self._status_var = tk.StringVar(value="Select chart type and click Refresh (Ctrl+Click to multi-select)")
        ttk.Label(self, textvariable=self._status_var, style="Secondary.TLabel").pack(
            anchor=tk.W, pady=(0, 5)
        )

        # Results — extended selection for multi-select
        self._results = ResultsView(
            self,
            columns=[
                ("rank", "#", 40),
                ("name", "Name", 300),
                ("artist", "Artist", 250),
                ("type", "Type", 80),
            ],
            on_double_click=self._on_result_double_click,
            selectmode="extended",
        )
        self._results.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Action buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame, text="Add to Queue", command=self._add_to_queue,
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            btn_frame, text="Copy URL", command=self._copy_url,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            btn_frame, text="Download Assets", command=self._download_selected,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            btn_frame, text="Select All", command=self._results.select_all,
            style="Secondary.TButton",
        ).pack(side=tk.RIGHT)

    def _do_refresh(self):
        type_map = {
            "Songs": ["songs"],
            "Albums": ["albums"],
            "Both": ["songs", "albums"],
            "Music Videos": ["music-videos"],
        }
        chart_types = type_map.get(self._type_var.get(), ["songs", "albums"])
        limit = int(self._limit_var.get())

        self._refresh_btn.configure(state=tk.DISABLED)
        self._status_var.set("Fetching charts...")
        self._results.clear()

        self._task = self._app.run_async(self._run_refresh(chart_types, limit))

    async def _run_refresh(self, chart_types, limit):
        try:
            data = await get_charts(
                self._app.client, self._app.config.storefront, chart_types, limit
            )
            self._app.schedule_on_gui(self._populate_charts, data)
        except Exception as e:
            self._app.schedule_on_gui(self._status_var.set, f"Charts error: {e}")
            self._app.log(f"Charts error: {e}", "ERROR")
        finally:
            self._app.schedule_on_gui(self._refresh_btn.configure, state=tk.NORMAL)

    def _populate_charts(self, data):
        self._results.clear()
        if not data or "results" not in data:
            self._status_var.set("No charts data available")
            return

        results = data["results"]
        count = 0

        # Map API chart types to queue item types
        type_to_queue = {
            "songs": "song",
            "albums": "album",
            "music-videos": "music-video",
        }

        for chart_type in ["songs", "albums", "music-videos"]:
            charts = results.get(chart_type, [])
            for chart in charts:
                for i, item in enumerate(chart.get("data", []), 1):
                    count += 1
                    attrs = item.get("attributes", {})
                    name = attrs.get("name", "Unknown")
                    artist = attrs.get("artistName", "Unknown")
                    display_type = chart_type.replace("-", " ").title()

                    self._results.add_row(
                        (i, name, artist, display_type),
                        data={
                            "url": attrs.get("url", ""),
                            "type": type_to_queue.get(chart_type, chart_type),
                            "id": item.get("id", ""),
                            "name": name,
                            "artist": artist,
                        },
                    )

        self._status_var.set(f"Showing {count} chart entries (Ctrl+Click to multi-select)")

    def _on_result_double_click(self, data):
        url = data.get("url", "")
        if url:
            self._app.switch_to_download_tab(url)

    def _add_to_queue(self):
        """Add all selected items to the download queue."""
        selected = self._results.get_all_selected_data()
        if not selected:
            self._status_var.set("No items selected")
            return

        added = 0
        skipped_songs = 0
        for data in selected:
            item_type = data.get("type", "")
            if item_type == "song":
                skipped_songs += 1
                continue

            name = data.get("name", "Unknown")
            artist = data.get("artist", "")
            display_name = f"{name} - {artist}" if artist else name

            result = self._app.queue_manager.add(
                name=display_name,
                item_type=item_type,
                item_id=data.get("id", ""),
                url=data.get("url", ""),
            )
            if result:
                added += 1

        parts = []
        if added:
            parts.append(f"Added {added} items to queue")
        if skipped_songs:
            parts.append(f"skipped {skipped_songs} songs (not downloadable)")

        msg = "; ".join(parts) if parts else "No new items added (may already be in queue)"
        self._status_var.set(msg)

        if added:
            self._app.log(msg, "SUCCESS")
        if skipped_songs:
            self._app.log("Songs cannot be queued for asset download", "INFO")

    def _copy_url(self):
        data = self._results.get_selected_data()
        if data and data.get("url"):
            self._app.root.clipboard_clear()
            self._app.root.clipboard_append(data["url"])
            self._status_var.set("URL copied to clipboard")
        else:
            self._status_var.set("No item selected")

    def _download_selected(self):
        data = self._results.get_selected_data()
        if data and data.get("url"):
            self._app.switch_to_download_tab(data["url"])
        else:
            self._status_var.set("No item selected")
