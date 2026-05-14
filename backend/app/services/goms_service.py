# File: goms_service.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: GOMS 분석 기반 자격증-직무-전공 연결 서비스
#
# 데이터 소스:
#   - data/raw/csv/job_raw_merged_rows.csv  (자격증-직무-전공 연결)
#   - data/raw/csv/ncs_mapping_rows.csv     (NCS 자격증 매핑)
#   - data/raw/csv/고용24 직업정보상세 요약.csv (직업 상세 정보)
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
    """cert_name → [job_name, …] 인덱스 (job_raw_merged 기준)."""
    index: dict[str, list[str]] = defaultdict(list)
    for row in _load_job_raw_merged():
        cert = row.get("cert_name", "").strip()
        job = row.get("raw_job_name", "").strip()
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
    """
    rows = _load_job_info_csv()
    if not rows:
        return {}

    matched: list[dict[str, Any]] = []
    for row in rows:
        name = (row.get("직업 소분류명") or row.get("occp_sclsf_nm", "")).strip()
        if job_name in name:
            matched.append(_normalize_job_info_row(row))

    return matched[0] if matched else {}


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
    """GET /jobs/cert-jobs/{cert_name} 응답용 envelope."""
    if not cert_name or not cert_name.strip():
        return err_envelope("INVALID_INPUT", "cert_name이 비어 있습니다.")
    jobs = get_cert_job_connections(cert_name.strip())
    return ok_envelope({
        "cert_name": cert_name.strip(),
        "jobs":      jobs,
        "total":     len(jobs),
        "sources":   ["job_raw_merged", "ncs_mapping"],
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
