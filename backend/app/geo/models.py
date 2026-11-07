"""SQLAlchemy models for H3 hexagonal geospatial intelligence.

These tables extend the existing schema with H3 hexagonal indexing, hotspot
intelligence, weather-cell records, and the Uber-style task distribution system.

All new tables follow the existing conventions:
- String(64) prefixed UUID primary keys
- UTCDateTime timestamps
- is_demo flag for demo data
- Check constraints for data validation
- Spatial indexes where appropriate
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UTCDateTime, new_id, utc_now


# ---------------------------------------------------------------------------
# H3 Hexagonal Grid
# ---------------------------------------------------------------------------


class H3Cell(Base, TimestampMixin):
    """Registry of H3 hexagonal cells covering the agricultural region.

    Each cell represents a geographic area at a specific H3 resolution.
    Cells are pre-computed for the configured resolutions and stored for
    efficient spatial queries and aggregation.
    """

    __tablename__ = "h3_cells"
    __table_args__ = (
        Index("ix_h3_cells_resolution", "resolution"),
        Index("ix_h3_cells_center", "center_lat", "center_lng"),
        Index("ix_h3_cells_res_center", "resolution", "center_lat", "center_lng"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("h3c")
    )
    cell_id: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    """H3 cell identifier as a decimal string (64-bit integer)."""

    resolution: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    """H3 resolution level (0-15)."""

    center_lat: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    center_lng: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    area_m2: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    boundary_geojson: Mapped[dict] = mapped_column(JSON, nullable=False)
    """GeoJSON Polygon representing the cell boundary."""

    parent_cell_id: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, index=True
    )
    """Parent H3 cell ID at resolution-1, if any."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "resolution >= 0 AND resolution <= 15", name="ck_h3_cells_resolution_range"
        ),
        CheckConstraint(
            "center_lat >= -90 AND center_lat <= 90",
            name="ck_h3_cells_lat_range",
        ),
        CheckConstraint(
            "center_lng >= -180 AND center_lng <= 180",
            name="ck_h3_cells_lng_range",
        ),
        CheckConstraint("area_m2 > 0", name="ck_h3_cells_positive_area"),
        UniqueConstraint("cell_id", name="uq_h3_cells_cell_id"),
    )


class FarmHexagonAssignment(Base, TimestampMixin):
    """Assignment of a farm or plot to an H3 cell.

    A farm may span multiple H3 cells; each cell intersection is recorded
    separately with the area overlap percentage.
    """

    __tablename__ = "farm_hexagon_assignments"
    __table_args__ = (
        Index("ix_farm_hex_geo", "geo_code"),
        Index("ix_farm_hex_cell", "h3_cell_id"),
        Index("ix_farm_hex_farm", "farm_id"),
        UniqueConstraint(
            "farm_id", "h3_cell_id", name="uq_farm_hexagon_assignment"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("fha")
    )
    farm_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    geo_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    h3_cell_id: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    resolution: Mapped[int] = mapped_column(Integer, nullable=False)
    overlap_area_m2: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    overlap_percentage: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    """True if this is the primary (centroid) cell for the farm."""
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_farm_hex_resolution_range",
        ),
        CheckConstraint(
            "overlap_percentage IS NULL OR (overlap_percentage >= 0 AND overlap_percentage <= 100)",
            name="ck_farm_hex_overlap_pct",
        ),
    )


# ---------------------------------------------------------------------------
# Observations with H3 context
# ---------------------------------------------------------------------------


