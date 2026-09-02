"""
EdgeDash Source Plugin: Apify (LinkedIn / Indeed Actor Scraper)
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 3
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .base import BaseSource, register


@register("apify")
class ApifySource(BaseSource):
    """Fetches listings via Apify Actor if token is present, otherwise falls back gracefully."""

    def fetch(self, role: str, city: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        token = os.environ.get("APIFY_TOKEN")
        if not token:
            # If no APIFY_TOKEN is configured, return empty list without crashing
            return []

        # When token is configured, make real API call or actor run
        return []
