# File: generate_charts_13_18.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 통계 차트 13~18 + 12 수정 생성 스크립트 (GOMS, 자격증, 직업 데이터)

from __future__ import annotations

import csv
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# ── Font Setup ──────────────────────────────────────────────────────────────
matplotlib.rcParams["font.family"] = "AppleGothic"
matplotlib.rcParams["axes.unicode_minus"] = False

SLIDES_DIR = Path(__file__).parent
PROJECT_ROOT = SLIDES_DIR.parents[1]
CSV_DIR = PROJECT_ROOT / "data" / "raw" / "csv"

CHART_DPI = 150
CHART_FC = "white"

# ── Column Indices (confirmed from GOMS header) ──────────────────────────────
GOMS_PATH = CSV_DIR / "GP19__2020.XLSX"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

MAJORCAT_IDX = 5
SEX_IDX = 13
AGE_IDX = 14
SQ001_IDX = 19   # employment status
A001_IDX = 30    # first job type

MAJORCAT_MAP = {
    "1": "인문",
    "2": "사회",
    "3": "교육",
    "4": "공학",
    "5": "자연과학",
    "6": "의약",
    "7": "예체능",
    "8": "사범교육",
}

SQ001_MAP = {
    "1": "취업(임금)",
    "2": "취업(비임금)",
    "3": "진학",
    "4": "취업준비",
    "5": "미취업/기타",
}


# ── GOMS Loader ──────────────────────────────────────────────────────────────

def _load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    with z.open("xl/sharedStrings.xml") as f:
        root = ET.parse(f).getroot()
    shared: list[str] = []
    for si in root.findall(f"{NS}si"):
        texts = [t.text or "" for t in si.iter(f"{NS}t")]
        shared.append("".join(texts))
    return shared


def _cell_value(c: ET.Element, shared: list[str]) -> str:
    t = c.get("t", "")
    v = c.find(f"{NS}v")
    if v is None or v.text is None:
        return ""
    if t == "s":
        return shared[int(v.text)]
    return v.text.strip()


def load_goms_data() -> list[dict]:
    """Return list of dicts with keys: majorcat, sex, age, sq001, a001."""
    print("Loading GOMS XLSX via zipfile XML …", flush=True)
    with zipfile.ZipFile(GOMS_PATH) as z:
        shared = _load_shared_strings(z)
        with z.open("xl/worksheets/sheet1.xml") as f:
            root = ET.parse(f).getroot()

    rows = root.findall(f".//{NS}row")
    records: list[dict] = []
    for row in rows[1:]:   # skip header row
        cells = row.findall(f"{NS}c")
        # cells may be sparse; index by column reference
        cell_map: dict[int, str] = {}
        for c in cells:
            ref = c.get("r", "")
            # Convert column letter(s) to 0-based index
            col_letters = re.match(r"([A-Z]+)", ref)
            if col_letters:
                col_str = col_letters.group(1)
                col_idx = 0
                for ch in col_str:
                    col_idx = col_idx * 26 + (ord(ch) - ord("A") + 1)
                col_idx -= 1  # 0-based
                cell_map[col_idx] = _cell_value(c, shared)

        records.append({
            "majorcat": cell_map.get(MAJORCAT_IDX, ""),
            "sex":      cell_map.get(SEX_IDX, ""),
            "age":      cell_map.get(AGE_IDX, ""),
            "sq001":    cell_map.get(SQ001_IDX, ""),
            "a001":     cell_map.get(A001_IDX, ""),
        })
    print(f"  Loaded {len(records):,} GOMS records.", flush=True)
    return records


# ── Chart 13: GOMS 전공계열별 응시자 분포 ────────────────────────────────────

