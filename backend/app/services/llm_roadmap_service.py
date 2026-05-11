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


def _select_diverse(
    candidates: list[dict],
    risk_order: int,
    max_n: int = 35,
) -> list[dict]:
    """티어별로 고르게 샘플링해 LLM이 전 단계에 배치할 수 있는 후보를 공급한다.

    high_risk(3~5)면 기능사/산업기사를 더 많이, low_risk(1~2)면 기사/기술사를 더 많이 포함.
    단순 정렬 대신 버킷 균등 채우기로 한 티어에 쏠리지 않게 한다.
    """
    buckets: dict[int, list[dict]] = {1: [], 2: [], 3: [], 4: [], 9: []}  # 9=비기술
    for c in candidates:
        tier = _TIER_ORDER.get(c.get("cert_grade_tier", ""), 0)
        key = tier if tier in buckets else 9
        buckets[key].append(c)

    high_risk = risk_order >= 3
    # 위험군 높으면 쉬운 것(1,2) 더 많이, 낮으면 어려운 것(3,4) 더 많이
    quotas = (
        {1: 10, 2: 8, 3: 6, 4: 3, 9: 8} if high_risk
        else {1: 4, 2: 6, 3: 10, 4: 8, 9: 7}
    )
    result: list[dict] = []
    for key, quota in quotas.items():
        result.extend(buckets[key][:quota])
    return result[:max_n]


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


# grade_tier → roadmap_stage 매핑 (risk_order별)
_TIER_TO_STAGE_HIGH: dict[str, str] = {   # risk 3~5 (높은 위험군)
    "1_기능사":   "roadmap_stage_0002",
    "2_산업기사": "roadmap_stage_0003",
    "3_기사":     "roadmap_stage_0004",
    "4_기술사":   "roadmap_stage_0005",
    "5_기능장":   "roadmap_stage_0005",
    "":           "roadmap_stage_0002",   # 비기술 → 탐색 시작
}
_TIER_TO_STAGE_LOW: dict[str, str] = {    # risk 1~2 (낮은 위험군)
    "1_기능사":   "roadmap_stage_0003",
    "2_산업기사": "roadmap_stage_0003",
    "3_기사":     "roadmap_stage_0004",
    "4_기술사":   "roadmap_stage_0005",
    "5_기능장":   "roadmap_stage_0005",
    "":           "roadmap_stage_0003",
}


def _parse_difficulty(dense: str) -> float | None:
    """text_for_dense에서 시험 난이도 수치(1.0~5.0)를 파싱한다."""
    m = re.search(r"시험 난이도:\s*(\d+(?:\.\d+)?)", dense)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _difficulty_to_stage(difficulty: float, risk_order: int) -> str:
    """난이도 수치를 roadmap_stage_id로 변환한다. 위험군이 높을수록 같은 난이도라도 더 이른 단계에 배치."""
    if risk_order >= 3:
        if difficulty <= 2.5:
            return "roadmap_stage_0002"
        elif difficulty <= 3.5:
            return "roadmap_stage_0003"
        else:
            return "roadmap_stage_0004"
    else:
        if difficulty <= 2.0:
            return "roadmap_stage_0002"
        elif difficulty <= 3.5:
            return "roadmap_stage_0003"
        else:
            return "roadmap_stage_0004"


def _assign_stages(
    selected: list[dict],
    risk_order: int,
    starting_stage_id: str,
    max_per_stage: int = 4,
) -> dict[str, list[dict]]:
    """grade_tier 기반으로 자격증을 단계에 구조적으로 배치한다. LLM 의존 없음.
    비기술/빈 티어는 text_for_dense의 시험 난이도 수치로 단계를 결정한다."""
    stage_map = _TIER_TO_STAGE_HIGH if risk_order >= 3 else _TIER_TO_STAGE_LOW
    stage_order = [s["id"] for s in _LOCAL_STAGES]
    start_idx = stage_order.index(starting_stage_id) if starting_stage_id in stage_order else 1

    buckets: dict[str, list[dict]] = {sid: [] for sid in stage_order}
    for c in selected:
        tier = c.get("cert_grade_tier") or ""
        if tier in stage_map and tier != "":
            target = stage_map[tier]
        else:
            # 비기술/빈 티어: 난이도 점수로 배치, 없으면 기본값
            difficulty = _parse_difficulty(c.get("text_for_dense", ""))
            if difficulty is not None:
                target = _difficulty_to_stage(difficulty, risk_order)
            else:
                target = stage_map.get("", starting_stage_id)
        # 시작 단계 이전이면 시작 단계로 당김
        if stage_order.index(target) < start_idx:
            target = starting_stage_id
        if len(buckets[target]) < max_per_stage:
            buckets[target].append(c)

    return buckets


