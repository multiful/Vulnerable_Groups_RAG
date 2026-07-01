# File: llm_roadmap_service.py
# Last Updated: 2026-07-01 (hallucination guard, grade배치개선, UX용어정제)
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
import time
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
    "risk_0004": "roadmap_stage_0002",
    "risk_0005": "roadmap_stage_0002",
}

_TIER_ORDER: dict[str, int] = {
    "1_기능사": 1, "2_산업기사": 2, "3_기사": 3,
    "4_기술사": 4, "5_기능장": 5,
}

# ── OpenAI 호출 결과 서버 캐시 ──
# 동일 cert_id / (risk+domain) 조합은 1시간 내 재호출하지 않는다.
_EXPLAIN_TTL  = 3600  # explain_cert 캐시 TTL (초)
_ROADMAP_TTL  = 3600  # llm_recommendations 캐시 TTL (초)
_explain_cache: dict[str, tuple[float, str | None]] = {}
_roadmap_cache: dict[str, tuple[float, dict]]        = {}


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


_NCS_MAP_CSV      = _PROJECT_ROOT / "data/canonical/relations/cert_ncs_mapping.csv"
_NCS_MASTER_CSV   = _PROJECT_ROOT / "data/processed/master/ncs_master.csv"
_JOB_MAP_CSV      = _PROJECT_ROOT / "data/canonical/relations/cert_job_mapping.csv"
_JOB_MASTER_CSV   = _PROJECT_ROOT / "data/processed/master/job_master.csv"
_PREREQ_CSV       = _PROJECT_ROOT / "data/canonical/relations/cert_prerequisite.csv"
_CERT_MASTER_CSV  = _PROJECT_ROOT / "data/processed/master/cert_master.csv"
_SP_MASTER_CSV    = _PROJECT_ROOT / "data/processed/master/support_program_master.csv"
_SP_RISK_MAP_CSV  = _PROJECT_ROOT / "data/canonical/relations/support_program_risk_stage_mapping.csv"


@lru_cache(maxsize=1)
def _load_ncs_map() -> dict[str, str]:
    """cert_id → NCS 소직무분류 콤마 목록 (중복 제거)."""
    ncs_labels: dict[str, str] = {}
    if _NCS_MASTER_CSV.exists():
        with _NCS_MASTER_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                nid = r.get("ncsID", "")
                sub = r.get("소직무분류", "")
                if nid and sub:
                    ncs_labels[nid] = sub

    result: dict[str, list[str]] = {}
    if _NCS_MAP_CSV.exists():
        with _NCS_MAP_CSV.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("is_active", "").lower() != "true":
                    continue
                cid = r.get("cert_id", "")
                label = ncs_labels.get(r.get("ncs_id", ""), "")
                if cid and label:
                    result.setdefault(cid, []).append(label)

    return {cid: ", ".join(dict.fromkeys(v)) for cid, v in result.items()}


@lru_cache(maxsize=1)
def _load_job_map() -> dict[str, list[str]]:
    """cert_id → job_role_name 목록 (cert_job_mapping × job_master 조인)."""
    job_names: dict[str, str] = {}
    if _JOB_MASTER_CSV.exists():
        with _JOB_MASTER_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                jid = r.get("job_role_id", "")
                jname = r.get("job_role_name", "")
                if jid and jname:
                    job_names[jid] = jname

    result: dict[str, list[str]] = {}
    if _JOB_MAP_CSV.exists():
        with _JOB_MAP_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("is_active", "").lower() != "true":
                    continue
                cid = r.get("cert_id", "")
                jname = job_names.get(r.get("job_role_id", ""), "")
                if cid and jname:
                    result.setdefault(cid, []).append(jname)

    return result


@lru_cache(maxsize=1)
def _load_prereq_map() -> dict[str, list[str]]:
    """cert_id → 선행 자격증 이름 목록."""
    cert_names: dict[str, str] = {}
    if _CERT_MASTER_CSV.exists():
        with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                cid = r.get("cert_id", "")
                cname = r.get("cert_name", "")
                if cid and cname:
                    cert_names[cid] = cname

    result: dict[str, list[str]] = {}
    if _PREREQ_CSV.exists():
        with _PREREQ_CSV.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("is_active", "").lower() != "true":
                    continue
                cid = r.get("cert_id", "")
                pid = r.get("prerequisite_cert_id", "")
                pname = cert_names.get(pid, "")
                if cid and pname:
                    result.setdefault(cid, []).append(pname)

    return result


