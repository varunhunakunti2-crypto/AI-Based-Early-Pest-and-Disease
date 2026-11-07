"""Tests for the isolated inference service.

No ``ultralytics`` is imported: a fake detector stands in for the real model so
CI never needs torch or the weights. What is tested here is the HTTP contract
and, above all, that output cannot escape the demo labelling.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from serve.app import LABEL_STATUS, create_app


class FakeDetector:
    num_classes = 3

    def __init__(self, *, detections: list[dict] | None = None, failure: Exception | None = None):
        self._detections = detections if detections is not None else []
        self._failure = failure
        self.calls: list[tuple[Path, float]] = []

    def detect(self, image_path: Path, *, conf: float) -> list[dict]:
        self.calls.append((image_path, conf))
        if self._failure is not None:
            raise self._failure
        return self._detections


class FakeRegistry:
    def __init__(self, detector: FakeDetector) -> None:
        self.detector = detector
        self.loaded = ["plant"]

    def get(self, key: str) -> FakeDetector:
        if key not in {"pest", "plant"}:
            raise KeyError(key)
        return self.detector


def _client(detector: FakeDetector) -> TestClient:
    return TestClient(create_app(FakeRegistry(detector)))


def test_health_reports_demo() -> None:
    response = _client(FakeDetector()).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["is_demo"] is True
    assert set(body["models"]) == {"pest", "plant"}


def test_detect_returns_labelled_demo_output() -> None:
    detector = FakeDetector(
        detections=[
            {
                "class_id": 7,
                "class_name": "banana leaf",
                "confidence": 0.342123,
                "bbox_xyxy": [0.0, 0.19, 319.97, 319.95],
            }
        ]
    )
    response = _client(detector).post(
        "/v1/detect",
        files={"file": ("leaf.jpg", b"not-a-real-image", "image/jpeg")},
        data={"model": "plant", "conf": "0.3"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_demo"] is True
    assert body["label_status"] == LABEL_STATUS
    assert "not a diagnosis" in body["warning"]
    assert body["model"] == "plant"
    assert body["classes"] == 3
    assert body["detections"] == [
        {
            "class_id": 7,
            "class_name": "banana leaf",
            "confidence": 0.3421,
            "bbox_xyxy": [0.0, 0.19, 319.97, 319.95],
            "label_status": LABEL_STATUS,
        }
    ]
    assert detector.calls[0][1] == pytest.approx(0.3)


def test_detect_rejects_unknown_model() -> None:
    response = _client(FakeDetector()).post(
        "/v1/detect",
        files={"file": ("leaf.jpg", b"x", "image/jpeg")},
        data={"model": "tomato"},
    )
    assert response.status_code == 422


def test_detect_rejects_empty_upload() -> None:
    response = _client(FakeDetector()).post(
        "/v1/detect",
        files={"file": ("leaf.jpg", b"", "image/jpeg")},
        data={"model": "plant"},
    )
    assert response.status_code == 422


def test_detect_rejects_out_of_range_conf() -> None:
    response = _client(FakeDetector()).post(
        "/v1/detect",
        files={"file": ("leaf.jpg", b"x", "image/jpeg")},
        data={"model": "plant", "conf": "1.5"},
    )
    assert response.status_code == 422


def test_inference_failure_is_a_safe_503() -> None:
    detector = FakeDetector(failure=RuntimeError("model exploded"))
    response = _client(detector).post(
        "/v1/detect",
        files={"file": ("leaf.jpg", b"x", "image/jpeg")},
        data={"model": "plant"},
    )
    assert response.status_code == 503
    assert "inference failed" in response.json()["detail"]
    assert "model exploded" not in response.json()["detail"]
