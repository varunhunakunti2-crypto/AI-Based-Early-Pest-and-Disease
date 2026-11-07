"""H3 hexagonal grid service layer.

Business logic for H3 cell management, farm-to-cell assignment, observation
assignment, and hexagon-level data aggregation.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.h3_config import default_resolution, get_resolution
from app.db.models import (
    Crop,
    DiseaseReport,
    FarmHexagonAssignment,
    GeoObservation,
    H3Cell,
    HotspotCluster,
    PestReport,
    Target,
    User,
)
from app.db.session import get_db
from app.geo import (
    cell_info,
    generate_grid,
    geo_to_h3,
    great_circle_distance_m,
    h3_get_resolution,
    h3_to_center,
    h3_to_children,
    h3_to_geo,
    h3_to_geo_boundary,
    h3_to_parent,
    h3_is_valid,
    k_ring,
)


class H3ServiceError(ValueError):
    """Raised for H3 service business logic errors."""


def resolve_cell_id(cell_id_input: str | int) -> int:
    """Parse a cell ID from string or int input."""
    try:
        return int(cell_id_input)
    except (TypeError, ValueError) as exc:
        raise H3ServiceError(f"Invalid H3 cell ID: {cell_id_input}") from exc


def validate_cell(cell_id: int) -> None:
    """Validate that a cell ID is structurally valid."""
    if not h3_is_valid(cell_id):
        raise H3ServiceError(f"Invalid H3 cell ID: {cell_id}")


def get_cell_info(cell_id: int) -> dict:
    """Return detailed information about an H3 cell."""
    validate_cell(cell_id)
    info = cell_info(cell_id)
    center_lat, center_lng = h3_to_center(cell_id)
    boundary = h3_to_geo_boundary(cell_id)
    return {
        "cell_id": str(info.cell_id),
        "resolution": info.resolution,
        "center_lat": float(info.center_lat),
        "center_lng": float(info.center_lng),
        "area_m2": float(info.area_m2),
        "boundary": [[float(lat), float(lng)] for lat, lng in info.boundary],
    }


def get_neighbours(cell_id: int, k: int = 1) -> list[dict]:
    """Return neighbouring H3 cells within k rings."""
    validate_cell(cell_id)
    if k < 0 or k > 3:
        raise H3ServiceError("k must be between 0 and 3")
    neighbour_ids = k_ring(cell_id, k=k)
    # Exclude the center cell itself
    neighbour_ids = [cid for cid in neighbour_ids if cid != cell_id]
    return [get_cell_info(cid) for cid in neighbour_ids]


def get_parent(cell_id: int, parent_resolution: Optional[int] = None) -> dict:
    """Return the parent cell at a coarser resolution."""
    validate_cell(cell_id)
    current_res = h3_get_resolution(cell_id)
    if parent_resolution is None:
        parent_resolution = current_res - 1
    if parent_resolution >= current_res:
        raise H3ServiceError("Parent resolution must be lower than current resolution")
    if parent_resolution < 0:
        raise H3ServiceError("Parent resolution must be >= 0")
    parent_id = h3_to_parent(cell_id, parent_resolution)
    return get_cell_info(parent_id)


def get_children(cell_id: int, child_resolution: Optional[int] = None) -> list[dict]:
    """Return child cells at a finer resolution."""
    validate_cell(cell_id)
    current_res = h3_get_resolution(cell_id)
    if child_resolution is None:
        child_resolution = current_res + 1
    if child_resolution <= current_res:
        raise H3ServiceError("Child resolution must be higher than current resolution")
    if child_resolution > 15:
        raise H3ServiceError("Child resolution cannot exceed 15")
    child_ids = h3_to_children(cell_id, child_resolution)
    return [get_cell_info(cid) for cid in child_ids]


def generate_grid_in_bbox(
    lat_min: float,
    lng_min: float,
    lat_max: float,
    lng_max: float,
    resolution: Optional[int] = None,
) -> list[dict]:
    """Generate H3 cells covering a bounding box."""
    if resolution is None:
        resolution = default_resolution()
    if not (-90 <= lat_min <= lat_max <= 90):
        raise H3ServiceError("Invalid latitude bounds")
    if not (-180 <= lng_min <= lng_max <= 180):
        raise H3ServiceError("Invalid longitude bounds")
    cell_ids = generate_grid(lat_min, lng_min, lat_max, lng_max, resolution=resolution)
    return [get_cell_info(cid) for cid in cell_ids]


def assign_farm_to_cell(
    db: Session,
    farm_id: str,
    geo_code: str,
    lat: float,
    lng: float,
    resolution: Optional[int] = None,
    is_primary: bool = True,
) -> dict:
    """Assign a farm to an H3 cell based on its GPS coordinates.

    Creates or updates a FarmHexagonAssignment record and ensures the H3 cell
    exists in the h3_cells registry.
    """
    if resolution is None:
        resolution = default_resolution()

    cell_id = geo_to_h3(lat, lng, resolution=resolution)
    cell_id_str = str(cell_id)

    # Ensure the H3 cell exists in the registry
    existing_cell = db.scalar(select(H3Cell).where(H3Cell.cell_id == cell_id_str))
    if existing_cell is None:
        info = cell_info(cell_id)
        boundary = h3_to_geo_boundary(cell_id)
        import json

        new_cell = H3Cell(
            cell_id=cell_id_str,
            resolution=resolution,
            center_lat=float(info.center_lat),
            center_lng=float(info.center_lng),
            area_m2=float(info.area_m2),
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [[[lng, lat] for lat, lng in boundary]],
            },
            parent_cell_id=str(h3_to_parent(cell_id, resolution - 1))
            if resolution > 0
            else None,
            is_active=True,
            is_demo=False,
        )
        db.add(new_cell)
        db.flush()

    # If this is the primary assignment, unset other primary assignments for this farm
    if is_primary:
        db.execute(
            __import__("sqlalchemy", fromlist=["update"]).update(FarmHexagonAssignment)
            .where(FarmHexagonAssignment.farm_id == farm_id)
            .where(FarmHexagonAssignment.is_primary.is_(True))
            .values(is_primary=False)
        )

    # Check for existing assignment
    existing = db.scalar(
        select(FarmHexagonAssignment).where(
            FarmHexagonAssignment.farm_id == farm_id,
            FarmHexagonAssignment.h3_cell_id == cell_id_str,
        )
    )
    if existing is None:
        assignment = FarmHexagonAssignment(
            farm_id=farm_id,
            geo_code=geo_code,
            h3_cell_id=cell_id_str,
            resolution=resolution,
            is_primary=is_primary,
            is_demo=False,
        )
        db.add(assignment)
        db.flush()
        assignment_id = assignment.id
    else:
        existing.is_primary = is_primary
        db.flush()
        assignment_id = existing.id

    return {
        "assignment_id": assignment_id,
        "farm_id": farm_id,
        "h3_cell_id": cell_id_str,
        "resolution": resolution,
        "is_primary": is_primary,
    }


def get_farms_in_cell(
    db: Session, h3_cell_id: str, resolution: Optional[int] = None
) -> list[dict]:
    """Return farms assigned to an H3 cell."""
    query = select(FarmHexagonAssignment).where(
        FarmHexagonAssignment.h3_cell_id == h3_cell_id
    )
    if resolution is not None:
        query = query.where(FarmHexagonAssignment.resolution == resolution)
    rows = db.scalars(query).all()
    return [
        {
            "assignment_id": row.id,
            "farm_id": row.farm_id,
            "geo_code": row.geo_code,
            "h3_cell_id": row.h3_cell_id,
            "resolution": row.resolution,
            "overlap_percentage": (
                float(row.overlap_percentage) if row.overlap_percentage else None
            ),
            "is_primary": row.is_primary,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def get_cell_for_coordinates(
    lat: float, lng: float, resolution: Optional[int] = None
) -> dict:
    """Return the H3 cell containing given coordinates."""
    if resolution is None:
        resolution = default_resolution()
    cell_id = geo_to_h3(lat, lng, resolution=resolution)
    return get_cell_info(cell_id)


def aggregate_observations_in_cell(
    db: Session, h3_cell_id: str, resolution: Optional[int] = None
) -> dict:
    """Aggregate observations for an H3 cell."""
    query = select(GeoObservation).where(GeoObservation.h3_cell_id == h3_cell_id)
    if resolution is not None:
        query = query.where(GeoObservation.resolution == resolution)
    rows = db.scalars(query).all()

    total = len(rows)
    verified = sum(1 for r in rows if r.verification_status == "confirmed")
    pending = sum(1 for r in rows if r.verification_status == "pending_review")
    rejected = sum(1 for r in rows if r.verification_status == "rejected")
    unique_farms = len({r.geo_code for r in rows})

    # Crop/target breakdown
    crop_targets: dict[str, dict[str, int]] = {}
    for r in rows:
        key = r.target_code
        if key not in crop_targets:
            crop_targets[key] = {"count": 0, "verified": 0}
        crop_targets[key]["count"] += 1
        if r.verification_status == "confirmed":
            crop_targets[key]["verified"] += 1

    return {
        "h3_cell_id": h3_cell_id,
        "total_observations": total,
        "verified": verified,
        "pending_review": pending,
        "rejected": rejected,
        "unique_farms": unique_farms,
        "crop_targets": crop_targets,
    }


def get_hotspots_in_cell(
    db: Session, h3_cell_id: str, resolution: Optional[int] = None
) -> list[dict]:
    """Return hotspot clusters for an H3 cell."""
    query = select(HotspotCluster).where(HotspotCluster.h3_cell_id == h3_cell_id)
    if resolution is not None:
        query = query.where(HotspotCluster.resolution == resolution)
    rows = db.scalars(query).all()
    return [
        {
            "hotspot_id": row.id,
            "target_type": row.target_type,
            "target_code": row.target_code,
            "crop_code": row.crop_code,
            "classification": row.classification,
            "score": float(row.score),
            "total_reports": row.total_reports,
            "unique_affected_farms": row.unique_affected_farms,
            "verified_farms": row.verified_farms,
            "calculated_at": row.calculated_at.isoformat(),
        }
        for row in rows
    ]


def calculate_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in kilometres."""
    return great_circle_distance_m(lat1, lng1, lat2, lng2) / 1000.0


