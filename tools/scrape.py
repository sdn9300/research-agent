from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"


@dataclass(slots=True)
class ScrapeResult:
    url: str
    text: str
    title: str = ""
    source: str = "local"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
        elif tag in {"br", "p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in {"p", "div", "section", "article", "li", "tr"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._parts)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()


def _extract_title(page_html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", page_html, flags=re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def html_to_text(page_html: str) -> str:
    parser = _TextExtractor()
    parser.feed(page_html)
    parser.close()
    return parser.get_text()


def _looks_like_html(text: str) -> bool:
    lowered = text.lstrip().lower()
    return lowered.startswith("<!doctype html") or lowered.startswith("<html") or "<body" in lowered


def _read_local_file(path: Path) -> ScrapeResult:
    raw = path.read_text(encoding="utf-8")
    is_html = _looks_like_html(raw)
    return ScrapeResult(
        url=path.as_uri(),
        text=html_to_text(raw) if is_html else raw.strip(),
        title=_extract_title(raw) if is_html else path.stem,
        source="local",
    )


def _scrape_with_firecrawl(url: str, api_key: str, timeout_seconds: int) -> ScrapeResult:
    payload = json.dumps({"url": url, "formats": ["markdown", "html"]}).encode("utf-8")
    request = Request(
        os.getenv("FIRECRAWL_SCRAPE_URL", DEFAULT_FIRECRAWL_URL),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (compatible; ResearchAgent/1.0)",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec: B310
        body = json.loads(response.read().decode("utf-8", errors="replace"))

    data = body.get("data") if isinstance(body, dict) else {}
    text = ""
    title = ""
    if isinstance(data, dict):
        text = (
            data.get("markdown")
            or data.get("content")
            or data.get("text")
            or data.get("html")
            or ""
        )
        title = str(data.get("title") or "")

    if not text:
        raise RuntimeError("Firecrawl scrape returned no usable text.")

    return ScrapeResult(url=url, text=str(text).strip(), title=title, source="firecrawl")


def scrape_url(
    url: str,
    *,
    api_key: str | None = None,
    timeout_seconds: int = 30,
) -> dict[str, str]:
    """Scrape a URL using Firecrawl when configured, otherwise support local file fixtures."""

    parsed = urlparse(url)
    if parsed.scheme == "file":
        local_path = Path(parsed.path.lstrip("/"))
        return _read_local_file(local_path).to_dict()

    if parsed.scheme == "" and Path(url).exists():
        return _read_local_file(Path(url)).to_dict()

    resolved_api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
    if resolved_api_key:
        return _scrape_with_firecrawl(url, resolved_api_key, timeout_seconds).to_dict()

    raise RuntimeError(
        "No Firecrawl API key configured and the supplied URL is not a local file. "
        "Provide FIRECRAWL_API_KEY or use a file:// fixture for offline validation."
    )

