"""Version 1 API router.

Every route that exposes data or initiates work must be routed through this
table. An unrouted endpoint is dead code; a routed endpoint without an
authorisation dependency is a defect.
"""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    advisories,
    alerts,
    assessments,
    auth,
    conversations,
    detections,
    forecast,
    health,
    map,
    me,
    observations,
    review,
    uploads,
    videos,
)

api_router = APIRouter()

# Health
api_router.include_router(health.router)

# Auth & identity
api_router.include_router(auth.router)
if hasattr(auth, "admin_router"):
    api_router.include_router(auth.admin_router)
api_router.include_router(me.router)
api_router.include_router(admin.router)

# Observations & review
api_router.include_router(observations.router)
api_router.include_router(review.router)

# Advisories
api_router.include_router(advisories.router)
if hasattr(advisories, "admin_router"):
    api_router.include_router(advisories.admin_router)

# Alerts
api_router.include_router(alerts.router)
if hasattr(alerts, "admin_router"):
    api_router.include_router(alerts.admin_router)

# Forecast
api_router.include_router(forecast.router)
if hasattr(forecast, "admin_router"):
    api_router.include_router(forecast.admin_router)

# Conversations, uploads & assessments
api_router.include_router(conversations.router)
api_router.include_router(uploads.router)
api_router.include_router(assessments.router)

# Demo-labelled pretrained detections (isolated ml/serve process)
api_router.include_router(detections.router)

# Map
api_router.include_router(map.router)
api_router.include_router(videos.router)
