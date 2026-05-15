# File: goms_service.py
# Last Updated: 2026-05-15
# Content Hash: SHA256:TBD
# Role: GOMS 분석 기반 자격증-직무-전공 연결 서비스
#
# 데이터 소스:
#   - data/raw/csv/job_raw_merged_rows.csv  (자격증-직무-전공 연결)
#   - data/raw/csv/ncs_mapping_rows.csv     (NCS 자격증 매핑)
#   - data/raw/csv/고용24 직업정보상세 요약.csv (직업 상세 정보)
#   - data/raw/csv/job_info_rows.csv        (직업 6개 점수 + 급여 + 유사직업)
#   - data/raw/csv/data_jobs_rows.csv       (자격증→직업 워크넷 연결)
#
# 주의: GOMS XLSX 원본 파싱은 이 서비스에서 직접 수행하지 않는다.
#       GOMS 통계 차트 생성은 docs/slides/generate_charts_13_18.py 참고.
from __future__ import annotations

import csv
import logging
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parents[3]
_JOB_RAW_MERGED_CSV = _PROJECT_ROOT / "data" / "raw" / "csv" / "job_raw_merged_rows.csv"
_NCS_MAPPING_CSV = _PROJECT_ROOT / "data" / "raw" / "csv" / "ncs_mapping_rows.csv"
_JOB_INFO_CSV = _PROJECT_ROOT / "data" / "raw" / "csv" / "고용24 직업정보상세 요약.csv"
_JOB_ALIAS_CSV      = _PROJECT_ROOT / "data" / "processed" / "mappings" / "job_alias_mapping.csv"
_JOB_INFO_EXT_CSV   = _PROJECT_ROOT / "data" / "raw" / "csv" / "job_info_rows.csv"
_DATA_JOBS_ROWS_CSV = _PROJECT_ROOT / "data" / "raw" / "csv" / "data_jobs_rows.csv"


# ── Data Loaders ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_job_raw_merged() -> list[dict[str, str]]:
    """job_raw_merged_rows.csv 로드 (cert-job-major 연결 정보)."""
    if not _JOB_RAW_MERGED_CSV.exists():
        logger.warning("job_raw_merged_rows.csv not found: %s", _JOB_RAW_MERGED_CSV)
        return []
    rows: list[dict[str, str]] = []
    try:
        with _JOB_RAW_MERGED_CSV.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                rows.append(dict(row))
    except Exception as e:
        logger.warning("job_raw_merged_rows.csv 로드 실패: %s", e)
    return rows


@lru_cache(maxsize=1)
def _load_ncs_mapping() -> list[dict[str, str]]:
    """ncs_mapping_rows.csv 로드 (NCS 대/중직무 ↔ 자격증 매핑)."""
    if not _NCS_MAPPING_CSV.exists():
        logger.warning("ncs_mapping_rows.csv not found: %s", _NCS_MAPPING_CSV)
        return []
    rows: list[dict[str, str]] = []
    try:
        with _NCS_MAPPING_CSV.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                rows.append(dict(row))
    except Exception as e:
        logger.warning("ncs_mapping_rows.csv 로드 실패: %s", e)
    return rows


@lru_cache(maxsize=1)
def _load_job_alias_map() -> dict[str, str]:
    """raw_job_name → matched_job_role_name (정규화 매핑). is_active=TRUE 행만."""
    if not _JOB_ALIAS_CSV.exists():
        return {}
    out: dict[str, str] = {}
    try:
        with _JOB_ALIAS_CSV.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("is_active", "TRUE").strip().upper() not in ("TRUE", "1", "YES"):
                    continue
                raw = row.get("raw_job_name", "").strip()
                normalized = row.get("matched_job_role_name", "").strip()
                if raw and normalized:
                    out[raw.lower()] = normalized
    except Exception as e:
        logger.warning("job_alias_mapping.csv 로드 실패: %s", e)
    return out


