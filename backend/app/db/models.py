"""SQLAlchemy models — the single schema authority for the API.

The entity map follows ``final/feature-specs/05-data-layer.md``. Types are kept
portable (SQLite for local dev, PostgreSQL 16 for deployment). PostGIS geometry
is intentionally not declared here: the pilot API only serves block/mandal
aggregates and a migration can add the geometry column when boundary data is
approved. Nothing in the API returns farm-level geometry.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
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
from app.geo import models as _geo_models  # noqa: F401  (registers H3 geo tables)
from app.modules.conversations import orm as _chat_orm
from app.modules.video import orm as _video_orm

# Re-export the chat and video models so ``app.db.models`` remains the single
# import surface for ORM models. The chat schema is owned by the conversations
# module (Alembic ``0002_chat_persistence``); the video schema is owned by the
# video module (Alembic ``0003_video_persistence``).
Conversation = _chat_orm.ConversationRow
Message = _chat_orm.MessageRow
MessageEvent = _chat_orm.MessageEventRow
ImageUpload = _chat_orm.ImageUploadRow
ChatReviewRequest = _chat_orm.ReviewRequestRow
VideoUpload = _video_orm.VideoUploadRow
VideoReading = _video_orm.VideoReadingRow

# H3 hexagonal geospatial intelligence models
H3Cell = _geo_models.H3Cell
FarmHexagonAssignment = _geo_models.FarmHexagonAssignment
GeoObservation = _geo_models.GeoObservation
DiseaseReport = _geo_models.DiseaseReport
PestReport = _geo_models.PestReport
HotspotCluster = _geo_models.HotspotCluster
HotspotHistory = _geo_models.HotspotHistory
RegionalRiskScore = _geo_models.RegionalRiskScore
WeatherCellRecord = _geo_models.WeatherCellRecord
InspectionTask = _geo_models.InspectionTask
TaskAssignment = _geo_models.TaskAssignment
TaskStatusHistory = _geo_models.TaskStatusHistory
FieldAgentProfile = _geo_models.FieldAgentProfile
UserTaskAvailability = _geo_models.UserTaskAvailability
InspectionResult = _geo_models.InspectionResult
ExpertVerification = _geo_models.ExpertVerification
RecoveryMonitoringRecord = _geo_models.RecoveryMonitoringRecord


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("usr"))
    phone_e164: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    active_role: Mapped[str] = mapped_column(String(40), default="farmer", nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_login_first_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Role(Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (Index("ix_user_roles_user_active", "user_id", "revoked_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("url"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.code"), nullable=False)
    granted_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class UserPermission(Base):
    __tablename__ = "user_permissions"
    __table_args__ = (Index("ix_user_permissions_user_active", "user_id", "revoked_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("upm"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(60), nullable=False)
    granted_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("dev"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    app_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    push_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (Index("ix_consents_user_type", "user_id", "type", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cns"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(60), nullable=False)
    version: Mapped[str] = mapped_column(String(60), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), default="app", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class UserAreaAssignment(Base):
    __tablename__ = "user_area_assignments"
    __table_args__ = (Index("ix_area_assignments_user_active", "user_id", "active_to"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("uaa"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    geo_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(30), default="block", nullable=False)
    active_from: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    active_to: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_family", "user_id", "family_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ses"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    refresh_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class OtpCode(Base):
    __tablename__ = "otp_codes"
    __table_args__ = (Index("ix_otp_phone_created", "phone_e164", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("otp"))
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


# ---------------------------------------------------------------------------
# Geography and crop context
# ---------------------------------------------------------------------------
class Geography(Base):
    __tablename__ = "geographies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("geo"))
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    level: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    boundary_version: Mapped[str] = mapped_column(
        String(60), default="demo-2026-11", nullable=False
    )
    valid_from: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Crop(Base, TimestampMixin):
    __tablename__ = "crops"

    code: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    supported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supported_from: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Target(Base, TimestampMixin):
    __tablename__ = "targets"
    __table_args__ = (UniqueConstraint("crop_code", "code", name="uq_target_crop_code"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("tgt"))
    crop_code: Mapped[str] = mapped_column(ForeignKey("crops.code"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    supported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    forecast_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    taxonomy_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class CropCalendar(Base):
    __tablename__ = "crop_calendars"
    __table_args__ = (Index("ix_crop_calendars_lookup", "crop_code", "geo_code", "season"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ccal"))
    crop_code: Mapped[str] = mapped_column(ForeignKey("crops.code"), nullable=False)
    geo_code: Mapped[str] = mapped_column(String(64), nullable=False)
    season: Mapped[str] = mapped_column(String(40), nullable=False)
    planting_window: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    stage_windows: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class GrowingArea(Base):
    __tablename__ = "growing_areas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ga"))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    geo_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    precision: Mapped[str] = mapped_column(String(20), default="block", nullable=False)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class CropCycle(Base):
    __tablename__ = "crop_cycles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cyc"))
    growing_area_id: Mapped[str] = mapped_column(
        ForeignKey("growing_areas.id"), nullable=False, index=True
    )
    crop_code: Mapped[str] = mapped_column(ForeignKey("crops.code"), nullable=False)
    variety: Mapped[str | None] = mapped_column(String(120), nullable=True)
    planting_date: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    stage_updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


# ---------------------------------------------------------------------------
# Observations and media
# ---------------------------------------------------------------------------
class Observation(Base, TimestampMixin):
    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("user_id", "client_report_id", name="uq_observation_client"),
        Index("ix_observations_user_created", "user_id", "created_at"),
        Index("ix_observations_area_status", "area_code", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("obs"))
    client_report_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    subject_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    growing_area_id: Mapped[str | None] = mapped_column(
        ForeignKey("growing_areas.id"), nullable=True
    )
    area_code: Mapped[str] = mapped_column(String(64), nullable=False)
    crop_code: Mapped[str] = mapped_column(ForeignKey("crops.code"), nullable=False)
    variety: Mapped[str | None] = mapped_column(String(120), nullable=True)
    growth_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending_upload", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class ImageAsset(Base):
    __tablename__ = "image_assets"
    __table_args__ = (Index("ix_image_assets_hash", "content_hash"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("img"))
    observation_id: Mapped[str] = mapped_column(
        ForeignKey("observations.id"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(400), nullable=False)
    original_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mime: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="camera", nullable=False)
    compression: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    upload_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class ImageQualityResult(Base):
    __tablename__ = "image_quality_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("iql"))
    image_id: Mapped[str] = mapped_column(ForeignKey("image_assets.id"), nullable=False, index=True)
    gate_version: Mapped[str] = mapped_column(String(80), nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class ImagePrediction(Base):
    __tablename__ = "image_predictions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("prd"))
    image_id: Mapped[str] = mapped_column(ForeignKey("image_assets.id"), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    candidates: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence_band: Mapped[str | None] = mapped_column(String(20), nullable=True)
    calibrated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    abstained: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    abstain_reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    quality_flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class ReviewRequest(Base):
    __tablename__ = "review_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rrq"))
    observation_id: Mapped[str] = mapped_column(
        ForeignKey("observations.id"), nullable=False, index=True
    )
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


# ---------------------------------------------------------------------------
# Review and verification
# ---------------------------------------------------------------------------
class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (Index("ix_reviews_observation_created", "observation_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rev"))
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.id"), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    corrected_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(30), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    duplicate_of: Mapped[str | None] = mapped_column(String(64), nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class ReviewEvidence(Base):
    __tablename__ = "review_evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("revd"))
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class ReviewEvent(Base):
    __tablename__ = "review_events"
    __table_args__ = (Index("ix_review_events_observation", "observation_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("reve"))
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class ObservationVerification(Base):
    __tablename__ = "observation_verification"

    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="pending_review", nullable=False)
    evidence_tier: Mapped[str] = mapped_column(String(30), default="unverified", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_id: Mapped[str | None] = mapped_column(ForeignKey("reviews.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class ReviewAssignment(Base):
    __tablename__ = "review_assignments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ras"))
    observation_id: Mapped[str] = mapped_column(
        ForeignKey("observations.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    area_code: Mapped[str] = mapped_column(String(64), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


# ---------------------------------------------------------------------------
# Forecast and weather
# ---------------------------------------------------------------------------
class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"
    __table_args__ = (Index("ix_weather_geo_source", "geo_code", "source_timestamp"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("wxs"))
    geo_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    completeness: Mapped[float] = mapped_column(Numeric(4, 3), default=0, nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("fs"))
    crop_code: Mapped[str] = mapped_column(String(60), nullable=False)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False)
    geo_code: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_time: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    features: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_refs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        Index("ix_forecasts_lookup", "crop_code", "target_code", "geo_code", "issue_time"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("fcst"))
    crop_code: Mapped[str] = mapped_column(String(60), nullable=False)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False)
    geo_code: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_time: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    valid_to: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    risk_band: Mapped[str] = mapped_column(String(30), nullable=False)
    probability: Mapped[float | None] = mapped_column(Numeric(6, 5), nullable=True)
    confidence_band: Mapped[str] = mapped_column(
        String(20), default="not_calibrated", nullable=False
    )
    coverage: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    coverage_detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    drivers: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    feature_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("feature_snapshots.id"), nullable=True
    )
    boundary_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("frn"))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="running", nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    areas_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    areas_scored: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    areas_insufficient: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Advisory and alerts
# ---------------------------------------------------------------------------
class Advisory(Base):
    __tablename__ = "advisories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("adv"))
    crop_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False)
    geo_scope: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    withdrawal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class AdvisoryVersion(Base):
    __tablename__ = "advisory_versions"
    __table_args__ = (UniqueConstraint("advisory_id", "version", name="uq_advisory_version"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("advv"))
    advisory_id: Mapped[str] = mapped_column(
        ForeignKey("advisories.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    action_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(400), default="", nullable=False)
    season: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    valid_to: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class AdvisoryApproval(Base):
    __tablename__ = "advisory_approvals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("adva"))
    version_id: Mapped[str] = mapped_column(
        ForeignKey("advisory_versions.id"), nullable=False, index=True
    )
    approver_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AlertPolicy(Base):
    __tablename__ = "alert_policies"
    __table_args__ = (Index("ix_alert_policies_scope", "geo_code", "target_code"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("apol"))
    geo_code: Mapped[str] = mapped_column(String(64), nullable=False)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False)
    min_band: Mapped[str] = mapped_column(String(30), default="high", nullable=False)
    min_coverage: Mapped[str] = mapped_column(String(20), default="partial", nullable=False)
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    channels: Mapped[list] = mapped_column(JSON, default=lambda: ["in_app"], nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("alrt"))
    forecast_id: Mapped[str] = mapped_column(ForeignKey("forecasts.id"), nullable=False, index=True)
    geo_code: Mapped[str] = mapped_column(String(64), nullable=False)
    target_code: Mapped[str] = mapped_column(String(80), nullable=False)
    band: Mapped[str] = mapped_column(String(30), nullable=False)
    window_from: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    window_to: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    message_version: Mapped[str] = mapped_column(String(80), nullable=False)
    coverage: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("adl"))
    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    suppressed_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class AlertFeedback(Base):
    __tablename__ = "alert_feedback"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("afb"))
    delivery_id: Mapped[str] = mapped_column(
        ForeignKey("alert_deliveries.id"), nullable=False, index=True
    )
    rating: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", "target_code", name="uq_notification_pref"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("npr"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    target_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


# ---------------------------------------------------------------------------
# Registry, audit and idempotency
# ---------------------------------------------------------------------------
class ModelRegistry(Base):
    __tablename__ = "model_registry"
    __table_args__ = (UniqueConstraint("kind", "version", name="uq_model_kind_version"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("mdl"))
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    artefact_key: Mapped[str | None] = mapped_column(String(400), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("aud"))
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("user_id", "scope", "key", name="uq_idempotency_user_scope_key"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("idm"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(80), nullable=False)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("exp"))
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(400), nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)


class SystemConfig(Base):
    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
# The chat schema (``conversations``, ``messages``, ``message_events``,
# ``image_uploads`` and ``chat_review_requests``) is owned by the
# ``conversations`` module and migrated by Alembic ``0002_chat_persistence``.
# It is re-exported above so ``app.db.models`` remains the single import
# surface for ORM models. ``ReviewRequest`` earlier in this file is the
# observation-review queue (``review_requests``); the chat request is a
# separate table (``chat_review_requests``) so the two workflows cannot be
# confused.
class MessageAttachment(Base):
    """Optional link from a chat message to a stored image asset.

    Not used by the Phase 2 chat slice, which stores the image descriptor on
    ``messages.image``; kept for the observation/image-asset integration.
    """

    __tablename__ = "message_attachments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("mat"))
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), nullable=False, index=True)
    image_id: Mapped[str] = mapped_column(ForeignKey("image_assets.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
