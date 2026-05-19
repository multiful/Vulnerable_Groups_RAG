# File: build_frontend_data.py
# Last Updated: 2026-05-19
# Content Hash: SHA256:TBD
# Role: data/canonical/candidates/cert_candidates.jsonl → frontend/public/data/cert_candidates.json
#       FE에서 쓰지 않는 무거운 필드(text_for_dense, text_for_sparse 등) 제거 + 합격률 pre-extract.
#       1번 병목(FE 초기 페이로드 크기) 해결용.
#
# 실행:
#   python scripts/build_frontend_data.py
#
# 정책:
#   - text_for_dense / text_for_sparse 제거 (FE 미사용)
#   - 합격률·검정 횟수는 explicit 필드(avg_pass_rate_3yr, exam_sessions_per_year)로 추출
#   - written_avg_pass_rate / practical_avg_pass_rate → cert_master.csv 보충
#   - acq_trend / acq_recent / acq_yoy_pct → 전공별 취득 현황_rows.csv 보충
#   - content_hash, source_ids, quality_flags, valid_from/to, updated_at 등 운영성 필드 제거
#   - FE 표시·필터링에 필요한 필드만 유지
#   - related_domains: data/canonical/relations/domain_adjacency.csv의 keyword 규칙으로
#     교차 도메인 확장 (8개 클러스터: IT/의료/관광/디자인/금융/기계/환경 등) canonical data 불변
#
# 증분 빌드 규칙(CLAUDE.md §12): jsonl content_hash 동일하면 재생성 스킵 가능
#   (현재 구현: 매번 전체 재생성. content_hash 비교는 후속 최적화 대상)

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_JSONL = _PROJECT_ROOT / "data/canonical/candidates/cert_candidates.jsonl"
_OUT = _PROJECT_ROOT / "frontend/public/data/cert_candidates.json"
_CERT_MASTER_CSV = _PROJECT_ROOT / "data/raw/csv/cert_master.csv"
_ACQUI_TREND_CSV = _PROJECT_ROOT / "data/raw/csv/전공별 취득 현황_rows.csv"
_CERT_DOMAIN_CSV = _PROJECT_ROOT / "data/canonical/relations/cert_domain_mapping.csv"
_DOMAIN_ADJACENCY_CSV = _PROJECT_ROOT / "data/canonical/relations/domain_adjacency.csv"

# text_for_dense에서 추출할 패턴들
_PASS_RATE_RE = re.compile(r"3년 평균 합격률:\s*([\d.]+)\s*%")
_SESSIONS_RE = re.compile(r"연간 검정 횟수:\s*(.+?)\.")

# FE가 실제로 쓰는 필드 (이 외엔 모두 제거)
_KEEP_FIELDS = {
    "candidate_id",
    "cert_id",
    "cert_name",
    "aliases",
    "issuer",
    "primary_domain",
    "related_domains",
    "related_jobs",
    "related_majors",
    "recommended_risk_stages",
    "roadmap_stages",
    "cert_grade_tier",
    "exam_sessions_per_year",
    # explicit 추가:
    "avg_pass_rate_3yr",
}


def _extract_pass_rate(text: str) -> float | None:
    if not text:
        return None
    m = _PASS_RATE_RE.search(text)
    return float(m.group(1)) if m else None


def _extract_sessions(text: str) -> int | None:
    if not text:
        return None
    m = _SESSIONS_RE.search(text)
    if not m:
        return None
    val = m.group(1).strip()
    if "상시" in val:
        return 0
    num_m = re.search(r"(\d+)", val)
    return int(num_m.group(1)) if num_m else None


def _load_cert_master_rates() -> dict[str, dict]:
    """cert_name → {written_avg_pass_rate, practical_avg_pass_rate}"""
    out: dict[str, dict] = {}
    if not _CERT_MASTER_CSV.exists():
        return out
    try:
        with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = row.get("cert_name", "").strip()
                if not name:
                    continue
                w_raw = row.get("written_avg_pass_rate", "").strip()
                p_raw = row.get("practical_avg_pass_rate", "").strip()
                try:
                    w = float(w_raw) if w_raw else None
                except ValueError:
                    w = None
                try:
                    p = float(p_raw) if p_raw else None
                except ValueError:
                    p = None
                out[name] = {"written_avg_pass_rate": w, "practical_avg_pass_rate": p}
    except Exception as e:
        print(f"WARN: cert_master.csv 로드 실패: {e}", file=sys.stderr)
    return out


