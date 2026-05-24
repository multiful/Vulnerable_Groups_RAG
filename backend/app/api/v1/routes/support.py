# File: support.py
# Last Updated: 2026-05-25
# Content Hash: SHA256:TBD
# Role: GET /api/v1/support/bundle — 취업지원 자원 번들 조회 (F-17)
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.config import Settings, get_settings
from backend.app.services import support_bundle_service

router = APIRouter()


@router.get("/support/bundle")
def get_support_bundle(
    risk_stage_id: str,
    domain_id: str | None = None,
    domain_name: str | None = None,
    job_ids: str | None = None,
    job_names: str | None = None,
    cert_ids: str | None = None,
    region: str | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    위험군 단계 × 도메인/직무 기반 취업지원 자원 번들.
    - 1단계: 채용정보 (partial)
    - 2~3단계: 채용정보 + 훈련과정 (standard)
    - 4~5단계: 채용정보 + 훈련과정 + 일자리카페 + 과정평가형 (full)
    """
    return support_bundle_service.get_support_bundle(
        settings=settings,
        risk_stage_id=risk_stage_id,
        domain_id=domain_id,
        domain_name=domain_name,
        job_ids=job_ids.split(",") if job_ids else None,
        job_names=job_names.split(",") if job_names else None,
        cert_ids=cert_ids.split(",") if cert_ids else None,
        region=region,
    )
