"""Search tab - catalog search with results display and queue integration."""

import asyncio
import tkinter as tk
from tkinter import ttk
from typing import Optional

from ...core.search import search_catalog
from ..widgets.results_view import ResultsView


class SearchTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, app: "AMARApp"):  # noqa: F821
        super().__init__(parent, padding=15)
        self._app = app
        self._search_task: Optional[asyncio.Future] = None

        self._build_ui()

    def _build_ui(self):
        # Search input row
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="Query:").pack(side=tk.LEFT, padx=(0, 5))

        self._query_var = tk.StringVar()
        self._query_entry = ttk.Entry(input_frame, textvariable=self._query_var, font=("Consolas", 10))
        self._query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self._query_entry.bind("<Return>", lambda e: self._do_search())

        ttk.Label(input_frame, text="Type:").pack(side=tk.LEFT, padx=(0, 5))
        self._type_var = tk.StringVar(value="All")
        type_combo = ttk.Combobox(
            input_frame,
            textvariable=self._type_var,
            values=["All", "Songs", "Albums", "Artists", "Music Videos"],
            state="readonly",
            width=15,
        )
        type_combo.pack(side=tk.LEFT, padx=(0, 10))

        self._search_btn = ttk.Button(input_frame, text="Search", command=self._do_search)
        self._search_btn.pack(side=tk.LEFT)

        # Status label
        self._status_var = tk.StringVar(value="Enter a search query (Ctrl+Click to select multiple)")
        ttk.Label(self, textvariable=self._status_var, style="Secondary.TLabel").pack(
            anchor=tk.W, pady=(0, 5)
        )

        # Results treeview — extended selection for multi-select
        self._results = ResultsView(
            self,
            columns=[
                ("num", "#", 40),
                ("type", "Type", 80),
                ("name", "Name", 250),
                ("artist", "Artist", 200),
                ("detail", "Detail", 200),
                ("year", "Year", 60),
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

    def _do_search(self):
        query = self._query_var.get().strip()
        if not query:
            self._status_var.set("Search query cannot be empty")
            return

        type_map = {
            "All": ["songs", "albums", "artists"],
            "Songs": ["songs"],
            "Albums": ["albums"],
            "Artists": ["artists"],
            "Music Videos": ["music-videos"],
        }
        types = type_map.get(self._type_var.get(), ["songs", "albums", "artists"])

        self._search_btn.configure(state=tk.DISABLED)
        self._status_var.set(f"Searching for '{query}'...")
        self._results.clear()

        self._search_task = self._app.run_async(self._run_search(query, types))

    async def _run_search(self, query, types):
        try:
            results = await search_catalog(
                self._app.client, self._app.config.storefront, query, types
            )
            self._app.schedule_on_gui(self._populate_results, results)
        except Exception as e:
            self._app.schedule_on_gui(self._status_var.set, f"Search failed: {e}")
            self._app.log(f"Search error: {e}", "ERROR")
        finally:
            self._app.schedule_on_gui(self._search_btn.configure, state=tk.NORMAL)

    def _populate_results(self, results):
        self._results.clear()
        if not results or "results" not in results:
            self._status_var.set("No results found")
            return

        res = results["results"]
        count = 0

        # Artists
        for item in res.get("artists", {}).get("data", [])[:10]:
            count += 1
            attrs = item.get("attributes", {})
            name = attrs.get("name", "")
            genres = ", ".join(attrs.get("genreNames", []))
            self._results.add_row(
                (count, "Artist", name, "", genres, ""),
                data={
                    "url": attrs.get("url", ""),
                    "type": "artist",
                    "id": item.get("id", ""),
                    "name": name,
                    "artist": name,
                },
            )

        # Albums
        for item in res.get("albums", {}).get("data", [])[:10]:
            count += 1
            attrs = item.get("attributes", {})
            name = attrs.get("name", "")
            artist = attrs.get("artistName", "")
            year = attrs.get("releaseDate", "")[:4]
            self._results.add_row(
                (count, "Album", name, artist, "", year),
                data={
                    "url": attrs.get("url", ""),
                    "type": "album",
                    "id": item.get("id", ""),
                    "name": name,
                    "artist": artist,
                },
            )

        # Songs
        for item in res.get("songs", {}).get("data", [])[:10]:
            count += 1
            attrs = item.get("attributes", {})
            name = attrs.get("name", "")
            artist = attrs.get("artistName", "")
            from ...utils import convert_ms
            duration_ms = attrs.get("durationInMillis")
            duration = convert_ms(duration_ms) if duration_ms else ""
            self._results.add_row(
                (
                    count,
                    "Song",
                    name,
                    artist,
                    f"{attrs.get('albumName', '')} ({duration})",
                    "",
                ),
                data={
                    "url": attrs.get("url", ""),
                    "type": "song",
                    "id": item.get("id", ""),
                    "name": name,
                    "artist": artist,
                },
            )

        # Music Videos
        for item in res.get("music-videos", {}).get("data", [])[:10]:
            count += 1
            attrs = item.get("attributes", {})
            name = attrs.get("name", "")
            artist = attrs.get("artistName", "")
            self._results.add_row(
                (count, "Video", name, artist, "", ""),
                data={
                    "url": attrs.get("url", ""),
                    "type": "music-video",
                    "id": item.get("id", ""),
                    "name": name,
                    "artist": artist,
                },
            )

        self._status_var.set(f"Found {count} results (Ctrl+Click to multi-select)")

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
            display_name = f"{name} - {artist}" if artist and artist != name else name

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
