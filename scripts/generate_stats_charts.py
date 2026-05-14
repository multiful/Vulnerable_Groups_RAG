# Content Hash: SHA256:TBD
# Role: DIDIM 통계 시각화 생성 스크립트
# 출력: docs/slides/*.png
# 데이터 소스:
#   - frontend/public/data/cert_candidates.json (1,290 자격증)
#   - data/raw/csv/한국산업인력공단_연도별 회별 국가기술자격 _rows.csv
#   - data/raw/csv/전공별 취득 현황_rows.csv
#   - data/raw/csv/행정구역별연도별성별 취득현황_rows.csv
#   - data/raw/csv/고용24 직업정보상세 요약.csv
#   - data/canonical/candidates/cert_candidates.jsonl
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

# ── 한글 폰트 설정 ─────────────────────────────────────────────────────────────
def _setup_korean_font():
    """macOS / Linux 환경에서 한글 폰트를 찾아 적용."""
    candidates = [
        "AppleGothic", "Apple SD Gothic Neo", "NanumGothic",
        "NanumBarunGothic", "Malgun Gothic", "DejaVu Sans",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for c in candidates:
        if c in available:
            plt.rcParams["font.family"] = c
            break
    plt.rcParams["axes.unicode_minus"] = False

_setup_korean_font()

ROOT = Path(__file__).parents[1]
SLIDES = ROOT / "docs" / "slides"
SLIDES.mkdir(parents=True, exist_ok=True)

# ── 공통 스타일 ────────────────────────────────────────────────────────────────
PALETTE_MAIN   = ["#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]
PALETTE_GRADE  = {
    "1_기능사":   "#10b981",
    "2_산업기사": "#0ea5e9",
    "3_기사":     "#6366f1",
    "4_기술사":   "#8b5cf6",
    "5_기능장":   "#f59e0b",
    "":           "#94a3b8",
}
GRADE_LABEL = {
    "1_기능사":   "기능사",
    "2_산업기사": "산업기사",
    "3_기사":     "기사",
    "4_기술사":   "기술사",
    "5_기능장":   "기능장",
    "":           "비기술",
}
DOMAIN_NAMES: dict[str, str] = {
    "domain_0001":"데이터/AI","domain_0002":"소프트웨어개발","domain_0003":"IT인프라/보안",
    "domain_0004":"네트워크/통신","domain_0005":"전기/전자","domain_0006":"건설/토목",
    "domain_0007":"기계/제조","domain_0008":"화학/바이오","domain_0009":"식품/환경",
    "domain_0010":"경영/행정","domain_0011":"회계/세무","domain_0012":"금융/보험",
    "domain_0013":"법률/행정","domain_0014":"교육/상담","domain_0015":"사회복지",
    "domain_0016":"보건/의료","domain_0017":"물류/유통","domain_0018":"마케팅/광고",
    "domain_0019":"디자인/콘텐츠","domain_0020":"영상/방송","domain_0021":"관광/호텔",
    "domain_0022":"조리/식음료","domain_0023":"뷰티/패션","domain_0024":"스포츠/레저",
    "domain_0025":"농업/임업","domain_0026":"에너지/자원","domain_0027":"안전/소방",
    "domain_0028":"차량/운송","domain_0029":"항공/해운","domain_0030":"부동산/임대",
    "domain_0031":"인사/노무","domain_0032":"무역/통상","domain_0033":"창업/경영컨설팅",
    "domain_0034":"공공/복지","domain_0035":"도서관/기록","domain_0036":"군사/안보",
    "domain_0037":"소방/방재","domain_0038":"환경/에너지안전","domain_0039":"조선/해양",
    "domain_0040":"항만/물류",
}
RISK_LABELS = {
    "risk_0001":"1단계\n취업 안정권",
    "risk_0002":"2단계\n준비 활성",
    "risk_0003":"3단계\n준비 정체",
    "risk_0004":"4단계\n고위험군",
    "risk_0005":"5단계\n최고위험군",
}

def _fig_save(fig: plt.Figure, name: str):
    path = SLIDES / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✅ {name}")

# ══════════════════════════════════════════════════════════════════════════════
# 1. 자격증 등급 분포 (pie)
# ══════════════════════════════════════════════════════════════════════════════
def chart_grade_distribution(data: list[dict]):
    grade_cnt: dict[str, int] = {}
    for c in data:
        g = c.get("cert_grade_tier", "")
        grade_cnt[g] = grade_cnt.get(g, 0) + 1

    order = ["1_기능사","2_산업기사","3_기사","4_기술사","5_기능장",""]
    labels = [GRADE_LABEL[g] for g in order if g in grade_cnt]
    sizes  = [grade_cnt[g] for g in order if g in grade_cnt]
    colors = [PALETTE_GRADE[g] for g in order if g in grade_cnt]

    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, colors=colors,
        autopct=lambda p: f"{p:.1f}%\n({int(p*sum(sizes)/100)}종)",
        startangle=140, pctdistance=0.78,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    for at in autotexts:
        at.set_fontsize(9)
        at.set_fontweight("bold")
        at.set_color("white")

    ax.legend(
        wedges, labels,
        title="등급", loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=11,
    )
    ax.set_title("DIDIM 추천 자격증 등급 분포\n(총 1,290종)", fontsize=15, fontweight="bold", pad=18)
    _fig_save(fig, "01_cert_grade_distribution.png")


# ══════════════════════════════════════════════════════════════════════════════
# 2. 합격률 분포 히스토그램
# ══════════════════════════════════════════════════════════════════════════════
def chart_pass_rate_histogram(data: list[dict]):
    rates = [c["avg_pass_rate_3yr"] for c in data if c.get("avg_pass_rate_3yr") is not None]

    fig, ax = plt.subplots(figsize=(9, 5))
    n, bins, patches = ax.hist(rates, bins=20, color="#6366f1", edgecolor="white", linewidth=0.8, alpha=0.9)

    # 구간별 색상
    for patch, left in zip(patches, bins[:-1]):
        if left < 20:
            patch.set_facecolor("#ef4444")
        elif left < 40:
            patch.set_facecolor("#f59e0b")
        elif left < 60:
            patch.set_facecolor("#0ea5e9")
        else:
            patch.set_facecolor("#10b981")

    avg_rate = sum(rates) / len(rates)
    ax.axvline(avg_rate, color="#1e293b", linestyle="--", linewidth=1.8, label=f"평균 {avg_rate:.1f}%")
    ax.set_xlabel("3년 평균 합격률 (%)", fontsize=12)
    ax.set_ylabel("자격증 수 (종)", fontsize=12)
    ax.set_title(f"국가기술자격 합격률 분포\n(데이터 보유 {len(rates)}종 / 전체 1,290종)", fontsize=14, fontweight="bold", pad=12)
    ax.legend(fontsize=11)

    legend_patches = [
        mpatches.Patch(color="#ef4444", label="어려움 (<20%)"),
        mpatches.Patch(color="#f59e0b", label="보통 (20~40%)"),
        mpatches.Patch(color="#0ea5e9", label="양호 (40~60%)"),
        mpatches.Patch(color="#10b981", label="취득 용이 (>60%)"),
    ]
    ax.legend(handles=legend_patches + [
        mpatches.Patch(color="#1e293b", label=f"평균 {avg_rate:.1f}%")
    ], loc="upper right", fontsize=9.5)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    _fig_save(fig, "02_pass_rate_histogram.png")


# ══════════════════════════════════════════════════════════════════════════════
# 3. 도메인별 추천 자격증 수 (상위 15)
# ══════════════════════════════════════════════════════════════════════════════
def chart_domain_distribution(data: list[dict]):
    domain_cnt: dict[str, int] = {}
    for c in data:
        d = c.get("primary_domain", "unknown")
        domain_cnt[d] = domain_cnt.get(d, 0) + 1

    sorted_domains = sorted(domain_cnt.items(), key=lambda x: -x[1])[:15]
    labels = [DOMAIN_NAMES.get(d, d) for d, _ in sorted_domains]
    counts = [v for _, v in sorted_domains]
    colors = [PALETTE_MAIN[i % len(PALETTE_MAIN)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(labels[::-1], counts[::-1], color=colors[::-1], height=0.7, edgecolor="white")
    for bar, count in zip(bars, counts[::-1]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{count}종", va="center", fontsize=10, fontweight="bold", color="#1e293b")
    ax.set_xlabel("자격증 수 (종)", fontsize=12)
    ax.set_title("분야별 추천 자격증 수 (상위 15개 도메인)", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlim(0, max(counts) * 1.18)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.3)
    _fig_save(fig, "03_domain_distribution.png")


# ══════════════════════════════════════════════════════════════════════════════
# 4. 위험군 단계별 추천 자격증 커버리지
# ══════════════════════════════════════════════════════════════════════════════
def chart_risk_stage_coverage(data: list[dict]):
    stage_cnt: dict[str, int] = {}
    stage_order = ["risk_0001","risk_0002","risk_0003","risk_0004","risk_0005"]
    for s in stage_order:
        stage_cnt[s] = 0
    for c in data:
        for s in c.get("recommended_risk_stages", []):
            if s in stage_cnt:
                stage_cnt[s] += 1

    labels = [RISK_LABELS[s] for s in stage_order]
    counts = [stage_cnt[s] for s in stage_order]
    stage_colors = ["#10b981","#0ea5e9","#6366f1","#f59e0b","#ef4444"]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(labels, counts, color=stage_colors, width=0.6, edgecolor="white", linewidth=1.5)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 12,
                f"{count}종", ha="center", fontsize=11, fontweight="bold", color="#1e293b")
    ax.set_ylabel("추천 자격증 수 (중복 허용)", fontsize=12)
    ax.set_title("위험군 단계별 추천 자격증 커버리지\n(1단계=취업 안정권 ↔ 5단계=최고위험군)", fontsize=14, fontweight="bold", pad=12)
    ax.set_ylim(0, max(counts) * 1.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    _fig_save(fig, "04_risk_stage_coverage.png")


# ══════════════════════════════════════════════════════════════════════════════
# 5. 등급별 평균 합격률
# ══════════════════════════════════════════════════════════════════════════════
def chart_pass_rate_by_grade(data: list[dict]):
    grade_rates: dict[str, list] = {}
    for c in data:
        g = c.get("cert_grade_tier", "")
        r = c.get("avg_pass_rate_3yr")
        if g and r is not None and g != "":
            grade_rates.setdefault(g, []).append(r)

    order = ["1_기능사","2_산업기사","3_기사","4_기술사","5_기능장"]
    labels, avgs, stds, ns = [], [], [], []
    for g in order:
        if g in grade_rates:
            vals = grade_rates[g]
            labels.append(GRADE_LABEL[g])
            avgs.append(np.mean(vals))
            stds.append(np.std(vals))
            ns.append(len(vals))

    colors = [PALETTE_GRADE[g] for g in order if g in grade_rates]
    x = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(x, avgs, yerr=stds, color=colors, width=0.55,
                  edgecolor="white", linewidth=1.5,
                  error_kw={"elinewidth": 1.5, "ecolor": "#475569", "capsize": 5})
    for i, (bar, avg, n) in enumerate(zip(bars, avgs, ns)):
        ax.text(bar.get_x() + bar.get_width() / 2, avg + max(stds) * 0.08,
                f"{avg:.1f}%\n(n={n})", ha="center", fontsize=10, fontweight="bold", color="#1e293b")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel("3년 평균 합격률 (%)", fontsize=12)
    ax.set_title("등급별 평균 합격률 비교\n(오차막대: 표준편차)", fontsize=14, fontweight="bold", pad=12)
    ax.set_ylim(0, max(avgs) * 1.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    _fig_save(fig, "05_pass_rate_by_grade.png")


# ══════════════════════════════════════════════════════════════════════════════
# 6. 연도별 회별 합격률 추세 (상위 5개 등급)
# ══════════════════════════════════════════════════════════════════════════════
def chart_yearly_pass_rate_trend(csv_path: Path):
    if not csv_path.exists():
        print(f"  ⚠️  {csv_path.name} not found, skipping")
        return

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    # 필기만 사용
    df = df[df["examTypCcd"] == "필기"].copy()
    df["passRateNum"] = pd.to_numeric(df["passRateNum"], errors="coerce")
    df = df.dropna(subset=["passRateNum", "implYy"])

    grade_order = ["기능사","산업기사","기사","기술사","기능장"]
    grade_colors = {"기능사":"#10b981","산업기사":"#0ea5e9","기사":"#6366f1","기술사":"#8b5cf6","기능장":"#f59e0b"}

    yearly = (
        df.groupby(["implYy", "grdNm"])["passRateNum"]
        .mean()
        .reset_index()
        .rename(columns={"implYy": "year", "grdNm": "grade", "passRateNum": "avg_rate"})
    )

    fig, ax = plt.subplots(figsize=(10, 5.5))
    for grade in grade_order:
        sub = yearly[yearly["grade"] == grade].sort_values("year")
        if sub.empty:
            continue
        ax.plot(sub["year"], sub["avg_rate"], marker="o", linewidth=2.2, markersize=6,
                label=grade, color=grade_colors.get(grade, "#94a3b8"))

    ax.set_xlabel("연도", fontsize=12)
    ax.set_ylabel("필기 평균 합격률 (%)", fontsize=12)
    ax.set_title("연도별 국가기술자격 등급별 필기 합격률 추세\n(한국산업인력공단 공공데이터)", fontsize=13, fontweight="bold", pad=12)
    ax.legend(fontsize=10, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.3)
    _fig_save(fig, "06_yearly_pass_rate_trend.png")


# ══════════════════════════════════════════════════════════════════════════════
# 7. 전공별 상위 취득 자격증 (Top 10 전공)
# ══════════════════════════════════════════════════════════════════════════════
def chart_major_cert_acquisition(csv_path: Path):
    if not csv_path.exists():
        print(f"  ⚠️  {csv_path.name} not found, skipping")
        return

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    # 전공계열(mdobligFldNm)별 누적 취득수(accumAcquCnt) 집계
    df["accumAcquCnt"] = pd.to_numeric(df["accumAcquCnt"], errors="coerce").fillna(0)
    major_total = (
        df.groupby("mdobligFldNm")["accumAcquCnt"]
        .sum()
        .sort_values(ascending=False)
        .head(12)
    )

    fig, ax = plt.subplots(figsize=(10, 6.5))
    colors = [PALETTE_MAIN[i % len(PALETTE_MAIN)] for i in range(len(major_total))]
    bars = ax.barh(major_total.index[::-1], major_total.values[::-1], color=colors[::-1], height=0.65, edgecolor="white")
    for bar, val in zip(bars, major_total.values[::-1]):
        ax.text(bar.get_width() + max(major_total.values) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{int(val):,}명", va="center", fontsize=9.5, color="#1e293b")
    ax.set_xlabel("누적 자격증 취득자 수 (명)", fontsize=12)
    ax.set_title("전공 계열별 국가기술자격 누적 취득 현황 (상위 12개)\n(한국산업인력공단 2025년 통계)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(0, max(major_total.values) * 1.18)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.3)
    _fig_save(fig, "07_major_cert_acquisition.png")


# ══════════════════════════════════════════════════════════════════════════════
# 8. 지역별 자격증 취득 현황
# ══════════════════════════════════════════════════════════════════════════════
def chart_regional_distribution(csv_path: Path):
    if not csv_path.exists():
        print(f"  ⚠️  {csv_path.name} not found, skipping")
        return

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["accumAcquCnt"] = pd.to_numeric(df["accumAcquCnt"], errors="coerce").fillna(0)
    regional = (
        df.groupby("sido")["accumAcquCnt"]
        .sum()
        .sort_values(ascending=False)
    )

    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = ["#6366f1" if s in ["서울","경기","인천"] else "#0ea5e9" for s in regional.index]
    bars = ax.bar(regional.index, regional.values, color=colors, edgecolor="white", linewidth=1)
    ax.set_ylabel("누적 취득자 수 (명)", fontsize=12)
    ax.set_title("지역별 국가기술자격 누적 취득 현황\n(한국산업인력공단 2025년 통계)", fontsize=13, fontweight="bold", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    plt.xticks(fontsize=9)
    _fig_save(fig, "08_regional_distribution.png")


# ══════════════════════════════════════════════════════════════════════════════
# 9. 고용24 직업 만족도 & 일자리전망 (상위 20개 직업)
# ══════════════════════════════════════════════════════════════════════════════
def chart_job_satisfaction(csv_path: Path):
    if not csv_path.exists():
        print(f"  ⚠️  {csv_path.name} not found, skipping")
        return

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["직업만족도(%)"] = pd.to_numeric(df["직업만족도(%)"], errors="coerce")
    df = df.dropna(subset=["직업만족도(%)","직업 소분류명"]).copy()
    df = df.drop_duplicates("직업 소분류명")

    top20 = df.nlargest(20, "직업만족도(%)")

    fig, ax = plt.subplots(figsize=(11, 8))
    colors = ["#10b981" if s >= 70 else "#0ea5e9" if s >= 60 else "#f59e0b"
              for s in top20["직업만족도(%)"]]
    bars = ax.barh(top20["직업 소분류명"][::-1], top20["직업만족도(%)"][::-1],
                   color=colors[::-1], height=0.65, edgecolor="white")
    for bar, val in zip(bars, top20["직업만족도(%)"][::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=9, fontweight="bold")
    ax.set_xlabel("직업 만족도 (%)", fontsize=12)
    ax.set_xlim(0, 100)
    ax.axvline(60, color="#ef4444", linestyle="--", linewidth=1.2, alpha=0.6, label="60% 기준선")
    ax.legend(fontsize=9)
    ax.set_title("직업별 만족도 상위 20개 (고용24 직업정보)\n자격증과 연결된 직업의 실제 만족도 데이터", fontsize=13, fontweight="bold", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.3)
    _fig_save(fig, "09_job_satisfaction_top20.png")


# ══════════════════════════════════════════════════════════════════════════════
# 10. 합격률 상위/하위 자격증 (Top 10 / Bottom 10)
# ══════════════════════════════════════════════════════════════════════════════
def chart_top_bottom_certs(data: list[dict]):
    rated = [(c["cert_name"], c["avg_pass_rate_3yr"], c.get("cert_grade_tier",""))
             for c in data if c.get("avg_pass_rate_3yr") is not None]
    rated.sort(key=lambda x: -x[1])
    top10    = rated[:10]
    bottom10 = [r for r in rated if r[1] > 0][-10:]  # 0% 제외

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    def _horizontal_bar(ax, items, title, cmap_color):
        names = [n[:12] + "…" if len(n) > 13 else n for n, _, _ in items]
        rates = [r for _, r, _ in items]
        ax.barh(names[::-1], rates[::-1], color=cmap_color, height=0.65, edgecolor="white")
        for i, (rate, (name, r, grade)) in enumerate(zip(rates[::-1], items[::-1])):
            ax.text(rate + 0.5, i, f"{rate:.1f}%  [{GRADE_LABEL.get(grade, grade)}]",
                    va="center", fontsize=8.5, color="#1e293b")
        ax.set_xlim(0, max(rates) * 1.35)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="x", alpha=0.3)
        ax.set_xlabel("3년 평균 합격률 (%)", fontsize=10)

    _horizontal_bar(ax1, top10, "합격률 상위 10개 자격증\n(취득 진입 장벽 낮음)", "#10b981")
    _horizontal_bar(ax2, bottom10, "합격률 하위 10개 자격증\n(고난이도 — 단계별 준비 권장)", "#ef4444")

    fig.suptitle("DIDIM 추천 자격증 합격률 비교\n(한국산업인력공단 3년 평균)", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout(pad=2)
    _fig_save(fig, "10_top_bottom_pass_rate.png")


# ══════════════════════════════════════════════════════════════════════════════
# 11. DIDIM 데이터 파이프라인 커버리지 요약
# ══════════════════════════════════════════════════════════════════════════════
def chart_data_coverage_summary(data: list[dict]):
    categories = [
        "자격증 DB 총계",
        "합격률 데이터 보유",
        "도메인 분류 완료",
        "직무 연결 완료",
        "위험군 매핑 완료",
        "로드맵 경로 매핑",
    ]
    has_pass    = sum(1 for c in data if c.get("avg_pass_rate_3yr") is not None)
    has_domain  = sum(1 for c in data if c.get("primary_domain"))
    has_jobs    = sum(1 for c in data if c.get("related_jobs"))
    has_risk    = sum(1 for c in data if c.get("recommended_risk_stages"))
    has_roadmap = sum(1 for c in data if c.get("roadmap_stages"))
    total       = len(data)

    counts = [total, has_pass, has_domain, has_jobs, has_risk, has_roadmap]
    pcts   = [100, has_pass/total*100, has_domain/total*100,
               has_jobs/total*100, has_risk/total*100, has_roadmap/total*100]
    colors = ["#6366f1","#0ea5e9","#10b981","#10b981","#10b981","#f59e0b"]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.barh(categories[::-1], pcts[::-1], color=colors[::-1], height=0.6, edgecolor="white")
    for bar, pct, cnt in zip(bars, pcts[::-1], counts[::-1]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}%  ({cnt:,}종)", va="center", fontsize=10, fontweight="bold", color="#1e293b")
    ax.set_xlim(0, 120)
    ax.set_xlabel("데이터 완성도 (%)", fontsize=12)
    ax.set_title(f"DIDIM Canonical 데이터 레이어 커버리지\n(전체 자격증 {total:,}종 기준)", fontsize=13, fontweight="bold", pad=12)
    ax.axvline(100, color="#94a3b8", linestyle="--", linewidth=1, alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.3)
    _fig_save(fig, "11_data_coverage_summary.png")


# ══════════════════════════════════════════════════════════════════════════════
# 12. 아키텍처 API 연동 현황 요약
# ══════════════════════════════════════════════════════════════════════════════
def chart_api_integration_status():
    apis = [
        ("Q-Net 시험일정",        "✅ 활성", 100, "#10b981"),
        ("Q-Net 접수일정",        "✅ 활성", 100, "#10b981"),
        ("WorkNet 채용정보",      "✅ 활성", 100, "#10b981"),
        ("Work24 훈련과정",       "✅ 활성", 100, "#10b981"),
        ("서울시 일자리카페",      "✅ 활성", 100, "#10b981"),
        ("서울시 건강증진센터",    "✅ 활성", 100, "#10b981"),
        ("서울시 공공서비스예약",  "✅ 활성", 100, "#10b981"),
        ("YouTube 강의 추천",     "✅ 활성", 100, "#10b981"),
        ("Kakao 지도 시각화",     "✅ 활성", 100, "#10b981"),
        ("Kakao REST 지오코딩",   "✅ 활성", 100, "#10b981"),
        ("커리어넷 학과/직업",     "⚙️ 통합중", 50, "#f59e0b"),
        ("과정평가형 자격",        "✅ 활성", 100, "#10b981"),
        ("RAG Evidence 검색",     "✅ 활성", 100, "#10b981"),
        ("GOMS 대졸자 분석",      "📊 분석중", 60, "#0ea5e9"),
    ]

    labels  = [a[0] for a in apis]
    pcts    = [a[2] for a in apis]
    colors  = [a[3] for a in apis]
    statuss = [a[1] for a in apis]

    fig, ax = plt.subplots(figsize=(11, 7))
    bars = ax.barh(labels[::-1], pcts[::-1], color=colors[::-1], height=0.65, edgecolor="white")
    for bar, status in zip(bars, statuss[::-1]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                status, va="center", fontsize=10)
    ax.set_xlim(0, 130)
    ax.set_xlabel("연동 완성도 (%)", fontsize=12)
    ax.set_title("DIDIM Execution Layer — 실시간 API 연동 현황\n(2026년 5월 기준)", fontsize=13, fontweight="bold", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.3)
    _fig_save(fig, "12_api_integration_status.png")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("📊 DIDIM 통계 시각화 생성 시작")
    print(f"   출력 경로: {SLIDES}")

    # 자격증 데이터 로드
    cand_path = ROOT / "frontend" / "public" / "data" / "cert_candidates.json"
    with open(cand_path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"   자격증 데이터: {len(data)}종 로드 완료")

    # CSV 경로
    csv_root = ROOT / "data" / "raw" / "csv"
    pass_rate_csv  = csv_root / "한국산업인력공단_연도별 회별 국가기술자격 _rows.csv"
    major_csv      = csv_root / "전공별 취득 현황_rows.csv"
    regional_csv   = csv_root / "행정구역별연도별성별 취득현황_rows.csv"
    job_csv        = csv_root / "고용24 직업정보상세 요약.csv"

    print("\n차트 생성 중…")
    chart_grade_distribution(data)
    chart_pass_rate_histogram(data)
    chart_domain_distribution(data)
    chart_risk_stage_coverage(data)
    chart_pass_rate_by_grade(data)
    chart_yearly_pass_rate_trend(pass_rate_csv)
    chart_major_cert_acquisition(major_csv)
    chart_regional_distribution(regional_csv)
    chart_job_satisfaction(job_csv)
    chart_top_bottom_certs(data)
    chart_data_coverage_summary(data)
    chart_api_integration_status()

    print(f"\n✅ 완료! {len(list(SLIDES.glob('*.png')))}개 PNG → {SLIDES}")

if __name__ == "__main__":
    main()
