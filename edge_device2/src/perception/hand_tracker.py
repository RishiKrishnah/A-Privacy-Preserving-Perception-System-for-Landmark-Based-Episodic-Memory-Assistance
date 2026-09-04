from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
import time
import urllib.request

import cv2
import mediapipe as mp

LOGGER = logging.getLogger(__name__)

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)


@dataclass
class HandObservation:
    handedness: str
    center: tuple[float, float]
    confidence: float
    points: list[tuple[float, float]]


class HandTracker:
    def __init__(self, model_path, max_num_hands=2,
                 min_detection_confidence=0.45,
                 min_tracking_confidence=0.45,
                 auto_download=True):
        self.model_path = Path(model_path)
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.landmarker = None
        self.enabled = False
        self._last_timestamp_ms = 0

        if not self.model_path.exists():
            if not auto_download:
                raise FileNotFoundError(self.model_path)
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            LOGGER.info("Downloading MediaPipe hand model...")
            urllib.request.urlretrieve(MODEL_URL, self.model_path)

        self._initialize()
        self.enabled = True

    def _initialize(self):
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(
                model_asset_path=str(self.model_path)
            ),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=self.max_num_hands,
            min_hand_detection_confidence=self.min_detection_confidence,
            min_hand_presence_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

    def infer(self, frame):
        if not self.enabled or self.landmarker is None:
            return []

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        timestamp_ms = max(
            int(time.monotonic() * 1000),
            self._last_timestamp_ms + 1,
        )
        self._last_timestamp_ms = timestamp_ms

        result = self.landmarker.detect_for_video(image, timestamp_ms)
        observations = []

        for idx, hand_landmarks in enumerate(result.hand_landmarks or []):
            points = [
                (float(p.x * frame.shape[1]), float(p.y * frame.shape[0]))
                for p in hand_landmarks
            ]
            cx = sum(p[0] for p in points) / len(points)
            cy = sum(p[1] for p in points) / len(points)

            handedness = "unknown"
            confidence = 0.0
            if result.handedness and idx < len(result.handedness):
                handedness = result.handedness[idx][0].category_name or "unknown"
                confidence = float(result.handedness[idx][0].score or 0.0)

            observations.append(
                HandObservation(handedness, (cx, cy), confidence, points)
            )

        return observations

    def close(self):
        if self.landmarker is not None:
            try:
                self.landmarker.close()
            except Exception:
                pass
            self.landmarker = None
            self.enabled = False
