from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_words(text: str) -> list[str]:
    normalized = normalize_text(text)
    return normalized.split(" ") if normalized else []


def make_chunk_id(company_name: str, source_url: str, index: int, text: str) -> str:
    digest = hashlib.sha1(
        f"{company_name}|{source_url}|{index}|{normalize_text(text)}".encode("utf-8")
    ).hexdigest()
    return f"chunk_{digest[:16]}"


def chunk_text(
    text: str,
    *,
    company_name: str,
    source_url: str,
    chunk_size_words: int = 220,
    overlap_words: int = 40,
    min_words: int = 1,
    scraped_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Split text into deterministic chunk dictionaries ready for embedding."""

    if chunk_size_words <= 0:
        raise ValueError("chunk_size_words must be positive.")
    if overlap_words < 0:
        raise ValueError("overlap_words cannot be negative.")
    if overlap_words >= chunk_size_words:
        raise ValueError("overlap_words must be smaller than chunk_size_words.")

    words = split_words(text)
    if not words:
        return []

    step = chunk_size_words - overlap_words
    created_at = scraped_at or datetime.now(timezone.utc)
    chunks: list[dict[str, Any]] = []

    for index, start in enumerate(range(0, len(words), step)):
        end = min(len(words), start + chunk_size_words)
        chunk_words = words[start:end]
        if len(chunk_words) < min_words and chunks:
            break
        chunk_text_value = " ".join(chunk_words).strip()
        if not chunk_text_value:
            continue

        chunks.append(
            {
                "chunk_id": make_chunk_id(company_name, source_url, index, chunk_text_value),
                "text": chunk_text_value,
                "source_url": source_url,
                "scraped_at": created_at.isoformat(),
                "company_name": company_name,
                "chunk_index": index,
            }
        )

        if end >= len(words):
            break

    return chunks
