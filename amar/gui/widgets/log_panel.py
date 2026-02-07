"""Scrollable log panel widget with timestamp, level coloring, clear button, and line count."""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Optional


class LogPanel(ttk.LabelFrame):
    """A scrollable, auto-tailing log display with color-coded log levels."""

    def __init__(self, parent, max_lines: int = 1000, theme=None, **kwargs):
        super().__init__(parent, text="Log", **kwargs)
        self._max_lines = max_lines
        self._line_count = 0

        # Use theme colors or defaults
        if theme:
            bg = theme.log_bg
            fg = theme.log_fg
        else:
            bg = "#1e1e1e"
            fg = "#cccccc"

        # Toolbar row with clear button and line count
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 3))

        self._line_count_var = tk.StringVar(value="0 lines")
        ttk.Label(
            toolbar, textvariable=self._line_count_var,
            font=("Segoe UI", 8), style="Secondary.TLabel",
        ).pack(side=tk.LEFT, padx=(2, 0))

        ttk.Button(
            toolbar, text="Clear Log", command=self.clear,
            style="Secondary.TButton",
        ).pack(side=tk.RIGHT, padx=(0, 2))

        # Log text area
        self._text = tk.Text(
            self,
            height=8,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=bg,
            fg=fg,
            insertbackground=fg,
            selectbackground=theme.tree_select_bg if theme else "#3c3c3c",
            borderwidth=0,
            padx=5,
            pady=5,
        )
        scrollbar = ttk.Scrollbar(self, command=self._text.yview)
        self._text.configure(yscrollcommand=scrollbar.set)

        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._apply_tag_colors(theme)

    def _apply_tag_colors(self, theme=None):
        if theme:
            self._text.tag_configure("INFO", foreground=theme.log_fg)
            self._text.tag_configure("SUCCESS", foreground=theme.log_success)
            self._text.tag_configure("WARNING", foreground=theme.log_warning)
            self._text.tag_configure("ERROR", foreground=theme.log_error)
        else:
            self._text.tag_configure("INFO", foreground="#cccccc")
            self._text.tag_configure("SUCCESS", foreground="#4ec9b0")
            self._text.tag_configure("WARNING", foreground="#dcdcaa")
            self._text.tag_configure("ERROR", foreground="#f44747")

    def apply_theme(self, theme) -> None:
        """Apply a new theme to the log panel (called on theme toggle)."""
        self._text.configure(
            bg=theme.log_bg,
            fg=theme.log_fg,
            insertbackground=theme.log_fg,
            selectbackground=theme.tree_select_bg,
        )
        self._apply_tag_colors(theme)

    def log(self, message: str, level: str = "INFO") -> None:
        """Append a log message. Must be called from the GUI thread."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._text.configure(state=tk.NORMAL)
        self._text.insert(tk.END, f"[{timestamp}] {message}\n", level)

        # Trim old lines
        line_count = int(self._text.index("end-1c").split(".")[0])
        if line_count > self._max_lines:
            self._text.delete("1.0", f"{line_count - self._max_lines}.0")

        self._text.see(tk.END)
        self._text.configure(state=tk.DISABLED)

        # Update line count display
        self._line_count = int(self._text.index("end-1c").split(".")[0]) - 1
        self._line_count_var.set(f"{self._line_count} lines")

    def clear(self) -> None:
        """Clear all log entries."""
        self._text.configure(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.configure(state=tk.DISABLED)
        self._line_count = 0
        self._line_count_var.set("0 lines")
