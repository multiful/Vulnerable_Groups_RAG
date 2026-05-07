# File: llm_roadmap_service.py
# Last Updated: 2026-05-07
# Content Hash: SHA256:TBD
# Role: LLM 기반 로드맵 조립 (DB 도메인 필터 → OpenAI 선별/정렬/설명 → RoadmapData 반환)
#
# 흐름:
#   1. cert_candidates.jsonl 로드
#   2. domain_id 필터 → 최대 25개 후보 추출
#   3. risk_stage + 시작 단계 파악
#   4. OpenAI GPT-4o-mini 호출 (JSON mode)
#   5. 응답 파싱 → 표준 roadmap_by_stage 구조 반환

from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

_PROJECT_ROOT = Path(__file__).parents[3]
_CANDIDATES_JSONL = _PROJECT_ROOT / "data/canonical/candidates/cert_candidates.jsonl"
_DOMAIN_MASTER = _PROJECT_ROOT / "data/processed/master/domain_master.csv"
_RISK_MASTER_CSV = _PROJECT_ROOT / "data/processed/master/risk_stage_master.csv"

_LOCAL_STAGES = [
    {"id": "roadmap_stage_0001", "name": "상태 인식", "order": 1,
     "description": "현재 생활 상태와 진로·취업 준비 수준을 점검하는 초기 단계"},
    {"id": "roadmap_stage_0002", "name": "탐색 시작", "order": 2,
     "description": "관심 분야, 전공 연계성, 가능한 직무와 자격증을 탐색하는 단계"},
    {"id": "roadmap_stage_0003", "name": "역량 준비", "order": 3,
     "description": "기초 학습, 자격증 준비, 교육훈련 참여 등으로 역량을 쌓는 단계"},
    {"id": "roadmap_stage_0004", "name": "실행 확대", "order": 4,
     "description": "지원 활동, 대외활동, 실전 경험을 늘리며 진로 실행을 확장하는 단계"},
    {"id": "roadmap_stage_0005", "name": "유지·정착", "order": 5,
     "description": "형성된 진로 경로와 생활 리듬을 유지하며 장기 계획으로 정착하는 단계"},
]
_STAGE_MAP = {s["id"]: s for s in _LOCAL_STAGES}

# risk_stage_to_roadmap_stage.csv 기준
_STARTING_STAGE: dict[str, str] = {
    "risk_0001": "roadmap_stage_0003",
    "risk_0002": "roadmap_stage_0002",
    "risk_0003": "roadmap_stage_0002",
    "risk_0004": "roadmap_stage_0001",
    "risk_0005": "roadmap_stage_0001",
}

_TIER_ORDER: dict[str, int] = {
    "1_기능사": 1, "2_산업기사": 2, "3_기사": 3,
    "4_기술사": 4, "5_기능장": 5,
}


@lru_cache(maxsize=1)
def _load_candidates() -> list[dict]:
    if not _CANDIDATES_JSONL.exists():
        return []
    out: list[dict] = []
    with _CANDIDATES_JSONL.open(encoding="utf-8") as f:
        for line in f:
            if s := line.strip():
                out.append(json.loads(s))
    return out


@lru_cache(maxsize=1)
def _load_domain_names() -> dict[str, str]:
    if not _DOMAIN_MASTER.exists():
        return {}
    out: dict[str, str] = {}
    with _DOMAIN_MASTER.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["domain_sub_label_id"]] = r["domain_sub_label_name"]
    return out


@lru_cache(maxsize=1)
def _load_risk_stages() -> dict[str, dict]:
    if not _RISK_MASTER_CSV.exists():
        return {}
    out: dict[str, dict] = {}
    with _RISK_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["risk_stage_id"]] = {
                "id": r["risk_stage_id"],
                "name": r["risk_stage_name"],
                "description": r.get("description", ""),
                "order": int(r.get("risk_stage_order", 0)),
            }
    return out


def _filter_domain(candidates: list[dict], domain_id: str) -> list[dict]:
    """primary_domain 매칭 우선. 부족하면 related_domains로 보충 (최소 10개 확보 목표)."""
    primary = [c for c in candidates if c.get("primary_domain") == domain_id]
    if len(primary) >= 10:
        return primary
    related = [
        c for c in candidates
        if c.get("primary_domain") != domain_id
        and domain_id in (c.get("related_domains") or [])
    ]
    return primary + related


def _filter_risk(candidates: list[dict], risk_id: str) -> list[dict]:
    return [c for c in candidates if risk_id in (c.get("recommended_risk_stages") or [])]


