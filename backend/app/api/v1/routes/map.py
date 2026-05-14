# File: map.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: GET /api/v1/map/infra — 지도 인프라 점 집계 엔드포인트
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.api.deps import SettingsDep
from backend.app.services import map_service

router = APIRouter(prefix="/map")


@router.get("/infra")
def get_infra_map(
    settings: SettingsDep,
    gu: str | None = Query(default=None, description="서울시 구 이름 필터 (예: 마포구)"),
    cert_id: str | None = Query(default=None, description="자격증 ID — 관련 훈련기관 포함용"),
) -> dict:
    """
    지도 인프라 점 집계.
    - 일자리카페: 서울 열린데이터광장
    - 건강증진센터: 서울 열린데이터광장
    - 훈련기관: Work24 → cert_id → NCS → Kakao 지오코딩
    """
    return map_service.get_infra_points(settings, gu=gu, cert_id=cert_id)
