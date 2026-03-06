"""Search page - search Apple Music catalog and browse results."""

import customtkinter as ctk

from app.api.apple_music import AppleMusicClient
from app.core.utils import parse_apple_music_url


class SearchPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._results = {}
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            header, text="Search",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text="Search the Apple Music catalog for artists, albums, songs, and more",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w", pady=(2, 0))

        # ── Search Bar ──
        search_card = ctk.CTkFrame(self, corner_radius=12)
        search_card.grid(row=1, column=0, sticky="ew", padx=24, pady=8)

        search_row = ctk.CTkFrame(search_card, fg_color="transparent")
        search_row.pack(fill="x", padx=16, pady=12)
        search_row.grid_columnconfigure(0, weight=1)

        self._search_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Search artists, albums, songs...",
            height=42,
            font=ctk.CTkFont(size=14),
            corner_radius=10,
        )
        self._search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._search_entry.bind("<Return>", lambda e: self._do_search())

        self._search_btn = ctk.CTkButton(
            search_row, text="Search", height=42, width=100,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10,
            command=self._do_search,
        )
        self._search_btn.grid(row=0, column=1)

        # Filter row
        filter_row = ctk.CTkFrame(search_card, fg_color="transparent")
        filter_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            filter_row, text="Type:",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
        ).pack(side="left", padx=(0, 6))

        self._type_var = ctk.StringVar(value="all")
        types = [("All", "all"), ("Artists", "artists"), ("Albums", "albums"),
                 ("Songs", "songs"), ("Music Videos", "music-videos"), ("Playlists", "playlists")]
        for label, value in types:
            rb = ctk.CTkRadioButton(
                filter_row, text=label, variable=self._type_var, value=value,
                font=ctk.CTkFont(size=12),
                radiobutton_height=16, radiobutton_width=16,
            )
            rb.pack(side="left", padx=(0, 12))

        # Storefront selector
        ctk.CTkLabel(
            filter_row, text="Storefront:",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
        ).pack(side="left", padx=(16, 6))

        self._sf_entry = ctk.CTkEntry(
            filter_row, width=60, height=28,
            font=ctk.CTkFont(size=12),
            corner_radius=6,
        )
        self._sf_entry.insert(0, self.app.config.storefront)
        self._sf_entry.pack(side="left")

        self._status_label = ctk.CTkLabel(
            filter_row, text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
        )
        self._status_label.pack(side="right")

        # ── Results ──
        self._results_scroll = ctk.CTkScrollableFrame(
            self, corner_radius=12,
            label_text="Results",
            label_font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._results_scroll.grid(row=2, column=0, sticky="nsew", padx=24, pady=(4, 16))
        self._results_scroll.grid_columnconfigure(0, weight=1)

        self._results_empty = ctk.CTkLabel(
            self._results_scroll,
            text="Search for something to see results here",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        )
        self._results_empty.grid(row=0, column=0, pady=40)

    def _do_search(self):
        term = self._search_entry.get().strip()
        if not term:
            return
        if not self.app.config.token:
            self._status_label.configure(text="No token configured!")
            return

        self._search_btn.configure(state="disabled", text="Searching...")
        self._status_label.configure(text="Searching...")
        self._clear_results()

        type_val = self._type_var.get()
        if type_val == "all":
            types = ["songs", "albums", "artists", "music-videos", "playlists"]
        else:
            types = [type_val]

        sf = self._sf_entry.get().strip() or self.app.config.storefront

        async def _search():
            try:
                client = self.app.client
                data = await client.search(term, sf, types, limit=25)
                self.after(0, self._display_results, data)
            except Exception as e:
                self.after(0, self._search_error, str(e))

        self.app.run_async(_search())

    def _search_error(self, error: str):
        self._search_btn.configure(state="normal", text="Search")
        self._status_label.configure(text=f"Error: {error}")

    def _clear_results(self):
        for widget in self._results_scroll.winfo_children():
            if widget != self._results_empty:
                widget.destroy()
        self._results_empty.grid_remove()

    def _display_results(self, data: dict):
        self._search_btn.configure(state="normal", text="Search")
        self._clear_results()

        results_data = data.get("results", {})
        total_count = 0

        type_order = ["artists", "albums", "songs", "music-videos", "playlists"]
        type_labels = {
            "artists": "Artists", "albums": "Albums", "songs": "Songs",
            "music-videos": "Music Videos", "playlists": "Playlists",
        }
        type_colors = {
            "artists": ("#7c5cfc", "#5a3fd6"),
            "albums": ("#fa2d48", "#d41e38"),
            "songs": ("#22c55e", "#16a34a"),
            "music-videos": ("#3b82f6", "#2563eb"),
            "playlists": ("#f59e0b", "#d97706"),
        }

        row_idx = 0
        for rtype in type_order:
            section = results_data.get(rtype, {})
            items = section.get("data", [])
            if not items:
                continue

            # Section header
            section_label = ctk.CTkLabel(
                self._results_scroll,
                text=f"  {type_labels.get(rtype, rtype)}  ({len(items)})",
                font=ctk.CTkFont(size=14, weight="bold"),
            )
            section_label.grid(row=row_idx, column=0, sticky="w", padx=4, pady=(12, 4))
            row_idx += 1

            for item in items:
                attrs = item.get("attributes", {})
                item_id = item.get("id", "")
                name = attrs.get("name", "Unknown")
                subtitle_parts = []

                if rtype == "artists":
                    genres = attrs.get("genreNames", [])
                    if genres:
                        subtitle_parts.append(", ".join(genres[:3]))
                elif rtype in ("albums", "songs", "music-videos"):
                    artist = attrs.get("artistName", "")
                    if artist:
                        subtitle_parts.append(artist)
                    if rtype == "albums":
                        release = attrs.get("releaseDate", "")
                        if release:
                            subtitle_parts.append(release[:4])
                        count = attrs.get("trackCount", 0)
                        if count:
                            subtitle_parts.append(f"{count} tracks")
                elif rtype == "playlists":
                    curator = attrs.get("curatorName", "")
                    if curator:
                        subtitle_parts.append(curator)

                subtitle = "  \u2022  ".join(subtitle_parts)

                # Result item frame
                item_frame = ctk.CTkFrame(
                    self._results_scroll, corner_radius=8,
                    fg_color=("gray92", "gray17"),
                    cursor="hand2",
                )
                item_frame.grid(row=row_idx, column=0, sticky="ew", padx=4, pady=2)
                item_frame.grid_columnconfigure(1, weight=1)

                # Type badge
                color = type_colors.get(rtype, ("#6b7280", "#4b5563"))
                badge = ctk.CTkLabel(
                    item_frame,
                    text=rtype.replace("-", " ").split()[0][:3].upper(),
                    font=ctk.CTkFont(size=9, weight="bold"),
                    fg_color=color[0], text_color="white",
                    corner_radius=4, width=36,
                )
                badge.grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=8)

                # Name
                name_lbl = ctk.CTkLabel(
                    item_frame, text=name,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    anchor="w",
                )
                name_lbl.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(8, 0))

                # Subtitle
                if subtitle:
                    sub_lbl = ctk.CTkLabel(
                        item_frame, text=subtitle,
                        font=ctk.CTkFont(size=11),
                        text_color=("gray50", "gray60"),
                        anchor="w",
                    )
                    sub_lbl.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=(0, 8))

                # Action buttons
                btn_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
                btn_frame.grid(row=0, column=2, rowspan=2, padx=(0, 10), pady=8)

                dl_btn = ctk.CTkButton(
                    btn_frame, text="Download", height=28, width=80,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    corner_radius=6,
                    command=lambda rt=rtype.rstrip("s") if rtype != "music-videos" else "music-video",
                                   rid=item_id: self._download_item(rt, rid),
                )
                dl_btn.pack(side="left", padx=(0, 4))

                copy_btn = ctk.CTkButton(
                    btn_frame, text="Copy URL", height=28, width=70,
                    font=ctk.CTkFont(size=11),
                    fg_color=("gray80", "gray25"),
                    hover_color=("gray70", "gray35"),
                    text_color=("gray20", "gray80"),
                    corner_radius=6,
                    command=lambda a=attrs: self._copy_url(a.get("url", "")),
                )
                copy_btn.pack(side="left")

                row_idx += 1
                total_count += 1

        if total_count == 0:
            self._results_empty.configure(text="No results found")
            self._results_empty.grid()

        self._status_label.configure(text=f"{total_count} results found")

    def _download_item(self, resource_type: str, resource_id: str):
        """Trigger download from search results."""
        sf = self._sf_entry.get().strip() or self.app.config.storefront
        # Build a fake URL and use the download page
        url_map = {
            "artist": f"https://music.apple.com/{sf}/artist/x/{resource_id}",
            "album": f"https://music.apple.com/{sf}/album/x/{resource_id}",
            "song": f"https://music.apple.com/{sf}/song/x/{resource_id}",
            "music-video": f"https://music.apple.com/{sf}/music-video/x/{resource_id}",
            "playlist": f"https://music.apple.com/{sf}/playlist/x/{resource_id}",
        }
        url = url_map.get(resource_type, "")
        if url:
            dl_page = self.app._pages.get("download")
            if dl_page:
                dl_page._url_entry.delete(0, "end")
                dl_page._url_entry.insert(0, url)
                self.app._show_page("download")
                dl_page._start_download()

    def _copy_url(self, url: str):
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
