# File: recommendation_service.py
# Last Updated: 2026-05-20
# Content Hash: SHA256:TBD
# Role: cert_candidates.jsonl 기반 구조적 추천 + 순서형 로드맵 조립 + DAG 경로 생성
#
# 추천 흐름:
#   1. risk_stage_id → 시작 roadmap_stage 결정
#   2. held_cert_ids / major_name → 동적 진입점 조정
#   3. domain_ids / job_ids / major_name 필터 (OR 조건)
#   4. risk_stage 필터 → 직접 매칭 없으면 domain-only fallback
#   5. 자격증별 sequence_score 계산 (아래 우선순위)
#   6. (stage_order, level_score, -pass_rate) 오름차순 정렬 → 순서형 로드맵 반환
#   7. cert_to_cert_relation.csv DAG 순회 → 자격증 경로(Path) 생성
#      - held_cert_ids 제공 시: 보유 자격증에서 상위 체인
#      - 미제공 시: 시퀀스 상위 N개(outgoing 엣지 보유)에서 체인
#
# ★ 레벨 추론 우선순위 (모두 기존 CSV 데이터 기반):
#   1순위 — cert_grade_tier (cert_master.csv 출처, NCS 공식 체계):
#     1_기능사=10/roadmap_0003, 2_산업기사=20/roadmap_0004,
#     3_기사=30/roadmap_0004, 4_기술사=40/roadmap_0005, 5_기능장=45/roadmap_0005
#   2순위 — avg_pass_rate_3yr (cert_master.csv 출처, 비기술자격에 적용):
#     합격률이 낮을수록 더 어려운 자격증 = 높은 roadmap_stage
#     ≥50% → roadmap_0002, 30-50% → roadmap_0003, 10-30% → roadmap_0004, <10% → roadmap_0005
#   3순위 — 자격증명 키워드 (pass_rate 데이터 없을 때만 fallback):
#     3급→0002, 2급→0002, 준전문가→0003, 개발자→0003, 1급→0004, 전문가→0005
#   동일 레벨 내: avg_pass_rate 높을수록 먼저 (쉬운 것부터)
#
# is_bottleneck: tier-relative 임계값(_BOTTLENECK_TIER_THRESHOLD) 미만 자격증에 플래그 — 사용자 고지용
# evidence 검색은 retrieval_service 담당.

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope
from backend.app.services import retrieval_service

# ---------- 경로 ----------
_PROJECT_ROOT    = Path(__file__).parents[3]
_CANDIDATES_JSONL = _PROJECT_ROOT / "data/canonical/candidates/cert_candidates.jsonl"
_CANDIDATES_CHANGED_JSONL = _PROJECT_ROOT / "data/canonical/candidates/cert_candidates_changed.jsonl"
_CANDIDATES_DIFF_JSON     = _PROJECT_ROOT / "data/canonical/candidates/.build_manifest_diff.json"
_CERT_MASTER_CSV  = _PROJECT_ROOT / "data/processed/master/cert_master.csv"
_RISK_MASTER_CSV  = _PROJECT_ROOT / "data/processed/master/risk_stage_master.csv"
_ROADMAP_MASTER   = _PROJECT_ROOT / "data/processed/master/roadmap_stage_master.csv"
_RISK_TO_ROADMAP  = _PROJECT_ROOT / "data/canonical/relations/risk_stage_to_roadmap_stage.csv"
_DOMAIN_MASTER    = _PROJECT_ROOT / "data/processed/master/domain_master.csv"
_MAJOR_MASTER     = _PROJECT_ROOT / "data/processed/master/major_master.csv"
_MAJOR_TO_DOMAIN  = _PROJECT_ROOT / "data/canonical/relations/major_to_domain.csv"
_CERT_TO_ROADMAP  = _PROJECT_ROOT / "data/canonical/relations/cert_to_roadmap_stage.csv"
_CERT_TO_CERT     = _PROJECT_ROOT / "data/canonical/relations/cert_to_cert_relation.csv"
_JOB_TO_DOMAIN    = _PROJECT_ROOT / "data/canonical/relations/job_to_domain.csv"
_MAJOR_ACQUI_CSV  = _PROJECT_ROOT / "data/raw/csv/전공별 취득 현황_rows.csv"
_REGION_ACQUI_CSV = _PROJECT_ROOT / "data/raw/csv/행정구역별연도별성별 취득현황_rows.csv"
_CERT_PREREQ_CSV  = _PROJECT_ROOT / "data/canonical/relations/cert_prerequisite.csv"

_RISK_ORDER = ["risk_0001", "risk_0002", "risk_0003", "risk_0004", "risk_0005"]

# ---------- 레벨 → roadmap_stage 매핑 ----------
# tier 기반 (기존 로직과 동일)
_TIER_SEQUENCE: dict[str, tuple[int, str]] = {
    "1_기능사":   (10, "roadmap_stage_0003"),
    "2_산업기사": (20, "roadmap_stage_0004"),
    "3_기사":     (30, "roadmap_stage_0004"),
    "4_기술사":   (40, "roadmap_stage_0005"),
    "5_기능장":   (45, "roadmap_stage_0005"),
}

