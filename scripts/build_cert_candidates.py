# Content Hash: SHA256:TBD
# Role: Phase 4 — cert_candidates.csv / .jsonl 생성
# 입력: data/processed/master/, data/canonical/relations/
# 출력: data/canonical/candidates/cert_candidates.csv, .jsonl
#       data/canonical/validation/candidates_taxonomy.json (DATA_SCHEMA.md §9.1.1 게이트 결과)
# 증분 규칙: content_hash 기반 — 변경 row만 재생성 가능 (전체 재생성 시 updated_at 비교)
#
# recommended_risk_stages 정책 (relations/FOLDER.md §P6-1, 2026-07-05 개정):
#   위험군은 risk_0001(고립위험청년, 가장 경미) ~ risk_0004(은둔청년, 가장 심각) 4단계다.
#   (구 정책은 "risk_0001=취업 안정권"이라는 5단계 체계 가정으로 설계돼, risk_0001·0002 사용자에게
#    기능사 등 접근 가능한 자격증을 원천 배제했다 — LLM-judge recall 평가로 발견된 회귀, DEV_LOG 2026-07-05.)
#   새 원칙: 아주 어려운 자격증(기술사·기능장, 합격률 <10%)만 활동제한형·은둔청년(0003·0004)에서 제외하고,
#   나머지는 전 단계(0001~0004)에 개방한다. 같은 위험군 안의 난이도 우선순위는 이 필드가 아니라
#   recommendation_service._fit_score의 difficulty_fit(FEATURE_SPEC.md F-03 §3.1)이 소프트하게 처리한다.
#   risk_0005(구 은둔군)는 백엔드 비활성 보존 상태라 신규 생성 시 더 이상 포함하지 않는다.
#   [기술자격 tier 기반]
#     1_기능사   → [0001, 0002, 0003, 0004]   (전 단계 개방 — 진입 접근성)
#     2_산업기사 → [0001, 0002, 0003, 0004]
#     3_기사     → [0001, 0002, 0003, 0004]
#     4_기술사   → [0001, 0002]                (고난도 — 활동제한형·은둔청년 제외)
#     5_기능장   → [0001, 0002]
#   [비기술자격 — 합격률 3yr 평균 기반]
#     ≥50%      → [0001, 0002, 0003, 0004]
#     30~50%    → [0001, 0002, 0003, 0004]
#     10~30%    → [0001, 0002, 0003, 0004]
#     <10%      → [0001, 0002]                 (매우 어려움 — 활동제한형·은둔청년 제외)
#     합격률 없음 → [0001, 0002, 0003, 0004]  (기본값)

from __future__ import annotations

import argparse
import os
import json
import hashlib
import sys
from datetime import datetime

import pandas as pd

# ---------- 경로 설정 (이 파일 기준 상위 디렉토리로 해석) ----------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))
MASTER_DIR  = os.path.join(BASE_DIR, "data", "processed", "master")
RELATION_DIR = os.path.join(BASE_DIR, "data", "canonical", "relations")
OUT_DIR     = os.path.join(BASE_DIR, "data", "canonical", "candidates")
VALIDATION_DIR = os.path.join(BASE_DIR, "data", "canonical", "validation")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(VALIDATION_DIR, exist_ok=True)

# ---------- 상수 ----------
# cert_grade_tier → 추천 대상 위험군 (§P6-1 정책, 2026-07-05 개정)
# 아주 어려운 등급(기술사·기능장)만 활동제한형·은둔청년(0003·0004)에서 제외하고 나머지는 전 단계 개방.
_ALL_ACTIVE_STAGES = ["risk_0001", "risk_0002", "risk_0003", "risk_0004"]
TIER_TO_RISK_STAGES: dict[str, list[str]] = {
    "1_기능사":   list(_ALL_ACTIVE_STAGES),
    "2_산업기사": list(_ALL_ACTIVE_STAGES),
    "3_기사":     list(_ALL_ACTIVE_STAGES),
    "4_기술사":   ["risk_0001", "risk_0002"],
    "5_기능장":   ["risk_0001", "risk_0002"],
}

