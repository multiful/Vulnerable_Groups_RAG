# File: map.py
# Last Updated: 2026-05-19
# Content Hash: SHA256:TBD
# Role: GET /api/v1/map/infra, /map/local-search — 지도 인프라 점 집계 엔드포인트
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
    - 일자리카페: 서울 열린데이터광장 (실패 시 Kakao fallback)
    - 건강증진센터: 서울 열린데이터광장 (실패 시 Kakao fallback)
    - 훈련기관: Work24 → cert_id → NCS → Kakao 지오코딩
    """
    return map_service.get_infra_points(settings, gu=gu, cert_id=cert_id)


@router.get("/local-search")
def kakao_local_search(
    settings: SettingsDep,
    q: str = Query(description="검색어 (예: 일자리카페, 고용복지플러스센터, 정신건강증진센터)"),
    rect: str | None = Query(default=None, description="직사각형 범위 x1,y1,x2,y2 (기본값: 서울 전체)"),
    size: int = Query(default=15, ge=1, le=15),
    page: int = Query(default=1, ge=1, le=45),
) -> dict:
    """
    Kakao 키워드 로컬 검색.
    서울시 API 미가용 시 대체 장소 검색용.
    """
    return map_service.get_kakao_local_search(q, settings, rect=rect, size=size, page=page)
