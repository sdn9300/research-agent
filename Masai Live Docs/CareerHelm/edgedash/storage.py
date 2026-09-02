"""
EdgeDash Subsystem 2: Isolated Storage Layer (Dual SQLite / Hosted Postgres)
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 2 (Rule 2 & Rules 47-51)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger("edgedash.storage")

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,           -- Stable SHA256 of source + url
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    url TEXT NOT NULL,
    description TEXT NOT NULL,
    source TEXT NOT NULL,
    posted_at TEXT,
    fetched_at TEXT NOT NULL,
    fit_score INTEGER NULL,
    fit_reason TEXT NULL,
    components TEXT NULL,          -- JSON string of component scores
    scored_at TEXT NULL
);

CREATE TABLE IF NOT EXISTS extraction_cache (
    desc_hash TEXT PRIMARY KEY,    -- SHA256 of raw description text
    extracted_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL,
    computed_at TEXT NOT NULL,
    skill TEXT NOT NULL,
    listings_blocked INTEGER NOT NULL,
    opportunity_cost REAL NOT NULL,
    mean_score REAL NOT NULL,
    top_score INTEGER NOT NULL,
    example_ids TEXT NOT NULL,     -- Comma-separated listing IDs
    also_nice_to_have INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cycle_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    records_touched INTEGER NOT NULL,
    status TEXT NOT NULL,          -- ok | failed | partial | nothing_to_do
    notes TEXT
);

CREATE TABLE IF NOT EXISTS verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    verdict TEXT NOT NULL,         -- pass | fail
    failed_check TEXT,
    observed_value REAL,
    threshold REAL,
    action_taken TEXT
);

CREATE TABLE IF NOT EXISTS query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    tool_used TEXT,
    params TEXT,
    status TEXT NOT NULL,          -- answered | refused | rate_limited
    duration_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_score ON listings(fit_score);
CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source);
CREATE INDEX IF NOT EXISTS idx_listings_fetched ON listings(fetched_at);
CREATE INDEX IF NOT EXISTS idx_gaps_snapshot ON skill_gaps(snapshot_id);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id VARCHAR(64) PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    url TEXT NOT NULL,
    description TEXT NOT NULL,
    source TEXT NOT NULL,
    posted_at TEXT,
    fetched_at TEXT NOT NULL,
    fit_score INTEGER NULL,
    fit_reason TEXT NULL,
    components TEXT NULL,
    scored_at TEXT NULL
);

CREATE TABLE IF NOT EXISTS extraction_cache (
    desc_hash VARCHAR(64) PRIMARY KEY,
    extracted_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_gaps (
    id SERIAL PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    computed_at TEXT NOT NULL,
    skill TEXT NOT NULL,
    listings_blocked INTEGER NOT NULL,
    opportunity_cost REAL NOT NULL,
    mean_score REAL NOT NULL,
    top_score INTEGER NOT NULL,
    example_ids TEXT NOT NULL,
    also_nice_to_have INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cycle_log (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    records_touched INTEGER NOT NULL,
    status TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS verdicts (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    verdict TEXT NOT NULL,
    failed_check TEXT,
    observed_value REAL,
    threshold REAL,
    action_taken TEXT
);

CREATE TABLE IF NOT EXISTS query_log (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    tool_used TEXT,
    params TEXT,
    status TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_score ON listings(fit_score);
CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source);
CREATE INDEX IF NOT EXISTS idx_listings_fetched ON listings(fetched_at);
CREATE INDEX IF NOT EXISTS idx_gaps_snapshot ON skill_gaps(snapshot_id);
"""


def compute_listing_id(source: str, url: str) -> str:
    """Compute stable SHA256 hex string for deduplication."""
    raw = f"{source.strip().lower()}:{url.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_desc_hash(description: str) -> str:
    """Compute stable SHA256 of JD description."""
    return hashlib.sha256(description.strip().encode("utf-8")).hexdigest()


