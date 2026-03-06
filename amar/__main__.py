"""AMAR entry point - supports both CLI and GUI modes."""

import asyncio
import os
import sys
import threading


def _extract_token_with_splash(base_path):
    """Show a splash window while extracting the token via Selenium.

    Returns True if a token was successfully extracted, False otherwise.
    """
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("AMAR - Initializing")
    root.geometry("420x180")
    root.resizable(False, False)
    root.configure(bg="#1e1e1e")

    # Center the window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 210
    y = (root.winfo_screenheight() // 2) - 90
    root.geometry(f"420x180+{x}+{y}")

    # Use clam theme for styling
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("TFrame", background="#1e1e1e")
    style.configure("TLabel", background="#1e1e1e", foreground="#d4d4d4")
    style.configure(
        "Horizontal.TProgressbar",
        background="#e8555d", troughcolor="#2d2d2d", bordercolor="#3c3c3c",
    )

    frame = ttk.Frame(root, padding=20)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        frame, text="AMAR", font=("Segoe UI", 18, "bold"),
    ).pack(pady=(0, 5))

    status_var = tk.StringVar(value="No token found. Extracting automatically...")
    ttk.Label(
        frame, textvariable=status_var, font=("Segoe UI", 10),
    ).pack(pady=(0, 10))

    progress = ttk.Progressbar(frame, mode="indeterminate", length=360)
    progress.pack(pady=(0, 10))
    progress.start(15)

    detail_var = tk.StringVar(value="Starting headless browser...")
    ttk.Label(
        frame, textvariable=detail_var, font=("Segoe UI", 8),
        foreground="#858585",
    ).pack()

    result = {"success": False, "error": None}

    def _run_extraction():
        try:
            detail_var.set("Connecting to music.apple.com...")
            from .api.token import extract_token_with_selenium
            token = extract_token_with_selenium(base_path)
            if token:
                result["success"] = True
                status_var.set("Token extracted successfully!")
                detail_var.set("Launching AMAR...")
            else:
                result["error"] = "Extraction returned no token."
                status_var.set("Token extraction failed.")
                detail_var.set("Please place token.txt in the AMAR directory.")
        except Exception as e:
            result["error"] = str(e)
            status_var.set("Token extraction failed.")
            detail_var.set(str(e)[:80])

        # Close the splash after a short delay so user can read the status
        root.after(1500 if result["success"] else 4000, root.destroy)

    thread = threading.Thread(target=_run_extraction, daemon=True)
    thread.start()

    root.mainloop()
    thread.join(timeout=5)

    return result["success"]


def main():
    base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    # Handle --extract-token before loading/checking token
    if "--extract-token" in sys.argv:
        from .api.token import extract_token_with_selenium
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
        return

    from .config import AMARConfig
    config = AMARConfig.load(base_path)

    # If no token, try auto-extraction (GUI) or show error (CLI)
    if not config.token:
        is_gui = "--gui" in sys.argv

        if is_gui:
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
                        "Please place a valid token.txt file in the AMAR\n"
                        "directory and try again.\n\n"
                        "Or run: python -m amar --extract-token",
                    )
                    root.destroy()
                except Exception:
                    pass
                sys.exit(1)

            # Reload config now that token.txt should exist
            config = AMARConfig.load(base_path)
            if not config.token:
                sys.exit(1)
        else:
            # CLI mode — just print a message
            print("  [X] No token found. Run with --extract-token first, or place token.txt in the AMAR directory.")
            print("  You can also extract a token using: python -m amar --extract-token")
            sys.exit(1)

    if "--gui" in sys.argv:
        from .gui.app import AMARApp
        app = AMARApp(config)
        app.run()
    else:
        from .cli.menu import run_cli
        asyncio.run(run_cli(config))


if __name__ == "__main__":
    main()
