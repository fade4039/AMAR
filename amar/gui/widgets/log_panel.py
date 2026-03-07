"""Minimal log panel - Apple HIG style."""

import tkinter as tk
from tkinter import ttk
from datetime import datetime


class LogPanel(ttk.Frame):
    """Compact log display with color-coded levels."""

    def __init__(self, parent, max_lines: int = 500, theme=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._max_lines = max_lines

        bg = theme.log_bg if theme else "#161618"
        fg = theme.log_fg if theme else "#98989D"

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=8, pady=(4, 2))

        self._line_var = tk.StringVar(value="0 lines")
        ttk.Label(toolbar, textvariable=self._line_var, font=("Segoe UI", 8), style="Secondary.TLabel").pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Clear", command=self.clear, style="Secondary.TButton").pack(side=tk.RIGHT)

        self._text = tk.Text(
            self, height=6, state=tk.DISABLED, wrap=tk.WORD,
            font=("Consolas", 9), bg=bg, fg=fg, insertbackground=fg,
            selectbackground=theme.table_select_bg if theme else "#3A3A3C",
            borderwidth=0, padx=8, pady=4,
        )
        sb = ttk.Scrollbar(self, command=self._text.yview)
        self._text.configure(yscrollcommand=sb.set)
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._apply_tag_colors(theme)

    def _apply_tag_colors(self, theme=None):
        if theme:
            self._text.tag_configure("INFO", foreground=theme.log_fg)
            self._text.tag_configure("SUCCESS", foreground=theme.green)
            self._text.tag_configure("WARNING", foreground=theme.orange)
            self._text.tag_configure("ERROR", foreground=theme.red)
        else:
            self._text.tag_configure("INFO", foreground="#98989D")
            self._text.tag_configure("SUCCESS", foreground="#30D158")
            self._text.tag_configure("WARNING", foreground="#FF9F0A")
            self._text.tag_configure("ERROR", foreground="#FF453A")

    def apply_theme(self, theme) -> None:
        self._text.configure(bg=theme.log_bg, fg=theme.log_fg, insertbackground=theme.log_fg, selectbackground=theme.table_select_bg)
        self._apply_tag_colors(theme)

    def log(self, message: str, level: str = "INFO") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._text.configure(state=tk.NORMAL)
        self._text.insert(tk.END, f"[{ts}] {message}\n", level)
        line_count = int(self._text.index("end-1c").split(".")[0])
        if line_count > self._max_lines:
            self._text.delete("1.0", f"{line_count - self._max_lines}.0")
        self._text.see(tk.END)
        self._text.configure(state=tk.DISABLED)
        self._line_var.set(f"{int(self._text.index('end-1c').split('.')[0]) - 1} lines")

    def clear(self) -> None:
        self._text.configure(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.configure(state=tk.DISABLED)
        self._line_var.set("0 lines")
