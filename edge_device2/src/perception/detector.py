from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

from ultralytics import YOLOWorld


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


@dataclass
class Detection:
    track_id: int
    label: str
    confidence: float
    xyxy: tuple[int, int, int, int]
    source_label: str | None = None

    @property
    def center(self):
        x1, y1, x2, y2 = self.xyxy
        return ((x1+x2)/2.0, (y1+y2)/2.0)

    @property
    def area(self):
        return max(0, self.xyxy[2]-self.xyxy[0]) * max(0, self.xyxy[3]-self.xyxy[1])


class WorldDetector:
    """YOLO-World with rich prompts and canonical semantic labels."""

    def __init__(self, model_path, prompts, confidence=0.20,
                 landmark_confidence=0.18, iou=0.45, imgsz=960,
                 device="auto", aliases=None, max_detections=40):
        self.model = YOLOWorld(model_path)
        self.prompts = {k: [_norm(x) for x in v] for k, v in prompts.items()}
        self.confidence = confidence
        self.landmark_confidence = landmark_confidence
        self.iou = iou
        self.imgsz = imgsz
        self.device = None if device in ("auto", "", None) else device
        self.aliases = {_norm(k): _norm(v) for k, v in (aliases or {}).items()}
        self.max_detections = max_detections

        flat = []
        self.prompt_to_canonical = {}
        for canonical, prompt_list in self.prompts.items():
            for prompt in prompt_list:
                flat.append(prompt)
                self.prompt_to_canonical[prompt] = canonical

        self.classes = flat
        self.model.set_classes(flat)

    def infer(self, frame) -> tuple[list[Detection], Any]:
        kwargs = dict(
            source=frame,
            persist=True,
            conf=self.confidence,
            iou=self.iou,
            imgsz=self.imgsz,
            verbose=False,
        )
        if self.device is not None:
            kwargs["device"] = self.device

        result = self.model.track(**kwargs)[0]
        if result.boxes is None:
            return [], result

        boxes = result.boxes
        coords = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)
        ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [-1] * len(coords)

        out = []
        landmark_labels = {"table", "desk", "shelf", "bed", "cupboard"}

        for box, conf, cls_id, track_id in zip(coords, confs, classes, ids):
            if int(track_id) < 0:
                continue

            raw = self.classes[int(cls_id)] if 0 <= int(cls_id) < len(self.classes) else str(cls_id)
            label = self.prompt_to_canonical.get(_norm(raw), _norm(raw))
            label = self.aliases.get(label, label)

            threshold = self.landmark_confidence if label in landmark_labels else self.confidence
            if float(conf) < threshold:
                continue

            x1, y1, x2, y2 = [int(round(v)) for v in box]
            out.append(Detection(
                track_id=int(track_id),
                label=label,
                confidence=float(conf),
                xyxy=(x1, y1, x2, y2),
                source_label=raw,
            ))

        out.sort(key=lambda d: d.confidence, reverse=True)
        return out[:self.max_detections], result
