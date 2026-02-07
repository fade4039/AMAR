"""Treeview wrapper for displaying search/chart results with multi-select support."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Tuple


class ResultsView(ttk.Frame):
    """A Treeview-based results table with scrollbar and selection callbacks.

    Supports both single-select ('browse') and multi-select ('extended') modes.
    """

    def __init__(
        self,
        parent,
        columns: List[Tuple[str, str, int]],  # (id, heading, width)
        on_select: Optional[Callable[[Dict], None]] = None,
        on_double_click: Optional[Callable[[Dict], None]] = None,
        selectmode: str = "browse",
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self._on_select = on_select
        self._on_double_click = on_double_click
        self._row_data: Dict[str, Dict] = {}

        col_ids = [c[0] for c in columns]
        self._tree = ttk.Treeview(
            self,
            columns=col_ids,
            show="headings",
            selectmode=selectmode,
        )

        for col_id, heading, width in columns:
            self._tree.heading(col_id, text=heading, anchor=tk.W)
            self._tree.column(col_id, width=width, minwidth=40, anchor=tk.W)

        scrollbar_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar_y.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.bind("<<TreeviewSelect>>", self._handle_select)
        self._tree.bind("<Double-1>", self._handle_double_click)

    def clear(self) -> None:
        """Remove all rows."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._row_data.clear()

    def add_row(self, values: Tuple, data: Optional[Dict] = None) -> str:
        """Insert a row. Returns the item ID.

        Args:
            values: Tuple of column values
            data: Optional dict of extra data associated with this row
        """
        item_id = self._tree.insert("", tk.END, values=values)
        if data:
            self._row_data[item_id] = data
        return item_id

    def get_selected_data(self) -> Optional[Dict]:
        """Get the data dict for the first selected row."""
        selection = self._tree.selection()
        if selection:
            return self._row_data.get(selection[0])
        return None

    def get_all_selected_data(self) -> List[Dict]:
        """Get data dicts for ALL selected rows (useful in extended selectmode)."""
        result = []
        for item_id in self._tree.selection():
            data = self._row_data.get(item_id)
            if data:
                result.append(data)
        return result

    def select_all(self) -> None:
        """Select all rows in the treeview."""
        children = self._tree.get_children()
        if children:
            self._tree.selection_set(children)

    def deselect_all(self) -> None:
        """Deselect all rows in the treeview."""
        self._tree.selection_remove(self._tree.selection())

    def _handle_select(self, event):
        if self._on_select:
            data = self.get_selected_data()
            if data:
                self._on_select(data)

    def _handle_double_click(self, event):
        if self._on_double_click:
            data = self.get_selected_data()
            if data:
                self._on_double_click(data)

    @property
    def row_count(self) -> int:
        return len(self._tree.get_children())
