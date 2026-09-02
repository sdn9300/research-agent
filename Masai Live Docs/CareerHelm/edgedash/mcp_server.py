"""
FastMCP Server exposing EdgeDash Market Intelligence tools for CareerOS.
Reference: CAREEROS-ARCH-v2.2 §5 (FastMCP Tool Mesh)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastmcp import FastMCP

from .config import Config, load_config
from .storage import Storage
from .orchestrator import Orchestrator
from .query.tools import (
    tool_best_matches,
    tool_top_gaps,
    tool_gap_detail,
    tool_companies_hiring,
    tool_skill_demand,
)
from .query.ask import ask

_config = load_config()
_storage = Storage(_config.db_path)
_orchestrator = Orchestrator(_config, _storage)

mcp = FastMCP(
    name="conductor-edgedash-intel",
    instructions=(
        "FastMCP tool interface for CareerOS Component (EdgeDash Core Engine & Market Discovery). "
        "Provides real-time job match retrieval, skill gap opportunity cost analysis, "
        "autonomous scraping cycle execution, and natural language market queries."
    ),
)


@mcp.tool()
def get_best_job_matches(limit: int = 10, min_score: int = 60) -> List[Dict[str, Any]]:
    """Retrieve top matched job opportunities scored above min_score."""
    return tool_best_matches(_storage, limit=limit, min_score=min_score)


@mcp.tool()
def get_skill_gap_analysis(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve top skill gaps ranked by weighted Opportunity Cost."""
    return tool_top_gaps(_storage, limit=limit)


@mcp.tool()
def get_skill_drilldown(skill: str) -> Dict[str, Any]:
    """Retrieve opportunity cost details and sample blocked jobs for a specific skill."""
    return tool_gap_detail(_storage, skill=skill)


@mcp.tool()
def get_companies_hiring(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve top hiring companies with open postings and average fit scores."""
    return tool_companies_hiring(_storage, limit=limit)


@mcp.tool()
def run_discovery_cycle(force_agent: Optional[str] = None) -> Dict[str, Any]:
    """Trigger an autonomous scraping, scoring, and gap analysis cycle."""
    return _orchestrator.run_cycle(force_agent=force_agent)


@mcp.tool()
def query_market_intel(question: str) -> Dict[str, Any]:
    """Ask a natural language question about jobs, skills, and market demand."""
    return ask(question, _storage)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
