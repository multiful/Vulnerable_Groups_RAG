# File: cert_info.py
# Last Updated: 2026-05-15
# Content Hash: SHA256:TBD
# Role: 한국산업인력공단 자격정보 + 시험정보 라우트 + cert_master 통계 + 선수과목 + 지역통계 + 연도별 세션
#
# GET /api/v1/certs/{cert_id}/info          → 자격정보 (응시자격·수수료)
# GET /api/v1/certs/{cert_id}/exam-info     → 시험정보 (시험과목·합격기준)
# GET /api/v1/certs/{cert_id}/full-info     → 자격정보 + 시험정보 합본
# GET /api/v1/certs/{cert_id}/stats         → cert_master 필기/실기 합격률·빈도·난이도
# GET /api/v1/certs/{cert_id}/prerequisites → 선수 자격증 목록 (cert_prerequisite.csv)
# GET /api/v1/certs/{cert_id}/session-rates → 연도별·회별 필기/실기 합격률 (연도별 회별 CSV)
# GET /api/v1/certs/region-stats            → 행정구역별 취득현황 (grade 필터 선택)
# GET /api/v1/certs/major-ncs               → 학과명 → NCS 직무 매핑
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from backend.app.api.deps import SettingsDep
from backend.app.services import cert_info_service

router = APIRouter(prefix="/certs")


@router.get("/region-stats")
async def get_region_stats(grade: Optional[str] = Query(None, description="등급명 (기능사/기사 등)")):
    """행정구역별·연도별·성별 자격증 취득현황. grade 미지정 시 전체 등급 집계."""
    return cert_info_service.get_region_stats(cert_grade=grade)


@router.get("/major-ncs")
async def get_major_ncs(major: str = Query(..., description="학과명 (부분 일치 허용)")):
    """학과명 → NCS 필수 직무 매핑 (한국산업인력공단 학과별 직무정_rows.csv)."""
    return cert_info_service.get_major_ncs(major_name=major)


@router.get("/{cert_id}/stats")
async def get_cert_stats(cert_id: str):
    """cert_master 기반 필기/실기 합격률·시험빈도·난이도 통계 (외부 API 불필요)."""
    return cert_info_service.get_cert_master_stats(cert_id=cert_id)


@router.get("/{cert_id}/prerequisites")
async def get_cert_prerequisites(cert_id: str):
    """cert_prerequisite.csv 기반 선수 자격증 목록."""
    return cert_info_service.get_cert_prerequisites(cert_id=cert_id)


@router.get("/{cert_id}/session-rates")
async def get_session_pass_rates(cert_id: str):
    """연도별·회별·필기/실기 합격률 상세 (한국산업인력공단 연도별 회별 CSV)."""
    return cert_info_service.get_session_pass_rates(cert_id=cert_id)


@router.get("/{cert_id}/info")
async def get_cert_info(cert_id: str, settings: SettingsDep):
    """국가자격 종목별 자격정보 (응시자격·취득방법·수수료)."""
    return cert_info_service.get_cert_item_info(cert_id=cert_id, settings=settings)


@router.get("/{cert_id}/exam-info")
async def get_cert_exam_info(cert_id: str, settings: SettingsDep):
    """국가기술자격 종목별 시험정보 (시험과목·출제기준·합격기준)."""
    return cert_info_service.get_cert_exam_info(cert_id=cert_id, settings=settings)


@router.get("/{cert_id}/full-info")
async def get_cert_full_info(cert_id: str, settings: SettingsDep):
    """자격정보 + 시험정보 합본."""
    return cert_info_service.get_cert_full_info(cert_id=cert_id, settings=settings)
