"""Download queue data model with observable pattern for GUI updates."""

import uuid
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class QueueItem:
    """A single item in the download queue."""

    id: str                          # Unique queue ID (UUID)
    name: str                        # Display name ("Album Name - Artist")
    item_type: str                   # "artist", "album", "music-video"
    item_id: str                     # Apple Music catalog ID
    url: str                         # Apple Music URL
    status: str = "pending"          # pending | downloading | complete | error | cancelled
    error: str = ""                  # Error message if status == "error"
    progress: float = 0.0            # 0-100

    @property
    def display_type(self) -> str:
        """Human-readable type for display."""
        return {
            "artist": "Artist",
            "album": "Album",
            "music-video": "Music Video",
        }.get(self.item_type, self.item_type.title())

    @property
    def status_icon(self) -> str:
        """Status emoji for treeview display."""
        return {
            "pending": "Pending",
            "downloading": "Downloading",
            "complete": "Done",
            "error": "Error",
            "cancelled": "Cancelled",
        }.get(self.status, "?")


class QueueManager:
    """Manages an ordered list of QueueItems with observer notifications.

    The observer pattern lets the GUI (status bar, queue tab) react to
    changes without tight coupling.
    """

    def __init__(self):
        self._items: List[QueueItem] = []
        self._observers: List[Callable[[], None]] = []

    # --- Observer pattern ---

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register a callback that fires whenever the queue changes."""
        self._observers.append(callback)

    def _notify(self) -> None:
        """Notify all observers of a change."""
        for cb in self._observers:
            try:
                cb()
            except Exception:
                pass

    # --- Queue operations ---

    def add(self, name: str, item_type: str, item_id: str, url: str) -> Optional[QueueItem]:
        """Add an item to the queue.

        Returns the QueueItem, or None if the type is not downloadable (e.g. songs).
        """
        if item_type == "song":
            return None

        # Avoid duplicates (same catalog ID and type)
        for existing in self._items:
            if existing.item_id == item_id and existing.item_type == item_type:
                if existing.status in ("pending", "downloading"):
                    return None  # Already queued

        item = QueueItem(
            id=str(uuid.uuid4()),
            name=name,
            item_type=item_type,
            item_id=item_id,
            url=url,
        )
        self._items.append(item)
        self._notify()
        return item

    def remove(self, queue_id: str) -> None:
        """Remove an item by its queue ID."""
        self._items = [item for item in self._items if item.id != queue_id]
        self._notify()

    def clear_completed(self) -> int:
        """Remove completed, error, and cancelled items. Returns count removed."""
        before = len(self._items)
        self._items = [
            item for item in self._items
            if item.status not in ("complete", "error", "cancelled")
        ]
        removed = before - len(self._items)
        if removed:
            self._notify()
        return removed

    def move_up(self, queue_id: str) -> None:
        """Move an item one position earlier in the queue."""
        for i, item in enumerate(self._items):
            if item.id == queue_id and i > 0:
                self._items[i], self._items[i - 1] = self._items[i - 1], self._items[i]
                self._notify()
                break

    def move_down(self, queue_id: str) -> None:
        """Move an item one position later in the queue."""
        for i, item in enumerate(self._items):
            if item.id == queue_id and i < len(self._items) - 1:
                self._items[i], self._items[i + 1] = self._items[i + 1], self._items[i]
                self._notify()
                break

    def update_status(self, queue_id: str, status: str, error: str = "", progress: float = -1) -> None:
        """Update an item's status and optionally progress/error."""
        for item in self._items:
            if item.id == queue_id:
                item.status = status
                if error:
                    item.error = error
                if progress >= 0:
                    item.progress = progress
                self._notify()
                break

    def update_progress(self, queue_id: str, progress: float) -> None:
        """Update just the progress of an item (frequent updates, no observer notify)."""
        for item in self._items:
            if item.id == queue_id:
                item.progress = progress
                break

    def get_item(self, queue_id: str) -> Optional[QueueItem]:
        """Get an item by queue ID."""
        for item in self._items:
            if item.id == queue_id:
                return item
        return None

    @property
    def items(self) -> List[QueueItem]:
        """All items in queue order."""
        return list(self._items)

    @property
    def pending_items(self) -> List[QueueItem]:
        """All pending items."""
        return [item for item in self._items if item.status == "pending"]

    @property
    def pending_count(self) -> int:
        return sum(1 for item in self._items if item.status == "pending")

    @property
    def total_count(self) -> int:
        return len(self._items)

    @property
    def status_summary(self) -> str:
        """Summary string for status bar: 'Queue: 3/5'."""
        pending = self.pending_count
        total = self.total_count
        return f"Queue: {pending}/{total}" if total else "Queue: 0"
