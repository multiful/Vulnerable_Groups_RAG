# File: llm_isolation_service.py
# Last Updated: 2026-06-25
# Content Hash: SHA256:TBD
# Role: 고립군 군집별 DIDIM 서비스 활성/비활성 이유를 LLM이 설명
#
# 설계 원칙:
#   - 어떤 서비스를 보여줄지 결정하는 것은 cluster_service_matrix.py 담당
#   - 이 파일은 그 결정에 대한 "왜"만 자연어로 변환
#   - JSON mode로 환각 방지, temperature 낮게 유지
#   - evidence 없으면 임의 사실 생성 금지 (빈 문자열 또는 hint 그대로 반환)
from __future__ import annotations

import json
import logging

from backend.app.core.config import Settings
from backend.app.services.cluster_service_matrix import (
    CLUSTER_ACTIVATION,
    DIDIM_SERVICES,
    build_service_context_for_llm,
)

logger = logging.getLogger(__name__)

# 군집 정의 (isolation_policy_service의 CLUSTER_META와 동기화 유지)
_CLUSTER_LABEL: dict[str, str] = {
    "1": "고립위험청년",
    "2": "활동형고립청년",
    "3": "활동제한형고립청년",
    "4": "은둔청년",
}

_CLUSTER_CONTEXT: dict[str, str] = {
    "1": (
        "사회적 관계망이 약화되기 시작했지만 아직 일부 사회활동이 가능한 상태입니다. "
        "자기이해·취업준비·사회참여를 균형 있게 지원하면 고립으로의 진행을 막을 수 있습니다."
    ),
    "2": (
        "신체적으로는 혼자 활동하지만 의미 있는 사회적 관계가 없는 상태입니다. "
        "치유적 관계 형성과 사회형 일경험을 통해 관계망을 서서히 넓혀가는 것이 중요합니다."
    ),
    "3": (
        "경제적·환경적 제약으로 외부 활동 자체가 어려운 상태입니다. "
        "당장 외출이나 대면 활동보다 온라인·집 기반 지원을 먼저 이용하는 것이 현실적입니다."
    ),
    "4": (
        "사회적 관계가 거의 단절되어 있고 자기관리가 어려운 상태입니다. "
        "취업·자격증보다 기본 생활 회복, 안전한 관계 형성, 심리적 지지가 먼저 필요합니다."
    ),
}

_SYSTEM_PROMPT = """\
당신은 고립·은둔 청년 지원 전문가입니다.
사용자의 군집 유형과 활성/비활성 서비스 목록을 받아
각 서비스에 대해 왜 지금 이 사람에게 적합하거나 적합하지 않은지를 한두 문장으로 설명합니다.

규칙:
- 설명은 따뜻하고 비판단적인 어조로 작성합니다.
- 비활성 서비스 설명은 "아직 때가 아님"을 인정하면서 희망적인 뉘앙스를 유지합니다.
- 존재하지 않는 정보를 지어내지 않습니다.
- 각 설명은 2문장 이내입니다.
- 반드시 JSON으로만 응답하며 다른 텍스트를 추가하지 않습니다.
"""


def _build_prompt(cluster_id: str, survey_summary: str | None) -> str:
    ctx = build_service_context_for_llm(cluster_id)
    label = _CLUSTER_LABEL.get(cluster_id, "고립 청년")
    cluster_ctx = _CLUSTER_CONTEXT.get(cluster_id, "")

    active_text = "\n".join(
        f'  - {s["id"]} ({s["name"]}): {s["desc"]}'
        for s in ctx["active"]
    )
    inactive_text = "\n".join(
        f'  - {s["id"]} ({s["name"]}): {s["reason_hint"]}'
        for s in ctx["inactive"]
    )

    survey_line = f"\n설문 요약: {survey_summary}" if survey_summary else ""

    return f"""군집 유형: {label} (군집 {cluster_id}단계)
군집 설명: {cluster_ctx}{survey_line}

[지금 이용 가능한 서비스]
{active_text or "(없음)"}

[지금은 아직인 서비스]
{inactive_text or "(없음)"}

위 정보를 바탕으로 아래 JSON 형식으로 응답하세요:
{{
  "active_explanations": {{
    "<service_id>": "<왜 지금 이 사람에게 적합한지 1~2문장>"
  }},
  "inactive_explanations": {{
    "<service_id>": "<왜 지금은 아직인지 희망적 어조로 1~2문장>"
  }}
}}"""


def explain_cluster_services(
    settings: Settings,
    cluster_id: str,
    survey_summary: str | None = None,
) -> dict:
    """
    군집 ID를 받아 각 DIDIM 서비스에 대한 LLM 설명을 생성.

    Args:
        cluster_id: '1'~'4'
        survey_summary: 설문 응답 요약 (선택, 개인화 품질 향상용)

    Returns:
        {
          "active_explanations": {"certification_roadmap": "왜 지금 좋은가", ...},
          "inactive_explanations": {"job_listings": "왜 아직은 아닌가", ...}
        }
    활성/비활성 결정은 cluster_service_matrix에서 가져오며 LLM이 변경하지 않음.
    """
    if cluster_id not in CLUSTER_ACTIVATION:
        return _fallback_explanations(cluster_id)

    openai_key = getattr(settings, "openai_api_key", None)
    if not openai_key:
        logger.warning("llm_isolation_service: OPENAI_API_KEY 미설정 — fallback 사용")
        return _fallback_explanations(cluster_id)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)

        prompt = _build_prompt(cluster_id, survey_summary)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1200,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        )

        raw = response.choices[0].message.content or "{}"
        result = json.loads(raw)

        # 키 검증: LLM이 반환한 service_id가 실제 존재하는지 확인
        active_exp  = _filter_valid_ids(result.get("active_explanations",  {}))
        inactive_exp = _filter_valid_ids(result.get("inactive_explanations", {}))

        return {
            "active_explanations":  active_exp,
            "inactive_explanations": inactive_exp,
        }

    except Exception as e:
        logger.warning("llm_isolation_service error: %s — fallback 사용", e)
        return _fallback_explanations(cluster_id)


def _filter_valid_ids(explanations: dict) -> dict:
    """LLM이 반환한 service_id 중 실제 DIDIM_SERVICES에 있는 것만 유지."""
    return {
        sid: text
        for sid, text in explanations.items()
        if sid in DIDIM_SERVICES and isinstance(text, str) and text.strip()
    }


def _fallback_explanations(cluster_id: str) -> dict:
    """
    LLM 호출 실패 시 cluster_service_matrix의 reason_inactive를 그대로 반환.
    active 서비스는 서비스 설명(desc)으로 대체.
    """
    ctx = build_service_context_for_llm(cluster_id)
    return {
        "active_explanations": {
            s["id"]: s["desc"]
            for s in ctx["active"]
        },
        "inactive_explanations": {
            s["id"]: s["reason_hint"]
            for s in ctx["inactive"]
            if s.get("reason_hint")
        },
    }
