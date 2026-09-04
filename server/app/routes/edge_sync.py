from __future__ import annotations

import os

from flask import Blueprint, jsonify, request


def create_edge_sync_routes(memory_service):
    bp = Blueprint(
        "edge_sync",
        __name__,
        url_prefix="/api/edge",
    )

    @bp.post("/events")
    def receive_event():
        # Optional shared secret.
        expected_key = os.getenv("EDGE_SYNC_API_KEY", "").strip()

        if expected_key:
            received_key = request.headers.get("X-Edge-API-Key", "")

            if received_key != expected_key:
                return jsonify({"error": "unauthorized"}), 401

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({"error": "JSON body is required"}), 400

        required = [
            "timestamp",
            "subject",
            "action",
        ]

        missing = [field for field in required if not data.get(field)]

        if missing:
            return jsonify(
                {
                    "error": "missing required fields",
                    "fields": missing,
                }
            ), 400

        try:
            timestamp = str(data["timestamp"])
            subject = str(data["subject"])
            action = str(data["action"])

            landmark = data.get("landmark")
            confidence = data.get("confidence")
            details = data.get("details")

            if confidence is not None:
                confidence = float(confidence)

            # Store through the existing memory service / edge client.
            memory_service.edge.local.initialize()

            event_id = memory_service.edge.local.add_event(
                timestamp=timestamp,
                subject=subject,
                action=action,
                landmark=landmark,
                confidence=confidence,
                details=details,
            )

            return jsonify(
                {
                    "status": "ok",
                    "event_id": event_id,
                    "raw_media_received": False,
                }
            ), 201

        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

        except Exception as exc:
            return jsonify(
                {
                    "error": "could not store event",
                    "details": str(exc),
                }
            ), 500

    return bp