def find_nearby_cells(
    lat: float, lng: float, radius_km: float, resolution: Optional[int] = None
) -> list[dict]:
    """Find H3 cells within a radius of given coordinates."""
    if resolution is None:
        resolution = default_resolution()
    center_cell = geo_to_h3(lat, lng, resolution=resolution)
    # Determine k ring based on radius and resolution
    # Approximate: each ring adds ~hex diameter
    hex_diameter_km = (
        __import__("backend.app.geo.h3_utils", fromlist=["hex_area_m2"]).hex_area_m2(
            resolution
        )
        ** 0.5
        / 1000.0
        * 2
    )
    k = max(1, int(radius_km / max(hex_diameter_km, 0.1)) + 1)
    k = min(k, 3)  # Cap for performance

    neighbour_ids = k_ring(center_cell, k=k)
    center_lat, center_lng = h3_to_center(center_cell)

    results = []
    for cid in neighbour_ids:
        if cid == center_cell:
            continue
        info = cell_info(cid)
        dist = calculate_distance_km(
            center_lat, center_lng, float(info.center_lat), float(info.center_lng)
        )
        if dist <= radius_km:
            results.append(
                {
                    "cell_id": str(info.cell_id),
                    "resolution": info.resolution,
                    "center_lat": float(info.center_lat),
                    "center_lng": float(info.center_lng),
                    "distance_km": round(dist, 2),
                    "area_m2": float(info.area_m2),
                }
            )

    results.sort(key=lambda x: x["distance_km"])
    return results


__all__ = [
    "H3ServiceError",
    "resolve_cell_id",
    "validate_cell",
    "get_cell_info",
    "get_neighbours",
    "get_parent",
    "get_children",
    "generate_grid_in_bbox",
    "assign_farm_to_cell",
    "get_farms_in_cell",
    "get_cell_for_coordinates",
    "aggregate_observations_in_cell",
    "get_hotspots_in_cell",
    "calculate_distance_km",
    "find_nearby_cells",
]