class GeoObservation(Base, TimestampMixin):
    """Observation linked to an H3 cell for spatial aggregation.

    Extends the existing observations table with H3 cell context for
    hexagon-level intelligence. Each observation is assigned to the H3
    cell containing its GPS location.
    """

    __tablename__ = "geo_observations"
    __table_args__ = (
        Index("ix_geo_obs_cell", "h3_cell_id"),
        Index("ix_geo_obs_geo", "geo_code"),
        Index("ix_geo_obs_crop_target", "crop_code", "target_code"),
        Index("ix_geo_obs_event", "event_date"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("geo")
    )
    observation_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    """Link to the core observations table, if applicable."""
    h3_cell_id: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    resolution: Mapped[int] = mapped_column(Integer, nullable=False)
    geo_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    crop_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    """Disease or pest target code."""
    event_date: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    reported_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, nullable=False
    )
    reporter_type: Mapped[str] = mapped_column(String(30), nullable=False)
    """farmer | field_agent | expert | ai_system"""
    verification_status: Mapped[str] = mapped_column(
        String(30), default="unverified", nullable=False, index=True
    )
    """unverified | pending_review | confirmed | probable | rejected | duplicate"""
    severity: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    """none | low | moderate | high | critical"""
    ai_confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    ai_model_version: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_geo_obs_resolution_range",
        ),
        CheckConstraint(
            "reporter_type IN ('farmer', 'field_agent', 'expert', 'ai_system')",
            name="ck_geo_obs_reporter_type",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'pending_review', 'confirmed', 'probable', 'rejected', 'duplicate')",
            name="ck_geo_obs_verification_status",
        ),
        CheckConstraint(
            "severity IS NULL OR severity IN ('none', 'low', 'moderate', 'high', 'critical')",
            name="ck_geo_obs_severity",
        ),
        CheckConstraint(
            "ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)",
            name="ck_geo_obs_ai_confidence_range",
        ),
    )


# ---------------------------------------------------------------------------
# Disease and Pest Reports
# ---------------------------------------------------------------------------


class DiseaseReport(Base, TimestampMixin):
    """Disease-specific report aggregated at H3 cell level.

    Separate from pest reports to allow independent hotspot tracking
    per disease type.
    """

    __tablename__ = "disease_reports"
    __table_args__ = (
        Index("ix_disease_cell", "h3_cell_id"),
        Index("ix_disease_crop", "crop_code"),
        Index("ix_disease_target", "target_code"),
        Index("ix_disease_event", "event_date"),
        UniqueConstraint(
            "h3_cell_id", "target_code", "event_date", "report_source",
            name="uq_disease_report_unique",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("dis")
    )
    h3_cell_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resolution: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    event_date: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    report_date: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, nullable=False
    )
    report_source: Mapped[str] = mapped_column(String(50), nullable=False)
    """farmer_report | field_agent | expert_verification | ai_detection"""
    case_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unique_farms: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    verified_farms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity_distribution: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    """{"low": 2, "moderate": 1, "high": 0, "critical": 0}"""
    avg_ai_confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_disease_resolution_range",
        ),
        CheckConstraint("case_count >= 1", name="ck_disease_positive_cases"),
        CheckConstraint("unique_farms >= 1", name="ck_disease_positive_farms"),
        CheckConstraint(
            "verified_farms >= 0 AND verified_farms <= unique_farms",
            name="ck_disease_verified_le_unique",
        ),
    )


class PestReport(Base, TimestampMixin):
    """Pest-specific report aggregated at H3 cell level.

    Separate from disease reports for independent hotspot tracking.
    """

    __tablename__ = "pest_reports"
    __table_args__ = (
        Index("ix_pest_cell", "h3_cell_id"),
        Index("ix_pest_crop", "crop_code"),
        Index("ix_pest_target", "target_code"),
        Index("ix_pest_event", "event_date"),
        UniqueConstraint(
            "h3_cell_id", "target_code", "event_date", "report_source",
            name="uq_pest_report_unique",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("pst")
    )
    h3_cell_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resolution: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    event_date: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    report_date: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, nullable=False
    )
    report_source: Mapped[str] = mapped_column(String(50), nullable=False)
    case_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unique_farms: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    verified_farms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity_distribution: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    avg_ai_confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_pest_resolution_range",
        ),
        CheckConstraint("case_count >= 1", name="ck_pest_positive_cases"),
        CheckConstraint("unique_farms >= 1", name="ck_pest_positive_farms"),
        CheckConstraint(
            "verified_farms >= 0 AND verified_farms <= unique_farms",
            name="ck_pest_verified_le_unique",
        ),
    )


