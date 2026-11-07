"""Weather-based regional risk intelligence for H3 cells.

Combines weather conditions, crop type, growth stage, pest/disease biology,
and historical observations to compute risk indicators per H3 cell.

IMPORTANT: Weather is a risk factor, not proof of infestation.
Do not recommend pesticides solely because weather conditions are favourable.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.h3_config import default_resolution
from app.db.models import (
    Crop,
    RegionalRiskScore,
    WeatherCellRecord,
    GeoObservation,
)
from app.geo import geo_to_h3, h3_get_resolution


# Default weather risk thresholds for common crop-disease combinations
# These are starting points; should be calibrated with local agricultural data
WEATHER_RISK_MODELS = {
    # crop_code: { target_code: { temp_min, temp_max, humidity_min, rainfall_min, ... } }
    "rice": {
        "blast": {
            "temp_optimal": [25, 30],
            "humidity_min": 85,
            "rainfall_min": 5,
            "leaf_wetness_min": 10,
            "risk_multiplier": 1.0,
        },
        "brown_spot": {
            "temp_optimal": [28, 32],
            "humidity_min": 70,
            "rainfall_min": 0,
            "risk_multiplier": 0.8,
        },
    },
    "tomato": {
        "early_blight": {
            "temp_optimal": [24, 29],
            "humidity_min": 85,
            "rainfall_min": 2,
            "leaf_wetness_min": 8,
            "risk_multiplier": 1.0,
        },
        "late_blight": {
            "temp_optimal": [15, 21],
            "humidity_min": 90,
            "rainfall_min": 5,
            "leaf_wetness_min": 10,
            "risk_multiplier": 1.2,
        },
    },
    "maize": {
        "fall_armyworm": {
            "temp_optimal": [25, 30],
            "humidity_min": 60,
            "rainfall_min": 0,
            "risk_multiplier": 0.9,
        },
    },
}

# Growth stage risk multipliers
GROWTH_STAGE_RISK = {
    "seedling": 0.6,
    "vegetative": 0.8,
    "flowering": 1.0,
    "fruiting": 1.1,
    "maturity": 0.7,
    "harvest": 0.4,
}


def compute_weather_risk(
    weather_variables: dict,
    crop_code: str,
    target_code: str,
    growth_stage: Optional[str] = None,
) -> dict:
    """Compute weather suitability risk for a crop-disease combination.

    Returns a dict with:
    - weather_risk: 0.0 to 1.0 weather suitability score
    - contributing_factors: breakdown of factors
    - model_used: which weather model was applied
    """
    model = WEATHER_RISK_MODELS.get(crop_code, {}).get(target_code)

    if model is None:
        # No specific model: return generic risk based on general conditions
        return _generic_weather_risk(weather_variables)

    temp = weather_variables.get("temperature_mean_c", weather_variables.get("temp_mean"))
    humidity = weather_variables.get("relative_humidity_mean_pct", weather_variables.get("rh_mean"))
    rainfall = weather_variables.get("rainfall_mm", weather_variables.get("precipitation", 0))
    leaf_wetness = weather_variables.get("leaf_wetness_proxy_hours", 0)

    temp_optimal = model["temp_optimal"]
    humidity_min = model["humidity_min"]
    rainfall_min = model.get("rainfall_min", 0)
    leaf_wetness_min = model.get("leaf_wetness_min", 0)

    factors = {}

    # Temperature suitability (0-1)
    if temp is not None:
        if temp_optimal[0] <= temp <= temp_optimal[1]:
            temp_score = 1.0
        elif temp < temp_optimal[0]:
            temp_score = max(0.0, 1.0 - (temp_optimal[0] - temp) / 10.0)
        else:
            temp_score = max(0.0, 1.0 - (temp - temp_optimal[1]) / 10.0)
    else:
        temp_score = 0.5  # Unknown
    factors["temperature"] = round(temp_score, 3)

    # Humidity suitability (0-1)
    if humidity is not None:
        humidity_score = min(1.0, humidity / max(humidity_min, 1)) if humidity < humidity_min else 1.0
    else:
        humidity_score = 0.5
    factors["humidity"] = round(humidity_score, 3)

    # Rainfall suitability (0-1)
    if rainfall is not None:
        if rainfall_min > 0:
            rainfall_score = min(1.0, rainfall / rainfall_min)
        else:
            # Some diseases prefer dry conditions
            rainfall_score = 0.5
    else:
        rainfall_score = 0.5
    factors["rainfall"] = round(rainfall_score, 3)

    # Leaf wetness suitability (0-1)
    if leaf_wetness is not None:
        wetness_score = min(1.0, leaf_wetness / max(leaf_wetness_min, 1))
    else:
        wetness_score = 0.5
    factors["leaf_wetness"] = round(wetness_score, 3)

    # Combined weather risk (weighted average)
    weather_risk = (
        0.3 * temp_score
        + 0.3 * humidity_score
        + 0.2 * rainfall_score
        + 0.2 * wetness_score
    )

    # Apply growth stage multiplier
    stage_multiplier = GROWTH_STAGE_RISK.get(growth_stage, 0.8) if growth_stage else 0.8
    weather_risk = round(min(1.0, weather_risk * stage_multiplier), 4)

    # Apply model risk multiplier
    model_multiplier = model.get("risk_multiplier", 1.0)
    weather_risk = round(min(1.0, weather_risk * model_multiplier), 4)

    factors["growth_stage"] = stage_multiplier
    factors["model_multiplier"] = model_multiplier

    return {
        "weather_risk": weather_risk,
        "contributing_factors": factors,
        "model_used": f"{crop_code}:{target_code}",
    }


def _generic_weather_risk(weather_variables: dict) -> dict:
    """Generic weather risk calculation when no specific model exists."""
    temp = weather_variables.get("temperature_mean_c", 25)
    humidity = weather_variables.get("relative_humidity_mean_pct", 70)

    # Generic favorable conditions: temp 20-30, humidity 60-90
    temp_score = 1.0 if 20 <= temp <= 30 else max(0.0, 1.0 - abs(temp - 25) / 15.0)
    humidity_score = min(1.0, humidity / 80.0) if humidity < 80 else 1.0

    weather_risk = round(0.5 * temp_score + 0.5 * humidity_score, 4)

    return {
        "weather_risk": weather_risk,
        "contributing_factors": {
            "temperature": round(temp_score, 3),
            "humidity": round(humidity_score, 3),
        },
        "model_used": "generic",
    }


def compute_biological_risk(
    crop_code: str,
    target_code: str,
    historical_frequency: float,
    verified_reports: int,
) -> float:
    """Compute biological risk based on pest/disease biology and history."""
    # Base biological risk from historical frequency
    freq_score = min(1.0, historical_frequency / 5.0)  # 5+ reports per period = max

    # Verification boost
    verify_score = min(1.0, verified_reports / 10.0)  # 10+ verified = max

    # Combined biological risk
    bio_risk = round(0.6 * freq_score + 0.4 * verify_score, 4)
    return bio_risk


def compute_historical_risk(
    db: Session,
    h3_cell_id: str,
    target_code: str,
    target_type: str,
    resolution: int,
    window_days: int = 90,
) -> float:
    """Compute historical risk based on past observations in the cell."""
    cutoff = datetime.utcnow() - timedelta(days=window_days)

    if target_type == "disease":
        from app.db.models import DiseaseReport

        rows = db.scalars(
            select(DiseaseReport).where(
                DiseaseReport.h3_cell_id == h3_cell_id,
                DiseaseReport.target_code == target_code,
                DiseaseReport.resolution == resolution,
                DiseaseReport.event_date >= cutoff,
            )
        ).all()
    else:
        from app.db.models import PestReport

        rows = db.scalars(
            select(PestReport).where(
                PestReport.h3_cell_id == h3_cell_id,
                PestReport.target_code == target_code,
                PestReport.resolution == resolution,
                PestReport.event_date >= cutoff,
            )
        ).all()

    total_reports = sum(r.case_count for r in rows)
    unique_farms = sum(r.unique_farms for r in rows)

    # Historical risk based on report frequency and unique farms
    hist_risk = round(min(1.0, (total_reports / 30.0) * 0.6 + (unique_farms / 10.0) * 0.4), 4)
    return hist_risk


def calculate_regional_risk(
    db: Session,
    h3_cell_id: str,
    crop_code: str,
    target_code: str,
    target_type: str,
    resolution: Optional[int] = None,
    growth_stage: Optional[str] = None,
    valid_days: int = 7,
    is_demo: bool = False,
) -> RegionalRiskScore:
    """Calculate comprehensive regional risk score for an H3 cell.

    Combines weather, biological, and historical risk factors.
    Weather is a risk factor, not proof of infestation.
    """
    if resolution is None:
        resolution = default_resolution()

    # Get latest weather for the cell
    weather_row = db.scalars(
        select(WeatherCellRecord).where(
            WeatherCellRecord.h3_cell_id == h3_cell_id,
            WeatherCellRecord.resolution == resolution,
        ).order_by(WeatherCellRecord.source_timestamp.desc())
    ).first()

    weather_risk = 0.0
    contributing_factors = {}
    if weather_row:
        weather_result = compute_weather_risk(
            weather_variables=weather_row.variables,
            crop_code=crop_code,
            target_code=target_code,
            growth_stage=growth_stage,
        )
        weather_risk = weather_result["weather_risk"]
        contributing_factors = weather_result["contributing_factors"]

    # Get historical risk
    historical_risk = compute_historical_risk(
        db=db,
        h3_cell_id=h3_cell_id,
        target_code=target_code,
        target_type=target_type,
        resolution=resolution,
    )

    # Get biological risk
    # Count verified reports for biological risk
    from app.db.models import DiseaseReport, PestReport

    if target_type == "disease":
        bio_rows = db.scalars(
            select(DiseaseReport).where(
                DiseaseReport.h3_cell_id == h3_cell_id,
                DiseaseReport.target_code == target_code,
                DiseaseReport.resolution == resolution,
            )
        ).all()
    else:
        bio_rows = db.scalars(
            select(PestReport).where(
                PestReport.h3_cell_id == h3_cell_id,
                PestReport.target_code == target_code,
                PestReport.resolution == resolution,
            )
        ).all()

    verified_reports = sum(r.verified_farms for r in bio_rows)
    hist_freq = len(bio_rows) / 12.0  # reports per month approx
    biological_risk = compute_biological_risk(
        crop_code=crop_code,
        target_code=target_code,
        historical_frequency=hist_freq,
        verified_reports=verified_reports,
    )

    # Composite risk score (weighted)
    # Weather: 30%, Biological: 40%, Historical: 30%
    risk_score = round(
        0.3 * weather_risk + 0.4 * biological_risk + 0.3 * historical_risk,
        4,
    )

    # Risk label
    if risk_score >= 0.75:
        risk_label = "critical"
    elif risk_score >= 0.50:
        risk_label = "high"
    elif risk_score >= 0.25:
        risk_label = "moderate"
    else:
        risk_label = "insufficient_data"

    contributing_factors.update({
        "weather_risk": weather_risk,
        "biological_risk": biological_risk,
        "historical_risk": historical_risk,
    })

    now = datetime.utcnow()
    valid_from = now
    valid_to = now + timedelta(days=valid_days)

    # Upsert
    existing = db.scalar(
        select(RegionalRiskScore).where(
            RegionalRiskScore.h3_cell_id == h3_cell_id,
            RegionalRiskScore.crop_code == crop_code,
            RegionalRiskScore.target_code == target_code,
            RegionalRiskScore.valid_from == valid_from,
        )
    )

    if existing is None:
        risk_record = RegionalRiskScore(
            h3_cell_id=h3_cell_id,
            resolution=resolution,
            crop_code=crop_code,
            target_code=target_code,
            valid_from=valid_from,
            valid_to=valid_to,
            risk_score=risk_score,
            weather_risk=weather_risk,
            biological_risk=biological_risk,
            historical_risk=historical_risk,
            risk_label=risk_label,
            contributing_factors=contributing_factors,
            is_demo=is_demo,
        )
        db.add(risk_record)
        db.flush()
        return risk_record
    else:
        existing.risk_score = risk_score
        existing.weather_risk = weather_risk
        existing.biological_risk = biological_risk
        existing.historical_risk = historical_risk
        existing.risk_label = risk_label
        existing.contributing_factors = contributing_factors
        existing.valid_to = valid_to
        db.flush()
        return existing


__all__ = [
    "WEATHER_RISK_MODELS",
    "GROWTH_STAGE_RISK",
    "compute_weather_risk",
    "compute_biological_risk",
    "compute_historical_risk",
    "calculate_regional_risk",
]
