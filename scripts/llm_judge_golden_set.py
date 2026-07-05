# File: llm_judge_golden_set.py
# Last Updated: 2026-07-05
# Content Hash: SHA256:TBD
# Role: LLM-as-a-Judge로 6개 신규 페르소나의 "정답 자격증 집합"(정답지)을 생성하고,
#       실제 recommendation_service 출력과 비교해 recall을 계산한다.
#
# 실행: PYTHONPATH=. python scripts/llm_judge_golden_set.py
#        PYTHONPATH=. python scripts/llm_judge_golden_set.py --persona PJ01
#
# 방법론:
#   1. 각 페르소나(위험군 단계 × 관심 도메인)에 대해, 해당 도메인에 related_domains로
#      연결된 실제 cert_candidates.jsonl 후보 전체(할루시네이션 방지 — LLM이 새 자격증을
#      지어내지 않고 실존 후보 중에서만 판정하도록 제한)를 LLM에 제시한다.
#   2. LLM(GPT-4o-mini)은 각 후보가 "이 페르소나에게 추천하기 적합한가"를 이진 판정한다.
#      난이도 정책(사용자 지정):
#        - risk_0001(고립위험청년): 난이도 있는 자격증(기사·기술사 등)도 허용
#        - risk_0002~0004: 너무 어렵거나 합격률이 낮은 자격증은 지양 — 접근 가능한 난이도 우선
#   3. 판정된 relevant_cert_ids를 "정답지"로 저장.
#   4. 같은 쿼리로 recommendation_service.recommendations()를 호출해 실제 시스템 출력을 얻고,
#      recall = |정답지 ∩ 실제 추천| / |정답지| 를 계산한다 (전체 roadmap_sequence 기준 + top-10 기준).
#
# 출력: docs/evaluation/llm_judge_golden_set_2026-07-05.jsonl (persona별 1줄)
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(_ROOT))

from backend.app.core.config import Settings  # noqa: E402
from backend.app.services.recommendation_service import (  # noqa: E402
    _load_candidates,
    _load_pass_rate_map,
    _load_cert_detail_map,
    recommendations,
)

_OUT_PATH = _ROOT / "docs/evaluation/llm_judge_golden_set_2026-07-05.jsonl"

_RISK_STAGE_DESC: dict[str, str] = {
    "risk_0001": "1단계 고립위험청년 — 고립 위험 신호가 일부 있으나 사회 기능을 부분적으로 유지하는 단계. "
                 "구직·학습 활동을 스스로 이어갈 여력이 있는 편이다.",
    "risk_0002": "2단계 활동형 고립청년 — 외출·활동은 하지만 관계 형성에 어려움이 있고 사회 안착을 반복 탈락하는 단계.",
    "risk_0003": "3단계 활동제한형 고립청년 — 사회활동이 비자발적으로 극히 제한되고 고립 기간이 확인되는 단계.",
    "risk_0004": "4단계 은둔청년 — 가족 외 관계 단절, 외출 회피 장기화, 생활리듬 붕괴가 동반되는 단계.",
}

_DIFFICULTY_POLICY: dict[str, str] = {
    "risk_0001": (
        "이 사용자는 사회 기능을 상당 부분 유지하고 있다. 난이도 있는 자격증(기사·기술사 등급, "
        "합격률이 낮은 자격증 포함)도 도전 가능한 후보로 적극 포함해도 된다."
    ),
    "risk_0002": (
        "이 사용자는 관계 형성에 어려움을 겪고 반복적으로 탈락 경험이 있다. 너무 어렵거나 "
        "합격률이 매우 낮은 자격증(예: 기술사, 준비 기간이 긴 고난도 자격증)은 지양하고, "
        "접근 가능한 난이도(기능사·산업기사, 합격률이 상대적으로 높은 자격증)를 우선한다."
    ),
    "risk_0003": (
        "이 사용자는 사회활동이 비자발적으로 제한돼 있다. 너무 어렵거나 합격률이 매우 낮은 "
        "자격증은 지양하고, 접근 가능한 난이도를 우선한다."
    ),
    "risk_0004": (
        "이 사용자는 가족 외 관계가 단절되고 외출 회피가 장기화된 가장 취약한 단계다. "
        "너무 어렵거나 합격률이 매우 낮은 자격증은 지양하고, 부담 없이 시작할 수 있는 "
        "낮은 난이도(기능사, 합격률이 높은 자격증)를 우선한다."
    ),
}

