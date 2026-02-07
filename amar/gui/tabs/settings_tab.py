"""Settings tab - configuration, token management, performance tuning, appearance."""

import os
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Optional

from ...api.token import extract_token_with_selenium
from ...config import COUNTRY_CODES


class SettingsTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, app: "AMARApp"):  # noqa: F821
        super().__init__(parent, padding=15)
        self._app = app

        self._build_ui()

    def _build_ui(self):
        # --- Appearance ---
        appearance_frame = ttk.LabelFrame(self, text="Appearance", padding=10)
        appearance_frame.pack(fill=tk.X, pady=(0, 10))

        appearance_row = ttk.Frame(appearance_frame)
        appearance_row.pack(fill=tk.X)

        ttk.Label(appearance_row, text="Theme:").pack(side=tk.LEFT, padx=(0, 10))

        current = self._app.config.theme
        btn_text = "Switch to Light Mode" if current == "dark" else "Switch to Dark Mode"
        self._theme_btn = ttk.Button(
            appearance_row, text=btn_text, command=self._app.toggle_theme,
            style="Secondary.TButton",
        )
        self._theme_btn.pack(side=tk.LEFT)

        # --- Save Location ---
        loc_frame = ttk.LabelFrame(self, text="Save Location", padding=10)
        loc_frame.pack(fill=tk.X, pady=(0, 10))

        loc_row = ttk.Frame(loc_frame)
        loc_row.pack(fill=tk.X)

        self._path_var = tk.StringVar(value=self._app.config.save_path or "(not set)")
        ttk.Entry(loc_row, textvariable=self._path_var, state="readonly", font=("Consolas", 9)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(loc_row, text="Browse...", command=self._browse_path, style="Secondary.TButton").pack(side=tk.LEFT)

        # --- Token Management ---
        token_frame = ttk.LabelFrame(self, text="Token Management", padding=10)
        token_frame.pack(fill=tk.X, pady=(0, 10))

        self._token_status_var = tk.StringVar(
            value="Token: " + ("Loaded" if self._app.config.token else "Missing")
        )
        ttk.Label(token_frame, textvariable=self._token_status_var).pack(anchor=tk.W, pady=(0, 5))

        token_btn_row = ttk.Frame(token_frame)
        token_btn_row.pack(fill=tk.X)

        self._extract_btn = ttk.Button(
            token_btn_row, text="Refresh Token (Selenium)", command=self._extract_token
        )
        self._extract_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            token_btn_row, text="Paste Token Manually", command=self._paste_token,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT)

        # --- Performance ---
        perf_frame = ttk.LabelFrame(self, text="Performance", padding=10)
        perf_frame.pack(fill=tk.X, pady=(0, 10))

        # Max concurrency
        row1 = ttk.Frame(perf_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Max concurrent connections:", width=30, anchor=tk.W).pack(side=tk.LEFT)
        self._concurrency_var = tk.IntVar(value=self._app.config.max_concurrency)
        ttk.Spinbox(row1, from_=1, to=20, textvariable=self._concurrency_var, width=5).pack(side=tk.LEFT)

        # Rate limit
        row2 = ttk.Frame(perf_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Rate limit (req/sec):", width=30, anchor=tk.W).pack(side=tk.LEFT)
        self._rate_var = tk.DoubleVar(value=self._app.config.rate_limit)
        ttk.Spinbox(row2, from_=1.0, to=20.0, increment=1.0, textvariable=self._rate_var, width=5).pack(
            side=tk.LEFT
        )

        # Chunk size
        row3 = ttk.Frame(perf_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="Download chunk size:", width=30, anchor=tk.W).pack(side=tk.LEFT)
        self._chunk_var = tk.StringVar(value="64 KB")
        ttk.Combobox(
            row3,
            textvariable=self._chunk_var,
            values=["16 KB", "32 KB", "64 KB", "128 KB", "256 KB"],
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT)

        # Cache TTL
        row4 = ttk.Frame(perf_frame)
        row4.pack(fill=tk.X, pady=2)
        ttk.Label(row4, text="API cache TTL (seconds):", width=30, anchor=tk.W).pack(side=tk.LEFT)
        self._cache_var = tk.IntVar(value=self._app.config.cache_ttl)
        ttk.Spinbox(row4, from_=0, to=3600, increment=60, textvariable=self._cache_var, width=5).pack(
            side=tk.LEFT
        )

        # Max retries
        row5 = ttk.Frame(perf_frame)
        row5.pack(fill=tk.X, pady=2)
        ttk.Label(row5, text="Max retries:", width=30, anchor=tk.W).pack(side=tk.LEFT)
        self._retry_var = tk.IntVar(value=self._app.config.retry_max)
        ttk.Spinbox(row5, from_=0, to=10, textvariable=self._retry_var, width=5).pack(side=tk.LEFT)

        # --- Default Storefront ---
        sf_frame = ttk.LabelFrame(self, text="Default Storefront", padding=10)
        sf_frame.pack(fill=tk.X, pady=(0, 10))

        sf_values = [f"{code.upper()} - {name}" for code, name in sorted(COUNTRY_CODES.items())]
        current_sf = self._app.config.storefront
        current_display = f"{current_sf.upper()} - {COUNTRY_CODES.get(current_sf, current_sf)}"

        self._sf_var = tk.StringVar(value=current_display)
        ttk.Combobox(
            sf_frame,
            textvariable=self._sf_var,
            values=sf_values,
            state="readonly",
            width=40,
        ).pack(anchor=tk.W)

        # --- Buttons ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Save Settings", command=self._save_settings).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        ttk.Button(
            btn_frame, text="Reset to Defaults", command=self._reset_defaults,
            style="Danger.TButton",
        ).pack(side=tk.LEFT)

    def update_theme_button(self, current_theme: str) -> None:
        """Update the theme toggle button text after a theme switch."""
        btn_text = "Switch to Light Mode" if current_theme == "dark" else "Switch to Dark Mode"
        self._theme_btn.configure(text=btn_text)

    def apply_theme(self, theme) -> None:
        """Apply theme to non-ttk widgets (paste-token dialog, etc.)."""
        pass  # Currently no non-ttk widgets that persist; dialog is transient

    def _browse_path(self):
        path = filedialog.askdirectory(title="Select save location")
        if path:
            self._path_var.set(path)

    def _extract_token(self):
        self._extract_btn.configure(state=tk.DISABLED)
        self._token_status_var.set("Extracting token...")
        self._app.log("Extracting token via Selenium...", "INFO")

        import threading

        def _run():
            try:
                token = extract_token_with_selenium(self._app.config.base_path)
                if token:
                    self._app.config.save_token(token)
                    self._app.schedule_on_gui(self._token_status_var.set, "Token: Updated")
                    self._app.log("Token extracted and saved", "SUCCESS")
                    self._app.update_status(token="Token: Valid")
                    # Recreate client session with new token
                    import asyncio
                    asyncio.run_coroutine_threadsafe(
                        self._app.client.close(), self._app._loop
                    )
                    self._app.client._config = self._app.config
                else:
                    self._app.schedule_on_gui(self._token_status_var.set, "Token: Extraction failed")
                    self._app.log("Token extraction returned None", "ERROR")
            except Exception as e:
                self._app.schedule_on_gui(self._token_status_var.set, f"Token: Error - {e}")
                self._app.log(f"Token extraction error: {e}", "ERROR")
            finally:
                self._app.schedule_on_gui(self._extract_btn.configure, state=tk.NORMAL)

        threading.Thread(target=_run, daemon=True).start()

    def _paste_token(self):
        dialog = tk.Toplevel(self._app.root)
        dialog.title("Paste Token")
        dialog.geometry("500x150")
        dialog.transient(self._app.root)
        dialog.grab_set()

        # Theme the dialog window
        theme = self._app.theme
        dialog.configure(bg=theme.bg)

        ttk.Label(dialog, text="Paste your Apple Music developer token:").pack(pady=(10, 5))

        token_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=token_var, width=60, font=("Consolas", 9))
        entry.pack(padx=10, fill=tk.X)
        entry.focus_set()

        def _save():
            token = token_var.get().strip()
            if token:
                self._app.config.save_token(token)
                self._token_status_var.set("Token: Updated (manual)")
                self._app.log("Token saved manually", "SUCCESS")
                self._app.update_status(token="Token: Valid")
            dialog.destroy()

        ttk.Button(dialog, text="Save", command=_save).pack(pady=10)

    def _save_settings(self):
        config = self._app.config

        # Save path
        path = self._path_var.get()
        if path and path != "(not set)":
            config.save_path = path

        # Performance
        config.max_concurrency = self._concurrency_var.get()
        config.rate_limit = self._rate_var.get()
        config.retry_max = self._retry_var.get()
        config.cache_ttl = self._cache_var.get()

        # Chunk size
        chunk_map = {
            "16 KB": 16384,
            "32 KB": 32768,
            "64 KB": 65536,
            "128 KB": 131072,
            "256 KB": 262144,
        }
        config.chunk_size = chunk_map.get(self._chunk_var.get(), 65536)

        # Storefront
        sf_text = self._sf_var.get()
        if " - " in sf_text:
            code = sf_text.split(" - ")[0].strip().lower()
            if code in COUNTRY_CODES:
                config.storefront = code
                self._app.update_status(storefront=f"Storefront: {code.upper()}")

        config.save()
        self._app.log("Settings saved", "SUCCESS")

    def _reset_defaults(self):
        self._concurrency_var.set(10)
        self._rate_var.set(18.0)
        self._chunk_var.set("64 KB")
        self._cache_var.set(300)
        self._retry_var.set(3)
        self._app.log("Settings reset to defaults (click Save to apply)", "INFO")