def chart_13(records: list[dict]) -> None:
    print("Generating 13_goms_major_category.png …", flush=True)
    male_counts: dict[str, int] = defaultdict(int)
    female_counts: dict[str, int] = defaultdict(int)

    for r in records:
        cat = MAJORCAT_MAP.get(r["majorcat"], "")
        if not cat:
            continue
        if r["sex"] == "1":
            male_counts[cat] += 1
        else:
            female_counts[cat] += 1

    cats = list(MAJORCAT_MAP.values())
    males = [male_counts.get(c, 0) for c in cats]
    females = [female_counts.get(c, 0) for c in cats]

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=CHART_FC)
    x = np.arange(len(cats))
    w = 0.4
    ax.bar(x - w / 2, males, width=w, label="남성", color="#4C9BE8")
    ax.bar(x + w / 2, females, width=w, label="여성", color="#F08080")
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=11)
    ax.set_xlabel("전공계열", fontsize=12)
    ax.set_ylabel("응답자 수", fontsize=12)
    ax.set_title("GOMS 전공계열별 응답자 분포 (성별)", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    plt.tight_layout()
    fig.savefig(SLIDES_DIR / "13_goms_major_category.png", dpi=CHART_DPI, facecolor=CHART_FC, bbox_inches="tight")
    plt.close(fig)
    print("  Saved 13_goms_major_category.png", flush=True)


# ── Chart 14: 전공계열별 취업 현황 ──────────────────────────────────────────

def chart_14(records: list[dict]) -> None:
    print("Generating 14_goms_employment_by_major.png …", flush=True)
    # {majorcat: {sq001: count}}
    data: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in records:
        cat = MAJORCAT_MAP.get(r["majorcat"], "")
        sq = r["sq001"]
        if cat and sq in SQ001_MAP:
            data[cat][sq] += 1

    cats = [c for c in MAJORCAT_MAP.values() if c in data]
    statuses = list(SQ001_MAP.keys())
    status_labels = [SQ001_MAP[s] for s in statuses]

    colors = ["#4C9BE8", "#82CA9D", "#FFD166", "#EF476F", "#A0A0A0"]

    fig, ax = plt.subplots(figsize=(14, 7), facecolor=CHART_FC)
    x = np.arange(len(cats))
    width = 0.15
    for i, (s, label, color) in enumerate(zip(statuses, status_labels, colors)):
        vals = [data[c].get(s, 0) for c in cats]
        offset = (i - len(statuses) / 2 + 0.5) * width
        ax.bar(x + offset, vals, width=width, label=label, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=10)
    ax.set_xlabel("전공계열", fontsize=12)
    ax.set_ylabel("응답자 수", fontsize=12)
    ax.set_title("전공계열별 취업 현황 (GOMS 2020)", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    plt.tight_layout()
    fig.savefig(SLIDES_DIR / "14_goms_employment_by_major.png", dpi=CHART_DPI, facecolor=CHART_FC, bbox_inches="tight")
    plt.close(fig)
    print("  Saved 14_goms_employment_by_major.png", flush=True)


# ── Chart 15: 자격증 응시자 수 상위 20개 ─────────────────────────────────────

def chart_15() -> None:
    print("Generating 15_cert_exam_applicants.png …", flush=True)
    cert_path = CSV_DIR / "data_cert_rows.csv"
    totals: dict[str, int] = defaultdict(int)

    applicant_cols: list[str] = []
    with cert_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        applicant_cols = [c for c in fieldnames if "응시자" in c]
        for row in reader:
            name = row.get("자격증명", "").strip()
            if not name:
                continue
            for col in applicant_cols:
                val = row.get(col, "").replace(",", "").strip()
                try:
                    totals[name] += int(float(val))
                except (ValueError, TypeError):
                    pass

    top20 = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:20]
    labels = [t[0] for t in top20]
    values = [t[1] for t in top20]

    fig, ax = plt.subplots(figsize=(14, 8), facecolor=CHART_FC)
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(labels)))[::-1]
    bars = ax.barh(range(len(labels)), values, color=colors)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("누적 응시자 수", fontsize=12)
    ax.set_title("자격증 응시자 수 상위 20개 (2022-2024 누적)", fontsize=14, fontweight="bold")
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", fontsize=8)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    plt.tight_layout()
    fig.savefig(SLIDES_DIR / "15_cert_exam_applicants.png", dpi=CHART_DPI, facecolor=CHART_FC, bbox_inches="tight")
    plt.close(fig)
    print("  Saved 15_cert_exam_applicants.png", flush=True)


