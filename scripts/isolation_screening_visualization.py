# File: isolation_screening_visualization.py
# Last Updated: 2026-06-23
# Content Hash: SHA256:TBD
# Role: 고립은둔청년 판별 스크리닝 — 통계 분석 결과 시각화 (PDF 방법론 기반)
#       신뢰타당성분석.pdf + 은둔청소년 스크리닝 척도 개발.pdf 방법론 적용
#       Forest plot / ROC / Youden's J / Domain heatmap / Publication table
"""
사용법:
    python scripts/isolation_screening_visualization.py

출력: results/isolation_screening/figures/ 폴더
"""
from __future__ import annotations

import json
import math
import re
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
from matplotlib import rcParams
import numpy as np
import pandas as pd
import openpyxl
from scipy import stats

warnings.filterwarnings("ignore")

# ── 한글 폰트 설정 ────────────────────────────────────────────────────────
import matplotlib.font_manager as fm

def _set_korean_font():
    candidates = [
        "AppleGothic", "NanumGothic", "Malgun Gothic",
        "DejaVu Sans", "Arial Unicode MS",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for c in candidates:
        if c in available:
            rcParams["font.family"] = c
            break
    rcParams["axes.unicode_minus"] = False

_set_korean_font()

# ── 경로 ─────────────────────────────────────────────────────────────────
EXCEL_PATH = Path("data/raw/csv/★TABLE_서울시 고립은둔청년 실태조사(청년조사)_전체_v1_230127 (2).xlsx")
RESULTS_DIR = Path("results/isolation_screening")
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

N_ISO = 486
N_GEN = 5027
COL_ISO = 14
COL_GEN = 15

SKIP_PREFIX = {"【0】", "【SQ1】", "【SQ2", "【SQ4】", "【SQ5】", "【DQ"}

# ── 3요인 도메인 매핑 (스크리닝 척도 PDF 기반) ───────────────────────────
FACTOR_MAP = {
    "A13": "사회단절·고립",
    "A14": "사회단절·고립",
    "A10": "사회단절·고립",
    "A11": "사회단절·고립",
    "A12": "사회단절·고립",
    "A7":  "사회단절·고립",
    "A8":  "사회단절·고립",
    "A18": "사회단절·고립",
    "A1":  "회피·사회이행",
    "A2":  "회피·사회이행",
    "A3":  "회피·사회이행",
    "A17": "회피·사회이행",
    "B6":  "회피·사회이행",
    "C1":  "회피·사회이행",
    "B1":  "불규칙한 생활방식",
    "B2":  "불규칙한 생활방식",
    "B3":  "불규칙한 생활방식",
    "B7":  "불규칙한 생활방식",
    "B9":  "불규칙한 생활방식",
    "B10": "불규칙한 생활방식",
    "B11": "불규칙한 생활방식",
    "B12": "불규칙한 생활방식",
    "A5":  "경제·생활여건",
    "A6":  "경제·생활여건",
    "A4":  "경제·생활여건",
    "A19": "선행경험",
    "A20": "선행경험",
    "C4":  "회복·지원욕구",
    "C7":  "회복·지원욕구",
    "C8":  "회복·지원욕구",
}

FACTOR_COLORS = {
    "사회단절·고립":     "#e74c3c",
    "회피·사회이행":     "#e67e22",
    "불규칙한 생활방식": "#9b59b6",
    "경제·생활여건":     "#3498db",
    "선행경험":          "#27ae60",
    "회복·지원욕구":     "#16a085",
    "기타":              "#95a5a6",
}


# =============================================================================
# 데이터 로딩 (analysis 스크립트와 동일 로직)
# =============================================================================

def _parse_n(val) -> int | None:
    if val is None:
        return None
    s = str(val).strip().lstrip("(").rstrip(")")
    try:
        return int(float(s.replace(",", "")))
    except ValueError:
        return None


def load_data() -> pd.DataFrame:
    if (RESULTS_DIR / "stage2_all_items.csv").exists():
        df = pd.read_csv(RESULTS_DIR / "stage2_all_items.csv")
        # CI / Youden 컬럼이 없으면 계산
        if "ci_lo" not in df.columns:
            df["se_h"] = df.apply(lambda r: math.sqrt(1/r.n_iso + 1/r.n_gen), axis=1)
            df["ci_lo"] = (df.cohen_h - 1.96 * df.se_h).clip(lower=0)
            df["ci_hi"] = df.cohen_h + 1.96 * df.se_h
        if "youden_j" not in df.columns:
            df["youden_j"] = (df.pct_isolated - df.pct_general) / 100
        df["factor"] = df["section"].apply(_assign_factor)
        df = df.sort_values("cohen_h", ascending=False).reset_index(drop=True)
        return df

    # Excel에서 직접 파싱
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True)
    ws = wb["테이블"]
    all_rows = [list(r) for r in ws.iter_rows(values_only=True)]

    records = []
    cur_header = ""
    n_iso, n_gen = N_ISO, N_GEN

    for row in all_rows:
        if row[0] and isinstance(row[0], str) and row[0].startswith("【"):
            cur_header = row[0].strip()
            n_iso, n_gen = N_ISO, N_GEN
            continue
        if any(cur_header.startswith(p) for p in SKIP_PREFIX):
            continue
        if not cur_header:
            continue
        r0 = str(row[0] or "")
        if "사례수" in r0:
            v_i = _parse_n(row[COL_ISO] if len(row) > COL_ISO else None)
            v_g = _parse_n(row[COL_GEN] if len(row) > COL_GEN else None)
            if v_i and v_g:
                n_iso, n_gen = v_i, v_g
            continue
        if any(x in r0 for x in ("BASE", "▣", "합  계", "평균")):
            continue
        if not r0 or len(row) <= COL_GEN:
            continue
        try:
            pi = float(row[COL_ISO]) if row[COL_ISO] is not None else None
            pg = float(row[COL_GEN]) if row[COL_GEN] is not None else None
        except (TypeError, ValueError):
            continue
        if pi is None or pg is None:
            continue
        records.append({
            "section": cur_header, "category": r0.strip(),
            "pct_isolated": round(pi, 3), "pct_general": round(pg, 3),
            "n_iso": n_iso, "n_gen": n_gen,
        })

    df = pd.DataFrame(records)
    # 통계 계산
    df["cohen_h"] = df.apply(lambda r: _cohen_h(r.pct_isolated, r.pct_general), axis=1)
    df["diff_pct"] = df.pct_isolated - df.pct_general
    df["se_h"] = df.apply(lambda r: math.sqrt(1/r.n_iso + 1/r.n_gen), axis=1)
    df["ci_lo"] = (df.cohen_h - 1.96 * df.se_h).clip(lower=0)
    df["ci_hi"] = df.cohen_h + 1.96 * df.se_h
    df[["chi2", "p_value"]] = df.apply(
        lambda r: pd.Series(_chi2(r.pct_isolated, r.pct_general, r.n_iso, r.n_gen)),
        axis=1,
    )
    df["significant"] = df.p_value < 0.05
    df["youden_j"] = (df.pct_isolated - df.pct_general) / 100
    df["factor"] = df.section.apply(_assign_factor)
    df = df.sort_values("cohen_h", ascending=False).reset_index(drop=True)
    return df


