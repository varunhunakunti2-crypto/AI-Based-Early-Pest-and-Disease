"""Expert verification API routes.

Allows agricultural experts and pathologists to verify inspection results
and observations, confirming or rejecting disease/pest detections.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_principal, require_roles
from app.core.errors import ApiError
from app.db.models import (
    ExpertVerification,
    InspectionResult,
    GeoObservation,
    User,
)
from app.db.session import get_db

router = APIRouter(tags=["expert-verification"])


class ExpertVerificationRequest(BaseModel):
    observation_id: Optional[str] = Field(default=None)
    inspection_result_id: Optional[str] = Field(default=None)
    verification_status: str = Field(
        pattern="^(confirmed|probable|rejected|duplicate|needs_visit|unresolved)$"
    )
    corrected_target_code: Optional[str] = Field(default=None, max_length=80)
    corrected_severity: Optional[str] = Field(
        default=None, pattern="^(none|low|moderate|high|critical)$"
    )
    notes: Optional[str] = Field(default=None, max_length=2000)


class ExpertVerificationResponse(BaseModel):
    verification_id: str
    observation_id: Optional[str]
    inspection_result_id: Optional[str]
    verified_by: str
    verification_status: str
    corrected_target_code: Optional[str]
    corrected_severity: Optional[str]
    notes: Optional[str]
    verified_at: str


@router.post(
    "/verify",
    response_model=ExpertVerificationResponse,
    status_code=status.HTTP_201_CREATED,
)
def verify_observation(
    payload: ExpertVerificationRequest,
    user=Depends(require_roles("expert", "pathologist", "agronomist", "admin")),
    db: Session = Depends(get_db),
) -> ExpertVerificationResponse:
    """Verify an observation or inspection result.

    Only experts, pathologists, agronomists, and admins can verify.
    Updates the observation verification status or inspection result.
    """
    if not payload.observation_id and not payload.inspection_result_id:
        raise ApiError(
            400,
            "missing_reference",
            "Either observation_id or inspection_result_id must be provided",
        )

    if payload.observation_id:
        obs = db.get(GeoObservation, payload.observation_id)
        if obs is None:
            raise ApiError(404, "not_found", "Observation not found")
        obs.verification_status = payload.verification_status
        obs.updated_at = datetime.now(timezone.utc)
        db.flush()

    if payload.inspection_result_id:
        result = db.get(InspectionResult, payload.inspection_result_id)
        if result is None:
            raise ApiError(404, "not_found", "Inspection result not found")

    verification = ExpertVerification(
        observation_id=payload.observation_id,
        inspection_result_id=payload.inspection_result_id,
        verified_by=user.id,
        verification_status=payload.verification_status,
        corrected_target_code=payload.corrected_target_code,
        corrected_severity=payload.corrected_severity,
        notes=payload.notes,
        is_demo=False,
    )
    db.add(verification)
    db.flush()
    db.commit()
    db.refresh(verification)

    return ExpertVerificationResponse(
        verification_id=verification.id,
        observation_id=verification.observation_id,
        inspection_result_id=verification.inspection_result_id,
        verified_by=verification.verified_by,
        verification_status=verification.verification_status,
        corrected_target_code=verification.corrected_target_code,
        corrected_severity=verification.corrected_severity,
        notes=verification.notes,
        verified_at=verification.verified_at.isoformat(),
    )


@router.get("/verifications/{verification_id}")
def get_verification(
    verification_id: str = Path(..., description="Verification ID"),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Return an expert verification by ID."""
    verification = db.get(ExpertVerification, verification_id)
    if verification is None:
        raise ApiError(404, "not_found", "Verification not found")

    return {
        "verification_id": verification.id,
        "observation_id": verification.observation_id,
        "inspection_result_id": verification.inspection_result_id,
        "verified_by": verification.verified_by,
        "verification_status": verification.verification_status,
        "corrected_target_code": verification.corrected_target_code,
        "corrected_severity": verification.corrected_severity,
        "notes": verification.notes,
        "verified_at": verification.verified_at.isoformat(),
        "created_at": verification.created_at.isoformat(),
    }


@router.get("/pending")
def list_pending_verifications(
    target_type: Optional[str] = Query(
        default=None, pattern="^(disease|pest)$"
    ),
    target_code: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(require_roles("expert", "pathologist", "agronomist", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    """List observations pending expert verification."""
    query = select(GeoObservation).where(
        GeoObservation.verification_status.in_(["pending_review", "unverified"])
    )
    if target_code:
        query = query.where(GeoObservation.target_code == target_code)
    query = query.order_by(GeoObservation.event_date.desc()).limit(limit)

    rows = db.scalars(query).all()
    return {
        "observations": [
            {
                "observation_id": r.id,
                "h3_cell_id": r.h3_cell_id,
                "crop_code": r.crop_code,
                "target_code": r.target_code,
                "event_date": r.event_date.isoformat(),
                "reported_at": r.reported_at.isoformat(),
                "reporter_type": r.reporter_type,
                "verification_status": r.verification_status,
                "severity": r.severity,
                "ai_confidence": (
                    float(r.ai_confidence) if r.ai_confidence else None
                ),
            }
            for r in rows
        ],
        "count": len(rows),
    }


__all__ = ["router"]
