"""Token extraction and management for Apple Music API."""

import asyncio
from typing import Optional

from app.config import AMARConfig


async def extract_token_selenium() -> Optional[str]:
    """Extract Apple Music developer token using Selenium.

    Navigates to music.apple.com and extracts the JWT token
    from the page's JavaScript context.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        def _extract():
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--log-level=3")

            driver = webdriver.Chrome(options=options)
            try:
                driver.get("https://music.apple.com/us/browse")
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "audio"))
                )

                token = driver.execute_script("""
                    const scripts = document.querySelectorAll('script[type="module"]');
                    for (const script of scripts) {
                        const src = script.src;
                        if (src) {
                            const xhr = new XMLHttpRequest();
                            xhr.open('GET', src, false);
                            xhr.send();
                            const match = xhr.responseText.match(/eyJh[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+/);
                            if (match) return match[0];
                        }
                    }
                    return null;
                """)
                return token
            finally:
                driver.quit()

        return await asyncio.to_thread(_extract)
    except Exception as e:
        raise RuntimeError(f"Token extraction failed: {e}") from e


def validate_token(token: str) -> bool:
    """Basic validation that the token looks like a JWT."""
    if not token:
        return False
    parts = token.split(".")
    return len(parts) == 3 and token.startswith("eyJ")
