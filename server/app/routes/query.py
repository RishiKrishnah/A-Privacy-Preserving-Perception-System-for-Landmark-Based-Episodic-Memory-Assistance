from flask import Blueprint, jsonify, request


def create_query_routes(memory_service, gemini_service):
    bp = Blueprint("query", __name__, url_prefix="/api")

    @bp.post("/query")
    def query():
        payload = request.get_json(silent=True) or {}
        question = str(payload.get("question", "")).strip()
        if not question:
            return jsonify({"error": "question is required"}), 400

        memories = memory_service.retrieve_for_question(question)
        answer = gemini_service.answer(question, memories)

        return jsonify({
            "answer": answer,
            "memories_used": memories,
            "privacy": {
                "raw_media_sent_to_gemini": False,
                "semantic_records_sent_to_gemini": True
            }
        })

    return bp