# 비기술자격 합격률 → (레벨 점수, 유효 roadmap_stage) — PRIMARY (데이터 기반)
# 합격률 낮을수록 어려운 자격증 → 높은 stage에 배치
# 임계값: 50/30/10 (변별력 강화)
_PASSRATE_STAGE_MAP: list[tuple[float, int, str]] = [
    (50.0, 15, "roadmap_stage_0002"),  # 쉬움: 합격률 ≥50%
    (30.0, 22, "roadmap_stage_0003"),  # 중간: 30~50%
    (10.0, 30, "roadmap_stage_0004"),  # 어려움: 10~30%
    (0.0,  40, "roadmap_stage_0005"),  # 매우 어려움: <10%
]

_BOTTLENECK_THRESHOLD = 10.0  # 비기술자격 fallback 임계값

# R4-3: tier-relative is_bottleneck 임계값.
# 기능사 20% 미만은 병목이지만 기술사 20% 미만은 정상적 난이도 — tier별 분리.
_BOTTLENECK_TIER_THRESHOLD: dict[str, float] = {
    "1_기능사":   20.0,
    "2_산업기사": 15.0,
    "3_기사":     10.0,
    "4_기술사":    5.0,
    "5_기능장":    5.0,
}

# tier 점수 (redundancy 비교용) — 빈값은 0 (비기술자격, 비교 대상 제외)
_TIER_SCORE: dict[str, int] = {
    "1_기능사": 10, "2_산업기사": 20, "3_기사": 30,
    "4_기술사": 40, "5_기능장": 45,
}

# ── P6-2: 위험군별 tier 하한 ──
# 위험군 기반 필터. 해당 risk_stage에 포함된 기술자격 중 tier_min 미만은 제외.
# 비기술자격(tier_score=0)은 제외 대상이 아니며 pass_rate 로직으로 관리.
# 적용 위치: direct + fallback 필터 양쪽에서 일관 적용.
_RISK_TIER_MIN: dict[str, int] = {
    "risk_0001": 20,  # 취업 안정권 — 산업기사 이상만 (기능사 제외)
    "risk_0002": 15,  # 준안정권 — 기능사 상위(산업기사 경계 허용)
    "risk_0003": 10,  # 모든 기술자격 허용
    "risk_0004": 10,
    "risk_0005": 10,
}

# 비기술자격 키워드 패턴 → (레벨 점수, 유효 roadmap_stage) — FALLBACK (pass_rate 없을 때만)
# ★ 순서 중요: 준전문가가 전문가보다 먼저
_NONTECH_KEYWORD_RULES: list[tuple[str, int, str]] = [
    (r"준전문가",          20, "roadmap_stage_0003"),
    (r"전문가",            40, "roadmap_stage_0005"),
    (r"1급",               30, "roadmap_stage_0004"),
    (r"개발자",            25, "roadmap_stage_0003"),
    (r"준$|준\(",          20, "roadmap_stage_0003"),
    (r"2급",               15, "roadmap_stage_0002"),
    (r"3급",               10, "roadmap_stage_0002"),
]
_NONTECH_DEFAULT = (15, "roadmap_stage_0002")

# achievability: risk_stage 거리 기준
_ACHIEVABILITY = {0: "immediate", 1: "near_term", 2: "long_term"}


# ---------- 로드 ----------
@lru_cache(maxsize=1)
def _load_candidates() -> list[dict]:
    if not _CANDIDATES_JSONL.exists():
        return []
    out = []
    with _CANDIDATES_JSONL.open(encoding="utf-8") as f:
        for line in f:
            if s := line.strip():
                out.append(json.loads(s))
    return out


@lru_cache(maxsize=1)
def _load_pass_rate_map() -> dict[str, float]:
    if not _CERT_MASTER_CSV.exists():
        return {}
    out: dict[str, float] = {}
    with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                out[r["cert_id"]] = float(r.get("avg_pass_rate_3yr", ""))
            except ValueError:
                pass
    return out


@lru_cache(maxsize=1)
def _load_cert_detail_map() -> dict[str, dict]:
    """cert_id → {written_avg, practical_avg, exam_frequency, exam_difficulty, exam_fee_info, exam_eligibility_info}"""
    if not _CERT_MASTER_CSV.exists():
        return {}
    out: dict[str, dict] = {}
    with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            cid = r.get("cert_id", "")
            if not cid:
                continue
            def _flt(v: str) -> float | None:
                try:
                    return float(v) if v and v.strip() else None
                except ValueError:
                    return None
            out[cid] = {
                "written_avg_pass_rate":   _flt(r.get("written_avg_pass_rate", "")),
                "practical_avg_pass_rate": _flt(r.get("practical_avg_pass_rate", "")),
                "exam_frequency":          (r.get("exam_frequency") or "").strip() or None,
                "exam_difficulty":         _flt(r.get("exam_difficulty", "")),
                "exam_fee_info":           (r.get("exam_fee_info") or "").strip() or None,
                "exam_eligibility_info":   (r.get("exam_eligibility_info") or "").strip() or None,
            }
    return out


def _exam_freq_score(freq_str: str | None) -> float:
    """exam_frequency 문자열 → 접근성 가중치 (0.0~0.15).
    시험 기회가 많을수록 취업 급한 사용자에게 유리 → 점수 가산."""
    if not freq_str:
        return 0.0
    import re
    m = re.search(r"연\s*(\d+)회", freq_str)
    if m:
        n = int(m.group(1))
        # 연1회=0.0, 연2회=0.04, 연3회=0.08, 연4+회=0.12, 연10+회=0.15
        if n >= 10:
            return 0.15
        if n >= 4:
            return 0.12
        if n >= 3:
            return 0.08
        if n >= 2:
            return 0.04
    return 0.0


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


