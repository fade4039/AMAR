"""Settings page - configuration, token management, and preferences."""

import customtkinter as ctk
from tkinter import filedialog

from app.config import AMARConfig
from app.core.token import extract_token_selenium, validate_token


class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            header, text="Settings",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text="Configure AMAR preferences, token, and download options",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w", pady=(2, 0))

        # ── Scrollable settings area ──
        self._scroll = ctk.CTkScrollableFrame(self, corner_radius=12)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=24, pady=(4, 16))
        self._scroll.grid_columnconfigure(0, weight=1)

        config = self.app.config
        row = 0

        # ════ Token Management ════
        row = self._section_header("Token Management", row)

        token_frame = ctk.CTkFrame(self._scroll, corner_radius=10)
        token_frame.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        token_frame.grid_columnconfigure(0, weight=1)
        row += 1

        token_inner = ctk.CTkFrame(token_frame, fg_color="transparent")
        token_inner.pack(fill="x", padx=16, pady=12)
        token_inner.grid_columnconfigure(0, weight=1)

        self._token_entry = ctk.CTkEntry(
            token_inner,
            placeholder_text="Paste your Apple Music JWT token here...",
            height=38,
            font=ctk.CTkFont(size=12, family="Courier"),
            corner_radius=8,
            show="*",
        )
        self._token_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        if config.token:
            self._token_entry.insert(0, config.token)

        btn_row = ctk.CTkFrame(token_inner, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="w", pady=(8, 0))

        ctk.CTkButton(
            btn_row, text="Save Token", height=32, width=100,
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=6,
            command=self._save_token,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Auto-Extract (Selenium)", height=32, width=170,
            font=ctk.CTkFont(size=12),
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray35"),
            text_color=("gray20", "gray80"),
            corner_radius=6,
            command=self._auto_extract_token,
        ).pack(side="left", padx=(0, 8))

        self._token_toggle_btn = ctk.CTkButton(
            btn_row, text="Show", height=32, width=60,
            font=ctk.CTkFont(size=12),
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray35"),
            text_color=("gray20", "gray80"),
            corner_radius=6,
            command=self._toggle_token_visibility,
        )
        self._token_toggle_btn.pack(side="left")

        self._token_status = ctk.CTkLabel(
            btn_row, text="",
            font=ctk.CTkFont(size=12),
        )
        self._token_status.pack(side="left", padx=(12, 0))

        # ════ Appearance ════
        row = self._section_header("Appearance", row)

        row = self._setting_toggle(
            "Dark Mode", "Switch between dark and light themes",
            config.theme == "dark", self._toggle_theme, row,
        )

        # ════ Download Options ════
        row = self._section_header("Download Options", row)

        # Save path
        path_frame = ctk.CTkFrame(self._scroll, corner_radius=10, fg_color=("gray92", "gray17"))
        path_frame.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        path_frame.grid_columnconfigure(1, weight=1)
        row += 1

        ctk.CTkLabel(
            path_frame, text="Save Location",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=(12, 2), sticky="w")

        path_row = ctk.CTkFrame(path_frame, fg_color="transparent")
        path_row.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        path_row.grid_columnconfigure(0, weight=1)

        self._path_entry = ctk.CTkEntry(
            path_row, height=32,
            font=ctk.CTkFont(size=12),
            corner_radius=6,
        )
        self._path_entry.insert(0, config.save_path)
        self._path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            path_row, text="Browse", height=32, width=70,
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            command=self._browse_path,
        ).grid(row=0, column=1)

        # Toggles
        row = self._setting_toggle("Download Artwork", "Download cover art and profile images", config.download_artwork, None, row)
        row = self._setting_toggle("Download Editorial", "Download editorial artwork", config.download_editorial, None, row)
        row = self._setting_toggle("Download Videos", "Download editorial video previews", config.download_videos, None, row)
        row = self._setting_toggle("Download Metadata", "Save INFO.txt with metadata", config.download_metadata, None, row)
        row = self._setting_toggle("Auto-Organize", "Organize downloads by artist/album", config.auto_organize, None, row)

        # Artwork size
        row = self._setting_slider(
            "Artwork Size", f"Maximum artwork dimension ({config.artwork_size}px)",
            500, 4000, config.artwork_size, row,
        )

        # ════ Performance ════
        row = self._section_header("Performance", row)

        row = self._setting_slider(
            "Max Concurrency", f"Simultaneous connections ({config.max_concurrency})",
            1, 20, config.max_concurrency, row,
        )

        row = self._setting_slider(
            "Rate Limit", f"Requests per second ({config.rate_limit})",
            1, 20, config.rate_limit, row,
        )

        row = self._setting_slider(
            "Max Retries", f"Retry failed requests ({config.retry_max} times)",
            0, 10, config.retry_max, row,
        )

        row = self._setting_slider(
            "Cache TTL", f"API response cache ({config.cache_ttl}s)",
            0, 3600, config.cache_ttl, row,
        )

        # ════ Actions ════
        row = self._section_header("Actions", row)

        actions_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        actions_frame.grid(row=row, column=0, sticky="ew", padx=4, pady=(4, 20))
        row += 1

        ctk.CTkButton(
            actions_frame, text="Save All Settings", height=40, width=160,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            command=self._save_settings,
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            actions_frame, text="Reset to Defaults", height=40, width=160,
            font=ctk.CTkFont(size=14),
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray35"),
            text_color=("gray20", "gray80"),
            corner_radius=8,
            command=self._reset_defaults,
        ).pack(side="left")

    def _section_header(self, title: str, row: int) -> int:
        header = ctk.CTkLabel(
            self._scroll, text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.grid(row=row, column=0, sticky="w", padx=8, pady=(20, 8))
        return row + 1

    def _setting_toggle(self, title: str, desc: str, initial: bool, callback, row: int) -> int:
        frame = ctk.CTkFrame(self._scroll, corner_radius=8, fg_color=("gray92", "gray17"))
        frame.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
        frame.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.grid(row=0, column=0, sticky="w", padx=16, pady=10)

        ctk.CTkLabel(info, text=title, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(
            info, text=desc,
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w")

        switch = ctk.CTkSwitch(
            frame, text="",
            onvalue=True, offvalue=False,
            width=44,
            command=callback,
        )
        if initial:
            switch.select()
        switch.grid(row=0, column=1, padx=(0, 16), pady=10)

        # Store reference for saving
        attr_name = title.lower().replace(" ", "_").replace("-", "_")
        setattr(self, f"_toggle_{attr_name}", switch)

        return row + 1

    def _setting_slider(self, title: str, desc: str, min_val, max_val, initial, row: int) -> int:
        frame = ctk.CTkFrame(self._scroll, corner_radius=8, fg_color=("gray92", "gray17"))
        frame.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
        frame.grid_columnconfigure(1, weight=1)

        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.grid(row=0, column=0, sticky="w", padx=16, pady=10)

        ctk.CTkLabel(info, text=title, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")

        desc_label = ctk.CTkLabel(
            info, text=desc,
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        )
        desc_label.pack(anchor="w")

        slider_frame = ctk.CTkFrame(frame, fg_color="transparent")
        slider_frame.grid(row=0, column=1, sticky="ew", padx=(8, 16), pady=10)
        slider_frame.grid_columnconfigure(0, weight=1)

        value_label = ctk.CTkLabel(
            slider_frame, text=str(int(initial) if isinstance(initial, (int, float)) else initial),
            font=ctk.CTkFont(size=12, weight="bold"),
            width=50,
        )
        value_label.grid(row=0, column=1, padx=(8, 0))

        def on_slide(val):
            int_val = int(float(val))
            value_label.configure(text=str(int_val))

        slider = ctk.CTkSlider(
            slider_frame,
            from_=min_val, to=max_val,
            number_of_steps=max(1, max_val - min_val) if isinstance(min_val, int) else 100,
            command=on_slide,
        )
        slider.set(float(initial))
        slider.grid(row=0, column=0, sticky="ew")

        attr_name = title.lower().replace(" ", "_").replace("-", "_")
        setattr(self, f"_slider_{attr_name}", slider)
        setattr(self, f"_slider_{attr_name}_label", value_label)

        return row + 1

    def _save_token(self):
        token = self._token_entry.get().strip()
        if not token:
            self._token_status.configure(text="No token entered", text_color=("red", "#ef4444"))
            return
        if not validate_token(token):
            self._token_status.configure(text="Invalid token format", text_color=("red", "#ef4444"))
            return
        self.app.config.token = token
        self.app.reload_client()
        self.app.update_token_display()
        self._token_status.configure(text="Token saved!", text_color=("green", "#22c55e"))

    def _auto_extract_token(self):
        self._token_status.configure(text="Extracting...", text_color=("gray50", "gray60"))

        async def _extract():
            try:
                token = await extract_token_selenium()
                if token and validate_token(token):
                    self.app.config.token = token
                    self.app.reload_client()
                    self.after(0, self._on_token_extracted, token)
                else:
                    self.after(0, self._token_status.configure,
                              {"text": "Extraction failed", "text_color": ("red", "#ef4444")})
            except Exception as e:
                self.after(0, self._token_status.configure,
                          {"text": f"Error: {e}", "text_color": ("red", "#ef4444")})

        self.app.run_async(_extract())

    def _on_token_extracted(self, token: str):
        self._token_entry.delete(0, "end")
        self._token_entry.insert(0, token)
        self._token_status.configure(text="Token extracted!", text_color=("green", "#22c55e"))
        self.app.update_token_display()

    def _toggle_token_visibility(self):
        current = self._token_entry.cget("show")
        if current == "*":
            self._token_entry.configure(show="")
            self._token_toggle_btn.configure(text="Hide")
        else:
            self._token_entry.configure(show="*")
            self._token_toggle_btn.configure(text="Show")

    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        new_theme = "light" if current.lower() == "dark" else "dark"
        ctk.set_appearance_mode(new_theme)
        self.app.config.theme = new_theme
        self.app.config.save()

    def _browse_path(self):
        path = filedialog.askdirectory(title="Select Download Location")
        if path:
            self._path_entry.delete(0, "end")
            self._path_entry.insert(0, path)

    def _save_settings(self):
        config = self.app.config

        # Save path
        config.save_path = self._path_entry.get().strip()

        # Toggles
        toggle_map = {
            "download_artwork": "_toggle_download_artwork",
            "download_editorial": "_toggle_download_editorial",
            "download_videos": "_toggle_download_videos",
            "download_metadata": "_toggle_download_metadata",
            "auto_organize": "_toggle_auto_organize",
        }
        for attr, widget_name in toggle_map.items():
            widget = getattr(self, widget_name, None)
            if widget:
                setattr(config, attr, bool(widget.get()))

        # Sliders
        slider_map = {
            "artwork_size": "_slider_artwork_size",
            "max_concurrency": "_slider_max_concurrency",
            "rate_limit": "_slider_rate_limit",
            "retry_max": "_slider_max_retries",
            "cache_ttl": "_slider_cache_ttl",
        }
        for attr, widget_name in slider_map.items():
            widget = getattr(self, widget_name, None)
            if widget:
                val = widget.get()
                setattr(config, attr, int(val) if attr != "rate_limit" else float(val))

        config.save()
        self.app.reload_client()

        # Show confirmation
        self._show_save_confirmation()

    def _show_save_confirmation(self):
        # Flash a temporary label
        confirm = ctk.CTkLabel(
            self,
            text="  Settings saved successfully  ",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("green", "#16a34a"),
            text_color="white",
            corner_radius=8,
        )
        confirm.place(relx=0.5, rely=0.95, anchor="center")
        self.after(2000, confirm.destroy)

    def _reset_defaults(self):
        new_config = AMARConfig()
        # Preserve token
        token = self.app.config.token
        new_config.save()
        if token:
            new_config.token = token
        self.app.config = new_config
        self.app.reload_client()

        # Rebuild the UI to reflect defaults
        for w in self._scroll.winfo_children():
            w.destroy()
        self._build_ui()
