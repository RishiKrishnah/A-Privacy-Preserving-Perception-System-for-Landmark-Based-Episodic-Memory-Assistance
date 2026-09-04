from __future__ import annotations

from flask import Flask, jsonify, request

from src.config import load_config, resolve_project_path
from src.memory_store import MemoryStore

cfg = load_config()
db_cfg = cfg["database"]

store = MemoryStore(
    resolve_project_path(db_cfg.get("path", "data/memory.db")),
    float(db_cfg.get("dedup_window_seconds", 4.0)),
)
store.initialize()

app = Flask(__name__)


def limit_arg(name, default, maximum):
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, maximum))


@app.get("/health")
def health():
    try:
        ok = store.integrity_check() == "ok"
    except Exception as exc:
        return jsonify({
            "status": "error",
            "service": "edge-semantic-memory",
            "database": "unavailable",
            "raw_media_exposed": False,
            "error": str(exc),
        }), 503

    return jsonify({
        "status": "ok" if ok else "degraded",
        "service": "edge-semantic-memory",
        "database": "available" if ok else "degraded",
        "raw_media_exposed": False,
    }), 200 if ok else 503


@app.get("/memory/recent")
def recent():
    return jsonify({"memories": store.recent(limit_arg("limit",20,200))})


@app.get("/memory/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "q is required"}), 400
    return jsonify({"memories": store.search(q, limit_arg("limit",20,200))})


@app.get("/memory/events")
def events():
    return jsonify({
        "memories": store.events(
            request.args.get("from"),
            request.args.get("to"),
            limit_arg("limit",100,500),
        )
    })


if __name__ == "__main__":
    api_cfg = cfg["api"]
    app.run(
        host=str(api_cfg.get("host", "127.0.0.1")),
        port=int(api_cfg.get("port", 9000)),
        debug=False,
        threaded=True,
    )
