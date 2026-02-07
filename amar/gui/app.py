"""Main AMAR GUI application with async-tkinter bridge and theming."""

import asyncio
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Coroutine, Optional

from ..api.client import AsyncAppleMusicClient
from ..config import AMARConfig
from .queue_manager import QueueManager
from .theme import THEMES, ThemeColors, apply_theme
from .widgets.log_panel import LogPanel


class AMARApp:
    """Main application window for AMAR with async support.

    Runs an asyncio event loop in a background thread. GUI updates are
    pushed to the main thread via root.after(), and async work is
    submitted via asyncio.run_coroutine_threadsafe().
    """

    def __init__(self, config: AMARConfig):
        self.config = config
        self.client: Optional[AsyncAppleMusicClient] = None
        self.theme: ThemeColors = THEMES.get(config.theme, THEMES["dark"])
        self.queue_manager = QueueManager()

        # Async event loop in background thread
        self._loop = asyncio.new_event_loop()
        self._async_thread = threading.Thread(
            target=self._run_async_loop, daemon=True, name="amar-async"
        )

        # Build root window
        self.root = tk.Tk()
        self.root.title("AMAR - Apple Music API Ripper V2")
        self.root.geometry("1050x750")
        self.root.minsize(850, 650)

        # Set window icon
        self._set_icon()

        # Configure ttk style
        self._style = ttk.Style(self.root)
        available = self._style.theme_names()
        if "clam" in available:
            self._style.theme_use("clam")

        # Apply initial theme
        apply_theme(self.root, self._style, self.theme)

        # Register queue observer for status bar updates
        self.queue_manager.on_change(self._on_queue_change)

        self._build_ui()

    def _set_icon(self):
        """Set the window icon from Icon.ico if available."""
        try:
            # When frozen, PyInstaller extracts data to _MEIPASS temp dir
            if getattr(sys, 'frozen', False):
                meipass = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
                candidates = [
                    os.path.join(meipass, "Icon.ico"),
                    os.path.join(os.path.dirname(sys.executable), "Icon.ico"),
                ]
            else:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                candidates = [os.path.join(project_root, "Icon.ico")]
            for ico_path in candidates:
                if os.path.isfile(ico_path):
                    self.root.iconbitmap(ico_path)
                    break
        except Exception:
            pass  # Icon is cosmetic, don't crash

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run_async(self, coro: Coroutine) -> asyncio.Future:
        """Submit a coroutine to the background async event loop."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def schedule_on_gui(self, callback: Callable, *args, **kwargs) -> None:
        """Schedule a callback on the tkinter main thread.

        Supports both positional and keyword arguments.
        """
        try:
            if kwargs:
                self.root.after(0, lambda: callback(*args, **kwargs))
            else:
                self.root.after(0, callback, *args)
        except tk.TclError:
            pass  # Window already destroyed

    def log(self, message: str, level: str = "INFO") -> None:
        """Thread-safe log method. Can be called from any thread."""
        self.schedule_on_gui(self._log_panel.log, message, level)

    def make_log_callback(self) -> Callable[[str, str], None]:
        """Create a log callback safe for use from async code."""
        def _cb(message: str, level: str = "INFO"):
            self.log(message, level)
        return _cb

    def update_status(self, **kwargs) -> None:
        """Update status bar fields. Accepts: status, storefront, token, queue."""
        for key, value in kwargs.items():
            var = self._status_vars.get(key)
            if var:
                self.schedule_on_gui(var.set, value)

    def _on_queue_change(self) -> None:
        """Called when the queue manager changes — update status bar."""
        self.update_status(queue=self.queue_manager.status_summary)

    def toggle_theme(self) -> None:
        """Switch between dark and light themes."""
        new_name = "light" if self.config.theme == "dark" else "dark"
        self.config.theme = new_name
        self.config.save()
        self.theme = THEMES[new_name]
        apply_theme(self.root, self._style, self.theme)

        # Update non-ttk widgets that need manual recoloring
        self._log_panel.apply_theme(self.theme)

        # Update listboxes in storefront tab
        sf_tab = self._tabs.get("storefront")
        if sf_tab:
            sf_tab.apply_theme(self.theme)

        # Update queue tab tree tag colors
        queue_tab = self._tabs.get("queue")
        if queue_tab:
            queue_tab.apply_theme(self.theme)

        # Update settings tab theme button text
        settings_tab = self._tabs.get("settings")
        if settings_tab:
            settings_tab.update_theme_button(new_name)

        self.log(f"Switched to {new_name} mode", "SUCCESS")

    def _build_ui(self):
        # Main frame with generous padding
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top bar
        top_bar = ttk.Frame(main_frame)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        # Title label
        ttk.Label(
            top_bar,
            text="AMAR",
            font=("Segoe UI", 16, "bold"),
        ).pack(side=tk.LEFT)

        ttk.Label(
            top_bar,
            text="  Apple Music API Ripper",
            font=("Segoe UI", 10),
            style="Secondary.TLabel",
        ).pack(side=tk.LEFT, pady=(5, 0))

        # Separator between top bar and notebook
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 8))

        # Notebook (tabs)
        self._notebook = ttk.Notebook(main_frame)
        self._notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Tabs will be added after client initialization
        self._tabs = {}

        # Separator between notebook and log panel
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 8))

        # Log panel (docked at bottom)
        self._log_panel = LogPanel(main_frame, theme=self.theme)
        self._log_panel.pack(fill=tk.X, pady=(0, 8))

        # Status bar
        self._build_status_bar(main_frame)

    def _build_status_bar(self, parent):
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X)

        self._status_vars = {
            "status": tk.StringVar(value="Ready"),
            "storefront": tk.StringVar(value=f"Storefront: {self.config.storefront.upper()}"),
            "token": tk.StringVar(value="Token: " + ("Valid" if self.config.token else "Missing")),
            "queue": tk.StringVar(value="Queue: 0"),
        }

        for i, (key, var) in enumerate(self._status_vars.items()):
            if i > 0:
                ttk.Separator(status_frame, orient=tk.VERTICAL).pack(
                    side=tk.LEFT, fill=tk.Y, padx=5, pady=2
                )
            ttk.Label(status_frame, textvariable=var, font=("Segoe UI", 9)).pack(
                side=tk.LEFT, padx=5
            )

    def _init_tabs(self):
        """Initialize all tabs after the client is ready."""
        from .tabs.download_tab import DownloadTab
        from .tabs.queue_tab import QueueTab
        from .tabs.search_tab import SearchTab
        from .tabs.charts_tab import ChartsTab
        from .tabs.storefront_tab import StorefrontTab
        from .tabs.settings_tab import SettingsTab

        self._tabs["download"] = DownloadTab(self._notebook, self)
        self._notebook.add(self._tabs["download"], text="  Download  ")

        self._tabs["queue"] = QueueTab(self._notebook, self)
        self._notebook.add(self._tabs["queue"], text="  Queue  ")

        self._tabs["search"] = SearchTab(self._notebook, self)
        self._notebook.add(self._tabs["search"], text="  Search  ")

        self._tabs["charts"] = ChartsTab(self._notebook, self)
        self._notebook.add(self._tabs["charts"], text="  Charts  ")

        self._tabs["storefront"] = StorefrontTab(self._notebook, self)
        self._notebook.add(self._tabs["storefront"], text="  Storefront  ")

        self._tabs["settings"] = SettingsTab(self._notebook, self)
        self._notebook.add(self._tabs["settings"], text="  Settings  ")

    async def _init_client(self):
        """Initialize the async API client."""
        self.client = AsyncAppleMusicClient(self.config)
        self.client.set_log_callback(self.make_log_callback())
        await self.client._ensure_session()

    async def _cleanup(self):
        """Clean up the async client."""
        if self.client:
            await self.client.close()

    def _on_close(self):
        """Handle window close - clean up async resources."""
        try:
            future = asyncio.run_coroutine_threadsafe(self._cleanup(), self._loop)
            future.result(timeout=5)
        except Exception:
            pass

        self._loop.call_soon_threadsafe(self._loop.stop)
        self._async_thread.join(timeout=3)
        self.root.destroy()

    def run(self):
        """Start the application."""
        # Start async thread
        self._async_thread.start()

        # Initialize client asynchronously
        future = asyncio.run_coroutine_threadsafe(self._init_client(), self._loop)
        try:
            future.result(timeout=10)
            self.log("API client initialized", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to initialize API client: {e}", "ERROR")

        # Build tabs
        self._init_tabs()

        # Set close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Run tkinter main loop
        self.root.mainloop()

    def switch_to_download_tab(self, url: str = "") -> None:
        """Switch to the download tab, optionally pre-filling the URL."""
        download_tab = self._tabs.get("download")
        if download_tab:
            self._notebook.select(download_tab)
            if url:
                download_tab.set_url(url)

    def switch_to_queue_tab(self) -> None:
        """Switch to the queue tab."""
        queue_tab = self._tabs.get("queue")
        if queue_tab:
            self._notebook.select(queue_tab)