@lru_cache(maxsize=1)
def _load_support_programs() -> dict[str, dict]:
    """support_program_id → program dict (master)."""
    out: dict[str, dict] = {}
    if _SP_MASTER_CSV.exists():
        with _SP_MASTER_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("is_active", "").lower() == "true":
                    out[r["support_program_id"]] = r
    return out


@lru_cache(maxsize=1)
def _load_sp_risk_map() -> dict[str, list[str]]:
    """risk_stage_id → [support_program_id, ...] (active only)."""
    out: dict[str, list[str]] = {}
    if _SP_RISK_MAP_CSV.exists():
        with _SP_RISK_MAP_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("is_active", "").lower() == "true":
                    out.setdefault(r["risk_stage_id"], []).append(r["support_program_id"])
    return out


_SP_CATEGORY_DISPLAY: dict[str, str] = {
    "자기이해_및_심리상담":  "자기이해 및 심리상담",
    "치유적_관계형성":      "치유적 관계 형성",
    "일_경험_및_사회활동":  "일 경험 및 사회활동",
    "사후관리":             "사후 지원",
    "별도_지원":            "별도 생계·주거 지원",
}
_SP_PHASE_DISPLAY: dict[str, str] = {
    "고립된_삶":   "고립 단계",
    "회복":        "회복 단계",
    "통합된_삶":   "사회 통합 단계",
}


def get_support_programs_for_risk(risk_stage_id: str) -> dict:
    """risk_stage_id 에 매핑된 지원 제도 목록 반환."""
    programs = _load_support_programs()
    sp_risk_map = _load_sp_risk_map()
    sp_ids = sp_risk_map.get(risk_stage_id, [])
    if not sp_ids:
        return ok_envelope({"risk_stage_id": risk_stage_id, "support_programs": [], "total": 0, "by_category": []})

    result = []
    for sp_id in sp_ids:
        p = programs.get(sp_id)
        if p:
            raw_cat   = p.get("service_category", "")
            raw_phase = p.get("lifecycle_phase", "")
            result.append({
                "support_program_id": sp_id,
                "support_program_name": p.get("support_program_name", ""),
                "service_category": raw_cat,
                "category_display": _SP_CATEGORY_DISPLAY.get(raw_cat, raw_cat.replace("_", " ")),
                "lifecycle_phase": raw_phase,
                "phase_display": _SP_PHASE_DISPLAY.get(raw_phase, raw_phase.replace("_", " ")),
                "description": p.get("description", ""),
            })

    # category_display 기준으로 그룹핑
    grouped: dict[str, list[dict]] = {}
    for item in result:
        cat_key = item["category_display"]
        grouped.setdefault(cat_key, []).append(item)

    return ok_envelope({
        "risk_stage_id": risk_stage_id,
        "total": len(result),
        "by_category": [
            {"category": cat, "programs": items}
            for cat, items in grouped.items()
        ],
        "support_programs": result,
    })


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


