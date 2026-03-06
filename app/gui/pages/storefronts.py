"""Storefronts page - browse and select from 130+ Apple Music storefronts."""

import customtkinter as ctk

from app.config import STOREFRONTS


class StorefrontsPage(ctk.CTkFrame):
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
            header, text="Storefronts",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text=f"Browse and select from {len(STOREFRONTS)} available Apple Music storefronts",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w", pady=(2, 0))

        # ── Current + Search ──
        controls = ctk.CTkFrame(self, corner_radius=12)
        controls.grid(row=1, column=0, sticky="ew", padx=24, pady=8)

        ctrl_row = ctk.CTkFrame(controls, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(
            ctrl_row, text="Current Storefront:",
            font=ctk.CTkFont(size=13),
        ).pack(side="left")

        self._current_label = ctk.CTkLabel(
            ctrl_row,
            text=f"  {self.app.config.storefront.upper()} - {STOREFRONTS.get(self.app.config.storefront, 'Unknown')}",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self._current_label.pack(side="left", padx=(4, 24))

        # Search
        ctk.CTkLabel(
            ctrl_row, text="Filter:",
            font=ctk.CTkFont(size=13),
        ).pack(side="left", padx=(0, 8))

        self._filter_entry = ctk.CTkEntry(
            ctrl_row, placeholder_text="Search storefronts...",
            height=32, width=200,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
        )
        self._filter_entry.pack(side="left")
        self._filter_entry.bind("<KeyRelease>", lambda e: self._filter_storefronts())

        # ── Grid ──
        self._grid_scroll = ctk.CTkScrollableFrame(self, corner_radius=12)
        self._grid_scroll.grid(row=2, column=0, sticky="nsew", padx=24, pady=(4, 16))

        # Configure grid columns
        for i in range(4):
            self._grid_scroll.grid_columnconfigure(i, weight=1)

        self._sf_buttons = {}
        self._populate_grid()

    def _populate_grid(self, filter_text: str = ""):
        # Clear existing
        for widget in self._grid_scroll.winfo_children():
            widget.destroy()
        self._sf_buttons.clear()

        sorted_sfs = sorted(STOREFRONTS.items(), key=lambda x: x[1])
        current = self.app.config.storefront

        row, col = 0, 0
        for code, name in sorted_sfs:
            if filter_text and filter_text.lower() not in name.lower() and filter_text.lower() not in code.lower():
                continue

            is_active = code == current

            btn = ctk.CTkButton(
                self._grid_scroll,
                text=f"{code.upper()}  {name}",
                height=38,
                font=ctk.CTkFont(size=12, weight="bold" if is_active else "normal"),
                fg_color=("gray75", "gray30") if is_active else ("gray90", "gray17"),
                hover_color=("gray70", "gray35"),
                text_color=("gray10", "gray95") if is_active else ("gray30", "gray75"),
                corner_radius=8,
                anchor="w",
                command=lambda c=code: self._select_storefront(c),
            )
            btn.grid(row=row, column=col, sticky="ew", padx=3, pady=3)

            self._sf_buttons[code] = btn

            col += 1
            if col >= 4:
                col = 0
                row += 1

    def _filter_storefronts(self):
        text = self._filter_entry.get().strip()
        self._populate_grid(text)

    def _select_storefront(self, code: str):
        self.app.config.storefront = code
        self.app.config.save()
        self.app.reload_client()

        self._current_label.configure(
            text=f"  {code.upper()} - {STOREFRONTS.get(code, 'Unknown')}"
        )

        # Re-populate to update active state
        filter_text = self._filter_entry.get().strip()
        self._populate_grid(filter_text)

    def on_show(self):
        self._current_label.configure(
            text=f"  {self.app.config.storefront.upper()} - {STOREFRONTS.get(self.app.config.storefront, 'Unknown')}"
        )