@lru_cache(maxsize=1)
def _load_roadmap_stages() -> dict[str, dict]:
    if not _ROADMAP_MASTER.exists():
        return {}
    out: dict[str, dict] = {}
    with _ROADMAP_MASTER.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["roadmap_stage_id"]] = {
                "id": r["roadmap_stage_id"],
                "name": r["roadmap_stage_name"],
                "description": r.get("description", ""),
                "order": int(r.get("stage_order", 0)),
            }
    return out


@lru_cache(maxsize=1)
def _load_risk_to_roadmap() -> dict[str, str]:
    if not _RISK_TO_ROADMAP.exists():
        return {}
    with _RISK_TO_ROADMAP.open(encoding="utf-8-sig") as f:
        return {r["risk_stage_id"]: r["roadmap_stage_id"] for r in csv.DictReader(f)}


@lru_cache(maxsize=1)
def _load_domain_map() -> dict[str, str]:
    if not _DOMAIN_MASTER.exists():
        return {}
    out: dict[str, str] = {}
    with _DOMAIN_MASTER.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["domain_sub_label_name"].strip().lower()] = r["domain_sub_label_id"]
    return out


@lru_cache(maxsize=1)
def _load_major_to_domain_map() -> dict[str, str]:
    """normalized major_name → domain_sub_label_id (2단계 join: major_master + major_to_domain)"""
    if not _MAJOR_MASTER.exists() or not _MAJOR_TO_DOMAIN.exists():
        return {}
    major_id_map: dict[str, str] = {}
    with _MAJOR_MASTER.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            key = r.get("normalized_key", "").strip().lower() or r.get("major_name", "").strip().lower()
            if key:
                major_id_map[key] = r["major_id"]
    m2d: dict[str, str] = {}
    with _MAJOR_TO_DOMAIN.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            m2d[r["major_id"]] = r["domain_sub_label_id"]
    return {k: m2d[v] for k, v in major_id_map.items() if v in m2d}


@lru_cache(maxsize=1)
def _load_job_to_domain_map() -> dict[str, list[str]]:
    """job_role_id → [domain_sub_label_id, ...] (is_active=True 행만)"""
    if not _JOB_TO_DOMAIN.exists():
        return {}
    out: dict[str, list[str]] = defaultdict(list)
    with _JOB_TO_DOMAIN.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("is_active", "True").strip().lower() not in ("true", "1"):
                continue
            out[r["job_role_id"]].append(r["domain_sub_label_id"])
    return dict(out)


@lru_cache(maxsize=1)
def _load_cert_to_roadmap_map() -> dict[str, str]:
    """cert_id → roadmap_stage_id"""
    if not _CERT_TO_ROADMAP.exists():
        return {}
    with _CERT_TO_ROADMAP.open(encoding="utf-8-sig") as f:
        return {r["cert_id"]: r["roadmap_stage_id"] for r in csv.DictReader(f)}


@lru_cache(maxsize=1)
def _load_cert_name_map() -> dict[str, str]:
    """cert_id → cert_name"""
    if not _CERT_MASTER_CSV.exists():
        return {}
    out: dict[str, str] = {}
    with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["cert_id"]] = r["cert_name"]
    return out


@lru_cache(maxsize=1)
def _load_cert_graph() -> dict[str, tuple[tuple[str, str, str, float], ...]]:
    """from_cert_id → ((to_cert_id, relation_type, source, confidence), ...)
    cert_to_cert_relation.csv 기반 forward DAG. is_active=False 행은 제외."""
    if not _CERT_TO_CERT.exists():
        return {}
    acc: dict[str, list[tuple[str, str, str, float]]] = defaultdict(list)
    with _CERT_TO_CERT.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("is_active", "True").strip().lower() not in ("true", "1", "yes"):
                continue
            try:
                conf = float(r.get("confidence") or 1.0)
            except ValueError:
                conf = 1.0
            acc[r["from_cert_id"]].append(
                (r["to_cert_id"], r.get("relation_type", ""), r.get("source", ""), conf)
            )
    # lru_cache 호환을 위해 불변 자료구조로 변환
    return {k: tuple(v) for k, v in acc.items()}


@lru_cache(maxsize=1)
def _load_cert_acqui_map() -> dict[str, int]:
    """jmNm(자격증명) → 전체 누적 취득자 수 (전공별 취득 현황_rows.csv).
    여러 전공에 걸쳐 집계된 값이므로 최대값을 사용한다."""
    if not _MAJOR_ACQUI_CSV.exists():
        return {}
    out: dict[str, int] = {}
    try:
        with _MAJOR_ACQUI_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                name = (r.get("jmNm") or "").strip()
                try:
                    cnt = int(r.get("accumAcquCnt") or 0)
                except (ValueError, TypeError):
                    cnt = 0
                if name and cnt > 0:
                    if out.get(name, 0) < cnt:
                        out[name] = cnt
    except Exception:
        pass
    return out


