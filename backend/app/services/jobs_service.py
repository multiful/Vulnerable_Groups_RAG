# File: jobs_service.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: WorkNet 채용정보 + 고용24 직업정보 조회
# cert_id 기반 검색은 cert_lookup_service를 경유한다 (canonical 데이터 연결 원칙)
#
# APIs:
#   WorkNet 채용목록: http://openapi.work.go.kr/opi/opi/opia/wantedApi.do
#     인증키: GET_JOB_API_KEY
#     returnType: XML
#
#   고용24 직업정보: 로컬 CSV (data/raw/csv/고용24 직업정보상세 요약.csv)
from __future__ import annotations

import csv
import logging
import time
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parents[3]
_JOB_INFO_CSV = _PROJECT_ROOT / "data/raw/csv/고용24 직업정보상세 요약.csv"
_WORKNET_BASE = "http://openapi.work.go.kr/opi/opi/opia/wantedApi.do"

_TTL = 180  # WorkNet 채용 데이터는 3분 캐시 (너무 오래 캐싱하면 마감 여부가 틀릴 수 있음)
_jobs_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    entry = _jobs_cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _jobs_cache[key] = (time.monotonic(), value)

# WorkNet 지역코드 (주요 도시)
REGION_CODES: dict[str, str] = {
    "서울": "11",
    "부산": "26",
    "대구": "27",
    "인천": "28",
    "광주": "29",
    "대전": "30",
    "울산": "31",
    "세종": "36",
    "경기": "41",
    "강원": "51",
    "충북": "43",
    "충남": "44",
    "전북": "45",
    "전남": "46",
    "경북": "47",
    "경남": "48",
    "제주": "50",
}


@lru_cache(maxsize=1)
def _load_job_info() -> list[dict]:
    if not _JOB_INFO_CSV.exists():
        return []
    out: list[dict] = []
    try:
        with _JOB_INFO_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                out.append(dict(r))
    except Exception as e:
        logger.warning("고용24 직업정보 CSV 로드 실패: %s", e)
    return out


