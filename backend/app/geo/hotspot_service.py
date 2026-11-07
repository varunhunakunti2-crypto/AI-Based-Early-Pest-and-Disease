"""Hotspot intelligence engine for H3 hexagonal geographic surveillance.

Calculates dynamic hotspot scores per H3 cell for disease and pest outbreaks,
with configurable thresholds and classification (LOW/MODERATE/HIGH/CRITICAL).

Key principles:
- Never treats every uploaded image as a separate affected farm (deduplicates by farm)
- Separates disease reports from pest reports
- Separates by crop type
- Weather is a risk factor, not proof of infestation
- Configurable thresholds calibrated using actual agricultural data
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.h3_config import default_resolution
from app.db.models import (
    DiseaseReport,
    GeoObservation,
    HotspotCluster,
    HotspotHistory,
    PestReport,
    RegionalRiskScore,
    WeatherCellRecord,
)
from app.geo import h3_get_resolution, k_ring


# ---------------------------------------------------------------------------
# Classification thresholds
# ---------------------------------------------------------------------------

# These thresholds are configurable via system configuration.
# Default values are starting points; they should be calibrated using
# actual agricultural data from pilot deployments.
DEFAULT_HOTSPOT_THRESHOLDS = {
    "low": 0.00,
    "moderate": 0.25,
    "high": 0.50,
    "critical": 0.75,
}

# Weight factors for hotspot score calculation
HOTOPSOT_WEIGHTS = {
    "report_count": 0.20,        # Volume of reports
    "unique_farms": 0.25,        # Unique affected farms (deduplicated)
    "verified_ratio": 0.25,      # Proportion of verified reports
    "severity": 0.20,            # Severity distribution
    "recency": 0.10,             # How recent the reports are
}

# Severity weights for scoring
SEVERITY_WEIGHTS = {
    "none": 0.0,
    "low": 0.25,
    "moderate": 0.50,
    "high": 0.75,
    "critical": 1.0,
}

# Reporter type weights
REPORTER_WEIGHTS = {
    "farmer": 0.6,
    "field_agent": 0.8,
    "expert": 1.0,
    "ai_system": 0.5,
}


def classify_hotspot(score: float, thresholds: Optional[dict] = None) -> str:
    """Classify a hotspot score into LOW/MODERATE/HIGH/CRITICAL."""
    thresholds = thresholds or DEFAULT_HOTSPOT_THRESHOLDS
    if score >= thresholds["critical"]:
        return "critical"
    if score >= thresholds["high"]:
        return "high"
    if score >= thresholds["moderate"]:
        return "moderate"
    return "low"


def compute_hotspot_score(
    total_reports: int,
    unique_farms: int,
    verified_farms: int,
    severity_distribution: dict,
    recency_factor: float,
    config: Optional[dict] = None,
) -> float:
    """Compute a composite hotspot score (0.0 to 1.0).

    Factors:
    - report_count: Volume of reports (normalized)
    - unique_farms: Number of unique affected farms (deduplicated)
    - verified_ratio: Proportion of verified reports
    - severity: Weighted average severity
    - recency: How recent the reports are
    """
    config = config or {}
    weights = config.get("weights", HOTOPSOT_WEIGHTS)
    thresholds = config.get("thresholds", DEFAULT_HOTSPOT_THRESHOLDS)

    # Normalize report count (logarithmic scale to prevent saturation)
    report_score = min(1.0, total_reports / 20.0)  # 20+ reports = max score

    # Unique farms score (normalized)
    farm_score = min(1.0, unique_farms / 10.0)  # 10+ unique farms = max score

    # Verified ratio
    verified_ratio = verified_farms / total_reports if total_reports > 0 else 0.0

    # Severity weighted average
    total_weight = sum(SEVERITY_WEIGHTS.get(k, 0) * v for k, v in severity_distribution.items())
    total_count = sum(severity_distribution.values()) or 1
    severity_score = total_weight / total_count

    # Composite score
    score = (
        weights["report_count"] * report_score
        + weights["unique_farms"] * farm_score
        + weights["verified_ratio"] * verified_ratio
        + weights["severity"] * severity_score
        + weights["recency"] * recency_factor
    )

    return round(min(1.0, max(0.0, score)), 4)


def compute_recency_factor(
    most_recent_report: Optional[datetime],
    window_days: int = 14,
) -> float:
    """Compute recency factor (0.0 to 1.0) based on most recent report."""
    if most_recent_report is None:
        return 0.0
    now = datetime.now(most_recent_report.tzinfo) if most_recent_report.tzinfo else datetime.utcnow()
    age_days = (now - most_recent_report).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    if age_days >= window_days:
        return 0.0
    return 1.0 - (age_days / window_days)


# ---------------------------------------------------------------------------
# Hotspot calculation
# ---------------------------------------------------------------------------


def calculate_hotspot_for_cell(
    db: Session,
    h3_cell_id: str,
    target_type: str,
    target_code: str,
    crop_code: Optional[str] = None,
    resolution: Optional[int] = None,
    thresholds: Optional[dict] = None,
    weather_risk_factor: Optional[float] = None,
) -> dict:
    """Calculate hotspot score and classification for a single H3 cell.

    Parameters
    ----------
    db: Database session
    h3_cell_id: H3 cell ID string
    target_type: 'disease' or 'pest'
    target_code: Disease or pest target code
    crop_code: Optional crop code filter
    resolution: H3 resolution (defaults to field-level 9)
    thresholds: Optional custom classification thresholds
    weather_risk_factor: Optional weather risk factor (0-1)

    Returns
    -------
    dict with hotspot calculation results
    """
    if resolution is None:
        resolution = default_resolution()

    # Gather observations from geo_observations table
    obs_query = select(GeoObservation).where(
        GeoObservation.h3_cell_id == h3_cell_id,
        GeoObservation.resolution == resolution,
        GeoObservation.target_code == target_code,
    )
    if crop_code:
        obs_query = obs_query.where(GeoObservation.crop_code == crop_code)
    obs_rows = db.scalars(obs_query).all()

    # Gather from disease_reports or pest_reports table
    if target_type == "disease":
        report_query = select(DiseaseReport).where(
            DiseaseReport.h3_cell_id == h3_cell_id,
            DiseaseReport.resolution == resolution,
            DiseaseReport.target_code == target_code,
        )
    else:
        report_query = select(PestReport).where(
            PestReport.h3_cell_id == h3_cell_id,
            PestReport.resolution == resolution,
            PestReport.target_code == target_code,
        )
    if crop_code:
        report_query = report_query.where(
            DiseaseReport.crop_code == crop_code
            if target_type == "disease"
            else PestReport.crop_code == crop_code
        )
    report_rows = db.scalars(report_query).all()

    # Aggregate statistics (deduplicated by farm)
    total_reports = sum(r.case_count for r in report_rows)
    unique_farms = sum(r.unique_farms for r in report_rows)
    verified_farms = sum(r.verified_farms for r in report_rows)
    unverified_reports = total_reports - verified_farms

    # Also count from observations
    obs_count = len(obs_rows)
    obs_verified = sum(1 for r in obs_rows if r.verification_status == "confirmed")
    obs_pending = sum(1 for r in obs_rows if r.verification_status == "pending_review")

    # Combine: use the max of reports table and observations table for counts
    # This ensures we don't double-count but capture all sources
    total_reports = max(total_reports, obs_count)
    verified_farms = max(verified_farms, obs_verified)
    unverified_reports = max(0, total_reports - verified_farms)

    # Severity distribution
    severity_dist = {}
    for r in report_rows:
        if r.severity_distribution:
            for sev, count in r.severity_distribution.items():
                severity_dist[sev] = severity_dist.get(sev, 0) + count

    # Find dates
    dates = [r.event_date for r in report_rows if r.event_date]
    obs_dates = [r.event_date for r in obs_rows if r.event_date]
    all_dates = dates + obs_dates
    first_reported = min(all_dates) if all_dates else None
    most_recent_report = max(all_dates) if all_dates else None

    # Recency factor
    recency = compute_recency_factor(most_recent_report)

    # Compute score
    score = compute_hotspot_score(
        total_reports=total_reports,
        unique_farms=unique_farms,
        verified_farms=verified_farms,
        severity_distribution=severity_dist,
        recency_factor=recency,
        config={"weights": HOTOPSOT_WEIGHTS, "thresholds": thresholds or DEFAULT_HOTSPOT_THRESHOLDS},
    )

    # Apply weather risk factor as a multiplier (weather is a risk factor, not proof)
    if weather_risk_factor is not None:
        # Weather can boost the score but not create a hotspot from nothing
        score = round(min(1.0, score * (1.0 + weather_risk_factor * 0.3)), 4)

    # Classification
    classification = classify_hotspot(score, thresholds or DEFAULT_HOTSPOT_THRESHOLDS)

    # Neighbor cells that are also hotspots
    neighbor_cell_ids = k_ring(int(h3_cell_id), k=1)
    neighbor_cell_ids = [str(cid) for cid in neighbor_cell_ids if cid != int(h3_cell_id)]

    result = {
        "h3_cell_id": h3_cell_id,
        "resolution": resolution,
        "target_type": target_type,
        "target_code": target_code,
        "crop_code": crop_code,
        "classification": classification,
        "score": score,
        "total_reports": total_reports,
        "unique_affected_farms": unique_farms,
        "verified_farms": verified_farms,
        "unverified_reports": unverified_reports,
        "pending_reviews": obs_pending,
        "severity_distribution": severity_dist,
        "first_reported": first_reported.isoformat() if first_reported else None,
        "most_recent_report": most_recent_report.isoformat() if most_recent_report else None,
        "recency_factor": round(recency, 4),
        "weather_risk_factor": weather_risk_factor,
        "neighbor_cells": neighbor_cell_ids,
        "historical_frequency": round(len(all_dates) / 30.0, 4),  # reports per 30 days
    }

    return result


def update_hotspot_cluster(
    db: Session,
    h3_cell_id: str,
    target_type: str,
    target_code: str,
    crop_code: Optional[str] = None,
    resolution: Optional[int] = None,
    thresholds: Optional[dict] = None,
    weather_risk_factor: Optional[float] = None,
    is_demo: bool = False,
) -> HotspotCluster:
    """Calculate and persist a hotspot cluster for an H3 cell."""
    if resolution is None:
        resolution = default_resolution()

    result = calculate_hotspot_for_cell(
        db=db,
        h3_cell_id=h3_cell_id,
        target_type=target_type,
        target_code=target_code,
        crop_code=crop_code,
        resolution=resolution,
        thresholds=thresholds,
        weather_risk_factor=weather_risk_factor,
    )

    # Upsert: update existing or create new
    existing = db.scalar(
        select(HotspotCluster).where(
            HotspotCluster.h3_cell_id == h3_cell_id,
            HotspotCluster.target_type == target_type,
            HotspotCluster.target_code == target_code,
            HotspotCluster.resolution == resolution,
        )
    )

    now = datetime.utcnow()

    if existing is None:
        cluster = HotspotCluster(
            h3_cell_id=h3_cell_id,
            resolution=resolution,
            target_type=target_type,
            target_code=target_code,
            crop_code=crop_code,
            classification=result["classification"],
            score=result["score"],
            total_reports=result["total_reports"],
            unique_affected_farms=result["unique_affected_farms"],
            verified_farms=result["verified_farms"],
            unverified_reports=result["unverified_reports"],
            pending_reviews=result["pending_reviews"],
            severity_distribution=result["severity_distribution"],
            first_reported=result["first_reported"],
            most_recent_report=result["most_recent_report"],
            historical_frequency=result["historical_frequency"],
            weather_risk_factor=result["weather_risk_factor"],
            neighbor_cells=result["neighbor_cells"],
            calculated_at=now,
            is_demo=is_demo,
        )
        db.add(cluster)
        db.flush()
        return cluster
    else:
        existing.classification = result["classification"]
        existing.score = result["score"]
        existing.total_reports = result["total_reports"]
        existing.unique_affected_farms = result["unique_affected_farms"]
        existing.verified_farms = result["verified_farms"]
        existing.unverified_reports = result["unverified_reports"]
        existing.pending_reviews = result["pending_reviews"]
        existing.severity_distribution = result["severity_distribution"]
        existing.first_reported = result["first_reported"]
        existing.most_recent_report = result["most_recent_report"]
        existing.historical_frequency = result["historical_frequency"]
        existing.weather_risk_factor = result["weather_risk_factor"]
        existing.neighbor_cells = result["neighbor_cells"]
        existing.calculated_at = now
        db.flush()
        return existing


def record_hotspot_history(
    db: Session,
    h3_cell_id: str,
    target_type: str,
    target_code: str,
    classification: str,
    score: float,
    unique_affected_farms: int,
    weather_risk_factor: Optional[float] = None,
    snapshot_date: Optional[datetime] = None,
    is_demo: bool = False,
) -> HotspotHistory:
    """Record a hotspot history snapshot for trend analysis."""
    if snapshot_date is None:
        snapshot_date = datetime.utcnow()

    history = HotspotHistory(
        h3_cell_id=h3_cell_id,
        target_type=target_type,
        target_code=target_code,
        snapshot_date=snapshot_date,
        classification=classification,
        score=score,
        unique_affected_farms=unique_affected_farms,
        weather_risk_factor=weather_risk_factor,
        is_demo=is_demo,
    )
    db.add(history)
    db.flush()
    return history


def get_hotspot_classification_label(classification: str) -> dict:
    """Return human-readable label and color for a hotspot classification."""
    labels = {
        "low": {"label": "Low Risk", "color": "#2f6f4e", "severity": "low"},
        "moderate": {"label": "Moderate Risk", "color": "#9a6700", "severity": "moderate"},
        "high": {"label": "High Risk", "color": "#c2410c", "severity": "high"},
        "critical": {"label": "Critical Risk", "color": "#b42318", "severity": "critical"},
    }
    return labels.get(classification, labels["low"])


# ---------------------------------------------------------------------------
# Batch hotspot calculation
# ---------------------------------------------------------------------------


def recalculate_all_hotspots(
    db: Session,
    target_type: str,
    target_code: str,
    crop_code: Optional[str] = None,
    resolution: Optional[int] = None,
    is_demo: bool = False,
) -> list[HotspotCluster]:
    """Recalculate hotspots for all cells that have reports for a target."""
    if resolution is None:
        resolution = default_resolution()

    # Find all cells with reports for this target
    if target_type == "disease":
        report_query = select(DiseaseReport.h3_cell_id).where(
            DiseaseReport.resolution == resolution,
            DiseaseReport.target_code == target_code,
        )
    else:
        report_query = select(PestReport.h3_cell_id).where(
            PestReport.resolution == resolution,
            PestReport.target_code == target_code,
        )
    if crop_code:
        report_query = report_query.where(
            DiseaseReport.crop_code == crop_code
            if target_type == "disease"
            else PestReport.crop_code == crop_code
        )
    cell_ids = [row[0] for row in db.execute(report_query).all()]

    clusters = []
    for cell_id in cell_ids:
        cluster = update_hotspot_cluster(
            db=db,
            h3_cell_id=cell_id,
            target_type=target_type,
            target_code=target_code,
            crop_code=crop_code,
            resolution=resolution,
            is_demo=is_demo,
        )
        clusters.append(cluster)

    return clusters


__all__ = [
    "DEFAULT_HOTSPOT_THRESHOLDS",
    "HOTOPSOT_WEIGHTS",
    "SEVERITY_WEIGHTS",
    "REPORTER_WEIGHTS",
    "classify_hotspot",
    "compute_hotspot_score",
    "compute_recency_factor",
    "calculate_hotspot_for_cell",
    "update_hotspot_cluster",
    "record_hotspot_history",
    "get_hotspot_classification_label",
    "recalculate_all_hotspots",
]