def _normalize_job_name(raw: str) -> str:
    """raw_job_name → 정규화된 직무명. 매핑 없으면 raw 반환."""
    alias_map = _load_job_alias_map()
    return alias_map.get(raw.strip().lower(), raw.strip())


@lru_cache(maxsize=1)
def _load_job_info_ext() -> dict[str, dict]:
    """직업명 → {pay, job_security, growth, work_conditions, professionalism, equity, similar_jobs, salary_summary, aptitude}
    Source: job_info_rows.csv (워크넷 직업사전 6개 점수 + 급여 + 유사직업)
    """
    if not _JOB_INFO_EXT_CSV.exists():
        return {}
    out: dict[str, dict] = {}

    def _score(raw: str) -> float | None:
        nums = re.findall(r"[\d.]+", str(raw))
        return float(nums[0]) if nums else None

    def _salary_from_text(text: str) -> str:
        m = re.search(r"평균\(50%\)\s*([\d,.]+)만원", text)
        if m:
            return m.group(1) + "만원"
        m2 = re.search(r"([\d,.]+)만원", text)
        return m2.group(1) + "만원" if m2 else ""

    try:
        with _JOB_INFO_EXT_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                name = (r.get("직업명") or "").strip()
                if not name:
                    continue
                out[name] = {
                    "pay_score":             _score(r.get("보상", "")),
                    "job_security_score":    _score(r.get("고용안정", "")),
                    "growth_score":          _score(r.get("발전가능성", "")),
                    "work_conditions_score": _score(r.get("근무여건", "")),
                    "professionalism_score": _score(r.get("직업전문성", "")),
                    "equity_score":          _score(r.get("고용평등", "")),
                    "similar_jobs":          (r.get("유사직업명") or "").strip() or None,
                    "salary_summary":        _salary_from_text(r.get("초임", "")),
                    "aptitude":              (r.get("적성") or "").strip()[:200] or None,
                    "employment_method":     (r.get("취업방법") or "").strip()[:300] or None,
                }
    except Exception as e:
        logger.warning("job_info_rows.csv 로드 실패: %s", e)
    return out


@lru_cache(maxsize=1)
def _load_cert_to_jobs_worknet() -> dict[str, list[str]]:
    """자격증명 → [직업명, ...] (data_jobs_rows.csv 워크넷 매핑)."""
    if not _DATA_JOBS_ROWS_CSV.exists():
        return {}
    out: dict[str, list[str]] = {}
    try:
        with _DATA_JOBS_ROWS_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                cert = (r.get("자격증명") or "").strip()
                job = (r.get("직업명") or "").strip()
                if cert and job and job not in out.get(cert, []):
                    out.setdefault(cert, []).append(job)
    except Exception as e:
        logger.warning("data_jobs_rows.csv 로드 실패: %s", e)
    return out


@lru_cache(maxsize=1)
def _load_job_info_csv() -> list[dict[str, str]]:
    """고용24 직업정보상세 요약.csv 로드."""
    if not _JOB_INFO_CSV.exists():
        logger.warning("고용24 직업정보상세 요약.csv not found: %s", _JOB_INFO_CSV)
        return []
    rows: list[dict[str, str]] = []
    try:
        with _JOB_INFO_CSV.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip English header row (second row in this CSV)
                name_val = row.get("직업 소분류명") or row.get("occp_sclsf_nm", "")
                if name_val and name_val == "occp_sclsf_nm":
                    continue
                rows.append(dict(row))
    except Exception as e:
        logger.warning("고용24 직업정보 CSV 로드 실패: %s", e)
    return rows


# ── Index Builders ────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _build_cert_to_jobs_index() -> dict[str, list[str]]:
    """cert_name → [job_name, …] 인덱스 (job_raw_merged 기준, alias 정규화 적용)."""
    index: dict[str, list[str]] = defaultdict(list)
    for row in _load_job_raw_merged():
        cert = row.get("cert_name", "").strip()
        raw_job = row.get("raw_job_name", "").strip()
        job = _normalize_job_name(raw_job) if raw_job else ""
        if cert and job and job not in index[cert]:
            index[cert].append(job)
    return dict(index)


