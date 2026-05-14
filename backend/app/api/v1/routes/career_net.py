# File: career_net.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 커리어넷 직업정보 + 학과정보 API 라우트
#
# GET /api/v1/career-net/jobs         → 직업 목록 (검색 가능)
# GET /api/v1/career-net/jobs/{seq}   → 직업 상세
# GET /api/v1/career-net/majors       → 학과 목록 (검색 가능)
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.api.deps import SettingsDep
from backend.app.services import career_net_service

router = APIRouter(prefix="/career-net")


@router.get("/jobs")
async def list_jobs(
    settings: SettingsDep,
    q: str | None = Query(default=None, description="직업명 검색어"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """커리어넷 직업정보 목록. q 파라미터로 직업명 검색 가능."""
    return career_net_service.get_job_list(q=q, page=page, page_size=page_size, settings=settings)


@router.get("/jobs/{job_seq}")
async def get_job(job_seq: str, settings: SettingsDep):
    """커리어넷 직업 상세 정보."""
    return career_net_service.get_job_detail(job_seq=job_seq, settings=settings)


@router.get("/majors")
async def list_majors(
    settings: SettingsDep,
    q: str | None = Query(default=None, description="학과명 검색어"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """커리어넷 학과정보 목록. q 파라미터로 학과명 검색 가능."""
    return career_net_service.get_major_list(q=q, page=page, page_size=page_size, settings=settings)
