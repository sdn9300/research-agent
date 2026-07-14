from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.embed_store import LocalVectorStore


def retrieve(
    query_text: str,
    *,
    store_path: str | Path,
    top_k: int = 5,
    company_name: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve top-k chunks with source metadata intact."""

    store = LocalVectorStore(store_path)
    return store.query(query_text, top_k=top_k, company_name=company_name)