@lru_cache(maxsize=1)
def _build_cert_to_jobs_ncs_index() -> dict[str, list[str]]:
    """cert_name → [job_name, …] 인덱스 (ncs_mapping 기준, 직업 필드)."""
    index: dict[str, list[str]] = defaultdict(list)
    for row in _load_ncs_mapping():
        cert = row.get("자격증명", "").strip()
        jobs_raw = row.get("직업", "").strip()
        if cert and jobs_raw:
            jobs = [j.strip() for j in jobs_raw.split(",") if j.strip()]
            for job in jobs:
                if job not in index[cert]:
                    index[cert].append(job)
    return dict(index)


@lru_cache(maxsize=1)
def _build_major_to_certs_index() -> dict[str, list[str]]:
    """major_name → [cert_name, …] 인덱스 (job_raw_merged 기준)."""
    index: dict[str, list[str]] = defaultdict(list)
    for row in _load_job_raw_merged():
        cert = row.get("cert_name", "").strip()
        major_raw = row.get("major_name", "").strip()
        if cert and major_raw:
            majors = [m.strip() for m in major_raw.split(",") if m.strip()]
            for major in majors:
                if cert not in index[major]:
                    index[major].append(cert)
    return dict(index)


@lru_cache(maxsize=1)
def _build_major_to_certs_ncs_index() -> dict[str, list[str]]:
    """학과 → [cert_name, …] 인덱스 (ncs_mapping 기준)."""
    index: dict[str, list[str]] = defaultdict(list)
    for row in _load_ncs_mapping():
        cert = row.get("자격증명", "").strip()
        majors_raw = row.get("학과", "").strip()
        if cert and majors_raw:
            majors = [m.strip() for m in majors_raw.split(",") if m.strip()]
            for major in majors:
                if cert not in index[major]:
                    index[major].append(cert)
    return dict(index)


# ── Service Functions ─────────────────────────────────────────────────────────

def get_cert_job_connections(cert_name: str) -> list[str]:
    """
    자격증 이름 → 연관 직업명 목록.
    job_raw_merged (완전 일치) + ncs_mapping (완전 일치) 결합.
    """
    jobs_merged = _build_cert_to_jobs_index().get(cert_name, [])
    jobs_ncs = _build_cert_to_jobs_ncs_index().get(cert_name, [])
    # deduplicate, preserve order
    seen: set[str] = set()
    result: list[str] = []
    for job in jobs_merged + jobs_ncs:
        if job not in seen:
            seen.add(job)
            result.append(job)
    return result


def get_major_cert_suggestions(major_name: str) -> list[str]:
    """
    전공명 → 추천 자격증 목록.
    job_raw_merged (major_name 필드) + ncs_mapping (학과 필드) 결합.
    """
    certs_merged = _build_major_to_certs_index().get(major_name, [])
    certs_ncs = _build_major_to_certs_ncs_index().get(major_name, [])
    seen: set[str] = set()
    result: list[str] = []
    for cert in certs_merged + certs_ncs:
        if cert not in seen:
            seen.add(cert)
            result.append(cert)
    return result