def _cohen_h(p1, p2):
    p1c = max(min(p1 / 100, 0.9999), 0.0001)
    p2c = max(min(p2 / 100, 0.9999), 0.0001)
    return abs(2 * math.asin(math.sqrt(p1c)) - 2 * math.asin(math.sqrt(p2c)))


def _chi2(p_iso, p_gen, n_iso, n_gen):
    o11 = max(round(n_iso * p_iso / 100), 0)
    o12 = max(n_iso - o11, 0)
    o21 = max(round(n_gen * p_gen / 100), 0)
    o22 = max(n_gen - o21, 0)
    try:
        chi2, p, _, _ = stats.chi2_contingency(
            np.array([[o11, o12], [o21, o22]]), correction=False
        )
        return float(chi2), float(p)
    except Exception:
        return 0.0, 1.0


def _assign_factor(section: str) -> str:
    m = re.search(r"【([A-Z]+\d+)", section)
    if not m:
        return "기타"
    key = m.group(1)
    for k, v in FACTOR_MAP.items():
        if key.startswith(k):
            return v
    return "기타"


def _section_short(section: str) -> str:
    m = re.search(r"【(.+?)】(.{0,18})", section)
    if m:
        return f"{m.group(1)} {m.group(2).strip()}"
    return section[:25]


