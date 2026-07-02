# File: chat_service.py
# Last Updated: 2026-07-02
# Content Hash: SHA256:125fbcbb2847a551d9d4d7eeae0549e37f34302f0061696872b7f78a9ec15ab0
# Role: 청년 진로 상담 에이전트 — RAG 기반 Q&A (GPT-4o-mini + evidence retrieval + 자체 검증 재생성)
from __future__ import annotations

import logging
import re
import time
from typing import Any

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_MAX_HISTORY = 10

# ── 답변 자체 검증 (환각 가드레일) ──────────────────────────────────
# llm_roadmap_service._self_evaluate와 동일한 휴리스틱 재검증 패턴.
_DATE_RE = re.compile(r"\d{4}\s*년\s*\d{1,2}\s*월(\s*\d{1,2}\s*일)?|\d{1,2}\s*월\s*\d{1,2}\s*일")
# 합격률·통과율 문맥의 %만 감지 (훈련비 지원 비율 등 시스템 프롬프트에 이미 존재하는
# 정책 수치까지 오탐하지 않도록 "합격/통과" 문맥에 인접한 경우로 한정)
_PASS_RATE_RE = re.compile(
    r"(합격률|합격\s*률|통과율)[^.?!\n]{0,20}?\d+\.?\d*\s*%|\d+\.?\d*\s*%[^.?!\n]{0,10}?(합격|통과)"
)
_LINK_RE = re.compile(r"https?://[^\s)\]]+")
_ALLOWED_LINK_DOMAINS = (
    "work24.go.kr", "hrd.go.kr", "bokjiro.go.kr", "q-net.or.kr",
    "moel.go.kr", "mentalhealth.go.kr", "suicide.or.kr", "mogef.go.kr",
    "youthcenter.go.kr", "career.go.kr", "youth.go.kr",
)


def _self_evaluate_reply(reply: str, has_evidence: bool) -> dict[str, Any]:
    """생성된 답변에서 미연동 일정·미근거 수치·미확인 링크를 휴리스틱으로 감지한다."""
    issues: list[str] = []
    if _DATE_RE.search(reply):
        issues.append("구체적 날짜(연/월/일) 언급 감지 — 시험·접수 일정 미연동 상태이므로 날짜를 지어내면 안 됨")
    if not has_evidence and _PASS_RATE_RE.search(reply):
        issues.append("근거 없이 %(합격률·수치) 언급 감지 — evidence가 없으면 수치를 발명하면 안 됨")
    for url in _LINK_RE.findall(reply):
        if not any(domain in url for domain in _ALLOWED_LINK_DOMAINS):
            issues.append(f"공식 도메인 목록 밖의 링크 감지: {url}")
    return {"issues": issues, "pass": len(issues) == 0}

# 동일 cert + 질문 조합의 evidence 재조회 방지 (embedding 비용 절감)
_EVIDENCE_TTL = 3600
_evidence_cache: dict[str, tuple[float, list[str]]] = {}

# 내부 분류 레이블 — 시스템 프롬프트 전용 (사용자에게 직접 노출 안 함)
_STAGE_LABELS: dict[str, str] = {
    "1": "유형A (사회이행 준비 중, 관계·활동 일부 유지)",
    "2": "유형B (활동은 하나 취업 안착 어려움, 대처능력 부족)",
    "3": "유형C (사회활동 제한, 일상 어려움 큼)",
    "4": "유형D (외부 접촉 최소화, 일상 안정화 필요)",
}

_BASE_SYSTEM_PROMPT = """당신은 DIDIM 서비스의 청년 진로 상담사입니다.
자격증 추천, 로드맵, 취업 준비, 정부 지원 정책을 친절하고 실질적으로 안내합니다.

## 사용자 유형별 특성 및 자격증 전략 (내부 참고용 — 사용자에게 유형 명칭을 직접 언급하지 말 것)

### 유형A — 사회이행 준비 중
특성: 관계·활동은 어느 정도 유지, 취·창업 시도 중.
자격증 전략: 기사·산업기사 등 전문 자격 도전 가능, 자기주도 학습 병행.
지원: 자기개발·진로탐색 프로그램, 청년도전지원사업, 마음건강바우처.

### 유형B — 취업 안착 어려움
특성: 취·창업 노력하지만 사회 안착 반복 탈락, 문제해결 어려움.
자격증 전략: 산업기사·기능사 + GTQ·컴퓨터활용능력 1급 등, 훈련과정 참여 중심.
지원: 치유적 관계 형성 프로그램, 사례관리 연계.

### 유형C — 사회활동 제한
특성: 대인관계·사회생활 어려움, 기본 활동도 힘든 상황.
자격증 전략: 기능사·컴퓨터활용능력 2급 등 부담 낮은 자격, 과정평가형 우선.
지원: 긴급복지 연계, 주거 지원, 생계 지원.

### 유형D — 일상 안정화 필요
특성: 외부 접촉 최소화, 일상 리듬 회복이 우선.
자격증 전략: 온라인 학습 자격, 일학습병행, 과정평가형 우선, 시험 부담 최소화.
지원: 공동생활·일상관리 프로그램, 사회기술 재학습.

## 정부 지원 정책
### 국민내일배움카드
- 대상: 실업자, 재직자(임금근로자), 자영업자
- 지원: 훈련비의 45~85% (연간 최대 500만원)
- 신청: 고용24(work24.go.kr) 또는 가까운 고용센터
- 제한: 현직 공무원·만 75세 이상 등 일부 제외

### 국민취업지원제도 (구직촉진수당)
- 대상: 취업경험이 부족한 청년(18~34세) 및 저소득층
- 지원: 월 50만원 × 최대 6개월 + 취업지원 서비스
- 신청: 고용24 또는 고용센터

### 훈련과정 찾기
- HRD-Net (hrd.go.kr): 국민내일배움카드 훈련과정 검색
- 고용24 (work24.go.kr): 카드 신청 및 훈련 신청

## 답변 원칙
- 확인되지 않은 시험 일정·날짜·링크를 지어내지 않는다.
- 자격증 합격률·난이도는 근거가 있을 때만 언급한다.
- 항상 실현 가능한 단계별 행동을 제안한다.
- 상황이 어려울수록 부담이 낮은 것을 먼저 권장한다.
- 사용자에게 내부 유형 명칭(유형A/B/C/D, 고립위험청년, 은둔청년 등)을 직접 말하지 않는다.
- 답변이 길어지면 3~4문장으로 핵심만 먼저 말하고, 필요 시 추가 설명을 제안한다.
"""