class Storage:
    """Encapsulated storage interface for EdgeDash SQLite & Postgres backends."""

    def __init__(self, db_path: Optional[str] = None):
        database_url = os.getenv("DATABASE_URL")
        if database_url and database_url.startswith("postgres"):
            self.backend = "postgres"
            self.connection_string = database_url
            self.db_path = "postgres"
            print(f"[Storage] Active backend: Hosted Postgres (Supabase/Neon)")
        else:
            self.backend = "sqlite"
            self.db_path = str(db_path or "edgedash.db")
            self.connection_string = self.db_path
            print(f"[Storage] Active backend: Local SQLite ({self.db_path})")

        self.initialize_schema()

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        if self.backend == "postgres":
            try:
                import psycopg2
                import psycopg2.extras
                conn = psycopg2.connect(self.connection_string, cursor_factory=psycopg2.extras.RealDictCursor)
                try:
                    yield conn
                finally:
                    conn.close()
            except ImportError:
                try:
                    import psycopg
                    from psycopg.rows import dict_row
                    conn = psycopg.connect(self.connection_string, row_factory=dict_row)
                    try:
                        yield conn
                    finally:
                        conn.close()
                except ImportError:
                    raise RuntimeError("Postgres driver (psycopg2 or psycopg) not installed. Please install psycopg2-binary.")
        else:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def _translate_query(self, query: str) -> str:
        """Translate SQLite syntax to Postgres syntax when on Postgres."""
        if self.backend != "postgres":
            return query

        q = query.replace("?", "%s")
        # Translate upserts
        q = q.replace("INSERT OR IGNORE INTO listings", "INSERT INTO listings")
        if "INSERT INTO listings" in q and "ON CONFLICT" not in q:
            q = q.rstrip(";") + " ON CONFLICT (id) DO NOTHING"
        return q

    def initialize_schema(self) -> None:
        """Create tables and indices if they do not exist."""
        try:
            with self.get_connection() as conn:
                if self.backend == "postgres":
                    with conn.cursor() as cur:
                        cur.execute(POSTGRES_SCHEMA)
                    conn.commit()
                else:
                    conn.executescript(SQLITE_SCHEMA)
                    conn.commit()
        except Exception as e:
            logger.warning(f"Schema initialization warning: {e}")

    # -------------------------------------------------------------------
    # Listings CRUD & Deduplication
    # -------------------------------------------------------------------

    def upsert_listings(self, raw_listings: List[Dict[str, Any]]) -> int:
        if not raw_listings:
            return 0

        inserted_count = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        if self.backend == "postgres":
            query = """
                INSERT INTO listings (
                    id, title, company, location, url, description, source, posted_at, fetched_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """
        else:
            query = """
                INSERT OR IGNORE INTO listings (
                    id, title, company, location, url, description, source, posted_at, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for item in raw_listings:
                source = item.get("source", "manual")
                url = item.get("url", "")
                if not url:
                    continue

                listing_id = compute_listing_id(source, url)
                params = (
                    listing_id,
                    item.get("title", "Unknown Role"),
                    item.get("company", "Unknown Company"),
                    item.get("location", ""),
                    url,
                    item.get("description", ""),
                    source,
                    item.get("posted_at"),
                    item.get("fetched_at", now_iso),
                )
                cursor.execute(query, params)
                if cursor.rowcount > 0:
                    inserted_count += 1
            conn.commit()

        return inserted_count

    def get_unscored_listings(self, limit: int = 50) -> List[Dict[str, Any]]:
        query = self._translate_query("SELECT * FROM listings WHERE fit_score IS NULL ORDER BY fetched_at DESC LIMIT ?")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def update_listing_score(
        self,
        listing_id: str,
        fit_score: int,
        fit_reason: str,
        components: Dict[str, Any],
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        query = self._translate_query("""
            UPDATE listings
            SET fit_score = ?, fit_reason = ?, components = ?, scored_at = ?
            WHERE id = ?
        """)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                fit_score,
                fit_reason,
                json.dumps(components),
                now_iso,
                listing_id,
            ))
            conn.commit()

    def get_all_scored_listings(self) -> List[Dict[str, Any]]:
        query = "SELECT * FROM listings WHERE fit_score IS NOT NULL ORDER BY fit_score DESC"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def get_listing_by_id(self, listing_id: str) -> Optional[Dict[str, Any]]:
        query = self._translate_query("SELECT * FROM listings WHERE id = ?")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (listing_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # -------------------------------------------------------------------
    # Extraction Cache
    # -------------------------------------------------------------------

    def get_cached_extraction(self, desc_hash: str) -> Optional[Dict[str, Any]]:
        query = self._translate_query("SELECT extracted_json FROM extraction_cache WHERE desc_hash = ?")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (desc_hash,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["extracted_json"])
            return None

    def set_cached_extraction(self, desc_hash: str, extracted_data: Dict[str, Any]) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        if self.backend == "postgres":
            query = """
                INSERT INTO extraction_cache (desc_hash, extracted_json, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (desc_hash) DO UPDATE SET extracted_json = EXCLUDED.extracted_json
            """
        else:
            query = """
                INSERT INTO extraction_cache (desc_hash, extracted_json, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(desc_hash) DO UPDATE SET extracted_json = excluded.extracted_json
            """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (desc_hash, json.dumps(extracted_data), now_iso))
            conn.commit()

    # -------------------------------------------------------------------
    # Skill Gaps & Snapshots
    # -------------------------------------------------------------------

    def save_skill_gap_snapshot(
        self,
        snapshot_id: str,
        gaps: List[Dict[str, Any]],
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        query = self._translate_query("""
            INSERT INTO skill_gaps (
                snapshot_id, computed_at, skill, listings_blocked,
                opportunity_cost, mean_score, top_score, example_ids, also_nice_to_have
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for g in gaps:
                cursor.execute(query, (
                    snapshot_id,
                    now_iso,
                    g["skill"],
                    g["listings_blocked"],
                    g["opportunity_cost"],
                    g.get("mean_score", 0.0),
                    g.get("top_score", 0),
                    ",".join(g.get("example_ids", [])),
                    1 if g.get("also_nice_to_have") else 0,
                ))
            conn.commit()

    def get_latest_skill_gaps(self, limit: int = 10) -> List[Dict[str, Any]]:
        query = self._translate_query("""
            SELECT * FROM skill_gaps
            WHERE snapshot_id = (SELECT snapshot_id FROM skill_gaps ORDER BY computed_at DESC LIMIT 1)
            ORDER BY opportunity_cost DESC
            LIMIT ?
        """)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------
    # Cycle Log & Diagnostics
    # -------------------------------------------------------------------

    def log_cycle_task(
        self,
        cycle_id: str,
        agent: str,
        started_at: datetime,
        finished_at: datetime,
        records_touched: int,
        status: str,
        notes: Optional[str] = None,
    ) -> None:
        query = self._translate_query("""
            INSERT INTO cycle_log (
                cycle_id, agent, started_at, finished_at, records_touched, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                cycle_id,
                agent,
                started_at.isoformat(),
                finished_at.isoformat(),
                records_touched,
                status,
                notes,
            ))
            conn.commit()

    def get_recent_cycle_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        query = self._translate_query("SELECT * FROM cycle_log ORDER BY finished_at DESC LIMIT ?")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def record_verdict(
        self,
        cycle_id: str,
        verdict: str,
        failed_check: Optional[str] = None,
        observed_value: Optional[float] = None,
        threshold: Optional[float] = None,
        action_taken: Optional[str] = None,
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        query = self._translate_query("""
            INSERT INTO verdicts (
                cycle_id, checked_at, verdict, failed_check, observed_value, threshold, action_taken
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                cycle_id,
                now_iso,
                verdict,
                failed_check,
                observed_value,
                threshold,
                action_taken,
            ))
            conn.commit()

    def get_latest_verdict(self) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM verdicts ORDER BY checked_at DESC LIMIT 1"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            return dict(row) if row else None

    # -------------------------------------------------------------------
    # Query Telemetry
    # -------------------------------------------------------------------

    def log_query(
        self,
        question: str,
        tool_used: Optional[str],
        params: Optional[Dict[str, Any]],
        status: str,
        duration_ms: int,
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        query = self._translate_query("""
            INSERT INTO query_log (
                question, tool_used, params, status, duration_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                question,
                tool_used,
                json.dumps(params) if params else None,
                status,
                duration_ms,
                now_iso,
            ))
            conn.commit()


# ---------------------------------------------------------------------------
# CLI Commands (--migrate, --check)
# ---------------------------------------------------------------------------

def cli_main():
    parser = argparse.ArgumentParser(description="EdgeDash Storage Administration")
    parser.add_argument("--migrate", action="store_true", help="Create tables/schema on active database backend")
    parser.add_argument("--check", action="store_true", help="Print active backend, connectivity status, and table row counts")
    args = parser.parse_args()

    storage = Storage()

    if args.migrate:
        storage.initialize_schema()
        print(f"[Storage] Migration complete. All tables created/verified on active backend ({storage.backend}).")

    if args.check:
        print("=" * 60)
        print("EDGEDASH STORAGE STATUS CHECK")
        print("=" * 60)
        print(f"Active Backend:   {storage.backend.upper()}")
        print(f"Connection Path:  {storage.db_path}")

        try:
            with storage.get_connection() as conn:
                cursor = conn.cursor()

                tables = ["listings", "extraction_cache", "skill_gaps", "cycle_log", "verdicts", "query_log"]
                print("\nTable Row Counts:")
                for tbl in tables:
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM {tbl}")
                    cnt = cursor.fetchone()["cnt"]
                    print(f"  - {tbl:<20}: {cnt} rows")

            print("\nDatabase Connectivity: OK (Verified)")
            print("=" * 60)
        except Exception as e:
            print(f"\nDatabase Connectivity: FAILED ({e})")
            print("=" * 60)
            sys.exit(1)


if __name__ == "__main__":
    cli_main()
