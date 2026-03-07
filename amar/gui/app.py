"""AMAR GUI - Apple HIG sidebar navigation layout."""

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
from .theme import THEMES, ThemeColors, apply_theme, FONT_FAMILY, FONT_LARGE_TITLE, FONT_CAPTION1


class AMARApp:
    """Main application with Apple HIG sidebar navigation."""

    NAV_ITEMS = [
        ("download", "Download"),
        ("queue", "Queue"),
        ("search", "Search"),
        ("charts", "Charts"),
        ("storefront", "Storefront"),
        ("settings", "Settings"),
    ]

    def __init__(self, config: AMARConfig):
        self.config = config
        self.client: Optional[AsyncAppleMusicClient] = None
        self.theme: ThemeColors = THEMES.get(config.theme, THEMES["dark"])
        self.queue_manager = QueueManager()

        self._loop = asyncio.new_event_loop()
        self._async_thread = threading.Thread(
            target=self._run_async_loop, daemon=True, name="amar-async"
        )

        self.root = tk.Tk()
        self.root.title("AMAR")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)
        self._set_icon()

        self._style = ttk.Style(self.root)
        if "clam" in self._style.theme_names():
            self._style.theme_use("clam")

        apply_theme(self.root, self._style, self.theme)
        self.queue_manager.on_change(self._on_queue_change)

        self._current_page = None
        self._pages = {}
        self._nav_buttons = {}
        self._sidebar_labels = []  # tk.Labels we need to re-theme
        self._build_ui()

    def _set_icon(self):
        try:
            if getattr(sys, 'frozen', False):
                meipass = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
                candidates = [os.path.join(meipass, "Icon.ico"), os.path.join(os.path.dirname(sys.executable), "Icon.ico")]
            else:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                candidates = [os.path.join(project_root, "Icon.ico")]
            for ico_path in candidates:
                if os.path.isfile(ico_path):
                    self.root.iconbitmap(ico_path)
                    break
        except Exception:
            pass

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run_async(self, coro: Coroutine) -> asyncio.Future:
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def schedule_on_gui(self, callback: Callable, *args, **kwargs) -> None:
        try:
            if kwargs:
                self.root.after(0, lambda: callback(*args, **kwargs))
            else:
                self.root.after(0, callback, *args)
        except tk.TclError:
            pass

    def log(self, message: str, level: str = "INFO") -> None:
        self.schedule_on_gui(self._log_panel.log, message, level)

    def make_log_callback(self) -> Callable[[str, str], None]:
        def _cb(message: str, level: str = "INFO"):
            self.log(message, level)
        return _cb

    def update_status(self, **kwargs) -> None:
        for key, value in kwargs.items():
            var = self._status_vars.get(key)
            if var:
                self.schedule_on_gui(var.set, value)

    def _on_queue_change(self) -> None:
        self.update_status(queue=self.queue_manager.status_summary)

    def toggle_theme(self) -> None:
        new_name = "light" if self.config.theme == "dark" else "dark"
        self.config.theme = new_name
        self.config.save()
        self.theme = THEMES[new_name]
        apply_theme(self.root, self._style, self.theme)

        self._log_panel.apply_theme(self.theme)
        self._retheme_sidebar()

        sf_tab = self._pages.get("storefront")
        if sf_tab:
            sf_tab.apply_theme(self.theme)
        queue_tab = self._pages.get("queue")
        if queue_tab:
            queue_tab.apply_theme(self.theme)
        settings_tab = self._pages.get("settings")
        if settings_tab:
            settings_tab.update_theme_button(new_name)

        self.log(f"Switched to {new_name} mode", "SUCCESS")

    def _retheme_sidebar(self):
        """Re-apply colors to non-ttk sidebar widgets after theme toggle."""
        t = self.theme
        self._sidebar_canvas.configure(bg=t.sidebar_bg)
        for lbl, color_key in self._sidebar_labels:
            color = getattr(t, color_key, t.fg_secondary)
            lbl.configure(bg=t.sidebar_bg, fg=color)
        for key, btn in self._nav_buttons.items():
            if key == self._current_page:
                btn.configure(style="SidebarItemActive.TButton")
            else:
                btn.configure(style="SidebarItem.TButton")

    def _build_ui(self):
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # --- Sidebar ---
        sidebar = ttk.Frame(main, style="Sidebar.TFrame", width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # App title
        title_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        title_frame.pack(fill=tk.X, padx=16, pady=(20, 4))

        lbl_title = tk.Label(title_frame, text="AMAR", font=FONT_LARGE_TITLE, bg=self.theme.sidebar_bg, fg=self.theme.accent, anchor="w")
        lbl_title.pack(fill=tk.X)
        self._sidebar_labels.append((lbl_title, "accent"))

        lbl_sub = tk.Label(title_frame, text="Apple Music API Ripper", font=FONT_CAPTION1, bg=self.theme.sidebar_bg, fg=self.theme.fg_secondary, anchor="w")
        lbl_sub.pack(fill=tk.X)
        self._sidebar_labels.append((lbl_sub, "fg_secondary"))

        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=(12, 8))

        lbl_section = tk.Label(sidebar, text="LIBRARY", font=(FONT_FAMILY, 8, "bold"), bg=self.theme.sidebar_bg, fg=self.theme.fg_tertiary, anchor="w")
        lbl_section.pack(fill=tk.X, padx=18, pady=(4, 4))
        self._sidebar_labels.append((lbl_section, "fg_tertiary"))

        # Nav buttons
        self._sidebar_canvas = tk.Canvas(sidebar, bg=self.theme.sidebar_bg, highlightthickness=0)
        self._sidebar_canvas.pack(fill=tk.BOTH, expand=True, padx=8)

        nav_inner = ttk.Frame(self._sidebar_canvas, style="Sidebar.TFrame")
        self._sidebar_canvas.create_window((0, 0), window=nav_inner, anchor="nw", width=184)

        for key, label in self.NAV_ITEMS:
            btn = ttk.Button(nav_inner, text=f"  {label}", style="SidebarItem.TButton", command=lambda k=key: self._navigate(k))
            btn.pack(fill=tk.X, pady=1)
            self._nav_buttons[key] = btn

        # Status at bottom of sidebar
        status_bottom = ttk.Frame(sidebar, style="Sidebar.TFrame")
        status_bottom.pack(fill=tk.X, side=tk.BOTTOM, padx=16, pady=(0, 16))

        self._status_vars = {
            "status": tk.StringVar(value="Ready"),
            "storefront": tk.StringVar(value=self.config.storefront.upper()),
            "token": tk.StringVar(value="Token: " + ("Valid" if self.config.token else "Missing")),
            "queue": tk.StringVar(value="Queue: 0"),
        }

        for var_key, color_key in [("queue", "fg_secondary"), ("storefront", "fg_tertiary"), ("token", "fg_tertiary")]:
            lbl = tk.Label(status_bottom, textvariable=self._status_vars[var_key], font=FONT_CAPTION1, bg=self.theme.sidebar_bg, fg=getattr(self.theme, color_key), anchor="w")
            lbl.pack(fill=tk.X)
            self._sidebar_labels.append((lbl, color_key))

        # --- Right content area ---
        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._content_frame = ttk.Frame(right)
        self._content_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X)

        from .widgets.log_panel import LogPanel
        self._log_panel = LogPanel(right, theme=self.theme)
        self._log_panel.pack(fill=tk.X)

    def _navigate(self, page_key: str):
        if page_key == self._current_page:
            return

        if self._current_page and self._current_page in self._nav_buttons:
            self._nav_buttons[self._current_page].configure(style="SidebarItem.TButton")
        self._nav_buttons[page_key].configure(style="SidebarItemActive.TButton")

        if self._current_page and self._current_page in self._pages:
            self._pages[self._current_page].pack_forget()

        if page_key not in self._pages:
            self._pages[page_key] = self._create_page(page_key)

        self._pages[page_key].pack(in_=self._content_frame, fill=tk.BOTH, expand=True)
        self._current_page = page_key

    def _create_page(self, key: str):
        from .tabs.download_tab import DownloadTab
        from .tabs.queue_tab import QueueTab
        from .tabs.search_tab import SearchTab
        from .tabs.charts_tab import ChartsTab
        from .tabs.storefront_tab import StorefrontTab
        from .tabs.settings_tab import SettingsTab

        creators = {
            "download": lambda: DownloadTab(self._content_frame, self),
            "queue": lambda: QueueTab(self._content_frame, self),
            "search": lambda: SearchTab(self._content_frame, self),
            "charts": lambda: ChartsTab(self._content_frame, self),
            "storefront": lambda: StorefrontTab(self._content_frame, self),
            "settings": lambda: SettingsTab(self._content_frame, self),
        }
        return creators[key]()

    def _init_tabs(self):
        self._navigate("download")

    async def _init_client(self):
        self.client = AsyncAppleMusicClient(self.config)
        self.client.set_log_callback(self.make_log_callback())
        await self.client._ensure_session()

    async def _cleanup(self):
        if self.client:
            await self.client.close()

    def _on_close(self):
        try:
            future = asyncio.run_coroutine_threadsafe(self._cleanup(), self._loop)
            future.result(timeout=5)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._async_thread.join(timeout=3)
        self.root.destroy()

    def run(self):
        self._async_thread.start()
        future = asyncio.run_coroutine_threadsafe(self._init_client(), self._loop)
        try:
            future.result(timeout=10)
            self.log("API client initialized", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to initialize API client: {e}", "ERROR")
        self._init_tabs()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def switch_to_download_tab(self, url: str = "") -> None:
        self._navigate("download")
        download_tab = self._pages.get("download")
        if download_tab and url:
            download_tab.set_url(url)

    def switch_to_queue_tab(self) -> None:
        self._navigate("queue")
