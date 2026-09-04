from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory_store import MemoryStore

db = ROOT / "data" / "memory.db"
store = MemoryStore(db)
store.initialize()

base = datetime.now().replace(microsecond=0)
demo = [
    ("wallet", "PLACE", "shelf", "wallet placed on shelf"),
    ("phone", "PICK", "desk", "phone picked from desk"),
    ("keys", "PLACE", "table", "keys placed on table"),
    ("laptop", "INTERACT", "desk", "interaction with laptop"),
]

for i, (subject, action, landmark, details) in enumerate(demo):
    store.add_event(
        (base - timedelta(minutes=20 - i * 5)).isoformat(),
        subject, action, landmark, details
    )

print(f"Seeded semantic memory database: {db}")
