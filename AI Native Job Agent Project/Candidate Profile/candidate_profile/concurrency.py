"""
Concurrency, field ownership enforcement, and LangGraph reducer for Candidate Profile.
Reference: CONDUCTOR-CP-AD-v1.0 (Architecture Design §4, §8, ADR-CP-2, §11)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, ConfigDict, Field

from candidate_profile.models import CandidateProfile, HistoryRef
from candidate_profile.observability import record_ownership_violation


class OwnershipViolationError(Exception):
    """Raised when a component attempts to write into a section it does not own."""

    def __init__(self, writer_component: str, attempted_section: str) -> None:
        self.writer_component = writer_component
        self.attempted_section = attempted_section
        super().__init__(
            f"Ownership violation: Component '{writer_component}' is not authorized "
            f"to write to section '{attempted_section}'."
        )


# Strict field-ownership mapping as per Architecture Design §4
OWNERSHIP_MAP: Dict[str, Set[str]] = {
    "conductor_orchestrator": {"profile_metadata"},
    "bootstrap_manual": {"identity", "education", "skills", "experience", "preferences"},
    "align_resume": {"tailoring_history"},
    "overture": {"outreach_history"},
    "usher": {"application_history"},
    "sentiment_classifier": {"interaction_signals"},
    # Read-only consumers have no owned write sections
    "gleaner": set(),
    "research_agent": set(),
    "future_fit": set(),
    "memory_module": set(),
}

APPEND_ONLY_SECTIONS: Set[str] = {
    "tailoring_history",
    "outreach_history",
    "application_history",
    "interaction_signals",
}

ALL_SECTIONS: Set[str] = {
    "profile_metadata",
    "identity",
    "education",
    "skills",
    "experience",
    "preferences",
    "tailoring_history",
    "outreach_history",
    "application_history",
    "interaction_signals",
}


def normalize_component_name(name: str) -> str:
    """Normalize consumer component names/aliases to canonical keys."""
    cleaned = name.lower().replace("-", "_").replace(" ", "_")
    if "align" in cleaned:
        return "align_resume"
    if "overture" in cleaned or "cold_email" in cleaned:
        return "overture"
    if "usher" in cleaned or "auto_apply" in cleaned or "pdf_apply" in cleaned:
        return "usher"
    if "sentiment" in cleaned:
        return "sentiment_classifier"
    if "conductor" in cleaned or "orchestrator" in cleaned:
        return "conductor_orchestrator"
    if "bootstrap" in cleaned or "manual" in cleaned:
        return "bootstrap_manual"
    if "gleaner" in cleaned or "gleaner" in cleaned:
        return "gleaner"
    if "research" in cleaned:
        return "research_agent"
    if "future" in cleaned:
        return "future_fit"
    if "memory" in cleaned:
        return "memory_module"
    return cleaned


class CandidateProfilePatch(BaseModel):
    """Scoped delta submitted by an owning component to update CandidateProfile state."""
    model_config = ConfigDict(extra="forbid")

    writer_component: str
    section: str
    value: Any
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def merge_candidate_profile(
    current: Optional[CandidateProfile],
    patch: Union[CandidateProfilePatch, CandidateProfile, None],
) -> CandidateProfile:
    """LangGraph-compatible reducer enforcing strict single-writer section ownership.

    - Unauthorized write attempts raise OwnershipViolationError immediately (ADR-CP-2, HG-4).
    - Append-only history sections are concatenated commutatively by run_id (EC-CP-CONC-01).
    - profile_metadata.updated_at and last_writer_component are updated automatically.
    """
    if current is None:
        if isinstance(patch, CandidateProfile):
            return patch
        raise ValueError("Cannot apply CandidateProfilePatch to a null current state.")

    if patch is None:
        return current

    if isinstance(patch, CandidateProfile):
        return patch

    if not isinstance(patch, CandidateProfilePatch):
        raise TypeError(f"Invalid patch type: {type(patch).__name__}")

    # Validate section existence
    if patch.section not in ALL_SECTIONS:
        raise ValueError(f"Unknown CandidateProfile section: '{patch.section}'")

    # Enforce field-ownership partitioning (HG-4, ADR-CP-2)
    normalized_writer = normalize_component_name(patch.writer_component)
    allowed_sections = OWNERSHIP_MAP.get(normalized_writer, set())
    if patch.section not in allowed_sections:
        record_ownership_violation(component=patch.writer_component)
        raise OwnershipViolationError(
            writer_component=patch.writer_component,
            attempted_section=patch.section,
        )

    # Process section update
    if patch.section in APPEND_ONLY_SECTIONS:
        existing_list: List[HistoryRef] = list(getattr(current, patch.section))
        items_to_add = patch.value if isinstance(patch.value, list) else [patch.value]

        existing_run_ids = {h.run_id for h in existing_list}
        for item in items_to_add:
            if isinstance(item, dict):
                ref = HistoryRef.model_validate(item)
            elif isinstance(item, HistoryRef):
                ref = item
            else:
                raise TypeError(
                    f"Items for append-only section '{patch.section}' must be HistoryRef instances or dicts."
                )

            # Commutative append: avoid duplicate run_ids
            if ref.run_id not in existing_run_ids:
                existing_list.append(ref)
                existing_run_ids.add(ref.run_id)

        updated_val = existing_list
    else:
        updated_val = patch.value

    # Update metadata
    updated_metadata = current.profile_metadata.model_copy(
        update={
            "updated_at": patch.timestamp or datetime.now(timezone.utc),
            "last_writer_component": patch.writer_component,
        }
    )

    return current.model_copy(
        update={
            patch.section: updated_val,
            "profile_metadata": updated_metadata,
        }
    )
