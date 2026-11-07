"""Unit tests for the pretrained-YOLO assessment engine.

The isolated inference service is replaced by an ``httpx.MockTransport``. No
torch, ultralytics or weights are needed, so this stays in the normal backend CI.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from app.core.config import Settings
from app.modules.conversations import engine as engine_module
from app.modules.conversations.engine import UploadContext, get_assessment_engine
from app.modules.conversations.pretrained_engine import (
    UNVERIFIED_LABEL_SUFFIX,
    PretrainedAssessmentEngine,
)
from PIL import Image


def _settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "_env_file": None,
        "media_root": str(tmp_path),
        "pretrained_inference_url": "http://inference.invalid",
        "pretrained_model": "plant",
        "pretrained_conf": 0.25,
        "pretrained_timeout_s": 1.0,
        "chat_engine": "pretrained",
    }
    values.update(overrides)
    return Settings(**values)


def _upload(
    tmp_path: Path,
    *,
    quality: str = "pass",
    storage_path: str | None = "demo_user/leaf.jpg",
    create: bool = True,
) -> UploadContext:
    if create and storage_path is not None:
        destination = tmp_path / storage_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 32), (34, 139, 34)).save(destination, format="JPEG")
    return UploadContext(
        upload_id="up_1",
        sha256="a" * 64,
        width=32,
        height=32,
        quality_result=quality,
        quality_flags=(),
        storage_path=storage_path,
    )


def _payload(**overrides) -> dict:
    body = {
        "is_demo": True,
        "warning": "DEMO OUTPUT — not a diagnosis.",
        "label_status": "unverified_model_label",
        "model": "plant",
        "architecture": "YOLOv11x",
        "model_version": "pretrained-plant-yolov11x-116",
        "classes": 116,
        "detections": [
            {
                "class_id": 0,
                "class_name": "banana leaf",
                "confidence": 0.342123,
                "bbox_xyxy": [0.0, 0.19, 319.97, 319.95],
                "label_status": "unverified_model_label",
            }
        ],
    }
    body.update(overrides)
    return body


def _engine(tmp_path: Path, handler, **overrides):
    settings = _settings(tmp_path, **overrides)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return PretrainedAssessmentEngine(settings, client=client)


def test_detection_is_demo_labelled_and_unverified(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_payload())

    result = _engine(tmp_path, handler).assess(upload=_upload(tmp_path))

    assert result.state == "assessed"
    assert result.is_demo is True
    assert result.calibrated is False
    assert result.confidence_band == "not_calibrated"
    assert result.model_version == "pretrained-plant-yolov11x-116"
    assert result.candidates == [
        {
            "label": "banana leaf",
            "display_name": f"banana leaf{UNVERIFIED_LABEL_SUFFIX}",
            "score": 0.3421,
        }
    ]
    assert len(requests) == 1
    assert str(requests[0].url) == "http://inference.invalid/v1/detect"


def test_empty_detections_are_an_abstention_not_a_healthy_verdict(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_payload(detections=[]))

    result = _engine(tmp_path, handler).assess(upload=_upload(tmp_path))

    assert result.state == "abstained"
    assert result.reason_code == "model_abstained"
    assert result.candidates == []
    assert result.is_demo is True
    assert "not a healthy verdict" in result.reason_text


def test_service_output_that_is_not_demo_is_rejected(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_payload(is_demo=False))

    result = _engine(tmp_path, handler).assess(upload=_upload(tmp_path))

    assert result.state == "failed"
    assert result.reason_code == "invalid_model_response"
    assert result.is_demo is True


def test_quality_gate_abstains_without_calling_the_service(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=_payload())

    result = _engine(tmp_path, handler).assess(upload=_upload(tmp_path, quality="blurry"))

    assert result.state == "abstained"
    assert result.reason_code == "quality_gate_failed"
    assert result.quality_flag == "blurry"
    assert result.is_demo is True
    assert calls == []


def test_missing_stored_image_fails_closed(tmp_path: Path) -> None:
    result = _engine(tmp_path, lambda request: httpx.Response(200, json=_payload())).assess(
        upload=_upload(tmp_path, storage_path=None)
    )
    assert result.state == "failed"
    assert result.reason_code == "image_unavailable"
    assert result.is_demo is True


def test_timeout_is_a_retryable_failure(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("too slow", request=request)

    result = _engine(tmp_path, handler).assess(upload=_upload(tmp_path))

    assert result.state == "failed"
    assert result.reason_code == "model_timeout"
    assert result.retryable is True


def test_service_5xx_is_a_retryable_failure(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "inference failed"})

    result = _engine(tmp_path, handler).assess(upload=_upload(tmp_path))

    assert result.state == "failed"
    assert result.reason_code == "model_unavailable"
    assert result.retryable is True
    assert result.candidates == []


def test_malformed_payload_is_not_turned_into_an_assessment(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"is_demo": True, "detections": "nope"})

    result = _engine(tmp_path, handler).assess(upload=_upload(tmp_path))

    assert result.state == "failed"
    assert result.reason_code == "invalid_model_response"


def test_no_image_abstains(tmp_path: Path) -> None:
    result = _engine(tmp_path, lambda request: httpx.Response(500)).assess(upload=None)
    assert result.state == "abstained"
    assert result.reason_code == "no_image"


def test_engine_selection_is_explicit(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path, chat_engine="pretrained")
    monkeypatch.setattr(engine_module, "get_settings", lambda: settings)
    get_assessment_engine.cache_clear()

    selected = get_assessment_engine()
    assert isinstance(selected, PretrainedAssessmentEngine)
    assert selected.is_demo is True

    get_assessment_engine.cache_clear()


@pytest.mark.parametrize("engine_name", ["yolo", "yolo_pretrained", "yolo-pretrained"])
def test_engine_selection_aliases(tmp_path: Path, monkeypatch, engine_name: str) -> None:
    settings = _settings(tmp_path, chat_engine=engine_name)
    monkeypatch.setattr(engine_module, "get_settings", lambda: settings)
    get_assessment_engine.cache_clear()

    assert isinstance(get_assessment_engine(), PretrainedAssessmentEngine)
    get_assessment_engine.cache_clear()


def test_model_override_is_sent_to_the_service(tmp_path: Path) -> None:
    bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.content)
        return httpx.Response(200, json=_payload())

    settings = _settings(tmp_path, pretrained_model="plant")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    engine = PretrainedAssessmentEngine(settings, client=client, model="pest")

    engine.assess(upload=_upload(tmp_path))

    assert b'name="model"' in bodies[0]
    assert b"pest" in bodies[0]