def _build_reason_prompt(risk_name: str, domain_name: str) -> str:
    return (
        f"당신은 청년 취업 진로 상담 전문가입니다.\n"
        f"사용자 위험군: {risk_name} / 관심 도메인: {domain_name}\n\n"
        f"아래 자격증 목록의 각 cert_id에 대해 reason을 한국어 2문장 이내로 작성하세요.\n"
        f"규칙:\n"
        f"- 첫 문장은 해당 자격증 이름을 정확히 사용해 시작\n"
        f"- 합격률·시험 과목·관련 직무 등 구체적 수치를 근거로 사용\n"
        f"- 이 사용자의 위험군 상황과 연결해 왜 지금 이 자격증이 적합한지 설명\n"
        f"- '좋은 기회', '도움이 됩니다' 같은 일반적 문장 금지\n"
        f"- valid JSON만 반환 (마크다운 블록 금지)\n\n"
        f"응답 형식: {{\"reasons\":{{\"cert_id1\":\"reason1\", \"cert_id2\":\"reason2\", ...}}}}"
    )


def _call_openai_for_reasons(
    system_prompt: str,
    cert_lines: list[str],
    api_key: str,
) -> dict[str, str]:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    user_msg = "다음 자격증들에 대한 reason을 작성해 주세요:\n" + "\n".join(cert_lines)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=2500,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw).get("reasons", {})
    except json.JSONDecodeError:
        return {}


def _build_roadmap_data(
    buckets: dict[str, list[dict]],
    reasons: dict[str, str],
    risk_id: str,
    starting_stage_id: str,
    llm_generated: bool = True,
) -> dict:
    by_stage: list[dict] = []
    sequence: list[dict] = []
    step = 1

    for stage in _LOCAL_STAGES:
        sid = stage["id"]
        certs_here: list[dict] = []
        for cand in buckets.get(sid, []):
            cert_id = cand["cert_id"]
            achievability = (
                "immediate" if risk_id in (cand.get("recommended_risk_stages") or [])
                else "near_term"
            )
            dense = cand.get("text_for_dense", "")
            pass_rate: float | None = None
            _m = re.search(r"3년 평균 합격률:\s*([\d.]+)%", dense)
            if _m:
                try:
                    pass_rate = float(_m.group(1))
                except ValueError:
                    pass
            certs_here.append({
                "step": step,
                "cert_id": cert_id,
                "cert_name": cand.get("cert_name", cert_id),
                "cert_grade_tier": cand.get("cert_grade_tier") or "",
                "avg_pass_rate": pass_rate,
                "is_bottleneck": False,
                "bottleneck_note": None,
                "is_redundant": False,
                "achievability": achievability,
                "related_jobs": (cand.get("related_jobs") or [])[:5],
                "llm_reason": reasons.get(cert_id, ""),
            })
            sequence.append({"cert_id": cert_id, "cert_name": cand.get("cert_name", cert_id)})
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
        "fallback_note": (
            "AI가 각 자격증 추천 이유를 분석한 맞춤 로드맵입니다."
            if llm_generated
            else "단계별 자격증 경로를 구성했습니다."
        ),
        "total_certs_in_roadmap": len(sequence),
        "llm_generated": llm_generated,
    }


