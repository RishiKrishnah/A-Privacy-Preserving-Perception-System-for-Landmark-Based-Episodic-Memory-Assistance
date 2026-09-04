from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from math import hypot


@dataclass
class LandmarkMatch:
    label: str
    confidence: float
    gap_px: float


def box_gap(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    dx = max(bx1-ax2, ax1-bx2, 0)
    dy = max(by1-ay2, ay1-by2, 0)
    return hypot(dx, dy)


def iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1,bx1), max(ay1,by1)
    ix2, iy2 = min(ax2,bx2), min(ay2,by2)
    inter = max(0,ix2-ix1) * max(0,iy2-iy1)
    aa = max(0,ax2-ax1) * max(0,ay2-ay1)
    ba = max(0,bx2-bx1) * max(0,by2-by1)
    union = aa + ba - inter
    return inter/union if union else 0.0


class LandmarkAssociator:
    """Associates a personal object with a landmark over multiple frames."""

    def __init__(self, landmarks, max_gap_px=180,
                 vertical_tolerance_px=140, history_frames=8,
                 confirmations=3):
        self.landmarks = set(landmarks)
        self.max_gap = max_gap_px
        self.vertical_tolerance = vertical_tolerance_px
        self.history_frames = history_frames
        self.confirmations = confirmations
        self.history = {}

    def update(self, obj, landmark_detections):
        candidates = []
        ox1, oy1, ox2, oy2 = obj.xyxy
        for lm in landmark_detections:
            if lm.label not in self.landmarks:
                continue
            gap = box_gap(obj.xyxy, lm.xyxy)
            lx1, ly1, lx2, ly2 = lm.xyxy
            vertical_gap = ly1 - oy2

            if gap <= self.max_gap and vertical_gap <= self.vertical_tolerance:
                candidates.append((gap, -lm.confidence, lm))

        if candidates:
            _, _, best = min(candidates, key=lambda x: (x[0], x[1]))
            hist = self.history.setdefault(
                obj.track_id, deque(maxlen=self.history_frames)
            )
            hist.append(best.label)

            counts = Counter(hist)
            label, count = counts.most_common(1)[0]
            if count >= self.confirmations:
                return LandmarkMatch(
                    label=label,
                    confidence=best.confidence,
                    gap_px=box_gap(obj.xyxy, best.xyxy),
                )

        return self._confirmed(obj.track_id)

    def _confirmed(self, track_id):
        hist = self.history.get(track_id)
        if not hist:
            return None
        label, count = Counter(hist).most_common(1)[0]
        if count >= self.confirmations:
            return LandmarkMatch(label, 0.55, self.max_gap)
        return None

    def clear(self, track_id):
        self.history.pop(track_id, None)
