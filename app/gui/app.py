"""AMAR v3 - Modern Desktop Application using CustomTkinter.

Main application window with sidebar navigation and async event loop integration.
"""

import asyncio
import threading
from typing import Optional

import customtkinter as ctk

from app.config import AMARConfig
from app.api.apple_music import AppleMusicClient
from app.core.ripper import AssetRipper, ProgressCallback
from app.gui.pages.download import DownloadPage
from app.gui.pages.search import SearchPage
from app.gui.pages.charts import ChartsPage
from app.gui.pages.library import LibraryPage
from app.gui.pages.storefronts import StorefrontsPage
from app.gui.pages.settings import SettingsPage


class AMARApp(ctk.CTk):
    """Main application window."""

    WIDTH = 1200
    HEIGHT = 780

    def __init__(self):
        super().__init__()

        self.title("AMAR - Apple Music Asset Ripper v3")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(900, 600)

        # Load config
        self.config = AMARConfig.load()

        # Apply theme
        ctk.set_appearance_mode(self.config.theme)
        ctk.set_default_color_theme("blue")

        # Async event loop in background thread
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # API client and ripper
        self.client: Optional[AppleMusicClient] = None
        self.ripper: Optional[AssetRipper] = None
        self._progress_cb = ProgressCallback()
        self._init_client()

        # Build UI
        self._build_layout()
        self._build_sidebar()
        self._build_pages()

        # Show default page
        self._show_page("download")

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _init_client(self):
        self.client = AppleMusicClient(self.config)
        self.ripper = AssetRipper(self.client, self.config, self._progress_cb)

    def reload_client(self):
        """Recreate the API client after config changes."""
        if self.client:
            asyncio.run_coroutine_threadsafe(self.client.close(), self._loop)
        self.config = AMARConfig.load()
        self._init_client()

    def run_async(self, coro):
        """Schedule an async coroutine from the GUI thread. Returns a Future."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo / Title
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(20, 4))

        title = ctk.CTkLabel(
            logo_frame, text="AMAR",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            logo_frame, text="Apple Music Asset Ripper v3",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        )
        subtitle.pack(anchor="w")

        # Separator
        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=("gray80", "gray25"))
        sep.pack(fill="x", padx=16, pady=(16, 8))

        # Navigation buttons
        self._nav_buttons = {}
        nav_items = [
            ("download", "Download"),
            ("search", "Search"),
            ("charts", "Charts"),
            ("library", "Library"),
            ("storefronts", "Storefronts"),
            ("settings", "Settings"),
        ]

        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=8, pady=4)

        for page_id, label in nav_items:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {label}",
                font=ctk.CTkFont(size=14),
                height=40,
                anchor="w",
                corner_radius=8,
                fg_color="transparent",
                text_color=("gray20", "gray80"),
                hover_color=("gray85", "gray25"),
                command=lambda pid=page_id: self._show_page(pid),
            )
            btn.pack(fill="x", pady=1)
            self._nav_buttons[page_id] = btn

        # Spacer
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Token status at bottom
        self._token_frame = ctk.CTkFrame(self.sidebar, fg_color=("gray90", "gray17"), corner_radius=8)
        self._token_frame.pack(fill="x", padx=12, pady=(4, 16))

        self._token_indicator = ctk.CTkLabel(
            self._token_frame,
            text="",
            width=10,
            font=ctk.CTkFont(size=10),
        )
        self._token_indicator.pack(side="left", padx=(12, 6), pady=10)

        self._token_label = ctk.CTkLabel(
            self._token_frame,
            text="Token: Checking...",
            font=ctk.CTkFont(size=12),
        )
        self._token_label.pack(side="left", padx=(0, 12), pady=10)

        self._update_token_status()

    def _update_token_status(self):
        token = self.config.token
        if token:
            self._token_indicator.configure(text_color=("green", "#22c55e"))
            self._token_indicator.configure(text="\u25cf")
            self._token_label.configure(text="Token: Active")
        else:
            self._token_indicator.configure(text_color=("red", "#ef4444"))
            self._token_indicator.configure(text="\u25cf")
            self._token_label.configure(text="Token: Missing")

    def _build_pages(self):
        self._pages = {}

        container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        container.grid(row=0, column=1, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        self._page_container = container

        page_classes = {
            "download": DownloadPage,
            "search": SearchPage,
            "charts": ChartsPage,
            "library": LibraryPage,
            "storefronts": StorefrontsPage,
            "settings": SettingsPage,
        }

        for page_id, page_cls in page_classes.items():
            page = page_cls(container, self)
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[page_id] = page

    def _show_page(self, page_id: str):
        # Update nav button states
        for pid, btn in self._nav_buttons.items():
            if pid == page_id:
                btn.configure(
                    fg_color=("gray80", "gray25"),
                    text_color=("gray10", "gray95"),
                    font=ctk.CTkFont(size=14, weight="bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("gray20", "gray80"),
                    font=ctk.CTkFont(size=14),
                )

        # Show selected page
        for pid, page in self._pages.items():
            if pid == page_id:
                page.tkraise()
                if hasattr(page, "on_show"):
                    page.on_show()

    def _on_close(self):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.client.close(), self._loop)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self.destroy()

    def log(self, level: str, message: str):
        """Log a message - thread-safe."""
        if hasattr(self, '_pages') and 'download' in self._pages:
            page = self._pages['download']
            if hasattr(page, 'add_log'):
                self.after(0, page.add_log, level, message)

    def update_token_display(self):
        self._update_token_status()