def llm_recommendations(body: dict[str, Any], settings: Settings) -> dict:
    """POST /api/v1/recommendations/llm
    구조적 배치(grade_tier 기반) + LLM reason 생성 분리 방식.
    LLM은 단계 배치를 결정하지 않고 reason 텍스트만 담당한다.
    """
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
            "cert_candidates.jsonl을 찾을 수 없습니다.",
        )

    domain_names = _load_domain_names()
    risk_stages = _load_risk_stages()

    domain_name = domain_name_override or domain_names.get(domain_id, domain_id)
    risk_info   = risk_stages.get(risk_id, {})
    risk_name   = risk_info.get("name", risk_id) if risk_id else "알 수 없음"
    risk_order  = risk_info.get("order", 3)
    starting_stage_id = _STARTING_STAGE.get(risk_id, "roadmap_stage_0003")

    domain_filtered = _filter_domain(candidates, domain_id)
    if not domain_filtered:
        return err_envelope("NO_CANDIDATES", f"도메인 {domain_id}에 해당하는 자격증이 없습니다.")

    risk_filtered = _filter_risk(domain_filtered, risk_id) if risk_id else domain_filtered
    if len(risk_filtered) < 5:
        risk_filtered = domain_filtered

    selected = _select_diverse(risk_filtered, risk_order=risk_order, max_n=35)

    # 1. 구조적 배치 (LLM 없이)
    buckets = _assign_stages(selected, risk_order, starting_stage_id, max_per_stage=4)

    # 2. LLM: reason 생성 (API 키 없으면 스킵)
    reasons: dict[str, str] = {}
    llm_generated = False
    if settings.openai_api_key:
        all_placed = [c for certs in buckets.values() for c in certs]
        cert_lines = [_format_cert_line(c) for c in all_placed]
        reason_prompt = _build_reason_prompt(risk_name, domain_name)
        try:
            reasons = _call_openai_for_reasons(reason_prompt, cert_lines, settings.openai_api_key)
            llm_generated = True
        except Exception:
            reasons = {}

    result = _build_roadmap_data(buckets, reasons, risk_id, starting_stage_id, llm_generated=llm_generated)
    return ok_envelope(result)


def explain_cert(body: dict[str, Any], settings: Settings) -> dict:
    """POST /api/v1/recommendations/cert_explain
    단일 자격증에 대한 AI 추천 이유 2문장 생성.
    evidence API가 원문 스니펫을 보여주는 것과 달리 사용자 맥락(도메인·위험군) 기반 설명을 생성한다.
    OpenAI 키가 없으면 NOT_CONFIGURED를 반환한다.
    """
    cert_id: str = body.get("cert_id") or ""
    domain_id: str = body.get("domain_id") or ""
    risk_stage_id: str = body.get("risk_stage_id") or ""

    if not cert_id:
        return err_envelope("MISSING_REQUIRED_FIELD", "cert_id가 필요합니다.")

    if not settings.openai_api_key:
        return err_envelope("NOT_CONFIGURED", "OpenAI API 키가 설정되지 않아 AI 설명을 생성할 수 없습니다.")

    candidates = _load_candidates()
    cert = next((c for c in candidates if c.get("cert_id") == cert_id), None)
    if not cert:
        return err_envelope("NOT_FOUND", f"cert_id={cert_id}를 찾을 수 없습니다.")

    domain_names = _load_domain_names()
    risk_stages = _load_risk_stages()
    domain_name = domain_names.get(domain_id, domain_id) if domain_id else "해당 분야"
    risk_info = risk_stages.get(risk_stage_id, {})
    risk_name = risk_info.get("name", "해당 단계") if risk_stage_id else "해당 단계"

    cert_line = _format_cert_line(cert)
    prompt = (
        f"당신은 청년 취업 진로 상담 전문가입니다.\n"
        f"사용자 관심 분야: {domain_name} / 위험군: {risk_name}\n\n"
        f"아래 자격증이 이 사용자에게 왜 적합한지 한국어 2문장 이내로 설명하세요.\n"
        f"규칙: 첫 문장에 자격증 이름을 반드시 포함. 합격률·관련 직무·활용처 등 구체적 근거 사용. "
        f"'도움이 됩니다'처럼 모호한 표현 금지. 격려하는 톤.\n\n"
        f"{cert_line}"
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5,
        )
        explanation = (resp.choices[0].message.content or "").strip()
        return ok_envelope({"cert_id": cert_id, "explanation": explanation})
    except Exception as exc:
        return err_envelope("AI_ERROR", f"AI 설명 생성 실패: {str(exc)[:120]}")