def _select_top(
    candidates: list[dict],
    risk_order: int,
    max_n: int = 25,
) -> list[dict]:
    """위험군 높을수록(3~5) 쉬운 자격증(기능사) 우선, 낮을수록(1~2) 상위 자격증 우선.
    reverse=False(ascending) → 기능사(1) 먼저 / reverse=True(descending) → 기술사(4) 먼저."""
    high_risk = risk_order >= 3
    return sorted(
        candidates,
        key=lambda c: _TIER_ORDER.get(c.get("cert_grade_tier", ""), 3),
        reverse=not high_risk,
    )[:max_n]


def _format_cert_line(c: dict) -> str:
    """LLM 프롬프트용 자격증 한 줄 포맷. text_for_dense에서 핵심 정보를 추출."""
    cert_id = c.get("cert_id", "")
    cert_name = c.get("cert_name", "")
    grade = c.get("cert_grade_tier") or "비기술"
    dense = c.get("text_for_dense", "")

    # text_for_dense에서 합격률·시험과목·관련직무 발췌
    import re as _re
    pass_rate = ""
    m = _re.search(r"3년 평균 합격률:\s*([\d.]+%)", dense)
    if m:
        pass_rate = f"합격률 {m.group(1)}"

    subjects = ""
    m2 = _re.search(r"시험 과목:\s*([^\.]+)", dense)
    if m2:
        subjects = m2.group(1).strip()

    jobs = ""
    m3 = _re.search(r"관련 직무:\s*([^\.]+)", dense)
    if m3:
        jobs = m3.group(1).strip()[:40]  # 너무 길면 자름

    extras = " | ".join(filter(None, [pass_rate, subjects, jobs]))
    return f"- {cert_id} | {cert_name} | {grade} | {extras}" if extras else f"- {cert_id} | {cert_name} | {grade}"


def _build_system_prompt(
    risk_name: str,
    risk_desc: str,
    domain_name: str,
    starting_stage_name: str,
) -> str:
    return (
        f"당신은 청년 취업 진로 상담 전문가입니다.\n\n"
        f"사용자 정보:\n"
        f"- 위험군: {risk_name} — {risk_desc}\n"
        f"- 관심 도메인: {domain_name}\n"
        f"- 권장 시작 단계: {starting_stage_name}\n\n"
        f"로드맵 단계 (stage_id → 단계명 → 배치 기준):\n"
        f"  roadmap_stage_0001 → 상태 인식: 합격률 높고 매우 쉬운 입문 자격증\n"
        f"  roadmap_stage_0002 → 탐색 시작: 기초·입문 비기술자격, 3급·준전문가\n"
        f"  roadmap_stage_0003 → 역량 준비: 기능사·중급 비기술자격, 1~2급\n"
        f"  roadmap_stage_0004 → 실행 확대: 산업기사·기사, 전문가급\n"
        f"  roadmap_stage_0005 → 유지·정착: 기술사·기능장·최상위\n\n"
        f"선택 규칙:\n"
        f"- 각 단계 최대 4개, 전체 최대 12개\n"
        f"- cert_id는 목록에 있는 것만 사용 (임의 생성 금지)\n"
        f"- 반드시 valid JSON만 반환 (마크다운 블록 사용 금지)\n\n"
        f"reason 작성 규칙 (중요):\n"
        f"- reason 첫 문장은 반드시 해당 cert_id의 자격증명(목록의 두 번째 컬럼)을 정확히 사용해 시작\n"
        f"- 반드시 해당 자격증의 구체적 정보(합격률·시험 과목·관련 직무 등)를 근거로 작성\n"
        f"- 이 사용자의 위험군 상황({risk_name})과 연결하여 왜 지금 이 자격증이 적합한지 설명\n"
        f"- '좋은 기회', '도움이 됩니다' 같은 일반적 문장 사용 금지\n"
        f"- 한국어 2문장 이내\n\n"
        f"응답 형식 (JSON):\n"
        f'{{"roadmap":['
        f'{{"stage_id":"roadmap_stage_0001","certs":[{{"cert_id":"...","reason":"..."}}]}},'
        f'{{"stage_id":"roadmap_stage_0002","certs":[]}},'
        f'{{"stage_id":"roadmap_stage_0003","certs":[]}},'
        f'{{"stage_id":"roadmap_stage_0004","certs":[]}},'
        f'{{"stage_id":"roadmap_stage_0005","certs":[]}}'
        f']}}'
    )


def _call_openai(system_prompt: str, cert_list_text: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"사용 가능한 자격증 목록:\n{cert_list_text}"},
        ],
        temperature=0.2,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or "{}"


