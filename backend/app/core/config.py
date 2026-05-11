# File: config.py
# Last Updated: 2026-05-12
# Content Hash: SHA256:TBD
# Role: Pydantic Settings — CORS, Supabase, 임베딩, RAG 경로, YouTube API
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- HTTP ---
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="쉼표로 구분. Vite 기본 포트 + Vercel 배포 도메인 추가",
    )
    rag_top_k: int = Field(default=5, ge=1, le=50)

    # --- Supabase (pgvector). 키는 배포 환경·팀 계정에서 주입 ---
    supabase_url: str | None = None
    supabase_service_key: str | None = Field(
        default=None,
        description="서버 인제스트·검색용 service_role (클라이언트에 노출 금지)",
    )
    supabase_table_name: str = "documents"
    supabase_match_rpc: str = "match_documents"

    # --- 임베딩 (LangChain 래퍼) ---
    embedding_provider: Literal["openai", "huggingface"] = "openai"
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- 오프라인 산출물 경로 (저장소 루트 기준 상대 경로 권장) ---
    chunks_jsonl_relative: str = "data/index_ready/chunks/chunks.jsonl"

    # --- YouTube Data API v3 (F-11 관련 동영상 추천) ---
    youtube_api_key: str | None = Field(
        default=None,
        description="YouTube Data API v3 키. 백엔드에서만 사용. 클라이언트 노출 금지.",
    )
    youtube_video_cache_table: str = "cert_video_cache"
    youtube_video_cache_ttl_days: int = 30
    youtube_video_max_results: int = 5
    youtube_query_version: int = 2  # v2: 숏츠 제외 + medium duration 필터

    @field_validator("supabase_url", "openai_api_key", "youtube_api_key", mode="before")
    @classmethod
    def strip_blank(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