# 비기술자격(tier 없음) — 합격률 기반. (min_pass_rate_inclusive, risk_stages)
# <10%(매우 어려움)만 활동제한형·은둔청년에서 제외, 나머지는 전 단계 개방.
PASSRATE_TO_RISK_STAGES: list[tuple[float, list[str]]] = [
    (50.0, list(_ALL_ACTIVE_STAGES)),
    (30.0, list(_ALL_ACTIVE_STAGES)),
    (10.0, list(_ALL_ACTIVE_STAGES)),
    (0.0,  ["risk_0001", "risk_0002"]),
]
# 합격률도 tier도 없는 경우 기본값
DEFAULT_NONTECH_RISK_STAGES: list[str] = list(_ALL_ACTIVE_STAGES)

LIST_COLS = [
    "aliases", "related_domains", "related_jobs", "related_majors",
    "recommended_risk_stages", "roadmap_stages", "source_ids",
]


# ---------- 유틸 ----------
def _str(val) -> str:
    s = str(val).strip()
    return "" if s in ("nan", "None", "none") else s


def content_hash(d: dict) -> str:
    """updated_at 제외한 내용 기반 SHA256 (변경 감지용)."""
    stable = {k: v for k, v in d.items() if k not in ("content_hash", "updated_at")}
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


# ---------- 로드 ----------
def _load_csv(path: str, required: bool = True) -> pd.DataFrame | None:
    if os.path.exists(path):
        return pd.read_csv(path, encoding="utf-8-sig")
    if required:
        raise FileNotFoundError(path)
    return None


def load_lookups() -> dict:
    """모든 관계 파일을 cert_id 기준 dict로 반환."""
    df_cert    = _load_csv(os.path.join(MASTER_DIR, "cert_master.csv"))
    df_alias   = _load_csv(os.path.join(MASTER_DIR, "cert_alias.csv"), required=False)
    df_domain  = _load_csv(os.path.join(RELATION_DIR, "cert_domain_mapping.csv"))
    df_job_map = _load_csv(os.path.join(RELATION_DIR, "cert_job_mapping.csv"), required=False)
    df_roadmap = _load_csv(os.path.join(RELATION_DIR, "cert_to_roadmap_stage.csv"))
    df_cmm     = _load_csv(os.path.join(RELATION_DIR, "cert_major_mapping.csv"), required=False)
    df_jm      = _load_csv(os.path.join(MASTER_DIR, "job_master.csv"), required=False)
    df_mm      = _load_csv(os.path.join(MASTER_DIR, "major_master.csv"), required=False)

    alias_map = (
        df_alias.groupby("cert_id")["alias"].apply(list).to_dict()
        if df_alias is not None else {}
    )

    # is_primary 컬럼: True/False 또는 "True"/"False" 혼재 처리
    df_domain["is_primary_bool"] = df_domain["is_primary"].astype(str).str.lower() == "true"
    primary_map = (
        df_domain[df_domain["is_primary_bool"]]
        .set_index("cert_id")["domain_sub_label_id"]
        .to_dict()
    )
    fallback_primary_map = df_domain.groupby("cert_id")["domain_sub_label_id"].first().to_dict()
    related_domains_map  = df_domain.groupby("cert_id")["domain_sub_label_id"].apply(list).to_dict()

    related_jobs_map = (
        df_job_map.groupby("cert_id")["job_role_id"].apply(list).to_dict()
        if df_job_map is not None else {}
    )
    job_name_lookup = (
        df_jm.set_index("job_role_id")["job_role_name"].to_dict()
        if df_jm is not None else {}
    )

    roadmap_map = df_roadmap.groupby("cert_id")["roadmap_stage_id"].apply(list).to_dict()

    if df_cmm is not None and df_mm is not None:
        major_name_map = df_mm.set_index("major_id")["major_name"].to_dict()
        cert_majors = (
            df_cmm.groupby("cert_id")["major_id"]
            .apply(lambda ids: [major_name_map.get(m, m) for m in ids])
            .to_dict()
        )
    else:
        cert_majors = {}

    return {
        "df_cert": df_cert,
        "alias_map": alias_map,
        "primary_map": primary_map,
        "fallback_primary_map": fallback_primary_map,
        "related_domains_map": related_domains_map,
        "related_jobs_map": related_jobs_map,
        "job_name_lookup": job_name_lookup,
        "roadmap_map": roadmap_map,
        "cert_majors": cert_majors,
    }


