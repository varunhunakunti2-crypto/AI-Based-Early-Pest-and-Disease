"""H3 hexagonal geospatial intelligence tables.

Revision ID: 0004_h3_hexagonal_grid
Revises: 0003_video_persistence
Create Date: 2026-11-06

Adds H3 hexagonal cell registry, farm-to-cell assignments, geo-tagged
observations, disease/pest reports, hotspot clusters, regional risk scores,
weather cell records, inspection tasks, task assignments, field agent
profiles, inspection results, expert verifications, and recovery monitoring
records.

Additive only. All new tables carry is_demo flags and follow existing
naming conventions (String(64) prefixed UUIDs, UTCDateTime, CheckConstraints).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_h3_hexagonal_grid"
down_revision: str | None = "0003_video_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # h3_cells
    # ------------------------------------------------------------------
    op.create_table(
        "h3_cells",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("cell_id", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("center_lat", sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column("center_lng", sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column("area_m2", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("boundary_geojson", sa.JSON(), nullable=False),
        sa.Column("parent_cell_id", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_h3_cells"),
        sa.UniqueConstraint("cell_id", name="uq_h3_cells_cell_id"),
        sa.CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_h3_cells_resolution_range",
        ),
        sa.CheckConstraint(
            "center_lat >= -90 AND center_lat <= 90", name="ck_h3_cells_lat_range"
        ),
        sa.CheckConstraint(
            "center_lng >= -180 AND center_lng <= 180", name="ck_h3_cells_lng_range"
        ),
        sa.CheckConstraint("area_m2 > 0", name="ck_h3_cells_positive_area"),
    )
    op.create_index("ix_h3_cells_resolution", "h3_cells", ["resolution"])
    op.create_index("ix_h3_cells_center", "h3_cells", ["center_lat", "center_lng"])
    op.create_index(
        "ix_h3_cells_res_center",
        "h3_cells",
        ["resolution", "center_lat", "center_lng"],
    )
    op.create_index("ix_h3_cells_parent", "h3_cells", ["parent_cell_id"])

    # ------------------------------------------------------------------
    # farm_hexagon_assignments
    # ------------------------------------------------------------------
    op.create_table(
        "farm_hexagon_assignments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("farm_id", sa.String(length=64), nullable=False),
        sa.Column("geo_code", sa.String(length=64), nullable=False),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("overlap_area_m2", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "overlap_percentage", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_farm_hexagon_assignments"),
        sa.UniqueConstraint(
            "farm_id", "h3_cell_id", name="uq_farm_hexagon_assignment"
        ),
        sa.CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_farm_hex_resolution_range",
        ),
        sa.CheckConstraint(
            "overlap_percentage IS NULL OR (overlap_percentage >= 0 AND overlap_percentage <= 100)",
            name="ck_farm_hex_overlap_pct",
        ),
    )
    op.create_index("ix_farm_hex_geo", "farm_hexagon_assignments", ["geo_code"])
    op.create_index("ix_farm_hex_cell", "farm_hexagon_assignments", ["h3_cell_id"])
    op.create_index("ix_farm_hex_farm", "farm_hexagon_assignments", ["farm_id"])

    # ------------------------------------------------------------------
    # geo_observations
    # ------------------------------------------------------------------
    op.create_table(
        "geo_observations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("observation_id", sa.String(length=64), nullable=True),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("geo_code", sa.String(length=64), nullable=False),
        sa.Column("crop_code", sa.String(length=60), nullable=False),
        sa.Column("target_code", sa.String(length=80), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "reported_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reporter_type", sa.String(length=30), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'unverified'"),
        ),
        sa.Column("severity", sa.String(length=30), nullable=True),
        sa.Column("ai_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("ai_model_version", sa.String(length=80), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_geo_observations"),
        sa.CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_geo_obs_resolution_range",
        ),
        sa.CheckConstraint(
            "reporter_type IN ('farmer', 'field_agent', 'expert', 'ai_system')",
            name="ck_geo_obs_reporter_type",
        ),
        sa.CheckConstraint(
            "verification_status IN ('unverified', 'pending_review', 'confirmed', 'probable', 'rejected', 'duplicate')",
            name="ck_geo_obs_verification_status",
        ),
        sa.CheckConstraint(
            "severity IS NULL OR severity IN ('none', 'low', 'moderate', 'high', 'critical')",
            name="ck_geo_obs_severity",
        ),
        sa.CheckConstraint(
            "ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)",
            name="ck_geo_obs_ai_confidence_range",
        ),
    )
    op.create_index("ix_geo_obs_cell", "geo_observations", ["h3_cell_id"])
    op.create_index("ix_geo_obs_geo", "geo_observations", ["geo_code"])
    op.create_index(
        "ix_geo_obs_crop_target", "geo_observations", ["crop_code", "target_code"]
    )
    op.create_index("ix_geo_obs_event", "geo_observations", ["event_date"])
    op.create_index("ix_geo_obs_observation", "geo_observations", ["observation_id"])

    # ------------------------------------------------------------------
    # disease_reports
    # ------------------------------------------------------------------
    op.create_table(
        "disease_reports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("crop_code", sa.String(length=60), nullable=False),
        sa.Column("target_code", sa.String(length=80), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "report_date",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("report_source", sa.String(length=50), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("unique_farms", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("verified_farms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "severity_distribution", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("avg_ai_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_disease_reports"),
        sa.UniqueConstraint(
            "h3_cell_id", "target_code", "event_date", "report_source",
            name="uq_disease_report_unique",
        ),
        sa.CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_disease_resolution_range",
        ),
        sa.CheckConstraint("case_count >= 1", name="ck_disease_positive_cases"),
        sa.CheckConstraint("unique_farms >= 1", name="ck_disease_positive_farms"),
        sa.CheckConstraint(
            "verified_farms >= 0 AND verified_farms <= unique_farms",
            name="ck_disease_verified_le_unique",
        ),
    )
    op.create_index("ix_disease_cell", "disease_reports", ["h3_cell_id"])
    op.create_index("ix_disease_crop", "disease_reports", ["crop_code"])
    op.create_index("ix_disease_target", "disease_reports", ["target_code"])
    op.create_index("ix_disease_event", "disease_reports", ["event_date"])

    # ------------------------------------------------------------------
    # pest_reports
    # ------------------------------------------------------------------
    op.create_table(
        "pest_reports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("crop_code", sa.String(length=60), nullable=False),
        sa.Column("target_code", sa.String(length=80), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "report_date",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("report_source", sa.String(length=50), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("unique_farms", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("verified_farms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "severity_distribution", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("avg_ai_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pest_reports"),
        sa.UniqueConstraint(
            "h3_cell_id", "target_code", "event_date", "report_source",
            name="uq_pest_report_unique",
        ),
        sa.CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_pest_resolution_range",
        ),
        sa.CheckConstraint("case_count >= 1", name="ck_pest_positive_cases"),
        sa.CheckConstraint("unique_farms >= 1", name="ck_pest_positive_farms"),
        sa.CheckConstraint(
            "verified_farms >= 0 AND verified_farms <= unique_farms",
            name="ck_pest_verified_le_unique",
        ),
    )
    op.create_index("ix_pest_cell", "pest_reports", ["h3_cell_id"])
    op.create_index("ix_pest_crop", "pest_reports", ["crop_code"])
    op.create_index("ix_pest_target", "pest_reports", ["target_code"])
    op.create_index("ix_pest_event", "pest_reports", ["event_date"])

    # ------------------------------------------------------------------
    # hotspot_clusters
    # ------------------------------------------------------------------
    op.create_table(
        "hotspot_clusters",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=30), nullable=False),
        sa.Column("target_code", sa.String(length=80), nullable=False),
        sa.Column("crop_code", sa.String(length=60), nullable=True),
        sa.Column(
            "classification",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'low'"),
        ),
        sa.Column("score", sa.Numeric(precision=6, scale=4), nullable=False, server_default=sa.text("0.0")),
        sa.Column("total_reports", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "unique_affected_farms", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("verified_farms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unverified_reports", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("pending_reviews", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "severity_distribution", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("first_reported", sa.DateTime(timezone=True), nullable=True),
        sa.Column("most_recent_report", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "historical_frequency", sa.Numeric(precision=6, scale=4), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column("weather_risk_factor", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "neighbor_cells", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id", name="pk_hotspot_clusters"),
        sa.UniqueConstraint(
            "h3_cell_id", "target_type", "target_code", "resolution",
            name="uq_hotspot_cluster_unique",
        ),
        sa.CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_hotspot_resolution_range",
        ),
        sa.CheckConstraint(
            "classification IN ('low', 'moderate', 'high', 'critical')",
            name="ck_hotspot_classification",
        ),
        sa.CheckConstraint("score >= 0 AND score <= 1", name="ck_hotspot_score_range"),
        sa.CheckConstraint(
            "target_type IN ('disease', 'pest')", name="ck_hotspot_target_type"
        ),
        sa.CheckConstraint(
            "weather_risk_factor IS NULL OR (weather_risk_factor >= 0 AND weather_risk_factor <= 1)",
            name="ck_hotspot_weather_risk_range",
        ),
    )
    op.create_index("ix_hotspot_cell", "hotspot_clusters", ["h3_cell_id"])
    op.create_index("ix_hotspot_type", "hotspot_clusters", ["target_type"])
    op.create_index("ix_hotspot_target", "hotspot_clusters", ["target_code"])
    op.create_index("ix_hotspot_classification", "hotspot_clusters", ["classification"])
    op.create_index("ix_hotspot_updated", "hotspot_clusters", ["updated_at"])

    # ------------------------------------------------------------------
    # hotspot_history
    # ------------------------------------------------------------------
    op.create_table(
        "hotspot_history",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=30), nullable=False),
        sa.Column("target_code", sa.String(length=80), nullable=False),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("classification", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Numeric(precision=6, scale=4), nullable=False, server_default=sa.text("0.0")),
        sa.Column(
            "unique_affected_farms", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("weather_risk_factor", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_hotspot_history"),
    )
    op.create_index("ix_hotspot_hist_cell", "hotspot_history", ["h3_cell_id"])
    op.create_index("ix_hotspot_hist_date", "hotspot_history", ["snapshot_date"])
    op.create_index("ix_hotspot_hist_target", "hotspot_history", ["target_code"])

    # ------------------------------------------------------------------
    # regional_risk_scores
    # ------------------------------------------------------------------
    op.create_table(
        "regional_risk_scores",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("crop_code", sa.String(length=60), nullable=False),
        sa.Column("target_code", sa.String(length=80), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.Numeric(precision=6, scale=4), nullable=False, server_default=sa.text("0.0")),
        sa.Column("weather_risk", sa.Numeric(precision=6, scale=4), nullable=False, server_default=sa.text("0.0")),
        sa.Column("biological_risk", sa.Numeric(precision=6, scale=4), nullable=False, server_default=sa.text("0.0")),
        sa.Column("historical_risk", sa.Numeric(precision=6, scale=4), nullable=False, server_default=sa.text("0.0")),
        sa.Column(
            "risk_label",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'insufficient_data'"),
        ),
        sa.Column(
            "contributing_factors", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_regional_risk_scores"),
        sa.UniqueConstraint(
            "h3_cell_id", "crop_code", "target_code", "valid_from",
            name="uq_risk_score_unique",
        ),
        sa.CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_risk_resolution_range",
        ),
        sa.CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="ck_risk_score_range"),
        sa.CheckConstraint(
            "weather_risk >= 0 AND weather_risk <= 1", name="ck_risk_weather_range"
        ),
        sa.CheckConstraint(
            "valid_to > valid_from", name="ck_risk_valid_window",
        ),
        sa.CheckConstraint(
            "risk_label IN ('insufficient_data', 'low', 'moderate', 'high', 'critical')",
            name="ck_risk_label",
        ),
    )
    op.create_index("ix_risk_cell", "regional_risk_scores", ["h3_cell_id"])
    op.create_index(
        "ix_risk_crop_target", "regional_risk_scores", ["crop_code", "target_code"]
    )
    op.create_index("ix_risk_valid", "regional_risk_scores", ["valid_from", "valid_to"])

    # ------------------------------------------------------------------
    # weather_cell_records
    # ------------------------------------------------------------------
    op.create_table(
        "weather_cell_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "variables", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column(
            "completeness", sa.Numeric(precision=4, scale=3), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_weather_cell_records"),
        sa.UniqueConstraint(
            "h3_cell_id", "source", "source_timestamp",
            name="uq_weather_cell_unique",
        ),
        sa.CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_weather_cell_resolution_range",
        ),
        sa.CheckConstraint(
            "completeness >= 0 AND completeness <= 1",
            name="ck_weather_cell_completeness_range",
        ),
        sa.CheckConstraint(
            "expires_at > source_timestamp", name="ck_weather_cell_expires",
        ),
    )
    op.create_index("ix_weather_cell", "weather_cell_records", ["h3_cell_id"])
    op.create_index("ix_weather_source_ts", "weather_cell_records", ["source_timestamp"])
    op.create_index("ix_weather_expires", "weather_cell_records", ["expires_at"])

    # ------------------------------------------------------------------
    # inspection_tasks
    # ------------------------------------------------------------------
    op.create_table(
        "inspection_tasks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("crop_code", sa.String(length=60), nullable=False),
        sa.Column("target_code", sa.String(length=80), nullable=False),
        sa.Column("task_type", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default=sa.text("'moderate'")),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'CREATED'")),
        sa.Column("assigned_to", sa.String(length=64), nullable=True),
        sa.Column("assigned_by", sa.String(length=64), nullable=True),
        sa.Column("assignment_type", sa.String(length=20), nullable=False, server_default=sa.text("'automatic'")),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspected_issue", sa.Text(), nullable=True),
        sa.Column("crop_growth_stage", sa.String(length=50), nullable=True),
        sa.Column("inspection_instructions", sa.Text(), nullable=True),
        sa.Column("max_distance_km", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column(
            "required_expertise", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inspection_tasks"),
        sa.CheckConstraint(
            "resolution >= 0 AND resolution <= 15",
            name="ck_task_resolution_range",
        ),
        sa.CheckConstraint(
            "task_type IN ('hotspot_verification', 'routine_scouting', 'recovery_inspection', 'expert_review')",
            name="ck_task_type",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'moderate', 'high', 'urgent')", name="ck_task_priority"
        ),
        sa.CheckConstraint(
            "status IN ('CREATED', 'AVAILABLE', 'ASSIGNED', 'ACCEPTED', 'IN_PROGRESS', 'SUBMITTED', 'UNDER_REVIEW', 'VERIFIED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'EXPIRED', 'REASSIGNED')",
            name="ck_task_status",
        ),
        sa.CheckConstraint(
            "assignment_type IN ('automatic', 'voluntary')",
            name="ck_task_assignment_type",
        ),
        sa.CheckConstraint(
            "deadline IS NULL OR expires_at IS NULL OR expires_at >= deadline",
            name="ck_task_deadline_expires",
        ),
    )
    op.create_index("ix_task_cell", "inspection_tasks", ["h3_cell_id"])
    op.create_index("ix_task_status", "inspection_tasks", ["status"])
    op.create_index("ix_task_priority", "inspection_tasks", ["priority"])
    op.create_index(
        "ix_task_crop_target", "inspection_tasks", ["crop_code", "target_code"]
    )
    op.create_index("ix_task_created", "inspection_tasks", ["created_at"])
    op.create_index("ix_task_deadline", "inspection_tasks", ["deadline"])
    op.create_index("ix_task_assigned", "inspection_tasks", ["assigned_to"])

    # ------------------------------------------------------------------
    # task_assignments
    # ------------------------------------------------------------------
    op.create_table(
        "task_assignments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("assigned_by", sa.String(length=64), nullable=False),
        sa.Column("assignment_type", sa.String(length=20), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("declined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("distance_km", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_task_assignments"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["inspection_tasks.id"],
            name="fk_task_assignments_task_id_inspection_tasks",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "assignment_type IN ('automatic', 'voluntary')",
            name="ck_task_assign_assignment_type",
        ),
    )
    op.create_index("ix_task_assign_task", "task_assignments", ["task_id"])
    op.create_index("ix_task_assign_user", "task_assignments", ["user_id"])
    op.create_index("ix_task_assign_at", "task_assignments", ["assigned_at"])

    # ------------------------------------------------------------------
    # task_status_history
    # ------------------------------------------------------------------
    op.create_table(
        "task_status_history",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("changed_by", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id", name="pk_task_status_history"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["inspection_tasks.id"],
            name="fk_task_status_history_task_id_inspection_tasks",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_task_hist_task", "task_status_history", ["task_id"])
    op.create_index("ix_task_hist_at", "task_status_history", ["created_at"])

    # ------------------------------------------------------------------
    # field_agent_profiles
    # ------------------------------------------------------------------
    op.create_table(
        "field_agent_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("primary_geo_code", sa.String(length=64), nullable=True),
        sa.Column(
            "expertise_areas", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.Column(
            "crop_experience", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.Column(
            "max_distance_km", sa.Numeric(precision=6, scale=2), nullable=False, server_default=sa.text("10.0")
        ),
        sa.Column(
            "is_available", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("current_lat", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("current_lng", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("location_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "current_workload", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "max_concurrent_tasks", sa.Integer(), nullable=False, server_default=sa.text("3")
        ),
        sa.Column("completion_rate", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_field_agent_profiles"),
        sa.UniqueConstraint("user_id", name="uq_field_agent_profiles_user_id"),
        sa.CheckConstraint(
            "max_distance_km > 0", name="ck_field_agent_positive_distance"
        ),
        sa.CheckConstraint(
            "current_workload >= 0 AND max_concurrent_tasks > 0",
            name="ck_field_agent_workload_positive",
        ),
        sa.CheckConstraint(
            "completion_rate IS NULL OR (completion_rate >= 0 AND completion_rate <= 1)",
            name="ck_field_agent_completion_rate_range",
        ),
    )
    op.create_index("ix_field_agent_user", "field_agent_profiles", ["user_id"])
    op.create_index(
        "ix_field_agent_geo", "field_agent_profiles", ["primary_geo_code"]
    )
    op.create_index(
        "ix_field_agent_available", "field_agent_profiles", ["is_available"]
    )

    # ------------------------------------------------------------------
    # user_task_availability
    # ------------------------------------------------------------------
    op.create_table(
        "user_task_availability",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("available_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_distance_km", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column(
            "preferred_crop_codes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.Column(
            "preferred_target_codes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_task_availability"),
        sa.CheckConstraint(
            "available_to > available_from", name="ck_availability_window"
        ),
        sa.CheckConstraint(
            "max_distance_km IS NULL OR max_distance_km > 0",
            name="ck_availability_positive_distance",
        ),
    )
    op.create_index("ix_availability_user", "user_task_availability", ["user_id"])
    op.create_index(
        "ix_availability_window",
        "user_task_availability",
        ["available_from", "available_to"],
    )

    # ------------------------------------------------------------------
    # inspection_results
    # ------------------------------------------------------------------
    op.create_table(
        "inspection_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("inspected_by", sa.String(length=64), nullable=False),
        sa.Column(
            "inspection_date",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("crop_code", sa.String(length=60), nullable=False),
        sa.Column("target_code", sa.String(length=80), nullable=False),
        sa.Column("found_issue", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("severity", sa.String(length=30), nullable=True),
        sa.Column("ai_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("symptoms_observed", sa.Text(), nullable=True),
        sa.Column("photos_taken", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("videos_taken", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("farmer_notified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inspection_results"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["inspection_tasks.id"],
            name="fk_inspection_results_task_id_inspection_tasks",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_inspection_task", "inspection_results", ["task_id"])
    op.create_index("ix_inspection_cell", "inspection_results", ["h3_cell_id"])

    # ------------------------------------------------------------------
    # expert_verifications
    # ------------------------------------------------------------------
    op.create_table(
        "expert_verifications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("observation_id", sa.String(length=64), nullable=True),
        sa.Column("inspection_result_id", sa.String(length=64), nullable=True),
        sa.Column("verified_by", sa.String(length=64), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("corrected_target_code", sa.String(length=80), nullable=True),
        sa.Column("corrected_severity", sa.String(length=30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id", name="pk_expert_verifications"),
        sa.CheckConstraint(
            "verification_status IN ('confirmed', 'probable', 'rejected', 'duplicate', 'needs_visit', 'unresolved')",
            name="ck_expert_verification_status",
        ),
    )
    op.create_index("ix_expert_obs", "expert_verifications", ["observation_id"])
    op.create_index("ix_expert_result", "expert_verifications", ["inspection_result_id"])
    op.create_index("ix_expert_status", "expert_verifications", ["verification_status"])
    op.create_index("ix_expert_verified_by", "expert_verifications", ["verified_by"])

    # ------------------------------------------------------------------
    # recovery_monitoring_records
    # ------------------------------------------------------------------
    op.create_table(
        "recovery_monitoring_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("farm_id", sa.String(length=64), nullable=False),
        sa.Column("h3_cell_id", sa.String(length=32), nullable=False),
        sa.Column("crop_code", sa.String(length=60), nullable=False),
        sa.Column("target_code", sa.String(length=80), nullable=False),
        sa.Column("previous_severity", sa.String(length=30), nullable=False),
        sa.Column("current_severity", sa.String(length=30), nullable=False),
        sa.Column(
            "recovery_percentage", sa.Numeric(precision=5, scale=2), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "recovery_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'worsening'"),
        ),
        sa.Column("follow_up_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recovery_monitoring_records"),
        sa.CheckConstraint(
            "recovery_percentage >= 0 AND recovery_percentage <= 100",
            name="ck_recovery_percentage_range",
        ),
        sa.CheckConstraint(
            "recovery_status IN ('worsening', 'stable', 'partial_recovery', 'full_recovery')",
            name="ck_recovery_status",
        ),
    )
    op.create_index("ix_recovery_cell", "recovery_monitoring_records", ["h3_cell_id"])
    op.create_index("ix_recovery_farm", "recovery_monitoring_records", ["farm_id"])
    op.create_index(
        "ix_recovery_follow_up", "recovery_monitoring_records", ["follow_up_date"]
    )


def downgrade() -> None:
    op.drop_index("ix_recovery_follow_up", table_name="recovery_monitoring_records")
    op.drop_index("ix_recovery_farm", table_name="recovery_monitoring_records")
    op.drop_index("ix_recovery_cell", table_name="recovery_monitoring_records")
    op.drop_table("recovery_monitoring_records")

    op.drop_index("ix_expert_verified_by", table_name="expert_verifications")
    op.drop_index("ix_expert_status", table_name="expert_verifications")
    op.drop_index("ix_expert_result", table_name="expert_verifications")
    op.drop_index("ix_expert_obs", table_name="expert_verifications")
    op.drop_table("expert_verifications")

    op.drop_index("ix_inspection_cell", table_name="inspection_results")
    op.drop_index("ix_inspection_task", table_name="inspection_results")
    op.drop_table("inspection_results")

    op.drop_index("ix_availability_window", table_name="user_task_availability")
    op.drop_index("ix_availability_user", table_name="user_task_availability")
    op.drop_table("user_task_availability")

    op.drop_index("ix_field_agent_available", table_name="field_agent_profiles")
    op.drop_index("ix_field_agent_geo", table_name="field_agent_profiles")
    op.drop_index("ix_field_agent_user", table_name="field_agent_profiles")
    op.drop_table("field_agent_profiles")

    op.drop_index("ix_task_assigned", table_name="inspection_tasks")
    op.drop_index("ix_task_deadline", table_name="inspection_tasks")
    op.drop_index("ix_task_created", table_name="inspection_tasks")
    op.drop_index("ix_task_crop_target", table_name="inspection_tasks")
    op.drop_index("ix_task_priority", table_name="inspection_tasks")
    op.drop_index("ix_task_status", table_name="inspection_tasks")
    op.drop_index("ix_task_cell", table_name="inspection_tasks")
    op.drop_table("inspection_tasks")

    op.drop_index("ix_task_assign_at", table_name="task_assignments")
    op.drop_index("ix_task_assign_user", table_name="task_assignments")
    op.drop_index("ix_task_assign_task", table_name="task_assignments")
    op.drop_table("task_assignments")

    op.drop_index("ix_task_hist_at", table_name="task_status_history")
    op.drop_index("ix_task_hist_task", table_name="task_status_history")
    op.drop_table("task_status_history")

    op.drop_index("ix_risk_valid", table_name="regional_risk_scores")
    op.drop_index("ix_risk_crop_target", table_name="regional_risk_scores")
    op.drop_index("ix_risk_cell", table_name="regional_risk_scores")
    op.drop_table("regional_risk_scores")

    op.drop_index("ix_hotspot_updated", table_name="hotspot_clusters")
    op.drop_index("ix_hotspot_classification", table_name="hotspot_clusters")
    op.drop_index("ix_hotspot_target", table_name="hotspot_clusters")
    op.drop_index("ix_hotspot_type", table_name="hotspot_clusters")
    op.drop_index("ix_hotspot_cell", table_name="hotspot_clusters")
    op.drop_table("hotspot_clusters")

    op.drop_index("ix_hotspot_hist_target", table_name="hotspot_history")
    op.drop_index("ix_hotspot_hist_date", table_name="hotspot_history")
    op.drop_index("ix_hotspot_hist_cell", table_name="hotspot_history")
    op.drop_table("hotspot_history")

    op.drop_index("ix_pest_event", table_name="pest_reports")
    op.drop_index("ix_pest_target", table_name="pest_reports")
    op.drop_index("ix_pest_crop", table_name="pest_reports")
    op.drop_index("ix_pest_cell", table_name="pest_reports")
    op.drop_table("pest_reports")

    op.drop_index("ix_disease_event", table_name="disease_reports")
    op.drop_index("ix_disease_target", table_name="disease_reports")
    op.drop_index("ix_disease_crop", table_name="disease_reports")
    op.drop_index("ix_disease_cell", table_name="disease_reports")
    op.drop_table("disease_reports")

    op.drop_index("ix_geo_obs_observation", table_name="geo_observations")
    op.drop_index("ix_geo_obs_event", table_name="geo_observations")
    op.drop_index("ix_geo_obs_crop_target", table_name="geo_observations")
    op.drop_index("ix_geo_obs_geo", table_name="geo_observations")
    op.drop_index("ix_geo_obs_cell", table_name="geo_observations")
    op.drop_table("geo_observations")

    op.drop_index("ix_farm_hex_farm", table_name="farm_hexagon_assignments")
    op.drop_index("ix_farm_hex_cell", table_name="farm_hexagon_assignments")
    op.drop_index("ix_farm_hex_geo", table_name="farm_hexagon_assignments")
    op.drop_table("farm_hexagon_assignments")

    op.drop_index("ix_h3_cells_parent", table_name="h3_cells")
    op.drop_index("ix_h3_cells_res_center", table_name="h3_cells")
    op.drop_index("ix_h3_cells_center", table_name="h3_cells")
    op.drop_index("ix_h3_cells_resolution", table_name="h3_cells")
    op.drop_table("h3_cells")

    op.drop_index("ix_weather_expires", table_name="weather_cell_records")
    op.drop_index("ix_weather_source_ts", table_name="weather_cell_records")
    op.drop_index("ix_weather_cell", table_name="weather_cell_records")
    op.drop_table("weather_cell_records")
