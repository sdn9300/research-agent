"""
Configuration management and constants for Usher.
Loads settings from config.yaml with fallback to safe defaults.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

from .schemas import SubmissionMode


class BrowserConfig(BaseModel):
    headless: bool = True
    slow_mo_ms: int = 100
    timeout_ms: int = 30000
    viewport_width: int = 1280
    viewport_height: int = 800


class RateLimitsConfig(BaseModel):
    max_attempts_per_session: int = 15
    cooldown_seconds: int = 300
    max_consecutive_failures: int = 3


class GroqConfig(BaseModel):
    light_model: str = "llama-3.1-8b-instant"
    heavy_model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.2


class GraduationConfig(BaseModel):
    state_file: str = "attempts/graduation_state.json"
    default_threshold: int = 10
    platform_thresholds: Dict[str, int] = Field(
        default_factory=lambda: {
            "naukri": 10,
            "indeed": 10,
            "linkedin_easy_apply": 15,
        }
    )


class RetentionConfig(BaseModel):
    max_screenshot_age_days: int = 30
    max_attempt_log_age_days: int = 90
    auto_cleanup_enabled: bool = True


class HealthCheckConfig(BaseModel):
    timeout_ms: int = 10000
    mock_dom_check_enabled: bool = True


class UsherConfig(BaseModel):
    app_name: str = "Usher - PDF Auto-Apply Agent"
    version: str = "1.0.0"
    default_submission_mode: SubmissionMode = SubmissionMode.DRAFT
    confidence_threshold: float = 0.85
    platform_priority: List[str] = Field(
        default_factory=lambda: [
            "naukri",
            "indeed",
            "linkedin_easy_apply",
            "generic_ats_greenhouse",
            "generic_ats_lever",
            "generic_ats_workday",
            "generic_ats_unknown",
        ]
    )
    excluded_platforms: List[str] = Field(default_factory=list)
    session_storage_dir: str = "sessions"
    attempts_dir: str = "attempts"
    screenshots_dir: str = "attempts/screenshots"
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    rate_limits: RateLimitsConfig = Field(default_factory=RateLimitsConfig)
    graduation: GraduationConfig = Field(default_factory=GraduationConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    health_check: HealthCheckConfig = Field(default_factory=HealthCheckConfig)
    groq: GroqConfig = Field(default_factory=GroqConfig)

    # Base workspace directory
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)

    @property
    def full_sessions_dir(self) -> Path:
        p = self.base_dir / self.session_storage_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def full_attempts_dir(self) -> Path:
        p = self.base_dir / self.attempts_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def full_screenshots_dir(self) -> Path:
        p = self.base_dir / self.screenshots_dir
        p.mkdir(parents=True, exist_ok=True)
        return p


def load_config(config_path: Optional[Path] = None) -> UsherConfig:
    """Load configuration from config.yaml or return defaults."""
    project_root = Path(__file__).resolve().parent.parent
    path = config_path or (project_root / "config.yaml")

    if not path.exists():
        return UsherConfig(base_dir=project_root)

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

        # Handle nested browser viewport
        browser_data = raw_data.get("browser", {})
        if "viewport" in browser_data:
            vp = browser_data.pop("viewport")
            browser_data["viewport_width"] = vp.get("width", 1280)
            browser_data["viewport_height"] = vp.get("height", 800)

        raw_data["base_dir"] = project_root
        return UsherConfig(**raw_data)
    except Exception:
        return UsherConfig(base_dir=project_root)


# Global singleton instance
config: UsherConfig = load_config()
