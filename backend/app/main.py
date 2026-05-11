# File: main.py
# Last Updated: 2026-05-11
# Content Hash: SHA256:TBD
# Role: FastAPI application entrypoint
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import get_settings

load_dotenv()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 모든 lru_cache 파일 로더를 병렬로 워밍업.
    첫 번째 요청 지연(수백ms~수초)을 제거하기 위함."""
    from backend.app.services import recommendation_service as rs
    from backend.app.services import dag_service as ds
    from backend.app.services import llm_roadmap_service as ls
    from backend.app.services import retrieval_service as ret

    loaders = [
        rs._load_candidates,
        rs._load_pass_rate_map,
        rs._load_risk_stages,
        rs._load_roadmap_stages,
        rs._load_risk_to_roadmap,
        rs._load_domain_map,
        rs._load_major_to_domain_map,
        rs._load_job_to_domain_map,
        rs._load_cert_to_roadmap_map,
        rs._load_cert_name_map,
        rs._load_cert_graph,
        ds._load_relations,
        ds._load_cert_info,
        ls._load_candidates,
        ls._load_domain_names,
        ls._load_risk_stages,
        ret._load_candidates,
        ret._load_cert_names,
        ret._load_private_catalog,
        ret._load_national_catalog,
    ]
    try:
        await asyncio.gather(*(asyncio.to_thread(fn) for fn in loaders))
        logger.info("캐시 프리로드 완료 (%d loaders)", len(loaders))
    except Exception as exc:
        logger.warning("캐시 프리로드 일부 실패 (계속 진행): %s", exc)
    yield


app = FastAPI(
    title="vulnerable_groups_RAG API",
    description="위험군 맞춤 자격증·로드맵 추천 백엔드",
    version="0.1.0",
    lifespan=lifespan,
)
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(api_router)
