# File: chat.py
# Last Updated: 2026-05-15
# Content Hash: SHA256:TBD
# Role: POST /api/v1/chat — 청년 진로 상담 에이전트 엔드포인트
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.app.api.deps import SettingsDep
from backend.app.services import chat_service

router = APIRouter()


@router.post("/chat")
def post_chat(body: dict[str, Any] | None, settings: SettingsDep) -> dict:
    return chat_service.chat(body or {}, settings)
