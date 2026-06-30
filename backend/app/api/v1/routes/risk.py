# File: risk.py
# Last Updated: 2026-06-30
# Content Hash: SHA256:TBD
# Role: 위험군 관련 라우트 — 단계 조회 + 군집별 RAG 근거 검색
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.config import Settings, get_settings
from backend.app.services import risk_stage_service

router = APIRouter()

# 군집 ID → 검색 쿼리 매핑
_CLUSTER_QUERIES: dict[str, str] = {
    "1": "고립위험청년 사회관계망 예방 연계 지원 사례관리",
    "2": "활동형고립청년 일경험 사례관리 치유 관계형성",
    "3": "활동제한형고립청년 활동 제한 외출 어려움 지원",
    "4": "은둔청년 사회관계 단절 자기관리 어려움 지원",
}


@router.get("/risk/stages")
def list_risk_stages() -> dict:
    """위험군 단계 메타 조회 스텁. canonical 데이터 연동 전까지 NOT_IMPLEMENTATION."""
    return risk_stage_service.stages_list()


@router.get("/risk/stage-evidence")
def get_stage_evidence(
    cluster_id: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    군집 분류 근거 문서 검색 (RAG).

    chunks.jsonl에서 고립·은둔 청년 관련 연구 문서 스니펫을 반환한다.
    분류 결과 화면의 '연구 근거' 섹션에 표시하기 위한 endpoint.

    - cluster_id: '1'~'4' (고립위험청년~은둔청년)
    """
    from backend.app.services.retrieval_service import search_stage_evidence

    query = _CLUSTER_QUERIES.get(cluster_id, f"고립청년 지원 {cluster_id}단계")
    return search_stage_evidence(stage_id=cluster_id, query_text=query, settings=settings)
