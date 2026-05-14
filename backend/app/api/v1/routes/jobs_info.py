# File: jobs_info.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: GET /api/v1/jobs/cert-jobs/{cert_name}, GET /api/v1/jobs/info/{job_name}
#       자격증-직업 연결 조회 및 고용24 직업 상세 조회 엔드포인트
from __future__ import annotations

from fastapi import APIRouter, Path, Query

from backend.app.services import goms_service

router = APIRouter(prefix="/jobs")


@router.get(
    "/cert-jobs/{cert_name}",
    summary="자격증 연관 직업 조회",
    description=(
        "자격증 이름으로 연관 직업명 목록을 반환한다. "
        "job_raw_merged_rows.csv(자격증-직무 연결)와 "
        "ncs_mapping_rows.csv(NCS 자격증 매핑) 두 소스를 합산한다."
    ),
)
def get_cert_jobs(
    cert_name: str = Path(description="자격증명 (예: 정보처리기사)"),
) -> dict:
    """자격증 → 연관 직업명 목록 (GOMS/NCS 기반)."""
    return goms_service.get_cert_jobs_envelope(cert_name)


@router.get(
    "/info/{job_name}",
    summary="직업 상세 정보 조회",
    description=(
        "직업명 부분 일치로 고용24 직업정보상세 요약 CSV에서 "
        "임금, 직업만족도, 일자리전망, 하는일, 직업안내동영상 URL 등을 반환한다."
    ),
)
def get_job_info(
    job_name: str = Path(description="직업명 (부분 일치, 예: 소프트웨어개발자)"),
) -> dict:
    """고용24 직업 상세 정보 조회."""
    return goms_service.get_job_info_envelope(job_name)


@router.get(
    "/major-certs/{major_name}",
    summary="전공 추천 자격증 조회",
    description=(
        "전공명으로 추천 자격증 목록을 반환한다. "
        "job_raw_merged_rows.csv와 ncs_mapping_rows.csv 두 소스를 합산한다."
    ),
)
def get_major_certs(
    major_name: str = Path(description="전공명 (예: 컴퓨터공학과)"),
) -> dict:
    """전공 → 추천 자격증 목록 (GOMS/NCS 기반)."""
    return goms_service.get_major_certs_envelope(major_name)
