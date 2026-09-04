from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import hypot
from time import monotonic


@dataclass
class TrackState:
    label: str
    last_center: tuple[float, float]
    stable_frames: int = 0
    moving_frames: int = 0
    contact_count: int = 0
    release_count: int = 0
    picked: bool = False
    carried: bool = False
    move_emitted: bool = False
    last_seen: float = field(default_factory=monotonic)
    last_event_at: float = 0.0
    last_landmark: str | None = None
    confidence_history: deque = field(
        default_factory=lambda: deque(maxlen=8)
    )


@dataclass
class SemanticEvent:
    timestamp: str
    subject: str
    action: str
    landmark: str | None
    confidence: float
    details: str


def distance(a, b):
    return hypot(a[0]-b[0], a[1]-b[1])


def box_distance(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    dx = max(bx1-ax2, ax1-bx2, 0)
    dy = max(by1-ay2, ay1-by2, 0)
    return hypot(dx, dy)


class EventRecognizer:
    """Hand-aware temporal PICK/MOVE/PLACE recognizer."""

    def __init__(
        self, personal_objects, landmarks,
        contact_distance_px=110, movement_distance_px=14,
        min_moving_frames=3, contact_frames=3, release_frames=3,
        stable_frames=8, min_event_confidence=0.55,
        cooldown_seconds=2.0, emit_move=True, move_min_frames=8,
    ):
        self.personal_objects = set(personal_objects)
        self.landmarks = set(landmarks)
        self.contact_distance = contact_distance_px
        self.movement_threshold = movement_distance_px
        self.min_moving_frames = min_moving_frames
        self.contact_required = contact_frames
        self.release_required = release_frames
        self.stable_required = stable_frames
        self.min_confidence = min_event_confidence
        self.cooldown = cooldown_seconds
        self.emit_move = emit_move
        self.move_min_frames = move_min_frames
        self.tracks = {}

    def update(self, detections, hands, landmark_matches=None):
        now = monotonic()
        objects = [d for d in detections if d.label in self.personal_objects]
        landmark_matches = landmark_matches or {}
        events = []

        for d in objects:
            state = self.tracks.get(d.track_id)
            if state is None or state.label != d.label:
                state = TrackState(d.label, d.center)
                state.confidence_history.append(d.confidence)
                self.tracks[d.track_id] = state
                continue

            movement = distance(d.center, state.last_center)
            hand_near = any(
                box_distance(d.xyxy, self._hand_box(h)) <= self.contact_distance
                for h in hands
            )

            if movement >= self.movement_threshold:
                state.moving_frames += 1
                state.stable_frames = 0
            else:
                state.stable_frames += 1
                state.moving_frames = 0

            if hand_near:
                state.contact_count += 1
                state.release_count = 0
            else:
                state.release_count += 1
                state.contact_count = max(0, state.contact_count - 1)

            match = landmark_matches.get(d.track_id)
            if match:
                state.last_landmark = match.label

            state.confidence_history.append(d.confidence)

            if (
                not state.picked
                and state.contact_count >= self.contact_required
                and state.moving_frames >= self.min_moving_frames
                and self._can_emit(state, now)
            ):
                conf = self._pick_confidence(state, hands)
                if conf >= self.min_confidence:
                    events.append(self._event(
                        d, "PICK", None, conf,
                        "Sustained hand contact was followed by object movement."
                    ))
                    state.picked = True
                    state.carried = True
                    state.move_emitted = False
                    state.last_event_at = now

            if (
                self.emit_move and state.picked and state.carried
                and not state.move_emitted
                and state.moving_frames >= self.move_min_frames
                and self._can_emit(state, now)
            ):
                conf = self._pick_confidence(state, hands)
                if conf >= self.min_confidence:
                    events.append(self._event(
                        d, "MOVE", state.last_landmark, conf,
                        "The picked object continued moving."
                    ))
                    state.move_emitted = True
                    state.last_event_at = now

            if (
                state.picked and state.carried
                and state.release_count >= self.release_required
                and state.stable_frames >= self.stable_required
                and state.last_landmark in self.landmarks
                and self._can_emit(state, now)
            ):
                match = landmark_matches.get(d.track_id)
                conf = self._place_confidence(state, d.confidence, match)
                if conf >= self.min_confidence:
                    events.append(self._event(
                        d, "PLACE", state.last_landmark, conf,
                        f"Object was released and became stable near {state.last_landmark}."
                    ))
                    state.last_event_at = now
                    state.picked = False
                    state.carried = False
                    state.move_emitted = False
                    state.contact_count = 0
                    state.release_count = 0

            state.last_center = d.center
            state.last_seen = now

        for tid in list(self.tracks):
            if now - self.tracks[tid].last_seen > 5.0:
                self.tracks.pop(tid, None)

        return events

    @staticmethod
    def _hand_box(hand):
        cx, cy = hand.center
        return (int(cx-35), int(cy-35), int(cx+35), int(cy+35))

    def _pick_confidence(self, state, hands):
        obj = sum(state.confidence_history) / max(1, len(state.confidence_history))
        hand = max((float(h.confidence) for h in hands), default=0.0)
        temporal = min(1.0, state.moving_frames / max(1, self.min_moving_frames))
        return max(0.0, min(1.0, 0.50*obj + 0.30*hand + 0.20*temporal))

    def _place_confidence(self, state, detection_conf, match):
        obj = sum(state.confidence_history) / max(1, len(state.confidence_history))
        landmark = float(match.confidence) if match else 0.55
        stable = min(1.0, state.stable_frames / max(1, self.stable_required))
        return max(0.0, min(1.0, 0.50*obj + 0.30*landmark + 0.20*stable))

    def _can_emit(self, state, now):
        return now - state.last_event_at >= self.cooldown

    @staticmethod
    def _event(detection, action, landmark, confidence, details):
        timestamp = datetime.now(timezone.utc).astimezone().replace(
            microsecond=0
        ).isoformat()
        return SemanticEvent(
            timestamp=timestamp,
            subject=detection.label,
            action=action,
            landmark=landmark,
            confidence=round(float(confidence), 3),
            details=details,
        )
