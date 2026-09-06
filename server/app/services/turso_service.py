from __future__ import annotations

import os
from typing import Any

import libsql_client


class TursoMemoryStore:
    """
    Persistent semantic-memory store backed by Turso/libSQL.

    Turso credentials are read only from the Render/server environment.
    The edge device never receives these credentials.
    """

    def __init__(self):
        self.url = os.getenv("TURSO_DATABASE_URL", "").strip()
        self.auth_token = os.getenv("TURSO_AUTH_TOKEN", "").strip()

        if not self.url:
            raise RuntimeError("TURSO_DATABASE_URL is not configured.")

        if not self.auth_token:
            raise RuntimeError("TURSO_AUTH_TOKEN is not configured.")

    def _connect(self):
        return libsql_client.create_client_sync(
            self.url,
            auth_token=self.auth_token,
        )

    def initialize(self):
        with self._connect() as client:
            client.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    action TEXT NOT NULL,
                    landmark TEXT,
                    confidence REAL,
                    details TEXT
                )
                """
            )

            client.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_timestamp
                ON memory_events(timestamp)
                """
            )

            client.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_subject
                ON memory_events(subject)
                """
            )

            client.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_action
                ON memory_events(action)
                """
            )

            client.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_landmark
                ON memory_events(landmark)
                """
            )

    def add_event(
        self,
        timestamp,
        subject,
        action,
        landmark=None,
        confidence=None,
        details=None,
    ):
        with self._connect() as client:
            result = client.execute(
                """
                SELECT id
                FROM memory_events
                WHERE subject = ?
                  AND action = ?
                  AND COALESCE(landmark, '') = COALESCE(?, '')
                  AND ABS(
                      (julianday(timestamp) - julianday(?)) * 86400.0
                  ) <= 4.0
                ORDER BY id DESC
                LIMIT 1
                """,
                [
                    subject,
                    action,
                    landmark,
                    timestamp,
                ],
            )

            if result.rows:
                return int(result.rows[0][0])

            result = client.execute(
                """
                INSERT INTO memory_events
                (
                    timestamp,
                    subject,
                    action,
                    landmark,
                    confidence,
                    details
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    timestamp,
                    subject,
                    action,
                    landmark,
                    confidence,
                    details,
                ],
            )

            # Retrieve the inserted row ID.
            result = client.execute(
                """
                SELECT id
                FROM memory_events
                ORDER BY id DESC
                LIMIT 1
                """
            )

            return int(result.rows[0][0])

    def recent(self, limit=20):
        limit = max(1, min(int(limit), 200))

        with self._connect() as client:
            result = client.execute(
                """
                SELECT
                    id,
                    timestamp,
                    subject,
                    action,
                    landmark,
                    confidence,
                    details
                FROM memory_events
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                [limit],
            )

            return self._rows_to_dicts(result)

    def search(self, query, limit=20):
        query = str(query).strip()

        if not query:
            return self.recent(limit)

        limit = max(1, min(int(limit), 200))
        q = f"%{query}%"

        with self._connect() as client:
            result = client.execute(
                """
                SELECT
                    id,
                    timestamp,
                    subject,
                    action,
                    landmark,
                    confidence,
                    details
                FROM memory_events
                WHERE subject LIKE ?
                   OR action LIKE ?
                   OR COALESCE(landmark, '') LIKE ?
                   OR COALESCE(details, '') LIKE ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                [q, q, q, q, limit],
            )

            return self._rows_to_dicts(result)

    def events(self, start=None, end=None, limit=100):
        limit = max(1, min(int(limit), 500))

        clauses = []
        params: list[Any] = []

        if start:
            clauses.append("timestamp >= ?")
            params.append(start)

        if end:
            clauses.append("timestamp <= ?")
            params.append(end)

        where = ""

        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        params.append(limit)

        with self._connect() as client:
            result = client.execute(
                f"""
                SELECT
                    id,
                    timestamp,
                    subject,
                    action,
                    landmark,
                    confidence,
                    details
                FROM memory_events
                {where}
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                params,
            )

            return self._rows_to_dicts(result)

    def integrity_check(self):
        with self._connect() as client:
            result = client.execute("PRAGMA integrity_check")

            if not result.rows:
                return "unknown"

            return str(result.rows[0][0])

    @staticmethod
    def _rows_to_dicts(result):
        columns = [
            "id",
            "timestamp",
            "subject",
            "action",
            "landmark",
            "confidence",
            "details",
        ]

        return [dict(zip(columns, row)) for row in result.rows]