def _retrieve_evidence(cert_name: str, user_question: str, settings: Settings, cert_id: str = "") -> list[str]:
    """cert_name 기반으로 관련 evidence snippet을 가져온다."""
    _ev_key = f"{cert_id or cert_name}|{user_question[:80]}"
    _ev_entry = _evidence_cache.get(_ev_key)
    if _ev_entry is not None and (time.monotonic() - _ev_entry[0]) < _EVIDENCE_TTL:
        return _ev_entry[1]

    try:
        from backend.app.services.retrieval_service import search_evidence

        if not cert_id:
            _evidence_cache[_ev_key] = (time.monotonic(), [])
            return []

        result = search_evidence(
            {"cert_id": cert_id, "cert_name": cert_name, "query_text": user_question},
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


def _retrieve_stage_evidence(stage_id: str, user_question: str, settings: Settings) -> list[str]:
    """stage_id 기반으로 위험군 관련 evidence snippet을 가져온다."""
    _ev_key = f"stage_{stage_id}|{user_question[:80]}"
    _ev_entry = _evidence_cache.get(_ev_key)
    if _ev_entry is not None and (time.monotonic() - _ev_entry[0]) < _EVIDENCE_TTL:
        return _ev_entry[1]

    try:
        from backend.app.services.retrieval_service import search_stage_evidence

        result = search_stage_evidence(stage_id, user_question, settings)
        if not result.get("success"):
            _evidence_cache[_ev_key] = (time.monotonic(), [])
            return []
        rows = result.get("data", {}).get("evidence", [])
        snippets: list[str] = []
        seen: set[str] = set()
        for row in rows[:3]:
            snippet = (row.get("snippet") or "").strip()
            sec = (row.get("section_path") or [""])[0]
            if snippet and snippet not in seen:
                seen.add(snippet)
                label = f"[{sec}] " if sec else ""
                snippets.append(f"{label}{snippet}")
        _evidence_cache[_ev_key] = (time.monotonic(), snippets)
        return snippets
    except Exception as e:
        logger.debug("stage evidence retrieval failed: %s", e)
        return []


def _build_system_prompt(context: dict[str, Any], evidence_snippets: list[str]) -> str:
    parts = [_BASE_SYSTEM_PROMPT.strip()]

    stage_id = context.get("stage_id")
    if stage_id:
        label = _STAGE_LABELS.get(str(stage_id), f"유형{stage_id}")
        parts.append(f"\n[현재 사용자 상황 유형 — 내부 참고용]: {label}")

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

    # RAG: cert / stage 기반 evidence 검색
    evidence_snippets: list[str] = []
    cert_name = context.get("cert_name")
    cert_id = str(context.get("cert_id") or "")
    stage_id = str(context.get("stage_id") or "")
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )
    if last_user:
        if cert_id:
            evidence_snippets = _retrieve_evidence(cert_name or "", last_user, settings, cert_id=cert_id)
        if stage_id:
            stage_snippets = _retrieve_stage_evidence(stage_id, last_user, settings)
            evidence_snippets = evidence_snippets + stage_snippets

    system_prompt = _build_system_prompt(context, evidence_snippets)

    has_evidence = len(evidence_snippets) > 0

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        base_messages = [{"role": "system", "content": system_prompt}, *messages]
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=base_messages,
            max_tokens=600,
            temperature=0.5,
        )
        reply = (response.choices[0].message.content or "").strip()

        # ── 자체 검증 + 1회 재생성 (환각 가드레일) ──
        eval_result = _self_evaluate_reply(reply, has_evidence)
        refined = False
        if eval_result["issues"]:
            issue_list = "\n".join(f"  - {i}" for i in eval_result["issues"])
            refine_messages = base_messages + [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": (
                    f"위 답변에서 다음 문제가 감지됐습니다:\n{issue_list}\n\n"
                    "확인되지 않은 날짜·수치·링크를 모두 제거하고 같은 톤으로 답변을 다시 작성하세요."
                )},
            ]
            try:
                response2 = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=refine_messages,
                    max_tokens=600,
                    temperature=0.5,
                )
                refined_reply = (response2.choices[0].message.content or "").strip()
                if refined_reply:
                    reply = refined_reply
                    refined = True
            except Exception as e:
                logger.debug("chat self-refine retry failed: %s", e)

        return ok_envelope({
            "reply": reply,
            "role": "assistant",
            "used_evidence": has_evidence,
            "eval": {"issues": eval_result["issues"], "refined": refined},
        })
    except Exception as exc:
        return err_envelope(
            "UPSTREAM_ERROR",
            f"OpenAI 호출 중 오류가 발생했습니다: {exc}",
            {"exc_type": type(exc).__name__},
        )
