# File: admin.py
# Last Updated: 2026-05-10
# Content Hash: SHA256:TBD
# Role: POST /admin/* 스켈 (canonicalize, candidates 등) + cache 무효화
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.app.schemas.envelope import ok_envelope
from backend.app.services import metadata_service, recommendation_service

router = APIRouter()


@router.post("/admin/canonicalize")
def post_canonicalize(body: dict[str, Any] | None = None) -> dict:
    return metadata_service.not_implemented("canonicalize", body or {})


@router.post("/admin/candidates/rebuild")
def post_candidates_rebuild(body: dict[str, Any] | None = None) -> dict:
    return metadata_service.not_implemented("candidates_rebuild", body or {})


@router.get("/admin/validation")
def get_validation() -> dict:
    return metadata_service.not_implemented("validation", {})


@router.post("/admin/cache/clear")
def post_cache_clear() -> dict:
    """lru_cache 기반 로더를 모두 무효화한다.
    빌드 파이프라인이 데이터 파일을 교체한 뒤 호출해 캐시를 갱신한다.
    프로덕션에서는 내부망 또는 토큰 인증을 추가할 것.
    """
    recommendation_service._invalidate_caches()
    return ok_envelope({"cleared": True})
