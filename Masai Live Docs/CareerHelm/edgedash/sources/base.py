"""
EdgeDash Source Plugin Layer: Base & Registry
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 3
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Type

SOURCES: Dict[str, Type[BaseSource]] = {}


def register(name: str) -> Callable[[Type[BaseSource]], Type[BaseSource]]:
    """Decorator to register a job source plugin."""
    def decorator(cls: Type[BaseSource]) -> Type[BaseSource]:
        SOURCES[name.lower().strip()] = cls
        cls.source_name = name.lower().strip()
        return cls
    return decorator


class BaseSource(ABC):
    """Abstract base class for all job board source adapters."""
    source_name: str = "base"

    @abstractmethod
    def fetch(self, role: str, city: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch raw job postings. Returns a list of dicts with canonical fields:
        title, company, location, url, description, source, posted_at.
        """
        pass
