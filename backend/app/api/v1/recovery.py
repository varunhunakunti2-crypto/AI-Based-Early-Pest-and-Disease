"""Recovery monitoring API routes.

Tracks farm recovery after treatment/intervention, with follow-up
inspection dates and recovery progress.
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
    RecoveryMonitoringRecord,
    User,
)
from app.db.session import get_db

router = APIRouter(tags=["recovery"])


class RecoveryRecordCreate(BaseModel):
    farm_id: str
    h3_cell_id: str
    crop_code: str
    target_code: str
    previous_severity: str = Field(
        pattern="^(none|low|moderate|high|critical)$"
    )
    current_severity: str = Field(
        pattern="^(none|low|moderate|high|critical)$"
    )
    recovery_percentage: float = Field(default=0.0, ge=0, le=100)
    recovery_status: str = Field(
        default="worsening",
        pattern="^(worsening|stable|partial_recovery|full_recovery)$",
    )
    follow_up_date: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=2000)


class RecoveryRecordResponse(BaseModel):
    record_id: str
    farm_id: str
    h3_cell_id: str
    crop_code: str
    target_code: str
    previous_severity: str
    current_severity: str
    recovery_percentage: float
    recovery_status: str
    follow_up_date: Optional[str]
    notes: Optional[str]
    created_at: str


@router.post(
    "/records",
    response_model=RecoveryRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recovery_record(
    payload: RecoveryRecordCreate,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> RecoveryRecordResponse:
    """Create a recovery monitoring record for a farm."""
    follow_up_dt = None
    if payload.follow_up_date:
        follow_up_dt = datetime.fromisoformat(payload.follow_up_date)

    record = RecoveryMonitoringRecord(
        farm_id=payload.farm_id,
        h3_cell_id=payload.h3_cell_id,
        crop_code=payload.crop_code,
        target_code=payload.target_code,
        previous_severity=payload.previous_severity,
        current_severity=payload.current_severity,
        recovery_percentage=payload.recovery_percentage,
        recovery_status=payload.recovery_status,
        follow_up_date=follow_up_dt,
        notes=payload.notes,
        is_demo=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return RecoveryRecordResponse(
        record_id=record.id,
        farm_id=record.farm_id,
        h3_cell_id=record.h3_cell_id,
        crop_code=record.crop_code,
        target_code=record.target_code,
        previous_severity=record.previous_severity,
        current_severity=record.current_severity,
        recovery_percentage=float(record.recovery_percentage),
        recovery_status=record.recovery_status,
        follow_up_date=(
            record.follow_up_date.isoformat() if record.follow_up_date else None
        ),
        notes=record.notes,
        created_at=record.created_at.isoformat(),
    )


@router.get("/records/{record_id}")
def get_recovery_record(
    record_id: str = Path(..., description="Recovery record ID"),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Return a recovery monitoring record by ID."""
    record = db.get(RecoveryMonitoringRecord, record_id)
    if record is None:
        raise ApiError(404, "not_found", "Recovery record not found")

    return {
        "record_id": record.id,
        "farm_id": record.farm_id,
        "h3_cell_id": record.h3_cell_id,
        "crop_code": record.crop_code,
        "target_code": record.target_code,
        "previous_severity": record.previous_severity,
        "current_severity": record.current_severity,
        "recovery_percentage": float(record.recovery_percentage),
        "recovery_status": record.recovery_status,
        "follow_up_date": (
            record.follow_up_date.isoformat() if record.follow_up_date else None
        ),
        "notes": record.notes,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


@router.get("/farms/{farm_id}/records")
def list_farm_recovery_records(
    farm_id: str = Path(..., description="Farm ID"),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """List all recovery monitoring records for a farm."""
    from sqlalchemy import select

    rows = db.scalars(
        select(RecoveryMonitoringRecord)
        .where(RecoveryMonitoringRecord.farm_id == farm_id)
        .order_by(RecoveryMonitoringRecord.created_at.desc())
    ).all()

    return {
        "farm_id": farm_id,
        "records": [
            {
                "record_id": r.id,
                "h3_cell_id": r.h3_cell_id,
                "crop_code": r.crop_code,
                "target_code": r.target_code,
                "previous_severity": r.previous_severity,
                "current_severity": r.current_severity,
                "recovery_percentage": float(r.recovery_percentage),
                "recovery_status": r.recovery_status,
                "follow_up_date": (
                    r.follow_up_date.isoformat() if r.follow_up_date else None
                ),
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.put("/records/{record_id}")
def update_recovery_record(
    record_id: str,
    payload: RecoveryRecordCreate,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> RecoveryRecordResponse:
    """Update a recovery monitoring record."""
    record = db.get(RecoveryMonitoringRecord, record_id)
    if record is None:
        raise ApiError(404, "not_found", "Recovery record not found")

    record.previous_severity = payload.previous_severity
    record.current_severity = payload.current_severity
    record.recovery_percentage = payload.recovery_percentage
    record.recovery_status = payload.recovery_status
    record.notes = payload.notes
    if payload.follow_up_date:
        record.follow_up_date = datetime.fromisoformat(payload.follow_up_date)
    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)

    return RecoveryRecordResponse(
        record_id=record.id,
        farm_id=record.farm_id,
        h3_cell_id=record.h3_cell_id,
        crop_code=record.crop_code,
        target_code=record.target_code,
        previous_severity=record.previous_severity,
        current_severity=record.current_severity,
        recovery_percentage=float(record.recovery_percentage),
        recovery_status=record.recovery_status,
        follow_up_date=(
            record.follow_up_date.isoformat() if record.follow_up_date else None
        ),
        notes=record.notes,
        created_at=record.created_at.isoformat(),
    )


__all__ = ["router"]
