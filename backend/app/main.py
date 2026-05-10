# File: main.py
# Last Updated: 2026-04-03
# Content Hash: SHA256:TBD
# Role: FastAPI application entrypoint
from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import get_settings

load_dotenv()

app = FastAPI(
    title="vulnerable_groups_RAG API",
    description="위험군 맞춤 자격증·로드맵 추천 백엔드",
    version="0.1.0",
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
