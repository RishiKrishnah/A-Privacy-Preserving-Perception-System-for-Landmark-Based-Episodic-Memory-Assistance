from flask import Blueprint, jsonify, request


def create_memory_routes(memory_service):
    bp = Blueprint("memory", __name__, url_prefix="/api/memories")

    @bp.get("/recent")
    def recent():
        limit = request.args.get("limit", 20, type=int)
        return jsonify({"memories": memory_service.edge.recent(limit)})

    return bp
