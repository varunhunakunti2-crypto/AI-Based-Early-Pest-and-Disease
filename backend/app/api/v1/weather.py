"""Weather API routes for H3 cell-level weather intelligence.

Integrates Open-Meteo weather data stored at H3 cell level with
weather-supported risk indicators.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_principal
from app.core.errors import ApiError
from app.db.models import User, WeatherCellRecord
from app.db.session import get_db
from app.geo import geo_to_h3, h3_get_resolution
from app.geo.weather_risk_service import calculate_regional_risk

router = APIRouter(tags=["weather"])


class WeatherRecordResponse(BaseModel):
    record_id: str
    h3_cell_id: str
    resolution: int
    source: str
    source_timestamp: str
    fetched_at: str
    variables: dict
    completeness: float
    is_stale: bool


class WeatherRiskRequest(BaseModel):
    h3_cell_id: str
    crop_code: str
    target_code: str
    target_type: str = Field(pattern="^(disease|pest)$")
    resolution: Optional[int] = Field(default=None, ge=0, le=15)
    growth_stage: Optional[str] = Field(default=None, max_length=50)


class WeatherRiskResponse(BaseModel):
    h3_cell_id: str
    crop_code: str
    target_code: str
    risk_score: float
    weather_risk: float
    biological_risk: float
    historical_risk: float
    risk_label: str
    contributing_factors: dict
    valid_from: str
    valid_to: str


class WeatherCellRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    resolution: Optional[int] = Field(default=None, ge=0, le=15)


@router.get("/hexagon/{cell_id}", response_model=Optional[WeatherRecordResponse])
def get_weather_for_hexagon(
    cell_id: str = Path(..., description="H3 cell ID"),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> Optional[WeatherRecordResponse]:
    """Return the latest weather record for an H3 cell."""
    from sqlalchemy import select

    row = db.scalars(
        select(WeatherCellRecord)
        .where(WeatherCellRecord.h3_cell_id == cell_id)
        .order_by(WeatherCellRecord.source_timestamp.desc())
    ).first()

    if row is None:
        return None

    return WeatherRecordResponse(
        record_id=row.id,
        h3_cell_id=row.h3_cell_id,
        resolution=row.resolution,
        source=row.source,
        source_timestamp=row.source_timestamp.isoformat(),
        fetched_at=row.fetched_at.isoformat(),
        variables=row.variables,
        completeness=float(row.completeness),
        is_stale=row.is_stale,
    )


@router.get("/farm/{farm_id}")
def get_weather_for_farm(
    farm_id: str = Path(..., description="Farm ID"),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Return weather for a farm's primary H3 cell."""
    from app.db.models import FarmHexagonAssignment

    assignment = db.scalars(
        select(FarmHexagonAssignment).where(
            FarmHexagonAssignment.farm_id == farm_id,
            FarmHexagonAssignment.is_primary.is_(True),
        )
    ).first()

    if assignment is None:
        raise ApiError(404, "farm_not_found", "Farm has no H3 cell assignment")

    row = db.scalars(
        select(WeatherCellRecord)
        .where(WeatherCellRecord.h3_cell_id == assignment.h3_cell_id)
        .order_by(WeatherCellRecord.source_timestamp.desc())
    ).first()

    if row is None:
        return {"farm_id": farm_id, "cell_id": assignment.h3_cell_id, "weather": None}

    return {
        "farm_id": farm_id,
        "cell_id": assignment.h3_cell_id,
        "weather": {
            "source": row.source,
            "source_timestamp": row.source_timestamp.isoformat(),
            "variables": row.variables,
            "completeness": float(row.completeness),
            "is_stale": row.is_stale,
        },
    }


@router.post("/cell-from-coordinates")
def weather_cell_from_coordinates(
    payload: WeatherCellRequest,
    user=Depends(get_principal),
) -> dict:
    """Return the H3 cell ID for given coordinates (for weather lookup)."""
    resolution = payload.resolution or 9
    cell_id = geo_to_h3(payload.lat, payload.lng, resolution=resolution)
    return {
        "cell_id": str(cell_id),
        "resolution": resolution,
        "center_lat": payload.lat,
        "center_lng": payload.lng,
    }


@router.post("/regional-risk", response_model=WeatherRiskResponse)
def calculate_regional_risk_endpoint(
    payload: WeatherRiskRequest,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> WeatherRiskResponse:
    """Calculate weather-supported regional risk for an H3 cell."""
    try:
        risk = calculate_regional_risk(
            db=db,
            h3_cell_id=payload.h3_cell_id,
            crop_code=payload.crop_code,
            target_code=payload.target_code,
            target_type=payload.target_type,
            resolution=payload.resolution,
            growth_stage=payload.growth_stage,
        )
    except ValueError as exc:
        raise ApiError(400, "risk_error", str(exc)) from exc
    db.commit()
    return WeatherRiskResponse(
        h3_cell_id=risk.h3_cell_id,
        crop_code=risk.crop_code,
        target_code=risk.target_code,
        risk_score=float(risk.risk_score),
        weather_risk=float(risk.weather_risk),
        biological_risk=float(risk.biological_risk),
        historical_risk=float(risk.historical_risk),
        risk_label=risk.risk_label,
        contributing_factors=risk.contributing_factors,
        valid_from=risk.valid_from.isoformat(),
        valid_to=risk.valid_to.isoformat(),
    )


@router.get("/regional-risk/{cell_id}")
def get_regional_risk(
    cell_id: str = Path(..., description="H3 cell ID"),
    crop_code: str = Query(...),
    target_code: str = Query(...),
    target_type: str = Query(pattern="^(disease|pest)$"),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Return the latest regional risk score for an H3 cell."""
    from sqlalchemy import select

    row = db.scalars(
        select(WeatherCellRecord.__class__.__bases__[0])  # placeholder
    ).first()
    # Use RegionalRiskScore model
    from app.db.models import RegionalRiskScore

    row = db.scalars(
        select(RegionalRiskScore).where(
            RegionalRiskScore.h3_cell_id == cell_id,
            RegionalRiskScore.crop_code == crop_code,
            RegionalRiskScore.target_code == target_code,
        ).order_by(RegionalRiskScore.valid_from.desc())
    ).first()

    if row is None:
        return {"cell_id": cell_id, "risk": None}

    return {
        "cell_id": row.h3_cell_id,
        "crop_code": row.crop_code,
        "target_code": row.target_code,
        "risk_score": float(row.risk_score),
        "risk_label": row.risk_label,
        "weather_risk": float(row.weather_risk),
        "biological_risk": float(row.biological_risk),
        "historical_risk": float(row.historical_risk),
        "contributing_factors": row.contributing_factors,
        "valid_from": row.valid_from.isoformat(),
        "valid_to": row.valid_to.isoformat(),
    }


__all__ = ["router"]
