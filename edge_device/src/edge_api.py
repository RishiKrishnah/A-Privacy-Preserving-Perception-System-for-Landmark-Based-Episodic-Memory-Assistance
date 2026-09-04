from pathlib import Path
from flask import Flask, jsonify, request

from memory_store import MemoryStore

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "memory.db"

store = MemoryStore(DB)
store.initialize()
app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "edge-semantic-memory"})


@app.get("/memory/recent")
def recent():
    limit = request.args.get("limit", 20, type=int)
    return jsonify({"memories": store.recent(limit)})


@app.get("/memory/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q is required"}), 400
    limit = request.args.get("limit", 20, type=int)
    return jsonify({"memories": store.search(query, limit)})


@app.get("/memory/events")
def events():
    start = request.args.get("from")
    end = request.args.get("to")
    limit = request.args.get("limit", 100, type=int)
    return jsonify({"memories": store.events(start, end, limit)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
