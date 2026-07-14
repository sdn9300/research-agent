from __future__ import annotations

import re
from typing import Any

from graph.state import ResearchAgentState
from schemas.company_brief import CompanyBrief


def _token_set(value: str) -> set[str]:
    return {token for token in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,}", value.lower())}


def _citation_lookup(state: ResearchAgentState) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for citation in state.draft_brief.get("citations", []) if state.draft_brief else []:
        if isinstance(citation, dict):
            lookup[str(citation.get("chunk_id", ""))] = citation
    return lookup


def _chunk_lookup(state: ResearchAgentState) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for chunk in state.retrieved_chunks:
        chunk_id = str(chunk.get("chunk_id", ""))
        if chunk_id:
            lookup[chunk_id] = chunk
    return lookup


def _supported_claim(claim: str, chunk_text: str) -> bool:
    claim_tokens = _token_set(claim)
    source_tokens = _token_set(chunk_text)
    if not claim_tokens or not source_tokens:
        return False
    overlap = len(claim_tokens & source_tokens)
    return overlap >= 2 or claim.lower() in chunk_text.lower()


def self_check(state: ResearchAgentState) -> ResearchAgentState:
    """Validate that draft claims are grounded in retrieved chunk evidence."""

    issues: list[str] = []
    if not state.draft_brief:
        state.self_check_passed = False
        state.self_check_issues = ["missing draft brief"]
        return state

    citation_lookup = _citation_lookup(state)
    chunk_lookup = _chunk_lookup(state)

    cleaned_tech_signals: list[str] = []
    for signal in state.draft_brief.get("tech_signals", []):
        if not isinstance(signal, str):
            continue
        matched = False
        for chunk_id, chunk in chunk_lookup.items():
            if _supported_claim(signal, str(chunk.get("text", ""))):
                matched = True
                break
        if matched:
            cleaned_tech_signals.append(signal)
        else:
            issues.append(f"unsupported tech signal: {signal}")

    cleaned_recent_news: list[dict[str, str]] = []
    for item in state.draft_brief.get("recent_news", []):
        if not isinstance(item, dict):
            continue
        citation_id = str(item.get("citation_id", ""))
        headline = str(item.get("headline", ""))
        citation = next((c for c in citation_lookup.values() if c.get("citation_id") == citation_id), None)
        if not citation:
            issues.append(f"missing citation for recent news: {headline}")
            continue
        chunk = chunk_lookup.get(str(citation.get("chunk_id", "")))
        if not chunk or not _supported_claim(headline, str(chunk.get("text", ""))):
            issues.append(f"unsupported recent news: {headline}")
            continue
        cleaned_recent_news.append({"headline": headline, "citation_id": citation_id})

    summary = str(state.draft_brief.get("summary", "")).strip()
    summary_supported = False
    if summary:
        for chunk in chunk_lookup.values():
            if _supported_claim(summary, str(chunk.get("text", ""))):
                summary_supported = True
                break
    if not summary_supported:
        issues.append("unsupported summary")
        summary = f"Verified source material for {state.company_name} was found, but the draft summary was too weakly grounded."

    culture_notes = str(state.draft_brief.get("culture_notes", "")).strip()
    culture_supported = False
    if culture_notes:
        for chunk in chunk_lookup.values():
            if _supported_claim(culture_notes, str(chunk.get("text", ""))):
                culture_supported = True
                break
    if not culture_supported:
        issues.append("unsupported culture notes")
        culture_notes = f"Source material for {state.company_name} is limited, so culture inference remains cautious."

    citations = state.draft_brief.get("citations", [])
    cleaned_citations: list[dict[str, Any]] = []
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        chunk_id = str(citation.get("chunk_id", ""))
        source_url = str(citation.get("source_url", ""))
        citation_id = str(citation.get("citation_id", ""))
        if not chunk_id or not source_url or chunk_id not in chunk_lookup:
            issues.append(f"invalid citation: {citation_id or chunk_id}")
            continue
        cleaned_citations.append(
            {
                "citation_id": citation_id,
                "chunk_id": chunk_id,
                "source_url": source_url,
            }
        )

    if not cleaned_citations:
        issues.append("no valid citations survived self-check")

    cleaned_brief = {
        "company_name": state.draft_brief.get("company_name", state.company_name),
        "summary": summary,
        "tech_signals": cleaned_tech_signals,
        "recent_news": cleaned_recent_news,
        "culture_notes": culture_notes,
        "confidence_flags": list(state.draft_brief.get("confidence_flags", [])),
        "citations": cleaned_citations,
        "run_metadata": dict(state.draft_brief.get("run_metadata", {})),
    }
    if issues:
        cleaned_brief["confidence_flags"].append("self_check_reviewed")
        cleaned_brief["confidence_flags"].append("partial_output")

    state.self_check_issues = issues
    state.self_check_passed = len(issues) == 0
    state.draft_brief = cleaned_brief
    state.final_brief = CompanyBrief.model_validate(cleaned_brief)
    return state

