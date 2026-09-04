from __future__ import annotations

import argparse
import logging
import time

import cv2

from src.config import load_config, resolve_project_path
from src.events.event_recognizer import EventRecognizer
from src.memory_store import MemoryStore
from src.cloud_sync import CloudSync
from src.perception.detector import WorldDetector
from src.perception.hand_tracker import HandTracker
from src.perception.landmarks import LandmarkAssociator


LOGGER = logging.getLogger("edge")


def setup_logging(level):
    logging.basicConfig(
        level=getattr(logging, str(level).upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def open_camera(index, width, height, fps, backend="auto"):
    api = cv2.CAP_ANY
    if backend.lower() == "dshow" and hasattr(cv2, "CAP_DSHOW"):
        api = cv2.CAP_DSHOW
    cap = cv2.VideoCapture(index, api)
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    return cap


def draw_overlay(frame, detections, hands, events, draw_boxes=True, draw_hands=True):
    if draw_boxes:
        for d in detections:
            x1, y1, x2, y2 = d.xyxy
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"{d.label} #{d.track_id} {d.confidence:.2f}",
                (x1, max(18, y1 - 7)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

    if draw_hands:
        for h in hands:
            cx, cy = map(int, h.center)
            cv2.circle(frame, (cx, cy), 8, (255, 0, 255), -1)
            cv2.putText(
                frame,
                f"hand {h.confidence:.2f}",
                (cx + 8, cy),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 0, 255),
                1,
                cv2.LINE_AA,
            )

    if events:
        e = events[-1]
        text = f"{e.action}: {e.subject}"
        if e.landmark:
            text += f" -> {e.landmark}"
        cv2.rectangle(
            frame, (10, 42), (min(frame.shape[1] - 10, 620), 84), (0, 0, 0), -1
        )
        cv2.putText(
            frame,
            text,
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


def parse_args():
    p = argparse.ArgumentParser(description="Robust landmark-aware edge perception")
    p.add_argument("--config", default=None)
    p.add_argument("--camera", type=int, default=None)
    p.add_argument("--no-window", action="store_true")
    p.add_argument("--no-hands", action="store_true")
    p.add_argument("--no-events", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    cfg = load_config(args.config)
    setup_logging(cfg.get("application", {}).get("log_level", "INFO"))

    cam_cfg = cfg["camera"]
    camera_index = (
        args.camera if args.camera is not None else int(cam_cfg.get("index", 0))
    )
    width, height, fps = (
        int(cam_cfg.get("width", 1280)),
        int(cam_cfg.get("height", 720)),
        int(cam_cfg.get("fps", 30)),
    )

    obj_cfg = cfg["objects"]
    personal = [str(x).lower() for x in obj_cfg["personal"]]
    landmarks = [str(x).lower() for x in obj_cfg["landmarks"]]

    p_cfg = cfg["perception"]
    prompts = p_cfg.get("prompts") or {
        x: [x] for x in personal + landmarks + ["person"]
    }

    detector = WorldDetector(
        model_path=str(p_cfg.get("model", "yolov8s-world.pt")),
        prompts=prompts,
        confidence=float(p_cfg.get("confidence", 0.20)),
        landmark_confidence=float(p_cfg.get("landmark_confidence", 0.18)),
        iou=float(p_cfg.get("iou", 0.45)),
        imgsz=int(p_cfg.get("imgsz", 960)),
        device=str(p_cfg.get("device", "auto")),
        aliases=obj_cfg.get("aliases", {}),
        max_detections=int(p_cfg.get("max_detections", 40)),
    )

    hand_tracker = None
    h_cfg = cfg["hands"]
    if h_cfg.get("enabled", True) and not args.no_hands:
        try:
            hand_tracker = HandTracker(
                resolve_project_path(
                    h_cfg.get("model_path", "data/hand_landmarker.task")
                ),
                max_num_hands=int(h_cfg.get("max_num_hands", 2)),
                min_detection_confidence=float(
                    h_cfg.get("min_detection_confidence", 0.45)
                ),
                min_tracking_confidence=float(
                    h_cfg.get("min_tracking_confidence", 0.45)
                ),
                auto_download=bool(h_cfg.get("auto_download", True)),
            )
        except Exception:
            LOGGER.exception(
                "Hand tracker could not start. Events will be disabled until it is available."
            )
            hand_tracker = None

    e_cfg = cfg["events"]
    recognizer = EventRecognizer(
        personal_objects=personal,
        landmarks=landmarks,
        contact_distance_px=float(e_cfg.get("contact_distance_px", 110)),
        movement_distance_px=float(e_cfg.get("movement_distance_px", 14)),
        min_moving_frames=int(e_cfg.get("min_moving_frames", 3)),
        contact_frames=int(e_cfg.get("contact_frames", 3)),
        release_frames=int(e_cfg.get("release_frames", 3)),
        stable_frames=int(e_cfg.get("stable_frames", 8)),
        min_event_confidence=float(e_cfg.get("min_event_confidence", 0.55)),
        cooldown_seconds=float(e_cfg.get("cooldown_seconds", 2.0)),
        emit_move=bool(e_cfg.get("emit_move", True)),
        move_min_frames=int(e_cfg.get("move_min_frames", 8)),
    )

    associator = LandmarkAssociator(
        landmarks,
        max_gap_px=float(e_cfg.get("landmark_max_gap_px", 180)),
        vertical_tolerance_px=float(e_cfg.get("landmark_vertical_tolerance_px", 140)),
        history_frames=int(e_cfg.get("landmark_history_frames", 8)),
        confirmations=int(e_cfg.get("landmark_confirmations", 3)),
    )

    db_cfg = cfg["database"]
    db = resolve_project_path(db_cfg.get("path", "data/memory.db"))
    store = MemoryStore(db, float(db_cfg.get("dedup_window_seconds", 4.0)))
    store.initialize()

    cloud_sync = CloudSync()

    LOGGER.info(
        "Cloud sync configured | server=%s",
        cloud_sync.base_url,
    )

    display = cfg.get("display", {})
    show = bool(display.get("show_window", True)) and not args.no_window

    cap = None
    failures = 0
    frame_count = 0
    start = time.monotonic()

    LOGGER.info("Edge perception started | camera=%s | db=%s", camera_index, db)

    try:
        while True:
            if cap is None:
                cap = open_camera(
                    camera_index,
                    width,
                    height,
                    fps,
                    str(cam_cfg.get("backend", "auto")),
                )
                if cap is None:
                    failures += 1
                    if failures > int(cam_cfg.get("reconnect_attempts", 5)):
                        raise RuntimeError(
                            f"Could not open camera {camera_index} after "
                            f"{failures - 1} retries."
                        )
                    delay = float(cam_cfg.get("reconnect_delay_seconds", 1.0))
                    LOGGER.warning("Camera unavailable; retry %d", failures)
                    time.sleep(delay * min(failures, 5))
                    continue
                failures = 0
                LOGGER.info("Camera connected")

            ok, frame = cap.read()
            if not ok or frame is None or frame.size == 0:
                failures += 1
                LOGGER.warning("Camera frame read failed; reconnecting")
                cap.release()
                cap = None
                time.sleep(float(cam_cfg.get("reconnect_delay_seconds", 1.0)))
                continue

            try:
                detections, _ = detector.infer(frame)
            except Exception:
                LOGGER.exception("Detector inference failed; skipping this frame")
                detections = []

            hands = []
            if hand_tracker is not None:
                try:
                    hands = hand_tracker.infer(frame)
                except Exception:
                    LOGGER.exception("Hand tracking failed for this frame")

            landmark_detections = [d for d in detections if d.label in landmarks]
            landmark_matches = {}

            for d in detections:
                if d.label in personal:
                    match = associator.update(d, landmark_detections)
                    if match:
                        landmark_matches[d.track_id] = match

            events = []
            if (
                not args.no_events
                and bool(e_cfg.get("enabled", True))
                and hand_tracker is not None
            ):
                events = recognizer.update(detections, hands, landmark_matches)

            for event in events:
                try:
                    # Always keep the semantic event locally first.
                    event_id = store.add_event(
                        event.timestamp,
                        event.subject,
                        event.action,
                        event.landmark,
                        event.confidence,
                        event.details,
                    )

                    LOGGER.info(
                        "MEMORY #%s | %s | %s | %s | %.2f",
                        event_id,
                        event.subject,
                        event.action,
                        event.landmark or "-",
                        event.confidence,
                    )

                    # Send ONLY the semantic event to Render.
                    # No camera frame is transmitted.
                    cloud_sync.send_event(event)

                except Exception:
                    LOGGER.exception("Could not store semantic event")

            frame_count += 1

            if show:
                draw_overlay(
                    frame,
                    detections,
                    hands,
                    events,
                    bool(display.get("draw_boxes", True)),
                    bool(display.get("draw_hands", True)),
                )
                elapsed = max(0.001, time.monotonic() - start)
                cv2.putText(
                    frame,
                    f"FPS {frame_count / elapsed:.1f}",
                    (15, 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow("Privacy-Preserving Edge Perception", frame)

                if (cv2.waitKey(1) & 0xFF) == ord("q"):
                    break

    except KeyboardInterrupt:
        LOGGER.info("Stopping on Ctrl+C")
    finally:
        if cap is not None:
            cap.release()
        if hand_tracker is not None:
            hand_tracker.close()
        cv2.destroyAllWindows()
        LOGGER.info("Edge perception stopped")


if __name__ == "__main__":
    main()
