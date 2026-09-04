from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class MemoryStore:
    """Small semantic-memory SQLite store.

    This is the prototype storage layer. The public methods form the
    hardware-independent contract used by the edge API.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    action TEXT NOT NULL,
                    landmark TEXT,
                    details TEXT
                )
                """
            )
            conn.commit()

    def add_event(
        self,
        timestamp: str,
        subject: str,
        action: str,
        landmark: str | None = None,
        details: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO memory_events
                   (timestamp, subject, action, landmark, details)
                   VALUES (?, ?, ?, ?, ?)""",
                (timestamp, subject, action, landmark, details),
            )
            conn.commit()

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT id, timestamp, subject, action, landmark, details
                   FROM memory_events
                   ORDER BY timestamp DESC, id DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        q = f"%{query.strip()}%"
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT id, timestamp, subject, action, landmark, details
                   FROM memory_events
                   WHERE subject LIKE ?
                      OR action LIKE ?
                      OR COALESCE(landmark, '') LIKE ?
                      OR COALESCE(details, '') LIKE ?
                   ORDER BY timestamp DESC, id DESC
                   LIMIT ?""",
                (q, q, q, q, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def events(self, start: str | None = None, end: str | None = None,
               limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        clauses = []
        params: list[Any] = []
        if start:
            clauses.append("timestamp >= ?")
            params.append(start)
        if end:
            clauses.append("timestamp <= ?")
            params.append(end)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(
                f"""SELECT id, timestamp, subject, action, landmark, details
                    FROM memory_events
                    {where}
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?""",
                params,
            ).fetchall()
        return [dict(r) for r in rows]
