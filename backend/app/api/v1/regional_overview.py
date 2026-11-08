"""Regional overview API - combined H3 hexagon, hotspot, weather, and task intelligence.

Provides a unified view of agricultural risk across H3 hexagons for map dashboards.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_principal
from app.db.models import (
    HotspotCluster,
    RegionalRiskScore,
)
from app.db.session import get_db
from app.geo import generate_grid

router = APIRouter(tags=["regional-overview"])


class HexagonSummary(BaseModel):
    cell_id: str
    center_lat: float
    center_lng: float
    resolution: int
    area_m2: float
    disease_hotspot: dict | None = None
    pest_hotspot: dict | None = None
    risk_score: float | None = None
    risk_label: str | None = None
    weather_risk: float | None = None


class RegionalOverviewResponse(BaseModel):
    bounds: dict
    resolution: int
    hexagons: list[HexagonSummary]
    count: int


class HotspotSummary(BaseModel):
    cell_id: str
    target_type: str
    target_code: str
    crop_code: str | None
    classification: str
    score: float
    unique_affected_farms: int


class HotspotsListResponse(BaseModel):
    hotspots: list[HotspotSummary]
    count: int


@router.get("/hexagons", response_model=RegionalOverviewResponse)
def regional_hexagons(
    lat_min: float = Query(ge=-90, le=90),
    lng_min: float = Query(ge=-180, le=180),
    lat_max: float = Query(ge=-90, le=90),
    lng_max: float = Query(ge=-180, le=180),
    resolution: int = Query(default=9, ge=0, le=15),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> RegionalOverviewResponse:
    """Return H3 hexagons with hotspot and risk intelligence for a bounding box."""
    cell_ids = generate_grid(lat_min, lng_min, lat_max, lng_max, resolution=resolution)

    hexagons = []
    for cell_id_int in cell_ids:
        cell_id_str = str(cell_id_int)

        # Get cell center and area
        from app.geo import h3_to_center, hex_area_m2

        center_lat, center_lng = h3_to_center(cell_id_int)
        area = hex_area_m2(resolution)

        # Get hotspots for this cell
        disease_hotspot = None
        pest_hotspot = None
        risk_score = None
        risk_label = None
        weather_risk = None

        # Disease hotspot
        dh = db.scalars(
            select(HotspotCluster).where(
                HotspotCluster.h3_cell_id == cell_id_str,
                HotspotCluster.target_type == "disease",
                HotspotCluster.resolution == resolution,
            )
        ).first()
        if dh:
            disease_hotspot = {
                "target_code": dh.target_code,
                "crop_code": dh.crop_code,
                "classification": dh.classification,
                "score": float(dh.score),
                "unique_affected_farms": dh.unique_affected_farms,
            }

        # Pest hotspot
        ph = db.scalars(
            select(HotspotCluster).where(
                HotspotCluster.h3_cell_id == cell_id_str,
                HotspotCluster.target_type == "pest",
                HotspotCluster.resolution == resolution,
            )
        ).first()
        if ph:
            pest_hotspot = {
                "target_code": ph.target_code,
                "crop_code": ph.crop_code,
                "classification": ph.classification,
                "score": float(ph.score),
                "unique_affected_farms": ph.unique_affected_farms,
            }

        # Regional risk (latest for any crop/target)
        rr = db.scalars(
            select(RegionalRiskScore)
            .where(
                RegionalRiskScore.h3_cell_id == cell_id_str,
                RegionalRiskScore.resolution == resolution,
            )
            .order_by(RegionalRiskScore.valid_from.desc())
        ).first()
        if rr:
            risk_score = float(rr.risk_score)
            risk_label = rr.risk_label
            weather_risk = float(rr.weather_risk)

        hexagons.append(
            HexagonSummary(
                cell_id=cell_id_str,
                center_lat=float(center_lat),
                center_lng=float(center_lng),
                resolution=resolution,
                area_m2=float(area),
                disease_hotspot=disease_hotspot,
                pest_hotspot=pest_hotspot,
                risk_score=risk_score,
                risk_label=risk_label,
                weather_risk=weather_risk,
            )
        )

    return RegionalOverviewResponse(
        bounds={
            "lat_min": lat_min,
            "lng_min": lng_min,
            "lat_max": lat_max,
            "lng_max": lng_max,
        },
        resolution=resolution,
        hexagons=hexagons,
        count=len(hexagons),
    )


@router.get("/hotspots", response_model=HotspotsListResponse)
def regional_hotspots(
    lat_min: float = Query(ge=-90, le=90),
    lng_min: float = Query(ge=-180, le=180),
    lat_max: float = Query(ge=-90, le=90),
    lng_max: float = Query(ge=-180, le=180),
    resolution: int = Query(default=9, ge=0, le=15),
    target_type: str | None = Query(default=None, pattern="^(disease|pest)$"),
    min_classification: str = Query(default="low", pattern="^(low|moderate|high|critical)$"),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> HotspotsListResponse:
    """Return hotspots within a bounding box."""
    cell_ids = generate_grid(lat_min, lng_min, lat_max, lng_max, resolution=resolution)
    cell_id_strs = [str(cid) for cid in cell_ids]

    classification_order = {"low": 0, "moderate": 1, "high": 2, "critical": 3}
    min_order = classification_order.get(min_classification, 0)

    query = select(HotspotCluster).where(
        HotspotCluster.h3_cell_id.in_(cell_id_strs),
        HotspotCluster.resolution == resolution,
    )
    if target_type:
        query = query.where(HotspotCluster.target_type == target_type)

    rows = db.scalars(query).all()
    hotspots = []
    for row in rows:
        if classification_order.get(row.classification, 0) >= min_order:
            hotspots.append(
                HotspotSummary(
                    cell_id=row.h3_cell_id,
                    target_type=row.target_type,
                    target_code=row.target_code,
                    crop_code=row.crop_code,
                    classification=row.classification,
                    score=float(row.score),
                    unique_affected_farms=row.unique_affected_farms,
                )
            )

    return HotspotsListResponse(
        hotspots=hotspots,
        count=len(hotspots),
    )


@router.get("/summary")
def regional_summary(
    lat_min: float = Query(ge=-90, le=90),
    lng_min: float = Query(ge=-180, le=180),
    lat_max: float = Query(ge=-90, le=90),
    lng_max: float = Query(ge=-180, le=180),
    resolution: int = Query(default=9, ge=0, le=15),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Return aggregated regional summary statistics."""
    cell_ids = generate_grid(lat_min, lng_min, lat_max, lng_max, resolution=resolution)
    cell_id_strs = [str(cid) for cid in cell_ids]

    # Count hotspots by classification
    disease_hotspots = db.scalars(
        select(HotspotCluster).where(
            HotspotCluster.h3_cell_id.in_(cell_id_strs),
            HotspotCluster.resolution == resolution,
            HotspotCluster.target_type == "disease",
        )
    ).all()

    pest_hotspots = db.scalars(
        select(HotspotCluster).where(
            HotspotCluster.h3_cell_id.in_(cell_id_strs),
            HotspotCluster.resolution == resolution,
            HotspotCluster.target_type == "pest",
        )
    ).all()

    # Count by classification
    classification_counts = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    for h in disease_hotspots + pest_hotspots:
        classification_counts[h.classification] = classification_counts.get(h.classification, 0) + 1

    # Total unique affected farms
    total_farms_disease = sum(h.unique_affected_farms for h in disease_hotspots)
    total_farms_pest = sum(h.unique_affected_farms for h in pest_hotspots)

    # Critical/hot hotspots needing attention
    critical_hotspots = [
        h for h in disease_hotspots + pest_hotspots if h.classification in ("high", "critical")
    ]

    return {
        "bounds": {
            "lat_min": lat_min,
            "lng_min": lng_min,
            "lat_max": lat_max,
            "lng_max": lng_max,
        },
        "resolution": resolution,
        "total_cells": len(cell_ids),
        "disease_hotspots": len(disease_hotspots),
        "pest_hotspots": len(pest_hotspots),
        "classification_counts": classification_counts,
        "total_unique_affected_farms": total_farms_disease + total_farms_pest,
        "critical_hotspots_count": len(critical_hotspots),
        "critical_hotspots": [
            {
                "cell_id": h.h3_cell_id,
                "target_type": h.target_type,
                "target_code": h.target_code,
                "classification": h.classification,
                "score": float(h.score),
            }
            for h in critical_hotspots[:10]
        ],
    }


__all__ = ["router"]
