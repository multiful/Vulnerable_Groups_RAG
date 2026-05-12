# File: build_frontend_data.py
# Last Updated: 2026-05-12
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
#   - content_hash, source_ids, quality_flags, valid_from/to, updated_at 등 운영성 필드 제거
#   - FE 표시·필터링에 필요한 필드만 유지
#
# 증분 빌드 규칙(CLAUDE.md §12): jsonl content_hash 동일하면 재생성 스킵 가능
#   (현재 구현: 매번 전체 재생성. content_hash 비교는 후속 최적화 대상)

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_JSONL = _PROJECT_ROOT / "data/canonical/candidates/cert_candidates.jsonl"
_OUT = _PROJECT_ROOT / "frontend/public/data/cert_candidates.json"

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


def main() -> int:
    if not _JSONL.exists():
        print(f"ERROR: {_JSONL} 없음. build_cert_candidates.py 먼저 실행.", file=sys.stderr)
        return 1

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

    print(f"입력 jsonl: {_JSONL} ({before_size:,} bytes)")
    print(f"출력 json : {_OUT} ({after_size:,} bytes, {after_size / before_size * 100:.1f}% 크기)")
    print(f"레코드 수: {len(slim)}")
    print(f"avg_pass_rate_3yr 추출 성공: {pass_rate_count}/{len(slim)}")
    print(f"exam_sessions_per_year 추출 성공: {sessions_count}/{len(slim)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