def _parse_avg_pass_rate(dense: str) -> float | None:
    """text_for_dense에서 3년 평균 합격률(%)을 파싱한다."""
    m = re.search(r"3년 평균 합격률:\s*([\d.]+)%", dense)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _passrate_to_difficulty(rate: float) -> float:
    """합격률(%)을 가상 난이도(1~5)로 역환산. 합격률 낮을수록 어려움."""
    if rate >= 70:
        return 1.5
    if rate >= 50:
        return 2.5
    if rate >= 30:
        return 3.5
    return 4.5


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
    빈 tier: ① 명시 난이도 → ② 합격률 역산 난이도 → ③ 기본값 순으로 배치."""
    stage_map = _TIER_TO_STAGE_HIGH if risk_order >= 3 else _TIER_TO_STAGE_LOW
    stage_order = [s["id"] for s in _LOCAL_STAGES]
    start_idx = stage_order.index(starting_stage_id) if starting_stage_id in stage_order else 1

    buckets: dict[str, list[dict]] = {sid: [] for sid in stage_order}
    for c in selected:
        tier = c.get("cert_grade_tier") or ""
        dense = c.get("text_for_dense", "")
        if tier in stage_map and tier != "":
            target = stage_map[tier]
        else:
            # ① 명시 난이도
            difficulty = _parse_difficulty(dense)
            if difficulty is not None:
                target = _difficulty_to_stage(difficulty, risk_order)
            else:
                # ② 합격률 역산
                rate = _parse_avg_pass_rate(dense)
                if rate is not None:
                    target = _difficulty_to_stage(_passrate_to_difficulty(rate), risk_order)
                else:
                    # ③ 기본값 (탐색 시작 또는 시작 단계)
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


_GRADE_DISPLAY: dict[str, str] = {
    "1_기능사": "기능사", "2_산업기사": "산업기사", "3_기사": "기사",
    "4_기술사": "기술사", "5_기능장": "기능장",
}
_ACHIEVABILITY_DISPLAY: dict[str, str] = {
    "immediate": "지금 바로 도전",
    "near_term": "단계 준비 후 도전",
}


def _build_roadmap_data(
    buckets: dict[str, list[dict]],
    reasons: dict[str, str],
    risk_id: str,
    starting_stage_id: str,
    llm_generated: bool = True,
    risk_info: dict | None = None,
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
            raw_tier = cand.get("cert_grade_tier") or ""
            certs_here.append({
                "step": step,
                "cert_id": cert_id,
                "cert_name": cand.get("cert_name", cert_id),
                "cert_grade_tier": raw_tier,
                "grade_display": _GRADE_DISPLAY.get(raw_tier, "전문자격"),
                "avg_pass_rate": pass_rate,
                "is_bottleneck": False,
                "bottleneck_note": None,
                "is_redundant": False,
                "achievability": achievability,
                "achievability_display": _ACHIEVABILITY_DISPLAY.get(achievability, achievability),
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
    risk_stage_payload = None
    if risk_info:
        risk_stage_payload = {
            "id": risk_info.get("id", risk_id),
            "name": risk_info.get("name", risk_id),
            "order": risk_info.get("order"),
        }
    return {
        "risk_stage": risk_stage_payload,
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

    # 캐시 히트 → OpenAI 호출 없이 반환
    _roadmap_key = f"{risk_id}|{domain_id}"
    _roadmap_entry = _roadmap_cache.get(_roadmap_key)
    if _roadmap_entry and (time.monotonic() - _roadmap_entry[0]) < _ROADMAP_TTL:
        return ok_envelope(_roadmap_entry[1])

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

    result = _build_roadmap_data(
        buckets, reasons, risk_id, starting_stage_id,
        llm_generated=llm_generated,
        risk_info=risk_info if risk_id else None,
    )
    _roadmap_cache[_roadmap_key] = (time.monotonic(), result)
    return ok_envelope(result)


def _enrich_cert_context(cert_id: str, cert: dict) -> str:
    """자격증에 대한 구체적 데이터 컨텍스트 문자열 빌드 (합격률·시험과목·직무·시험횟수)."""
    from backend.app.services import cert_info_service
    lines: list[str] = []

    # 1. cert_master 평균 합격률
    stats_env = cert_info_service.get_cert_master_stats(cert_id)
    if stats_env.get("success") and (sd := stats_env.get("data")):
        w = sd.get("written_avg_pass_rate")
        p = sd.get("practical_avg_pass_rate")
        avg = sd.get("avg_pass_rate_3yr")
        freq = sd.get("exam_frequency")
        diff = sd.get("exam_difficulty")
        rate_parts: list[str] = []
        if w is not None: rate_parts.append(f"필기 평균 {w:.1f}%")
        if p is not None: rate_parts.append(f"실기 평균 {p:.1f}%")
        if avg is not None: rate_parts.append(f"3년 평균 {avg:.1f}%")
        if rate_parts:
            lines.append("합격률: " + ", ".join(rate_parts))
        if freq:
            lines.append(f"연간 시험 횟수: {freq}")
        if diff is not None:
            diff_label = "어려움" if diff >= 4 else "보통" if diff >= 2.5 else "쉬움"
            lines.append(f"시험 난이도: {diff:.1f}/5 ({diff_label})")

    # 2. 연도별 회별 실 합격률 추이 (최근 3년)
    sr_env = cert_info_service.get_session_pass_rates(cert_id)
    if sr_env.get("success") and (srd := sr_env.get("data")):
        for label, key in [("필기", "written"), ("실기", "practical")]:
            rows = srd.get(key, [])
            if rows:
                yr_map: dict[str, list[float]] = {}
                for r in rows:
                    yr_map.setdefault(r["year"], []).append(r["pass_rate"])
                yr_avg = {y: sum(v) / len(v) for y, v in yr_map.items()}
                sorted_yrs = sorted(yr_avg.keys())[-3:]
                trend = ", ".join(f"{y}년 {yr_avg[y]:.1f}%" for y in sorted_yrs)
                lines.append(f"{label} 합격률 추이({sorted_yrs[0]}–{sorted_yrs[-1]}): {trend}")

    # 3. cert_master에서 exam_type_info (필기/실기/면접 구성)
    from backend.app.services import cert_info_service as _ci
    detail = _ci._load_cert_master_details().get(cert_id, {})
    exam_type = detail.get("exam_type_info") or ""
    exam_subj = detail.get("exam_subject_info") or ""
    if exam_type:
        lines.append(f"시험 구성: {exam_type}")
    elif exam_subj:
        lines.append(f"시험 구성: {exam_subj}")

    # 4. dense text에서 시험과목·관련직무 추출
    dense = cert.get("text_for_dense", "")
    for pattern, label in [
        (r"시험 과목:\s*([^\.]+)", "시험 과목"),
        (r"관련 직무:\s*([^\.]+)", "관련 직무"),
    ]:
        m = re.search(pattern, dense)
        if m:
            lines.append(f"{label}: {m.group(1).strip()[:100]}")

    # 5. 관련 직업·취업처 (candidates JSON field)
    related_occ = cert.get("related_occupation", "") or cert.get("related_jobs_text", "")
    if related_occ and "관련 직무" not in "\n".join(lines):
        lines.append(f"관련 직업: {str(related_occ)[:100]}")

    # 6. 국가자격/공인민간자격 카탈로그 — 진로(자격활용) · 도입목적 · 자격 활용 현황
    cert_name = cert.get("cert_name", "")
    if cert_name:
        from backend.app.services import retrieval_service as _rs
        # 국가자격 카탈로그
        nat_index = _rs._load_national_catalog()
        nat_rec = nat_index.get(cert_name)
        if not nat_rec:
            norm = re.sub(r'[\s\(\)\[\]（）]', '', cert_name).lower()
            for key, val in nat_index.items():
                key_norm = re.sub(r'[\s\(\)\[\]（）]', '', key).lower()
                if norm and key_norm and (norm in key_norm or key_norm in norm):
                    nat_rec = val
                    break
        if nat_rec:
            career = nat_rec.get("career", "")
            purpose = nat_rec.get("purpose", "")
            if career:
                lines.append(f"진로(자격활용): {career[:200]}")
            if purpose:
                lines.append(f"도입목적: {purpose[:150]}")
        else:
            # 공인민간자격 카탈로그
            priv_index = _rs._load_private_catalog()
            priv_rec = priv_index.get(cert_name)
            if not priv_rec:
                norm = re.sub(r'[\s\(\)\[\]（）]', '', cert_name).lower()
                for key, val in priv_index.items():
                    key_norm = re.sub(r'[\s\(\)\[\]（）]', '', key).lower()
                    if norm and key_norm and (norm in key_norm or key_norm in norm):
                        priv_rec = val
                        break
            if priv_rec:
                usage = priv_rec.get("usage_status", "")
                if usage:
                    clean = " ".join(l.strip() for l in usage.splitlines() if l.strip())
                    lines.append(f"자격 활용 현황: {clean[:200]}")

    # 7. NCS 직무 분류 (cert_ncs_mapping × ncs_master)
    ncs_label = _load_ncs_map().get(cert_id, "")
    if ncs_label:
        lines.append(f"NCS 직무 분류: {ncs_label[:200]}")

    # 8. 구조화 직무 목록 (cert_job_mapping × job_master) — regex 추출 대체
    structured_jobs = _load_job_map().get(cert_id, [])
    if structured_jobs:
        job_str = ", ".join(structured_jobs[:10])
        # 기존 regex 기반 "관련 직무" 라인이 있으면 교체, 없으면 추가
        for i, ln in enumerate(lines):
            if ln.startswith("관련 직무:") or ln.startswith("관련 직업:"):
                lines[i] = f"관련 직무: {job_str}"
                break
        else:
            lines.append(f"관련 직무: {job_str}")

    # 9. 선행 자격증 (cert_prerequisite)
    prereqs = _load_prereq_map().get(cert_id, [])
    if prereqs:
        lines.append(f"선행 자격증: {', '.join(prereqs[:3])}")

    return "\n".join(lines) if lines else ""


def explain_cert(body: dict[str, Any], settings: Settings) -> dict:
    """POST /api/v1/recommendations/cert_explain
    단일 자격증에 대한 AI 추천 이유 생성.
    합격률 추이·시험과목·관련 직업 등 실 데이터를 컨텍스트로 포함해 구체적 근거를 생성한다.
    OpenAI 키가 없으면 NOT_CONFIGURED를 반환한다.
    """
    cert_id: str = body.get("cert_id") or ""
    domain_id: str = body.get("domain_id") or ""
    risk_stage_id: str = body.get("risk_stage_id") or ""
    job_name_override: str = body.get("job_name") or ""

    if not cert_id:
        return err_envelope("MISSING_REQUIRED_FIELD", "cert_id가 필요합니다.")

    if not settings.openai_api_key:
        return err_envelope("NOT_CONFIGURED", "OpenAI API 키가 설정되지 않아 AI 설명을 생성할 수 없습니다.")

    # 캐시 히트 → OpenAI 호출 없이 반환
    _explain_key = f"{cert_id}|{domain_id}|{risk_stage_id}|{job_name_override}"
    _explain_entry = _explain_cache.get(_explain_key)
    if _explain_entry and (time.monotonic() - _explain_entry[0]) < _EXPLAIN_TTL:
        return ok_envelope({"cert_id": cert_id, "explanation": _explain_entry[1]})

    candidates = _load_candidates()
    cert = next((c for c in candidates if c.get("cert_id") == cert_id), None)
    if not cert:
        return err_envelope("NOT_FOUND", f"cert_id={cert_id}를 찾을 수 없습니다.")

    domain_names = _load_domain_names()
    risk_stages = _load_risk_stages()
    domain_name = domain_names.get(domain_id, domain_id) if domain_id else "해당 분야"
    risk_info = risk_stages.get(risk_stage_id, {})
    risk_name = risk_info.get("name", "해당 단계") if risk_stage_id else "해당 단계"
    job_context = f" / 희망 직무: {job_name_override}" if job_name_override else ""

    _GRADE_LABEL = {
        "5_기능장": "기능장", "4_기술사": "기술사", "3_기사": "기사",
        "2_산업기사": "산업기사", "1_기능사": "기능사",
    }
    cert_name = cert.get("cert_name", cert_id)
    cert_grade = _GRADE_LABEL.get(cert.get("cert_grade_tier", ""), cert.get("cert_grade_tier", ""))
    enriched_ctx = _enrich_cert_context(cert_id, cert)
    has_pass_rate = "합격률" in enriched_ctx
    has_any_data = bool(enriched_ctx.strip())

    if has_pass_rate:
        data_quality = "full"
        data_section = f"[실 데이터]\n{enriched_ctx}"
    elif has_any_data:
        data_quality = "limited"
        data_section = f"[실 데이터]\n{enriched_ctx}"
    else:
        data_quality = "limited"
        data_section = "[실 데이터]\n없음"

    # ── 자체 평가 엔진 ──────────────────────────────────────────────
    _FORBIDDEN_RE = [
        r"에\s*도움이\s*됩니다",
        r"[을를]\s*제공합니다",          # "기회를", "조건을", "가능성을" 등 모두 포함
        r"[을를]\s*높일\s*수\s*있습니다",
        r"강점이\s*있습니다",
        r"발판이\s*될\s*것",
        r"현실화될\s*것",
        r"기회를\s*마련할\s*수\s*있습니다",
        r"기회를\s*가집니다",
        r"것으로\s*기대됩니다",
        r"진로를\s*개척할\s*수\s*있습니다",
        r"좋습니다\s*[.。]?\s*$",
    ]
    _TASK_VERB_RE = re.compile(
        r"(수행하|담당하|처리하|운용하|검토하|관리하|설계하|개발하|구축하|분석하|점검하|제작하|시험하)"
    )

    def _detect_forbidden(text: str) -> list[str]:
        return [p for p in _FORBIDDEN_RE if re.search(p, text)]

    def _self_evaluate(s1: str, s2: str, s3: str) -> dict[str, Any]:
        issues: list[str] = []
        # S1: 자격증명 + 합격률 수치
        if cert_name not in s1:
            issues.append(f"S1: 자격증명({cert_name}) 누락")
        if has_pass_rate and not re.search(r"\d+\.?\d*\s*%", s1):
            issues.append("S1: 합격률 % 수치 미인용 — 실 데이터에 있음에도 누락")
        if not has_pass_rate and re.search(r"\d+\.?\d*\s*%", s1):
            issues.append("S1: 실 데이터에 없는 합격률 수치 발명 — limited 케이스에서 % 사용 금지")
        for p in _detect_forbidden(s1):
            issues.append(f"S1 금지표현 감지: '{p}'")
        # S2: 구체적 업무 동사 2회 이상 또는 "하며"·"하고" 연결
        if not _TASK_VERB_RE.search(s2) and "하며" not in s2 and "하고" not in s2:
            issues.append("S2: 구체적 업무 동사(수행하·담당하·검토하 등) 없음")
        for p in _detect_forbidden(s2):
            issues.append(f"S2 금지표현 감지: '{p}'")
        # S3: 준비 기간 + 금지표현
        if not re.search(r"\d+개월|\d+주|상반기|하반기|연\s*\d+회", s3):
            issues.append("S3: 구체적 준비 기간/시험 회차 언급 없음")
        for p in _detect_forbidden(s3):
            issues.append(f"S3 금지표현 감지: '{p}'")

        score = max(1, 5 - len(issues))
        return {"score": score, "issues": issues, "pass": score >= 4}

    # ── JSON 구조화 출력 (sentence 별 독립 생성) ──────────────────────
    system_prompt = """\
