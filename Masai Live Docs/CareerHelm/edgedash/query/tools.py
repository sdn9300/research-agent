"""
EdgeDash Subsystem 9: Safe Parameterized Query Tool Registry
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 9 (Rule 40: Zero Text-to-SQL)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from ..storage import Storage

TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {}


def register_tool(name: str):
    def decorator(fn: Callable[..., Any]):
        TOOL_REGISTRY[name] = fn
        return fn
    return decorator


@register_tool("best_matches")
def tool_best_matches(storage: Storage, limit: int = 10, min_score: int = 60) -> List[Dict[str, Any]]:
    """Retrieve highest-scoring job matches above min_score."""
    clamped_limit = max(1, min(50, limit))
    clamped_score = max(0, min(100, min_score))

    query = """
        SELECT id, title, company, location, url, fit_score, fit_reason, posted_at
        FROM listings
        WHERE fit_score >= ?
        ORDER BY fit_score DESC
        LIMIT ?
    """
    with storage.get_connection() as conn:
        cursor = conn.execute(query, (clamped_score, clamped_limit))
        return [dict(row) for row in cursor.fetchall()]


@register_tool("companies_hiring")
def tool_companies_hiring(storage: Storage, limit: int = 10) -> List[Dict[str, Any]]:
    """List companies with the highest number of active job postings."""
    clamped_limit = max(1, min(50, limit))
    query = """
        SELECT company, COUNT(*) as posting_count, AVG(fit_score) as avg_fit_score
        FROM listings
        GROUP BY company
        ORDER BY posting_count DESC, avg_fit_score DESC
        LIMIT ?
    """
    with storage.get_connection() as conn:
        cursor = conn.execute(query, (clamped_limit,))
        return [dict(row) for row in cursor.fetchall()]


@register_tool("top_gaps")
def tool_top_gaps(storage: Storage, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve top skill gaps ranked by weighted Opportunity Cost."""
    clamped_limit = max(1, min(50, limit))
    return storage.get_latest_skill_gaps(limit=clamped_limit)


@register_tool("gap_detail")
def tool_gap_detail(storage: Storage, skill: str) -> Dict[str, Any]:
    """Retrieve detailed opportunity cost and example listings for a single skill."""
    query = """
        SELECT * FROM skill_gaps
        WHERE LOWER(skill) = ?
        ORDER BY computed_at DESC
        LIMIT 1
    """
    with storage.get_connection() as conn:
        cursor = conn.execute(query, (skill.lower().strip(),))
        row = cursor.fetchone()
        if not row:
            return {"error": f"No gap record found for skill '{skill}'."}
        
        gap_data = dict(row)
        example_ids = [lid.strip() for lid in gap_data.get("example_ids", "").split(",") if lid.strip()]
        
        examples = []
        for lid in example_ids:
            item = storage.get_listing_by_id(lid)
            if item:
                examples.append({
                    "id": item["id"],
                    "title": item["title"],
                    "company": item["company"],
                    "fit_score": item["fit_score"],
                    "url": item["url"],
                })
        gap_data["example_listings"] = examples
        return gap_data


@register_tool("listing_count")
def tool_listing_count(storage: Storage) -> Dict[str, Any]:
    """Retrieve total count of fetched and scored listings."""
    with storage.get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) as total, COUNT(fit_score) as scored FROM listings")
        row = cursor.fetchone()
        return {"total_listings": row["total"], "scored_listings": row["scored"]}


@register_tool("trend")
def tool_trend(storage: Storage) -> List[Dict[str, Any]]:
    """Retrieve historical skill gap snapshots."""
    query = """
        SELECT snapshot_id, computed_at, COUNT(*) as gap_count, SUM(opportunity_cost) as total_opp_cost
        FROM skill_gaps
        GROUP BY snapshot_id
        ORDER BY computed_at DESC
        LIMIT 10
    """
    with storage.get_connection() as conn:
        cursor = conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]


@register_tool("skill_demand")
def tool_skill_demand(storage: Storage, skill: str) -> Dict[str, Any]:
    """Inspect occurrences and demand of a specific skill across listings."""
    query = "SELECT id, title, company, fit_score, description FROM listings"
    with storage.get_connection() as conn:
        cursor = conn.execute(query)
        rows = [dict(r) for r in cursor.fetchall()]

    import re
    pattern = r"\b" + re.escape(skill.lower().strip()) + r"\b"
    matched_listings = []
    for r in rows:
        desc = (r.get("description") or "").lower()
        if re.search(pattern, desc):
            matched_listings.append({
                "id": r["id"],
                "title": r["title"],
                "company": r["company"],
                "fit_score": r.get("fit_score"),
            })

    return {
        "skill": skill,
        "demand_count": len(matched_listings),
        "percentage_of_all_jobs": round(len(matched_listings) / len(rows) * 100, 1) if rows else 0.0,
        "sample_jobs": matched_listings[:5],
    }
