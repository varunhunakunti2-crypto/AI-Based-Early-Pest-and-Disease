"""H3 hexagonal geospatial indexing package for AgroAI.

Provides pure-Python H3-compatible utilities (``h3_utils``) that work without
the official C-based ``h3`` package. When the official package is installed,
call ``set_h3_backend("official")`` to switch.
"""

from .h3_utils import (
    DEFAULT_RESOLUTIONS,
    EARTH_RADIUS_M,
    MAX_RESOLUTION,
    H3CellInfo,
    H3Error,
    cell_info,
    generate_grid,
    geo_to_h3,
    get_h3_backend,
    great_circle_distance_m,
    h3_get_base_cell,
    h3_get_resolution,
    h3_is_valid,
    h3_to_center,
    h3_to_children,
    h3_to_geo,
    h3_to_geo_boundary,
    h3_to_parent,
    hex_area_m2,
    k_ring,
    set_h3_backend,
)

__all__ = [
    "DEFAULT_RESOLUTIONS",
    "EARTH_RADIUS_M",
    "H3CellInfo",
    "H3Error",
    "MAX_RESOLUTION",
    "cell_info",
    "generate_grid",
    "geo_to_h3",
    "get_h3_backend",
    "great_circle_distance_m",
    "h3_get_base_cell",
    "h3_get_resolution",
    "h3_is_valid",
    "h3_to_center",
    "h3_to_children",
    "h3_to_geo",
    "h3_to_geo_boundary",
    "h3_to_parent",
    "hex_area_m2",
    "k_ring",
    "set_h3_backend",
]
