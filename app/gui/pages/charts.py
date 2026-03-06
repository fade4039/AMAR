"""Charts page - browse Apple Music top charts."""

import customtkinter as ctk

from app.core.utils import convert_ms


class ChartsPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            header, text="Charts",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text="Browse top charts from Apple Music",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w", pady=(2, 0))

        # ── Controls ──
        controls = ctk.CTkFrame(self, corner_radius=12)
        controls.grid(row=1, column=0, sticky="ew", padx=24, pady=8)

        ctrl_row = ctk.CTkFrame(controls, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(ctrl_row, text="Chart Type:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))

        self._chart_type = ctk.CTkSegmentedButton(
            ctrl_row,
            values=["Songs", "Albums", "Music Videos", "Playlists"],
            font=ctk.CTkFont(size=12),
        )
        self._chart_type.set("Songs")
        self._chart_type.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(ctrl_row, text="Limit:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))

        self._limit_var = ctk.StringVar(value="25")
        limit_menu = ctk.CTkOptionMenu(
            ctrl_row, values=["10", "25", "50", "100"],
            variable=self._limit_var,
            width=70, height=30,
            font=ctk.CTkFont(size=12),
        )
        limit_menu.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(ctrl_row, text="Storefront:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))

        self._sf_entry = ctk.CTkEntry(ctrl_row, width=50, height=30, font=ctk.CTkFont(size=12))
        self._sf_entry.insert(0, self.app.config.storefront)
        self._sf_entry.pack(side="left", padx=(0, 16))

        self._fetch_btn = ctk.CTkButton(
            ctrl_row, text="Load Charts", height=32, width=110,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            command=self._load_charts,
        )
        self._fetch_btn.pack(side="right")

        # ── Results ──
        self._results_scroll = ctk.CTkScrollableFrame(
            self, corner_radius=12,
            label_text="Chart Results",
            label_font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._results_scroll.grid(row=2, column=0, sticky="nsew", padx=24, pady=(4, 16))
        self._results_scroll.grid_columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._results_scroll,
            text="Click 'Load Charts' to browse the top charts",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        )
        self._empty_label.grid(row=0, column=0, pady=40)

    def _load_charts(self):
        if not self.app.config.token:
            return

        self._fetch_btn.configure(state="disabled", text="Loading...")
        self._clear_results()

        chart_map = {
            "Songs": "songs", "Albums": "albums",
            "Music Videos": "music-videos", "Playlists": "playlists",
        }
        chart_type = chart_map.get(self._chart_type.get(), "songs")
        limit = int(self._limit_var.get())
        sf = self._sf_entry.get().strip() or self.app.config.storefront

        async def _fetch():
            try:
                data = await self.app.client.get_charts(sf, [chart_type], limit)
                self.after(0, self._display_charts, data, chart_type)
            except Exception as e:
                self.after(0, self._chart_error, str(e))

        self.app.run_async(_fetch())

    def _chart_error(self, error: str):
        self._fetch_btn.configure(state="normal", text="Load Charts")
        self._empty_label.configure(text=f"Error: {error}")
        self._empty_label.grid()

    def _clear_results(self):
        for widget in self._results_scroll.winfo_children():
            if widget != self._empty_label:
                widget.destroy()
        self._empty_label.grid_remove()

    def _display_charts(self, data: dict, chart_type: str):
        self._fetch_btn.configure(state="normal", text="Load Charts")
        self._clear_results()

        results = data.get("results", {})
        chart_data = results.get(chart_type, [])

        if not chart_data:
            self._empty_label.configure(text="No chart data available")
            self._empty_label.grid()
            return

        chart = chart_data[0] if chart_data else {}
        chart_name = chart.get("name", "Top Charts")
        items = chart.get("data", [])

        # Chart title
        title_label = ctk.CTkLabel(
            self._results_scroll,
            text=f"  {chart_name}",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        title_label.grid(row=0, column=0, sticky="w", padx=4, pady=(8, 8))

        for idx, item in enumerate(items):
            attrs = item.get("attributes", {})
            item_id = item.get("id", "")
            name = attrs.get("name", "Unknown")

            row_frame = ctk.CTkFrame(
                self._results_scroll, corner_radius=8,
                fg_color=("gray92", "gray17"),
            )
            row_frame.grid(row=idx + 1, column=0, sticky="ew", padx=4, pady=2)
            row_frame.grid_columnconfigure(2, weight=1)

            # Rank number
            rank_label = ctk.CTkLabel(
                row_frame, text=f"#{idx + 1}",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=("gray40", "gray60"),
                width=45,
            )
            rank_label.grid(row=0, column=0, rowspan=2, padx=(10, 4), pady=8)

            # Artwork placeholder
            art_frame = ctk.CTkFrame(
                row_frame, width=50, height=50,
                corner_radius=6,
                fg_color=("gray85", "gray25"),
            )
            art_frame.grid(row=0, column=1, rowspan=2, padx=(4, 10), pady=8)
            art_frame.grid_propagate(False)

            # Name
            name_lbl = ctk.CTkLabel(
                row_frame, text=name,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            )
            name_lbl.grid(row=0, column=2, sticky="w", pady=(8, 0))

            # Subtitle
            subtitle_parts = []
            artist = attrs.get("artistName", "")
            if artist:
                subtitle_parts.append(artist)
            if chart_type == "songs":
                album = attrs.get("albumName", "")
                if album:
                    subtitle_parts.append(album)
                duration = attrs.get("durationInMillis", 0)
                if duration:
                    subtitle_parts.append(convert_ms(duration))
            elif chart_type == "albums":
                genres = attrs.get("genreNames", [])
                if genres:
                    subtitle_parts.append(genres[0])
                release = attrs.get("releaseDate", "")
                if release:
                    subtitle_parts.append(release[:4])

            if subtitle_parts:
                sub_lbl = ctk.CTkLabel(
                    row_frame, text="  \u2022  ".join(subtitle_parts),
                    font=ctk.CTkFont(size=11),
                    text_color=("gray50", "gray60"),
                    anchor="w",
                )
                sub_lbl.grid(row=1, column=2, sticky="w", pady=(0, 8))

            # Download button
            dl_btn = ctk.CTkButton(
                row_frame, text="Download", height=28, width=80,
                font=ctk.CTkFont(size=11, weight="bold"),
                corner_radius=6,
                command=lambda ct=chart_type.rstrip("s") if chart_type != "music-videos" else "music-video",
                               rid=item_id: self._download_chart_item(ct, rid),
            )
            dl_btn.grid(row=0, column=3, rowspan=2, padx=(8, 10), pady=8)

    def _download_chart_item(self, resource_type: str, resource_id: str):
        sf = self._sf_entry.get().strip() or self.app.config.storefront
        url_map = {
            "song": f"https://music.apple.com/{sf}/song/x/{resource_id}",
            "album": f"https://music.apple.com/{sf}/album/x/{resource_id}",
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
