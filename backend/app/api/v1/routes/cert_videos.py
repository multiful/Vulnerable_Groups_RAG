# File: cert_videos.py
# Last Updated: 2026-05-12
# Content Hash: SHA256:TBD
# Role: F-11 관련 동영상 추천 엔드포인트 — GET /api/v1/certs/{cert_id}/videos
from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.deps import SettingsDep
from backend.app.services import youtube_service

router = APIRouter()


@router.get("/certs/{cert_id}/videos")
def get_cert_videos(cert_id: str, settings: SettingsDep) -> dict:
    """자격증 관련 YouTube 영상 5개 반환 (캐시 우선, TTL 30일)."""
    return youtube_service.get_cert_videos(cert_id, settings)