def _risk_stages_for(tier: str, pass_rate: float | None) -> list[str]:
    """§P6-1 정책에 따라 recommended_risk_stages 계산.
    1) tier 있으면 TIER_TO_RISK_STAGES 사용
    2) tier 없고 pass_rate 있으면 PASSRATE_TO_RISK_STAGES match-first
    3) 둘 다 없으면 DEFAULT_NONTECH_RISK_STAGES
    """
    if tier and tier in TIER_TO_RISK_STAGES:
        return list(TIER_TO_RISK_STAGES[tier])
    if pass_rate is not None:
        for min_rate, stages in PASSRATE_TO_RISK_STAGES:
            if pass_rate >= min_rate:
                return list(stages)
    return list(DEFAULT_NONTECH_RISK_STAGES)


def _parse_pass_rate(val) -> float | None:
    s = _str(val)
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ---------- 행 생성 ----------
def build_candidate(row: pd.Series, lk: dict, updated_at: str) -> dict:
    cert_id   = str(row["cert_id"])
    cert_name = _str(row["cert_name"])
    tier      = _str(row.get("cert_grade_tier", ""))
    issuer    = _str(row.get("issuer", "")) or "한국산업인력공단"

    p_domain  = lk["primary_map"].get(cert_id) or lk["fallback_primary_map"].get(cert_id, "domain_unknown")
    r_domains = lk["related_domains_map"].get(cert_id, [p_domain])
    r_job_ids = lk["related_jobs_map"].get(cert_id, [])
    r_job_names = [lk["job_name_lookup"].get(j, j) for j in r_job_ids]
    r_majors  = lk["cert_majors"].get(cert_id, [])
    r_stages  = lk["roadmap_map"].get(cert_id, [])
    pass_rate = _parse_pass_rate(row.get("avg_pass_rate_3yr", ""))
    rec_risk  = _risk_stages_for(tier, pass_rate)
    aliases   = lk["alias_map"].get(cert_id, [])

    # text_for_dense: 의미 검색용 — 자격증 소개 + 직무/학과 컨텍스트
    # (RAG indexing guide: 단일 chunk가 독립적으로 검색 가능하도록 충분한 컨텍스트 포함)
    parts = [f"{cert_name} ({issuer})."]
    if tier:
        parts.append(f"등급: {tier}.")
    cert_type = _str(row.get("cert_type", ""))
    if cert_type:
        parts.append(f"자격 유형: {cert_type}.")
    if r_job_names:
        parts.append(f"관련 직무: {', '.join(r_job_names[:10])}.")  # 최대 10개
    if r_majors:
        parts.append(f"관련 학과: {', '.join(r_majors[:10])}.")
    diff = _str(row.get("exam_difficulty", ""))
    if diff:
        parts.append(f"시험 난이도: {diff}.")
    subj = _str(row.get("exam_subject_info", ""))
    if subj:
        parts.append(f"시험 과목: {subj}.")
    freq = _str(row.get("exam_frequency", ""))
    if freq:
        parts.append(f"연간 검정 횟수: {freq}.")
    avg_pass = _str(row.get("avg_pass_rate_3yr", ""))
    if avg_pass:
        parts.append(f"3년 평균 합격률: {avg_pass}%.")

    # text_for_sparse: exact match 보강용 — 자격증명 변형 + 직무명 + 학과명
    # (RAG indexing guide: text_for_sparse는 BM25 키워드 검색 활성화 시 사용)
    sparse_parts = [cert_name] + aliases + r_job_names + r_majors
    sparse_text = " ".join(p for p in sparse_parts if p)

    row_data = {
        "row_type": "certificate_candidate",
        "candidate_id": f"cand_{cert_id}",
        "cert_id": cert_id,
        "cert_name": cert_name,
        "aliases": aliases,
        "issuer": issuer,
        "primary_domain": p_domain,
        "related_domains": r_domains,
        "related_jobs": r_job_ids,
        "related_majors": r_majors,
        "recommended_risk_stages": rec_risk,
        "roadmap_stages": r_stages,
        "cert_grade_tier": tier,
        "text_for_dense": " ".join(parts),
        "text_for_sparse": sparse_text,
        "valid_from": None,
        "valid_to": None,
        "source_ids": [_str(row.get("source", "master")) or "master"],
        "quality_flags": {},
        "updated_at": updated_at,
    }
    row_data["content_hash"] = content_hash(row_data)
    return row_data