# =============================================================================
# FIGURE 1 — 종합 통계 테이블 (Publication-style)
# =============================================================================

def fig_summary_table(df: pd.DataFrame):
    top = df[df["significant"]].head(30).copy()
    top["label"] = top.apply(
        lambda r: f"{_section_short(r.section)} [{r.category[:10]}]", axis=1
    )

    col_data = [
        top["label"].tolist(),
        [f"{v:.3f}" for v in top["cohen_h"]],
        [f"{v:.2f}–{w:.2f}" for v, w in zip(top["ci_lo"], top["ci_hi"])],
        [f"{v:.1f}" for v in top["chi2"]],
        ["<0.001" if v < 0.001 else f"{v:.4f}" for v in top["p_value"]],
        [f"{v:+.1f}%" for v in top["diff_pct"]],
        [f"{v:.3f}" for v in top["youden_j"]],
        top["factor"].tolist(),
    ]
    col_labels = ["문항 (섹션[카테고리])", "Cohen's h", "95% CI", "χ²", "p값",
                  "차이(고립-일반)", "Youden's J", "요인"]

    fig, ax = plt.subplots(figsize=(20, 14))
    ax.axis("off")
    tbl = ax.table(
        cellText=list(zip(*col_data)),
        colLabels=col_labels,
        cellLoc="left",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7.5)
    tbl.scale(1, 1.4)

    # 헤더 스타일
    for j in range(len(col_labels)):
        tbl[(0, j)].set_facecolor("#2c3e50")
        tbl[(0, j)].set_text_props(color="white", fontweight="bold")

    # 행 음영 + 요인별 컬러
    for i, row_d in enumerate(top.itertuples(), start=1):
        fc = FACTOR_COLORS.get(row_d.factor, "#95a5a6")
        tbl[(i, 7)].set_facecolor(fc)
        tbl[(i, 7)].set_text_props(color="white", fontsize=7)
        bg = "#f8f9fa" if i % 2 == 0 else "white"
        for j in range(7):
            tbl[(i, j)].set_facecolor(bg)
        # Cohen's h 컬럼 크기별 음영
        h = row_d.cohen_h
        if h >= 0.8:
            tbl[(i, 1)].set_facecolor("#fadbd8")
        elif h >= 0.5:
            tbl[(i, 1)].set_facecolor("#fdebd0")
        elif h >= 0.2:
            tbl[(i, 1)].set_facecolor("#fef9e7")

    ax.set_title(
        "표 1. 고립·은둔청년 판별 문항 통계 검정 결과 (상위 30개, p<.05)\n"
        "* Cohen's h: ≥0.2 소, ≥0.5 중, ≥0.8 대 효과 크기",
        fontsize=12, fontweight="bold", pad=20,
    )
    plt.tight_layout()
    path = FIG_DIR / "fig1_summary_table.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# =============================================================================
# FIGURE 2 — Forest Plot (Cohen's h + 95% CI)
# =============================================================================

