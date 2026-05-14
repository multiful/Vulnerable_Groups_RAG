# File: cert_info.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 한국산업인력공단 자격정보 + 시험정보 라우트
#
# GET /api/v1/certs/{cert_id}/info      → 자격정보 (응시자격·수수료)
# GET /api/v1/certs/{cert_id}/exam-info → 시험정보 (시험과목·합격기준)
# GET /api/v1/certs/{cert_id}/full-info → 자격정보 + 시험정보 합본
from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.deps import SettingsDep
from backend.app.services import cert_info_service

router = APIRouter(prefix="/certs")


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
