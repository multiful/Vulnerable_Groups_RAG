# File: isolation_screening_analysis.py
# Last Updated: 2026-06-23
# Content Hash: SHA256:TBD
# Role: 서울시 고립은둔청년 실태조사 데이터 → 4단계 통계 분석 파이프라인
#       Stage1 전처리 → Stage2 집단 차이 검정 → Stage3 문항 최적화 → Stage4 가중치 및 ROC
"""
사용법:
    python scripts/isolation_screening_analysis.py

출력:
    results/isolation_screening/ 폴더에 JSON + CSV 결과 저장
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from scipy import stats

# ── 경로 설정 ─────────────────────────────────────────────────────────────
EXCEL_PATH = Path("data/raw/csv/★TABLE_서울시 고립은둔청년 실태조사(청년조사)_전체_v1_230127 (2).xlsx")
OUT_DIR = Path("results/isolation_screening")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 고립은둔 청년(col_idx=15) vs 미해당(col_idx=16) — 0-indexed
N_ISOLATED_DEFAULT = 486
N_GENERAL_DEFAULT  = 5027
COL_ISO = 14   # 고립은둔 청년 열 (0-indexed)
COL_GEN = 15   # 미해당 열 (0-indexed)

# ── 분석 제외 섹션 (인구통계/지역 → 변별 목적 아님) ─────────────────────
SKIP_SECTION_PREFIX = {"【0】", "【SQ1】", "【SQ2", "【SQ4】", "【SQ5】", "【DQ"}


# =============================================================================
# STAGE 1 — 데이터 파싱 및 전처리
# =============================================================================

def parse_excel_sections() -> list[dict]:
    """Excel '테이블' 시트에서 섹션별 카테고리 비율 추출."""
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True)
    ws = wb["테이블"]

    all_rows = [list(row) for row in ws.iter_rows(values_only=True)]

    sections: list[dict] = []
    cur: dict | None = None

    for raw_row in all_rows:
        if raw_row[0] and isinstance(raw_row[0], str) and raw_row[0].startswith("【"):
            cur = {"header": raw_row[0].strip(), "categories": []}
            sections.append(cur)
        elif cur and any(v is not None for v in raw_row):
            cur["categories"].append(raw_row)

    return sections


def _parse_n(val) -> int | None:
    """'(486)' 또는 486 → int 변환."""
    if val is None:
        return None
    s = str(val).strip().lstrip("(").rstrip(")")
    try:
        return int(float(s.replace(",", "")))
    except ValueError:
        return None


def extract_item_stats(sections: list[dict]) -> list[dict]:
    """각 섹션에서 고립은둔 vs 미해당 비율을 추출하여 분석용 레코드 생성."""
    records: list[dict] = []

    for sec in sections:
        header = sec["header"]

        # 분석 제외 섹션 스킵
        if any(header.startswith(p) for p in SKIP_SECTION_PREFIX):
            continue

        cats = sec["categories"]

        # 섹션별 N 동적 추출 (BASE 조건에 따라 달라짐)
        n_iso = N_ISOLATED_DEFAULT
        n_gen = N_GENERAL_DEFAULT
        for row in cats:
            r0 = str(row[0] or "")
            if "사례수" in r0 or "BASE" in r0:
                v_iso = _parse_n(row[COL_ISO] if len(row) > COL_ISO else None)
                v_gen = _parse_n(row[COL_GEN] if len(row) > COL_GEN else None)
                if v_iso and v_gen:
                    n_iso, n_gen = v_iso, v_gen
                break

        for row in cats:
            # 길이 체크
            if len(row) <= COL_GEN:
                continue

            # 카테고리 이름: col0이 문자열이어야 함
            cat_name = row[0]
            if not cat_name or not isinstance(cat_name, str):
                continue
            # 메타 행 제외
            if any(x in cat_name for x in ("사례수", "BASE", "▣", "합  계", "평균")):
                continue

            try:
                pct_iso = float(row[COL_ISO]) if row[COL_ISO] is not None else None
                pct_gen = float(row[COL_GEN]) if row[COL_GEN] is not None else None
            except (TypeError, ValueError):
                continue

            if pct_iso is None or pct_gen is None:
                continue

            records.append({
                "section":      header,
                "category":     cat_name.strip(),
                "pct_isolated": round(pct_iso, 3),
                "pct_general":  round(pct_gen, 3),
                "n_iso":        n_iso,
                "n_gen":        n_gen,
            })

    return records


# =============================================================================
# STAGE 2 — 집단 차이 검정 (Chi-squared + Cohen's h)
# =============================================================================

def cohen_h(p1: float, p2: float) -> float:
    """두 비율 간 Cohen's h 효과 크기."""
    p1c = max(min(p1 / 100, 0.9999), 0.0001)
    p2c = max(min(p2 / 100, 0.9999), 0.0001)
    return abs(2 * math.asin(math.sqrt(p1c)) - 2 * math.asin(math.sqrt(p2c)))