def fig_forest_plot(df: pd.DataFrame):
    sig = df[df["significant"] & (df["cohen_h"] >= 0.2)].head(25).copy()
    sig["label"] = sig.apply(
        lambda r: f"{_section_short(r.section)}\n  [{r.category[:18]}]", axis=1
    )
    sig = sig.sort_values("cohen_h")

    fig, ax = plt.subplots(figsize=(13, 12))
    y = np.arange(len(sig))

    for i, (_, row) in enumerate(sig.iterrows()):
        fc = FACTOR_COLORS.get(row.factor, "#95a5a6")
        ax.barh(i, row.cohen_h, left=0, height=0.5, color=fc, alpha=0.85)
        ax.errorbar(
            x=row.cohen_h, y=i,
            xerr=[[row.cohen_h - row.ci_lo], [row.ci_hi - row.cohen_h]],
            fmt="none", color="#2c3e50", capsize=4, linewidth=1.5,
        )
        direction = "↑고립" if row.diff_pct > 0 else "↑일반"
        ax.text(row.ci_hi + 0.02, i, f"h={row.cohen_h:.3f} ({direction})",
                va="center", fontsize=7.5)

    # 효과 크기 기준선
    for x_val, lbl, clr in [(0.2, "소", "#27ae60"), (0.5, "중", "#f39c12"), (0.8, "대", "#e74c3c")]:
        ax.axvline(x_val, color=clr, linestyle="--", alpha=0.6, linewidth=1)
        ax.text(x_val, len(sig) - 0.3, lbl, color=clr, fontsize=8, ha="center")

    ax.set_yticks(y)
    ax.set_yticklabels(sig["label"].tolist(), fontsize=7.5)
    ax.set_xlabel("Cohen's h (효과 크기)", fontsize=11)
    ax.set_title(
        "그림 1. Forest Plot — 고립·은둔청년 판별 문항 효과 크기 (95% CI)\n"
        "(유의미 문항 상위 25개, 요인별 색상 구분)",
        fontsize=12, fontweight="bold",
    )

    # 범례
    patches = [mpatches.Patch(color=c, label=f) for f, c in FACTOR_COLORS.items() if f != "기타"]
    ax.legend(handles=patches, loc="lower right", fontsize=8, framealpha=0.9)
    ax.set_xlim(0, sig["ci_hi"].max() + 0.35)
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    path = FIG_DIR / "fig2_forest_plot.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# =============================================================================
# FIGURE 3 — 요인별 Cohen's h 분포 (Box + Dot)
# =============================================================================

