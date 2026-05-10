# File: recommendation.py
# Last Updated: 2026-05-07
# Content Hash: SHA256:TBD
# Role: POST /api/v1/recommendations, /llm, /evidence, /related
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from backend.app.api.deps import SettingsDep
from backend.app.services import recommendation_service, llm_roadmap_service, dag_service

router = APIRouter()


@router.post("/recommendations")
def post_recommendations(body: dict[str, Any] | None = None) -> dict:
    return recommendation_service.recommendations(body or {})


@router.post("/recommendations/llm")
def post_recommendations_llm(
    body: dict[str, Any] | None,
    settings: SettingsDep,
) -> dict:
    return llm_roadmap_service.llm_recommendations(body or {}, settings)


@router.post("/recommendations/evidence")
def post_recommendations_evidence(
    body: dict[str, Any] | None,
    settings: SettingsDep,
) -> dict:
    return recommendation_service.recommendations_evidence(body or {}, settings)


@router.get("/recommendations/related")
def get_related_certs(cert_id: str = Query(..., description="cert_id")) -> dict:
    """DAG 기반 선행/후행 자격증 조회."""
    return dag_service.get_related_certs(cert_id)