def _load_cert_primary_domain() -> dict[str, str]:
    """cert_id → primary domain_sub_label_id (cert_domain_mapping.csv 기준)"""
    out: dict[str, str] = {}
    if not _CERT_DOMAIN_CSV.exists():
        return out
    try:
        with _CERT_DOMAIN_CSV.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("is_active") == "True":
                    out[row["cert_id"]] = row["domain_sub_label_id"]
    except Exception as e:
        print(f"WARN: cert_domain_mapping.csv 로드 실패: {e}", file=sys.stderr)
    return out


def _load_domain_adjacency_rules() -> list:
    """domain_adjacency.csv → [(source_domain, [keywords], [target_domains])] 규칙 목록.

    expansion_type == 'keyword'인 is_active 행만 로드한다.
    keywords 컬럼은 '|' 구분자로 분리한다.
    """
    rules: list = []
    if not _DOMAIN_ADJACENCY_CSV.exists():
        print("WARN: domain_adjacency.csv 없음 — 교차 도메인 확장 비활성화", file=sys.stderr)
        return rules
    # 행 구조: relation_id, source_domain_id, target_domain_id, expansion_type, keywords, note, is_active
    from collections import defaultdict
    src_kw_targets = defaultdict(set)  # (src_domain, keyword) → {target_domains}
    try:
        with _DOMAIN_ADJACENCY_CSV.open(encoding="utf-8-sig") as f:
            lines = [ln for ln in f if not ln.strip().startswith("#")]
        import io
        for row in csv.DictReader(io.StringIO("".join(lines))):
            if row.get("is_active", "").strip() != "True":
                continue
            if row.get("expansion_type", "").strip() != "keyword":
                continue
            src = row["source_domain_id"].strip()
            tgt = row["target_domain_id"].strip()
            for kw in row.get("keywords", "").split("|"):
                kw = kw.strip()
                if kw:
                    src_kw_targets[(src, kw)].add(tgt)
    except Exception as e:
        print(f"WARN: domain_adjacency.csv 로드 실패: {e}", file=sys.stderr)
        return rules

    for (src, kw), targets in src_kw_targets.items():
        rules.append((src, [kw], sorted(targets)))
    return rules


# 모듈 로드 시 adjacency 규칙을 캐시한다 (main() 호출마다 재로드 방지)
_ADJACENCY_RULES = None  # type: ignore[assignment]


def _get_adjacency_rules() -> list:
    global _ADJACENCY_RULES
    if _ADJACENCY_RULES is None:
        _ADJACENCY_RULES = _load_domain_adjacency_rules()
    return _ADJACENCY_RULES


def _expand_related_domains(
    cert_name: str,
    primary_domain: str,
    current_domains: list,
) -> list:
    """domain_adjacency.csv 키워드 규칙으로 related_domains를 확장한다."""
    extra: set[str] = set()
    for src_domain, keywords, targets in _get_adjacency_rules():
        if primary_domain != src_domain:
            continue
        if any(kw in cert_name for kw in keywords):
            extra.update(targets)
    extra -= set(current_domains)
    if not extra:
        return current_domains
    return current_domains + sorted(extra)


def _load_acq_trend() -> dict[str, dict]:
    """cert_name → {acq_trend: 'up'|'down'|'flat', acq_recent: int, acq_yoy_pct: float}
    yy1 = most recent year, yy2-yy3 = prior years baseline.
    Trend: up if yy1 > 1.15 * baseline, down if yy1 < 0.85 * baseline.
    """
    out: dict[str, dict] = {}
    if not _ACQUI_TREND_CSV.exists():
        return out
    try:
        with _ACQUI_TREND_CSV.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = row.get("jmNm", "").strip()
                if not name:
                    continue
                try:
                    yy1 = int(row.get("yy1AcquCnt", 0) or 0)
                    yy2 = int(row.get("yy2AcquCnt", 0) or 0)
                    yy3 = int(row.get("yy3AcquCnt", 0) or 0)
                except (ValueError, TypeError):
                    continue
                baseline = (yy2 + yy3) / 2.0 if (yy2 + yy3) > 0 else None
                if baseline and baseline > 0:
                    ratio = yy1 / baseline
                    if ratio >= 1.15:
                        trend = "up"
                    elif ratio <= 0.85:
                        trend = "down"
                    else:
                        trend = "flat"
                    yoy_pct = round((ratio - 1.0) * 100, 1)
                else:
                    trend = "flat"
                    yoy_pct = 0.0
                out[name] = {"acq_trend": trend, "acq_recent": yy1, "acq_yoy_pct": yoy_pct}
    except Exception as e:
        print(f"WARN: 전공별 취득 현황_rows.csv 로드 실패: {e}", file=sys.stderr)
    return out


