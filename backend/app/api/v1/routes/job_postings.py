# File: job_postings.py
# Last Updated: 2026-07-02
# Content Hash: SHA256:4c7d082bae4455a806d3ed46159c3584c42212cbb73c077b138ddfa5e3701690
# Role: GET /api/v1/job-postings — 자격증×직무 기반 대기업 채용공고 매칭 + LLM 연관성 분석
#
# Saramin API 승인 대기 중 → job_crawling_service (10개 기업 직접 크롤링) 사용
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Query

from backend.app.api.deps import SettingsDep
from backend.app.services import job_crawling_service, llm_cert_relevance_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/job-postings")


@router.get("/crawl-refresh")
async def trigger_crawl_refresh(background_tasks: BackgroundTasks) -> dict:
    """
    10개 기업 채용공고 캐시 강제 갱신 (백그라운드 실행).
    프론트엔드 초기 로딩 시 호출하거나 관리자가 수동 호출.
    """
    background_tasks.add_task(_run_refresh)
    return {"status": "refresh_started", "companies": [k for k, _ in job_crawling_service._CRAWLERS]}


async def _run_refresh() -> None:
    counts = await job_crawling_service.refresh_all_companies()
    logger.info("채용공고 크롤링 완료: %s", counts)


@router.get("/match")
def get_matching_postings(
    settings: SettingsDep,
    cert_name: str = Query(..., description="자격증명 (예: 정보처리기사)"),
    job_domain: str = Query(default="", description="희망 직무 도메인 (예: IT·개발)"),
    risk_stage: int = Query(default=3, ge=1, le=5, description="위험군 단계 (1~5)"),
    limit: int = Query(default=5, ge=1, le=10),
) -> dict:
    """
    자격증 + 희망 직무 기반으로:
    1. LLM 연관성 분석 (난이도, 연관성 설명, 직무 수요)
    2. 캐시된 10개 기업 채용공고 키워드 매칭
    반환.

    난이도 threshold (risk_stage 기반):
      1단계: 80+, 2단계: 70+, 3단계: 60+, 4단계: 40+, 5단계: 20+
    """
    DIFFICULTY_THRESHOLD = {1: 80, 2: 70, 3: 60, 4: 40, 5: 20}
    threshold = DIFFICULTY_THRESHOLD.get(risk_stage, 60)

    # LLM 연관성 분석
    relevance = llm_cert_relevance_service.get_cert_relevance(
        cert_name=cert_name,
        job_domain=job_domain,
        settings=settings,
    )

    # 난이도 threshold 체크 (추천 여부 판단용 메타)
    meets_threshold = relevance["difficulty_score"] >= threshold

    # 채용공고 매칭
    job_postings = job_crawling_service.get_matching_jobs(
        cert_name=cert_name,
        job_domain=job_domain,
        limit=limit,
    )

    return {
        "cert_name": cert_name,
        "job_domain": job_domain,
        "risk_stage": risk_stage,
        "difficulty_threshold": threshold,
        "difficulty_score": relevance["difficulty_score"],
        "meets_threshold": meets_threshold,
        "pass_rate": None,  # Q-Net 연동 시 채움 (현재 reserved)
        "domain_relevance_delta": relevance["relevance_delta_pct"],
        "relevance_summary": relevance["relevance_summary"],
        "job_demand_level": relevance["job_demand_level"],
        "relevance_from_llm": relevance["from_llm"],
        "difficulty_grounded": relevance.get("difficulty_grounded", False),
        "job_postings": job_postings,
        "posting_count": len(job_postings),
        "data_source": "crawled_cache",
    }


@router.get("/cache-status")
def get_cache_status() -> dict:
    """크롤링 캐시 상태 확인 (회사별 건수 + 캐시 TTL 잔여 여부)."""
    import time
    from pathlib import Path

    CACHE_DIR = Path("data/cache/job_postings")
    status: dict[str, dict] = {}
    for key, _ in job_crawling_service._CRAWLERS:
        p = CACHE_DIR / f"{key}.json"
        if p.exists():
            try:
                import json
                data = json.loads(p.read_text(encoding="utf-8"))
                age_sec = int(time.time() - data.get("cached_at", 0))
                status[key] = {
                    "count": len(data.get("postings", [])),
                    "age_seconds": age_sec,
                    "is_fresh": age_sec < job_crawling_service.CACHE_TTL,
                }
            except Exception:
                status[key] = {"count": 0, "age_seconds": -1, "is_fresh": False}
        else:
            status[key] = {"count": 0, "age_seconds": -1, "is_fresh": False}

    return {"companies": status, "ttl_seconds": job_crawling_service.CACHE_TTL}