# ---------------------------------------------------------------------------
# Hotspot Intelligence
# ---------------------------------------------------------------------------


class HotspotCluster(Base, TimestampMixin):
    """Computed hotspot cluster for a specific H3 cell.

    Hotspots are calculated per disease/pest/crop/region combination
    with configurable thresholds for LOW/MODERATE/HIGH/CRITICAL classification.
    """

    __tablename__ = "hotspot_clusters"
    __table_args__ = (
        Index("ix_hotspot_cell", "h3_cell_id"),
        Index("ix_hotspot_type", "hotspot_type"),
        Index("ix_hotspot_target", "target_code"),
        Index("ix_hotspot_classification", "classification"),
        Index("ix_hotspot_updated", "updated_at"),
        UniqueConstraint(
            "h3_cell_id", "target_type", "target_code", "resolution",
            name="uq_hotspot_cluster_unique",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("hot")
    )
    h3_cell_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resolution: Mapped[int] = mapped_column(Integer, nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    """disease | pest"""
    target_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    crop_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True, index=True)
    classification: Mapped[str] = mapped_column(
        String(20), default="low", nullable=False, index=True
    )
    """low | moderate | high | critical"""
    score: Mapped[float] = mapped_column(Numeric(6, 4), default=0.0, nullable=False)
    """Composite hotspot score (0.0 to 1.0)."""
    total_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_affected_farms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified_farms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unverified_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity_distribution: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    first_reported: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime, nullable=True
    )
    most_recent_report: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime, nullable=True
    )
    historical_frequency: Mapped[float] = mapped_column(
        Numeric(6, 4), default=0.0, nullable=False
    )
    weather_risk_factor: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    neighbor_cells: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    """List of neighboring H3 cell IDs that are also hotspots."""
    calculated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, nullable=False
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_hotspot_resolution_range",
        ),
        CheckConstraint(
            "classification IN ('low', 'moderate', 'high', 'critical')",
            name="ck_hotspot_classification",
        ),
        CheckConstraint(
            "score >= 0 AND score <= 1", name="ck_hotspot_score_range",
        ),
        CheckConstraint(
            "target_type IN ('disease', 'pest')",
            name="ck_hotspot_target_type",
        ),
        CheckConstraint(
            "weather_risk_factor IS NULL OR (weather_risk_factor >= 0 AND weather_risk_factor <= 1)",
            name="ck_hotspot_weather_risk_range",
        ),
    )


class HotspotHistory(Base, TimestampMixin):
    """Historical snapshot of hotspot state for trend analysis."""

    __tablename__ = "hotspot_history"
    __table_args__ = (
        Index("ix_hotspot_hist_cell", "h3_cell_id"),
        Index("ix_hotspot_hist_date", "snapshot_date"),
        Index("ix_hotspot_hist_target", "target_code"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("hoh")
    )
    h3_cell_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    snapshot_date: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, index=True
    )
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(6, 4), default=0.0, nullable=False)
    unique_affected_farms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weather_risk_factor: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


# ---------------------------------------------------------------------------
# Regional Risk Scores
# ---------------------------------------------------------------------------


