"""Convenience inference helpers for the IP102 pest detector."""

from __future__ import annotations

from pathlib import Path

from .model import PestDetector, load_detector


def detect_pests(
    image_path: str | Path,
    *,
    conf: float = 0.25,
    detector: PestDetector | None = None,
) -> list[dict]:
    """Run pest detection on a single image and return normalized detections.

    Each detection dict: ``{"class_id", "class_name", "confidence", "bbox_xyxy"}``.
    """
    if detector is None:
        detector = load_detector()

    results = detector.predict(str(image_path), conf=conf)
    detections: list[dict] = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue
        for box in boxes:
            xyxy = box.xyxy[0].tolist() if box.xyxy is not None else [0, 0, 0, 0]
            detections.append(
                {
                    "class_id": int(box.cls[0]),
                    "class_name": detector.class_name(int(box.cls[0])),
                    "confidence": float(box.conf[0]),
                    "bbox_xyxy": [round(float(v), 2) for v in xyxy],
                }
            )
    return detections


__all__ = ["detect_pests"]