# 6개 신규 페르소나 (사용자 지정)
PERSONAS: list[dict] = [
    {"persona_id": "PJ01", "risk_stage_id": "risk_0002", "domain_id": "domain_0002", "domain_name": "소프트웨어개발"},
    {"persona_id": "PJ02", "risk_stage_id": "risk_0001", "domain_id": "domain_0001", "domain_name": "데이터/AI"},
    {"persona_id": "PJ03", "risk_stage_id": "risk_0003", "domain_id": "domain_0016", "domain_name": "금융/회계"},
    {"persona_id": "PJ04", "risk_stage_id": "risk_0002", "domain_id": "domain_0033", "domain_name": "디자인"},
    {"persona_id": "PJ05", "risk_stage_id": "risk_0001", "domain_id": "domain_0027", "domain_name": "교육"},
    {"persona_id": "PJ06", "risk_stage_id": "risk_0004", "domain_id": "domain_0022", "domain_name": "법률"},
]

_SYSTEM_PROMPT = """\
당신은 청년 위험군 맞춤 자격증 추천 시스템의 품질을 평가하는 전문 심사위원(LLM-as-a-Judge)입니다.
주어진 사용자 페르소나(위험군 단계 + 관심 도메인)에 대해, 후보 자격증 목록 각각이
"이 페르소나에게 추천하기 적합한가(relevant)"를 판정합니다.

반드시 지켜야 할 것:
- 목록에 없는 자격증을 새로 만들어내지 않는다.
- 존재하지 않는 통계·수치를 지어내지 않는다.
- 난이도 정책을 반드시 반영한다(프롬프트에 명시됨).
- 도메인과 실질적으로 관련 없는 자격증은 제외한다.

출력 형식 (JSON만, 다른 텍스트 없이):
{
  "relevant_cert_ids": ["cert_xxxx", ...],
  "reasoning": {"cert_xxxx": "1문장 이유", ...}
}
"""


def _build_user_prompt(persona: dict, candidates: list[dict]) -> str:
    risk_desc = _RISK_STAGE_DESC[persona["risk_stage_id"]]
    policy = _DIFFICULTY_POLICY[persona["risk_stage_id"]]
    lines = [
        f"## 페르소나",
        f"- 위험군 단계: {risk_desc}",
        f"- 관심 도메인: {persona['domain_name']}",
        f"",
        f"## 난이도 정책 (반드시 반영)",
        policy,
        f"",
        f"## 후보 자격증 목록 ({len(candidates)}건) — 이 중에서만 판정",
    ]
    for c in candidates:
        pr = c["avg_pass_rate_3yr"]
        pr_str = f"{pr:.1f}%" if pr is not None else "합격률 미상"
        tier = c["cert_grade_tier"] or "비기술자격"
        jobs = len(c.get("related_jobs", []))
        lines.append(f"- {c['cert_id']} | {c['cert_name']} | 등급:{tier} | 합격률:{pr_str} | 관련직무수:{jobs}")
    lines.append("")
    lines.append("위 후보 전체에 대해 relevant/not-relevant를 판정하고, relevant로 판정한 cert_id만 JSON으로 반환하세요.")
    return "\n".join(lines)


