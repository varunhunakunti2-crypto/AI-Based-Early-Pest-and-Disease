"""Assessment engine backed by the isolated pretrained YOLO service.

The two YOLO detectors in ``ml/`` run on ``ultralytics`` (**AGPL-3.0**), so they
are kept out of this process. ``ml/serve`` exposes them over HTTP and this engine
is a thin client. Nothing here imports torch or ultralytics.

The output is demo-only by design:

* the model taxonomies (102 IP102 pests / 116 plant-disease classes) are not the
  project's approved D1a allowlist;
* no calibration or operating point is approved;
* the service reports ``label_status`` for every detection, which the engine
  renders as an explicit "unverified model label" in the candidate name.

``is_demo`` is hard-coded to ``True``: no settings value can promote this engine
to a non-demo result before the taxonomy and calibration gates close.
"""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.modules.conversations.engine import (
    _PROVIDER_IMAGE_TEXT,
    _PROVIDER_INVALID_TEXT,
    _PROVIDER_UNAVAILABLE_TEXT,
    _QUALITY_REASON,
    EngineResult,
    UploadContext,
)
from app.modules.conversations.media import MediaValidationError, encode_for_model

DEMO_MODEL_VERSION = "pretrained-yolo-0.1"
UNVERIFIED_LABEL_SUFFIX = " (unverified model label)"

_DEMO_TEXT = (
    "Demo-only detection from model {model}. The raw model label is shown "
    "unverified: the taxonomy and operating point are not approved. This is not "
    "a diagnosis and no treatment decision should be based on it."
)
_ABSTAIN_TEXT = (
    "The pretrained model found no detection above its threshold. This is an "
    "abstention, not a healthy verdict. Retake the photo or request expert review."
)


class PretrainedAssessmentEngine:
    """HTTP client for ``ml/serve``. Fails closed on any transport problem."""

    is_demo = True  # Permanent until D1a taxonomy and calibration are approved.

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
        model: str | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._model = (model or settings.pretrained_model).strip().lower()
        self.model_version = DEMO_MODEL_VERSION

    def assess(
        self,
        *,
        upload: UploadContext | None,
        crop_id: str | None = None,
        context: str | None = None,
    ) -> EngineResult:
        del crop_id, context  # No crop taxonomy exists yet; never infer one.

        if upload is None:
            return EngineResult(
                state="abstained",
                reason_code="no_image",
                reason_text="No photo was attached, so there is nothing to assess.",
                model_version=self.model_version,
                is_demo=True,
                next_steps=[],
            )

        if upload.quality_result != "pass":
            flag = upload.quality_result
            return EngineResult(
                state="abstained",
                reason_code="quality_gate_failed",
                reason_text=_QUALITY_REASON.get(
                    flag, "The photo did not pass the image-quality check. Retake it."
                ),
                quality_flag=flag,
                quality_flags=list(upload.quality_flags),
                model_version=self.model_version,
                is_demo=True,
                next_steps=["retake"],
            )

        try:
            image, media_type = encode_for_model(
                self._settings,
                upload.storage_path,
                max_side=self._settings.chat_max_image_side,
            )
        except (OSError, ValueError, MediaValidationError):
            return self._failed("image_unavailable", _PROVIDER_IMAGE_TEXT, retryable=True)

        try:
            payload = self._request(image, media_type)
        except Exception as error:  # noqa: BLE001 - mapped to a safe failure below
            if isinstance(error, httpx.TimeoutException):
                return self._failed("model_timeout", _PROVIDER_UNAVAILABLE_TEXT, retryable=True)
            if isinstance(error, httpx.HTTPStatusError):
                retryable = error.response.status_code >= 500 or error.response.status_code == 429
                return self._failed(
                    "model_unavailable", _PROVIDER_UNAVAILABLE_TEXT, retryable=retryable
                )
            if isinstance(error, httpx.HTTPError):
                return self._failed("model_unavailable", _PROVIDER_UNAVAILABLE_TEXT, retryable=True)
            return self._failed("invalid_model_response", _PROVIDER_INVALID_TEXT, retryable=True)

        return self._parse(payload)

    def _request(self, image: bytes, media_type: str) -> dict:
        url = f"{self._settings.pretrained_inference_url.rstrip('/')}/v1/detect"
        files = {"file": ("image.jpg", image, media_type)}
        data = {
            "model": self._model,
            "conf": str(self._settings.pretrained_conf),
        }
        if self._client is not None:
            response = self._client.post(url, files=files, data=data)
        else:
            with httpx.Client(timeout=self._settings.pretrained_timeout_s) as client:
                response = client.post(url, files=files, data=data)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("detection response is not an object")
        return payload

    def _parse(self, payload: dict) -> EngineResult:
        # The service must mark its own output as demo; refuse to show it otherwise.
        if payload.get("is_demo") is not True:
            return self._failed("invalid_model_response", _PROVIDER_INVALID_TEXT, retryable=True)

        detections = payload.get("detections")
        if not isinstance(detections, list):
            return self._failed("invalid_model_response", _PROVIDER_INVALID_TEXT, retryable=True)

        model_version = str(payload.get("model_version") or self.model_version)
        if not detections:
            return EngineResult(
                state="abstained",
                reason_code="model_abstained",
                reason_text=_ABSTAIN_TEXT,
                confidence_band="not_calibrated",
                calibrated=False,
                model_version=model_version,
                is_demo=True,
                next_steps=["retake", "request_review"],
            )

        best_by_label: dict[str, float] = {}
        for item in detections:
            if not isinstance(item, dict):
                continue
            name = item.get("class_name")
            confidence = item.get("confidence")
            if not isinstance(name, str) or not name:
                continue
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                continue
            score = min(1.0, max(0.0, float(confidence)))
            best_by_label[name] = max(best_by_label.get(name, 0.0), score)

        if not best_by_label:
            return self._failed("invalid_model_response", _PROVIDER_INVALID_TEXT, retryable=True)

        ordered = sorted(best_by_label.items(), key=lambda item: item[1], reverse=True)[:3]
        candidates = [
            {
                "label": name,
                "display_name": f"{name}{UNVERIFIED_LABEL_SUFFIX}",
                "score": round(score, 4),
            }
            for name, score in ordered
        ]
        return EngineResult(
            state="assessed",
            reason_text=_DEMO_TEXT.format(model=model_version),
            candidates=candidates,
            confidence_band="not_calibrated",
            calibrated=False,
            model_version=model_version,
            is_demo=True,
            next_steps=["add_context", "request_review"],
        )

    def _failed(self, code: str, text: str, *, retryable: bool) -> EngineResult:
        return EngineResult(
            state="failed",
            reason_code=code,
            reason_text=text,
            model_version=self.model_version,
            is_demo=True,
            next_steps=["retry", "request_review"],
            error_code=code,
            retryable=retryable,
        )
