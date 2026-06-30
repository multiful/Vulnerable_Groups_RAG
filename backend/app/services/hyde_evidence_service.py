# File: hyde_evidence_service.py
# Last Updated: 2026-06-30
# Content Hash: SHA256:TBD
# Role: HyDE(Hypothetical Document Embeddings) 기반 위험군 분류 근거 검색 + LLM 합성
#
# 파이프라인:
#   1. dimension_scores → LLM 가설 구절 생성 (실제 검색 쿼리 확장용, 외부 노출 안 함)
#   2. 가설 구절 토큰 → _chunk_keyword_search()로 연구 문서 청크 검색
#   3. 검색된 청크만 근거로 LLM 설명 합성 (환각 가드레일)
#   4. synthesis + raw evidence 반환
#
# 환각 가드레일:
#   - LLM은 제공된 [문서 N] 텍스트만 참조 허용
#   - 근거 없으면 "찾지 못했습니다" 반환 → None 처리 → 프론트 raw snippet fallback
#   - synthesis에는 반드시 [문서 N] 인라인 인용 포함 요구

from __future__ import annotations

import re
import time
from typing import Any

from backend.app.core.config import Settings
from backend.app.schemas.envelope import ok_envelope

_CLUSTER_NAMES: dict[str, str] = {
    "1": "고립위험청년",
    "2": "활동형고립청년",
    "3": "활동제한형고립청년",
    "4": "은둔청년",
}

_CLUSTER_CONTEXT: dict[str, str] = {
    "1": "사회관계망이 일부 유지되고 활동 능력이 있으나 고립 위험이 잠재된 상태",
    "2": "사회활동에 참여하려는 의지가 있으나 관계 형성 및 경제적 어려움이 동반된 상태",
    "3": "사회활동 참여에 제약이 있고 대인관계·정신건강 영역에서 복합적 어려움이 있는 상태",
    "4": "사회관계 단절과 외출 회피가 심화되어 자기관리와 활동 전반에 높은 어려움이 있는 상태",
}

# HyDE 결과 서버 캐시 (cluster_id|dim_hash → (timestamp, result))
_HYDE_TTL = 1800
_hyde_cache: dict[str, tuple[float, dict]] = {}


def _dim_cache_key(cluster_id: str, dim_scores: dict[str, int]) -> str:
    serialized = "|".join(f"{k}:{v}" for k, v in sorted(dim_scores.items()))
    return f"{cluster_id}|{serialized}"


def _generate_hyde_query(
    cluster_id: str,
    dim_scores: dict[str, int],
    api_key: str,
) -> str:
    """
    LLM이 차원 점수 패턴을 바탕으로 연구 논문 스타일 가설 구절 생성.
    이 구절은 키워드 추출용으로만 사용하며 사용자에게 노출하지 않는다.
    """
    cluster_name = _CLUSTER_NAMES.get(cluster_id, "고립청년")
    cluster_ctx = _CLUSTER_CONTEXT.get(cluster_id, "")
    high_dims = [
        f"{k}({v}%)" for k, v in sorted(dim_scores.items(), key=lambda x: -x[1]) if v >= 30
    ]
    dim_desc = ", ".join(high_dims) if high_dims else "전반적 낮은 점수"

    prompt = (
        f"다음은 청년 고립·은둔 관련 연구 논문에 나올 법한 설명입니다.\n"
        f"대상 유형: {cluster_name}\n"
        f"상태 맥락: {cluster_ctx}\n"
        f"주요 어려움 차원: {dim_desc}\n\n"
        f"위 대상의 특성을 설명하는 연구 논문 수준의 한국어 문장 3~5개를 작성하세요.\n"
        f"규칙:\n"
        f"- 학술 논문체 사용 (사회관계, 고립, 은둔, 자기관리, 정신건강 등 연구 용어)\n"
        f"- 수치나 통계를 발명하지 않음\n"
        f"- '이 연구에서는', '본 연구 결과' 등 논문 서술 방식 허용"
    )

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.25,
    )
    return (resp.choices[0].message.content or "").strip()


def _expand_query_tokens(hypothetical: str, base_query: str) -> str:
    """가설 구절에서 한국어 명사 토큰 추출 + 기본 쿼리 결합."""
    tokens = re.findall(r"[가-힣]{2,6}", hypothetical)
    # 불용어 제거 (조사·연결어 포함 짧은 기능어)
    stopwords = {"이러한", "이와", "같이", "경우", "때문", "대한", "있는", "하는", "하여", "통해", "위해", "연구"}
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        if t not in stopwords and t not in seen:
            seen.add(t)
            unique.append(t)
    expanded = base_query + " " + " ".join(unique[:25])
    return expanded.strip()


