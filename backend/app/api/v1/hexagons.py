"""H3 hexagonal grid API routes.

Endpoints for H3 cell management, farm-to-cell assignment, neighbour lookup,
and hexagon-level data aggregation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_principal
from app.core.errors import ApiError
from app.db.models import User
from app.db.session import get_db
from app.geo.service import (
    H3ServiceError,
    aggregate_observations_in_cell,
    assign_farm_to_cell,
    calculate_distance_km,
    find_nearby_cells,
    generate_grid_in_bbox,
    get_cell_for_coordinates,
    get_cell_info,
    get_farms_in_cell,
    get_hotspots_in_cell,
    get_children,
    get_neighbours,
    get_parent,
    resolve_cell_id,
    validate_cell,
)

router = APIRouter(tags=["hexagons"])


class CellInfoResponse(BaseModel):
    cell_id: str
    resolution: int
    center_lat: float
    center_lng: float
    area_m2: float
    boundary: list[list[float]]


class CellListResponse(BaseModel):
    cells: list[CellInfoResponse]
    count: int


class NeighboursResponse(BaseModel):
    cell_id: str
    neighbours: list[CellInfoResponse]
    count: int


class ParentResponse(BaseModel):
    cell_id: str
    parent: CellInfoResponse


class ChildrenResponse(BaseModel):
    cell_id: str
    children: list[CellInfoResponse]
    count: int


class GridRequest(BaseModel):
    lat_min: float = Field(ge=-90, le=90)
    lng_min: float = Field(ge=-180, le=180)
    lat_max: float = Field(ge=-90, le=90)
    lng_max: float = Field(ge=-180, le=180)
    resolution: int | None = Field(default=None, ge=0, le=15)


class GridResponse(BaseModel):
    cells: list[CellInfoResponse]
    count: int


class FarmAssignmentRequest(BaseModel):
    farm_id: str
    geo_code: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    resolution: int | None = Field(default=None, ge=0, le=15)
    is_primary: bool = True


class FarmAssignmentResponse(BaseModel):
    assignment_id: str
    farm_id: str
    h3_cell_id: str
    resolution: int
    is_primary: bool


class CellCoordRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    resolution: int | None = Field(default=None, ge=0, le=15)


class DistanceRequest(BaseModel):
    lat1: float = Field(ge=-90, le=90)
    lng1: float = Field(ge=-180, le=180)
    lat2: float = Field(ge=-90, le=90)
    lng2: float = Field(ge=-180, le=180)


class DistanceResponse(BaseModel):
    distance_km: float


class NearbyCellsRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_km: float = Field(gt=0, le=100)
    resolution: int | None = Field(default=None, ge=0, le=15)


class NearbyCellsResponse(BaseModel):
    center_cell_id: str
    cells: list[dict]
    count: int


class ObservationAggregateResponse(BaseModel):
    h3_cell_id: str
    total_observations: int
    verified: int
    pending_review: int
    rejected: int
    unique_farms: int
    crop_targets: dict


class HotspotListResponse(BaseModel):
    h3_cell_id: str
    hotspots: list[dict]
    count: int


@router.get("/cells/{cell_id}", response_model=CellInfoResponse)
def get_cell(
    cell_id: str = Path(..., description="H3 cell ID (decimal string)"),
    user: User = Depends(get_principal),
) -> CellInfoResponse:
    """Return detailed information about an H3 cell."""
    try:
        cid = resolve_cell_id(cell_id)
        validate_cell(cid)
    except H3ServiceError as exc:
        raise ApiError(400, "invalid_cell_id", str(exc)) from exc
    info = get_cell_info(cid)
    return CellInfoResponse(**info)


@router.get("/cells/{cell_id}/neighbours", response_model=NeighboursResponse)
def get_cell_neighbours(
    cell_id: str = Path(..., description="H3 cell ID"),
    k: int = Query(default=1, ge=0, le=3, description="Number of rings"),
    user: User = Depends(get_principal),
) -> NeighboursResponse:
    """Return neighbouring H3 cells within k rings."""
    try:
        cid = resolve_cell_id(cell_id)
        validate_cell(cid)
    except H3ServiceError as exc:
        raise ApiError(400, "invalid_cell_id", str(exc)) from exc
    neighbours = get_neighbours(cid, k=k)
    return NeighboursResponse(
        cell_id=cell_id,
        neighbours=[CellInfoResponse(**n) for n in neighbours],
        count=len(neighbours),
    )


@router.get("/cells/{cell_id}/parent", response_model=ParentResponse)
def get_cell_parent(
    cell_id: str = Path(..., description="H3 cell ID"),
    resolution: int | None = Query(default=None, ge=0, le=14),
    user: User = Depends(get_principal),
) -> ParentResponse:
    """Return the parent H3 cell at a coarser resolution."""
    try:
        cid = resolve_cell_id(cell_id)
        validate_cell(cid)
    except H3ServiceError as exc:
        raise ApiError(400, "invalid_cell_id", str(exc)) from exc
    parent = get_parent(cid, parent_resolution=resolution)
    return ParentResponse(cell_id=cell_id, parent=CellInfoResponse(**parent))


@router.get("/cells/{cell_id}/children", response_model=ChildrenResponse)
def get_cell_children(
    cell_id: str = Path(..., description="H3 cell ID"),
    resolution: int | None = Query(default=None, ge=1, le=15),
    user: User = Depends(get_principal),
) -> ChildrenResponse:
    """Return child H3 cells at a finer resolution."""
    try:
        cid = resolve_cell_id(cell_id)
        validate_cell(cid)
    except H3ServiceError as exc:
        raise ApiError(400, "invalid_cell_id", str(exc)) from exc
    children = get_children(cid, child_resolution=resolution)
    return ChildrenResponse(
        cell_id=cell_id,
        children=[CellInfoResponse(**c) for c in children],
        count=len(children),
    )


@router.post("/cells/grid", response_model=GridResponse)
def generate_grid_cells(
    payload: GridRequest,
    user: User = Depends(get_principal),
) -> GridResponse:
    """Generate H3 cells covering a bounding box."""
    try:
        cells = generate_grid_in_bbox(
            lat_min=payload.lat_min,
            lng_min=payload.lng_min,
            lat_max=payload.lat_max,
            lng_max=payload.lng_max,
            resolution=payload.resolution,
        )
    except H3ServiceError as exc:
        raise ApiError(400, "invalid_bounds", str(exc)) from exc
    return GridResponse(
        cells=[CellInfoResponse(**c) for c in cells],
        count=len(cells),
    )


@router.post("/cells/from-coordinates", response_model=CellInfoResponse)
def cell_from_coordinates(
    payload: CellCoordRequest,
    user: User = Depends(get_principal),
) -> CellInfoResponse:
    """Return the H3 cell containing given coordinates."""
    info = get_cell_for_coordinates(
        lat=payload.lat, lng=payload.lng, resolution=payload.resolution
    )
    return CellInfoResponse(**info)


@router.post("/farms/assign", response_model=FarmAssignmentResponse)
def assign_farm(
    payload: FarmAssignmentRequest,
    user: User = Depends(get_principal),
    db: Session = Depends(get_db),
) -> FarmAssignmentResponse:
    """Assign a farm to an H3 cell based on GPS coordinates."""
    try:
        result = assign_farm_to_cell(
            db=db,
            farm_id=payload.farm_id,
            geo_code=payload.geo_code,
            lat=payload.lat,
            lng=payload.lng,
            resolution=payload.resolution,
            is_primary=payload.is_primary,
        )
    except H3ServiceError as exc:
        raise ApiError(400, "assignment_error", str(exc)) from exc
    db.commit()
    return FarmAssignmentResponse(**result)


@router.get("/cells/{cell_id}/farms")
def get_farms_in_cell_endpoint(
    cell_id: str = Path(..., description="H3 cell ID"),
    resolution: int | None = Query(default=None, ge=0, le=15),
    user: User = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Return farms assigned to an H3 cell."""
    try:
        validate_cell(resolve_cell_id(cell_id))
    except H3ServiceError as exc:
        raise ApiError(400, "invalid_cell_id", str(exc)) from exc
    farms = get_farms_in_cell(db, h3_cell_id=cell_id, resolution=resolution)
    return {"cell_id": cell_id, "farms": farms, "count": len(farms)}


