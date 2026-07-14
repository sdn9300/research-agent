from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from graph.state import ResearchAgentState
from pipeline.chunker import chunk_text
from pipeline.embed_store import LocalVectorStore

SearchTool = Callable[[str], list[dict[str, str]]]
ScrapeTool = Callable[[str], dict[str, str]]


def _consume_tool_call(state: ResearchAgentState, count: int = 1) -> None:
    if state.tool_calls_used + count > state.tool_call_budget:
        raise RuntimeError(
            f"Tool-call budget exceeded: used {state.tool_calls_used}, "
            f"attempted +{count}, budget {state.tool_call_budget}."
        )
    state.tool_calls_used += count


def search_scrape(
    state: ResearchAgentState,
    *,
    search_tool: SearchTool,
    scrape_tool: ScrapeTool,
) -> ResearchAgentState:
    """Search, scrape, chunk, and store source material while respecting tool-call budget."""

    artifact_dir = state.artifact_path
    artifact_dir.mkdir(parents=True, exist_ok=True)
    store = LocalVectorStore(artifact_dir / "retrieval.sqlite")

    search_results: list[dict[str, str]] = []
    scraped_documents: list[dict[str, Any]] = []
    all_chunks: list[dict[str, Any]] = []

    for query in state.search_strategy:
        if state.tool_calls_used >= state.tool_call_budget:
            break

        _consume_tool_call(state, 1)
        query_results = search_tool(query)
        search_results.extend(query_results)

        for result in query_results:
            if state.tool_calls_used >= state.tool_call_budget:
                break

            url = result.get("url")
            if not url:
                continue

            _consume_tool_call(state, 1)
            scraped = scrape_tool(url)
            scraped_documents.append(
                {
                    "query": query,
                    "search_result": result,
                    "scrape_result": scraped,
                }
            )

            chunks = chunk_text(
                scraped["text"],
                company_name=state.company_name,
                source_url=scraped["url"],
                scraped_at=datetime.now(timezone.utc),
                min_words=1,
            )
            if chunks:
                store.add_chunks(chunks)
                all_chunks.extend(chunks)

        if state.tool_calls_used >= state.tool_call_budget:
            break

    state.search_results = search_results
    state.scraped_documents = scraped_documents
    state.retrieved_chunks = all_chunks
    return state
