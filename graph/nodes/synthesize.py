from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any

from graph.state import ResearchAgentState


def _best_chunk_text(state: ResearchAgentState) -> str:
    if state.retrieved_chunks:
        return str(state.retrieved_chunks[0]["text"])
    if state.scraped_documents:
        scrape = state.scraped_documents[0].get("scrape_result", {})
        if isinstance(scrape, dict):
            return str(scrape.get("text", ""))
    return ""


def _keyword_signals(text: str) -> list[str]:
    candidates = [
        "api",
        "apis",
        "automation",
        "analytics",
        "workflow",
        "platform",
        "cloud",
        "ai",
        "security",
        "engineering",
        "developer",
        "design",
        "product",
        "open source",
    ]
    lowered = text.lower()
    signals: list[str] = []
    for term in candidates:
        if term in lowered and term not in signals:
            signals.append(term)
    return signals[:5]


def _company_summary(chunk_text: str, company_name: str) -> str:
    if not chunk_text:
        return f"No verified source text was available for {company_name}."

    first_sentence = re.split(r"(?<=[.!?])\s+", chunk_text.strip())[0]
    return first_sentence[:220] if first_sentence else f"Verified source text was available for {company_name}."


def _collect_citations(state: ResearchAgentState) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, chunk in enumerate(state.retrieved_chunks, start=1):
        chunk_id = str(chunk.get("chunk_id", "")).strip()
        source_url = str(chunk.get("source_url", "")).strip()
        if not chunk_id or not source_url or chunk_id in seen:
            continue
        seen.add(chunk_id)
        citations.append(
            {
                "citation_id": f"c{index}",
                "chunk_id": chunk_id,
                "source_url": source_url,
            }
        )
    return citations


def synthesize(state: ResearchAgentState) -> ResearchAgentState:
    """Build a draft CompanyBrief and keep internal claim annotations for self-check."""

    chunk_text = _best_chunk_text(state)
    citations = _collect_citations(state)
    citation_map = {item["chunk_id"]: item for item in citations}
    source_chunk_id = next(iter(citation_map.keys()), "")
    source_url = citation_map[source_chunk_id]["source_url"] if source_chunk_id else "https://example.com"

    summary = _company_summary(chunk_text, state.company_name)
    tech_signals = _keyword_signals(chunk_text)
    culture_notes = (
        f"Source material for {state.company_name} suggests an emphasis on "
        f"{', '.join(tech_signals[:3])}." if tech_signals else f"Source material for {state.company_name} is limited."
    )

    recent_news: list[dict[str, str]] = []
    if state.search_results:
        news_title = state.search_results[0].get("title") or f"{state.company_name} news"
        if source_chunk_id:
            recent_news.append({"headline": news_title, "citation_id": citations[0]["citation_id"]})

    annotations: list[dict[str, Any]] = []
    if source_chunk_id:
        annotations.append(
            {
                "field": "summary",
                "claim": summary,
                "chunk_id": source_chunk_id,
                "source_url": source_url,
            }
        )
        annotations.append(
            {
                "field": "culture_notes",
                "claim": culture_notes,
                "chunk_id": source_chunk_id,
                "source_url": source_url,
            }
        )
        for signal in tech_signals:
            annotations.append(
                {
                    "field": "tech_signals",
                    "claim": signal,
                    "chunk_id": source_chunk_id,
                    "source_url": source_url,
                }
            )
        for news_item in recent_news:
            annotations.append(
                {
                    "field": "recent_news",
                    "claim": news_item["headline"],
                    "citation_id": news_item["citation_id"],
                    "chunk_id": source_chunk_id,
                    "source_url": source_url,
                }
            )

    state.claim_annotations = annotations
    state.draft_brief = {
        "company_name": state.company_name,
        "summary": summary,
        "tech_signals": tech_signals,
        "recent_news": recent_news,
        "culture_notes": culture_notes,
        "confidence_flags": [] if chunk_text else ["limited_source_coverage"],
        "citations": citations,
        "run_metadata": {
            "prompt_version": state.prompt_version,
            "latency_ms": 0,
            "token_cost_usd": 0.0,
            "tool_calls_used": state.tool_calls_used,
        },
    }
    return state