# ---------- taxonomy 게이트 (DATA_SCHEMA.md §9.1.1) ----------
def load_taxonomy_ids() -> tuple[set[str], set[str]]:
    """master CSV에서 허용 ID 집합을 로드한다.

    - domain_sub_label_id: data/processed/master/domain_master.csv
    - job_role_id:         data/processed/master/job_master.csv
    """
    df_domain = _load_csv(os.path.join(MASTER_DIR, "domain_master.csv"))
    df_job    = _load_csv(os.path.join(MASTER_DIR, "job_master.csv"), required=False)
    domain_ids = set(df_domain["domain_sub_label_id"].astype(str).tolist())
    job_ids = (
        set(df_job["job_role_id"].astype(str).tolist())
        if df_job is not None else set()
    )
    return domain_ids, job_ids


def validate_taxonomy(
    candidates: list[dict],
    domain_ids: set[str],
    job_ids: set[str],
) -> tuple[list[dict], list[dict]]:
    """candidate row를 master CSV ID 집합에 대해 검증한다.

    returns (valid_rows, violations) — violations 원소는 candidate_id / 위반 필드 / 위반 값.
    """
    valid: list[dict] = []
    violations: list[dict] = []
    for c in candidates:
        bad_fields: dict[str, list[str]] = {}
        if c["primary_domain"] not in domain_ids:
            bad_fields["primary_domain"] = [c["primary_domain"]]
        bad_related = [d for d in c["related_domains"] if d not in domain_ids]
        if bad_related:
            bad_fields["related_domains"] = bad_related
        bad_jobs = [j for j in c["related_jobs"] if j not in job_ids]
        if bad_jobs:
            bad_fields["related_jobs"] = bad_jobs
        if bad_fields:
            violations.append({
                "candidate_id": c["candidate_id"],
                "cert_id": c["cert_id"],
                "cert_name": c["cert_name"],
                "violations": bad_fields,
            })
        else:
            valid.append(c)
    return valid, violations


# ---------- build manifest (HASH_INCREMENTAL_BUILD_GUIDE.md §7.6/§8.3) ----------
BUILD_MANIFEST_NAME       = ".build_manifest.json"
BUILD_MANIFEST_DIFF_NAME  = ".build_manifest_diff.json"
CHANGED_JSONL_NAME        = "cert_candidates_changed.jsonl"


def load_build_manifest(path: str) -> dict[str, str]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return dict(data.get("candidates", {}))


def save_build_manifest(path: str, candidates: list[dict]) -> None:
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "candidates": {c["candidate_id"]: c["content_hash"] for c in candidates},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def diff_build_manifest(
    previous: dict[str, str],
    candidates: list[dict],
) -> dict[str, list[str]]:
    current = {c["candidate_id"]: c["content_hash"] for c in candidates}
    added    = sorted(set(current) - set(previous))
    removed  = sorted(set(previous) - set(current))
    updated  = sorted(k for k in current if k in previous and current[k] != previous[k])
    unchanged = sorted(k for k in current if k in previous and current[k] == previous[k])
    return {
        "added": added,
        "removed": removed,
        "updated": updated,
        "unchanged": unchanged,
    }


def save_build_manifest_diff(
    path: str,
    diff: dict[str, list[str]],
    previous_generated_at: str | None,
) -> None:
    """다운스트림 인덱스 소비용 diff 아티팩트.
    added/updated/removed 목록만 기록 (unchanged 제외). 매 실행마다 덮어쓴다."""
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "previous_generated_at": previous_generated_at,
        "counts": {k: len(v) for k, v in diff.items()},
        "added":   diff["added"],
        "updated": diff["updated"],
        "removed": diff["removed"],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_changed_jsonl(
    path: str,
    candidates: list[dict],
    changed_ids: set[str],
) -> int:
    """added + updated candidate_id 에 해당하는 행만 JSONL 로 기록.
    다운스트림(임베딩·인덱스 빌더)이 이 파일만 읽어 증분 반영하도록 구성."""
    written = 0
    with open(path, "w", encoding="utf-8") as f:
        for c in candidates:
            if c["candidate_id"] in changed_ids:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                written += 1
    return written