class RegionalRiskScore(Base, TimestampMixin):
    """Weather-supported regional risk score per H3 cell.

    Combines weather conditions, crop type, growth stage, pest/disease
    biology, and historical observations to compute risk indicators.
    Weather is a risk factor, not proof of infestation.
    """

    __tablename__ = "regional_risk_scores"
    __table_args__ = (
        Index("ix_risk_cell", "h3_cell_id"),
        Index("ix_risk_crop_target", "crop_code", "target_code"),
        Index("ix_risk_valid", "valid_from", "valid_to"),
        UniqueConstraint(
            "h3_cell_id", "crop_code", "target_code", "valid_from",
            name="uq_risk_score_unique",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("rsk")
    )
    h3_cell_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resolution: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    valid_to: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    risk_score: Mapped[float] = mapped_column(
        Numeric(6, 4), default=0.0, nullable=False
    )
    """Composite risk score (0.0 to 1.0)."""
    weather_risk: Mapped[float] = mapped_column(
        Numeric(6, 4), default=0.0, nullable=False
    )
    """Weather-suitability component (0.0 to 1.0)."""
    biological_risk: Mapped[float] = mapped_column(
        Numeric(6, 4), default=0.0, nullable=False
    )
    """Pest/disease biology suitability component."""
    historical_risk: Mapped[float] = mapped_column(
        Numeric(6, 4), default=0.0, nullable=False
    )
    """Historical observation frequency component."""
    risk_label: Mapped[str] = mapped_column(
        String(20), default="insufficient_data", nullable=False
    )
    """insufficient_data | low | moderate | high | critical"""
    contributing_factors: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    """{"temperature": 0.3, "humidity": 0.5, "rainfall": 0.1, ...}"""
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_risk_resolution_range",
        ),
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 1",
            name="ck_risk_score_range",
        ),
        CheckConstraint(
            "weather_risk >= 0 AND weather_risk <= 1",
            name="ck_risk_weather_range",
        ),
        CheckConstraint(
            "valid_to > valid_from", name="ck_risk_valid_window",
        ),
        CheckConstraint(
            "risk_label IN ('insufficient_data', 'low', 'moderate', 'high', 'critical')",
            name="ck_risk_label",
        ),
    )


# ---------------------------------------------------------------------------
# Weather Cell Records
# ---------------------------------------------------------------------------


class WeatherCellRecord(Base, TimestampMixin):
    """Weather data stored at H3 cell level with retention policy.

    Weather forecasts are stored per cell and expire according to a
    retention strategy to avoid unbounded growth.
    """

    __tablename__ = "weather_cell_records"
    __table_args__ = (
        Index("ix_weather_cell", "h3_cell_id"),
        Index("ix_weather_source_ts", "source_timestamp"),
        Index("ix_weather_expires", "expires_at"),
        UniqueConstraint(
            "h3_cell_id", "source", "source_timestamp",
            name="uq_weather_cell_unique",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("wcr")
    )
    h3_cell_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resolution: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, index=True
    )
    fetched_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    variables: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    """temperature_2m, relative_humidity_2m, precipitation, etc."""
    completeness: Mapped[float] = mapped_column(
        Numeric(4, 3), default=0.0, nullable=False
    )
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_weather_cell_resolution_range",
        ),
        CheckConstraint(
            "completeness >= 0 AND completeness <= 1",
            name="ck_weather_cell_completeness_range",
        ),
        CheckConstraint("expires_at > source_timestamp", name="ck_weather_cell_expires"),
    )


# ---------------------------------------------------------------------------
# Inspection Tasks (Uber-style distribution)
# ---------------------------------------------------------------------------