def get_job_info(job_name: str) -> dict[str, Any]:
    """
    직업명 (부분 일치) → 고용24 직업 상세 정보 dict.
    반환 키: job_name, job_code, salary, satisfaction, outlook, work_content, video_url
    워크넷 job_info_rows 점수(pay_score 등) 보충.
    """
    rows = _load_job_info_csv()
    base: dict[str, Any] = {}
    if rows:
        for row in rows:
            name = (row.get("직업 소분류명") or row.get("occp_sclsf_nm", "")).strip()
            if job_name in name:
                base = _normalize_job_info_row(row)
                break

    # Supplement with worknet scores (exact match first, then partial)
    ext_map = _load_job_info_ext()
    ext = ext_map.get(job_name)
    if not ext:
        for k, v in ext_map.items():
            if job_name in k:
                ext = v
                break

    if ext:
        base.setdefault("job_name", job_name)
        base.update({
            "pay_score":             ext.get("pay_score"),
            "job_security_score":    ext.get("job_security_score"),
            "growth_score":          ext.get("growth_score"),
            "work_conditions_score": ext.get("work_conditions_score"),
            "professionalism_score": ext.get("professionalism_score"),
            "equity_score":          ext.get("equity_score"),
            "similar_jobs":          ext.get("similar_jobs"),
            "salary_summary":        ext.get("salary_summary") or base.get("salary"),
            "aptitude":              ext.get("aptitude"),
            "employment_method":     ext.get("employment_method") or base.get("employment_method"),
        })

    return base


def _normalize_job_info_row(row: dict[str, str]) -> dict[str, Any]:
    salary_raw = row.get("임금") or row.get("wgs", "")
    sat_raw = row.get("직업만족도(%)") or row.get("occp_satsfc_rt", "")
    sat_nums = re.findall(r"[\d.]+", str(sat_raw))

    return {
        "job_name":       (row.get("직업 소분류명") or row.get("occp_sclsf_nm", "")).strip(),
        "job_code":       (row.get("직업코드") or row.get("occp_cd", "")).strip(),
        "salary":         salary_raw.strip(),
        "satisfaction":   float(sat_nums[0]) if sat_nums else None,
        "outlook":        (row.get("일자리전망") or row.get("occp_expct", "")).strip(),
        "work_content":   (row.get("하는일") or row.get("occp_work_conts", "")).strip(),
        "video_url":      (row.get("직업안내동영상") or row.get("occp_guid_mvp", "")).strip(),
        "employment_method": (row.get("되는길") or row.get("emply_mth", "")).strip(),
    }


# ── Envelope Wrappers ─────────────────────────────────────────────────────────

def get_cert_jobs_envelope(cert_name: str) -> dict[str, Any]:
    """GET /jobs/cert-jobs/{cert_name} 응답용 envelope.
    job_raw_merged + ncs_mapping + data_jobs_rows(worknet) 결합.
    """
    if not cert_name or not cert_name.strip():
        return err_envelope("INVALID_INPUT", "cert_name이 비어 있습니다.")
    name = cert_name.strip()
    jobs_goms = get_cert_job_connections(name)
    # Supplement from worknet (data_jobs_rows.csv)
    jobs_worknet = _load_cert_to_jobs_worknet().get(name, [])
    seen: set[str] = set(jobs_goms)
    extra = [j for j in jobs_worknet if j not in seen]
    jobs_all = jobs_goms + extra
    return ok_envelope({
        "cert_name": name,
        "jobs":      jobs_all,
        "total":     len(jobs_all),
        "sources":   ["job_raw_merged", "ncs_mapping", "worknet_data_jobs"],
    })


def get_job_info_envelope(job_name: str) -> dict[str, Any]:
    """GET /jobs/info/{job_name} 응답용 envelope."""
    if not job_name or not job_name.strip():
        return err_envelope("INVALID_INPUT", "job_name이 비어 있습니다.")
    info = get_job_info(job_name.strip())
    if not info:
        return err_envelope(
            "NOT_FOUND",
            f"'{job_name}'에 해당하는 직업정보가 없습니다.",
            details={"job_name": job_name},
        )
    return ok_envelope({"job": info})


def get_major_certs_envelope(major_name: str) -> dict[str, Any]:
    """전공 → 추천 자격증 목록 envelope."""
    if not major_name or not major_name.strip():
        return err_envelope("INVALID_INPUT", "major_name이 비어 있습니다.")
    certs = get_major_cert_suggestions(major_name.strip())
    return ok_envelope({
        "major_name": major_name.strip(),
        "certs":      certs,
        "total":      len(certs),
        "sources":    ["job_raw_merged", "ncs_mapping"],
    })
