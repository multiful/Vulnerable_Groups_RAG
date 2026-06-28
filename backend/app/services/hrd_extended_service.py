# File: hrd_extended_service.py
# Last Updated: 2026-06-26
# Content Hash: SHA256:TBD
# Role: Work24 확장 훈련과정 API
#   - 일학습병행 훈련과정 (F-29): callOpenApiSvcInfo313L01.do + GET_WORKSTUDY_API_KEY
#   - 국가인적자원개발 컨소시엄 훈련과정 (F-30): callOpenApiSvcInfo312L01.do + GET_HUMANDE_API_KEY
#   - 구직자취업역량 강화프로그램 (F-31): GET_PROGRAM_API_KEY + endpoint 승인 대기 중
#
# 공통 XML 응답 구조: <HRDNet><srchList><scn_list>...</scn_list></srchList></HRDNet>
# 훈련유형 구분: trainTarget 필드 (국가인적자원개발컨소시엄 / 공동훈련센터형 등)
from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_WORKSTUDY_URL  = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo313L01.do"
_HUMANDE_URL    = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo312L01.do"

_TTL = 300
_cache: dict[str, tuple[float, Any]] = {}

REGION_CODES: dict[str, str] = {
    "서울": "11", "부산": "26", "대구": "27", "인천": "28",
    "광주": "29", "대전": "30", "울산": "31", "세종": "36",
    "경기": "41", "강원": "51", "충북": "43", "충남": "44",
    "전북": "45", "전남": "46", "경북": "47", "경남": "48", "제주": "50",
}

NCS_CODES: dict[str, str] = {
    "사업관리": "01", "경영/회계/사무": "02", "금융/보험": "03",
    "교육/자연/사회과학": "04", "법률/경찰/소방/교도/국방": "05",
    "보건/의료": "06", "사회복지/종교": "07", "문화/예술/디자인/방송": "08",
    "운전/운송": "09", "영업판매": "10", "경비/청소": "11",
    "이용/숙박/여행/오락/스포츠": "12", "음식서비스": "13", "건설": "14",
    "기계": "15", "재료": "16", "화학/바이오": "17", "섬유/의복": "18",
    "전기/전자": "19", "정보통신": "20", "식품가공": "21",
    "인쇄/목재/가구/공예": "22", "환경/에너지/안전": "23", "농림어업": "24",
}


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic(), value)


def _parse_xml(xml_text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    courses: list[dict[str, Any]] = []
    for item in root.iter("scn_list"):
        raw: dict[str, Any] = {}
        for child in item:
            raw[child.tag] = (child.text or "").strip()
        courses.append(raw)
    return courses


def _normalize(raw: dict[str, Any], source_label: str) -> dict[str, Any]:
    return {
        "course_id":        raw.get("trprId") or raw.get("inst_base_id", ""),
        "course_name":      raw.get("title") or raw.get("trprNm", ""),
        "institution_name": raw.get("subTitle") or raw.get("traInstNm", ""),
        "institution_addr": raw.get("address") or raw.get("traAddr", ""),
        "course_url":       raw.get("titleLink", ""),
        "institution_url":  raw.get("subTitleLink", ""),
        "ncs_code":         raw.get("ncsCd", ""),
        "ncs_name":         raw.get("ncsCdNm", ""),
        "train_start":      raw.get("traStartDate") or raw.get("trStartDate", ""),
        "train_end":        raw.get("traEndDate")   or raw.get("trEndDate", ""),
        "capacity":         raw.get("yardMan", ""),
        "remaining":        raw.get("yremFxnum", ""),
        "tel":              raw.get("telNo", ""),
        "train_type":       raw.get("trainTarget", ""),
        "train_type_code":  raw.get("trainTargetCd", ""),
        "region_code":      raw.get("trngAreaCd", ""),
        "cost":             raw.get("courseMan", ""),
        "source":           source_label,
    }


def _call_work24(
    url: str,
    api_key: str,
    region: str | None,
    ncs_category: str | None,
    course_name: str | None,
    page_size: int,
    timeout: int,
) -> tuple[list[dict], int]:
    today = date.today()
    end_year  = today.year + ((today.month + 6 - 1) // 12)
    end_month = (today.month + 6 - 1) % 12 + 1

    params: dict[str, Any] = {
        "authKey":      api_key,
        "returnType":   "XML",
        "outType":      "1",
        "pageNum":      "1",
        "pageSize":     str(min(page_size, 100)),
        "srchTraStDt":  today.strftime("%Y%m%d"),
        "srchTraEndDt": f"{end_year}{end_month:02d}01",
        "sort":         "DESC",
        "sortCol":      "3",
    }
    if region:
        code = REGION_CODES.get(region)
        if code:
            params["srchTraArea1"] = code
    if course_name:
        params["srchTraProcessNm"] = course_name
    elif ncs_category:
        code = NCS_CODES.get(ncs_category)
        if code:
            params["srchNcs1"] = code

    resp = httpx.get(url, params=params, timeout=timeout)
    resp.raise_for_status()

    raw_list = _parse_xml(resp.text)
    total_count_el = ET.fromstring(resp.text).findtext("scn_cnt")
    total = int(total_count_el) if total_count_el and total_count_el.isdigit() else len(raw_list)
    return raw_list, total


# ── 일학습병행 훈련과정 (F-29) ────────────────────────────────────────────────

def get_workstudy_courses(
    settings: Settings,
    region: str | None = None,
    ncs_category: str | None = None,
    course_name: str | None = None,
    page_size: int = 20,
) -> dict:
    """
    일학습병행 훈련과정 목록 조회 (F-29).
    Work24 callOpenApiSvcInfo313L01 — 공동훈련센터형 일학습병행 과정.

    Args:
        region: 지역명 (예: 서울, 경기)
        ncs_category: NCS 1차 분류명 (예: 정보통신)
        course_name: 훈련과정명 검색어
        page_size: 결과 수 (기본 20, 최대 100)
    """
    api_key = settings.get_workstudy_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "GET_WORKSTUDY_API_KEY 환경변수가 설정되지 않았습니다.")

    page_size = min(max(1, page_size), 100)
    cache_key = f"workstudy:{region}:{ncs_category}:{course_name}:{page_size}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        raw_list, total = _call_work24(
            _WORKSTUDY_URL, api_key, region, ncs_category, course_name,
            page_size, settings.training_api_timeout,
        )
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "일학습병행 훈련과정 API 응답 시간이 초과되었습니다.")
    except httpx.HTTPStatusError as e:
        logger.warning("일학습병행 API HTTP 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", f"Work24 일학습병행 API 오류: {e.response.status_code}")
    except Exception as e:
        logger.warning("일학습병행 API 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", str(e))

    courses = [_normalize(r, "Work24_일학습병행") for r in raw_list]

    result = ok_envelope({
        "region":       region,
        "ncs_category": ncs_category,
        "course_name":  course_name,
        "total":        total,
        "count":        len(courses),
        "courses":      courses,
        "source":       "Work24_일학습병행훈련과정",
    })
    _cache_set(cache_key, result)
    return result


