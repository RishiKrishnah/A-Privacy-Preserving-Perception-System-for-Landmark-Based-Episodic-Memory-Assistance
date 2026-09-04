from __future__ import annotations

import sqlite3
from pathlib import Path


class MemoryStore:
    """SQLite semantic-memory store; never stores camera frames."""

    def __init__(self, db_path, dedup_window_seconds=4.0):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.dedup_window = float(dedup_window_seconds)

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def initialize(self):
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    action TEXT NOT NULL,
                    landmark TEXT,
                    confidence REAL,
                    details TEXT
                )
            """)
            for index in (
                "CREATE INDEX IF NOT EXISTS idx_memory_timestamp ON memory_events(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_memory_subject ON memory_events(subject)",
                "CREATE INDEX IF NOT EXISTS idx_memory_action ON memory_events(action)",
                "CREATE INDEX IF NOT EXISTS idx_memory_landmark ON memory_events(landmark)",
            ):
                conn.execute(index)
            conn.commit()

    def add_event(self, timestamp, subject, action, landmark=None,
                  confidence=None, details=None):
        with self.connect() as conn:
            # ISO timestamps are normalized by the event generator. julianday
            # gives a robust time-window comparison in SQLite.
            duplicate = conn.execute("""
                SELECT id FROM memory_events
                WHERE subject = ?
                  AND action = ?
                  AND COALESCE(landmark, '') = COALESCE(?, '')
                  AND ABS(
                      (julianday(timestamp) - julianday(?)) * 86400.0
                  ) <= ?
                ORDER BY id DESC
                LIMIT 1
            """, (
                subject, action, landmark, timestamp, self.dedup_window
            )).fetchone()

            if duplicate:
                return int(duplicate["id"])

            cur = conn.execute("""
                INSERT INTO memory_events
                (timestamp, subject, action, landmark, confidence, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (timestamp, subject, action, landmark, confidence, details))
            conn.commit()
            return int(cur.lastrowid)

    def recent(self, limit=20):
        limit = max(1, min(int(limit), 200))
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT id,timestamp,subject,action,landmark,confidence,details
                FROM memory_events
                ORDER BY timestamp DESC,id DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def search(self, query, limit=20):
        query = query.strip()
        if not query:
            return self.recent(limit)
        limit = max(1, min(int(limit), 200))
        q = f"%{query}%"
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT id,timestamp,subject,action,landmark,confidence,details
                FROM memory_events
                WHERE subject LIKE ? OR action LIKE ?
                   OR COALESCE(landmark,'') LIKE ?
                   OR COALESCE(details,'') LIKE ?
                ORDER BY timestamp DESC,id DESC
                LIMIT ?
            """, (q,q,q,q,limit)).fetchall()
        return [dict(r) for r in rows]

    def events(self, start=None, end=None, limit=100):
        limit = max(1, min(int(limit), 500))
        clauses, params = [], []
        if start:
            clauses.append("timestamp >= ?")
            params.append(start)
        if end:
            clauses.append("timestamp <= ?")
            params.append(end)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(f"""
                SELECT id,timestamp,subject,action,landmark,confidence,details
                FROM memory_events
                {where}
                ORDER BY timestamp DESC,id DESC
                LIMIT ?
            """, params).fetchall()
        return [dict(r) for r in rows]

    def integrity_check(self):
        with self.connect() as conn:
            return conn.execute("PRAGMA integrity_check").fetchone()[0]
