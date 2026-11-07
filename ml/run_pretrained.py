"""Run the pretrained YOLO detectors in ``ml/`` on a single image.

This is an *experimental* runner for the two Hugging Face models that ship in
this folder:

* ``pest``  - YOLO11s on IP102 (102 pest classes)
* ``plant`` - YOLOv11x on a 116-class plant-disease benchmark

It is **not** the governed assessment pipeline. Output is labelled ``demo`` and
is never a diagnosis: the models are used outside their validated domain, their
taxonomies do not match the open D1a allowlist, and no calibration or operating
point has been approved. See ``README.md`` and
``../final/docs-context/progress-tracker.md``.

Usage (from ``ml/``)::

    ..\\backend\\.venv\\Scripts\\python run_pretrained.py --model pest  --image leaf.jpg
    ..\\backend\\.venv\\Scripts\\python run_pretrained.py --model plant --image leaf.jpg
    ..\\backend\\.venv\\Scripts\\python run_pretrained.py --model pest  --download-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEMO_BANNER = (
    "DEMO OUTPUT — not a diagnosis, not a confirmed case. "
    "Taxonomy and operating point are not approved."
)


def _run_pest(image: Path, conf: float) -> dict:
    from agroai_pest_detection import PestDetector
    from agroai_pest_detection.inference import detect_pests

    detector = PestDetector()
    detections = detect_pests(image, conf=conf, detector=detector)
    return {
        "model": "agroai_pest_detection",
        "architecture": "YOLO11s",
        "classes": detector.num_classes,
        "detections": detections,
    }


def _run_plant(image: Path, conf: float) -> dict:
    from plant_diseasedetection import PlantDiseaseDetector
    from plant_diseasedetection.inference import detect_image

    detector = PlantDiseaseDetector()
    detections = detect_image(image, conf=conf, detector=detector)
    return {
        "model": "plant_diseasedetection",
        "architecture": "YOLOv11x",
        "classes": detector.num_classes,
        "detections": detections,
    }


def _print_human(result: dict) -> None:
    print(f"\n{DEMO_BANNER}\n")
    print(f"Model: {result['model']} ({result['architecture']}, {result['classes']} classes)")
    detections = result["detections"]
    if not detections:
        print("No detection above threshold. This is an abstention, not a healthy result.")
        return
    print(f"Detections: {len(detections)}")
    for index, item in enumerate(detections, start=1):
        print(
            f"  {index}. {item['class_name']:<45} "
            f"conf={item['confidence']:.3f}  bbox={item['bbox_xyxy']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["pest", "plant", "both"], default="pest")
    parser.add_argument("--image", type=Path, help="Path to a JPEG/PNG image")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Load each model (downloading weights) without running inference",
    )
    args = parser.parse_args(argv)

    if not args.download_only and args.image is None:
        parser.error("--image is required unless --download-only is set")
    if args.image is not None and not args.image.exists():
        parser.error(f"image not found: {args.image}")

    runners = {"pest": _run_pest, "plant": _run_plant}
    selected = ["pest", "plant"] if args.model == "both" else [args.model]

    results = []
    for name in selected:
        if args.download_only:
            if name == "pest":
                from agroai_pest_detection import PestDetector

                detector = PestDetector()
            else:
                from plant_diseasedetection import PlantDiseaseDetector

                detector = PlantDiseaseDetector()
            print(f"{name}: loaded {detector.num_classes} classes")
            continue
        results.append(runners[name](args.image, args.conf))

    if args.download_only:
        return 0

    if args.json:
        print(json.dumps({"is_demo": True, "warning": DEMO_BANNER, "results": results}, indent=2))
    else:
        for result in results:
            _print_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
