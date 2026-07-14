from __future__ import annotations

import html as html_lib
import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


DEFAULT_SEARCH_URL = "https://html.duckduckgo.com/html/?q={query}"


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = "web"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(value)).strip()


def _load_fixture_html() -> str | None:
    fixture_path = os.getenv("WEB_SEARCH_FIXTURE")
    if not fixture_path:
        return None
    return Path(fixture_path).read_text(encoding="utf-8")


def _parse_search_results(page_html: str, max_results: int) -> list[SearchResult]:
    results: list[SearchResult] = []

    blocks = re.split(r'<div[^>]*class="[^"]*\bresult\b[^"]*"[^>]*>', page_html, flags=re.I)
    candidate_blocks = blocks[1:] if len(blocks) > 1 else [page_html]

    anchor_pattern = re.compile(
        r'<a[^>]*class="[^"]*\bresult__a\b[^"]*"[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>',
        flags=re.I | re.S,
    )
    snippet_pattern = re.compile(
        r'<a[^>]*class="[^"]*\bresult__snippet\b[^"]*"[^>]*>(?P<snippet>.*?)</a>',
        flags=re.I | re.S,
    )

    for block in candidate_blocks:
        anchor_match = anchor_pattern.search(block)
        if not anchor_match:
            continue

        url = html_lib.unescape(anchor_match.group("url"))
        title = _clean_text(anchor_match.group("title"))
        snippet_match = snippet_pattern.search(block)
        snippet = _clean_text(snippet_match.group("snippet")) if snippet_match else ""

        if not title or not url:
            continue

        results.append(SearchResult(title=title, url=url, snippet=snippet))
        if len(results) >= max_results:
            break

    return results


def web_search(
    query: str,
    *,
    max_results: int = 5,
    html: str | None = None,
    search_url: str = DEFAULT_SEARCH_URL,
    timeout_seconds: int = 20,
) -> list[dict[str, str]]:
    """Search the web or parse supplied HTML into normalized result dictionaries."""

    if max_results <= 0:
        return []

    page_html = html if html is not None else _load_fixture_html()
    if page_html is None:
        url = search_url.format(query=quote_plus(query))
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ResearchAgent/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec: B310
            page_html = response.read().decode("utf-8", errors="replace")

    return [result.to_dict() for result in _parse_search_results(page_html, max_results)]


def load_search_results_from_json(path: str | Path) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]
    raise ValueError("Search fixture JSON must contain a list of result objects.")

