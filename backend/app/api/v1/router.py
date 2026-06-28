# File: router.py
# Last Updated: 2026-06-26 (hrd_extended 라우터 추가)
# Content Hash: SHA256:TBD
# Role: /api/v1 라우터 집결
from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.routes import (
    action,
    admin,
    career_net,
    cert_info,
    cert_videos,
    chat,
    health,
    hrd_extended,
    isolation_policy,
    jobs,
    jobs_info,
    map,
    ncs,
    recommendation,
    risk,
    roadmap,
    schedule,
    seoul,
    support,
    training,
    youth_center,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(risk.router, tags=["risk"])
api_router.include_router(recommendation.router, tags=["recommendation"])
api_router.include_router(roadmap.router, tags=["roadmap"])
api_router.include_router(schedule.router, tags=["schedule"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(cert_videos.router, tags=["cert_videos"])
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(jobs_info.router, tags=["jobs_info"])
api_router.include_router(training.router, tags=["training"])
api_router.include_router(seoul.router, tags=["seoul"])
api_router.include_router(action.router, tags=["action"])
api_router.include_router(map.router, tags=["map"])
api_router.include_router(career_net.router, tags=["career_net"])
api_router.include_router(cert_info.router, tags=["cert_info"])
api_router.include_router(ncs.router, tags=["ncs"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(support.router, tags=["support"])
api_router.include_router(isolation_policy.router, tags=["isolation_policy"])
api_router.include_router(youth_center.router, tags=["youth_center"])
api_router.include_router(hrd_extended.router, tags=["hrd_extended"])