class InspectionTask(Base, TimestampMixin):
    """Inspection task in the Uber-style geographic distribution system.

    Lifecycle: CREATED -> AVAILABLE -> ASSIGNED -> ACCEPTED ->
    IN_PROGRESS -> SUBMITTED -> UNDER_REVIEW -> VERIFIED -> COMPLETED
    Terminal: REJECTED | CANCELLED | EXPIRED | REASSIGNED
    """

    __tablename__ = "inspection_tasks"
    __table_args__ = (
        Index("ix_task_cell", "h3_cell_id"),
        Index("ix_task_status", "status"),
        Index("ix_task_priority", "priority"),
        Index("ix_task_crop_target", "crop_code", "target_code"),
        Index("ix_task_created", "created_at"),
        Index("ix_task_deadline", "deadline"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("tsk")
    )
    h3_cell_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resolution: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    """hotspot_verification | routine_scouting | recovery_inspection | expert_review"""
    priority: Mapped[str] = mapped_column(
        String(20), default="moderate", nullable=False, index=True
    )
    """low | moderate | high | urgent"""
    status: Mapped[str] = mapped_column(
        String(30), default="CREATED", nullable=False, index=True
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    """User ID of the assigned field agent/expert/farmer."""
    assigned_by: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    """User ID or 'system' for automatic assignment."""
    assignment_type: Mapped[str] = mapped_column(
        String(20), default="automatic", nullable=False
    )
    """automatic | voluntary"""
    deadline: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime, nullable=True, index=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime, nullable=True, index=True
    )
    suspected_issue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    crop_growth_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    inspection_instructions: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    max_distance_km: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    required_expertise: Mapped[Optional[list]] = mapped_column(
        JSON, default=list, nullable=False
    )
    """List of required expertise areas (e.g., ['rice_blast', 'field_scouting'])."""
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_task_resolution_range",
        ),
        CheckConstraint(
            "task_type IN ('hotspot_verification', 'routine_scouting', 'recovery_inspection', 'expert_review')",
            name="ck_task_type",
        ),
        CheckConstraint(
            "priority IN ('low', 'moderate', 'high', 'urgent')",
            name="ck_task_priority",
        ),
        CheckConstraint(
            "status IN ('CREATED', 'AVAILABLE', 'ASSIGNED', 'ACCEPTED', 'IN_PROGRESS', 'SUBMITTED', 'UNDER_REVIEW', 'VERIFIED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'EXPIRED', 'REASSIGNED')",
            name="ck_task_status",
        ),
        CheckConstraint(
            "assignment_type IN ('automatic', 'voluntary')",
            name="ck_task_assignment_type",
        ),
        CheckConstraint(
            "deadline IS NULL OR expires_at IS NULL OR expires_at >= deadline",
            name="ck_task_deadline_expires",
        ),
    )


