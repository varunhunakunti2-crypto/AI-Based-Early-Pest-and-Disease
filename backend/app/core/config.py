"""Application settings.

Values come from environment variables prefixed with ``APP_`` or from a local
``.env`` file. No secrets belong in source control.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class ChatLabel(BaseModel):
    """One candidate label the vision provider is allowed to choose.

    The approved crop/target taxonomy is a product decision (D1/D2). It is not
    hard-coded here: a deployment supplies the approved labels as JSON and marks
    them approved. Until then results stay visibly demo-labelled.
    """

    label: str
    display_name: str

    @field_validator("label", "display_name")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("chat label fields must not be blank")
        return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )

    app_name: str = "PS-03 API"
    environment: str = "dev"
    version: str = "0.1.0"
    api_v1_prefix: str = "/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Photo-assessment deployment configuration. Both paths must be supplied
    # by the deployment; there is deliberately no built-in taxonomy, crop list
    # or operating point.
    assessment_policy_path: str | None = None
    model_registry_path: str | None = None
    assessment_inference_timeout_s: float = 5.0
    assessment_inference_attempts: int = 2

    # Chat assessment engine. ``demo`` serves a deterministic, visibly labelled
    # synthetic result so the end-to-end path works without an external model.
    # ``openai_compatible`` calls a vision provider behind the same seam.
    # Unknown values fail closed with ``model_not_configured``.
    chat_engine: str = "demo"

    # OpenAI-compatible vision provider. The key is read from the environment
    # or an untracked .env and is never logged. Empty key/model/labels fail
    # closed at request time rather than inventing an assessment.
    chat_api_key: str | None = None
    chat_base_url: str = "https://api.openai.com/v1"
    chat_model: str | None = None
    # Approved candidate labels, supplied as JSON. Example:
    # APP_CHAT_LABELS=[{"label":"early_blight","display_name":"Possible early blight"}]
    chat_labels: list[ChatLabel] = []
    # ``is_demo`` stays true until the operator confirms the label set is the
    # approved release taxonomy. No taxonomy is invented in code.
    chat_labels_approved: bool = False
    chat_timeout_s: float = 30.0
    chat_max_image_side: int = 1024

    # Pretrained YOLO detectors. They run in the isolated service in ``ml/serve``
    # because ``ultralytics`` is AGPL-3.0; the backend reaches it over HTTP only.
    # ``chat_engine=pretrained`` selects the client engine. Output is always
    # demo-labelled until the D1a taxonomy and calibration are approved.
    pretrained_inference_url: str = "http://127.0.0.1:8010"
    pretrained_model: str = "plant"
    pretrained_conf: float = 0.25
    pretrained_timeout_s: float = 60.0

    # Chat image uploads. Local development storage only; a deployment replaces
    # this with object storage. No file is ever served without an owner check.
    media_root: str = "var/media"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_dimension: int = 8000

    # Video reading (spec 09). Short clips only. Every ceiling is enforced before
    # or during decode so a hostile file cannot exhaust the worker. Sampling is
    # deterministic for the same file and settings.
    video_max_bytes: int = 50 * 1024 * 1024
    video_max_duration_s: float = 30.0
    video_max_dimension: int = 1920
    video_sample_fps: float = 2.0
    video_max_frames: int = 24
    video_frame_max_side: int = 1024
    video_min_usable_frames: int = 3
    video_min_duration_ms: int = 500
    video_assess_frames: int = 3
    video_track_iou: float = 0.3
    video_track_max_age: int = 5
    video_motion_threshold: int = 25
    video_motion_min_area_fraction: float = 0.005

    # Logging: one JSON event per line, no payloads and no PII.
    log_level: str = "INFO"

    # Interactive API docs are for dev/staging only; production may disable them.
    docs_enabled: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    # Persistence. PostgreSQL 16 + PostGIS is the production target; SQLite
    # keeps local development and the test suite runnable without services.
    database_url: str = f"sqlite:///{(BACKEND_ROOT / 'var' / 'ps03.db').as_posix()}"
    seed_reference_data: bool = True
    seed_demo_users: bool = False

    # Bootstrap admin (development only; must be supplied through the
    # environment in any deployed setting).
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_mfa_secret: str | None = None

    # Tokens and sessions.
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    mfa_challenge_minutes: int = 5

    # OTP and authentication throttling.
    otp_ttl_minutes: int = 5
    otp_max_attempts: int = 5
    expose_otp_in_dev: bool = True
    auth_rate_limit_per_minute: int = 30

    # Identity (spec 03). The default secret is for local development only;
    # production startup refuses it. Tokens, OTPs and lockout limits are kept
    # here so a deployment can tune them without a code change.
    auth_secret: str = "dev-only-insecure-secret-change-me"
    auth_access_ttl_minutes: int = 15
    auth_refresh_ttl_days: int = 30
    auth_mfa_challenge_ttl_minutes: int = 5
    auth_otp_ttl_minutes: int = 5
    auth_otp_max_attempts: int = 5
    auth_otp_phone_limit: int = 5
    auth_otp_ip_limit: int = 20
    auth_otp_rate_window_minutes: int = 15
    auth_staff_failure_limit: int = 10
    auth_staff_lockout_minutes: int = 15

    # Decision D10 is open. ``None`` means a deleted account is soft-deleted
    # with no hard-delete date; do not invent a retention period here.
    auth_deletion_retention_days: int | None = None

    # First-admin bootstrap. Never a public endpoint and never logged. All
    # three values must be supplied together; the TOTP secret is the base32
    # seed the admin enrols in their authenticator.
    auth_bootstrap_admin_email: str | None = None
    auth_bootstrap_admin_password: str | None = None
    auth_bootstrap_admin_totp_secret: str | None = None

    # Media storage.
    storage_backend: str = "local"
    storage_root: Path = BACKEND_ROOT / "var" / "storage"
    upload_url_ttl_seconds: int = 900
    signed_url_ttl_seconds: int = 300
    min_image_dimension: int = 480
    allowed_image_types: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # Versioned model inputs. Every prediction carries the version string it
    # was produced with; nothing here represents a trained production model.
    quality_gate_version: str = "demo-quality-gate-0.1"
    image_model_version: str = "demo-image-classifier-0.1"
    forecast_model_version: str = "demo-rules-forecast-0.1"

    # Forecast and coverage thresholds (demo configuration pending sign-off).
    forecast_horizon_days: int = 10
    weather_stale_hours: int = 24
    min_active_reporters: int = 3
    small_count_threshold: int = 5


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
