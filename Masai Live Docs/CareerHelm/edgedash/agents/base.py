"""
EdgeDash Subsystem 2: Agent Base Class & Protocol
Reference: EDGEDASH-CORE-ARCH-v1.0 §1
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    agent_name: str
    status: str  # ok | failed | partial | nothing_to_do
    records_touched: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    name: str = "base_agent"

    @abstractmethod
    def execute(self, config: Any, storage: Any, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute agent task and return structured result."""
        pass