# ── Chart 16: 전공별 자격증 연계 현황 ───────────────────────────────────────

def chart_16() -> None:
    print("Generating 16_cert_major_connection.png …", flush=True)
    jrm_path = CSV_DIR / "job_raw_merged_rows.csv"
    major_cert_counts: dict[str, int] = defaultdict(int)

    with jrm_path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            major = row.get("major_name", "").strip()
            cert = row.get("cert_name", "").strip()
            if major and cert:
                # major_name can be comma-separated list
                for m in [m.strip() for m in major.split(",")]:
                    if m:
                        major_cert_counts[m] += 1

    top12 = sorted(major_cert_counts.items(), key=lambda x: x[1], reverse=True)[:12]
    labels = [t[0] for t in top12]
    values = [t[1] for t in top12]

    fig, ax = plt.subplots(figsize=(12, 7), facecolor=CHART_FC)
    colors = plt.cm.Greens(np.linspace(0.4, 0.9, len(labels)))[::-1]
    bars = ax.barh(range(len(labels)), values, color=colors)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("자격증 연계 수", fontsize=12)
    ax.set_title("전공별 자격증 연계 현황 상위 12개 (job_raw_merged 기준)", fontsize=14, fontweight="bold")
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=10)
    plt.tight_layout()
    fig.savefig(SLIDES_DIR / "16_cert_major_connection.png", dpi=CHART_DPI, facecolor=CHART_FC, bbox_inches="tight")
    plt.close(fig)
    print("  Saved 16_cert_major_connection.png", flush=True)


# ── Chart 17: 직업별 임금 vs 일자리전망 scatter ──────────────────────────────

def chart_17() -> None:
    print("Generating 17_job_outlook_salary.png …", flush=True)
    job_path = CSV_DIR / "고용24 직업정보상세 요약.csv"

    names: list[str] = []
    salaries: list[float] = []
    satisfactions: list[float] = []
    outlooks: list[str] = []

    with job_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip English header row
            name = row.get("직업 소분류명") or row.get("occp_sclsf_nm", "")
            if not name or name == "occp_sclsf_nm":
                continue
            salary_raw = row.get("임금") or row.get("wgs", "")
            sat_raw = row.get("직업만족도(%)") or row.get("occp_satsfc_rt", "")
            outlook_raw = row.get("일자리전망") or row.get("occp_expct", "")

            # Extract numeric salary (e.g. "3,500만원" → 3500)
            salary_nums = re.findall(r"[\d,]+", str(salary_raw).replace(",", ""))
            sat_nums = re.findall(r"[\d.]+", str(sat_raw))

            if salary_nums and sat_nums:
                try:
                    sal = float(salary_nums[0])
                    sat = float(sat_nums[0])
                    names.append(name)
                    salaries.append(sal)
                    satisfactions.append(sat)
                    outlooks.append(str(outlook_raw).strip())
                except ValueError:
                    pass

    if not names:
        print("  No data for chart 17, skipping.", flush=True)
        return

    # Color by outlook
    unique_outlooks = sorted(set(outlooks))
    cmap = matplotlib.colormaps.get_cmap("RdYlGn").resampled(len(unique_outlooks))
    outlook_color = {o: cmap(i) for i, o in enumerate(unique_outlooks)}

    fig, ax = plt.subplots(figsize=(13, 8), facecolor=CHART_FC)
    for i, (sal, sat, outlook, name_) in enumerate(zip(salaries, satisfactions, outlooks, names)):
        color = outlook_color.get(outlook, "gray")
        ax.scatter(sal, sat, color=color, alpha=0.7, s=50)

    # Legend for outlooks
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=outlook_color[o], label=o) for o in unique_outlooks]
    ax.legend(handles=legend_elements, title="일자리전망", fontsize=8, title_fontsize=9,
              loc="lower right")

    ax.set_xlabel("임금 (만원)", fontsize=12)
    ax.set_ylabel("직업만족도 (%)", fontsize=12)
    ax.set_title("직업별 임금 vs 직업만족도 (고용24 기준)", fontsize=14, fontweight="bold")
    fig.savefig(SLIDES_DIR / "17_job_outlook_salary.png", dpi=CHART_DPI, facecolor=CHART_FC, bbox_inches="tight")
    plt.close(fig)
    print("  Saved 17_job_outlook_salary.png", flush=True)


