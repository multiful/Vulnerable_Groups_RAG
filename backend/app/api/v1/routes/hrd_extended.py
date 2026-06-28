# File: hrd_extended.py
# Last Updated: 2026-06-26
# Content Hash: SHA256:TBD
# Role: GET /api/v1/training/workstudy, /consortium, /jobseeker-program
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.api.deps import SettingsDep
from backend.app.services import hrd_extended_service

router = APIRouter(prefix="/training")


@router.get("/workstudy")
def get_workstudy_courses(
    settings: SettingsDep,
    region: str | None = Query(default=None, description="지역명 (예: 서울, 경기)"),
    ncs_category: str | None = Query(default=None, description="NCS 1차 분류명 (예: 정보통신)"),
    course_name: str | None = Query(default=None, description="훈련과정명 검색어"),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """일학습병행 훈련과정 목록 조회 (F-29). Work24 313L01 기반."""
    return hrd_extended_service.get_workstudy_courses(
        settings,
        region=region,
        ncs_category=ncs_category,
        course_name=course_name,
        page_size=page_size,
    )


@router.get("/consortium")
def get_consortium_courses(
    settings: SettingsDep,
    region: str | None = Query(default=None, description="지역명 (예: 서울, 경기)"),
    ncs_category: str | None = Query(default=None, description="NCS 1차 분류명 (예: 정보통신)"),
    course_name: str | None = Query(default=None, description="훈련과정명 검색어"),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """국가인적자원개발 컨소시엄 훈련과정 목록 조회 (F-30). Work24 312L01 기반."""
    return hrd_extended_service.get_consortium_courses(
        settings,
        region=region,
        ncs_category=ncs_category,
        course_name=course_name,
        page_size=page_size,
    )


@router.get("/jobseeker-program")
def get_jobseeker_programs(
    settings: SettingsDep,
    region: str | None = Query(default=None, description="지역명 (예: 서울, 경기)"),
    keyword: str | None = Query(default=None, description="검색어"),
    page_size: int = Query(default=10, ge=1, le=50),
) -> dict:
    """구직자취업역량 강화프로그램 조회 (F-31). API 키 발급 완료, 엔드포인트 승인 대기 중."""
    return hrd_extended_service.get_jobseeker_programs(
        settings,
        region=region,
        keyword=keyword,
        page_size=page_size,
    )