def _parse_response(
    llm_json: str,
    cand_map: dict[str, dict],
    risk_id: str,
    starting_stage_id: str,
) -> dict:
    try:
        data = json.loads(llm_json)
    except json.JSONDecodeError:
        data = {}

    roadmap_items: list[dict] = data.get("roadmap", [])
    stage_entries_by_id: dict[str, list[dict]] = {}
    for item in roadmap_items:
        sid = item.get("stage_id", "")
        stage_entries_by_id[sid] = item.get("certs", [])

    by_stage: list[dict] = []
    sequence: list[dict] = []
    step = 1

    for stage in _LOCAL_STAGES:
        sid = stage["id"]
        entries = stage_entries_by_id.get(sid, [])
        certs_here: list[dict] = []

        for entry in entries:
            cert_id = entry.get("cert_id", "")
            cand = cand_map.get(cert_id)
            if not cand:
                continue
            achievability = (
                "immediate" if risk_id in (cand.get("recommended_risk_stages") or [])
                else "near_term"
            )
            certs_here.append({
                "step": step,
                "cert_id": cert_id,
                "cert_name": cand.get("cert_name", cert_id),
                "cert_grade_tier": cand.get("cert_grade_tier") or "",
                "avg_pass_rate": None,
                "is_bottleneck": False,
                "bottleneck_note": None,
                "is_redundant": False,
                "achievability": achievability,
                "related_jobs": (cand.get("related_jobs") or [])[:5],
                "llm_reason": entry.get("reason", ""),
            })
            sequence.append({
                "cert_id": cert_id,
                "cert_name": cand.get("cert_name", cert_id),
            })
            step += 1

        by_stage.append({
            "stage": stage,
            "is_starting_point": sid == starting_stage_id,
            "recommended_certs": certs_here,
        })

    start_info = _STAGE_MAP.get(starting_stage_id)
    return {
        "risk_stage": None,
        "starting_roadmap_stage": (
            {"id": starting_stage_id, "name": start_info["name"]} if start_info else None
        ),
        "roadmap_by_stage": by_stage,
        "roadmap_sequence": sequence,
        "cert_paths": [],
        "fallback_used": False,
        "fallback_note": "AI가 선별한 맞춤 로드맵입니다. (GPT-4o-mini)",
        "total_certs_in_roadmap": len(sequence),
        "llm_generated": True,
    }


def llm_recommendations(body: dict[str, Any], settings: Settings) -> dict:
    """POST /api/v1/recommendations/llm"""
    if not settings.openai_api_key:
        return err_envelope(
            "LLM_NOT_CONFIGURED",
            "OpenAI API 키가 설정되지 않았습니다. backend/.env 에 OPENAI_API_KEY를 추가하세요.",
        )

    risk_id: str = body.get("risk_stage_id") or ""
    domain_ids: list[str] = list(body.get("domain_ids") or [])
    domain_name_override: str = body.get("domain_name") or ""

    if not domain_ids:
        return err_envelope("MISSING_REQUIRED_FIELD", "domain_ids가 필요합니다.")

    domain_id = domain_ids[0]
    candidates = _load_candidates()
    if not candidates:
        return err_envelope(
            "DATA_NOT_READY",
            "cert_candidates.jsonl을 찾을 수 없습니다. scripts/build_cert_candidates.py를 먼저 실행하세요.",
        )

    domain_names = _load_domain_names()
    risk_stages = _load_risk_stages()

    domain_name = domain_name_override or domain_names.get(domain_id, domain_id)
    risk_info = risk_stages.get(risk_id, {})
    risk_name = risk_info.get("name", risk_id) if risk_id else "알 수 없음"
    risk_desc = risk_info.get("description", "") if risk_id else ""
    risk_order = risk_info.get("order", 3)
    starting_stage_id = _STARTING_STAGE.get(risk_id, "roadmap_stage_0003")
    starting_stage = _STAGE_MAP.get(starting_stage_id, _LOCAL_STAGES[2])

    domain_filtered = _filter_domain(candidates, domain_id)
    if not domain_filtered:
        return err_envelope("NO_CANDIDATES", f"도메인 {domain_id}에 해당하는 자격증이 없습니다.")

    risk_filtered = _filter_risk(domain_filtered, risk_id) if risk_id else domain_filtered
    if len(risk_filtered) < 5:
        risk_filtered = domain_filtered

    selected = _select_top(risk_filtered, risk_order=risk_order, max_n=25)
    cand_map = {c["cert_id"]: c for c in candidates}

    cert_lines = [
        _format_cert_line(c)
        for c in selected
    ]
    cert_list_text = "\n".join(cert_lines)

    system_prompt = _build_system_prompt(
        risk_name=risk_name,
        risk_desc=risk_desc,
        domain_name=domain_name,
        starting_stage_name=starting_stage["name"],
    )

    try:
        llm_json = _call_openai(system_prompt, cert_list_text, settings.openai_api_key)
        result = _parse_response(llm_json, cand_map, risk_id, starting_stage_id)
        return ok_envelope(result)
    except Exception as exc:
        return err_envelope("LLM_ERROR", f"LLM 호출 실패: {exc}")