def _parse_worknet_xml(xml_text: str) -> list[dict[str, Any]]:
    """WorkNet XML 응답 → job 목록. 에러 응답(messageCd != 000) 시 ValueError 발생."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    # API 에러 응답 감지 (예: 유효하지 않은 인증키)
    msg_cd = root.find("messageCd")
    if msg_cd is not None and (msg_cd.text or "").strip() != "000":
        msg_el = root.find("message")
        err_text = (msg_el.text or "알 수 없는 오류").strip() if msg_el is not None else "알 수 없는 오류"
        raise ValueError(err_text)

    jobs: list[dict[str, Any]] = []
    for wanted in root.iter("wanted"):
        job: dict[str, Any] = {}
        for child in wanted:
            job[child.tag] = (child.text or "").strip()
        jobs.append(job)
    return jobs


def _normalize_worknet_job(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id":        raw.get("wantedAuthNo") or raw.get("wantedNo"),
        "title":         raw.get("title", ""),
        "company":       raw.get("company", ""),
        "company_type":  raw.get("coTpNm", ""),
        "region":        raw.get("region", ""),
        "sal_type":      raw.get("salTpNm", ""),
        "salary":        raw.get("sal", ""),
        "employment_type": raw.get("empTpNm", ""),
        "education":     raw.get("eduNm", ""),
        "career":        raw.get("career", ""),
        "close_date":    raw.get("closeDt", ""),
        "reg_date":      raw.get("regDt", ""),
        "url":           raw.get("wantedInfoUrl") or raw.get("url", ""),
    }


def get_hiring_jobs(
    settings: Settings,
    occupation: str | None = None,
    cert_lic: str | None = None,
    region: str | None = None,
    keyword: str | None = None,
    education: str | None = None,
    display: int = 20,
) -> dict:
    """
    WorkNet 채용목록 조회.
    occupation: 직종코드 (예: "171" — 정보처리/컴퓨터 운용)
    cert_lic: 자격면허 코드
    region: 지역명(한국어) or 코드
    """
    api_key = settings.get_job_api_key
    if not api_key:
        return err_envelope(
            "API_KEY_MISSING",
            "워크넷 API 키가 설정되지 않았습니다.",
        )

    region_code: str | None = None
    if region:
        region_code = REGION_CODES.get(region, region if region.isdigit() else None)

    cache_key = f"hiring|{occupation}|{cert_lic}|{region}|{keyword}|{education}|{display}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params: dict[str, Any] = {
        "authKey":    api_key,
        "callTp":     "L",
        "returnType": "XML",
        "startPage":  "1",
        "display":    str(min(display, 100)),
    }
    if occupation:
        params["occupation"] = occupation
    if cert_lic:
        params["certLic"] = cert_lic
    if region_code:
        params["region"] = region_code
    if keyword:
        params["keyword"] = keyword
    if education:
        params["education"] = education

    try:
        resp = httpx.get(
            _WORKNET_BASE,
            params=params,
            timeout=settings.worknet_api_timeout,
        )
        resp.raise_for_status()
        raw_jobs = _parse_worknet_xml(resp.text)
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "워크넷 API 응답 시간이 초과되었습니다.")
    except httpx.HTTPStatusError as e:
        return err_envelope("EXTERNAL_API_ERROR", f"워크넷 API 오류: HTTP {e.response.status_code}")
    except ValueError as e:
        # WorkNet API 자체 에러 (예: 유효하지 않은 인증키)
        logger.warning("worknet API error response: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", f"워크넷 API 오류: {e}")
    except Exception as e:
        logger.warning("worknet API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "채용정보 조회 중 오류가 발생했습니다.")

    jobs = [_normalize_worknet_job(j) for j in raw_jobs]

    result = ok_envelope({
        "query": {
            "occupation": occupation,
            "cert_lic":   cert_lic,
            "region":     region,
            "keyword":    keyword,
        },
        "jobs":  jobs,
        "total": len(jobs),
    })
    _cache_set(cache_key, result)
    return result


def get_hiring_by_cert_id(
    cert_id: str,
    settings: Settings,
    region: str | None = None,
    display: int = 20,
) -> dict:
    """
    cert_id 기반 WorkNet 채용정보 조회.
    cert_lookup_service를 통해 cert_id → cert_name(keyword) + NCS → WorkNet occupation 코드 파생.
    직접 문자열 매칭 없이 canonical 데이터 체인으로 파라미터 생성.
    """
    from backend.app.services.cert_lookup_service import get_worknet_search_params, get_cert_info

    cert = get_cert_info(cert_id)
    if not cert:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")

    search_params = get_worknet_search_params(cert_id)

    return get_hiring_jobs(
        settings,
        occupation=search_params.get("occupation"),
        keyword=search_params.get("keyword"),
        region=region,
        display=display,
    )


def get_job_detail(job_name: str | None = None, job_code: str | None = None) -> dict:
    """
    고용24 직업정보 CSV에서 직업 상세 조회.
    job_name: 직업명 (부분 일치)
    job_code: 직업 코드 (완전 일치)
    """
    job_info = _load_job_info()
    if not job_info:
        return err_envelope("DATA_NOT_READY", "고용24 직업정보 CSV를 찾을 수 없습니다.")

    if not job_name and not job_code:
        return err_envelope("MISSING_REQUIRED_FIELD", "job_name 또는 job_code 중 하나가 필요합니다.")

    results = []
    for row in job_info:
        name_field = row.get("직업명", "") or row.get("job_name", "")
        code_field = row.get("직업코드", "") or row.get("job_code", "")

        if job_code and code_field == job_code:
            results.append(row)
        elif job_name and job_name in name_field:
            results.append(row)

    if not results:
        return err_envelope("NOT_FOUND", f"'{job_name or job_code}'에 해당하는 직업정보가 없습니다.")

    # 상위 5개만
    normalized = []
    for r in results[:5]:
        normalized.append({
            "job_name":       r.get("직업명") or r.get("job_name"),
            "job_code":       r.get("직업코드") or r.get("job_code"),
            "employment_type": r.get("취업방법") or r.get("employment_type"),
            "salary":         r.get("임금") or r.get("salary"),
            "satisfaction":   r.get("직업만족율") or r.get("satisfaction"),
            "future_outlook": r.get("직업예상") or r.get("future_outlook"),
            "work_content":   r.get("직업근무내용") or r.get("work_content"),
            "video_url":      r.get("직업안내동영상") or r.get("video_url"),
        })

    return ok_envelope({
        "query":   {"job_name": job_name, "job_code": job_code},
        "results": normalized,
        "total":   len(results),
    })
