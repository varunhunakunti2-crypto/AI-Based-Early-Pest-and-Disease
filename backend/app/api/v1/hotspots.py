"""Pest and disease hotspot API routes.

Endpoints for hotspot intelligence, classification, history, and regional
outbreak analysis.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_principal
from app.core.errors import ApiError
from app.db.models import User
from app.db.session import get_db
from app.geo.hotspot_service import (
    DEFAULT_HOTSPOT_THRESHOLDS,
    calculate_hotspot_for_cell,
    get_hotspot_classification_label,
    recalculate_all_hotspots,
    record_hotspot_history,
    update_hotspot_cluster,
)
from app.geo.service import get_hotspots_in_cell

router = APIRouter(tags=["hotspots"])


class HotspotCalculateRequest(BaseModel):
    h3_cell_id: str
    target_type: str = Field(pattern="^(disease|pest)$")
    target_code: str
    crop_code: Optional[str] = None
    resolution: Optional[int] = Field(default=None, ge=0, le=15)
    weather_risk_factor: Optional[float] = Field(default=None, ge=0, le=1)


class HotspotResponse(BaseModel):
    h3_cell_id: str
    resolution: int
    target_type: str
    target_code: str
    crop_code: Optional[str]
    classification: str
    score: float
    total_reports: int
    unique_affected_farms: int
    verified_farms: int
    unverified_reports: int
    pending_reviews: int
    severity_distribution: dict
    first_reported: Optional[str]
    most_recent_report: Optional[str]
    recency_factor: float
    weather_risk_factor: Optional[float]
    neighbor_cells: list[str]
    historical_frequency: float


class HotspotClassificationInfo(BaseModel):
    classification: str
    label: str
    color: str
    severity: str


class HotspotRecalculateRequest(BaseModel):
    target_type: str = Field(pattern="^(disease|pest)$")
    target_code: str
    crop_code: Optional[str] = None
    resolution: Optional[int] = Field(default=None, ge=0, le=15)


class NearbyHotspotsRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_km: float = Field(gt=0, le=100)
    resolution: Optional[int] = Field(default=None, ge=0, le=15)
    target_type: Optional[str] = Field(default=None, pattern="^(disease|pest)$")
    target_code: Optional[str] = None
    min_classification: Optional[str] = Field(default="low", pattern="^(low|moderate|high|critical)$")


@router.post("/calculate", response_model=HotspotResponse)
def calculate_hotspot(
    payload: HotspotCalculateRequest,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> HotspotResponse:
    """Calculate hotspot score and classification for an H3 cell."""
    try:
        result = calculate_hotspot_for_cell(
            db=db,
            h3_cell_id=payload.h3_cell_id,
            target_type=payload.target_type,
            target_code=payload.target_code,
            crop_code=payload.crop_code,
            resolution=payload.resolution,
            weather_risk_factor=payload.weather_risk_factor,
        )
    except ValueError as exc:
        raise ApiError(400, "invalid_request", str(exc)) from exc
    return HotspotResponse(**result)


@router.post("/update-cluster")
def update_hotspot(
    payload: HotspotCalculateRequest,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Calculate and persist a hotspot cluster for an H3 cell."""
    from app.db.models import HotspotCluster

    cluster = update_hotspot_cluster(
        db=db,
        h3_cell_id=payload.h3_cell_id,
        target_type=payload.target_type,
        target_code=payload.target_code,
        crop_code=payload.crop_code,
        resolution=payload.resolution,
        weather_risk_factor=payload.weather_risk_factor,
    )
    db.commit()
    return {
        "hotspot_id": cluster.id,
        "cell_id": cluster.h3_cell_id,
        "classification": cluster.classification,
        "score": float(cluster.score),
        "calculated_at": cluster.calculated_at.isoformat(),
    }


