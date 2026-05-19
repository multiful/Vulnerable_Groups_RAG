# File: goms_service.py
# Last Updated: 2026-05-19
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
_JOB_RAW_MERGED_CSV  = _PROJECT_ROOT / "data" / "raw" / "csv" / "job_raw_merged_rows.csv"
_NCS_MAPPING_CSV     = _PROJECT_ROOT / "data" / "raw" / "csv" / "ncs_mapping_rows.csv"
_JOB_INFO_CSV        = _PROJECT_ROOT / "data" / "raw" / "csv" / "고용24 직업정보상세 요약.csv"
_JOB_ALIAS_CSV       = _PROJECT_ROOT / "data" / "processed" / "mappings" / "job_alias_mapping.csv"
_JOB_INFO_EXT_CSV    = _PROJECT_ROOT / "data" / "raw" / "csv" / "job_info_rows.csv"
_DATA_JOBS_ROWS_CSV  = _PROJECT_ROOT / "data" / "raw" / "csv" / "data_jobs_rows.csv"
_CERT_MASTER_CSV     = _PROJECT_ROOT / "data" / "processed" / "master" / "cert_master.csv"
_JOB_MASTER_CSV      = _PROJECT_ROOT / "data" / "processed" / "master" / "job_master.csv"
_CERT_JOB_MAP_CSV    = _PROJECT_ROOT / "data" / "canonical" / "relations" / "cert_job_mapping.csv"

# 서비스(숙련직) 직무구분은 서비스·운송 도메인 자격증에서만 유효
_SERVICE_SKILLED_DOMAINS = frozenset(["모빌리티/운송", "교육/생활서비스", "국방/특수"])


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
def _load_job_duty_class_map() -> dict[str, str]:
    """직업명 → 직무구분 (job_info_rows.csv). 도메인 호환성 필터에 사용."""
    out: dict[str, str] = {}
    if not _JOB_INFO_EXT_CSV.exists():
        return out
    try:
        with _JOB_INFO_EXT_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                name = (r.get("직업명") or "").strip()
                cat = (r.get("직무구분") or "").strip()
                if name and cat:
                    out[name] = cat
    except Exception as e:
        logger.warning("job_duty_class 로드 실패: %s", e)
    return out


@lru_cache(maxsize=1)
def _load_cert_top_domain_map() -> dict[str, str]:
    """cert_name → top_domain (cert_master.csv). 도메인 호환성 필터에 사용."""
    out: dict[str, str] = {}
    if not _CERT_MASTER_CSV.exists():
        return out
    try:
        with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                name = (r.get("cert_name") or "").strip()
                td = (r.get("top_domain") or "").strip()
                if name:
                    out[name] = td
    except Exception as e:
        logger.warning("cert_master top_domain 로드 실패: %s", e)
    return out


def _filter_domain_compatible_jobs(jobs: list[str], cert_top_domain: str) -> list[str]:
    """
    서비스(숙련직) 직무구분 직업은 서비스/운송 도메인이 아닌 자격증에서 제외.
    - cert_top_domain이 빈 문자열(조회 실패)이면 필터 미적용 (보수적).
    - 직무구분 정보가 없는 직업은 포함 유지.
    """
    if not cert_top_domain:
        return list(jobs)
    duty_map = _load_job_duty_class_map()
    result = []
    for job in jobs:
        cat = duty_map.get(job)
        if cat == "서비스(숙련직)" and cert_top_domain not in _SERVICE_SKILLED_DOMAINS:
            continue
        result.append(job)
    return result


@lru_cache(maxsize=1)
def _load_job_master() -> dict[str, dict]:
    """job_role_id → {job_role_name, job_top_group_name} (job_master.csv, active only)."""
    out: dict[str, dict] = {}
    if not _JOB_MASTER_CSV.exists():
        return out
    try:
        with _JOB_MASTER_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("is_active", "TRUE").strip().upper() not in ("TRUE", "1", "YES"):
                    continue
                jid = r.get("job_role_id", "").strip()
                if jid:
                    out[jid] = {
                        "job_role_name":      r.get("job_role_name", "").strip(),
                        "job_top_group_name": r.get("job_top_group_name", "").strip(),
                    }
    except Exception as e:
        logger.warning("job_master.csv 로드 실패: %s", e)
    return out


@lru_cache(maxsize=1)
def _load_cert_name_to_id() -> dict[str, str]:
    """cert_name → cert_id (cert_master.csv)."""
    out: dict[str, str] = {}
    if not _CERT_MASTER_CSV.exists():
        return out
    try:
        with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                name = (r.get("cert_name") or "").strip()
                cid = (r.get("cert_id") or "").strip()
                if name and cid:
                    out[name] = cid
    except Exception as e:
        logger.warning("cert_master cert_name→id 로드 실패: %s", e)
    return out


@lru_cache(maxsize=1)
def _load_cert_job_canonical() -> dict[str, list[str]]:
    """cert_id → [job_role_id, ...] (cert_job_mapping.csv, active only)."""
    out: dict[str, list[str]] = {}
    if not _CERT_JOB_MAP_CSV.exists():
        return out
    try:
        with _CERT_JOB_MAP_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("is_active", "TRUE").strip().upper() not in ("TRUE", "1", "YES"):
                    continue
                cid = (r.get("cert_id") or "").strip()
                jid = (r.get("job_role_id") or "").strip()
                if cid and jid:
                    out.setdefault(cid, []).append(jid)
    except Exception as e:
        logger.warning("cert_job_mapping.csv 로드 실패: %s", e)
    return out


