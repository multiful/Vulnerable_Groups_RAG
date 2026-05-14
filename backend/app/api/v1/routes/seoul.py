# File: seoul.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: GET /api/v1/seoul/job-cafes, /health-centers, /reservations
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.api.deps import SettingsDep
from backend.app.services import seoul_service

router = APIRouter(prefix="/seoul")


@router.get("/job-cafes")
def get_job_cafes(
    settings: SettingsDep,
    gu: str | None = Query(default=None, description="구 이름으로 필터 (예: 강남구)"),
) -> dict:
    """서울시 일자리카페 위치·정보 조회."""
    return seoul_service.get_job_cafes(settings, gu=gu)


@router.get("/health-centers")
def get_health_centers(
    settings: SettingsDep,
    gu: str | None = Query(default=None, description="구 이름으로 필터 (예: 마포구)"),
) -> dict:
    """
    서울시 건강증진센터 정보 조회.
    회복 단계 청년에게 가까운 지원 공간을 안내합니다.
    """
    return seoul_service.get_health_centers(settings, gu=gu)


@router.get("/reservations")
def get_public_reservations(
    settings: SettingsDep,
    gu: str | None = Query(default=None, description="구 이름으로 필터"),
    service_type: str | None = Query(default=None, description="서비스 유형 (예: 체육시설, 문화시설)"),
) -> dict:
    """서울시 공공서비스 예약 정보 조회 ('오늘 공부하러 가기' CTA용)."""
    return seoul_service.get_public_reservations(settings, service_type=service_type, gu=gu)
