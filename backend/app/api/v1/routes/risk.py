# File: risk.py
# Last Updated: 2026-06-30
# Content Hash: SHA256:TBD
# Role: 위험군 관련 라우트 — 단계 조회 + 군집별 RAG 근거 검색 (HyDE 포함)
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.core.config import Settings, get_settings
from backend.app.services import risk_stage_service

router = APIRouter()

# 군집 ID → 검색 쿼리 매핑 (GET 레거시용)
_CLUSTER_QUERIES: dict[str, str] = {
    "1": "고립위험청년 사회관계망 예방 연계 지원 사례관리",
    "2": "활동형고립청년 일경험 사례관리 치유 관계형성",
    "3": "활동제한형고립청년 활동 제한 외출 어려움 지원",
    "4": "은둔청년 사회관계 단절 자기관리 어려움 지원",
}


class StageEvidenceBody(BaseModel):
    cluster_id: str
    dimension_scores: dict[str, int] = {}


@router.get("/risk/stages")
def list_risk_stages() -> dict:
    """위험군 단계 메타 조회 스텁. canonical 데이터 연동 전까지 NOT_IMPLEMENTATION."""
    return risk_stage_service.stages_list()


@router.get("/risk/stage-evidence")
def get_stage_evidence(
    cluster_id: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """레거시 GET — 키워드 검색만 수행 (dimension_scores 없음)."""
    from backend.app.services.retrieval_service import search_stage_evidence

    query = _CLUSTER_QUERIES.get(cluster_id, f"고립청년 지원 {cluster_id}단계")
    return search_stage_evidence(stage_id=cluster_id, query_text=query, settings=settings)


@router.post("/risk/stage-evidence")
def post_stage_evidence(
    body: StageEvidenceBody,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    HyDE 기반 군집 분류 근거 검색 + LLM 합성.

    dimension_scores: {"관계망": 88, "활동": 75, ...} (0~100 정수)
    OpenAI 키 없으면 단순 키워드 검색 fallback.
    LLM 합성은 제공 문서 외 정보를 사용하지 않는다 (환각 가드레일).
    """
    from backend.app.services.hyde_evidence_service import hyde_stage_evidence

    return hyde_stage_evidence(
        cluster_id=body.cluster_id,
        dim_scores=body.dimension_scores,
        settings=settings,
    )
