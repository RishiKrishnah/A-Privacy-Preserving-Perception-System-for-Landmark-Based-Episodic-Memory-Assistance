from __future__ import annotations

from pathlib import Path
import requests

# Local prototype import
import sys

EDGE_SRC = Path(__file__).resolve().parents[3] / "edge_device2" / "src"
if str(EDGE_SRC) not in sys.path:
    sys.path.insert(0, str(EDGE_SRC))

from memory_store import MemoryStore


class EdgeMemoryClient:
    def __init__(self, mode: str, local_db_path: str, edge_base_url: str):
        self.mode = mode.lower()
        self.local = MemoryStore(Path(local_db_path))
        self.edge_base_url = edge_base_url.rstrip("/")

    def health(self) -> dict:
        if self.mode == "local":
            self.local.initialize()
            return {"status": "ok", "mode": "local"}
        r = requests.get(f"{self.edge_base_url}/health", timeout=5)
        r.raise_for_status()
        return r.json()

    def recent(self, limit: int = 20) -> list[dict]:
        if self.mode == "local":
            return self.local.recent(limit)
        r = requests.get(
            f"{self.edge_base_url}/memory/recent",
            params={"limit": limit},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()["memories"]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        if self.mode == "local":
            return self.local.search(query, limit)
        r = requests.get(
            f"{self.edge_base_url}/memory/search",
            params={"q": query, "limit": limit},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()["memories"]
