"""Isolated inference service for the two pretrained YOLO detectors in ``ml/``.

This process is deliberately separate from the backend API. The detectors are
built on ``ultralytics``, which is **AGPL-3.0**; keeping the import in this
process means the backend service is not linked against it. The backend talks to
this service over HTTP only.

Everything this service returns is **demo** output:

* the taxonomies (102 IP102 pests / 116 plant-disease classes) are not the
  project's approved D1a allowlist;
* no calibration or operating point has been approved;
* the models are used outside their validated domain.

Callers must treat ``is_demo`` as permanent until those gates close.

Run locally (from ``ml/``)::

    ..\\backend\\.venv\\Scripts\\python -m uvicorn serve.app:app --host 127.0.0.1 --port 8010

The first request downloads weights from Hugging Face (38 MB pest, 457 MB plant).
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Protocol

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

DEMO_WARNING = (
    "DEMO OUTPUT — not a diagnosis, not a confirmed case. "
    "Taxonomy and operating point are not approved."
)

# Class names come straight from the model and are not mapped to the project
# taxonomy. Every detection carries this marker so a caller cannot silently
# promote it to an approved label.
LABEL_STATUS = "unverified_model_label"

MAX_IMAGE_BYTES = 15 * 1024 * 1024


@dataclass(frozen=True)
class ModelSpec:
    key: str
    package: str
    architecture: str
    model_version: str
    hf_repo: str


MODEL_SPECS: dict[str, ModelSpec] = {
    "pest": ModelSpec(
        key="pest",
        package="agroai_pest_detection",
        architecture="YOLO11s",
        model_version="pretrained-pest-yolo11s-ip102",
        hf_repo="Yashwanth1508/AgroAI-pest-detection",
    ),
    "plant": ModelSpec(
        key="plant",
        package="plant_diseasedetection",
        architecture="YOLOv11x",
        model_version="pretrained-plant-yolov11x-116",
        hf_repo="Ananthakrishnanmzen/PlantDiseaseDetection",
    ),
}


class Detector(Protocol):
    """Minimal surface the HTTP layer needs from a loaded model."""

    num_classes: int

    def detect(self, image_path: Path, *, conf: float) -> list[dict]: ...


class YoloDetectorAdapter:
    """Adapter over the packages in ``ml/``. Imports ``ultralytics`` lazily."""

    def __init__(self, spec: ModelSpec) -> None:
        self._spec = spec
        self._detector = None

    def _load(self):
        if self._detector is None:
            if self._spec.key == "pest":
                from agroai_pest_detection import PestDetector

                self._detector = PestDetector()
            else:
                from plant_diseasedetection import PlantDiseaseDetector

                self._detector = PlantDiseaseDetector()
        return self._detector

    @property
    def num_classes(self) -> int:
        return int(self._load().num_classes)

    def detect(self, image_path: Path, *, conf: float) -> list[dict]:
        detector = self._load()
        if self._spec.key == "pest":
            from agroai_pest_detection.inference import detect_pests

            return detect_pests(image_path, conf=conf, detector=detector)

        from plant_diseasedetection.inference import detect_image

        return detect_image(image_path, conf=conf, detector=detector)


class DetectorRegistry:
    """Lazily created, process-wide model instances keyed by model name."""

    def __init__(self) -> None:
        self._detectors: dict[str, Detector] = {}

    def get(self, key: str) -> Detector:
        if key not in MODEL_SPECS:
            raise KeyError(key)
        if key not in self._detectors:
            self._detectors[key] = YoloDetectorAdapter(MODEL_SPECS[key])
        return self._detectors[key]

    @property
    def loaded(self) -> list[str]:
        return sorted(self._detectors)


def _detections_payload(detections: list[dict]) -> list[dict]:
    payload = []
    for item in detections:
        payload.append(
            {
                "class_id": int(item["class_id"]),
                "class_name": str(item["class_name"]),
                "confidence": round(float(item["confidence"]), 4),
                "bbox_xyxy": [round(float(v), 2) for v in item["bbox_xyxy"]],
                "label_status": LABEL_STATUS,
            }
        )
    return payload


def create_app(registry: DetectorRegistry | None = None) -> FastAPI:
    app = FastAPI(
        title="PS-03 pretrained inference service",
        version="0.1.0",
        description=(
            "Runs the pretrained YOLO detectors in ml/ behind HTTP. "
            "Output is demo-labelled and never a diagnosis."
        ),
    )
    app.state.registry = registry if registry is not None else DetectorRegistry()

    def _registry(request: Request) -> DetectorRegistry:
        return request.app.state.registry

    @app.get("/health")
    def health(request: Request) -> dict:
        return {
            "status": "ok",
            "service": "ml-inference",
            "models": {key: spec.architecture for key, spec in MODEL_SPECS.items()},
            "loaded": _registry(request).loaded,
            "is_demo": True,
        }

    @app.get("/v1/models")
    def models() -> dict:
        return {
            "is_demo": True,
            "warning": DEMO_WARNING,
            "models": [
                {
                    "key": spec.key,
                    "architecture": spec.architecture,
                    "model_version": spec.model_version,
                    "hf_repo": spec.hf_repo,
                }
                for spec in MODEL_SPECS.values()
            ],
        }

    @app.post("/v1/detect")
    async def detect(
        request: Request,
        file: Annotated[UploadFile, File()],
        model: Annotated[str, Form()] = "plant",
        conf: Annotated[float, Form()] = 0.25,
    ) -> JSONResponse:
        if model not in MODEL_SPECS:
            raise HTTPException(status_code=422, detail=f"unknown model: {model}")
        if not 0.0 < conf <= 1.0:
            raise HTTPException(status_code=422, detail="conf must be in (0, 1]")

        data = await file.read(MAX_IMAGE_BYTES + 1)
        if not data:
            raise HTTPException(status_code=422, detail="empty upload")
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="image too large")

        suffix = Path(file.filename or "image.jpg").suffix or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(data)
            temp_path = Path(handle.name)

        try:
            detector = _registry(request).get(model)
            detections = detector.detect(temp_path, conf=conf)
            num_classes = int(detector.num_classes)
        except HTTPException:
            raise
        except Exception as error:  # noqa: BLE001 - surfaced as a safe 503
            raise HTTPException(
                status_code=503,
                detail=f"inference failed: {type(error).__name__}",
            ) from error
        finally:
            temp_path.unlink(missing_ok=True)

        spec = MODEL_SPECS[model]
        return JSONResponse(
            {
                "is_demo": True,
                "warning": DEMO_WARNING,
                "label_status": LABEL_STATUS,
                "model": spec.key,
                "architecture": spec.architecture,
                "model_version": spec.model_version,
                "hf_repo": spec.hf_repo,
                "classes": num_classes,
                "confidence_threshold": conf,
                "detections": _detections_payload(detections),
            }
        )

    return app


app = create_app()