def fig_factor_distribution(df: pd.DataFrame):
    sig = df[df["significant"] & (df["cohen_h"] >= 0.1)].copy()
    factors = [f for f in FACTOR_COLORS if f != "기타"]
    factor_data = {f: sig[sig.factor == f]["cohen_h"].values for f in factors}
    factor_data = {f: v for f, v in factor_data.items() if len(v) > 0}

    fig, ax = plt.subplots(figsize=(12, 6))
    positions = range(len(factor_data))
    labels = list(factor_data.keys())

    bp = ax.boxplot(
        [factor_data[f] for f in labels],
        positions=list(positions),
        patch_artist=True,
        widths=0.5,
        showfliers=False,
    )
    for patch, lbl in zip(bp["boxes"], labels):
        patch.set_facecolor(FACTOR_COLORS.get(lbl, "#95a5a6"))
        patch.set_alpha(0.7)
    for median in bp["medians"]:
        median.set_color("black")
        median.set_linewidth(2)

    # Dot plot 위에 중첩
    for i, lbl in enumerate(labels):
        vals = factor_data[lbl]
        jitter = np.random.uniform(-0.15, 0.15, size=len(vals))
        ax.scatter(
            i + jitter, vals,
            color=FACTOR_COLORS.get(lbl, "#95a5a6"),
            alpha=0.5, s=20, zorder=3,
        )
        ax.text(i, vals.max() + 0.05, f"n={len(vals)}", ha="center", fontsize=8)

    for x_val, lbl, clr in [(0.2, "소(0.2)", "#27ae60"), (0.5, "중(0.5)", "#f39c12"), (0.8, "대(0.8)", "#e74c3c")]:
        ax.axhline(x_val, color=clr, linestyle="--", alpha=0.5, linewidth=1)
        ax.text(len(labels) - 0.5, x_val + 0.01, lbl, color=clr, fontsize=8)

    ax.set_xticks(list(positions))
    ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=10)
    ax.set_ylabel("Cohen's h", fontsize=11)
    ax.set_title("그림 2. 요인별 효과 크기 분포 (은둔청소년 스크리닝 3요인 구조 기반)", fontsize=12, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = FIG_DIR / "fig3_factor_distribution.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# =============================================================================
# FIGURE 4 — 경험적 ROC 곡선 (개별 문항 점수)
# =============================================================================

def fig_roc_curve(df: pd.DataFrame):
    sig = df[df["significant"]].copy()
    # 고립군이 높은 항목: sensitivity = pct_iso/100, 1-spec = pct_gen/100
    # 고립군이 낮은 항목: sensitivity = 1 - pct_iso/100, 1-spec = 1 - pct_gen/100
    roc_pts = []
    for _, r in sig.iterrows():
        if r.diff_pct >= 0:
            sens = r.pct_isolated / 100
            fpr = r.pct_general / 100
        else:
            sens = 1 - r.pct_isolated / 100
            fpr = 1 - r.pct_general / 100
        roc_pts.append((fpr, sens, r.cohen_h, r.factor))

    roc_pts.sort(key=lambda x: x[0])
    fprs = [0] + [p[0] for p in roc_pts] + [1]
    tprs = [0] + [p[1] for p in roc_pts] + [1]
    auc_approx = float(stats.norm.cdf(
        sig["cohen_h"].mean() / math.sqrt(2)
    ))

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 왼쪽: ROC 산점도 (개별 문항)
    ax = axes[0]
    for fpr, tpr, h, fac in roc_pts:
        ax.scatter(fpr, tpr, color=FACTOR_COLORS.get(fac, "#95a5a6"),
                   s=h * 80, alpha=0.6, edgecolors="none")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, linewidth=1)
    ax.set_xlabel("1 - Specificity (위음성률)", fontsize=11)
    ax.set_ylabel("Sensitivity (민감도)", fontsize=11)
    ax.set_title("그림 3a. 개별 문항 ROC 공간 분포\n(원 크기 = Cohen's h)", fontsize=11, fontweight="bold")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.grid(alpha=0.3)
    patches = [mpatches.Patch(color=c, label=f) for f, c in FACTOR_COLORS.items() if f != "기타"]
    ax.legend(handles=patches, fontsize=7.5, loc="lower right", framealpha=0.8)

    # 오른쪽: 복합 ROC 곡선 (binormal 근사)
    ax2 = axes[1]
    h_vals = np.linspace(0, sig["cohen_h"].max() + 0.2, 200)
    mean_h = sig["cohen_h"].mean()
    sd_h = sig["cohen_h"].std()

    # 각 요인별 AUC
    factor_aucs = {}
    for fac in FACTOR_COLORS:
        fac_h = sig[sig.factor == fac]["cohen_h"]
        if len(fac_h) >= 3:
            fac_auc = float(stats.norm.cdf(fac_h.mean() / math.sqrt(2)))
            factor_aucs[fac] = fac_auc

    t = np.linspace(0, 1, 200)
    mu = mean_h / math.sqrt(2)
    tpr_curve = stats.norm.cdf(stats.norm.ppf(t) + mu)
    ax2.fill_between(t, tpr_curve, t, alpha=0.15, color="#e74c3c")
    ax2.plot(t, tpr_curve, color="#e74c3c", linewidth=2.5,
             label=f"합산 (AUC={auc_approx:.3f})")
    ax2.plot([0, 1], [0, 1], "k--", alpha=0.4, linewidth=1, label="무작위(AUC=0.5)")

    # 요인별 ROC
    fac_colors_roc = {"사회단절·고립": "#e74c3c", "회피·사회이행": "#e67e22",
                       "불규칙한 생활방식": "#9b59b6"}
    for fac, auc in factor_aucs.items():
        if fac not in fac_colors_roc:
            continue
        mu_f = stats.norm.ppf(auc) * math.sqrt(2) / math.sqrt(2)
        tpr_f = stats.norm.cdf(stats.norm.ppf(t) + mu_f)
        ax2.plot(t, tpr_f, color=fac_colors_roc[fac], linewidth=1.5,
                 linestyle="--", alpha=0.8, label=f"{fac} (AUC≈{auc:.3f})")

    # 참고: 신뢰타당성분석 PDF HQ-25 AUC
    mu_hq = stats.norm.ppf(0.817) * math.sqrt(2) / math.sqrt(2)
    tpr_hq = stats.norm.cdf(stats.norm.ppf(t) + mu_hq)
    ax2.plot(t, tpr_hq, color="#2980b9", linewidth=1.5, linestyle=":",
             label="HQ-25 참고 (AUC=0.817)")

    ax2.set_xlabel("1 - Specificity", fontsize=11)
    ax2.set_ylabel("Sensitivity", fontsize=11)
    ax2.set_title("그림 3b. ROC 곡선 (Binormal 근사)\n" +
                  "* 신뢰타당성분석 HQ-25 AUC=0.817 참조선 포함",
                  fontsize=11, fontweight="bold")
    ax2.legend(fontsize=8.5, loc="lower right", framealpha=0.9)
    ax2.set_xlim(0, 1); ax2.set_ylim(0, 1)
    ax2.grid(alpha=0.3)
    ax2.text(0.55, 0.10, f"전체 추정 AUC = {auc_approx:.3f}",
             fontsize=11, color="#c0392b", fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#e74c3c"))

    plt.tight_layout()
    path = FIG_DIR / "fig4_roc_curve.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# =============================================================================
# FIGURE 5 — Youden's J + 민감도/특이도 (최적 문항별)
# =============================================================================

def fig_youden(df: pd.DataFrame):
    sig = df[df["significant"] & (df["cohen_h"] >= 0.3)].head(20).copy()
    sig["sens"] = sig.apply(lambda r: r.pct_isolated/100 if r.diff_pct > 0 else 1-r.pct_isolated/100, axis=1)
    sig["spec"] = sig.apply(lambda r: 1-r.pct_general/100 if r.diff_pct > 0 else r.pct_general/100, axis=1)
    sig["youden"] = sig.sens + sig.spec - 1
    sig = sig.sort_values("youden", ascending=True)
    sig["label"] = sig.apply(lambda r: f"{_section_short(r.section)[:22]} [{r.category[:10]}]", axis=1)

    fig, ax = plt.subplots(figsize=(13, 9))
    y = np.arange(len(sig))
    bar_h = 0.28

    ax.barh(y + bar_h/2, sig.sens, bar_h, label="민감도 (Sensitivity)", color="#e74c3c", alpha=0.8)
    ax.barh(y - bar_h/2, sig.spec, bar_h, label="특이도 (Specificity)", color="#3498db", alpha=0.8)

    for i, (_, r) in enumerate(sig.iterrows()):
        ax.text(1.01, i, f"J={r.youden:.3f}", va="center", fontsize=8, color="#2c3e50")

    ax.axvline(0.8, color="#e74c3c", linestyle="--", alpha=0.5, linewidth=1, label="기준 80%")
    ax.set_yticks(y)
    ax.set_yticklabels(sig.label, fontsize=8)
    ax.set_xlabel("비율", fontsize=11)
    ax.set_xlim(0, 1.15)
    ax.set_title(
        "그림 4. 문항별 민감도/특이도 및 Youden's J Index\n"
        "(은둔청소년 척도 PDF: 사회단절·고립 J=0.835, 회피 J=0.726, 불규칙생활 J=0.601 참조)",
        fontsize=11, fontweight="bold",
    )
    ax.legend(fontsize=9, loc="lower right")
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    path = FIG_DIR / "fig5_youden_sensitivity_specificity.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# =============================================================================
# FIGURE 6 — 최적 12문항 가중치 + 요인 구조 대시보드
# =============================================================================

def fig_optimal_items_dashboard(df: pd.DataFrame):
    if not (RESULTS_DIR / "screening_items_final.json").exists():
        print("  [SKIP] screening_items_final.json 없음")
        return

    with open(RESULTS_DIR / "screening_items_final.json", encoding="utf-8") as f:
        items = json.load(f)
    opt = pd.DataFrame(items).sort_values("rank")

    fig = plt.figure(figsize=(18, 11))
    gs = GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.4)

    # ── 왼쪽: 가중치 가로 막대 ──
    ax1 = fig.add_subplot(gs[:, 0])
    labels = [f"#{r['rank']} {_section_short(r['section'])[:18]}\n[{r['category'][:14]}]"
              for r in items]
    weights = [r["weight"] for r in items]
    colors  = [FACTOR_COLORS.get(
        _assign_factor(r["section"]), "#95a5a6"
    ) for r in items]
    bars = ax1.barh(range(len(items))[::-1], weights, color=colors, alpha=0.85)
    ax1.set_yticks(range(len(items))[::-1])
    ax1.set_yticklabels(labels, fontsize=7.5)
    ax1.set_xlabel("가중치 (%)", fontsize=10)
    ax1.set_title("최적 12문항\n가중치 분포", fontsize=11, fontweight="bold")
    for bar, w in zip(bars, weights):
        ax1.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                 f"{w:.1f}%", va="center", fontsize=8)
    ax1.grid(axis="x", alpha=0.3)

    # ── 오른쪽 상단: 도넛 차트 (요인 비율) ──
    ax2 = fig.add_subplot(gs[0, 1])
    opt["factor"] = opt["section"].apply(_assign_factor)
    fac_counts = opt.groupby("factor")["weight"].sum()
    fc_colors = [FACTOR_COLORS.get(f, "#95a5a6") for f in fac_counts.index]
    wedges, texts, autotexts = ax2.pie(
        fac_counts.values, labels=fac_counts.index,
        colors=fc_colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.75,
        wedgeprops=dict(width=0.5),
    )
    for t in texts:
        t.set_fontsize(8)
    for at in autotexts:
        at.set_fontsize(8)
    ax2.set_title("요인별 가중치 비율", fontsize=11, fontweight="bold")

    # ── 오른쪽 중단: p값 분포 히스토그램 ──
    ax3 = fig.add_subplot(gs[0, 2])
    sig = df[df["significant"]].copy()
    ax3.hist(sig["cohen_h"], bins=20, color="#3498db", edgecolor="white", alpha=0.8)
    for x_val, lbl, clr in [(0.2, "소(0.2)", "#27ae60"), (0.5, "중(0.5)", "#f39c12"), (0.8, "대(0.8)", "#e74c3c")]:
        ax3.axvline(x_val, color=clr, linestyle="--", linewidth=1.5)
        ax3.text(x_val + 0.01, ax3.get_ylim()[1] * 0.85 if ax3.get_ylim()[1] > 0 else 1,
                 lbl, color=clr, fontsize=8)
    ax3.set_xlabel("Cohen's h", fontsize=10)
    ax3.set_ylabel("문항 수", fontsize=10)
    ax3.set_title(f"유의미 문항 효과 크기 분포\n(n={len(sig)})", fontsize=11, fontweight="bold")
    ax3.grid(alpha=0.3)

    # ── 오른쪽 하단: 고립군 vs 일반군 비율 비교 (상위 10항목) ──
    ax4 = fig.add_subplot(gs[1, 1:])
    top10 = df[df["significant"]].head(10).copy()
    top10 = top10.sort_values("cohen_h", ascending=True)
    top10["short_label"] = top10.apply(
        lambda r: f"{_section_short(r.section)[:15]} [{r.category[:10]}]", axis=1
    )
    y_pos = np.arange(len(top10))
    ax4.barh(y_pos - 0.2, top10["pct_isolated"], 0.35, label="고립은둔 청년", color="#e74c3c", alpha=0.8)
    ax4.barh(y_pos + 0.2, top10["pct_general"],  0.35, label="미해당(일반)",  color="#3498db", alpha=0.8)
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(top10["short_label"], fontsize=8)
    ax4.set_xlabel("응답 비율 (%)", fontsize=10)
    ax4.set_title("상위 10문항: 고립은둔 vs 일반 집단 응답 비율 비교", fontsize=11, fontweight="bold")
    ax4.legend(fontsize=9)
    ax4.grid(axis="x", alpha=0.3)

    fig.suptitle(
        "고립·은둔 청년 판별 스크리닝 문항 선별 종합 대시보드\n"
        "(서울시 고립은둔청년 실태조사 N=5,513, 고립은둔 N=486 vs 일반 N=5,027)",
        fontsize=13, fontweight="bold", y=1.01,
    )

    path = FIG_DIR / "fig6_dashboard.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# =============================================================================