# ── P2: cert_paths 점수화 가중치 ──
# relation_type 우선순위 (prerequisite = 법적/공식 선수 > recommended_prior > next_step)
_RELATION_TYPE_WEIGHT: dict[str, float] = {
    "prerequisite":      1.00,
    "recommended_prior": 0.80,
    "next_step":         0.50,
    "":                  0.40,
}
_LENGTH_PENALTY = 0.10  # 경로 길이당 감점
_PASSRATE_WEIGHT = 0.003  # pass_rate(%) → score 가산 (최대 ~0.3)


def _path_score(
    steps: list[dict],
    pass_rate_map: dict[str, float],
) -> float:
    """경로의 종합 점수.
    base = Σ(edge relation_type weight * confidence) / edge_count
    length_penalty = -_LENGTH_PENALTY * (length - 2)
    pass_rate_avg  = avg(pass_rate) * _PASSRATE_WEIGHT  (쉬운 경로 선호)
    """
    edges = steps[1:]  # 첫 노드는 시작점 (edge 없음)
    if not edges:
        return 0.0
    base = sum(
        _RELATION_TYPE_WEIGHT.get(s.get("relation_type") or "", 0.4)
        * float(s.get("confidence") or 1.0)
        for s in edges
    ) / len(edges)
    length_penalty = -_LENGTH_PENALTY * max(0, len(steps) - 2)
    pass_rates = [pass_rate_map.get(s["cert_id"]) for s in steps]
    pass_rates = [p for p in pass_rates if p is not None]
    pass_bonus = (
        (sum(pass_rates) / len(pass_rates)) * _PASSRATE_WEIGHT
        if pass_rates else 0.0
    )
    return round(base + length_penalty + pass_bonus, 4)


def _build_paths_from(
    start_cert_id: str,
    max_depth: int = 4,
    max_paths: int = 5,
) -> list[dict]:
    """cert_to_cert DAG에서 start_cert_id → 하위(advancement) 방향 경로 탐색.

    반환 형식: [{path_score, length, start_cert_id/name, end_cert_id/name,
                 steps:[{cert_id, cert_name, relation_type, source}, ...]}, ...]

    ▸ 정렬: path_score 내림차순 → length 내림차순 (길고 신뢰도 높은 경로 우선).
    ▸ 점수: relation_type (prerequisite > recommended_prior > next_step)
           - 길이 페널티 + pass_rate 가산 (쉬운 경로 우대).
    """
    graph = _load_cert_graph()
    names = _load_cert_name_map()
    pass_rate_map = _load_pass_rate_map()
    results: list[list[dict]] = []

    def dfs(chain: list[dict]) -> None:
        if len(results) >= max_paths:
            return
        node = chain[-1]["cert_id"]
        edges = graph.get(node, ())
        if len(chain) > max_depth or not edges:
            if len(chain) > 1:
                results.append([dict(s) for s in chain])
            return
        visited = {s["cert_id"] for s in chain}
        extended = False
        for to_id, rel_type, source, conf in edges:
            if len(results) >= max_paths:
                break
            if to_id in visited:
                continue
            extended = True
            chain.append({
                "cert_id": to_id,
                "cert_name": names.get(to_id, to_id),
                "relation_type": rel_type,
                "source": source,
                "confidence": conf,
            })
            dfs(chain)
            chain.pop()
        if not extended and len(chain) > 1:
            results.append([dict(s) for s in chain])

    dfs([{
        "cert_id": start_cert_id,
        "cert_name": names.get(start_cert_id, start_cert_id),
        "relation_type": None,
        "source": None,
        "confidence": 1.0,
    }])

    scored = [
        (p, _path_score(p, pass_rate_map)) for p in results
    ]
    # 점수 내림차순 → 길이 내림차순 (tie-break)
    scored.sort(key=lambda t: (-t[1], -len(t[0])))
    return [
        {
            "path_score": score,
            "length": len(p),
            "start_cert_id": p[0]["cert_id"],
            "start_cert_name": p[0]["cert_name"],
            "end_cert_id": p[-1]["cert_id"],
            "end_cert_name": p[-1]["cert_name"],
            "steps": p,
        }
        for p, score in scored[:max_paths]
    ]


# ---------- 레벨 추론 ----------
def _cert_level(cand: dict, pass_rate: float | None = None) -> tuple[int, str]:
    """
    (sequence_score, effective_roadmap_stage_id) 반환.

    우선순위:
      1. cert_grade_tier (NCS 공식 체계, cert_master.csv 출처)
      2. avg_pass_rate (합격률 기반, 비기술자격에 적용) ← 주요 데이터 신호
      3. 자격증명 키워드 fallback (pass_rate 없을 때만)
    """
    tier = cand.get("cert_grade_tier", "")
    if tier and tier in _TIER_SEQUENCE:
        return _TIER_SEQUENCE[tier]

    # 비기술자격: 합격률 기반 (데이터 기반 primary)
    if pass_rate is not None:
        for min_rate, level, stage in _PASSRATE_STAGE_MAP:
            if pass_rate >= min_rate:
                return (level, stage)
        return (40, "roadmap_stage_0005")

    # 합격률 없음: 키워드 fallback
    name = cand.get("cert_name", "")
    for pattern, score, stage in _NONTECH_KEYWORD_RULES:
        if re.search(pattern, name):
            return (score, stage)
    return _NONTECH_DEFAULT


