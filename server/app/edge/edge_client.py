from __future__ import annotations

from app.services.turso_service import TursoMemoryStore


class EdgeMemoryClient:
    """
    Compatibility wrapper.

    The API name is retained so the rest of the application
    does not need major changes.

    In production, semantic memories are stored in Turso.
    """

    def __init__(self):
        self.turso = TursoMemoryStore()
        self.turso.initialize()

    def health(self) -> dict:
        integrity = self.turso.integrity_check()

        return {
            "status": "ok" if integrity == "ok" else "degraded",
            "mode": "turso",
            "database": "available" if integrity == "ok" else "degraded",
        }

    def recent(self, limit: int = 20) -> list[dict]:
        return self.turso.recent(limit)

    def search(self, query: str, limit: int = 20) -> list[dict]:
        return self.turso.search(query, limit)

    def events(
        self,
        start=None,
        end=None,
        limit: int = 100,
    ) -> list[dict]:
        return self.turso.events(start, end, limit)

    def add_event(
        self,
        timestamp,
        subject,
        action,
        landmark=None,
        confidence=None,
        details=None,
    ):
        return self.turso.add_event(
            timestamp=timestamp,
            subject=subject,
            action=action,
            landmark=landmark,
            confidence=confidence,
            details=details,
        )
