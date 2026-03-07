"""Library page - download history, favorites, and file browser."""

import json
import os
import subprocess
import sys
from pathlib import Path

import customtkinter as ctk

from app.config import HISTORY_FILE, FAVORITES_FILE, CONFIG_DIR


class LibraryPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            header, text="Library",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text="Browse your downloads, history, and favorites",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w", pady=(2, 0))

        # ── Stats bar ──
        stats_frame = ctk.CTkFrame(self, corner_radius=12)
        stats_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=8)

        stats_inner = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_inner.pack(fill="x", padx=16, pady=12)

        self._stat_files = self._make_stat(stats_inner, "0", "Files Downloaded")
        self._stat_size = self._make_stat(stats_inner, "0 B", "Total Size")
        self._stat_history = self._make_stat(stats_inner, "0", "History Entries")
        self._stat_favorites = self._make_stat(stats_inner, "0", "Favorites")

        # Open folder button
        open_btn = ctk.CTkButton(
            stats_inner, text="Open Downloads Folder", height=32, width=160,
            font=ctk.CTkFont(size=12),
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray35"),
            text_color=("gray20", "gray80"),
            corner_radius=6,
            command=self._open_downloads_folder,
        )
        open_btn.pack(side="right")

        # ── Tabs ──
        self._tab_view = ctk.CTkTabview(self, corner_radius=12)
        self._tab_view.grid(row=2, column=0, sticky="nsew", padx=24, pady=(4, 16))

        # History tab
        history_tab = self._tab_view.add("History")
        history_tab.grid_columnconfigure(0, weight=1)
        history_tab.grid_rowconfigure(1, weight=1)

        history_controls = ctk.CTkFrame(history_tab, fg_color="transparent")
        history_controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkButton(
            history_controls, text="Refresh", height=28, width=80,
            font=ctk.CTkFont(size=11),
            corner_radius=6,
            command=self._load_history,
        ).pack(side="left")

        ctk.CTkButton(
            history_controls, text="Clear History", height=28, width=100,
            font=ctk.CTkFont(size=11),
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray35"),
            text_color=("gray20", "gray80"),
            corner_radius=6,
            command=self._clear_history,
        ).pack(side="right")

        self._history_scroll = ctk.CTkScrollableFrame(history_tab, corner_radius=8)
        self._history_scroll.grid(row=1, column=0, sticky="nsew")
        self._history_scroll.grid_columnconfigure(0, weight=1)

        # Favorites tab
        favorites_tab = self._tab_view.add("Favorites")
        favorites_tab.grid_columnconfigure(0, weight=1)
        favorites_tab.grid_rowconfigure(1, weight=1)

        fav_controls = ctk.CTkFrame(favorites_tab, fg_color="transparent")
        fav_controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkButton(
            fav_controls, text="Refresh", height=28, width=80,
            font=ctk.CTkFont(size=11),
            corner_radius=6,
            command=self._load_favorites,
        ).pack(side="left")

        self._favorites_scroll = ctk.CTkScrollableFrame(favorites_tab, corner_radius=8)
        self._favorites_scroll.grid(row=1, column=0, sticky="nsew")
        self._favorites_scroll.grid_columnconfigure(0, weight=1)

        # Files tab
        files_tab = self._tab_view.add("Files")
        files_tab.grid_columnconfigure(0, weight=1)
        files_tab.grid_rowconfigure(1, weight=1)

        files_controls = ctk.CTkFrame(files_tab, fg_color="transparent")
        files_controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self._path_label = ctk.CTkLabel(
            files_controls, text="",
            font=ctk.CTkFont(size=12, family="Courier"),
            text_color=("gray50", "gray60"),
        )
        self._path_label.pack(side="left")

        ctk.CTkButton(
            files_controls, text="Refresh", height=28, width=80,
            font=ctk.CTkFont(size=11),
            corner_radius=6,
            command=lambda: self._browse_files(""),
        ).pack(side="right")

        self._files_scroll = ctk.CTkScrollableFrame(files_tab, corner_radius=8)
        self._files_scroll.grid(row=1, column=0, sticky="nsew")
        self._files_scroll.grid_columnconfigure(0, weight=1)

    def _make_stat(self, parent, value, label):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", padx=(0, 32))

        val_label = ctk.CTkLabel(
            frame, text=value,
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        val_label.pack(anchor="w")

        ctk.CTkLabel(
            frame, text=label,
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w")

        return val_label

    def on_show(self):
        self._update_stats()
        self._load_history()
        self._load_favorites()
        self._browse_files("")

    def _update_stats(self):
        base = Path(self.app.config.save_path)
        total_files = 0
        total_size = 0

        if base.exists():
            for root, dirs, files in os.walk(base):
                total_files += len(files)
                for f in files:
                    try:
                        total_size += (Path(root) / f).stat().st_size
                    except OSError:
                        pass

        history = self._read_json(HISTORY_FILE)
        favorites = self._read_json(FAVORITES_FILE)

        self._stat_files.configure(text=str(total_files))
        self._stat_size.configure(text=self._human_size(total_size))
        self._stat_history.configure(text=str(len(history)))
        self._stat_favorites.configure(text=str(len(favorites)))

    def _load_history(self):
        for w in self._history_scroll.winfo_children():
            w.destroy()

        history = self._read_json(HISTORY_FILE)
        if not history:
            ctk.CTkLabel(
                self._history_scroll, text="No download history yet",
                font=ctk.CTkFont(size=13), text_color=("gray50", "gray60"),
            ).grid(row=0, column=0, pady=30)
            return

        for i, entry in enumerate(history[:100]):
            frame = ctk.CTkFrame(self._history_scroll, corner_radius=6, fg_color=("gray92", "gray17"))
            frame.grid(row=i, column=0, sticky="ew", padx=2, pady=2)
            frame.grid_columnconfigure(1, weight=1)

            rtype = entry.get("type", "unknown")
            ctk.CTkLabel(
                frame, text=rtype.upper()[:6],
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=("gray50", "gray60"),
                width=50,
            ).grid(row=0, column=0, padx=(10, 8), pady=8)

            ctk.CTkLabel(
                frame, text=entry.get("name", "Unknown"),
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            ).grid(row=0, column=1, sticky="w")

            details = []
            total = entry.get("total_files", 0)
            if total:
                details.append(f"{total} files")
            ts = entry.get("timestamp", "")
            if ts:
                details.append(ts[:19].replace("T", " "))

            if details:
                ctk.CTkLabel(
                    frame, text="  \u2022  ".join(details),
                    font=ctk.CTkFont(size=11),
                    text_color=("gray50", "gray60"),
                ).grid(row=0, column=2, padx=(8, 12), pady=8)

    def _load_favorites(self):
        for w in self._favorites_scroll.winfo_children():
            w.destroy()

        favorites = self._read_json(FAVORITES_FILE)
        if not favorites:
            ctk.CTkLabel(
                self._favorites_scroll, text="No favorites saved yet",
                font=ctk.CTkFont(size=13), text_color=("gray50", "gray60"),
            ).grid(row=0, column=0, pady=30)
            return

        for i, fav in enumerate(favorites):
            frame = ctk.CTkFrame(self._favorites_scroll, corner_radius=6, fg_color=("gray92", "gray17"))
            frame.grid(row=i, column=0, sticky="ew", padx=2, pady=2)
            frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                frame, text=fav.get("name", "Unknown"),
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=10, pady=8)

            artist = fav.get("artist", "")
            if artist:
                ctk.CTkLabel(
                    frame, text=artist,
                    font=ctk.CTkFont(size=11),
                    text_color=("gray50", "gray60"),
                ).grid(row=0, column=1, padx=8, pady=8)

            # Remove button
            ctk.CTkButton(
                frame, text="Remove", height=24, width=60,
                font=ctk.CTkFont(size=10),
                fg_color=("gray80", "gray25"),
                hover_color=("gray70", "gray35"),
                text_color=("gray20", "gray80"),
                corner_radius=4,
                command=lambda rt=fav.get("resource_type", ""), rid=fav.get("resource_id", ""): (
                    self._remove_favorite(rt, rid)
                ),
            ).grid(row=0, column=2, padx=(4, 10), pady=8)

    def _remove_favorite(self, resource_type: str, resource_id: str):
        favorites = self._read_json(FAVORITES_FILE)
        favorites = [
            f for f in favorites
            if not (f.get("resource_id") == resource_id and f.get("resource_type") == resource_type)
        ]
        self._write_json(FAVORITES_FILE, favorites)
        self._load_favorites()
        self._update_stats()

    def _browse_files(self, subpath: str):
        for w in self._files_scroll.winfo_children():
            w.destroy()

        base = Path(self.app.config.save_path)
        target = base / subpath if subpath else base
        self._path_label.configure(text=str(target))

        if not target.exists():
            ctk.CTkLabel(
                self._files_scroll, text="Download folder does not exist yet",
                font=ctk.CTkFont(size=13), text_color=("gray50", "gray60"),
            ).grid(row=0, column=0, pady=30)
            return

        # Back button if in subfolder
        row = 0
        if subpath:
            parent = str(Path(subpath).parent) if Path(subpath).parent != Path(subpath) else ""
            back_frame = ctk.CTkFrame(self._files_scroll, corner_radius=6, fg_color=("gray92", "gray17"), cursor="hand2")
            back_frame.grid(row=row, column=0, sticky="ew", padx=2, pady=2)
            back_frame.grid_columnconfigure(1, weight=1)
            back_frame.bind("<Button-1>", lambda e, p=parent: self._browse_files(p))

            ctk.CTkLabel(back_frame, text="\u2190", font=ctk.CTkFont(size=16), width=30).grid(row=0, column=0, padx=10, pady=6)
            lbl = ctk.CTkLabel(back_frame, text=".. (Go Back)", font=ctk.CTkFont(size=13), anchor="w")
            lbl.grid(row=0, column=1, sticky="w")
            lbl.bind("<Button-1>", lambda e, p=parent: self._browse_files(p))
            row += 1

        try:
            entries = sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return

        for entry in entries:
            item_frame = ctk.CTkFrame(self._files_scroll, corner_radius=6, fg_color=("gray92", "gray17"))
            item_frame.grid(row=row, column=0, sticky="ew", padx=2, pady=1)
            item_frame.grid_columnconfigure(1, weight=1)

            if entry.is_dir():
                item_frame.configure(cursor="hand2")
                rel = str(entry.relative_to(base))
                item_frame.bind("<Button-1>", lambda e, p=rel: self._browse_files(p))

                icon_lbl = ctk.CTkLabel(item_frame, text="\U0001F4C1", font=ctk.CTkFont(size=14), width=30)
                icon_lbl.grid(row=0, column=0, padx=10, pady=6)
                icon_lbl.bind("<Button-1>", lambda e, p=rel: self._browse_files(p))

                name_lbl = ctk.CTkLabel(item_frame, text=entry.name, font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
                name_lbl.grid(row=0, column=1, sticky="w")
                name_lbl.bind("<Button-1>", lambda e, p=rel: self._browse_files(p))
            else:
                ext = entry.suffix.lower()
                icon = "\U0001F5BC" if ext in (".jpg", ".jpeg", ".png", ".webp") else "\U0001F4C4"

                ctk.CTkLabel(item_frame, text=icon, font=ctk.CTkFont(size=14), width=30).grid(row=0, column=0, padx=10, pady=6)
                ctk.CTkLabel(item_frame, text=entry.name, font=ctk.CTkFont(size=13), anchor="w").grid(row=0, column=1, sticky="w")

                try:
                    size = entry.stat().st_size
                    ctk.CTkLabel(
                        item_frame, text=self._human_size(size),
                        font=ctk.CTkFont(size=11, family="Courier"),
                        text_color=("gray50", "gray60"),
                    ).grid(row=0, column=2, padx=(8, 12), pady=6)
                except OSError:
                    pass

            row += 1

        if row == 0:
            ctk.CTkLabel(
                self._files_scroll, text="Empty folder",
                font=ctk.CTkFont(size=13), text_color=("gray50", "gray60"),
            ).grid(row=0, column=0, pady=30)

    def _open_downloads_folder(self):
        path = self.app.config.save_path
        Path(path).mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    def _clear_history(self):
        self._write_json(HISTORY_FILE, [])
        self._load_history()
        self._update_stats()

    @staticmethod
    def _read_json(path: Path) -> list:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    @staticmethod
    def _write_json(path: Path, data: list):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def _human_size(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
