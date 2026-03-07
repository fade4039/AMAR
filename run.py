#!/usr/bin/env python3
"""AMAR v3 - Apple Music Asset Ripper

Launch the modern CustomTkinter desktop application.

Usage:
    python run.py              # Launch GUI
    python run.py --cli        # Launch CLI mode
    python run.py --extract    # Extract token via Selenium
"""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if "--extract" in sys.argv:
        import asyncio
        from app.core.token import extract_token_selenium, validate_token
        from app.config import AMARConfig

        print("AMAR v3 - Token Extractor")
        print("=" * 40)
        print("Launching headless browser to extract token from Apple Music...")

        async def _extract():
            try:
                token = await extract_token_selenium()
                if token and validate_token(token):
                    config = AMARConfig.load()
                    config.token = token
                    print(f"[OK] Token extracted and saved!")
                    print(f"     Token: {token[:20]}...{token[-10:]}")
                else:
                    print("[ERROR] Could not extract a valid token.")
                    print("        Make sure Chrome/Chromium is installed.")
                    sys.exit(1)
            except Exception as e:
                print(f"[ERROR] {e}")
                sys.exit(1)

        asyncio.run(_extract())

    elif "--cli" in sys.argv:
        import asyncio
        from app.config import AMARConfig
        from app.api.apple_music import AppleMusicClient
        from app.core.ripper import AssetRipper, ProgressCallback
        from app.core.utils import parse_apple_music_url

        config = AMARConfig.load()
        if not config.token:
            print("[ERROR] No token configured.")
            print("        Run: python run.py --extract")
            print("        Or manually place your JWT in ~/.amar/token.txt")
            sys.exit(1)

        async def run_cli():
            client = AppleMusicClient(config)
            cb = ProgressCallback()
            cb.on_log = lambda level, msg: print(f"  [{level.upper()}] {msg}")
            cb.on_progress = lambda tid, prog, status, detail: print(
                f"  [{int(prog*100):>3}%] {detail or status}"
            )
            ripper = AssetRipper(client, config, cb)

            print()
            print("AMAR v3 - Apple Music Asset Ripper")
            print("=" * 50)
            print(f"  Storefront: {config.storefront.upper()} ({config.storefront_name})")
            print(f"  Save Path:  {config.save_path}")
            print(f"  Token:      {'Active' if config.token else 'Missing'}")
            print("=" * 50)
            print()

            while True:
                print("  [1] Download from URL")
                print("  [2] Search catalog")
                print("  [3] View charts")
                print("  [4] Change storefront")
                print("  [0] Exit")
                print()
                choice = input("  > ").strip()

                if choice == "0":
                    break
                elif choice == "1":
                    url = input("  URL: ").strip()
                    parsed = parse_apple_music_url(url)
                    if not parsed:
                        print("  [ERROR] Invalid Apple Music URL\n")
                        continue
                    print(f"  Detected: {parsed['type']} ({parsed['storefront'].upper()})")
                    print()
                    try:
                        result = await ripper._rip_by_type(
                            parsed["type"], parsed["id"], parsed["storefront"], "cli",
                        )
                        print(f"\n  [DONE] {result.get('name', 'Unknown')} - {result.get('total_files', 0)} files\n")
                    except Exception as e:
                        print(f"\n  [ERROR] {e}\n")

                elif choice == "2":
                    term = input("  Search: ").strip()
                    if not term:
                        continue
                    try:
                        data = await client.search(term)
                        results = data.get("results", {})
                        for rtype in ("artists", "albums", "songs", "music-videos"):
                            items = results.get(rtype, {}).get("data", [])
                            if items:
                                print(f"\n  --- {rtype.upper()} ---")
                                for item in items[:10]:
                                    attrs = item.get("attributes", {})
                                    artist = attrs.get("artistName", "")
                                    name = attrs.get("name", "Unknown")
                                    display = f"{artist} - {name}" if artist else name
                                    print(f"  [{item['id']}] {display}")
                        print()
                    except Exception as e:
                        print(f"  [ERROR] {e}\n")

                elif choice == "3":
                    try:
                        data = await client.get_charts()
                        results = data.get("results", {})
                        for rtype in ("songs", "albums"):
                            charts = results.get(rtype, [])
                            if charts:
                                chart = charts[0]
                                print(f"\n  --- {chart.get('name', rtype.upper())} ---")
                                for i, item in enumerate(chart.get("data", [])[:20], 1):
                                    attrs = item.get("attributes", {})
                                    name = attrs.get("name", "?")
                                    artist = attrs.get("artistName", "")
                                    print(f"  {i:>3}. {artist} - {name}" if artist else f"  {i:>3}. {name}")
                        print()
                    except Exception as e:
                        print(f"  [ERROR] {e}\n")

                elif choice == "4":
                    sf = input(f"  Storefront code (current: {config.storefront}): ").strip().lower()
                    from app.config import STOREFRONTS
                    if sf in STOREFRONTS:
                        config.storefront = sf
                        config.save()
                        print(f"  [OK] Storefront set to {sf.upper()} ({STOREFRONTS[sf]})\n")
                    else:
                        print(f"  [ERROR] Unknown storefront: {sf}\n")

            await client.close()
            print("\n  Goodbye!\n")

        asyncio.run(run_cli())

    else:
        # Launch GUI
        try:
            import customtkinter
        except ImportError:
            print("[ERROR] customtkinter is not installed.")
            print("        Run: pip install customtkinter")
            sys.exit(1)

        from app.gui.app import AMARApp
        app = AMARApp()
        app.mainloop()


if __name__ == "__main__":
    main()