# FIGURE 7 — p값 히트맵 (요인 × 항목군)
# =============================================================================

def fig_pvalue_heatmap(df: pd.DataFrame):
    sig = df.copy()
    sig["var"] = sig["section"].apply(lambda s: re.search(r"【([A-Z]+\d+)", s).group(1)
                                       if re.search(r"【([A-Z]+\d+)", s) else "기타")
    sig["factor"] = sig["section"].apply(_assign_factor)

    # 각 (factor, var) 조합의 최대 Cohen's h 집계
    pivot = sig.groupby(["factor", "var"])["cohen_h"].max().reset_index()
    pivot_table = pivot.pivot(index="factor", columns="var", values="cohen_h").fillna(0)

    # 컬럼 수가 많으면 h 평균 상위 25개만
    top_vars = pivot.groupby("var")["cohen_h"].max().nlargest(25).index
    pivot_table = pivot_table[[c for c in pivot_table.columns if c in top_vars]]

    import matplotlib.colors as mcolors
    cmap = plt.cm.YlOrRd

    fig, ax = plt.subplots(figsize=(20, 6))
    im = ax.imshow(pivot_table.values, cmap=cmap, aspect="auto", vmin=0, vmax=1.3)

    ax.set_xticks(range(len(pivot_table.columns)))
    ax.set_xticklabels(pivot_table.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(pivot_table.index)))
    ax.set_yticklabels(pivot_table.index, fontsize=9)

    for i in range(len(pivot_table.index)):
        for j in range(len(pivot_table.columns)):
            val = pivot_table.values[i, j]
            if val > 0:
                txt_col = "white" if val > 0.8 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=7, color=txt_col)

    plt.colorbar(im, ax=ax, label="Cohen's h (최대값)", fraction=0.02)
    ax.set_title("그림 5. 요인 × 변수 Cohen's h 히트맵 (상위 25개 변수)", fontsize=12, fontweight="bold")
    plt.tight_layout()
    path = FIG_DIR / "fig7_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# =============================================================================
