from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.company_brief import CompanyBrief


class ResearchAgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    company_name: str
    job_description: str | None = None
    artifact_dir: str = "artifacts/research_agent"
    prompt_version: str = "v0.2.0"
    tool_call_budget: int = Field(default=6, ge=1)
    tool_calls_used: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    status: Literal["pending", "running", "success", "failed", "retrying"] = "pending"
    search_strategy: list[str] = Field(default_factory=list)
    search_results: list[dict[str, Any]] = Field(default_factory=list)
    scraped_documents: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_chunks: list[dict[str, Any]] = Field(default_factory=list)
    draft_brief: dict[str, Any] | None = None
    claim_annotations: list[dict[str, Any]] = Field(default_factory=list)
    final_brief: CompanyBrief | None = None
    self_check_passed: bool = False
    self_check_issues: list[str] = Field(default_factory=list)
    error: str | None = None

    @property
    def artifact_path(self) -> Path:
        return Path(self.artifact_dir)


class ResearchGraphResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: ResearchAgentState
    final_task_status: Literal["success", "failed"]

