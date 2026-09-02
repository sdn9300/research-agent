"""
EdgeDash Subsystem 5: Deterministic Scoring Engine
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 5 (Rule 20: 100% Pure Arithmetic)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import Config, ScoringWeights


SENIORITY_BANDS = {
    "entry": 0,
    "junior": 0,
    "mid": 1,
    "senior": 2,
    "lead": 3,
    "principal": 3,
    "staff": 3,
}


def compute_skill_component(
    required_skills: List[str],
    nice_to_have: List[str],
    candidate_skills: Set[str],
) -> Tuple[float, List[str], List[str]]:
    """Compute S_skill = (matched_req + (1/3)*matched_nice) / (req + (1/3)*nice).
    Returns (score_ratio, matched_required, gap_skills).
    """
    req_set = {s.strip().lower() for s in required_skills if s.strip()}
    nice_set = {s.strip().lower() for s in nice_to_have if s.strip()}

    matched_req = [s for s in req_set if s in candidate_skills]
    matched_nice = [s for s in nice_set if s in candidate_skills]
    gaps = [s for s in req_set if s not in candidate_skills]

    numerator = len(matched_req) + (1.0 / 3.0) * len(matched_nice)
    denominator = len(req_set) + (1.0 / 3.0) * len(nice_set)

    if denominator == 0:
        return 0.5, matched_req, gaps

    s_skill = min(1.0, max(0.0, numerator / denominator))
    return s_skill, matched_req, gaps


def compute_seniority_component(
    job_seniority: str,
    job_years: int,
    candidate_years: int,
) -> float:
    """Compute S_seniority: exact (1.0), 1 band away (0.6), 2 bands (0.25), 3+ bands (0.0)."""
    # Infer candidate band from experience years
    if candidate_years <= 2:
        cand_band = 0
    elif candidate_years <= 5:
        cand_band = 1
    elif candidate_years <= 8:
        cand_band = 2
    else:
        cand_band = 3

    job_band = SENIORITY_BANDS.get(job_seniority.lower().strip(), 1)
    diff = abs(cand_band - job_band)

    if diff == 0:
        return 1.0
    elif diff == 1:
        return 0.6
    elif diff == 2:
        return 0.25
    else:
        return 0.0


def compute_location_component(
    location_str: Optional[str],
    remote_ok: bool,
    target_city: str,
) -> float:
    """Compute S_location: remote or target city (1.0), unknown (0.5), non-remote mismatch (0.1)."""
    if remote_ok:
        return 1.0

    if not location_str or not location_str.strip():
        return 0.5

    loc_lower = location_str.lower()
    if "remote" in loc_lower or "anywhere" in loc_lower or "hybrid" in loc_lower:
        return 1.0

    if target_city.lower().strip() in loc_lower:
        return 1.0

    return 0.1


def compute_recency_component(
    posted_at_iso: Optional[str],
    now: Optional[datetime] = None,
) -> Tuple[float, Optional[int]]:
    """Compute S_recency: linear decay from 1.0 (0 days) to 0.0 (30 days). Default 0.5 for null."""
    if not posted_at_iso:
        return 0.5, None

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    try:
        dt_posted = datetime.fromisoformat(posted_at_iso)
        if dt_posted.tzinfo is None:
            dt_posted = dt_posted.replace(tzinfo=timezone.utc)

        days_ago = max(0, (now - dt_posted).total_seconds() / 86400.0)
        days_int = int(days_ago)

        if days_ago >= 30.0:
            return 0.0, days_int
        return max(0.0, 1.0 - (days_ago / 30.0)), days_int
    except Exception:
        return 0.5, None


def score_listing(
    extracted_facts: Dict[str, Any],
    listing_meta: Dict[str, Any],
    config: Config,
    now: Optional[datetime] = None,
) -> Tuple[int, str, Dict[str, Any]]:
    """Score a job listing deterministically.
    Returns (fit_score: 0-100, fit_reason: str, components: dict).
    """
    candidate_skills = {s.lower().strip() for s in config.my_skills}
    weights = config.weights

    # 1. Skill Component
    s_skill, matched_req, gaps = compute_skill_component(
        extracted_facts.get("required_skills", []),
        extracted_facts.get("nice_to_have", []),
        candidate_skills,
    )

    # 2. Seniority Component
    s_seniority = compute_seniority_component(
        extracted_facts.get("seniority", "mid"),
        extracted_facts.get("years_required", 2),
        config.experience_years,
    )

    # 3. Location Component
    s_location = compute_location_component(
        listing_meta.get("location"),
        extracted_facts.get("remote_ok", False),
        config.target_city,
    )

    # 4. Recency Component
    s_recency, days_ago = compute_recency_component(
        listing_meta.get("posted_at"),
        now=now,
    )

    # Total Weighted Score
    total_raw = (
        weights.skill * s_skill
        + weights.seniority * s_seniority
        + weights.location * s_location
        + weights.recency * s_recency
    )

    # Normalize by sum of weights in case weights don't sum to exactly 1.0
    weight_sum = weights.skill + weights.seniority + weights.location + weights.recency
    if weight_sum > 0:
        total_raw = total_raw / weight_sum

    final_score = int(round(total_raw * 100))
    final_score = max(0, min(100, final_score))

    # Construct deterministic reason string
    total_req_count = len(extracted_facts.get("required_skills", []))
    req_str = f"{len(matched_req)}/{total_req_count} required skills" if total_req_count > 0 else "skills evaluated"
    sen_str = "seniority fits" if s_seniority >= 0.6 else "seniority stretch"
    loc_str = "remote/local" if s_location >= 0.9 else "location mismatch"
    rec_str = f"posted {days_ago}d ago" if days_ago is not None else "recent"

    reason_parts = [req_str, sen_str, loc_str, rec_str]
    if gaps:
        reason_parts.append(f"gap: {', '.join(gaps[:3])}")

    fit_reason = " · ".join(reason_parts)

    components = {
        "s_skill": round(s_skill, 3),
        "s_seniority": round(s_seniority, 3),
        "s_location": round(s_location, 3),
        "s_recency": round(s_recency, 3),
        "matched_required": matched_req,
        "gaps": gaps,
        "days_ago": days_ago,
    }

    return final_score, fit_reason, components
