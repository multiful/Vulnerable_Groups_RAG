# File: normalize_difficulty.py
# Last Updated: 2026-05-12
# Content Hash: SHA256:TBD
# Role: cert_master.csv의 exam_difficulty를 합격률 백분위 기반으로 재정규화
#
# 정규화 원칙:
#   avg_pass_rate_3yr 있는 자격: 전체 합격률 분포에서 20% 백분위 구간으로 난이도 1-5 배분
#   합격률 없는 자격: cert_grade_tier 기반 기본값 부여
#   등급 보정(선택): 기술사/기능장 +0.5 보정, 기능사 -0.5 보정 (cap 1-5)
#
# 실행: python -m scripts.normalize_difficulty
from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
CERT_MASTER  = PROJECT_ROOT / "data/processed/master/cert_master.csv"

# cert_grade_tier별 기본 난이도 (합격률 없을 때)
_TIER_DEFAULT: dict[str, float] = {
    "4_기술사":  5.0,
    "5_기능장":  5.0,
    "3_기사":    4.0,
    "2_산업기사": 3.0,
    "1_기능사":  2.0,
}

# 등급 보정값 (백분위 기반 점수에 가산)
_TIER_ADJUST: dict[str, float] = {
    "4_기술사":  0.5,
    "5_기능장":  0.5,
    "3_기사":    0.0,
    "2_산업기사": 0.0,
    "1_기능사":  -0.5,
}

# 난이도 → 한글 라벨
DIFF_LABEL: dict[int, str] = {
    1: "하 (쉬움)",
    2: "중하",
    3: "중 (보통)",
    4: "중상",
    5: "상 (어려움)",
}


def _parse_float(val: str) -> float | None:
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return None


def compute_normalized_difficulty(
    pass_rate: float | None,
    tier: str,
    percentile_thresholds: tuple[float, float, float, float],
) -> float:
    """합격률 백분위 구간에서 난이도 1-5 반환.

    percentile_thresholds = (p20, p40, p60, p80) — 전체 분포의 각 분위수.
    합격률이 낮을수록 높은 난이도 (inverse).
    """
    p20, p40, p60, p80 = percentile_thresholds

    if pass_rate is not None:
        # 합격률 → 역방향 난이도 (높은 합격률 = 쉬움 = 낮은 난이도)
        if pass_rate >= p80:
            base = 1.0
        elif pass_rate >= p60:
            base = 2.0
        elif pass_rate >= p40:
            base = 3.0
        elif pass_rate >= p20:
            base = 4.0
        else:
            base = 5.0

        # 등급 보정
        adjust = _TIER_ADJUST.get(tier, 0.0)
        score = base + adjust
    else:
        # 합격률 없으면 tier 기본값
        score = _TIER_DEFAULT.get(tier, 3.0)

    return float(max(1, min(5, round(score * 2) / 2)))  # 0.5 단위 반올림, 1-5 클램프


def main() -> None:
    if not CERT_MASTER.exists():
        print(f"cert_master.csv 없음: {CERT_MASTER}", file=sys.stderr)
        sys.exit(1)

    with CERT_MASTER.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(csv.DictReader(open(CERT_MASTER, encoding="utf-8-sig")).fieldnames or [])

    # 합격률 수집 → 백분위 계산
    pass_rates: list[float] = sorted(
        pr for r in rows
        if (pr := _parse_float(r.get("avg_pass_rate_3yr", "") or "")) is not None
    )
    n = len(pass_rates)
    print(f"합격률 데이터 있는 자격: {n}개 / 전체 {len(rows)}개")

    p20 = pass_rates[int(n * 0.20)]
    p40 = pass_rates[int(n * 0.40)]
    p60 = pass_rates[int(n * 0.60)]
    p80 = pass_rates[int(n * 0.80)]
    thresholds = (p20, p40, p60, p80)
    print(f"백분위 임계값: 20th={p20:.1f}%, 40th={p40:.1f}%, 60th={p60:.1f}%, 80th={p80:.1f}%")

    # 각 자격에 새 난이도 적용
    from collections import Counter
    dist: Counter = Counter()
    updated = 0

    for row in rows:
        pass_rate = _parse_float(row.get("avg_pass_rate_3yr", "") or "")
        tier = (row.get("cert_grade_tier") or "").strip()
        new_diff = compute_normalized_difficulty(pass_rate, tier, thresholds)
        old_diff = row.get("exam_difficulty", "").strip()
        row["exam_difficulty"] = str(new_diff)
        dist[new_diff] += 1
        if old_diff != str(new_diff):
            updated += 1

    print(f"난이도 변경 자격: {updated}개")
    print(f"새 분포: {dict(sorted(dist.items()))}")

    # cert_master.csv 덮어쓰기
    with CERT_MASTER.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"저장 완료: {CERT_MASTER}")
    print("\n다음 단계: python -m scripts.build_cert_candidates 로 candidates 재빌드")


if __name__ == "__main__":
    main()
