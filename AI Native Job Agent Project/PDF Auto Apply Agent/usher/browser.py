"""
Playwright browser lifecycle and persistent session management for Usher.
Handles isolated browser contexts, session-state persistence, and screenshot capture.
"""

import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Tuple

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from .config import UsherConfig, config as default_config

logger = logging.getLogger(__name__)


class PlaywrightSessionManager:
    """Manages browser lifecycle and per-platform session storage state."""

    def __init__(self, cfg: Optional[UsherConfig] = None):
        self.config = cfg or default_config

    def get_session_path(self, platform_name: str) -> Path:
        """Returns the local storage-state JSON file path for a platform."""
        safe_name = "".join(c for c in platform_name.lower() if c.isalnum() or c in ("-", "_"))
        return self.config.full_sessions_dir / f"{safe_name}_state.json"

    def has_saved_session(self, platform_name: str) -> bool:
        """Checks if a valid session state exists for the platform."""
        p = self.get_session_path(platform_name)
        return p.exists() and p.stat().st_size > 2

    def save_session(self, context: BrowserContext, platform_name: str) -> Path:
        """Saves current browser cookies/localStorage state to disk."""
        target_path = self.get_session_path(platform_name)
        context.storage_state(path=str(target_path))
        logger.info("[SessionManager] Saved session state for %s to %s", platform_name, target_path)
        return target_path

    @contextmanager
    def create_session(
        self,
        platform_name: Optional[str] = None,
        headless: Optional[bool] = None,
    ) -> Generator[Tuple[Browser, BrowserContext, Page], None, None]:
        """
        Launches a Chromium browser instance, attaches session state if available,
        and yields (browser, context, page).
        """
        is_headless = self.config.browser.headless if headless is None else headless
        session_file = self.get_session_path(platform_name) if platform_name else None

        with sync_playwright() as p:
            browser: Browser = p.chromium.launch(
                headless=is_headless,
                slow_mo=self.config.browser.slow_mo_ms,
            )

            context_kwargs = {
                "viewport": {
                    "width": self.config.browser.viewport_width,
                    "height": self.config.browser.viewport_height,
                },
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            }

            if session_file and session_file.exists() and session_file.stat().st_size > 2:
                logger.info("[SessionManager] Restoring session state for %s", platform_name)
                context_kwargs["storage_state"] = str(session_file)

            context: BrowserContext = browser.new_context(**context_kwargs)
            context.set_default_timeout(self.config.browser.timeout_ms)

            page: Page = context.new_page()

            try:
                yield browser, context, page
            finally:
                if platform_name and not is_headless:
                    try:
                        self.save_session(context, platform_name)
                    except Exception as e:
                        logger.warning("[SessionManager] Could not save session: %s", e)
                context.close()
                browser.close()

    def capture_screenshot(
        self,
        page: Page,
        attempt_id: str,
        suffix: str = "state",
    ) -> Path:
        """Captures page screenshot and saves to attempts/screenshots/."""
        filename = f"{attempt_id}_{suffix}.png"
        target_path = self.config.full_screenshots_dir / filename
        page.screenshot(path=str(target_path), full_page=True)
        logger.info("[SessionManager] Screenshot saved: %s", target_path)
        return target_path
