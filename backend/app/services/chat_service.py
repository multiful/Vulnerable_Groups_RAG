# File: chat_service.py
# Last Updated: 2026-05-25
# Content Hash: SHA256:TBD
# Role: 청년 진로 상담 에이전트 — RAG 기반 Q&A (GPT-4o-mini + evidence retrieval)
from __future__ import annotations

import logging
import time
from typing import Any

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_MAX_HISTORY = 10

# 동일 cert + 질문 조합의 evidence 재조회 방지 (embedding 비용 절감)
_EVIDENCE_TTL = 3600
_evidence_cache: dict[str, tuple[float, list[str]]] = {}

_STAGE_LABELS: dict[str, str] = {
    "1": "1단계 (취업 안정권)",
    "2": "2단계 (준비 활성)",
    "3": "3단계 (준비 정체)",
    "4": "4단계 (고위험군)",
    "5": "5단계 (최고위험군)",
}

_BASE_SYSTEM_PROMPT = """당신은 DIDIM 서비스의 청년 진로 상담사입니다.
청년 위험군(1~5단계)에 맞는 자격증 추천, 로드맵, 취업 준비, 정부 지원 정책을 친절하고 실질적으로 안내합니다.

## 위험군 단계
- 1단계 (취업 안정권): 전문 자격증 심화 — 기사·기술사·전문 자격 위주
- 2~3단계 (중간 위험군): 역량 강화 — 기사·산업기사 + GTQ·컴퓨터활용능력 1급 등
- 4~5단계 (고위험군): 작은 성취 우선 — 기능사·산업기사 + 컴퓨터활용능력 2급 등

## 정부 지원 정책 (알고 있는 내용)
### 국민내일배움카드
- 대상: 실업자, 재직자(임금근로자), 자영업자
- 지원: 훈련비의 45~85% 지원 (연간 최대 500만원 한도)
- 신청: 고용24(work24.go.kr) 또는 가까운 고용센터
- 제한: 현직 공무원·만 75세 이상·대규모기업 사업주 등 일부 제외
- 방법: 고용24 → 훈련/국민내일배움카드 → 신청

### 국민취업지원제도 (구직촉진수당)
- 대상: 취업경험이 부족한 청년(18~34세) 및 저소득층
- 지원: 월 50만원 × 최대 6개월 + 취업지원 서비스
- 신청: 고용24 또는 고용센터

### 청년도약계좌 / 청년희망적금
- 청년 자산 형성을 위한 금융 지원 (금융위원회 관할)

### 훈련과정 찾기
- HRD-Net (hrd.go.kr): 국민내일배움카드 훈련과정 검색
- 고용24 (work24.go.kr): 카드 신청 및 훈련 신청

## 답변 원칙
- 확인되지 않은 시험 일정·날짜·링크를 지어내지 않는다.
- 자격증 합격률·난이도는 근거가 있을 때만 언급한다.
- 항상 실현 가능한 단계별 행동을 제안한다.
- 위험군이 높을수록(4~5단계) 부담이 낮은 것을 먼저 권장한다.
- 답변이 길어지면 3~4문장으로 핵심만 먼저 말하고, 필요 시 추가 설명을 제안한다.
"""


def _retrieve_evidence(cert_name: str, user_question: str, settings: Settings) -> list[str]:
    """cert_name 기반으로 관련 evidence snippet을 가져온다."""
    _ev_key = f"{cert_name}|{user_question[:80]}"
    _ev_entry = _evidence_cache.get(_ev_key)
    if _ev_entry is not None and (time.monotonic() - _ev_entry[0]) < _EVIDENCE_TTL:
        return _ev_entry[1]

    try:
        from backend.app.services.retrieval_service import search_evidence

        result = search_evidence(
            {"cert_name": cert_name, "query_text": user_question},
            settings,
        )
        if not result.get("success"):
            _evidence_cache[_ev_key] = (time.monotonic(), [])
            return []
        rows = result.get("data", {}).get("evidence", [])
        snippets: list[str] = []
        seen: set[str] = set()
        for row in rows[:5]:
            snippet = (row.get("snippet") or "").strip()
            sec = (row.get("section_path") or [""])[0]
            if snippet and snippet not in seen:
                seen.add(snippet)
                label = f"[{sec}] " if sec else ""
                snippets.append(f"{label}{snippet}")
        _evidence_cache[_ev_key] = (time.monotonic(), snippets)
        return snippets
    except Exception as e:
        logger.debug("chat evidence retrieval failed: %s", e)
        return []


def _build_system_prompt(context: dict[str, Any], evidence_snippets: list[str]) -> str:
    parts = [_BASE_SYSTEM_PROMPT.strip()]

    stage_id = context.get("stage_id")
    if stage_id:
        label = _STAGE_LABELS.get(str(stage_id), f"{stage_id}단계")
        parts.append(f"\n[현재 사용자 위험군]: {label}")

    domain_name = context.get("domain_name") or context.get("domain_id")
    if domain_name:
        parts.append(f"[관심 도메인]: {domain_name}")

    job_name = context.get("job_name") or context.get("job_id")
    if job_name:
        parts.append(f"[관심 직무]: {job_name}")

    cert_id = context.get("cert_id")
    cert_name = context.get("cert_name")
    if cert_name:
        parts.append(f"[현재 자격증]: {cert_name} (cert_id={cert_id or '미지정'})")
    elif cert_id:
        parts.append(f"[현재 자격증 cert_id]: {cert_id}")

    if evidence_snippets:
        parts.append("\n[공식 문서 근거 — 답변 시 활용 가능]")
        for i, s in enumerate(evidence_snippets, 1):
            parts.append(f"근거{i}: {s}")
        parts.append("(위 근거는 공식 문서에서 추출된 내용입니다. 답변에 활용하되 원문 그대로 인용하지 않아도 됩니다.)")

    return "\n".join(parts)


def chat(body: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """POST /api/v1/chat 핸들러.

    body 예시:
      {
        "messages": [{"role": "user", "content": "..."}],
        "context": {
          "stage_id": "3",
          "cert_id": "1320",
          "cert_name": "정보처리기사",
          "domain_name": "데이터/AI",
          "job_name": "데이터 분석"
        }
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

    messages = messages[-_MAX_HISTORY:]

    # RAG: cert_name이 있으면 마지막 user 질문 기반으로 evidence 검색
    evidence_snippets: list[str] = []
    cert_name = context.get("cert_name")
    if cert_name:
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
        )
        if last_user:
            evidence_snippets = _retrieve_evidence(cert_name, last_user, settings)

    system_prompt = _build_system_prompt(context, evidence_snippets)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                *messages,
            ],
            max_tokens=600,
            temperature=0.5,
        )
        reply = (response.choices[0].message.content or "").strip()
        return ok_envelope({
            "reply": reply,
            "role": "assistant",
            "used_evidence": len(evidence_snippets) > 0,
        })
    except Exception as exc:
        return err_envelope(
            "UPSTREAM_ERROR",
            f"OpenAI 호출 중 오류가 발생했습니다: {exc}",
            {"exc_type": type(exc).__name__},
        )