def _read_previous_manifest_generated_at(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("generated_at")
    except (OSError, json.JSONDecodeError):
        return None


def write_validation_report(
    violations: list[dict],
    total: int,
    path: str,
) -> None:
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "total_candidates": total,
        "violation_count": len(violations),
        "violations": violations,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


# ---------- 저장 ----------
def save_csv(candidates: list[dict], path: str) -> None:
    df = pd.DataFrame(candidates)
    for col in LIST_COLS:
        df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False))
    df["quality_flags"] = df["quality_flags"].apply(lambda x: json.dumps(x))
    df.to_csv(path, index=False, encoding="utf-8-sig")


def save_jsonl(candidates: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


# ---------- 메인 ----------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cert_candidates 빌드 + taxonomy 게이트")
    parser.add_argument(
        "--allow-violations",
        action="store_true",
        help="DATA_SCHEMA.md §9.1.1 taxonomy 위반이 있어도 빌드를 계속한다 (기본: 실패).",
    )
    args = parser.parse_args(argv)

    print("Phase 4: Candidate Generation 시작")

    lk = load_lookups()
    df_cert = lk["df_cert"]

    # is_active 필터 — 비활성 자격증 제외
    if "is_active" in df_cert.columns:
        before = len(df_cert)
        df_cert = df_cert[df_cert["is_active"].astype(str).str.lower() != "false"]
        skipped = before - len(df_cert)
        if skipped:
            print(f"  is_active=False {skipped}개 제외")

    updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    candidates = [build_candidate(row, lk, updated_at) for _, row in df_cert.iterrows()]

    # taxonomy 게이트 (DATA_SCHEMA.md §9.1.1) — master CSV ID 기준 검증
    domain_ids, job_ids = load_taxonomy_ids()
    valid_candidates, violations = validate_taxonomy(candidates, domain_ids, job_ids)
    validation_path = os.path.join(VALIDATION_DIR, "candidates_taxonomy.json")
    write_validation_report(violations, total=len(candidates), path=validation_path)

    if violations:
        print(
            f"  taxonomy 위반 {len(violations)}개 감지 "
            f"(domain_ids={len(domain_ids)}, job_ids={len(job_ids)})"
        )
        print(f"  위반 리포트: {validation_path}")
        if not args.allow_violations:
            print(
                "  --allow-violations 플래그 없이 위반이 존재하여 빌드를 중단한다. "
                "DATA_SCHEMA.md §9.1.1 참조."
            )
            return 1

    out_csv   = os.path.join(OUT_DIR, "cert_candidates.csv")
    out_jsonl = os.path.join(OUT_DIR, "cert_candidates.jsonl")
    build_manifest_path = os.path.join(OUT_DIR, BUILD_MANIFEST_NAME)
    diff_path           = os.path.join(OUT_DIR, BUILD_MANIFEST_DIFF_NAME)
    changed_path        = os.path.join(OUT_DIR, CHANGED_JSONL_NAME)

    # row-level 증분 diff (HASH_INCREMENTAL_BUILD_GUIDE.md §8.3) — content_hash 비교
    prev_manifest = load_build_manifest(build_manifest_path)
    prev_generated_at = _read_previous_manifest_generated_at(build_manifest_path)
    diff = diff_build_manifest(prev_manifest, valid_candidates)
    changed_ids: set[str] = set(diff["added"]) | set(diff["updated"])

    save_csv(valid_candidates, out_csv)
    save_jsonl(valid_candidates, out_jsonl)
    save_build_manifest(build_manifest_path, valid_candidates)
    save_build_manifest_diff(diff_path, diff, prev_generated_at)
    changed_written = save_changed_jsonl(changed_path, valid_candidates, changed_ids)

    # 품질 요약
    no_job    = sum(1 for c in valid_candidates if not c["related_jobs"])
    print(f"생성 완료: {len(valid_candidates)}행 (위반 제외)")
    print(f"  related_jobs 없음:     {no_job}개 (domain_0028 언어/속기 등 정상)")
    print(
        "  증분 diff: "
        f"added={len(diff['added'])} "
        f"updated={len(diff['updated'])} "
        f"removed={len(diff['removed'])} "
        f"unchanged={len(diff['unchanged'])}"
    )
    print(f"  출력: {out_csv}")
    print(f"  출력: {out_jsonl}")
    print(f"  검증: {validation_path}")
    print(f"  manifest: {build_manifest_path}")
    print(f"  diff:     {diff_path}")
    print(f"  changed:  {changed_path} ({changed_written}행)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