당신은 청년 취업 진로 상담 전문가입니다.
반드시 아래 JSON 스키마로만 응답하세요. 다른 텍스트 없이 JSON만 출력합니다.

{
  "s1": "문장1: [자격증명] 포함 + 합격률 수치 대조·해석 (없으면 직무에서의 역할 규정)",
  "s2": "문장2: 희망직무에서 담당하는 구체적 업무 2가지(동사 포함) + 관련 직무 전환 명시",
  "s3": "문장3: [위험군 명칭] 언급 + 연 N회 시험 기준 M개월 준비 계획 + 취득 후 구체적 결과"
}

─ 각 필드 제약 ─
s1: cert_name을 첫 단어로 시작 / 합격률 있으면 "필기 X% … 실기 Y%" 형태로 인용 필수
    ※ [실 데이터]에 합격률이 없으면 % 수치를 절대 사용하지 말 것 — 자격증 역할·과목 설명으로만 대체
s2: "~하며" 또는 "~수행하고" 같은 동사로 업무 2개 나열 / 관련직무로 "전환·이동" 표현
s3: "[위험군]인 지금" 또는 "[위험군]에서" 로 시작 / 반드시 "N개월" 또는 "상·하반기" 포함
    → 마지막 어절은 반드시 행동 결과: "~확정됩니다", "~잡힙니다", "~설정됩니다" 등

