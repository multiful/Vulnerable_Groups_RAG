# File: build_frontend_data.py
# Last Updated: 2026-05-15
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

        slim_rec: dict = {k: rec.get(k) for k in _KEEP_FIELDS if k in rec}
        slim_rec["avg_pass_rate_3yr"] = pass_rate
        slim_rec["exam_sessions_per_year"] = sessions

        # Supplement from cert_master.csv
        cert_name = rec.get("cert_name", "")
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

    print(f"입력 jsonl: {_JSONL} ({before_size:,} bytes)")
    print(f"출력 json : {_OUT} ({after_size:,} bytes, {after_size / before_size * 100:.1f}% 크기)")
    print(f"레코드 수: {len(slim)}")
    print(f"avg_pass_rate_3yr 추출 성공: {pass_rate_count}/{len(slim)}")
    print(f"exam_sessions_per_year 추출 성공: {sessions_count}/{len(slim)}")
    print(f"written_avg_pass_rate 보충: {written_count}/{len(slim)}")
    print(f"practical_avg_pass_rate 보충: {practical_count}/{len(slim)}")
    print(f"acq_trend 보충: {trend_count}/{len(slim)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
