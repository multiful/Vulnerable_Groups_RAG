# File: ncs.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: NCS 능력단위별 자격 종목 조회 라우트 (항목 10)
#
# GET /api/v1/ncs/certs    → NCS 코드/대직무코드/키워드로 연관 자격증 조회
# GET /api/v1/ncs/list     → NCS 코드 목록
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from backend.app.services import ncs_service

router = APIRouter(prefix="/ncs")


@router.get("/certs")
async def get_certs_by_ncs(
    ncs_id:     Optional[str] = Query(default=None, description="NCS 소직무 ID (예: ncs_0001)"),
    major_code: Optional[str] = Query(default=None, description="NCS 대직무코드 (예: 20)"),
    keyword:    Optional[str] = Query(default=None, description="NCS 분류명 키워드 검색"),
    page:       int           = Query(default=1, ge=1),
    page_size:  int           = Query(default=30, ge=1, le=100),
) -> dict:
    """NCS 코드 또는 키워드로 연관 자격증 목록 조회."""
    return ncs_service.get_certs_by_ncs(
        ncs_id=ncs_id,
        major_code=major_code,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.get("/list")
async def list_ncs(
    keyword: Optional[str] = Query(default=None, description="NCS 분류명 검색어"),
) -> dict:
    """NCS 코드 목록 조회 (드롭다운·검색용)."""
    return ncs_service.get_ncs_list(keyword=keyword)