@router.post("/distance", response_model=DistanceResponse)
def calculate_distance(
    payload: DistanceRequest,
    user: User = Depends(get_principal),
) -> DistanceResponse:
    """Calculate distance between two coordinates in kilometres."""
    dist = calculate_distance_km(
        lat1=payload.lat1,
        lng1=payload.lng1,
        lat2=payload.lat2,
        lng2=payload.lng2,
    )
    return DistanceResponse(distance_km=round(dist, 3))


@router.post("/cells/nearby", response_model=NearbyCellsResponse)
def nearby_cells(
    payload: NearbyCellsRequest,
    user: User = Depends(get_principal),
) -> NearbyCellsResponse:
    """Find H3 cells within a radius of given coordinates."""
    results = find_nearby_cells(
        lat=payload.lat,
        lng=payload.lng,
        radius_km=payload.radius_km,
        resolution=payload.resolution,
    )
    center_cell = geo_to_h3(payload.lat, payload.lng, resolution=payload.resolution or 8)
    return NearbyCellsResponse(
        center_cell_id=str(center_cell),
        cells=results,
        count=len(results),
    )


@router.get("/cells/{cell_id}/observations", response_model=ObservationAggregateResponse)
def cell_observations(
    cell_id: str = Path(..., description="H3 cell ID"),
    resolution: int | None = Query(default=None, ge=0, le=15),
    user: User = Depends(get_principal),
    db: Session = Depends(get_db),
) -> ObservationAggregateResponse:
    """Return aggregated observation statistics for an H3 cell."""
    try:
        validate_cell(resolve_cell_id(cell_id))
    except H3ServiceError as exc:
        raise ApiError(400, "invalid_cell_id", str(exc)) from exc
    agg = aggregate_observations_in_cell(db, h3_cell_id=cell_id, resolution=resolution)
    return ObservationAggregateResponse(**agg)


@router.get("/cells/{cell_id}/hotspots", response_model=HotspotListResponse)
def cell_hotspots(
    cell_id: str = Path(..., description="H3 cell ID"),
    resolution: int | None = Query(default=None, ge=0, le=15),
    user: User = Depends(get_principal),
    db: Session = Depends(get_db),
) -> HotspotListResponse:
    """Return hotspot clusters for an H3 cell."""
    try:
        validate_cell(resolve_cell_id(cell_id))
    except H3ServiceError as exc:
        raise ApiError(400, "invalid_cell_id", str(exc)) from exc
    hotspots = get_hotspots_in_cell(db, h3_cell_id=cell_id, resolution=resolution)
    return HotspotListResponse(
        cell_id=cell_id,
        hotspots=hotspots,
        count=len(hotspots),
    )


__all__ = ["router"]
