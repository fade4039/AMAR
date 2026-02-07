"""Progress bar composite widget with label and percentage display."""

import tkinter as tk
from tkinter import ttk


class LabeledProgress(ttk.Frame):
    """A progress bar with an associated label showing status text and percentage."""

    def __init__(self, parent, label_text: str = "", **kwargs):
        super().__init__(parent, **kwargs)

        self._label_var = tk.StringVar(value=label_text)
        self._label = ttk.Label(self, textvariable=self._label_var, font=("Segoe UI", 9))
        self._label.pack(fill=tk.X, anchor=tk.W)

        # Progress bar row with percentage label
        bar_row = ttk.Frame(self)
        bar_row.pack(fill=tk.X, pady=(2, 0))

        self._progress = ttk.Progressbar(bar_row, mode="determinate", maximum=100)
        self._progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self._pct_var = tk.StringVar(value="0%")
        self._pct_label = ttk.Label(
            bar_row, textvariable=self._pct_var, font=("Segoe UI", 9, "bold"),
            width=5, anchor=tk.E,
        )
        self._pct_label.pack(side=tk.RIGHT)

        self._detail_var = tk.StringVar(value="")
        self._detail = ttk.Label(
            self, textvariable=self._detail_var, font=("Segoe UI", 8),
            style="Secondary.TLabel",
        )
        self._detail.pack(fill=tk.X, anchor=tk.W)

    def set_progress(self, value: float, detail: str = "") -> None:
        """Update progress bar value (0-100) and optional detail text."""
        clamped = min(100, max(0, value))
        self._progress["value"] = clamped
        self._pct_var.set(f"{int(clamped)}%")
        if detail:
            self._detail_var.set(detail)

    def set_label(self, text: str) -> None:
        """Update the main label text."""
        self._label_var.set(text)

    def reset(self) -> None:
        """Reset progress to 0."""
        self._progress["value"] = 0
        self._pct_var.set("0%")
        self._detail_var.set("")

    def set_indeterminate(self, active: bool = True) -> None:
        """Switch to indeterminate mode (bouncing bar)."""
        if active:
            self._progress.configure(mode="indeterminate")
            self._progress.start(15)
            self._pct_var.set("...")
        else:
            self._progress.stop()
            self._progress.configure(mode="determinate")
            self._progress["value"] = 0
            self._pct_var.set("0%")
