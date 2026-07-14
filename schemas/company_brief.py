from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    source_url: HttpUrl


class RecentNewsItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=1)
    citation_id: str = Field(min_length=1)


class RunMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_version: str = Field(min_length=1)
    latency_ms: int = Field(ge=0)
    token_cost_usd: float = Field(ge=0)
    tool_calls_used: int = Field(ge=0)


class CompanyBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    tech_signals: List[str] = Field(default_factory=list)
    recent_news: List[RecentNewsItem] = Field(default_factory=list)
    culture_notes: str = Field(min_length=1)
    confidence_flags: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    run_metadata: RunMetadata

