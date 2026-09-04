from __future__ import annotations

import logging
import os
from typing import Any

import requests


LOGGER = logging.getLogger("edge.cloud_sync")


class CloudSync:
    """
    Sends semantic memory events from the edge device to the
    deployed Render server.

    Raw camera frames are NEVER sent.
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = (
            base_url
            or os.getenv("CLOUD_SERVER_URL")
            or "https://a-privacy-preserving-perception-system.onrender.com"
        ).rstrip("/")

        self.api_key = os.getenv("EDGE_SYNC_API_KEY", "").strip()
        self.timeout = 10

    def enabled(self) -> bool:
        return bool(self.base_url)

    def send_event(self, event: Any) -> bool:
        """
        Send one SemanticEvent to Render.

        Returns True when the server accepts the event.
        """

        payload = {
            "timestamp": event.timestamp,
            "subject": event.subject,
            "action": event.action,
            "landmark": event.landmark,
            "confidence": event.confidence,
            "details": event.details,
        }

        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["X-Edge-API-Key"] = self.api_key

        try:
            response = requests.post(
                f"{self.base_url}/api/edge/events",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )

            response.raise_for_status()

            LOGGER.info(
                "Cloud sync successful | %s | %s | %s",
                event.subject,
                event.action,
                event.landmark or "-",
            )

            return True

        except requests.RequestException as exc:
            LOGGER.warning(
                "Cloud sync failed: %s",
                exc,
            )
            return False
