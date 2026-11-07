"""Core detector: loads and runs the YOLOv11x plant-disease model.

Weights are downloaded on first load from Hugging Face
(``Ananthakrishnanmzen/PlantDiseaseDetection``) unless a local ``best.pt`` is
present in ``ml/plant_diseasedetection/weights/``.

Heavy dependencies (ultralytics, huggingface_hub) are imported lazily so this
module can be imported even when they are not installed; they are required only
when instantiating :class:`PlantDiseaseDetector`.
"""

from __future__ import annotations

from pathlib import Path

# Repository root (two levels up from this file:
# .../ml/plant_diseasedetection/model.py)
REPO_ROOT = Path(__file__).resolve().parents[2]
WEIGHTS_DIR = REPO_ROOT / "ml" / "plant_diseasedetection" / "weights"
DEFAULT_HF_REPO = "Ananthakrishnanmzen/PlantDiseaseDetection"
DEFAULT_WEIGHTS_FILENAME = "PlantDiseaseDetection.pt"


def _import_ultralytics():
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise ImportError(
            "ultralytics is required to load the YOLOv11x detector. "
            "Install it with: pip install -r ml/plant_diseasedetection/requirements.txt"
        ) from exc
    return YOLO


def _import_hf_hub_download():
    try:
        from huggingface_hub import hf_hub_download  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise ImportError(
            "huggingface-hub is required to download model weights. "
            "Install it with: pip install -r ml/plant_diseasedetection/requirements.txt"
        ) from exc
    return hf_hub_download


class PlantDiseaseDetector:
    """YOLOv11x plant disease detector (116 classes)."""

    def __init__(
        self,
        weights: str | Path | None = None,
        hf_repo: str = DEFAULT_HF_REPO,
        hf_filename: str = DEFAULT_WEIGHTS_FILENAME,
        device: str | None = None,
        verbose: bool = False,
    ) -> None:
        self.hf_repo = hf_repo
        self.hf_filename = hf_filename
        self.device = device
        self.verbose = verbose
        self.model = self._load_model(weights)
        self._names: dict[int, str] | None = None

    # ------------------------------------------------------------------ loading
    def _local_weights(self) -> Path | None:
        if not WEIGHTS_DIR.exists():
            return None
        candidates = sorted(WEIGHTS_DIR.glob("*.pt"))
        if candidates:
            return candidates[0]
        return None

    def _load_model(self, weights: str | Path | None):
        YOLO = _import_ultralytics()

        if weights is not None:
            weight_path = Path(weights)
            if not weight_path.exists():
                raise FileNotFoundError(f"Weight file not found: {weight_path}")
            return YOLO(str(weight_path), verbose=self.verbose)

        local = self._local_weights()
        if local is not None:
            return YOLO(str(local), verbose=self.verbose)

        # Download from Hugging Face on first use (requires network).
        hf_hub_download = _import_hf_hub_download()
        downloaded = hf_hub_download(
            repo_id=self.hf_repo,
            filename=self.hf_filename,
        )
        return YOLO(downloaded, verbose=self.verbose)

    # ------------------------------------------------------------------ inference
    def predict(
        self,
        source: str | Path,
        *,
        conf: float = 0.25,
        iou: float = 0.7,
        imgsz: int = 640,
        save: bool = False,
        save_txt: bool = False,
        save_conf: bool = False,
        save_crop: bool = False,
        show: bool = False,
        project: str | Path | None = None,
        name: str | None = None,
        **kwargs,
    ):
        """Run inference on an image path/URL/PIL image/np array.

        Returns an iterable of :class:`ultralytics.engine.results.Results`.
        """
        return self.model.predict(
            source=str(source),
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            save=save,
            save_txt=save_txt,
            save_conf=save_conf,
            save_crop=save_crop,
            show=show,
            project=str(project) if project is not None else None,
            name=name,
            device=self.device,
            verbose=self.verbose,
            **kwargs,
        )

    # ------------------------------------------------------------------ class names
    @property
    def names(self) -> dict[int, str]:
        if self._names is None:
            if hasattr(self.model, "model") and self.model.model is not None:
                model_names = getattr(self.model.model, "names", {}) or {}
            else:
                model_names = getattr(self.model, "names", {}) or {}
            self._names = {int(k): str(v) for k, v in model_names.items()}
        return self._names

    def class_name(self, class_id: int) -> str:
        return self.names.get(int(class_id), f"class_{int(class_id)}")

    @property
    def num_classes(self) -> int:
        return len(self.names)


def load_detector(
    weights: str | Path | None = None,
    *,
    hf_repo: str = DEFAULT_HF_REPO,
    hf_filename: str = DEFAULT_WEIGHTS_FILENAME,
    device: str | None = None,
    verbose: bool = False,
) -> PlantDiseaseDetector:
    """Convenience constructor for :class:`PlantDiseaseDetector`."""
    return PlantDiseaseDetector(
        weights=weights,
        hf_repo=hf_repo,
        hf_filename=hf_filename,
        device=device,
        verbose=verbose,
    )


__all__ = [
    "PlantDiseaseDetector",
    "load_detector",
    "DEFAULT_HF_REPO",
    "DEFAULT_WEIGHTS_FILENAME",
]
