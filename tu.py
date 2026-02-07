"""Standalone token extraction utility.

Delegates to the amar package for the actual extraction logic.
Can still be run directly: python tu.py
"""

import os
import sys

script_dir = os.path.dirname(os.path.realpath(__file__))

try:
    from amar.api.token import extract_token_with_selenium

    print("Extracting token from Apple Music...")
    token = extract_token_with_selenium(script_dir)
    if token:
        print(f"Token saved to {os.path.join(script_dir, 'token.txt')}")
    else:
        print("Failed to extract developer token.")
        sys.exit(1)
except ImportError:
    # Fallback if amar package isn't available - use original logic
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait

    token_path = os.path.join(script_dir, "token.txt")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://music.apple.com")
        token = WebDriverWait(driver, 15).until(
            lambda d: d.execute_script(
                "try { return MusicKit.getInstance().developerToken; } "
                "catch(e) { return null; }"
            )
        )

        if token:
            with open(token_path, "w") as f:
                f.write(token)
            print(f"Token saved to {token_path}")
        else:
            print("Failed to extract developer token.")
    finally:
        driver.quit()
except RuntimeError as e:
    print(f"Error: {e}")
    sys.exit(1)