def chi_square_2prop(p_iso: float, p_gen: float,
                     n_iso: int = N_ISOLATED_DEFAULT,
                     n_gen: int = N_GENERAL_DEFAULT) -> tuple[float, float]:
    """2×2 카이제곱 검정. (chi2, p_value) 반환."""
    o11 = round(n_iso * p_iso / 100)
    o12 = n_iso - o11
    o21 = round(n_gen * p_gen / 100)
    o22 = n_gen - o21
    if o11 + o12 + o21 + o22 == 0:
        return 0.0, 1.0
    obs = np.array([[o11, o12], [o21, o22]])
    # 셀 값 0 방지
    obs = np.maximum(obs, 0)
    try:
        chi2, p, _, _ = stats.chi2_contingency(obs, correction=False)
    except Exception:
        return 0.0, 1.0
    return float(chi2), float(p)


def run_difference_tests(records: list[dict]) -> pd.DataFrame:
    """각 항목에 대해 chi-squared + Cohen's h 계산."""
    rows = []
    for r in records:
        chi2, pval = chi_square_2prop(
            r["pct_isolated"], r["pct_general"],
            n_iso=r.get("n_iso", N_ISOLATED_DEFAULT),
            n_gen=r.get("n_gen", N_GENERAL_DEFAULT),
        )
        h = cohen_h(r["pct_isolated"], r["pct_general"])
        diff = r["pct_isolated"] - r["pct_general"]

        rows.append({
            **r,
            "chi2":      round(chi2, 4),
            "p_value":   round(pval, 6),
            "cohen_h":   round(h, 4),
            "diff_pct":  round(diff, 3),
            "significant": pval < 0.05,
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("cohen_h", ascending=False).reset_index(drop=True)
    return df


# =============================================================================
# STAGE 3 — 문항 최적화 (도메인 그룹핑 + 최적 12문항 선별)
# =============================================================================

DOMAIN_MAP: dict[str, str] = {
    "A7":  "물리적_고립",   # 외출 빈도
    "A8":  "물리적_고립",   # 은둔 기간
    "A9":  "물리적_고립",
    "A10": "물리적_고립",   # 지난 2주 교류
    "A11": "물리적_고립",
    "A13": "물리적_고립",   # 대면 교류 빈도
    "A14": "물리적_고립",   # 고립 기간
    "A12": "정서적_고립",   # 정서적 지지망
    "A18": "외로움",        # UCLA 외로움 척도
    "B12": "우울",          # PHQ-9 우울 척도
    "B1":  "생활패턴",      # 수면/생활 리듬
    "B2":  "생활패턴",
    "B3":  "생활패턴",
    "B9":  "자기관리",      # 위생/자기관리
    "B7":  "생활패턴",      # 식사
    "A1":  "취업_사회이행", # 노동 여부
    "A2":  "취업_사회이행", # 취업 의향
    "A3":  "취업_사회이행", # 미활동 기간
    "A5":  "경제_수준",     # 가정 경제 수준
    "A6":  "경제_수준",     # 본인 경제 수준
    "C1":  "회복_의지",     # 벗어나고 싶다
    "C4":  "회복_의지",     # 필요한 지원
    "A19": "선행_경험",     # 성인기 전 경험
    "A20": "선행_경험",     # 성인기 후 경험
    "B6":  "디지털_고립",   # PC/모바일 활동
    "A17": "디지털_고립",   # 온라인 대화
    "C8":  "지원_경험",     # 지원사업 경험
    "C7":  "지원_경험",
    "C5":  "지원_경험",
    "SQ6": "사회구조",
    "SQ7": "사회구조",
    "SQ8": "사회구조",
}


def assign_domain(section_header: str) -> str:
    """섹션 헤더에서 변수명 추출 → 도메인 매핑."""
    m = re.search(r"【([A-Z0-9_]+)", section_header)
    if not m:
        return "기타"
    var = m.group(1)
    # 복합 변수 (SQ7_1 TO ...) → 공통 prefix만 사용
    prefix = re.match(r"([A-Z]+\d+)", var)
    key = prefix.group(1) if prefix else var
    for k, v in DOMAIN_MAP.items():
        if key.startswith(k):
            return v
    return "기타"


def _section_var(header: str) -> str:
    """섹션 헤더에서 변수명(A1, A12_1 등) 추출."""
    m = re.search(r"【([A-Z0-9_]+)", header)
    return m.group(1) if m else header


def optimize_items(df: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    """효과 크기 기준 + 도메인 다양성 + 섹션 중복 제거하며 최적 문항 선별."""
    df = df[df["significant"] & (df["cohen_h"] >= 0.15)].copy()
    df["domain"] = df["section"].apply(assign_domain)
    df["var_key"] = df["section"].apply(_section_var)

    selected: list[int] = []
    seen_domains: dict[str, int] = {}
    seen_sections: set[str] = set()
    MAX_PER_DOMAIN = 2  # 도메인당 최대 2개

    # 1차: 효과 크기 내림차순 + 섹션 중복 제거 + 도메인 다양성
    for idx, row in df.iterrows():
        if len(selected) >= top_n:
            break
        dom = row["domain"]
        sec = row["var_key"]
        # 같은 섹션(같은 질문) 중복 방지
        if sec in seen_sections:
            continue
        # 도메인 상한
        if seen_domains.get(dom, 0) >= MAX_PER_DOMAIN:
            continue
        selected.append(idx)
        seen_domains[dom] = seen_domains.get(dom, 0) + 1
        seen_sections.add(sec)

    # 2차: 아직 top_n 미달이면 섹션 중복 허용하되 도메인 제한 완화하여 추가
    MAX_PER_DOMAIN_EXTENDED = 3
    seen_sections_extended: set[str] = set(
        df.loc[selected, "var_key"].tolist() if selected else []
    )
    for idx, row in df.iterrows():
        if len(selected) >= top_n:
            break
        if idx in selected:
            continue
        dom = row["domain"]
        sec = row["var_key"]
        if sec in seen_sections_extended:
            continue
        if seen_domains.get(dom, 0) >= MAX_PER_DOMAIN_EXTENDED:
            continue
        selected.append(idx)
        seen_domains[dom] = seen_domains.get(dom, 0) + 1
        seen_sections_extended.add(sec)

    result = df.loc[selected].copy()
    result = result.sort_values("cohen_h", ascending=False).reset_index(drop=True)
    result["rank"] = result.index + 1
    return result


# =============================================================================
# STAGE 4 — 가중치 산출 및 판별 타당성 검증 (Cohen's h 기반 proxy AUC)
# =============================================================================

def compute_weights(best_items: pd.DataFrame) -> pd.DataFrame:
    """Cohen's h를 정규화하여 문항 가중치 산출."""
    total_h = best_items["cohen_h"].sum()
    best_items = best_items.copy()
    best_items["weight"] = (best_items["cohen_h"] / total_h * 100).round(2)
    return best_items


def estimate_discriminant_score(best_items: pd.DataFrame) -> dict:
    """
    비율 데이터 기반 판별력 추정.
    각 문항에서 고립군 쪽 응답을 '양성'으로 간주하고,
    Cohen's h 가중 합산 점수로 두 집단 점수 분포 추정.
    """
    # 고립군 기대 점수 (각 항목 가중치 × (p_isolated > p_general ? 1 : 0))
    iso_score = sum(
        row["weight"] * (1 if row["diff_pct"] > 0 else 0)
        for _, row in best_items.iterrows()
    )
    gen_score = sum(
        row["weight"] * (1 if row["diff_pct"] < 0 else 0)
        for _, row in best_items.iterrows()
    )

    # 간이 AUC 추정 (정규분포 가정 하 Wilcoxon-Mann-Whitney 통계량 근사)
    # E[P(X_iso > X_gen)] ≈ Φ( mean_diff / pooled_sd ) 단순 추정
    # 여기서는 Cohen's h 합산으로 proxy AUC 계산
    mean_h = best_items["cohen_h"].mean()
    # 표준 정규분포 근사: AUC = Φ(d/√2), d = mean Cohen's h
    proxy_auc = float(stats.norm.cdf(mean_h / math.sqrt(2)))

    total_weight = best_items["weight"].sum()
    positive_items = (best_items["diff_pct"] > 0).sum()
    return {
        "n_items":            len(best_items),
        "mean_cohen_h":       round(mean_h, 4),
        "proxy_auc":          round(proxy_auc, 4),
        "isolated_expected_score": round(iso_score, 2),
        "general_expected_score":  round(gen_score, 2),
        "total_weight":       round(total_weight, 2),
        "items_higher_in_isolated": int(positive_items),
    }


# =============================================================================
# 메인 실행
# =============================================================================

def main() -> None:
    print("=" * 60)
    print("고립은둔청년 판별 스크리닝 문항 선별 분석 파이프라인")
    print("=" * 60)

    # STAGE 1 — 파싱
    print("\n[Stage 1] 데이터 파싱 중...")
    sections = parse_excel_sections()
    records  = extract_item_stats(sections)
    print(f"  총 섹션: {len(sections)}개 | 유효 카테고리 레코드: {len(records)}개")

    # STAGE 2 — 집단 차이 검정
    print("\n[Stage 2] 집단 차이 검정 (Chi-squared + Cohen's h)...")
    df_all = run_difference_tests(records)
    sig_df = df_all[df_all["significant"]]
    print(f"  통계적 유의(p<0.05): {len(sig_df)}개 / 전체 {len(df_all)}개")
    print(f"  Cohen's h ≥ 0.2 (중간 효과): {(sig_df['cohen_h'] >= 0.2).sum()}개")
    print(f"  Cohen's h ≥ 0.5 (큰 효과):   {(sig_df['cohen_h'] >= 0.5).sum()}개")

    top10 = df_all[df_all["significant"]].head(10)
    print("\n  [상위 10개 효과 크기 항목]")
    for _, r in top10.iterrows():
        print(f"  {r['section'][:30]:<32} 카테고리:[{r['category'][:16]:<16}]"
              f" h={r['cohen_h']:.3f} diff={r['diff_pct']:+.1f}%")

    # STAGE 3 — 문항 최적화
    print("\n[Stage 3] 문항 최적화 (도메인 다양성 유지, 최적 12문항 선별)...")
    best_df = optimize_items(df_all, top_n=12)
    print(f"  선별된 문항 수: {len(best_df)}개")
    print(f"\n  {'순위':<4} {'도메인':<14} {'섹션':<30} {'카테고리':<20} {'h값':<6} {'차이'}")
    for _, r in best_df.iterrows():
        print(f"  {int(r['rank']):<4} {r['domain']:<14} {r['section'][:28]:<30}"
              f" {r['category'][:18]:<20} {r['cohen_h']:.3f} {r['diff_pct']:+.1f}%")

    # STAGE 4 — 가중치 및 판별 타당성
    print("\n[Stage 4] 가중치 산출 및 판별 타당성 검증...")
    best_df = compute_weights(best_df)
    disc    = estimate_discriminant_score(best_df)

    print(f"  선별 문항 수:       {disc['n_items']}")
    print(f"  평균 Cohen's h:     {disc['mean_cohen_h']:.4f}")
    print(f"  추정 AUC (proxy):   {disc['proxy_auc']:.4f}")
    print(f"  고립군 방향 문항:   {disc['items_higher_in_isolated']}개")

    print("\n  [최종 문항 가중치]")
    print(f"  {'순위':<4} {'가중치':>6} {'도메인':<14} {'섹션':<25} {'카테고리'}")
    for _, r in best_df.iterrows():
        print(f"  {int(r['rank']):<4} {r['weight']:>5.1f}%  {r['domain']:<14}"
              f" {r['section'][:23]:<25} {r['category'][:24]}")

    # ── 결과 저장 ──
    df_all.to_csv(OUT_DIR / "stage2_all_items.csv", index=False, encoding="utf-8-sig")
    best_df.to_csv(OUT_DIR / "stage3_optimal_items.csv", index=False, encoding="utf-8-sig")
    with open(OUT_DIR / "stage4_discrimination.json", "w", encoding="utf-8") as f:
        json.dump(disc, f, ensure_ascii=False, indent=2)

    # 최종 스크리닝 문항 요약 JSON
    screening_items = []
    for _, r in best_df.iterrows():
        screening_items.append({
            "rank":      int(r["rank"]),
            "section":   r["section"],
            "category":  r["category"],
            "domain":    r["domain"],
            "cohen_h":   r["cohen_h"],
            "weight":    r["weight"],
            "diff_pct":  r["diff_pct"],
            "pct_isolated": r["pct_isolated"],
            "pct_general":  r["pct_general"],
            "direction": "고립군↑" if r["diff_pct"] > 0 else "일반군↑",
        })
    with open(OUT_DIR / "screening_items_final.json", "w", encoding="utf-8") as f:
        json.dump(screening_items, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장 완료: {OUT_DIR}/")
    print("  · stage2_all_items.csv       — 전체 문항 검정 결과")
    print("  · stage3_optimal_items.csv   — 최적 12문항")
    print("  · stage4_discrimination.json — 판별 타당성 지표")
    print("  · screening_items_final.json — 최종 스크리닝 문항 요약")


if __name__ == "__main__":
    main()