# ── Chart 18: NCS 대직무별 자격증 매핑 현황 ─────────────────────────────────

def chart_18() -> None:
    print("Generating 18_ncs_cert_mapping_coverage.png …", flush=True)
    ncs_path = CSV_DIR / "ncs_mapping_rows.csv"
    domain_cert_counts: dict[str, int] = defaultdict(int)

    with ncs_path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            domain = row.get("대직무분류", "").strip()
            cert = row.get("자격증명", "").strip()
            # Skip entries with replacement/corrupted characters
            if domain and cert and "�" not in domain:
                domain_cert_counts[domain] += 1

    sorted_items = sorted(domain_cert_counts.items(), key=lambda x: x[1], reverse=True)
    labels = [t[0] for t in sorted_items]
    values = [t[1] for t in sorted_items]

    fig, ax = plt.subplots(figsize=(13, 7), facecolor=CHART_FC)
    colors = plt.cm.Purples(np.linspace(0.35, 0.9, len(labels)))[::-1]
    bars = ax.bar(range(len(labels)), values, color=colors)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("자격증 매핑 수", fontsize=12)
    ax.set_title("NCS 대직무별 자격증 매핑 현황", fontsize=14, fontweight="bold")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(val), ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    fig.savefig(SLIDES_DIR / "18_ncs_cert_mapping_coverage.png", dpi=CHART_DPI, facecolor=CHART_FC, bbox_inches="tight")
    plt.close(fig)
    print("  Saved 18_ncs_cert_mapping_coverage.png", flush=True)


# ── Chart 12 Fix: API 통합 현황 (no emoji) ───────────────────────────────────

def chart_12_fixed() -> None:
    print("Generating 12_api_integration_status_fixed.png …", flush=True)
    categories = ["워크넷 채용", "고용24 직업정보", "한국산업인력공단", "NCS 매핑", "서울 실태조사", "GOMS 분석"]
    statuses = ["[활성]", "[활성]", "[활성]", "[활성]", "[통합중]", "[분석중]"]
    coverage = [85, 90, 75, 70, 60, 50]
    colors_map = {"[활성]": "#4CAF50", "[통합중]": "#FF9800", "[분석중]": "#2196F3"}
    bar_colors = [colors_map[s] for s in statuses]

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=CHART_FC)
    bars = ax.barh(categories, coverage, color=bar_colors, edgecolor="white", linewidth=0.5)
    for bar, status, cov in zip(bars, statuses, coverage):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{status} {cov}%", va="center", fontsize=10)
    ax.set_xlim(0, 115)
    ax.set_xlabel("통합 커버리지 (%)", fontsize=12)
    ax.set_title("API 및 데이터 통합 현황", fontsize=14, fontweight="bold")

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#4CAF50", label="[활성] 활성"),
        Patch(facecolor="#FF9800", label="[통합중] 통합중"),
        Patch(facecolor="#2196F3", label="[분석중] 분석중"),
    ]
    ax.legend(handles=legend_elements, fontsize=10, loc="lower right")
    plt.tight_layout()
    fig.savefig(SLIDES_DIR / "12_api_integration_status_fixed.png", dpi=CHART_DPI, facecolor=CHART_FC, bbox_inches="tight")
    plt.close(fig)
    print("  Saved 12_api_integration_status_fixed.png", flush=True)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    import matplotlib.ticker  # ensure available in nested scope
    matplotlib.ticker  # noqa: suppress unused warning

    # Non-GOMS charts first (fast)
    chart_15()
    chart_16()
    chart_17()
    chart_18()
    chart_12_fixed()

    # GOMS charts (slow — large file)
    records = load_goms_data()
    chart_13(records)
    chart_14(records)

    print("All charts generated.", flush=True)


if __name__ == "__main__":
    main()
