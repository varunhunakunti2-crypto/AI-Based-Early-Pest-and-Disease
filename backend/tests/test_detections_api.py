"""API tests for the demo-labelled detection route.

The engine is stubbed so the route's wiring, persistence lookup and demo
labelling are tested without torch or the inference service. The real HTTP
contract is covered by ``tests/test_pretrained_engine.py`` and ``ml/tests``.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import pytest
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.modules.conversations import orm  # noqa: F401  (registers the tables)
from app.modules.conversations.engine import EngineResult
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

client = TestClient(app)


def _noise_image(size: int = 512) -> Image.Image:
    image = Image.new("RGB", (size, size), (34, 139, 34))
    draw = ImageDraw.Draw(image)
    for index in range(0, size, 8):
        shade = 40 + (index % 180)
        draw.line((0, index, size, (index * 7) % size), fill=(shade, 160, 60), width=2)
    return image


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture()
def session_factory(tmp_path) -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def override() -> Iterator[Session]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    settings = get_settings()
    previous_root = settings.media_root
    settings.media_root = str(tmp_path / "media")
    app.dependency_overrides[get_session] = override
    try:
        yield factory
    finally:
        app.dependency_overrides.pop(get_session, None)
        settings.media_root = previous_root


class _StubEngine:
    def __init__(self, result: EngineResult) -> None:
        self._result = result
        self.model_version = result.model_version
        self.is_demo = result.is_demo
        self.model: str | None = None

    def assess(self, *, upload, crop_id=None, context=None) -> EngineResult:
        del upload, crop_id, context
        return self._result


def _upload() -> dict:
    response = client.post(
        "/v1/uploads",
        files={"file": ("leaf.png", _png(_noise_image()), "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_detection_route_returns_demo_labelled_result(session_factory, monkeypatch) -> None:
    descriptor = _upload()
    stub = _StubEngine(
        EngineResult(
            state="assessed",
            reason_text="Demo-only detection.",
            candidates=[
                {
                    "label": "banana leaf",
                    "display_name": "banana leaf (unverified model label)",
                    "score": 0.3421,
                }
            ],
            confidence_band="not_calibrated",
            calibrated=False,
            model_version="pretrained-plant-yolov11x-116",
            is_demo=True,
        )
    )
    monkeypatch.setattr(
        "app.api.v1.detections.build_engine",
        lambda settings, model: stub,
    )

    response = client.post("/v1/detections", json={"upload_id": descriptor["upload_id"]})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "assessed"
    assert body["is_demo"] is True
    assert body["model_version"] == "pretrained-plant-yolov11x-116"
    assert body["candidates"][0]["display_name"].endswith("(unverified model label)")


def test_detection_route_rejects_unknown_upload(session_factory, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.detections.build_engine",
        lambda settings, model: _StubEngine(
            EngineResult(
                state="failed",
                reason_text="unused",
                model_version="x",
                is_demo=True,
            )
        ),
    )

    response = client.post("/v1/detections", json={"upload_id": "up_missing"})

    assert response.status_code == 404
    assert response.json()["code"] == "upload_not_found"


def test_detection_route_rejects_unknown_model(session_factory) -> None:
    descriptor = _upload()
    response = client.post(
        "/v1/detections",
        json={"upload_id": descriptor["upload_id"], "model": "tomato"},
    )
    assert response.status_code == 422
