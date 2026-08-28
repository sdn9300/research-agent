"""
Smoke and integration tests for PlaywrightSessionManager and browser lifecycle.
Verifies Phase 0 Playwright bootstrap requirements.
"""

import json
import tempfile
from pathlib import Path

from usher.browser import PlaywrightSessionManager
from usher.config import UsherConfig


def test_browser_session_lifecycle_and_screenshot():
    """Verify Playwright session launches headless, executes DOM query, and captures screenshot."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cfg = UsherConfig(
            base_dir=Path(temp_dir),
            session_storage_dir="test_sessions",
            screenshots_dir="test_screenshots",
        )
        session_mgr = PlaywrightSessionManager(cfg=cfg)

        with session_mgr.create_session(platform_name="naukri_test", headless=True) as (
            browser,
            context,
            page,
        ):
            # Navigate to dummy HTML
            test_html = """
            <!DOCTYPE html>
            <html>
            <head><title>Usher Auto Apply Test</title></head>
            <body>
                <h1>Application Form</h1>
                <input id="candidate-name" type="text" value="Soumyadeep Nath" />
                <button id="submit-btn">Apply Now</button>
            </body>
            </html>
            """
            page.set_content(test_html)

            # Verify page title and DOM content
            assert page.title() == "Usher Auto Apply Test"
            val = page.locator("#candidate-name").input_value()
            assert val == "Soumyadeep Nath"

            # Capture screenshot
            screenshot_path = session_mgr.capture_screenshot(
                page=page,
                attempt_id="smoke_test_001",
                suffix="form_view",
            )
            assert screenshot_path.exists()
            assert screenshot_path.stat().st_size > 0


def test_session_state_persistence():
    """Verify session manager saves and loads storage state JSON."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cfg = UsherConfig(
            base_dir=Path(temp_dir),
            session_storage_dir="test_sessions",
        )
        session_mgr = PlaywrightSessionManager(cfg=cfg)

        assert not session_mgr.has_saved_session("indeed")

        # Manually create mock session state
        session_file = session_mgr.get_session_path("indeed")
        session_file.write_text(
            json.dumps({"cookies": [{"name": "session_id", "value": "xyz123"}]}),
            encoding="utf-8",
        )

        assert session_mgr.has_saved_session("indeed")
