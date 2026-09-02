"""
Tests for EdgeDash FastMCP Tool Mesh (Subsystem FastMCP)
Reference: CAREEROS-ARCH-v2.2 §5
"""
import pytest
from edgedash.mcp_server import (
    get_best_job_matches,
    get_skill_gap_analysis,
    get_skill_drilldown,
    get_companies_hiring,
    run_discovery_cycle,
    query_market_intel,
)


def test_mcp_run_discovery_and_query_tools():
    # 1. Run discovery cycle with mock fetcher
    cycle_res = run_discovery_cycle()
    assert cycle_res["status"] in ("completed", "nothing_to_do")

    # 2. Get best job matches
    matches = get_best_job_matches(limit=5, min_score=0)
    assert isinstance(matches, list)

    # 3. Get skill gap analysis
    gaps = get_skill_gap_analysis(limit=5)
    assert isinstance(gaps, list)

    # 4. Get companies hiring
    companies = get_companies_hiring(limit=5)
    assert isinstance(companies, list)

    # 5. Query market intel NLP tool
    ans = query_market_intel("What are the best job matches?")
    assert ans["status"] in ("answered", "refused")