# 메인
# =============================================================================

def main():
    print("=" * 60)
    print("고립·은둔청년 판별 스크리닝 시각화 파이프라인")
    print("(신뢰타당성분석.pdf + 은둔청소년 스크리닝 척도 개발.pdf 기반)")
    print("=" * 60)

    print("\n[데이터 로딩 중...]")
    df = load_data()
    print(f"  로드: {len(df)}개 레코드 | 유의미: {df.significant.sum()}개")

    print("\n[Figure 1] 종합 통계 테이블...")
    fig_summary_table(df)

    print("[Figure 2] Forest Plot (Cohen's h + 95% CI)...")
    fig_forest_plot(df)

    print("[Figure 3] 요인별 효과 크기 분포...")
    fig_factor_distribution(df)

    print("[Figure 4] ROC 곡선 (경험적 + Binormal 근사)...")
    fig_roc_curve(df)

    print("[Figure 5] Youden's J + 민감도/특이도...")
    fig_youden(df)

    print("[Figure 6] 최적 12문항 대시보드...")
    fig_optimal_items_dashboard(df)

    print("[Figure 7] 요인×변수 Cohen's h 히트맵...")
    fig_pvalue_heatmap(df)

    # 요약 출력
    print("\n" + "=" * 60)
    print("분석 요약 (PDF 방법론 기준)")
    print("=" * 60)
    print(f"  총 분석 문항:      {len(df)}개")
    print(f"  통계 유의 (p<.05): {df.significant.sum()}개")
    print(f"  소 효과 이상 (h≥.2): {(df.significant & (df.cohen_h>=0.2)).sum()}개")
    print(f"  중 효과 이상 (h≥.5): {(df.significant & (df.cohen_h>=0.5)).sum()}개")
    print(f"  대 효과 이상 (h≥.8): {(df.significant & (df.cohen_h>=0.8)).sum()}개")
    print(f"  추정 AUC (Proxy):  {stats.norm.cdf(df[df.significant].cohen_h.mean()/math.sqrt(2)):.3f}")
    print(f"  [참조] HQ-25 AUC = 0.817 (신뢰타당성분석.pdf)")
    print(f"  [참조] 스크리닝 척도 AUC = 사회단절.929 / 회피.888 / 불규칙생활.818")
    print(f"\n  저장 경로: {FIG_DIR}/")
    for p in sorted(FIG_DIR.glob("*.png")):
        print(f"    · {p.name}")


if __name__ == "__main__":
    main()