─ 모든 필드 공통 금지 ─
• "~도움이 됩니다"  • "~기회를 제공합니다"  • "~을 높일 수 있습니다"
• "~강점이 있습니다"  • "~발판이 될 것입니다"  • "~현실화될 것입니다"
• "~기회를 마련할 수 있습니다"  • "~것으로 기대됩니다"
• "~기회를 가집니다"  ← 특히 s2에서 직무 전환 표현 시 금지
s2 직무 전환 표현: "~로 이동합니다", "~로 전환됩니다", "~에서도 동일하게 인정됩니다" 만 허용

─ 데이터 규칙 ─
• [실 데이터]에 있는 수치만 인용 / 없는 수치 절대 발명 금지
• 관련 직무는 [실 데이터] 목록 명칭만 사용\
"""

    _FS_USER_FULL = (
        "자격증=용접기술사(기술사) / 분야=기계/제조 / 희망직무=기계설계 / 위험군=활동제한형고립청년\n"
        "[실 데이터]\n합격률: 필기 평균 12.2%, 실기 평균 48.8%\n"
        "연간 시험 횟수: 연 2회\n관련 직무: 기계설계, 기계정비, 생산기술, 공정관리"
    )
    _FS_ASST_FULL = (
        '{"s1":"용접기술사 자격증은 필기 합격률 12.2%로 진입 장벽이 높지만 실기 합격률 48.8%는 '
        "실무 역량을 갖추면 통과 가능한 시험 구조임을 보여줍니다.\","
        '"s2":"기계설계 직무에서 용접부 강도 검토와 도면 검증 업무를 직접 수행하며, '
        "기계정비·공정관리 직무로 동일 자격을 그대로 인정받아 이동할 수 있습니다.\","
        '"s3":"활동제한형고립청년인 지금은 연 2회 시험 주기를 기준으로 '
        "6개월 집중 준비 루틴을 구성하면 사회 복귀의 첫 성과가 구체적으로 확정됩니다.\"}"
    )
    _FS_USER_LIMITED = (
        "자격증=섬유기계기사(기사) / 분야=패션/섬유 / 희망직무=패션 제작 / 위험군=활동형고립청년\n"
        "[실 데이터]\n연간 시험 횟수: 연 2회\n시험 난이도: 4.0/5 (어려움)\n관련 직무: 패션 제작"
    )
    _FS_ASST_LIMITED = (
        '{"s1":"섬유기계기사 자격증은 직물 생산 설비의 설계·운용을 전담하는 기사급 자격증으로 '
        "패션 제작 공정에서 기계 파트 전체를 책임집니다.\","
        '"s2":"패션 제작 직무에서 원단 생산 공정 관리와 설비 트러블슈팅 업무를 수행하며, '
        "난이도 4.0/5 수준이므로 관련 생산기술 직무로의 전환 시에도 동등하게 인정됩니다.\","
        '"s3":"활동형고립청년인 지금은 6~8개월 집중 학습으로 연 2회 시험 중 '
        "상반기를 목표로 잡으면 하반기 취업 일정이 구체적으로 잡힙니다.\"}"
    )

    few_shot_user = _FS_USER_FULL if has_pass_rate else _FS_USER_LIMITED
    few_shot_asst = _FS_ASST_FULL if has_pass_rate else _FS_ASST_LIMITED

    user_prompt = (
        f"자격증={cert_name}({cert_grade}) / 분야={domain_name} / "
        f"희망직무={job_name_override or '미지정'} / 위험군={risk_name}\n"
        f"{data_section}"
    )

    base_messages: list[dict] = [
        {"role": "system",    "content": system_prompt},
        {"role": "user",      "content": few_shot_user},
        {"role": "assistant", "content": few_shot_asst},
        {"role": "user",      "content": user_prompt},
    ]

    def _call_llm(messages: list[dict]) -> dict[str, str]:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=420,
            temperature=0.15,
        )
        raw = (resp.choices[0].message.content or "{}").strip()
        return json.loads(raw)

    try:
        # ── 1차 생성 ──
        parsed = _call_llm(base_messages)
        s1 = parsed.get("s1", "").strip()
        s2 = parsed.get("s2", "").strip()
        s3 = parsed.get("s3", "").strip()

        # ── 자체 평가 ──
        eval_result = _self_evaluate(s1, s2, s3)
        refined = False

        # ── 2차 재생성 (이슈가 하나라도 있으면 refine) ──
        if eval_result["issues"]:
            issue_list = "\n".join(f"  - {i}" for i in eval_result["issues"])
            refine_prompt = (
                f"위 답변에서 다음 문제가 감지됐습니다:\n{issue_list}\n\n"
                "각 문제를 수정하여 JSON을 다시 작성하세요. "
                "수정이 필요 없는 필드도 원래 내용을 유지해 전체 JSON을 반환하세요."
            )
            retry_messages = base_messages + [
                {"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)},
                {"role": "user",      "content": refine_prompt},
            ]
            parsed2 = _call_llm(retry_messages)
            s1 = parsed2.get("s1", s1).strip() or s1
            s2 = parsed2.get("s2", s2).strip() or s2
            s3 = parsed2.get("s3", s3).strip() or s3
            eval_result = _self_evaluate(s1, s2, s3)
            refined = True

        explanation = " ".join(filter(None, [s1, s2, s3]))
        _explain_cache[_explain_key] = (time.monotonic(), explanation)
        return ok_envelope({
            "cert_id": cert_id,
            "explanation": explanation,
            "data_quality": data_quality,
            "eval": {
                "score": eval_result["score"],
                "issues": eval_result["issues"],
                "refined": refined,
            },
        })
    except Exception as exc:
        return err_envelope("AI_ERROR", f"AI 설명 생성 실패: {str(exc)[:120]}")
