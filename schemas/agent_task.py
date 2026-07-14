from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from schemas.company_brief import CompanyBrief


class AgentTaskInputPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1)
    job_description: str | None = None


class AgentTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    agent_name: Literal["research_agent"] = "research_agent"
    input_payload: AgentTaskInputPayload
    status: Literal["pending", "running", "success", "failed", "retrying"]
    result: CompanyBrief | None = None
    retry_count: int = Field(ge=0, default=0)
    timestamp: datetime