@lru_cache(maxsize=1)
def _build_cert_related_majors_index() -> dict[str, list[str]]:
    """cert_name → [major_name, ...] (job_raw_merged major_name 필드 기준, 중복 제거)."""
    index: dict[str, list[str]] = defaultdict(list)
    for row in _load_job_raw_merged():
        cert = row.get("cert_name", "").strip()
        majors_raw = row.get("major_name", "").strip()
        if cert and majors_raw:
            for m in majors_raw.split(","):
                m = m.strip()
                if m and m not in index[cert]:
                    index[cert].append(m)
    return dict(index)


def _enrich_jobs(jobs: list[str]) -> list[dict]:
    """직업명 목록 → 상세 정보 포함 객체 목록 (job_info_rows 기반)."""
    ext_map = _load_job_info_ext()
    duty_map = _load_job_duty_class_map()
    result = []
    for job in jobs:
        ext = ext_map.get(job) or {}
        result.append({
            "name":                  job,
            "duty_class":            duty_map.get(job),
            "professionalism_score": ext.get("professionalism_score"),
            "growth_score":          ext.get("growth_score"),
            "job_security_score":    ext.get("job_security_score"),
            "salary_summary":        ext.get("salary_summary"),
            "similar_jobs":          ext.get("similar_jobs"),
        })
    return result


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
    """cert_name → [job_name, …] 인덱스 (job_raw_merged 기준).
    alias 정규화를 사용하지 않음 — role명으로 변환하면 worknet raw명과 중복되고
    match_score가 낮은 alias가 '일반사무' 등 부정확한 역할명을 반환하는 문제 방지.
    """
    index: dict[str, list[str]] = defaultdict(list)
    for row in _load_job_raw_merged():
        cert = row.get("cert_name", "").strip()
        raw_job = row.get("raw_job_name", "").strip()
        if cert and raw_job and raw_job not in index[cert]:
            index[cert].append(raw_job)
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
    job_raw_merged 기준. ncs_mapping 직업 필드는 도메인 혼합이 심해 제외.
    """
    return list(_build_cert_to_jobs_index().get(cert_name, []))


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
    고용24 CSV + job_info_rows 점수 + 직무구분을 합산.
    """
    rows = _load_job_info_csv()
    base: dict[str, Any] = {}
    if rows:
        for row in rows:
            name = (row.get("직업 소분류명") or row.get("occp_sclsf_nm", "")).strip()
            if job_name in name:
                base = _normalize_job_info_row(row)
                break

    # Supplement with job_info_rows scores (exact match first, then partial)
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

    # 직무구분 보충
    duty_map = _load_job_duty_class_map()
    if job_name in duty_map:
        base["duty_class"] = duty_map[job_name]
    elif not base.get("duty_class"):
        for k, v in duty_map.items():
            if job_name in k:
                base["duty_class"] = v
                break

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

def get_cert_jobs_envelope(cert_name: str, limit: int = 30) -> dict[str, Any]:
    """GET /jobs/cert-jobs/{cert_name} 응답용 envelope.

    세 가지 데이터 소스를 통합:
    1. cert_job_mapping → job_master: 캐노니컬 직무 역할 (구조적)
    2. job_raw_merged: GOMS 기반 실제 직업명
    3. data_jobs_rows (worknet): 워크넷 실제 직업명
    도메인 호환성 필터 적용 후 각 직업에 상세 점수·급여 보강.
    """
    if not cert_name or not cert_name.strip():
        return err_envelope("INVALID_INPUT", "cert_name이 비어 있습니다.")
    name = cert_name.strip()

    # ── 1. 캐노니컬 직무 역할 (cert_job_mapping → job_master) ─────────────────
    cert_id = _load_cert_name_to_id().get(name, "")
    job_master = _load_job_master()
    canonical_role_ids = _load_cert_job_canonical().get(cert_id, []) if cert_id else []
    canonical_roles: list[dict] = []
    for jid in canonical_role_ids:
        role = job_master.get(jid)
        if role:
            canonical_roles.append({
                "job_role_id":        jid,
                "job_role_name":      role["job_role_name"],
                "job_top_group_name": role["job_top_group_name"],
            })

    # ── 2. 실제 직업명 (job_raw_merged + worknet, 도메인 필터) ─────────────────
    jobs_goms = get_cert_job_connections(name)
    jobs_worknet = _load_cert_to_jobs_worknet().get(name, [])
    seen: set[str] = set(jobs_goms)
    extra = [j for j in jobs_worknet if j not in seen]
    jobs_all = jobs_goms + extra
    cert_top_domain = _load_cert_top_domain_map().get(name, "")
    jobs_all = _filter_domain_compatible_jobs(jobs_all, cert_top_domain)
    total_unfiltered = len(jobs_all)
    if limit > 0:
        jobs_all = jobs_all[:limit]

    # ── 3. 직업 상세 보강 (job_info_rows: 점수·급여) ─────────────────────────
    jobs_detail = _enrich_jobs(jobs_all)

    # ── 4. 연관 전공 (job_raw_merged major_name — 가장 정확한 소스) ──────────
    related_majors = _build_cert_related_majors_index().get(name, [])

    return ok_envelope({
        "cert_name":      name,
        "cert_id":        cert_id or None,
        # 캐노니컬 직무 역할 (구조화된 taxonomy)
        "canonical_roles":  canonical_roles,
        "canonical_total":  len(canonical_roles),
        # 실제 직업명 목록 (기존 호환 유지)
        "jobs":              jobs_all,
        "jobs_detail":       jobs_detail,
        "total":             len(jobs_all),
        "total_unfiltered":  total_unfiltered,
        # 연관 전공
        "related_majors": related_majors,
        "sources":        ["cert_job_mapping", "job_raw_merged", "worknet_data_jobs"],
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
