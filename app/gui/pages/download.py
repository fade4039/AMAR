"""Download page - URL input, options, progress tracking, and log display."""

import uuid
import customtkinter as ctk
from datetime import datetime

from app.core.utils import parse_apple_music_url


class DownloadPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._tasks = {}
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            header, text="Download",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text="Paste an Apple Music URL to download artwork and metadata",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w", pady=(2, 0))

        # ── URL Input ──
        input_card = ctk.CTkFrame(self, corner_radius=12)
        input_card.grid(row=1, column=0, sticky="ew", padx=24, pady=8)
        input_card.grid_columnconfigure(0, weight=1)

        url_row = ctk.CTkFrame(input_card, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(16, 8))
        url_row.grid_columnconfigure(0, weight=1)

        self._url_entry = ctk.CTkEntry(
            url_row,
            placeholder_text="Paste Apple Music URL here...",
            height=42,
            font=ctk.CTkFont(size=14),
            corner_radius=10,
        )
        self._url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._url_entry.bind("<Return>", lambda e: self._start_download())

        self._download_btn = ctk.CTkButton(
            url_row,
            text="Download",
            height=42,
            width=120,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10,
            command=self._start_download,
        )
        self._download_btn.grid(row=0, column=1)

        # ── Options ──
        opts_row = ctk.CTkFrame(input_card, fg_color="transparent")
        opts_row.pack(fill="x", padx=16, pady=(4, 16))

        self._opt_all_sf = ctk.CTkCheckBox(
            opts_row, text="All Storefronts",
            font=ctk.CTkFont(size=12),
            checkbox_height=18, checkbox_width=18, corner_radius=4,
        )
        self._opt_all_sf.pack(side="left", padx=(0, 16))

        self._opt_albums = ctk.CTkCheckBox(
            opts_row, text="Include Albums",
            font=ctk.CTkFont(size=12),
            checkbox_height=18, checkbox_width=18, corner_radius=4,
        )
        self._opt_albums.pack(side="left", padx=(0, 16))

        self._opt_videos = ctk.CTkCheckBox(
            opts_row, text="Include Videos",
            font=ctk.CTkFont(size=12),
            checkbox_height=18, checkbox_width=18, corner_radius=4,
        )
        self._opt_videos.pack(side="left", padx=(0, 16))

        # Detected type label
        self._type_label = ctk.CTkLabel(
            opts_row, text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
        )
        self._type_label.pack(side="right")

        self._url_entry.bind("<KeyRelease>", self._on_url_change)

        # ── Active Downloads / Progress ──
        progress_header = ctk.CTkFrame(self, fg_color="transparent")
        progress_header.grid(row=2, column=0, sticky="ew", padx=24, pady=(12, 4))

        ctk.CTkLabel(
            progress_header, text="Downloads",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        self._clear_btn = ctk.CTkButton(
            progress_header, text="Clear Completed", height=28, width=120,
            font=ctk.CTkFont(size=11),
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray35"),
            text_color=("gray20", "gray80"),
            corner_radius=6,
            command=self._clear_completed,
        )
        self._clear_btn.pack(side="right")

        # ── Scrollable task list + log ──
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=3, column=0, sticky="nsew", padx=24, pady=(4, 16))
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_rowconfigure(0, weight=1)
        bottom_frame.grid_rowconfigure(1, weight=1)

        # Task list
        self._task_scroll = ctk.CTkScrollableFrame(
            bottom_frame, corner_radius=12,
            label_text="Active Tasks",
            label_font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._task_scroll.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self._task_scroll.grid_columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._task_scroll,
            text="No active downloads\nPaste a URL above to get started",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
            justify="center",
        )
        self._empty_label.grid(row=0, column=0, pady=30)

        # Log panel
        self._log_frame = ctk.CTkFrame(bottom_frame, corner_radius=12)
        self._log_frame.grid(row=1, column=0, sticky="nsew")
        self._log_frame.grid_columnconfigure(0, weight=1)
        self._log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self._log_frame, text="  Activity Log",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        self._log_text = ctk.CTkTextbox(
            self._log_frame,
            height=120,
            font=ctk.CTkFont(family="Courier", size=12),
            corner_radius=8,
            state="disabled",
            wrap="word",
        )
        self._log_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    def _on_url_change(self, event=None):
        url = self._url_entry.get().strip()
        if url:
            parsed = parse_apple_music_url(url)
            if parsed:
                rtype = parsed["type"].replace("-", " ").title()
                sf = parsed["storefront"].upper()
                self._type_label.configure(text=f"Detected: {rtype} ({sf})")
            else:
                self._type_label.configure(text="Invalid URL")
        else:
            self._type_label.configure(text="")

    def _start_download(self):
        url = self._url_entry.get().strip()
        if not url:
            self.add_log("warning", "Please enter an Apple Music URL")
            return

        parsed = parse_apple_music_url(url)
        if not parsed:
            self.add_log("error", "Invalid Apple Music URL")
            return

        if not self.app.config.token:
            self.add_log("error", "No API token configured. Go to Settings to set one.")
            return

        task_id = str(uuid.uuid4())[:8]
        resource_type = parsed["type"]
        resource_id = parsed["id"]
        storefront = parsed["storefront"]
        all_sf = self._opt_all_sf.get()
        include_albums = self._opt_albums.get()

        # Create task UI
        self._add_task_ui(task_id, resource_type, resource_id, storefront)

        # Set up progress callback
        self.app._progress_cb.on_progress = lambda tid, prog, status, detail: (
            self.after(0, self._update_task, tid, prog, status, detail)
        )
        self.app._progress_cb.on_log = lambda level, msg: (
            self.after(0, self.add_log, level, msg)
        )

        # Run the download
        async def _do_download():
            try:
                ripper = self.app.ripper
                if all_sf:
                    result = await ripper.rip_all_storefronts(resource_type, resource_id, task_id)
                elif resource_type == "artist" and include_albums:
                    result = await ripper.rip_artist_full(resource_id, storefront, task_id)
                else:
                    result = await ripper._rip_by_type(resource_type, resource_id, storefront, task_id)

                self.after(0, self._finish_task, task_id, result)
            except Exception as e:
                self.after(0, self._error_task, task_id, str(e))

        self.app.run_async(_do_download())
        self._url_entry.delete(0, "end")
        self._type_label.configure(text="")
        self.add_log("info", f"Started downloading {resource_type} {resource_id} from {storefront.upper()}")

    def _add_task_ui(self, task_id: str, rtype: str, rid: str, sf: str):
        self._empty_label.grid_remove()

        frame = ctk.CTkFrame(self._task_scroll, corner_radius=10)
        frame.grid(sticky="ew", padx=4, pady=4)
        frame.grid_columnconfigure(1, weight=1)

        # Type badge
        type_colors = {
            "artist": ("#7c5cfc", "#5a3fd6"),
            "album": ("#fa2d48", "#d41e38"),
            "song": ("#22c55e", "#16a34a"),
            "music-video": ("#3b82f6", "#2563eb"),
            "playlist": ("#f59e0b", "#d97706"),
            "station": ("#06b6d4", "#0891b2"),
        }
        color = type_colors.get(rtype, ("#6b7280", "#4b5563"))

        badge = ctk.CTkLabel(
            frame, text=f" {rtype.upper()} ",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=color[0],
            text_color="white",
            corner_radius=4,
            width=80,
        )
        badge.grid(row=0, column=0, padx=(12, 8), pady=(12, 4), sticky="w")

        # Name / ID
        name_label = ctk.CTkLabel(
            frame, text=f"ID: {rid}  |  {sf.upper()}",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        name_label.grid(row=0, column=1, sticky="w", pady=(12, 4))

        # Status
        status_label = ctk.CTkLabel(
            frame, text="Starting...",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
        )
        status_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 4))

        # Progress bar
        progress = ctk.CTkProgressBar(frame, height=6, corner_radius=3)
        progress.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 12))
        progress.set(0)

        self._tasks[task_id] = {
            "frame": frame,
            "name": name_label,
            "status": status_label,
            "progress": progress,
            "badge": badge,
            "done": False,
        }

    def _update_task(self, task_id: str, progress: float, status: str, detail: str):
        task = self._tasks.get(task_id)
        if not task or task["done"]:
            return
        task["progress"].set(progress)
        task["status"].configure(text=detail or status)
        if detail and ":" in detail:
            # Update name with resolved name
            task["name"].configure(text=detail.split(": ", 1)[-1] if "Processing" in detail else task["name"].cget("text"))

    def _finish_task(self, task_id: str, result: dict):
        task = self._tasks.get(task_id)
        if not task:
            return
        task["done"] = True
        task["progress"].set(1.0)
        total = result.get("total_files", 0)
        name = result.get("name", "Unknown")
        task["status"].configure(
            text=f"Complete - {total} files downloaded",
            text_color=("green", "#22c55e"),
        )
        task["name"].configure(text=name)
        self.add_log("success", f"Completed: {name} ({total} files)")

        # Add to history
        self._add_to_history(result)

    def _error_task(self, task_id: str, error: str):
        task = self._tasks.get(task_id)
        if not task:
            return
        task["done"] = True
        task["status"].configure(
            text=f"Error: {error}",
            text_color=("red", "#ef4444"),
        )
        self.add_log("error", f"Download failed: {error}")

    def _clear_completed(self):
        to_remove = []
        for tid, task in self._tasks.items():
            if task["done"]:
                task["frame"].destroy()
                to_remove.append(tid)
        for tid in to_remove:
            del self._tasks[tid]
        if not self._tasks:
            self._empty_label.grid()

    def _add_to_history(self, result: dict):
        import json
        from app.config import HISTORY_FILE, CONFIG_DIR
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            history = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else []
        except (json.JSONDecodeError, TypeError):
            history = []
        entry = {
            "name": result.get("name", "Unknown"),
            "type": result.get("type", "unknown"),
            "total_files": result.get("total_files", 0),
            "timestamp": datetime.now().isoformat(),
        }
        history.insert(0, entry)
        if len(history) > 500:
            history = history[:500]
        HISTORY_FILE.write_text(json.dumps(history, indent=2))

    def add_log(self, level: str, message: str):
        self._log_text.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"success": "+", "error": "!", "warning": "?", "info": "*"}.get(level, "*")
        self._log_text.insert("end", f"[{timestamp}] [{prefix}] {message}\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")
