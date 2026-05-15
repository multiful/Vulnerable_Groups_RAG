# File: chat_service.py
# Last Updated: 2026-05-15
# Content Hash: SHA256:TBD
# Role: 청년 진로 상담 에이전트 — 대화 기반 Q&A (GPT-4o-mini)
from __future__ import annotations

from typing import Any

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

_MAX_HISTORY = 10

_STAGE_LABELS: dict[str, str] = {
    "1": "관심군 (1단계)",
    "2": "고립위험군 (2단계)",
    "3": "고립군 (3단계)",
    "4": "은둔위험군 (4단계)",
    "5": "은둔군 (5단계)",
}

_BASE_SYSTEM_PROMPT = """당신은 DIDIM 서비스의 청년 진로 상담사입니다.
청년 위험군(1~5단계), 자격증 추천, 로드맵, 취업 준비를 친절하고 실질적으로 도와줍니다.

위험군 단계 정의:
- 1단계 (관심군): 취업 안정권에서 관심이 필요한 상태
- 2단계 (고립위험군): 사회적 고립 위험이 있는 상태
- 3단계 (고립군): 사회적 고립 상태
- 4단계 (은둔위험군): 은둔 위험이 있는 상태
- 5단계 (은둔군): 취업을 원해도 하기 어려운 가장 높은 위험 상태

답변 원칙:
- 확인되지 않은 시험 일정, 링크, 날짜는 지어내지 않는다.
- 근거 없이 자격증 취득 난이도나 합격률을 단정하지 않는다.
- 항상 실현 가능한 단계별 행동을 제시한다.
"""


def _build_system_prompt(context: dict[str, Any]) -> str:
    parts = [_BASE_SYSTEM_PROMPT.strip()]

    stage_id = context.get("stage_id")
    if stage_id:
        label = _STAGE_LABELS.get(str(stage_id), f"{stage_id}단계")
        parts.append(f"\n[현재 사용자 위험군]: {label}")

    domain_id = context.get("domain_id")
    if domain_id:
        parts.append(f"[관심 도메인]: {domain_id}")

    cert_id = context.get("cert_id")
    cert_name = context.get("cert_name")
    if cert_name:
        parts.append(f"[현재 자격증]: {cert_name} (cert_id={cert_id or '미지정'})")
    elif cert_id:
        parts.append(f"[현재 자격증 cert_id]: {cert_id}")

    return "\n".join(parts)


def chat(body: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """POST /api/v1/chat 핸들러.

    body 예시:
      {
        "messages": [{"role": "user", "content": "..."}],
        "context": {"stage_id": "3", "cert_id": "1320", "cert_name": "정보처리기사"}
      }
    """
    if not settings.openai_api_key:
        return err_envelope(
            "NOT_CONFIGURED",
            "OpenAI API 키가 설정되지 않아 상담 기능을 사용할 수 없습니다.",
            {"field": "openai_api_key"},
        )

    messages_raw: list[dict[str, str]] = body.get("messages") or []
    context: dict[str, Any] = body.get("context") or {}

    # 유효한 메시지만 필터 (role / content 필수)
    messages = [
        m for m in messages_raw
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")
    ]

    if not messages:
        return err_envelope(
            "MISSING_REQUIRED_FIELD",
            "messages 배열에 유효한 메시지가 없습니다.",
            {"field": "messages"},
        )

    # 대화 히스토리 최대 10개 (오래된 것 truncate)
    messages = messages[-_MAX_HISTORY:]

    system_prompt = _build_system_prompt(context)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                *messages,
            ],
            max_tokens=500,
            temperature=0.6,
        )
        reply = (response.choices[0].message.content or "").strip()
        return ok_envelope({"reply": reply, "role": "assistant"})
    except Exception as exc:
        return err_envelope(
            "UPSTREAM_ERROR",
            f"OpenAI 호출 중 오류가 발생했습니다: {exc}",
            {"exc_type": type(exc).__name__},
        )