def _achievability(cand: dict, user_risk_id: str) -> str:
    """사용자 위험군 대비 자격증 접근 가능성."""
    rec = cand.get("recommended_risk_stages", [])
    if user_risk_id in rec:
        return "immediate"
    user_idx = _RISK_ORDER.index(user_risk_id) if user_risk_id in _RISK_ORDER else -1
    # rec에서 가장 가까운 위험군과의 거리 계산
    if not rec or user_idx < 0:
        return "long_term"
    min_dist = min(
        abs(user_idx - _RISK_ORDER.index(r))
        for r in rec if r in _RISK_ORDER
    )
    return _ACHIEVABILITY.get(min_dist, "long_term")


# ---------- 필터 ----------
def _tier_min_allows(c: dict, tier_min: int) -> bool:
    """기술자격만 tier_min 하한 적용. 비기술자격(tier_score=0)은 통과."""
    if tier_min <= 0:
        return True
    score = _TIER_SCORE.get(c.get("cert_grade_tier", ""), 0)
    if score == 0:
        return True  # 비기술자격은 pass_rate 로직으로 관리
    return score >= tier_min


def _filter_candidates(
    candidates: list[dict],
    risk_stage_id: str | None,
    domain_ids: list[str],
    job_ids: list[str],
    use_fallback: bool = True,
) -> tuple[list[dict], bool]:
    def _domain_job_match(c: dict) -> bool:
        if not domain_ids and not job_ids:
            return True
        domain_match = domain_ids and any(d in c.get("related_domains", []) for d in domain_ids)
        job_match = job_ids and any(j in c.get("related_jobs", []) for j in job_ids)
        return bool(domain_match or job_match)

    def _risk_match(c: dict, risk_id: str) -> bool:
        return risk_id in c.get("recommended_risk_stages", [])

    tier_min = _RISK_TIER_MIN.get(risk_stage_id or "", 0)

    results = [
        c for c in candidates
        if _domain_job_match(c)
        and (not risk_stage_id or _risk_match(c, risk_stage_id))
        and _tier_min_allows(c, tier_min)
    ]

    if not results and use_fallback and (domain_ids or job_ids):
        # 도메인/직무 조건만으로 전체 반환 (risk_stage 제약 해제)
        # risk_0005처럼 직접 매핑이 narrow한 도메인에서 발생.
        # tier_min은 fallback 에서도 유지 → risk_0001에 기능사 유입 차단.
        domain_only = [
            c for c in candidates
            if _domain_job_match(c) and _tier_min_allows(c, tier_min)
        ]
        return domain_only, True

    return results, False


# ---------- 도메인 resolver (P3: primary_domain fallback 정책) ----------
def _effective_domain(c: dict) -> str:
    """primary_domain 이 비어 있거나 placeholder 일 때 related_domains[0] 로 fallback.

    ▸ build_cert_candidates 의 taxonomy 게이트로 런타임에는 모두 유효한 domain_id가 들어오지만,
      방어적 계산을 위해 primary_domain 이 missing/unknown인 경우 related_domains 첫 값 사용.
    ▸ 둘 다 없으면 빈 문자열 — redundancy/필터 비교에서 skip 처리된다.
    """
    pd = (c.get("primary_domain") or "").strip()
    if pd and pd != "domain_unknown":
        return pd
    rd = c.get("related_domains") or []
    for d in rd:
        if d and d != "domain_unknown":
            return d
    return ""


# ---------- 보유 자격증 tier 기반 redundancy 계산 ----------
def _held_domain_max_tier(
    held_cert_ids: list[str],
    candidates: list[dict],
) -> dict[str, int]:
    """
    보유 자격증별 effective domain → 최고 tier_score 매핑.
    비기술자격(tier 빈값)은 비교 대상에서 제외.
    """
    cand_map = {c["cert_id"]: c for c in candidates}
    out: dict[str, int] = {}
    for cid in held_cert_ids:
        c = cand_map.get(cid)
        if not c:
            continue
        score = _TIER_SCORE.get(c.get("cert_grade_tier", ""), 0)
        if score == 0:
            continue
        domain = _effective_domain(c)
        if domain:
            out[domain] = max(out.get(domain, 0), score)
    return out