# ── 국가인적자원개발 컨소시엄 훈련과정 (F-30) ────────────────────────────────

def get_consortium_courses(
    settings: Settings,
    region: str | None = None,
    ncs_category: str | None = None,
    course_name: str | None = None,
    page_size: int = 20,
) -> dict:
    """
    국가인적자원개발 컨소시엄 훈련과정 목록 조회 (F-30).
    Work24 callOpenApiSvcInfo312L01 — 기업 컨소시엄 기반 훈련.

    Args:
        region: 지역명 (예: 서울, 경기)
        ncs_category: NCS 1차 분류명 (예: 정보통신)
        course_name: 훈련과정명 검색어
        page_size: 결과 수 (기본 20, 최대 100)
    """
    api_key = settings.get_humande_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "GET_HUMANDE_API_KEY 환경변수가 설정되지 않았습니다.")

    page_size = min(max(1, page_size), 100)
    cache_key = f"consortium:{region}:{ncs_category}:{course_name}:{page_size}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        raw_list, total = _call_work24(
            _HUMANDE_URL, api_key, region, ncs_category, course_name,
            page_size, settings.training_api_timeout,
        )
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "국가인적자원개발 컨소시엄 API 응답 시간이 초과되었습니다.")
    except httpx.HTTPStatusError as e:
        logger.warning("국가인적자원개발 컨소시엄 API HTTP 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", f"Work24 컨소시엄 API 오류: {e.response.status_code}")
    except Exception as e:
        logger.warning("국가인적자원개발 컨소시엄 API 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", str(e))

    courses = [_normalize(r, "Work24_국가인적자원개발컨소시엄") for r in raw_list]

    result = ok_envelope({
        "region":       region,
        "ncs_category": ncs_category,
        "course_name":  course_name,
        "total":        total,
        "count":        len(courses),
        "courses":      courses,
        "source":       "Work24_국가인적자원개발컨소시엄훈련과정",
    })
    _cache_set(cache_key, result)
    return result


# ── 구직자취업역량 강화프로그램 (F-31) ────────────────────────────────────────

def get_jobseeker_programs(
    settings: Settings,
    region: str | None = None,
    keyword: str | None = None,
    page_size: int = 10,
) -> dict:
    """
    구직자취업역량 강화프로그램 조회 (F-31).
    GET_PROGRAM_API_KEY 발급 완료, Work24 서비스 엔드포인트 승인 대기 중.

    Args:
        region: 지역명
        keyword: 검색어
        page_size: 결과 수
    """
    api_key = settings.get_program_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "GET_PROGRAM_API_KEY 환경변수가 설정되지 않았습니다.")

    return err_envelope(
        "SERVICE_PENDING",
        "구직자취업역량 강화프로그램 API 키가 발급되어 있으나, "
        "Work24 서비스 엔드포인트가 아직 승인 처리 중입니다. "
        "승인 완료 후 자동으로 활성화됩니다.",
    )
