# Pretrained inference service (isolated, demo output)

A small FastAPI wrapper around the two pretrained YOLO detectors in `ml/`:

| Model | Package | Architecture | Classes |
|---|---|---|---|
| `pest` | `agroai_pest_detection` | YOLO11s (IP102) | 102 |
| `plant` | `plant_diseasedetection` | YOLOv11x | 116 |

> **Demo output only.** The taxonomies do not match the project's approved D1a
> allowlist, no calibration or operating point exists, and the models are used
> outside their validated domain. Every response sets `is_demo: true`, carries a
> warning, and tags each detection `label_status: unverified_model_label`.
> Never present this as a diagnosis or map it to a project label without the
> taxonomy decision.

## Why a separate service

The detectors run on `ultralytics`, which is **AGPL-3.0**. Keeping the import in
this process means the backend API is not linked against it and CI never
installs torch. The backend reaches this service over HTTP only.

## Run

```bash
# from ml/
../backend/.venv/Scripts/python -m uvicorn serve.app:app --host 127.0.0.1 --port 8010
```

First call downloads weights from Hugging Face:

- pest: `Yashwanth1508/AgroAI-pest-detection` — `best.pt` (38 MB)
- plant: `Ananthakrishnanmzen/PlantDiseaseDetection` — `PlantDiseaseDetection.pt` (457 MB)

Weights are cached under the Hugging Face cache, never committed.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness + which models are loaded |
| `GET` | `/v1/models` | Model metadata and demo warning |
| `POST` | `/v1/detect` | Multipart `file`, form `model` = `pest`\|`plant`, form `conf` |

```bash
curl -s -F "file=@leaf.jpg" -F "model=plant" -F "conf=0.25" \
  http://127.0.0.1:8010/v1/detect
```

```json
{
  "is_demo": true,
  "warning": "DEMO OUTPUT — not a diagnosis, not a confirmed case. …",
  "label_status": "unverified_model_label",
  "model": "plant",
  "architecture": "YOLOv11x",
  "model_version": "pretrained-plant-yolov11x-116",
  "classes": 116,
  "detections": [
    {
      "class_id": 0,
      "class_name": "banana leaf",
      "confidence": 0.342,
      "bbox_xyxy": [0.0, 0.19, 319.97, 319.95],
      "label_status": "unverified_model_label"
    }
  ]
}
```

An empty `detections` list is an abstention, not a "healthy" verdict.

## Tests

```bash
# from ml/
../backend/.venv/Scripts/python -m pytest tests/test_serve.py
```

Tests use a fake detector, so they run without torch, ultralytics or weights.