# ---------- 로드맵 조립 ----------
def _build_roadmap_sequence(
    candidates: list[dict],
    starting_roadmap_id: str,
    roadmap_stages: dict[str, dict],
    pass_rate_map: dict,
    user_risk_id: str,
    top_n: int,
    held_max_tier: dict[str, int] | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Returns:
      sequence: 순서형 평탄화 리스트 (step 1, 2, 3, ...)
      by_stage: stage별 그룹 리스트
    """
    starting_order = roadmap_stages.get(starting_roadmap_id, {}).get("order", 1)

    # 각 cert에 유효 roadmap_stage 할당
    # pass_rate를 먼저 조회해 _cert_level에 전달 → 합격률 기반 순서 도출
    enriched = []
    for c in candidates:
        pass_rate = pass_rate_map.get(c["cert_id"])
        level_score, eff_stage = _cert_level(c, pass_rate)
        eff_stage_info = roadmap_stages.get(eff_stage, {})
        eff_order = eff_stage_info.get("order", 2)
        # 시작 단계보다 낮은 stage는 시작 단계로 올림
        if eff_order < starting_order:
            eff_stage = starting_roadmap_id
            eff_stage_info = roadmap_stages.get(eff_stage, {})
        # is_redundant: 보유 자격증의 같은 domain 내 tier보다 낮은 기술자격
        cert_tier_score = _TIER_SCORE.get(c.get("cert_grade_tier", ""), 0)
        eff_domain = _effective_domain(c)
        domain_held_max = (held_max_tier or {}).get(eff_domain, 0)
        is_redundant = cert_tier_score > 0 and cert_tier_score < domain_held_max

        enriched.append({
            **c,
            "_level_score": level_score,
            "_eff_stage_id": eff_stage,
            "_eff_stage_info": eff_stage_info,
            "_pass_rate": pass_rate,
            "_achievability": _achievability(c, user_risk_id),
            "_is_redundant": is_redundant,
        })

    # 전공별 취득 현황 기반 인기 지수 (누적 취득자 수 → 로그 스케일 → 소수점 보정값)
    acqui_map = _load_cert_acqui_map()
    detail_map = _load_cert_detail_map()
    import math as _math
    for x in enriched:
        cnt = acqui_map.get(x["cert_name"], 0)
        x["_popularity_boost"] = _math.log1p(cnt) * 0.01 if cnt > 0 else 0.0
        # exam_frequency 접근성 가중치: 시험 기회가 많을수록 취업 급한 사용자에게 유리
        detail = detail_map.get(x.get("cert_id", ""), {})
        x["_freq_score"] = _exam_freq_score(detail.get("exam_frequency"))

    # 전체 오름차순 정렬 (sequence용):
    #   1순위 stage_order → 2순위 level_score → 3순위 인기+빈도 보정 → 4순위 pass_rate 높을수록
    enriched.sort(key=lambda x: (
        x["_eff_stage_info"].get("order", 2),
        x["_level_score"],
        -(x["_popularity_boost"] + x["_freq_score"]),
        -(x["_pass_rate"] or 0.0),
    ))

    # ── 순서형 flat 리스트 ──
    sequence: list[dict] = []
    for i, c in enumerate(enriched, 1):
        pr = c["_pass_rate"]
        bn_thr = _BOTTLENECK_TIER_THRESHOLD.get(c.get("cert_grade_tier", "") or "", _BOTTLENECK_THRESHOLD)
        is_bn = pr is not None and pr < bn_thr
        detail = detail_map.get(c.get("cert_id", ""), {})
        sequence.append({
            "step": i,
            "candidate_id": c["candidate_id"],
            "cert_id": c["cert_id"],
            "cert_name": c["cert_name"],
            "cert_grade_tier": c.get("cert_grade_tier", "") or "비기술자격",
            "roadmap_stage_id": c["_eff_stage_id"],
            "roadmap_stage_name": c["_eff_stage_info"].get("name", ""),
            "avg_pass_rate": round(pr, 1) if pr is not None else None,
            "written_avg_pass_rate": round(detail["written_avg_pass_rate"], 1) if detail.get("written_avg_pass_rate") is not None else None,
            "practical_avg_pass_rate": round(detail["practical_avg_pass_rate"], 1) if detail.get("practical_avg_pass_rate") is not None else None,
            "exam_frequency": detail.get("exam_frequency"),
            "exam_difficulty": detail.get("exam_difficulty"),
            "exam_fee_info": detail.get("exam_fee_info"),
            "is_bottleneck": is_bn,
            "bottleneck_note": (
                f"해당 단계에서 정체 위험이 높습니다 (합격률 {round(pr, 1)}%)" if is_bn else None
            ),
            "is_redundant": c["_is_redundant"],
            "achievability": c["_achievability"],
            "primary_domain": _effective_domain(c),
            "related_jobs": c.get("related_jobs", [])[:5],
            "text_for_dense": c.get("text_for_dense", ""),
        })

    # ── stage별 그룹 (top_n 제한) ──
    sorted_stages = sorted(
        [s for s in roadmap_stages.values() if s["order"] >= starting_order],
        key=lambda s: s["order"],
    )
    stage_groups: dict[str, list] = {s["id"]: [] for s in sorted_stages}
    for c in enriched:
        sid = c["_eff_stage_id"]
        if sid in stage_groups:
            stage_groups[sid].append(c)

    step_map = {s["cert_id"]: s["step"] for s in sequence}

    by_stage: list[dict] = []
    for stage_info in sorted_stages:
        sid = stage_info["id"]
        certs_here = sorted(
            stage_groups.get(sid, []),
            key=lambda x: (x["_level_score"], -(x["_pass_rate"] or 0.0)),
        )[:top_n]
        by_stage.append({
            "stage": stage_info,
            "is_starting_point": sid == starting_roadmap_id,
            "recommended_certs": [
                {
                    "step": step_map.get(c["cert_id"]),
                    "cert_id": c["cert_id"],
                    "cert_name": c["cert_name"],
                    "cert_grade_tier": c.get("cert_grade_tier", "") or "비기술자격",
                    "avg_pass_rate": round(c["_pass_rate"], 1) if c["_pass_rate"] is not None else None,
                    "is_bottleneck": (c["_pass_rate"] is not None and c["_pass_rate"] < _BOTTLENECK_TIER_THRESHOLD.get(c.get("cert_grade_tier", "") or "", _BOTTLENECK_THRESHOLD)),
                    "bottleneck_note": (
                        f"해당 단계에서 정체 위험이 높습니다 (합격률 {round(c['_pass_rate'], 1)}%)"
                        if c["_pass_rate"] is not None and c["_pass_rate"] < _BOTTLENECK_TIER_THRESHOLD.get(c.get("cert_grade_tier", "") or "", _BOTTLENECK_THRESHOLD) else None
                    ),
                    "is_redundant": c["_is_redundant"],
                    "achievability": c["_achievability"],
                    "related_jobs": c.get("related_jobs", [])[:5],
                }
                for c in certs_here
            ],
        })

    return sequence, by_stage


# ---------- 동적 진입점 헬퍼 ----------
def _resolve_dynamic_entry(
    held_cert_ids: list[str],
    roadmap_stages: dict[str, dict],
    base_starting_id: str,
) -> tuple[str, list[str]]:
    """
    held_cert_ids 기반으로 starting_roadmap_id 동적 조정.
    Returns:
      (adjusted_starting_roadmap_id, held_cert_ids_to_exclude)
    """
    if not held_cert_ids:
        return base_starting_id, []

    cert_to_roadmap = _load_cert_to_roadmap_map()
    held_orders = [
        roadmap_stages.get(cert_to_roadmap.get(cid, ""), {}).get("order", 0)
        for cid in held_cert_ids
    ]
    max_held_order = max((o for o in held_orders if o > 0), default=0)
    if not max_held_order:
        return base_starting_id, held_cert_ids

    base_order = roadmap_stages.get(base_starting_id, {}).get("order", 2)
    if max_held_order < base_order:
        return base_starting_id, held_cert_ids

    # 보유 자격증 최고 단계 다음 stage로 진입점 전진
    sorted_stages = sorted(roadmap_stages.values(), key=lambda s: s["order"])
    advanced_id = next(
        (s["id"] for s in sorted_stages if s["order"] > max_held_order),
        base_starting_id,
    )
    return advanced_id, held_cert_ids


# ---------- 공개 API ----------
def recommendations(body: dict[str, Any]) -> dict:
    """
    POST /api/v1/recommendations
    body:
      risk_stage_id: str
      domain_ids: list[str]
      domain_names: list[str]     ← 이름으로도 가능 (e.g. "데이터/AI")
      major_name: str             ← 전공명 → domain 자동 추가
      job_ids: list[str]
      held_cert_ids: list[str]    ← 보유 자격증 → 동적 진입점 조정 + 결과에서 제외
      top_n_per_stage: int        (default 5)
    """
    risk_stage_id = body.get("risk_stage_id") or body.get("risk_stage")
    domain_ids: list[str] = list(body.get("domain_ids") or [])
    job_ids: list[str]    = list(body.get("job_ids") or [])
    held_cert_ids: list[str] = list(body.get("held_cert_ids") or [])
    top_n = int(body.get("top_n_per_stage") or 5)
    # roadmap_sequence 최대 반환 건수 — 기본 100, 클라이언트가 줄일 수 있음
    sequence_limit = int(body.get("sequence_limit") or 100)

    if body.get("domain_names"):
        domain_map = _load_domain_map()
        for name in body["domain_names"]:
            if did := domain_map.get(name.strip().lower()):
                if did not in domain_ids:
                    domain_ids.append(did)

    if body.get("major_name"):
        major_domain_map = _load_major_to_domain_map()
        norm_key = body["major_name"].strip().lower()
        # normalized_key 먼저, 없으면 그대로 검색
        if did := major_domain_map.get(norm_key):
            if did not in domain_ids:
                domain_ids.append(did)

    # R4-6: job_ids 단독 쿼리 시 job_to_domain.csv로 domain_ids 보완
    # domain_ids가 비어 있을 때만 확장 — 명시적 domain_ids 지정은 그대로 유지.
    if job_ids and not domain_ids:
        job_domain_map = _load_job_to_domain_map()
        for jid in job_ids:
            for did in job_domain_map.get(jid, []):
                if did not in domain_ids:
                    domain_ids.append(did)

    if not risk_stage_id and not domain_ids and not job_ids:
        return err_envelope(
            "MISSING_REQUIRED_FIELD",
            "risk_stage_id 또는 domain_ids / job_ids 중 하나 이상 필요합니다.",
        )

    candidates      = _load_candidates()
    pass_rate_map   = _load_pass_rate_map()
    risk_stages     = _load_risk_stages()
    roadmap_stages  = _load_roadmap_stages()
    risk_to_roadmap = _load_risk_to_roadmap()

    if not candidates:
        return err_envelope(
            "DATA_NOT_READY",
            "cert_candidates.jsonl을 찾을 수 없습니다. scripts/build_cert_candidates.py를 먼저 실행하세요.",
        )

    filtered, used_fallback = _filter_candidates(
        candidates, risk_stage_id, domain_ids, job_ids
    )

    # 보유 자격증 제외 + redundancy 계산용 held tier 맵
    held_set = set(held_cert_ids)
    held_max_tier = _held_domain_max_tier(held_cert_ids, candidates)
    if held_set:
        filtered = [c for c in filtered if c["cert_id"] not in held_set]

    base_starting_id = risk_to_roadmap.get(risk_stage_id or "", "roadmap_stage_0002")
    starting_roadmap_id, _ = _resolve_dynamic_entry(
        held_cert_ids, roadmap_stages, base_starting_id
    )
    entry_advanced = (starting_roadmap_id != base_starting_id)

    sequence, by_stage = _build_roadmap_sequence(
        filtered, starting_roadmap_id, roadmap_stages,
        pass_rate_map, risk_stage_id or "", top_n,
        held_max_tier=held_max_tier,
    )

    # ── cert_paths: DAG 기반 자격증 경로 ──
    # held_cert_ids 제공 시: 보유 자격증 각각에서 상승 경로
    # 미제공 시: 시퀀스 상위 10개 중 outgoing 엣지가 있는 cert에서 경로
    # 전체 수집 후 path_score 내림차순 전역 정렬.
    cert_paths: list[dict] = []
    graph = _load_cert_graph()
    if held_cert_ids:
        for cid in held_cert_ids:
            paths = _build_paths_from(cid, max_depth=4, max_paths=3)
            if paths:
                cert_paths.extend(paths)
    else:
        seen_starts: set[str] = set()
        for step in sequence[:10]:
            cid = step["cert_id"]
            if cid in seen_starts or cid not in graph:
                continue
            seen_starts.add(cid)
            paths = _build_paths_from(cid, max_depth=4, max_paths=2)
            if paths:
                cert_paths.extend(paths)
    # 전역 정렬: path_score 내림차순 → length 내림차순
    cert_paths.sort(key=lambda p: (-p.get("path_score", 0.0), -p.get("length", 0)))
    cert_paths = cert_paths[:5]

    risk_info = risk_stages.get(risk_stage_id) if risk_stage_id else None

    return ok_envelope({
        "risk_stage": risk_info or None,
        "starting_roadmap_stage": roadmap_stages.get(starting_roadmap_id),
        "query": {
            "risk_stage_id": risk_stage_id,
            "domain_ids": domain_ids,
            "job_ids": job_ids,
            "held_cert_ids": held_cert_ids,
            "major_name": body.get("major_name"),
        },
        "entry_advanced": entry_advanced,
        "fallback_used": used_fallback,
        "fallback_note": (
            "선택 도메인에 해당 위험군 직접 매핑 자격증이 없어 전체 도메인 자격증을 로드맵 순서로 제시합니다."
            if used_fallback else None
        ),
        "roadmap_sequence": sequence[:sequence_limit],
        "roadmap_by_stage": by_stage,
        "cert_paths": cert_paths,
        "total_certs_in_roadmap": len(sequence),
        "sequence_limit_applied": len(sequence) > sequence_limit,
    })


def recommendations_placeholder(body: dict[str, Any]) -> dict:
    return recommendations(body)


def recommendations_evidence(body: dict[str, Any], settings: Settings) -> dict:
    return retrieval_service.search_evidence(body, settings)


# ---------- P1: 다운스트림 증분 소비 ----------
def _invalidate_caches() -> None:
    """lru_cache 기반 로더들을 전부 무효화한다."""
    for fn in (
        _load_candidates,
        _load_pass_rate_map,
        _load_risk_stages,
        _load_roadmap_stages,
        _load_risk_to_roadmap,
        _load_domain_map,
        _load_major_to_domain_map,
        _load_job_to_domain_map,
        _load_cert_to_roadmap_map,
        _load_cert_name_map,
        _load_cert_graph,
        _load_cert_acqui_map,
    ):
        fn.cache_clear()


def reload_from_changed_jsonl() -> dict:
    """`.build_manifest_diff.json` + `cert_candidates_changed.jsonl` 를 소비한다.

    빌드 파이프라인이 생성한 증분 파일을 읽어 현재 서비스의 캐시를 무효화하고,
    변경 candidate ID 목록을 호출자에게 반환한다. (downstream 임베딩/인덱스 빌더가
    이 목록만 처리할 수 있도록 hook 을 제공.)

    Returns:
      {
        "status": "reloaded" | "no_diff",
        "added":   [candidate_id, ...],
        "updated": [candidate_id, ...],
        "removed": [candidate_id, ...],
        "changed_ids": [...],           # added + updated
        "previous_generated_at": str|null,
        "generated_at": str|null,
      }
    """
    if not _CANDIDATES_DIFF_JSON.exists():
        return {"status": "no_diff", "changed_ids": []}

    with _CANDIDATES_DIFF_JSON.open(encoding="utf-8") as f:
        diff = json.load(f)

    added   = list(diff.get("added") or [])
    updated = list(diff.get("updated") or [])
    removed = list(diff.get("removed") or [])
    changed_ids = added + updated

    # 캐시 무효화 → 다음 호출 시 jsonl 재로딩
    _invalidate_caches()

    return {
        "status": "reloaded",
        "added":   added,
        "updated": updated,
        "removed": removed,
        "changed_ids": changed_ids,
        "previous_generated_at": diff.get("previous_generated_at"),
        "generated_at": diff.get("generated_at"),
    }


def iter_changed_candidates() -> list[dict]:
    """`cert_candidates_changed.jsonl` 의 row 를 리스트로 반환 (다운스트림 임베딩/인덱스 빌더용).

    파일이 없거나 비어 있으면 빈 리스트. reload_from_changed_jsonl 과 함께 쓴다.
    """
    if not _CANDIDATES_CHANGED_JSONL.exists():
        return []
    out: list[dict] = []
    with _CANDIDATES_CHANGED_JSONL.open(encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                out.append(json.loads(s))
    return out
