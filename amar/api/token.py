"""Token management for Apple Music API."""

import os
from typing import Optional


def load_token(base_path: str) -> Optional[str]:
    """Load the developer token from token.txt.

    Returns the token string or None if not found.
    """
    token_path = os.path.join(base_path, "token.txt")
    try:
        with open(token_path, "r") as f:
            token = f.read().strip()
        return token if token else None
    except OSError:
        return None


def save_token(base_path: str, token: str) -> None:
    """Save a developer token to token.txt."""
    token_path = os.path.join(base_path, "token.txt")
    with open(token_path, "w") as f:
        f.write(token)


def extract_token_with_selenium(base_path: str) -> Optional[str]:
    """Extract the Apple Music developer token using Selenium.

    Uses WebDriverWait instead of a fixed sleep for faster and more
    reliable extraction.

    Returns the token string or None on failure.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        raise RuntimeError(
            "Selenium is not installed. Install with: pip install selenium"
        )

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get("https://music.apple.com")

        # Wait for MusicKit to initialize (up to 15 seconds)
        token = WebDriverWait(driver, 15).until(
            lambda d: d.execute_script(
                "try { return MusicKit.getInstance().developerToken; } "
                "catch(e) { return null; }"
            )
        )

        if token:
            save_token(base_path, token)
            return token
        return None
    except Exception as e:
        raise RuntimeError(f"Failed to extract token: {e}")
    finally:
        if driver:
            driver.quit()