class TaskAssignment(Base, TimestampMixin):
    """Record of a task being assigned to a user (audit history)."""

    __tablename__ = "task_assignments"
    __table_args__ = (
        Index("ix_task_assign_task", "task_id"),
        Index("ix_task_assign_user", "user_id"),
        Index("ix_task_assign_at", "assigned_at"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("tas")
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("inspection_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    assigned_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, nullable=False
    )
    assigned_by: Mapped[str] = mapped_column(String(64), nullable=False)
    assignment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    """automatic | voluntary"""
    accepted_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    declined_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    distance_km: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TaskStatusHistory(Base, TimestampMixin):
    """Audit history of task status changes."""

    __tablename__ = "task_status_history"
    __table_args__ = (
        Index("ix_task_hist_task", "task_id"),
        Index("ix_task_hist_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("tsh")
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("inspection_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, nullable=False
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


# ---------------------------------------------------------------------------
# Field Agent Profiles
# ---------------------------------------------------------------------------


class FieldAgentProfile(Base, TimestampMixin):
    """Profile for field agents and agricultural experts.

    Stores availability, expertise, and geographic coverage for
    intelligent task distribution.
    """

    __tablename__ = "field_agent_profiles"
    __table_args__ = (
        Index("ix_field_agent_user", "user_id"),
        Index("ix_field_agent_geo", "primary_geo_code"),
        Index("ix_field_agent_available", "is_available"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("fap")
    )
    user_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    primary_geo_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    expertise_areas: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    """List of disease/pest expertise area codes."""
    crop_experience: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    """List of crop codes with experience."""
    max_distance_km: Mapped[float] = mapped_column(
        Numeric(6, 2), default=10.0, nullable=False
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    current_lat: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    current_lng: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    location_updated_at: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime, nullable=True
    )
    current_workload: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_concurrent_tasks: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    completion_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    """Fraction of completed tasks (0.0 to 1.0)."""
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "max_distance_km > 0", name="ck_field_agent_positive_distance",
        ),
        CheckConstraint(
            "current_workload >= 0 AND max_concurrent_tasks > 0",
            name="ck_field_agent_workload_positive",
        ),
        CheckConstraint(
            "completion_rate IS NULL OR (completion_rate >= 0 AND completion_rate <= 1)",
            name="ck_field_agent_completion_rate_range",
        ),
    )


class UserTaskAvailability(Base, TimestampMixin):
    """User availability windows for voluntary task acceptance."""

    __tablename__ = "user_task_availability"
    __table_args__ = (
        Index("ix_availability_user", "user_id"),
        Index("ix_availability_window", "available_from", "available_to"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("uta")
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    available_from: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    available_to: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    max_distance_km: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    preferred_crop_codes: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    preferred_target_codes: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint("available_to > available_from", name="ck_availability_window"),
        CheckConstraint(
            "max_distance_km IS NULL OR max_distance_km > 0",
            name="ck_availability_positive_distance",
        ),
    )


# ---------------------------------------------------------------------------
# Inspection Results & Expert Verification
# ---------------------------------------------------------------------------


class InspectionResult(Base, TimestampMixin):
    """Result of a field inspection task."""

    __tablename__ = "inspection_results"
    __table_args__ = (
        Index("ix_inspection_task", "task_id"),
        Index("ix_inspection_cell", "h3_cell_id"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("ins")
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("inspection_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    h3_cell_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    inspected_by: Mapped[str] = mapped_column(String(64), nullable=False)
    inspection_date: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, nullable=False
    )
    crop_code: Mapped[str] = mapped_column(String(60), nullable=False)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False)
    found_issue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    severity: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    symptoms_observed: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    photos_taken: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    videos_taken: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    farmer_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ExpertVerification(Base, TimestampMixin):
    """Expert verification of an observation or inspection result."""

    __tablename__ = "expert_verifications"
    __table_args__ = (
        Index("ix_expert_obs", "observation_id"),
        Index("ix_expert_result", "inspection_result_id"),
        Index("ix_expert_status", "verification_status"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("exv")
    )
    observation_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    inspection_result_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    verified_by: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    """confirmed | probable | rejected | duplicate | needs_visit | unresolved"""
    corrected_target_code: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True
    )
    corrected_severity: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    notes: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, nullable=False
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('confirmed', 'probable', 'rejected', 'duplicate', 'needs_visit', 'unresolved')",
            name="ck_expert_verification_status",
        ),
    )


# ---------------------------------------------------------------------------
# Recovery Monitoring
# ---------------------------------------------------------------------------


class RecoveryMonitoringRecord(Base, TimestampMixin):
    """Recovery monitoring for farms after treatment/intervention."""

    __tablename__ = "recovery_monitoring_records"
    __table_args__ = (
        Index("ix_recovery_cell", "h3_cell_id"),
        Index("ix_recovery_farm", "farm_id"),
        Index("ix_recovery_follow_up", "follow_up_date"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("rcv")
    )
    farm_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    h3_cell_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    crop_code: Mapped[str] = mapped_column(String(60), nullable=False)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False)
    previous_severity: Mapped[str] = mapped_column(String(30), nullable=False)
    current_severity: Mapped[str] = mapped_column(String(30), nullable=False)
    recovery_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2), default=0.0, nullable=False
    )
    recovery_status: Mapped[str] = mapped_column(
        String(30), default="worsening", nullable=False
    )
    """worsening | stable | partial_recovery | full_recovery"""
    follow_up_date: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime, nullable=True, index=True
    )
    notes: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "recovery_percentage >= 0 AND recovery_percentage <= 100",
            name="ck_recovery_percentage_range",
        ),
        CheckConstraint(
            "recovery_status IN ('worsening', 'stable', 'partial_recovery', 'full_recovery')",
            name="ck_recovery_status",
        ),
    )


__all__ = [
    "H3Cell",
    "FarmHexagonAssignment",
    "GeoObservation",
    "DiseaseReport",
    "PestReport",
    "HotspotCluster",
    "HotspotHistory",
    "RegionalRiskScore",
    "WeatherCellRecord",
    "InspectionTask",
    "TaskAssignment",
    "TaskStatusHistory",
    "FieldAgentProfile",
    "UserTaskAvailability",
    "InspectionResult",
    "ExpertVerification",
    "RecoveryMonitoringRecord",
]
