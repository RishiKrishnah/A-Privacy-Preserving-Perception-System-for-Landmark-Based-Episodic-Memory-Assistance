from __future__ import annotations

import re

STOPWORDS = {
    "a",
    "an",
    "the",
    "i",
    "me",
    "my",
    "mine",
    "where",
    "what",
    "when",
    "did",
    "do",
    "was",
    "were",
    "is",
    "are",
    "to",
    "of",
    "on",
    "in",
    "at",
    "with",
    "and",
    "or",
    "please",
    "tell",
    "show",
    "about",
}


class MemoryService:
    def __init__(self, edge_client):
        self.edge = edge_client

    def retrieve_for_question(self, question: str, limit: int = 20) -> list[dict]:
        words = re.findall(r"[A-Za-z0-9_-]+", question.lower())
        keywords = [w for w in words if w not in STOPWORDS and len(w) > 2]

        # First try specific keyword retrieval. Merge results while preserving order.
        seen = set()
        results = []
        for keyword in keywords[:5]:
            for item in self.edge.search(keyword, limit):
                key = item.get("id")
                if key not in seen:
                    seen.add(key)
                    results.append(item)
                if len(results) >= limit:
                    return results[:limit]

        # Fall back to recent memories when the question has no searchable keyword.
        if not results:
            return self.edge.recent(limit)
        return results[:limit]