@router.post("/recalculate-batch")
def recalculate_batch(
    payload: HotspotRecalculateRequest,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Recalculate hotspots for all cells with reports for a target."""
    clusters = recalculate_all_hotspots(
        db=db,
        target_type=payload.target_type,
        target_code=payload.target_code,
        crop_code=payload.crop_code,
        resolution=payload.resolution,
    )
    db.commit()
    return {
        "target_type": payload.target_type,
        "target_code": payload.target_code,
        "cells_processed": len(clusters),
        "hotspots": [
            {
                "cell_id": c.h3_cell_id,
                "classification": c.classification,
                "score": float(c.score),
            }
            for c in clusters
        ],
    }


@router.get("/classifications")
def list_classifications() -> list[HotspotClassificationInfo]:
    """Return all hotspot classifications with labels and colors."""
    classifications = ["low", "moderate", "high", "critical"]
    return [
        HotspotClassificationInfo(
            classification=c,
            **get_hotspot_classification_label(c),
        )
        for c in classifications
    ]


@router.get("/cells/{cell_id}/hotspots")
def cell_hotspots(
    cell_id: str = Path(..., description="H3 cell ID"),
    resolution: Optional[int] = Query(default=None, ge=0, le=15),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Return hotspot clusters for an H3 cell."""
    hotspots = get_hotspots_in_cell(db, h3_cell_id=cell_id, resolution=resolution)
    return {"cell_id": cell_id, "hotspots": hotspots, "count": len(hotspots)}


@router.get("/nearby")
def nearby_hotspots(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radius_km: float = Query(gt=0, le=100, default=10),
    resolution: Optional[int] = Query(default=None, ge=0, le=15),
    target_type: Optional[str] = Query(default=None, pattern="^(disease|pest)$"),
    target_code: Optional[str] = Query(default=None),
    min_classification: str = Query(default="low", pattern="^(low|moderate|high|critical)$"),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Find hotspots near a location."""
    from app.geo.service import find_nearby_cells
    from app.db.models import HotspotCluster

    nearby = find_nearby_cells(
        lat=lat, lng=lng, radius_km=radius_km, resolution=resolution
    )

    classification_order = {"low": 0, "moderate": 1, "high": 2, "critical": 3}
    min_order = classification_order.get(min_classification, 0)

    hotspots = []
    for cell_info in nearby:
        cell_id = cell_info["cell_id"]
        query = select(HotspotCluster).where(HotspotCluster.h3_cell_id == cell_id)
        if target_type:
            query = query.where(HotspotCluster.target_type == target_type)
        if target_code:
            query = query.where(HotspotCluster.target_code == target_code)
        rows = db.scalars(query).all()
        for row in rows:
            if classification_order.get(row.classification, 0) >= min_order:
                hotspots.append({
                    "cell_id": row.h3_cell_id,
                    "target_type": row.target_type,
                    "target_code": row.target_code,
                    "crop_code": row.crop_code,
                    "classification": row.classification,
                    "score": float(row.score),
                    "distance_km": cell_info["distance_km"],
                    "unique_affected_farms": row.unique_affected_farms,
                    "calculated_at": row.calculated_at.isoformat(),
                })

    hotspots.sort(key=lambda x: (classification_order.get(x["classification"], 0), -x["distance_km"]), reverse=True)

    return {
        "center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "hotspots": hotspots,
        "count": len(hotspots),
    }


@router.post("/history/snapshot")
def record_hotspot_snapshot(
    h3_cell_id: str,
    target_type: str = "disease",
    target_code: str = "",
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Record a hotspot history snapshot for trend analysis."""
    if target_type not in ("disease", "pest"):
        raise ApiError(400, "invalid_target_type", "target_type must be 'disease' or 'pest'")
    if not target_code:
        raise ApiError(400, "missing_target_code", "target_code is required")
    from app.geo.hotspot_service import calculate_hotspot_for_cell

    result = calculate_hotspot_for_cell(
        db=db,
        h3_cell_id=h3_cell_id,
        target_type=target_type,
        target_code=target_code,
    )
    history = record_hotspot_history(
        db=db,
        h3_cell_id=h3_cell_id,
        target_type=target_type,
        target_code=target_code,
        classification=result["classification"],
        score=result["score"],
        unique_affected_farms=result["unique_affected_farms"],
        weather_risk_factor=result.get("weather_risk_factor"),
    )
    db.commit()
    return {
        "history_id": history.id,
        "cell_id": history.h3_cell_id,
        "classification": history.classification,
        "score": float(history.score),
        "snapshot_date": history.snapshot_date.isoformat(),
    }


@router.get("/history/{cell_id}")
def hotspot_history(
    cell_id: str = Path(..., description="H3 cell ID"),
    target_type: Optional[str] = Query(default=None, pattern="^(disease|pest)$"),
    target_code: Optional[str] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Return hotspot history for trend analysis."""
    from app.db.models import HotspotHistory

    cutoff = datetime.utcnow() - timedelta(days=days)
    query = select(HotspotHistory).where(
        HotspotHistory.h3_cell_id == cell_id,
        HotspotHistory.snapshot_date >= cutoff,
    )
    if target_type:
        query = query.where(HotspotHistory.target_type == target_type)
    if target_code:
        query = query.where(HotspotHistory.target_code == target_code)
    query = query.order_by(HotspotHistory.snapshot_date.desc())

    rows = db.scalars(query).all()
    return {
        "cell_id": cell_id,
        "days": days,
        "history": [
            {
                "snapshot_date": row.snapshot_date.isoformat(),
                "target_type": row.target_type,
                "target_code": row.target_code,
                "classification": row.classification,
                "score": float(row.score),
                "unique_affected_farms": row.unique_affected_farms,
                "weather_risk_factor": (
                    float(row.weather_risk_factor) if row.weather_risk_factor else None
                ),
            }
            for row in rows
        ],
        "count": len(rows),
    }


__all__ = ["router"]
