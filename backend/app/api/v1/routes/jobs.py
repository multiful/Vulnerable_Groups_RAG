# File: jobs.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: GET /api/v1/jobs/hiring, GET /api/v1/jobs/detail
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.api.deps import SettingsDep
from backend.app.services import jobs_service
from backend.app.services import cert_lookup_service

router = APIRouter(prefix="/jobs")


@router.get("/hiring")
def get_hiring_jobs(
    settings: SettingsDep,
    occupation: str | None = Query(default=None, description="직종코드 (예: 171)"),
    cert_lic: str | None = Query(default=None, description="자격면허 코드"),
    region: str | None = Query(default=None, description="지역명 (예: 서울)"),
    keyword: str | None = Query(default=None, description="키워드 검색"),
    education: str | None = Query(default=None, description="학력 코드 (예: 05 = 대졸 4년)"),
    display: int = Query(default=20, ge=1, le=100),
) -> dict:
    """WorkNet 실시간 채용정보 조회."""
    return jobs_service.get_hiring_jobs(
        settings,
        occupation=occupation,
        cert_lic=cert_lic,
        region=region,
        keyword=keyword,
        education=education,
        display=display,
    )


@router.get("/hiring/by-cert/{cert_id}")
def get_hiring_by_cert(
    cert_id: str,
    settings: SettingsDep,
    region: str | None = Query(default=None, description="지역명 (예: 서울)"),
    display: int = Query(default=20, ge=1, le=100),
) -> dict:
    """
    cert_id 기반 WorkNet 채용정보 조회.
    cert_id → cert_name + NCS → WorkNet 직종코드 자동 파생 (canonical 데이터 체인).
    직접 문자열 매칭 없이 구조화 데이터만 사용.
    """
    return jobs_service.get_hiring_by_cert_id(cert_id, settings, region=region, display=display)


@router.get("/cert-summary/{cert_id}")
def get_cert_summary(cert_id: str) -> dict:
    """
    cert_id 종합 조회 — cert 정보 + NCS 분류 + 관련 직무 + WorkNet/Work24 검색 파라미터.
    프론트엔드가 cert 관련 모든 데이터를 한 번에 가져올 때 사용.
    """
    from backend.app.schemas.envelope import ok_envelope, err_envelope
    summary = cert_lookup_service.get_cert_summary(cert_id)
    if not summary.get("found"):
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")
    return ok_envelope(summary)


@router.get("/detail")
def get_job_detail(
    job_name: str | None = Query(default=None, description="직업명 (부분 일치)"),
    job_code: str | None = Query(default=None, description="직업 코드"),
) -> dict:
    """고용24 직업정보 상세 조회 (임금, 만족도, 전망, 근무내용 등)."""
    return jobs_service.get_job_detail(job_name=job_name, job_code=job_code)
