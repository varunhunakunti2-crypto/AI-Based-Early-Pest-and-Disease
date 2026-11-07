"""Inspection result submission API routes.

Allows field agents and farmers to submit field inspection results
with photo/video evidence, symptom descriptions, and severity assessments.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_principal, require_roles
from app.core.errors import ApiError
from app.db.models import (
    InspectionResult,
    InspectionTask,
    User,
    WeatherCellRecord,
)
from app.db.session import get_db
from app.geo import geo_to_h3
from app.geo.hotspot_service import update_hotspot_cluster
from app.geo.weather_risk_service import calculate_regional_risk

router = APIRouter(tags=["inspections"])


class InspectionResultSubmitRequest(BaseModel):
    task_id: str
    h3_cell_id: str
    crop_code: str
    target_code: str
    found_issue: bool = False
    severity: Optional[str] = Field(
        default=None, pattern="^(none|low|moderate|high|critical)$"
    )
    ai_confidence: Optional[float] = Field(
        default=None, ge=0, le=1
    )
    symptoms_observed: Optional[str] = Field(default=None, max_length=2000)
    photos_taken: int = Field(default=0, ge=0)
    videos_taken: int = Field(default=0, ge=0)
    farmer_notified: bool = False


class InspectionResultResponse(BaseModel):
    result_id: str
    task_id: str
    h3_cell_id: str
    inspected_by: str
    inspection_date: str
    crop_code: str
    target_code: str
    found_issue: bool
    severity: Optional[str]
    ai_confidence: Optional[float]
    symptoms_observed: Optional[str]
    photos_taken: int
    videos_taken: int
    farmer_notified: bool


@router.post(
    "/results",
    response_model=InspectionResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_inspection_result(
    payload: InspectionResultSubmitRequest,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> InspectionResultResponse:
    """Submit a field inspection result with evidence.

    Accepted roles: farmer, field_agent, expert, admin.
    The result is linked to the task and H3 cell. Hotspot and risk
    calculations are updated asynchronously.
    """
    task = db.get(InspectionTask, payload.task_id)
    if task is None:
        raise ApiError(404, "task_not_found", "Inspection task not found")

    if task.assigned_to != user.id and user.role != "admin":
        raise ApiError(
            403,
            "not_assigned",
            "You are not assigned to this inspection task",
        )

    if task.status not in ("ACCEPTED", "IN_PROGRESS", "SUBMITTED"):
        raise ApiError(
            400,
            "invalid_task_status",
            f"Task must be in ACCEPTED, IN_PROGRESS, or SUBMITTED status (current: {task.status})",
        )

    # Create inspection result
    result = InspectionResult(
        task_id=payload.task_id,
        h3_cell_id=payload.h3_cell_id,
        inspected_by=user.id,
        crop_code=payload.crop_code,
        target_code=payload.target_code,
        found_issue=payload.found_issue,
        severity=payload.severity,
        ai_confidence=payload.ai_confidence,
        symptoms_observed=payload.symptoms_observed,
        photos_taken=payload.photos_taken,
        videos_taken=payload.videos_taken,
        farmer_notified=payload.farmer_notified,
        is_demo=task.is_demo,
    )
    db.add(result)
    db.flush()

    # Update task status to SUBMITTED
    task.status = "SUBMITTED"
    from app.geo.task_service import _record_status_change

    _record_status_change(
        db,
        task,
        task.status,
        "SUBMITTED",
        user.id,
        reason="Inspection result submitted",
    )

    # Update hotspot cluster for the cell if an issue was found
    if payload.found_issue:
        try:
            update_hotspot_cluster(
                db=db,
                h3_cell_id=payload.h3_cell_id,
                target_type="disease",  # default; could be inferred from target_code
                target_code=payload.target_code,
                crop_code=payload.crop_code,
                resolution=task.resolution,
                is_demo=task.is_demo,
            )
            # Also calculate regional risk
            calculate_regional_risk(
                db=db,
                h3_cell_id=payload.h3_cell_id,
                crop_code=payload.crop_code,
                target_code=payload.target_code,
                target_type="disease",
                resolution=task.resolution,
                is_demo=task.is_demo,
            )
        except Exception:
            # Don't fail the submission if hotspot/risk calculation fails
            pass

    db.commit()
    db.refresh(result)

    return InspectionResultResponse(
        result_id=result.id,
        task_id=result.task_id,
        h3_cell_id=result.h3_cell_id,
        inspected_by=result.inspected_by,
        inspection_date=result.inspection_date.isoformat(),
        crop_code=result.crop_code,
        target_code=result.target_code,
        found_issue=result.found_issue,
        severity=result.severity,
        ai_confidence=(
            float(result.ai_confidence) if result.ai_confidence else None
        ),
        symptoms_observed=result.symptoms_observed,
        photos_taken=result.photos_taken,
        videos_taken=result.videos_taken,
        farmer_notified=result.farmer_notified,
    )


@router.get("/results/{result_id}")
def get_inspection_result(
    result_id: str = Path(..., description="Inspection result ID"),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Return an inspection result by ID."""
    result = db.get(InspectionResult, result_id)
    if result is None:
        raise ApiError(404, "not_found", "Inspection result not found")

    # Authorization: inspector, task assignee, admin, or expert
    task = db.get(InspectionTask, result.task_id)
    if (
        result.inspected_by != user.id
        and (task is None or task.assigned_to != user.id)
        and user.role not in ("expert", "admin", "pathologist", "agronomist")
    ):
        raise ApiError(403, "forbidden", "Not authorized to view this result")

    return {
        "result_id": result.id,
        "task_id": result.task_id,
        "h3_cell_id": result.h3_cell_id,
        "inspected_by": result.inspected_by,
        "inspection_date": result.inspection_date.isoformat(),
        "crop_code": result.crop_code,
        "target_code": result.target_code,
        "found_issue": result.found_issue,
        "severity": result.severity,
        "ai_confidence": (
            float(result.ai_confidence) if result.ai_confidence else None
        ),
        "symptoms_observed": result.symptoms_observed,
        "photos_taken": result.photos_taken,
        "videos_taken": result.videos_taken,
        "farmer_notified": result.farmer_notified,
        "created_at": result.created_at.isoformat(),
    }


@router.get("/tasks/{task_id}/results")
def list_task_results(
    task_id: str = Path(..., description="Task ID"),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """List all inspection results for a task."""
    from sqlalchemy import select

    results = db.scalars(
        select(InspectionResult).where(InspectionResult.task_id == task_id)
    ).all()

    return {
        "task_id": task_id,
        "results": [
            {
                "result_id": r.id,
                "inspected_by": r.inspected_by,
                "inspection_date": r.inspection_date.isoformat(),
                "crop_code": r.crop_code,
                "target_code": r.target_code,
                "found_issue": r.found_issue,
                "severity": r.severity,
                "ai_confidence": (
                    float(r.ai_confidence) if r.ai_confidence else None
                ),
                "photos_taken": r.photos_taken,
                "videos_taken": r.videos_taken,
                "farmer_notified": r.farmer_notified,
                "created_at": r.created_at.isoformat(),
            }
            for r in results
        ],
        "count": len(results),
    }


__all__ = ["router"]
