"""
Tests for EdgeDash Query Tools & Safe NLP Interface (Subsystem 9)
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 4 Class 7
"""
import pytest
from edgedash.storage import Storage
from edgedash.query.tools import (
    tool_best_matches,
    tool_companies_hiring,
    tool_top_gaps,
    tool_listing_count,
    tool_skill_demand,
)
from edgedash.query.ask import ask, route_query


@pytest.fixture
def populated_db(temp_db):
    listings = [
        {"title": "MLE 1", "company": "OpenAI", "url": "https://openai.com/1", "source": "test", "description": "Python, Docker", "location": "Remote"},
        {"title": "MLE 2", "company": "OpenAI", "url": "https://openai.com/2", "source": "test", "description": "PyTorch, FastAPI", "location": "Remote"},
        {"title": "Dev 3", "company": "Stripe", "url": "https://stripe.com/1", "source": "test", "description": "Ruby, PostgreSQL", "location": "Bengaluru"},
    ]
    temp_db.upsert_listings(listings)
    unscored = temp_db.get_unscored_listings()
    for i, u in enumerate(unscored):
        temp_db.update_listing_score(u["id"], fit_score=70 + i * 10, fit_reason="Good match", components={})
    return temp_db


def test_tool_best_matches(populated_db):
    matches = tool_best_matches(populated_db, limit=5, min_score=60)
    assert len(matches) == 3
    assert matches[0]["fit_score"] >= matches[1]["fit_score"]


def test_tool_companies_hiring(populated_db):
    companies = tool_companies_hiring(populated_db)
    assert len(companies) == 2
    assert companies[0]["company"] == "OpenAI"
    assert companies[0]["posting_count"] == 2


def test_tool_listing_count(populated_db):
    counts = tool_listing_count(populated_db)
    assert counts["total_listings"] == 3
    assert counts["scored_listings"] == 3


def test_query_routing():
    tool, params = route_query("What are my best job matches?")
    assert tool == "best_matches"

    tool, params = route_query("Which companies are hiring?")
    assert tool == "companies_hiring"

    tool, params = route_query("What are my top skill gaps?")
    assert tool == "top_gaps"


def test_ask_out_of_scope_refusal(populated_db):
    res = ask("Should I take a pay cut for this job?", populated_db)
    assert res["status"] == "refused"
    assert "I can only answer questions about the job listings" in res["answer"]


def test_ask_valid_query(populated_db):
    res = ask("Show me the top matching jobs", populated_db)
    assert res["status"] == "answered"
    assert "Found" in res["answer"]
    assert res["tool_used"] == "best_matches"