def _synthesize_with_guardrail(
    cluster_id: str,
    dim_scores: dict[str, int],
    chunks: list[dict],
    api_key: str,
) -> str | None:
    """
    검색된 청크만 근거로 LLM 설명 합성.
    환각 가드레일:
      - 시스템 프롬프트에서 문서 외 정보 사용 엄격 금지
      - 각 문장에 [문서 N] 인용 요구
      - "찾지 못했습니다" 포함 시 None 반환 (프론트 fallback)
    """
    if not chunks:
        return None

    cluster_name = _CLUSTER_NAMES.get(cluster_id, "고립청년")
    high_dims = [
        f"{k}({v}%)" for k, v in sorted(dim_scores.items(), key=lambda x: -x[1])[:3] if v >= 20
    ]
    dim_summary = " / ".join(high_dims) if high_dims else "전반적 낮은 점수"

    doc_texts = "\n\n".join(
        f"[문서 {i + 1}] (출처: {c.get('doc_id', '').replace('_', ' ')})\n{c.get('snippet', '')[:600]}"
        for i, c in enumerate(chunks[:4])
    )

    system_prompt = (
        "당신은 청년 고립·은둔 연구 근거를 설명하는 전문가입니다.\n\n"
        "핵심 규칙:\n"
        "1. 반드시 아래 [제공 문서]에 있는 내용만 사용하세요.\n"
        "2. 문서에 없는 사실, 수치, 프로그램명을 절대 추가하지 마세요.\n"
        "3. 각 문장 끝에 [문서 N]으로 출처를 명시하세요.\n"
        "4. 관련 근거가 문서에 없으면 '해당 분류에 대한 문서 근거를 찾지 못했습니다.'라고만 응답하세요.\n"
        "5. 사용자에게 친절하고 이해하기 쉽게 2~3문장으로 설명하세요."
    )

    user_prompt = (
        f"[분류 결과]\n"
        f"유형: {cluster_name}\n"
        f"주요 어려움 차원: {dim_summary}\n\n"
        f"[제공 문서]\n{doc_texts}\n\n"
        f"위 제공 문서를 근거로, 이 사용자가 '{cluster_name}'으로 분류된 이유를 "
        f"사용자가 납득할 수 있도록 설명하세요.\n"
        f"각 문장에 [문서 N] 인용 필수."
    )

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=450,
        temperature=0.15,
    )
    result = (resp.choices[0].message.content or "").strip()

    # 환각 감지: 근거 없음 응답 → None
    if not result or "찾지 못했습니다" in result:
        return None
    return result


def _fallback_raw_evidence(cluster_id: str) -> dict[str, Any]:
    """OpenAI 키 없거나 LLM 실패 시 키워드 검색 결과만 반환."""
    from backend.app.services.retrieval_service import _chunk_keyword_search, _STAGE_DOC_IDS
    _CLUSTER_QUERIES: dict[str, str] = {
        "1": "고립위험청년 사회관계망 예방 연계 지원 사례관리",
        "2": "활동형고립청년 일경험 사례관리 치유 관계형성",
        "3": "활동제한형고립청년 활동 제한 외출 어려움 지원",
        "4": "은둔청년 사회관계 단절 자기관리 어려움 지원",
    }
    query = _CLUSTER_QUERIES.get(cluster_id, f"고립청년 지원 {cluster_id}")
    rows = _chunk_keyword_search(query, doc_ids=_STAGE_DOC_IDS, top_k=5)
    return ok_envelope({
        "cluster_id": cluster_id,
        "synthesis": None,
        "evidence": rows[:3],
        "hyde_used": False,
    })


def hyde_stage_evidence(
    cluster_id: str,
    dim_scores: dict[str, int],
    settings: Settings,
) -> dict[str, Any]:
    """
    POST /api/v1/risk/stage-evidence 메인 핸들러.

    dim_scores: {"관계망": 88, "활동": 75, "노동·경제": 60, "정신건강": 50, "자기관리": 40}
    """
    from backend.app.services.retrieval_service import _chunk_keyword_search, _STAGE_DOC_IDS

    # 캐시 확인
    cache_key = _dim_cache_key(cluster_id, dim_scores)
    cached = _hyde_cache.get(cache_key)
    if cached and (time.monotonic() - cached[0]) < _HYDE_TTL:
        return cached[1]

    # OpenAI 없으면 단순 키워드 검색 fallback
    if not settings.openai_api_key:
        result = _fallback_raw_evidence(cluster_id)
        _hyde_cache[cache_key] = (time.monotonic(), result)
        return result

    try:
        # Step 1: HyDE — 가설 구절 생성
        hypothetical = _generate_hyde_query(cluster_id, dim_scores, settings.openai_api_key)

        # Step 2: 키워드 확장 + 검색
        base_query = _CLUSTER_NAMES.get(cluster_id, "고립청년") + " 고립 은둔 사회관계 지원"
        expanded_query = _expand_query_tokens(hypothetical, base_query)
        chunks = _chunk_keyword_search(expanded_query, doc_ids=_STAGE_DOC_IDS, top_k=5)

        # Step 3: LLM 합성 (환각 가드레일 포함)
        synthesis = _synthesize_with_guardrail(
            cluster_id, dim_scores, chunks, settings.openai_api_key
        )

        result = ok_envelope({
            "cluster_id": cluster_id,
            "synthesis": synthesis,
            "evidence": chunks[:3],
            "hyde_used": True,
        })

    except Exception:
        result = _fallback_raw_evidence(cluster_id)

    _hyde_cache[cache_key] = (time.monotonic(), result)
    return result
