# File: llm_cert_relevance_service.py
# Last Updated: 2026-06-28
# Content Hash: SHA256:TBD
# Role: 자격증 × 희망 직무 도메인 연관성 LLM 분석 + 7일 캐시
#
# 설계 원칙:
#   - 추천 결정은 canonical data 담당, 이 서비스는 "왜" 설명만 생성
#   - 환각 방지: JSON mode + temperature 0.2
#   - 캐시 TTL 7일: 연관성 데이터는 자주 바뀌지 않음
#   - LLM 실패 시 fallback: 고정 설명 반환 (빈 추천 결과 방지)
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_PATH = Path("data/cache/cert_relevance_cache.json")
CACHE_TTL = 604800  # 7일

_SYSTEM_PROMPT = """\
당신은 국내 자격증 취득 및 취업 시장 전문가입니다.
주어진 자격증과 희망 직무 분야의 실질적 연관성을 분석합니다.

출력 형식 (JSON만, 다른 텍스트 없이):
{
  "relevance_delta_pct": 정수 (이 직무 분야 채용공고에서 이 자격증이 요구되는 빈도가 해당 직무 전체 평균 대비 높은 정도, -50~100 사이),
  "relevance_summary": "이 자격증이 해당 직무에 왜 유용한지 1~2문장 한국어 설명 (실제 활용 상황 중심)",
  "difficulty_score": 정수 (0~100, 100이 가장 어려움, Q-Net 합격률 역방향 기준),
  "job_demand_level": "상" | "중" | "하"
}

규칙:
- 실제 한국 취업 시장에 근거하여 작성
- 존재하지 않는 통계 수치를 지어내지 않음
- relevance_delta_pct는 -50~100 범위 정수만 반환
- 설명은 청년 취업 준비생 눈높이로 작성
"""


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if time.time() - data.get("saved_at", 0) < CACHE_TTL:
                return data.get("entries", {})
        except Exception:
            pass
    return {}


def _save_cache(entries: dict) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps({"saved_at": time.time(), "entries": entries}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.debug("연관성 캐시 저장 실패: %s", e)


def _cache_key(cert_name: str, job_domain: str) -> str:
    return f"{cert_name}::{job_domain}"


_FALLBACK_MAP: dict[str, dict] = {
    "정보처리기사": {
        "relevance_delta_pct": 27,
        "relevance_summary": "IT 개발 직군 채용에서 기본 자격으로 우대되며, 공공기관 SI 프로젝트에서는 필수 요건으로 명시되는 경우가 많습니다.",
        "difficulty_score": 58,
        "job_demand_level": "상",
    },
    "빅데이터분석기사": {
        "relevance_delta_pct": 22,
        "relevance_summary": "데이터 분석·AI 직군에서 직무 적합성을 증명하는 수단으로 활용되며, 금융·공공 분야 데이터 직군 채용에서 우대 빈도가 높습니다.",
        "difficulty_score": 65,
        "job_demand_level": "상",
    },
    "정보보안기사": {
        "relevance_delta_pct": 31,
        "relevance_summary": "보안 직군 채용에서 사실상 필수 자격증으로, ISMS 관련 공공기관과 금융사 채용공고에서 상시 요구됩니다.",
        "difficulty_score": 70,
        "job_demand_level": "상",
    },
    "SQLD": {
        "relevance_delta_pct": 18,
        "relevance_summary": "개발·데이터 직군 전반에서 기초 데이터 역량을 증명하며, 비개발 직군(기획·분석)에서도 우대 항목으로 자주 등장합니다.",
        "difficulty_score": 45,
        "job_demand_level": "중",
    },
}

_DEFAULT_FALLBACK = {
    "relevance_delta_pct": 15,
    "relevance_summary": "이 자격증은 해당 직무 분야와 관련성이 있으며, 취업 시 자격 보유 여부가 서류 통과율을 높이는 데 도움이 될 수 있습니다.",
    "difficulty_score": 55,
    "job_demand_level": "중",
}


def get_cert_relevance(
    cert_name: str,
    job_domain: str,
    settings=None,
) -> dict:
    """
    자격증 × 직무 도메인 연관성 분석.

    Returns:
        {
          "relevance_delta_pct": int,
          "relevance_summary": str,
          "difficulty_score": int,
          "job_demand_level": "상"|"중"|"하",
          "from_cache": bool,
          "from_llm": bool,
        }
    """
    key = _cache_key(cert_name, job_domain)
    cache = _load_cache()

    if key in cache:
        return {**cache[key], "from_cache": True, "from_llm": False}

    openai_key = getattr(settings, "openai_api_key", None) if settings else None
    if not openai_key:
        fallback = _FALLBACK_MAP.get(cert_name, _DEFAULT_FALLBACK)
        return {**fallback, "from_cache": False, "from_llm": False}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        user_msg = (
            f"자격증: {cert_name}\n"
            f"희망 직무 분야: {job_domain}\n\n"
            "위 자격증이 해당 직무 분야 취업에 얼마나 유용한지 분석해 주세요."
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=300,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)

        entry = {
            "relevance_delta_pct": int(parsed.get("relevance_delta_pct", 15)),
            "relevance_summary": str(parsed.get("relevance_summary", _DEFAULT_FALLBACK["relevance_summary"])),
            "difficulty_score": int(parsed.get("difficulty_score", 55)),
            "job_demand_level": str(parsed.get("job_demand_level", "중")),
        }
        cache[key] = entry
        _save_cache(cache)
        return {**entry, "from_cache": False, "from_llm": True}

    except Exception as e:
        logger.warning("LLM 연관성 분석 실패 (%s × %s): %s", cert_name, job_domain, e)
        fallback = _FALLBACK_MAP.get(cert_name, _DEFAULT_FALLBACK)
        return {**fallback, "from_cache": False, "from_llm": False}
