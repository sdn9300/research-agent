"""
EdgeDash Subsystem 9: Two-Stage Natural Language Query Pipeline
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 9
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple
from ..storage import Storage
from .tools import TOOL_REGISTRY


OUT_OF_SCOPE_REFUSAL = (
    "I can only answer questions about the job listings, skill gaps, companies hiring, "
    "and fit scores tracked in your EdgeDash database. "
    "Supported topics: 'best matches', 'top skill gaps', 'who is hiring', 'skill demand', 'listing count'."
)


def route_query(question: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Route natural language question to one of the 7 pre-written tools with clamped parameters."""
    q_lower = question.lower().strip()

    # Refusal checks for out of scope queries
    if any(k in q_lower for k in ["salary negotiation", "pay cut", "weather", "recipe", "stock price"]):
        return None, {}

    if any(k in q_lower for k in ["best", "match", "highest score", "fit", "top job"]):
        return "best_matches", {"limit": 10, "min_score": 60}

    if any(k in q_lower for k in ["who is hiring", "companies", "employers", "company"]):
        return "companies_hiring", {"limit": 10}

    if any(k in q_lower for k in ["gap", "missing skill", "opportunity cost", "what should i learn"]):
        return "top_gaps", {"limit": 10}

    if any(k in q_lower for k in ["how many", "count", "total job", "total listing", "volume"]):
        return "listing_count", {}

    if any(k in q_lower for k in ["trend", "history", "snapshots"]):
        return "trend", {}

    if "demand" in q_lower or "need" in q_lower or "require" in q_lower:
        # Extract potential skill word
        words = [w for w in q_lower.split() if w not in ["demand", "for", "is", "what", "the", "in", "of", "jobs"]]
        skill = words[-1] if words else "python"
        return "skill_demand", {"skill": skill}

    # Default to best matches
    return "best_matches", {"limit": 5, "min_score": 50}


def phrase_answer(tool_name: str, result_data: Any, question: str) -> str:
    """Format structured results into clear prose without hallucination."""
    if not result_data:
        return "No matching records found in your EdgeDash database."

    if tool_name == "best_matches":
        lines = [f"Found {len(result_data)} top job match(es):"]
        for j in result_data[:5]:
            lines.append(f"- **{j['title']}** at **{j['company']}** (Fit Score: {j['fit_score']}/100) — *{j.get('fit_reason', '')}*")
        return "\n".join(lines)

    elif tool_name == "companies_hiring":
        lines = ["Top companies currently hiring in your database:"]
        for c in result_data[:5]:
            lines.append(f"- **{c['company']}**: {c['posting_count']} opening(s) (Avg Fit Score: {round(c.get('avg_fit_score') or 0, 1)})")
        return "\n".join(lines)

    elif tool_name == "top_gaps":
        lines = ["Top skill gaps ranked by weighted Opportunity Cost:"]
        for g in result_data[:5]:
            lines.append(f"- **{g['skill'].title()}**: blocks {g['listings_blocked']} high-scoring jobs (Opportunity Cost: {g['opportunity_cost']})")
        return "\n".join(lines)

    elif tool_name == "listing_count":
        return f"Your EdgeDash database currently contains **{result_data['total_listings']}** total listings (**{result_data['scored_listings']}** scored)."

    elif tool_name == "skill_demand":
        return f"**{result_data['skill'].title()}** is required in **{result_data['demand_count']}** job(s) ({result_data['percentage_of_all_jobs']}% of all tracked positions)."

    return str(result_data)


def ask(question: str, storage: Storage) -> Dict[str, Any]:
    """Execute complete Natural Language Query flow with telemetry logging."""
    start_time = time.time()
    tool_name, params = route_query(question)

    if tool_name is None:
        duration_ms = int((time.time() - start_time) * 1000)
        storage.log_query(
            question=question,
            tool_used=None,
            params=None,
            status="refused",
            duration_ms=duration_ms,
        )
        return {
            "status": "refused",
            "answer": OUT_OF_SCOPE_REFUSAL,
            "data": None,
            "tool_used": None,
        }

    tool_fn = TOOL_REGISTRY.get(tool_name)
    if not tool_fn:
        return {"status": "error", "answer": f"Tool '{tool_name}' not found.", "data": None}

    raw_data = tool_fn(storage, **params)
    answer_text = phrase_answer(tool_name, raw_data, question)
    duration_ms = int((time.time() - start_time) * 1000)

    storage.log_query(
        question=question,
        tool_used=tool_name,
        params=params,
        status="answered",
        duration_ms=duration_ms,
    )

    return {
        "status": "answered",
        "answer": answer_text,
        "data": raw_data,
        "tool_used": tool_name,
        "duration_ms": duration_ms,
    }
