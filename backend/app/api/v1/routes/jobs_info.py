# File: jobs_info.py
# Last Updated: 2026-05-19
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
        "자격증 이름으로 연관 직업 정보를 반환한다. "
        "canonical_roles(cert_job_mapping 기반 구조화 직무), "
        "jobs(worknet 실제 직업명), jobs_detail(점수·급여), "
        "related_majors(연관 전공) 를 모두 포함한다."
    ),
)
def get_cert_jobs(
    cert_name: str = Path(description="자격증명 (예: 정보처리기사)"),
    limit: int = Query(default=30, ge=0, le=150, description="직업 목록 최대 건수 (0=무제한)"),
) -> dict:
    """자격증 → 캐노니컬 직무 역할 + 실제 직업명 + 직업 상세 + 연관 전공."""
    return goms_service.get_cert_jobs_envelope(cert_name, limit=limit)


@router.get(
    "/info/{job_name}",
    summary="직업 상세 정보 조회",
    description=(
        "직업명 부분 일치로 고용24 직업정보상세 요약 CSV에서 "
        "임금, 직업만족도, 일자리전망, 하는일, 직업안내동영상 URL, "
        "직무구분, 6개 점수를 반환한다."
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


@router.get(
    "/job-roles",
    summary="전체 직무 역할 목록 조회",
    description="job_master에 정의된 142개 캐노니컬 직무 역할 목록을 반환한다.",
)
def get_job_roles(
    top_group: str | None = Query(default=None, description="상위 그룹 필터 (예: IT/데이터)"),
) -> dict:
    """캐노니컬 직무 역할 전체 목록."""
    from backend.app.schemas.envelope import ok_envelope
    master = goms_service._load_job_master()
    roles_full = [
        {"job_role_id": jid, **info}
        for jid, info in master.items()
    ]
    if top_group:
        roles_full = [r for r in roles_full if top_group in r.get("job_top_group_name", "")]
    return ok_envelope({
        "roles": roles_full,
        "total": len(roles_full),
    })


@router.get(
    "/cert-jobs-by-id/{cert_id}",
    summary="cert_id로 연관 직업 조회",
    description="cert_id로 자격증명을 찾아 연관 직업 전체 정보를 반환한다.",
)
def get_cert_jobs_by_id(
    cert_id: str = Path(description="자격증 ID (예: cert_0135)"),
) -> dict:
    """cert_id → cert_name 변환 후 연관 직업 조회."""
    from backend.app.schemas.envelope import err_envelope
    id_to_name = {v: k for k, v in goms_service._load_cert_name_to_id().items()}
    cert_name = id_to_name.get(cert_id)
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")
    return goms_service.get_cert_jobs_envelope(cert_name)
