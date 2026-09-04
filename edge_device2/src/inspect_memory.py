from __future__ import annotations

from src.config import load_config, resolve_project_path
from src.memory_store import MemoryStore

cfg = load_config()
db = resolve_project_path(cfg["database"].get("path", "data/memory.db"))
store = MemoryStore(db)
store.initialize()

print(f"Database: {db}")
print(f"Integrity: {store.integrity_check()}")
print("-" * 100)

for row in store.recent(50):
    print(
        f"{row['timestamp']} | {row['subject']:10s} | "
        f"{row['action']:5s} | {row.get('landmark') or '-':10s} | "
        f"{float(row.get('confidence') or 0):.2f} | "
        f"{row.get('details') or ''}"
    )
