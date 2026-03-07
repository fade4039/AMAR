"""Storefront page - Apple HIG card layout."""

import asyncio
import tkinter as tk
from tkinter import ttk
from typing import Optional

from ...config import COUNTRY_CODES


class StorefrontTab(ttk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, padding=20, **kwargs)
        self._app = app
        self._task: Optional[asyncio.Future] = None
        self._build_ui()
        self._apply_listbox_theme(app.theme)

    def _build_ui(self):
        # Page title
        ttk.Label(self, text="Storefront", style="Title1.TLabel").pack(anchor=tk.W, pady=(0, 16))

        # --- Current Storefront Card ---
        current_card = ttk.LabelFrame(self, text="Current Storefront", padding=12)
        current_card.pack(fill=tk.X, pady=(0, 12))

        self._current_var = tk.StringVar(
            value=f"{self._app.config.storefront.upper()} - {COUNTRY_CODES.get(self._app.config.storefront, 'Unknown')}"
        )
        ttk.Label(current_card, textvariable=self._current_var, font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)

        # --- Select Storefront Card ---
        select_card = ttk.LabelFrame(self, text="Select Storefront", padding=12)
        select_card.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        filter_row = ttk.Frame(select_card)
        filter_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(filter_row, text="Filter:").pack(side=tk.LEFT, padx=(0, 8))
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", self._on_filter_change)
        ttk.Entry(filter_row, textvariable=self._filter_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        list_frame = ttk.Frame(select_card)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self._listbox = tk.Listbox(list_frame, font=("Consolas", 10), selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_frame, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scrollbar.set)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._all_entries = []
        for code in sorted(COUNTRY_CODES.keys()):
            entry = f"{code.upper()} - {COUNTRY_CODES[code]}"
            self._all_entries.append((code, entry))
            self._listbox.insert(tk.END, entry)

        # --- Action buttons ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Button(btn_frame, text="Apply", command=self._apply).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="View Details", command=self._view_details, style="Secondary.TButton").pack(side=tk.LEFT)

        # --- Details Card ---
        details_card = ttk.LabelFrame(self, text="Storefront Details", padding=12)
        details_card.pack(fill=tk.X)

        self._details_var = tk.StringVar(value="Select a storefront and click 'View Details'")
        ttk.Label(details_card, textvariable=self._details_var, wraplength=600).pack(anchor=tk.W)

    def _on_filter_change(self, *_):
        query = self._filter_var.get().strip().lower()
        self._listbox.delete(0, tk.END)
        for code, entry in self._all_entries:
            if query in entry.lower() or query in code.lower():
                self._listbox.insert(tk.END, entry)

    def _get_selected_code(self) -> Optional[str]:
        selection = self._listbox.curselection()
        if not selection:
            return None
        text = self._listbox.get(selection[0])
        return text.split(" - ")[0].strip().lower()

    def _apply(self):
        code = self._get_selected_code()
        if not code:
            self._app.log("No storefront selected", "WARNING")
            return

        self._app.config.storefront = code
        self._app.config.save()
        self._current_var.set(f"{code.upper()} - {COUNTRY_CODES.get(code, 'Unknown')}")
        self._app.update_status(storefront=f"Storefront: {code.upper()}")
        self._app.log(f"Storefront changed to {code.upper()} - {COUNTRY_CODES.get(code, code)}", "SUCCESS")

    def _view_details(self):
        code = self._get_selected_code()
        if not code:
            code = self._app.config.storefront

        self._details_var.set("Loading...")
        self._task = self._app.run_async(self._fetch_details(code))

    async def _fetch_details(self, code):
        try:
            data = await self._app.client.get(f"/v1/storefronts/{code}")
            if "data" in data and data["data"]:
                attrs = data["data"][0]["attributes"]
                name = attrs.get("name", "Unknown")
                lang = attrs.get("defaultLanguageTag", "Unknown")
                supported = ", ".join(attrs.get("supportedLanguageTags", []))
                text = f"Name: {name}\nDefault Language: {lang}\nSupported: {supported}"
            else:
                text = "No data available for this storefront"
        except Exception as e:
            text = f"Error fetching details: {e}"

        self._app.schedule_on_gui(self._details_var.set, text)

    def _apply_listbox_theme(self, theme) -> None:
        self._listbox.configure(
            bg=theme.tree_bg, fg=theme.tree_fg,
            selectbackground=theme.tree_select_bg, selectforeground=theme.tree_select_fg,
            highlightbackground=theme.border, highlightcolor=theme.border_focus,
        )

    def apply_theme(self, theme) -> None:
        self._apply_listbox_theme(theme)