def main() -> int:
    if not _JSONL.exists():
        print(f"ERROR: {_JSONL} 없음. build_cert_candidates.py 먼저 실행.", file=sys.stderr)
        return 1

    cert_master_rates = _load_cert_master_rates()
    acq_trend_map = _load_acq_trend()
    cert_primary_domain = _load_cert_primary_domain()

    records: list[dict] = []
    with _JSONL.open(encoding="utf-8") as f:
        for line in f:
            if s := line.strip():
                records.append(json.loads(s))

    slim: list[dict] = []
    for rec in records:
        text_dense = rec.get("text_for_dense", "")
        pass_rate = _extract_pass_rate(text_dense)
        sessions = rec.get("exam_sessions_per_year")
        if sessions is None:
            sessions = _extract_sessions(text_dense)

        cert_name = rec.get("cert_name", "")
        cert_id = rec.get("cert_id", "")

        slim_rec: dict = {k: rec.get(k) for k in _KEEP_FIELDS if k in rec}
        slim_rec["avg_pass_rate_3yr"] = pass_rate
        slim_rec["exam_sessions_per_year"] = sessions

        # IT 클러스터 교차 도메인 확장
        primary_domain = cert_primary_domain.get(cert_id, rec.get("primary_domain", ""))
        rel_domains = slim_rec.get("related_domains", [])
        if isinstance(rel_domains, str):
            rel_domains = [rel_domains]
        slim_rec["related_domains"] = _expand_related_domains(cert_name, primary_domain, rel_domains)

        # Supplement from cert_master.csv
        master_data = cert_master_rates.get(cert_name, {})
        slim_rec["written_avg_pass_rate"] = master_data.get("written_avg_pass_rate")
        slim_rec["practical_avg_pass_rate"] = master_data.get("practical_avg_pass_rate")

        # Supplement trend from 전공별 취득 현황
        trend_data = acq_trend_map.get(cert_name, {})
        slim_rec["acq_trend"] = trend_data.get("acq_trend")
        slim_rec["acq_recent"] = trend_data.get("acq_recent")
        slim_rec["acq_yoy_pct"] = trend_data.get("acq_yoy_pct")

        slim.append(slim_rec)

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    # 단일 라인 JSON (Vite/브라우저 파싱에 최적, 줄바꿈 오버헤드 제거)
    _OUT.write_text(
        json.dumps(slim, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    before_size = _JSONL.stat().st_size
    after_size = _OUT.stat().st_size
    pass_rate_count = sum(1 for r in slim if r.get("avg_pass_rate_3yr") is not None)
    sessions_count = sum(1 for r in slim if r.get("exam_sessions_per_year") is not None)
    written_count = sum(1 for r in slim if r.get("written_avg_pass_rate") is not None)
    practical_count = sum(1 for r in slim if r.get("practical_avg_pass_rate") is not None)
    trend_count = sum(1 for r in slim if r.get("acq_trend") is not None)
    expanded_count = sum(1 for r in slim if len(r.get("related_domains") or []) > 1)

    print(f"입력 jsonl: {_JSONL} ({before_size:,} bytes)")
    print(f"출력 json : {_OUT} ({after_size:,} bytes, {after_size / before_size * 100:.1f}% 크기)")
    print(f"레코드 수: {len(slim)}")
    print(f"avg_pass_rate_3yr 추출 성공: {pass_rate_count}/{len(slim)}")
    print(f"exam_sessions_per_year 추출 성공: {sessions_count}/{len(slim)}")
    print(f"written_avg_pass_rate 보충: {written_count}/{len(slim)}")
    print(f"practical_avg_pass_rate 보충: {practical_count}/{len(slim)}")
    print(f"acq_trend 보충: {trend_count}/{len(slim)}")
    print(f"related_domains 교차 확장: {expanded_count}개 자격증이 2개 이상 도메인 보유")
    return 0


if __name__ == "__main__":
    sys.exit(main())
