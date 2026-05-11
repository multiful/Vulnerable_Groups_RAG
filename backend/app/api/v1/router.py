# File: router.py
# Last Updated: 2026-05-12
# Content Hash: SHA256:TBD
# Role: /api/v1 라우터 집결
from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.routes import (
    admin,
    cert_videos,
    health,
    recommendation,
    risk,
    roadmap,
    schedule,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(risk.router, tags=["risk"])
api_router.include_router(recommendation.router, tags=["recommendation"])
api_router.include_router(roadmap.router, tags=["roadmap"])
api_router.include_router(schedule.router, tags=["schedule"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(cert_videos.router, tags=["cert_videos"])
