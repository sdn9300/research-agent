"""
Adapters module for ATS platforms and router registry.
Provides concrete adapters for Naukri, Indeed, LinkedIn Easy Apply, Greenhouse, Lever, Workday, and GenericATS.
"""

from typing import Optional

from .base import BaseATSAdapter
from .generic import GenericATSAdapter
from .greenhouse import GreenhouseAdapter
from .indeed import IndeedAdapter
from .lever import LeverAdapter
from .linkedin import LinkedInEasyApplyAdapter
from .naukri import NaukriAdapter
from .workday import WorkdayAdapter
from ..schemas import ApplicationChannel

__all__ = [
    "BaseATSAdapter",
    "NaukriAdapter",
    "IndeedAdapter",
    "LinkedInEasyApplyAdapter",
    "GreenhouseAdapter",
    "LeverAdapter",
    "WorkdayAdapter",
    "GenericATSAdapter",
    "get_adapter_for_channel",
    "get_adapter_for_url",
]


def get_adapter_for_channel(channel: ApplicationChannel) -> Optional[BaseATSAdapter]:
    """Factory to instantiate the appropriate adapter for an ApplicationChannel."""
    if channel == ApplicationChannel.NAUKRI:
        return NaukriAdapter()
    elif channel == ApplicationChannel.INDEED:
        return IndeedAdapter()
    elif channel == ApplicationChannel.LINKEDIN_EASY_APPLY:
        return LinkedInEasyApplyAdapter()
    elif channel == ApplicationChannel.GENERIC_ATS_GREENHOUSE:
        return GreenhouseAdapter()
    elif channel == ApplicationChannel.GENERIC_ATS_LEVER:
        return LeverAdapter()
    elif channel == ApplicationChannel.GENERIC_ATS_WORKDAY:
        return WorkdayAdapter()
    elif channel == ApplicationChannel.GENERIC_ATS_UNKNOWN:
        return GenericATSAdapter()
    return None


def get_adapter_for_url(url: str, fallback_to_generic: bool = True) -> Optional[BaseATSAdapter]:
    """Inspects URL to route to the appropriate adapter, falling back to GenericATSAdapter if enabled."""
    url_lower = url.lower()
    if "naukri.com" in url_lower:
        return NaukriAdapter()
    elif "indeed.com" in url_lower:
        return IndeedAdapter()
    elif "linkedin.com" in url_lower:
        return LinkedInEasyApplyAdapter()
    elif "greenhouse.io" in url_lower or "grnh.se" in url_lower:
        return GreenhouseAdapter()
    elif "lever.co" in url_lower:
        return LeverAdapter()
    elif "myworkdayjobs.com" in url_lower or "workday.com" in url_lower:
        return WorkdayAdapter()

    if fallback_to_generic:
        return GenericATSAdapter()

    return None
