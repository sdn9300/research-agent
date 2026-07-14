import sqlite3
import json
import time
from pathlib import Path

class RunLogger:
    """Simple SQLite logger for research‑agent runs.
    Records per‑run metadata such as prompt version, tool calls, latency, token cost, and retrieved chunk IDs.
    """

    def __init__(self, db_path: str | Path = "observability/logger.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    def _initialize_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    prompt_version TEXT,
                    tool_calls_used INTEGER,
                    latency_ms INTEGER,
                    token_cost_usd REAL,
                    chunk_ids TEXT,
                    citations TEXT
                )
                """
            )
            conn.commit()

    def log_run(
        self,
        run_id: str,
        company_name: str,
        prompt_version: str | None = None,
        tool_calls_used: int | None = None,
        latency_ms: int | None = None,
        token_cost_usd: float | None = None,
        chunk_ids: list[str] | None = None,
        citations: list[dict] | None = None,
    ) -> None:
        """Insert a run record.

        Arguments are optional – the caller can omit fields that are unavailable.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, timestamp, company_name, prompt_version,
                    tool_calls_used, latency_ms, token_cost_usd,
                    chunk_ids, citations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    company_name,
                    prompt_version,
                    tool_calls_used,
                    latency_ms,
                    token_cost_usd,
                    json.dumps(chunk_ids) if chunk_ids is not None else None,
                    json.dumps(citations) if citations is not None else None,
                ),
            )
            conn.commit()
