"""Standalone launcher for PyInstaller exe builds.

This file uses absolute imports (not relative) so it works both
when run as a script and when bundled by PyInstaller.

On startup, checks for token.txt. If missing, shows a splash window
and extracts the token via Selenium automatically.
"""

import asyncio
import os
import sys
import threading


def _get_base_path():
    """Get the base path - exe directory when frozen, script directory otherwise."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.realpath(__file__))


def _extract_token_with_splash(base_path):
    """Show an Apple HIG styled splash window while extracting the token.

    Returns True if a token was successfully extracted, False otherwise.
    """
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("AMAR")
    root.geometry("460x200")
    root.resizable(False, False)
    root.configure(bg="#1C1C1E")

    # Set window icon
    ico_candidates = [os.path.join(base_path, "Icon.ico")]
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', base_path)
        ico_candidates.insert(0, os.path.join(meipass, "Icon.ico"))
    for ico_path in ico_candidates:
        if os.path.isfile(ico_path):
            try:
                root.iconbitmap(ico_path)
            except Exception:
                pass
            break

    # Center on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 230
    y = (root.winfo_screenheight() // 2) - 100
    root.geometry(f"460x200+{x}+{y}")

    # Apple HIG dark theme
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("TFrame", background="#1C1C1E")
    style.configure("TLabel", background="#1C1C1E", foreground="#FFFFFF", font=("Segoe UI", 10))
    style.configure(
        "Horizontal.TProgressbar",
        background="#FC3C44", troughcolor="#3A3A3C", bordercolor="#2C2C2E",
    )

    frame = ttk.Frame(root, padding=24)
    frame.pack(fill=tk.BOTH, expand=True)

    # Title in Apple Music red
    ttk.Label(
        frame, text="AMAR", font=("Segoe UI", 22, "bold"),
        foreground="#FC3C44",
    ).pack(pady=(0, 4))

    status_var = tk.StringVar(value="No token found. Extracting automatically...")
    ttk.Label(frame, textvariable=status_var).pack(pady=(0, 12))

    progress = ttk.Progressbar(frame, mode="indeterminate", length=400)
    progress.pack(pady=(0, 12))
    progress.start(15)

    detail_var = tk.StringVar(value="Starting headless browser...")
    ttk.Label(
        frame, textvariable=detail_var, font=("Segoe UI", 8),
        foreground="#98989D",
    ).pack()

    result = {"success": False, "error": None}

    def _run_extraction():
        try:
            detail_var.set("Connecting to music.apple.com...")
            from amar.api.token import extract_token_with_selenium
            token = extract_token_with_selenium(base_path)
            if token:
                result["success"] = True
                status_var.set("Token extracted successfully!")
                detail_var.set("Launching AMAR...")
            else:
                result["error"] = "Extraction returned no token."
                status_var.set("Token extraction failed.")
                detail_var.set("Please place token.txt next to AMAR.exe manually.")
        except Exception as e:
            result["error"] = str(e)
            status_var.set("Token extraction failed.")
            detail_var.set(str(e)[:80])

        root.after(1500 if result["success"] else 4000, root.destroy)

    thread = threading.Thread(target=_run_extraction, daemon=True)
    thread.start()

    root.mainloop()
    thread.join(timeout=5)

    return result["success"]


def main():
    base_path = _get_base_path()

    from amar.config import AMARConfig
    config = AMARConfig.load(base_path)

    # If no token, try to extract it automatically with a splash screen
    if not config.token:
        success = _extract_token_with_splash(base_path)
        if not success:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "AMAR - No Token",
                    "Could not extract a token automatically.\n\n"
                    "Please place a valid token.txt file in the same\n"
                    "directory as AMAR.exe and try again.\n\n"
                    "You can get a token by visiting music.apple.com\n"
                    "and extracting it from the browser developer tools.",
                )
                root.destroy()
            except Exception:
                pass
            sys.exit(1)

        # Reload config now that token.txt should exist
        config = AMARConfig.load(base_path)
        if not config.token:
            sys.exit(1)

    if "--gui" in sys.argv or getattr(sys, 'frozen', False):
        # Default to GUI when running as exe
        from amar.gui.app import AMARApp
        app = AMARApp(config)
        app.run()
    elif "--extract-token" in sys.argv:
        from amar.api.token import extract_token_with_selenium
        try:
            print("  Extracting token from Apple Music...")
            token = extract_token_with_selenium(base_path)
            if token:
                print(f"  [OK] Token saved to {os.path.join(base_path, 'token.txt')}")
            else:
                print("  [X] Failed to extract token.")
                sys.exit(1)
        except RuntimeError as e:
            print(f"  [X] {e}")
            sys.exit(1)
    else:
        from amar.cli.menu import run_cli
        asyncio.run(run_cli(config))


if __name__ == "__main__":
    main()
