"""Demo-labelled detection endpoint for the pretrained YOLO models.

The scan screen uploads a photo through ``POST /v1/uploads`` and then calls this
endpoint with the returned ``upload_id``. The real inference runs in the isolated
service in ``ml/serve`` (``ultralytics`` is AGPL-3.0); this route only builds an
``UploadContext`` and delegates to the HTTP client engine.

Every response is demo-labelled. ``is_demo`` is always true and candidate names
carry an explicit "unverified model label" marker until the D1a taxonomy and an
operating point are approved.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.db.session import get_session
from app.modules.conversations import service
from app.modules.conversations.engine import UploadContext
from app.modules.conversations.models import Assessment, Candidate
from app.modules.conversations.pretrained_engine import PretrainedAssessmentEngine

router = APIRouter(prefix="/detections", tags=["conversations"])


class DetectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    upload_id: str = Field(min_length=1, max_length=64)
    # Omit to use ``settings.pretrained_model``. The scan screen asks the caller
    # for a pest or plant detector; neither is mapped to the project taxonomy.
    model: Literal["pest", "plant"] | None = None


def build_engine(settings: Settings, model: str | None) -> PretrainedAssessmentEngine:
    return PretrainedAssessmentEngine(settings, model=model)


@router.post("", response_model=Assessment)
def create_detection(
    payload: DetectionRequest,
    session: Session = Depends(get_session),
) -> Assessment:
    settings = get_settings()
    try:
        row = service.get_upload_row(session, payload.upload_id)
    except service.UploadNotFoundError as error:
        raise ApiError(
            code="upload_not_found",
            title="Upload not found",
            status=404,
        ) from error

    upload = UploadContext(
        upload_id=row.id,
        sha256=row.sha256,
        width=row.width,
        height=row.height,
        quality_result=row.quality_result,
        quality_flags=tuple(row.quality_flags or []),
        storage_path=row.storage_path,
    )
    result = build_engine(settings, payload.model).assess(upload=upload)

    return Assessment(
        state=result.state,
        reason_code=result.reason_code,
        reason_text=result.reason_text,
        quality_flag=result.quality_flag,
        quality_flags=result.quality_flags,
        candidates=[Candidate(**candidate) for candidate in result.candidates],
        confidence_band=result.confidence_band,
        calibrated=result.calibrated,
        model_version=result.model_version,
        generated_at=datetime.now(UTC),
        is_demo=result.is_demo,
        error_code=result.error_code,
        retryable=result.retryable,
    )
