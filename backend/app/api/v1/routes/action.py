# File: action.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: GET /api/v1/actions/today — 오늘의 한 가지 행동 추천
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.services import action_service

router = APIRouter(prefix="/actions")


@router.get("/today")
def get_today_action(
    risk_stage_id: str | None = Query(default=None, description="위험군 단계 ID (예: risk_0003)"),
    cert_ids: str | None = Query(default=None, description="추천 자격증 ID 목록 (쉼표 구분, 예: cert_001,cert_002)"),
    region: str | None = Query(default=None, description="지역명 (예: 서울)"),
) -> dict:
    """
    오늘 할 수 있는 작은 행동 하나를 추천합니다.
    위험군 단계에 맞는 실행 가능한 행동과 CTA를 반환합니다.
    """
    cert_id_list: list[str] = []
    if cert_ids:
        cert_id_list = [c.strip() for c in cert_ids.split(",") if c.strip()]

    return action_service.get_today_action(
        risk_stage_id=risk_stage_id,
        cert_ids=cert_id_list or None,
        region=region,
    )
