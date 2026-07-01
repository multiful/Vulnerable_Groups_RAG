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

    result = _build_roadmap_data(buckets, reasons, risk_id, starting_stage_id, llm_generated=llm_generated)
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

    system_prompt = """\
당신은 청년 취업 진로 상담 전문가입니다.
자격증 추천 근거를 정확히 3문장으로 작성합니다. 각 문장의 역할은 고정입니다.

─ 문장별 역할 ─
• 1문장: [자격증명] + [실 데이터]의 합격률·난이도를 수치로 인용하고 의미 해석
         합격률 없으면: 자격증이 해당 직무에서 어떤 역할을 하는지 한 문장으로 규정
• 2문장: 희망 직무에서 이 자격증으로 담당하는 구체적 업무 2가지 서술
         + 데이터에 있는 관련 직무로 경력 이동 가능성 명시
• 3문장: 사용자의 위험군·상황과 연결하여 지금 이 자격증이 필요한 이유
         + [실 데이터]의 시험 횟수를 근거로 구체적 준비 기간·전략 제시

─ 절대 금지 (이 표현으로 문장을 끝내면 틀린 답) ─
❌ "~에 도움이 됩니다"           ❌ "~기회를 제공합니다"
❌ "~을 높일 수 있습니다"        ❌ "~강점이 있습니다"
❌ "~발판이 될 것입니다"         ❌ "~현실화될 것입니다"
❌ "~기회를 마련할 수 있습니다"  ❌ "~것으로 기대됩니다"
❌ "~이 가능합니다"              ❌ "~좋습니다"
→ 3문장은 반드시 "[준비 기간]으로 [구체적 행동/결과]" 형태로 마무리
   예: "6개월 집중 준비로 상반기 시험을 첫 합격 목표로 설정할 수 있습니다."
   예: "연 2회 시험 중 하반기를 목표로 잡으면 취업 포트폴리오에 즉시 반영됩니다."

─ 데이터 규칙 ─
• [실 데이터]에 합격률 있음 → 필기·실기 수치를 모두 인용하고 "높다/낮다/의미" 해석 필수
• [실 데이터]에 없는 수치(합격률 등)는 절대 추측·발명 금지
• 관련 직무는 [실 데이터] 목록에 있는 명칭만 사용\
"""

    # messages 배열에 few-shot 쌍 삽입 (system 텍스트보다 효과적)
    _FS_USER_FULL = (
        "자격증=용접기술사(기술사) / 분야=기계/제조 / 희망직무=기계설계 / 위험군=활동제한형고립청년\n"
        "[실 데이터]\n"
        "합격률: 필기 평균 12.2%, 실기 평균 48.8%\n"
        "연간 시험 횟수: 연 2회\n"
        "관련 직무: 기계설계, 기계정비, 생산기술, 공정관리"
    )
    _FS_ASST_FULL = (
        "용접기술사 자격증은 필기 합격률 12.2%로 진입 장벽이 높지만, "
        "실기 합격률 48.8%는 실무 역량을 갖추면 통과 가능한 시험임을 보여줍니다. "
        "기계설계 직무에서 용접부 강도 검토·도면 검증 업무를 직접 담당하며, "
        "기계정비·공정관리 직무로 이동할 때도 동일한 자격으로 인정받습니다. "
        "활동에 제약이 있는 지금은 연 2회 시험 주기를 기준으로 "
        "6개월 집중 준비 루틴을 짜면 사회 복귀의 첫 성과를 자격증 취득으로 확정할 수 있습니다."
    )
    _FS_USER_LIMITED = (
        "자격증=섬유기계기사(기사) / 분야=패션/섬유 / 희망직무=패션 제작 / 위험군=활동형고립청년\n"
        "[실 데이터]\n"
        "연간 시험 횟수: 연 2회\n"
        "시험 난이도: 4.0/5 (어려움)\n"
        "관련 직무: 패션 제작"
    )
    _FS_ASST_LIMITED = (
        "섬유기계기사 자격증은 직물 생산 설비의 설계·운용을 전담하는 기사급 자격증으로, "
        "패션 제작 공정에서 기계 파트를 책임지는 직무와 직결됩니다. "
        "패션 제작 직무에서 원단 생산 공정 관리와 설비 트러블슈팅 업무를 수행하며, "
        "동일 분야 생산기술·품질관리 직무로 경력 축을 넓힐 수 있습니다. "
        "사회 활동을 늘려가는 단계에서 난이도 4.0/5는 6~8개월 집중 학습으로 대응 가능하고, "
        "연 2회 시험이므로 상반기·하반기 중 목표 시점을 하나 고정하면 "
        "준비 구조가 흔들리지 않습니다."
    )

    few_shot_user = _FS_USER_FULL if has_pass_rate else _FS_USER_LIMITED
    few_shot_asst = _FS_ASST_FULL if has_pass_rate else _FS_ASST_LIMITED

    user_prompt = (
        f"자격증={cert_name}({cert_grade}) / 분야={domain_name} / "
        f"희망직무={job_name_override or '미지정'} / 위험군={risk_name}\n"
        f"{data_section}"
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",    "content": system_prompt},
                {"role": "user",      "content": few_shot_user},
                {"role": "assistant", "content": few_shot_asst},
                {"role": "user",      "content": user_prompt},
            ],
            max_tokens=380,
            temperature=0.2,
        )
        explanation = (resp.choices[0].message.content or "").strip()
        _explain_cache[_explain_key] = (time.monotonic(), explanation)
        return ok_envelope({
            "cert_id": cert_id,
            "explanation": explanation,
            "data_quality": data_quality,
        })
    except Exception as exc:
        return err_envelope("AI_ERROR", f"AI 설명 생성 실패: {str(exc)[:120]}")
