from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable

from schemas.chunk import ChunkRecord


DEFAULT_VECTOR_DIMENSION = 128


def _normalize_vector(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector
    return [value / magnitude for value in vector]


def embed_text(text: str, *, dimensions: int = DEFAULT_VECTOR_DIMENSION) -> list[float]:
    """Deterministic local embedding suitable for offline retrieval tests."""

    if dimensions <= 0:
        raise ValueError("dimensions must be positive.")

    vector = [0.0] * dimensions
    tokens = [token.lower() for token in text.split() if token]
    for token in tokens:
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % dimensions
        weight = 1.0 + (int(digest[8:10], 16) / 255.0)
        vector[bucket] += weight
    return _normalize_vector(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(l * r for l, r in zip(left, right))


class LocalVectorStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    scraped_at TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def add_chunks(self, chunks: Iterable[dict[str, Any] | ChunkRecord]) -> list[ChunkRecord]:
        stored: list[ChunkRecord] = []
        with closing(self._connect()) as connection:
            for chunk in chunks:
                if isinstance(chunk, ChunkRecord):
                    record = chunk
                else:
                    record = ChunkRecord(
                        chunk_id=str(chunk["chunk_id"]),
                        text=str(chunk["text"]),
                        embedding=embed_text(str(chunk["text"])),
                        source_url=str(chunk["source_url"]),
                        scraped_at=chunk["scraped_at"],
                        company_name=str(chunk["company_name"]),
                    )

                connection.execute(
                    """
                    INSERT OR REPLACE INTO chunks (
                        chunk_id, company_name, source_url, scraped_at, text, embedding_json, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.chunk_id,
                        record.company_name,
                        str(record.source_url),
                        record.scraped_at.isoformat(),
                        record.text,
                        json.dumps(record.embedding),
                        json.dumps(
                            {
                                "chunk_id": record.chunk_id,
                                "source_url": str(record.source_url),
                                "scraped_at": record.scraped_at.isoformat(),
                                "company_name": record.company_name,
                            }
                        ),
                    ),
                )
                stored.append(record)
            connection.commit()
        return stored

    def query(
        self,
        query_text: str,
        *,
        top_k: int = 5,
        company_name: str | None = None,
    ) -> list[dict[str, Any]]:
        query_embedding = embed_text(query_text)
        with closing(self._connect()) as connection:
            if company_name:
                rows = connection.execute(
                    """
                    SELECT chunk_id, company_name, source_url, scraped_at, text, embedding_json, metadata_json
                    FROM chunks
                    WHERE company_name = ?
                    """,
                    (company_name,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT chunk_id, company_name, source_url, scraped_at, text, embedding_json, metadata_json
                    FROM chunks
                    """
                ).fetchall()

        scored: list[dict[str, Any]] = []
        for row in rows:
            stored_embedding = json.loads(row[5])
            score = cosine_similarity(query_embedding, stored_embedding)
            metadata = json.loads(row[6])
            scored.append(
                {
                    "chunk_id": row[0],
                    "company_name": row[1],
                    "source_url": row[2],
                    "scraped_at": row[3],
                    "text": row[4],
                    "embedding": stored_embedding,
                    "metadata": metadata,
                    "score": score,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]


def build_store(path: str | Path) -> LocalVectorStore:
    return LocalVectorStore(path)
