"""H3 hexagonal grid configuration for AgroAI.

Centralised configuration for H3 resolution settings so resolutions can be
changed in one place without editing code throughout the application.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class H3ResolutionConfig:
    """H3 resolution configuration for a specific use case."""

    name: str
    resolution: int
    description: str
    use_cases: tuple[str, ...]


# Default H3 resolutions used across AgroAI.
# These can be overridden via system configuration or environment variables.
H3_RESOLUTIONS: tuple[H3ResolutionConfig, ...] = (
    H3ResolutionConfig(
        name="region",
        resolution=6,
        description="Large agricultural regions (state/district level)",
        use_cases=("regional_overview", "district_intelligence"),
    ),
    H3ResolutionConfig(
        name="village",
        resolution=7,
        description="District and village-level intelligence",
        use_cases=("village_intelligence", "regional_hotspots"),
    ),
    H3ResolutionConfig(
        name="farm_cluster",
        resolution=8,
        description="Farm-cluster monitoring",
        use_cases=("farm_clusters", "plot_groups"),
    ),
    H3ResolutionConfig(
        name="field",
        resolution=9,
        description="Detailed field monitoring",
        use_cases=("farm_assignment", "observation_cells", "task_cells"),
    ),
    H3ResolutionConfig(
        name="fine",
        resolution=10,
        description="Optional fine-grained analysis",
        use_cases=("fine_analysis", "plant_level_approx"),
    ),
)


def get_resolution(use_case: str) -> int:
    """Return the H3 resolution for a given use case.

    Falls back to resolution 8 (field-level) if the use case is not recognised.
    """
    for config in H3_RESOLUTIONS:
        if use_case in config.use_cases:
            return config.resolution
    return H3_RESOLUTIONS[2].resolution  # default: farm_cluster (resolution 8)


def get_all_resolutions() -> tuple[int, ...]:
    """Return all configured H3 resolutions in ascending order."""
    return tuple(sorted(config.resolution for config in H3_RESOLUTIONS))


def default_resolution() -> int:
    """Return the default H3 resolution (farm_cluster = 8)."""
    return get_resolution("farm_assignment")


__all__ = [
    "H3ResolutionConfig",
    "H3_RESOLUTIONS",
    "get_resolution",
    "get_all_resolutions",
    "default_resolution",
]