def _judge_persona(persona: dict, settings: Settings, all_candidates: list[dict], pass_rate_map: dict) -> dict:
    domain_id = persona["domain_id"]
    matched = [c for c in all_candidates if domain_id in c.get("related_domains", [])]
    enriched = [
        {
            "cert_id": c["cert_id"],
            "cert_name": c["cert_name"],
            "cert_grade_tier": c.get("cert_grade_tier", ""),
            "avg_pass_rate_3yr": pass_rate_map.get(c["cert_id"]),
            "related_jobs": c.get("related_jobs", []),
        }
        for c in matched
    ]

    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    user_msg = _build_user_prompt(persona, enriched)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=2000,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    parsed = json.loads(raw)
    valid_ids = {c["cert_id"] for c in enriched}
    relevant = [cid for cid in parsed.get("relevant_cert_ids", []) if cid in valid_ids]
    reasoning = {k: v for k, v in parsed.get("reasoning", {}).items() if k in valid_ids}
    return {
        "candidate_pool_size": len(enriched),
        "relevant_cert_ids": relevant,
        "reasoning": reasoning,
    }


def _actual_system_cert_ids(persona: dict) -> list[str]:
    resp = recommendations({
        "risk_stage_id": persona["risk_stage_id"],
        "domain_ids": [persona["domain_id"]],
        "top_n_per_stage": 100,
    })
    if not resp.get("success"):
        return []
    seq = resp["data"].get("roadmap_sequence", [])
    return [s["cert_id"] for s in seq]


def _recall(gold: list[str], actual: list[str], k: int | None = None) -> float:
    if not gold:
        return 0.0
    actual_set = set(actual[:k]) if k else set(actual)
    hit = sum(1 for g in gold if g in actual_set)
    return hit / len(gold)


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge 골든셋 생성 + recall 평가")
    parser.add_argument("--persona", help="단일 persona_id만 실행 (예: PJ01)")
    args = parser.parse_args()

    settings = Settings()
    if not settings.openai_api_key:
        print("[ERROR] OPENAI_API_KEY 미설정 — backend/.env 확인", file=sys.stderr)
        return 1

    all_candidates = _load_candidates()
    pass_rate_map = _load_pass_rate_map()

    personas = PERSONAS
    if args.persona:
        personas = [p for p in personas if p["persona_id"] == args.persona]
        if not personas:
            print(f"[ERROR] persona '{args.persona}' 없음", file=sys.stderr)
            return 1

    results = []
    for persona in personas:
        print(f"[INFO] {persona['persona_id']} ({persona['risk_stage_id']} x {persona['domain_name']}) 판정 중...")
        judged = _judge_persona(persona, settings, all_candidates, pass_rate_map)
        actual_ids = _actual_system_cert_ids(persona)

        recall_all = _recall(judged["relevant_cert_ids"], actual_ids)
        recall_10 = _recall(judged["relevant_cert_ids"], actual_ids, k=10)

        result = {
            "persona_id": persona["persona_id"],
            "risk_stage_id": persona["risk_stage_id"],
            "domain_id": persona["domain_id"],
            "domain_name": persona["domain_name"],
            "candidate_pool_size": judged["candidate_pool_size"],
            "expected_relevant_cert_ids": judged["relevant_cert_ids"],
            "judge_reasoning": judged["reasoning"],
            "actual_system_cert_ids": actual_ids,
            "actual_system_total": len(actual_ids),
            "recall_all": round(recall_all, 3),
            "recall_at_10": round(recall_10, 3),
            "generated_by": "gpt-4o-mini (LLM-as-a-Judge)",
            "generated_at": "2026-07-05",
        }
        results.append(result)
        print(
            f"  gold={len(judged['relevant_cert_ids'])} "
            f"actual={len(actual_ids)} "
            f"recall_all={recall_all:.2f} recall@10={recall_10:.2f}"
        )

    _OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _OUT_PATH.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n[INFO] 저장 완료: {_OUT_PATH}")

    print(f"\n{'='*60}\n  SUMMARY\n{'='*60}")
    for r in results:
        print(f"  {r['persona_id']}  recall_all={r['recall_all']:.2f}  recall@10={r['recall_at_10']:.2f}  "
              f"(gold={len(r['expected_relevant_cert_ids'])}, actual={r['actual_system_total']})")
    avg_recall = sum(r["recall_all"] for r in results) / len(results) if results else 0.0
    print(f"\n  평균 recall_all = {avg_recall:.3f}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
