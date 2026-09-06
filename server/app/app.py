from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

from app.edge.edge_client import EdgeMemoryClient
from app.services.gemini_service import GeminiService
from app.services.memory_service import MemoryService
from app.routes.memory import create_memory_routes
from app.routes.query import create_query_routes
from app.routes.edge_sync import create_edge_sync_routes

SERVER_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(SERVER_ROOT / ".env")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.get("/")
def home():
    return jsonify(
        {
            "service": "Privacy-Preserving Episodic Memory Assistant",
            "status": "ok",
            "api": {
                "health": "/api/health",
                "memories": "/api/memories/recent",
                "query": "/api/query",
            },
        }
    )


edge_client = EdgeMemoryClient()
memory_service = MemoryService(edge_client)

app.register_blueprint(create_memory_routes(memory_service))
app.register_blueprint(create_edge_sync_routes(memory_service))


@app.get("/api/health")
def health():
    try:
        edge = edge_client.health()
        return jsonify(
            {
                "status": "ok",
                "edge": edge,
                "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
            }
        )
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


# Initialize lazily so the server can still be inspected without an API key.
@app.post("/api/query")
def query():
    from app.routes.query import create_query_routes

    # Delegate using a temporary blueprint view to keep initialization lazy.
    question = (
        __import__("flask").request.get_json(silent=True).get("question", "").strip()
    )
    if not question:
        return jsonify({"error": "question is required"}), 400
    try:
        gemini = GeminiService()
        memories = memory_service.retrieve_for_question(question)
        answer = gemini.answer(question, memories)
        return jsonify(
            {
                "answer": answer,
                "memories_used": memories,
                "privacy": {
                    "raw_media_sent_to_gemini": False,
                    "semantic_records_sent_to_gemini": True,
                },
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", "8000")),
        debug=False,
    )
