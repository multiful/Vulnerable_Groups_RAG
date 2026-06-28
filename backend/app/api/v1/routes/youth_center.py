# File: youth_center.py
# Last Updated: 2026-06-26
# Content Hash: SHA256:TBD
# Role: GET /api/v1/youth/* — 온통청년 청년정책(F-26)·청년공간(F-27)·청년콘텐츠(F-28)
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.config import Settings, get_settings
from backend.app.services import youth_center_service

router = APIRouter()


@router.get("/youth/policy")
def get_youth_policy(
    lclsf_nm: str | None = None,
    mclsf_nm: str | None = None,
    region: str | None = None,
    keyword: str | None = None,
    page_size: int = 5,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    온통청년 청년정책 조회 (F-26).

    - lclsf_nm: 정책대분류 (일자리|주거|교육|복지문화|참여권리)
    - mclsf_nm: 정책중분류 (취업|재직자|창업|미래역량강화 등)
    - region: 지역명 (예: 서울, 경기)
    - keyword: 검색 키워드
    - page_size: 결과 수 (기본 5, 최대 20)
    """
    page_size = min(max(1, page_size), 20)
    return youth_center_service.get_youth_policy(
        settings=settings,
        lclsf_nm=lclsf_nm,
        mclsf_nm=mclsf_nm,
        region=region,
        keyword=keyword,
        page_size=page_size,
    )


@router.get("/youth/space")
def get_youth_space(
    region: str | None = None,
    page_size: int = 5,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    온통청년 청년공간(센터) 조회 (F-27).

    - region: 지역명 (예: 서울, 경기)
    - page_size: 결과 수 (기본 5, 최대 20)
    """
    page_size = min(max(1, page_size), 20)
    return youth_center_service.get_youth_space(
        settings=settings,
        region=region,
        page_size=page_size,
    )


@router.get("/youth/content")
def get_youth_content(
    category: str | None = None,
    keyword: str | None = None,
    page_size: int = 5,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    온통청년 청년콘텐츠 조회 (F-28). 대분류별로 그룹핑하여 반환.

    - category: 일자리|주거|교육|복지문화|참여권리|전체 (기본 전체)
    - keyword: 검색 키워드
    - page_size: 결과 수 (기본 5, 최대 20)

    응답에 grouped_by_category 필드로 대분류별 콘텐츠를 구분하여 반환합니다.
    """
    page_size = min(max(1, page_size), 20)
    return youth_center_service.get_youth_content(
        settings=settings,
        category=category,
        keyword=keyword,
        page_size=page_size,
    )


@router.get("/youth/categories")
def get_youth_categories() -> dict:
    """
    온통청년 정책대분류 허용값 목록 조회.
    (API코드정보.xlsx 정책대분류 시트 기준)
    """
    return {
        "success": True,
        "data": {
            "categories": youth_center_service.ALLOWED_CATEGORIES,
            "description": "청년정책(F-26) 및 청년콘텐츠(F-28) lclsfNm 필터 허용값",
        },
    }
