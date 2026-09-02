"""
FastMCP Server exposing Candidate Profile tools for the CareerOS ecosystem.
Reference: CONDUCTOR-CP-IP-v2.0 (Phase 4)
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional
from fastmcp import FastMCP

from candidate_profile.models import CandidateProfile
from candidate_profile.storage import CandidateProfileStore
from candidate_profile.concurrency import (
    CandidateProfilePatch,
    OwnershipViolationError,
    merge_candidate_profile,
)
from candidate_profile.projections import (
    to_application_view,
    to_gleaner_query,
    to_outreach_context,
    to_research_scope,
    to_resume_profile,
    to_usher_profile,
)

# Global store instance (configurable via create_mcp_server)
_store = CandidateProfileStore()

mcp = FastMCP(
    name="conductor-candidate-profile",
    instructions=(
        "FastMCP tool interface for CONDUCTOR Component #10 (Candidate Profile JSON). "
        "Provides canonical candidate identity, projections for agent nodes, "
        "anti-fabrication skill provenance checks, and ownership-gated state updates."
    ),
)


@mcp.tool()
def get_candidate_profile(candidate_id: str = "c1f72b9a-4c28-4e89-9a25-8321e06d9a10") -> Dict[str, Any]:
    """Retrieve full canonical CandidateProfile JSON by candidate_id."""
    profile = _store.get(candidate_id)
    if profile is None:
        return {"error": f"Candidate profile with id '{candidate_id}' not found."}
    return profile.model_dump(mode="json")


@mcp.tool()
def get_candidate_projection(
    candidate_id: str = "c1f72b9a-4c28-4e89-9a25-8321e06d9a10",
    projection_type: str = "align_resume",
) -> Dict[str, Any]:
    """Generate a thin, mechanical projection for a specific consumer component.

    Supported projection_type values:
    - 'align_resume' / 'resume_profile': Returns AlignResume ResumeProfile
    - 'gleaner' / 'gleaner_query' / 'search_criteria': Returns GleanerQuery
    - 'overture' / 'outreach_context': Returns OutreachContext for cold email
    - 'usher' / 'application_view': Returns ApplicationView for PDF auto-apply
    - 'usher_profile': Returns UsherCandidateProfile domain model
    - 'research' / 'research_scope': Returns ResearchScope
    """
    profile = _store.get(candidate_id)
    if profile is None:
        return {"error": f"Candidate profile with id '{candidate_id}' not found."}

    norm_type = projection_type.lower().strip()

    if norm_type in ("align_resume", "resume_profile", "resume"):
        return to_resume_profile(profile).model_dump(mode="json")
    elif norm_type in ("gleaner", "gleaner_query", "search_criteria", "gleaner"):
        return to_gleaner_query(profile).model_dump(mode="json")
    elif norm_type in ("overture", "outreach_context", "outreach", "cold_email"):
        return to_outreach_context(profile).model_dump(mode="json")
    elif norm_type in ("usher", "application_view", "auto_apply"):
        return to_application_view(profile).model_dump(mode="json")
    elif norm_type in ("usher_profile", "usher_internal"):
        return to_usher_profile(profile).model_dump(mode="json")
    elif norm_type in ("research", "research_scope", "research_agent"):
        return to_research_scope(profile).model_dump(mode="json")
    else:
        return {
            "error": (
                f"Unknown projection_type '{projection_type}'. "
                "Valid options: 'align_resume', 'gleaner', 'overture', 'usher', 'usher_profile', 'research'."
            )
        }


@mcp.tool()
def patch_candidate_section(
    candidate_id: str,
    writer_component: str,
    section: str,
    value: Any,
) -> Dict[str, Any]:
    """Apply an ownership-validated delta patch to a CandidateProfile section.

    Enforces strict field-ownership partitioning (ADR-CP-2, HG-4).
    Unauthorized mutations raise an OwnershipViolationError and are rejected.
    """
    profile = _store.get(candidate_id)
    if profile is None:
        return {"error": f"Candidate profile with id '{candidate_id}' not found."}

    try:
        patch = CandidateProfilePatch(
            writer_component=writer_component,
            section=section,
            value=value,
        )
        updated_profile = merge_candidate_profile(profile, patch)
        _store.put(updated_profile)

        return {
            "status": "success",
            "candidate_id": candidate_id,
            "updated_section": section,
            "last_writer_component": writer_component,
            "updated_at": updated_profile.profile_metadata.updated_at.isoformat(),
        }
    except OwnershipViolationError as err:
        return {
            "status": "error",
            "error_type": "OwnershipViolationError",
            "message": str(err),
            "writer_component": writer_component,
            "attempted_section": section,
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
        }


@mcp.tool()
def check_skill_provenance(
    candidate_id: str = "c1f72b9a-4c28-4e89-9a25-8321e06d9a10",
    skill_name: str = "Python",
) -> Dict[str, Any]:
    """Inspect anti-fabrication provenance and verification status for a specific skill."""
    profile = _store.get(candidate_id)
    if profile is None:
        return {"error": f"Candidate profile with id '{candidate_id}' not found."}

    target_name = skill_name.strip().lower()
    for skill in profile.skills:
        if skill.name.strip().lower() == target_name:
            return {
                "found": True,
                "skill_name": skill.name,
                "proficiency": skill.proficiency_self_assessed.value,
                "taxonomy_ref": skill.taxonomy_ref,
                "evidence_refs": skill.evidence_refs,
                "source_type": skill.source.source_type,
                "source_ref": skill.source.source_ref,
                "verified": skill.source.verified,
                "recorded_at": skill.source.recorded_at.isoformat(),
            }

    return {
        "found": False,
        "skill_name": skill_name,
        "message": f"Skill '{skill_name}' is not in candidate's verified record.",
    }


def create_mcp_server(store: Optional[CandidateProfileStore] = None) -> FastMCP:
    """Factory creating an MCP server instance with a custom storage backend."""
    global _store
    if store is not None:
        _store = store
    return mcp


def main() -> None:
    """CLI entrypoint to run the FastMCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
