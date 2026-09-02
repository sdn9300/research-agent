"""
Tests for EdgeDash Storage Layer & Deduplication (Subsystem 2)
"""
import pytest
from edgedash.storage import Storage, compute_listing_id, compute_desc_hash


def test_deduplication_via_stable_hash(temp_db):
    """Rule 3 / Week 1 Class 1: Run 1 inserts N, Run 2 with identical listings returns 0 new."""
    batch_1 = [
        {"title": "MLE 1", "company": "Acme", "url": "https://example.com/1", "source": "test", "description": "desc 1"},
        {"title": "MLE 2", "company": "Beta", "url": "https://example.com/2", "source": "test", "description": "desc 2"},
    ]

    # Run 1: Both inserted
    new_count_1 = temp_db.upsert_listings(batch_1)
    assert new_count_1 == 2

    # Run 2: Exact same listings -> 0 new
    new_count_2 = temp_db.upsert_listings(batch_1)
    assert new_count_2 == 0

    # Run 3: 1 existing + 1 new -> 1 new
    batch_3 = [
        {"title": "MLE 1", "company": "Acme", "url": "https://example.com/1", "source": "test", "description": "desc 1"},
        {"title": "MLE 3", "company": "Gamma", "url": "https://example.com/3", "source": "test", "description": "desc 3"},
    ]
    new_count_3 = temp_db.upsert_listings(batch_3)
    assert new_count_3 == 1


def test_extraction_cache_roundtrip(temp_db):
    desc = "Looking for Senior Engineer with Python, Docker, Kubernetes."
    d_hash = compute_desc_hash(desc)

    # Empty cache initially
    assert temp_db.get_cached_extraction(d_hash) is None

    # Write cache
    facts = {"required_skills": ["python", "docker"], "seniority": "senior", "remote_ok": True}
    temp_db.set_cached_extraction(d_hash, facts)

    # Read back
    retrieved = temp_db.get_cached_extraction(d_hash)
    assert retrieved is not None
    assert retrieved["seniority"] == "senior"
    assert "docker" in retrieved["required_skills"]


def test_scoring_updates_and_queries(temp_db):
    batch = [
        {"title": "ML Eng", "company": "OpenAI", "url": "https://openai.com/1", "source": "test", "description": "desc"},
    ]
    temp_db.upsert_listings(batch)

    unscored = temp_db.get_unscored_listings()
    assert len(unscored) == 1
    listing_id = unscored[0]["id"]

    temp_db.update_listing_score(
        listing_id=listing_id,
        fit_score=85,
        fit_reason="4/5 skills · remote",
        components={"s_skill": 0.8},
    )

    scored = temp_db.get_all_scored_listings()
    assert len(scored) == 1
    assert scored[0]["fit_score"] == 85
    assert scored[0]["fit_reason"] == "4/5 skills · remote"
    assert len(temp_db.get_unscored_listings()) == 0
