# File: training_service.py
# Last Updated: 2026-05-20
# Content Hash: SHA256:TBD
# Role: 국민내일배움카드 훈련과정 API + 과정평가형 자격 조회
# cert_id 기반 검색은 cert_lookup_service를 경유한다 (canonical 데이터 연결 원칙)
#
# APIs:
#   훈련과정 목록: https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo310L01.do
#     인증키: GET_TRAINING_API_KEY
#   과정평가형 종목: http://openapi.q-net.or.kr/api/service/rest/ProcessEvalService/...
#     인증키: HRDKOREA_API_KEY_IN
from __future__ import annotations

import logging
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_TRAINING_BASE = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo310L01.do"
# NOTE: openapi.q-net.or.kr/ProcessEvalService 폐지(2025). B490007 대체 없음.
# process_eval / job_learner 함수는 graceful unavailable 응답으로 처리.
_QNET_PROCESS_EVAL_URL = "https://www.q-net.or.kr/man004.do?id=man00401&gSite=Q"
_QNET_JOB_LEARNER_URL  = "https://www.q-net.or.kr/ilhak001.do"


def _build_qnet_url(base: str, api_key_in: str, extra: dict[str, str]) -> str:
    """이미 URL-인코딩된 serviceKey를 직접 삽입 — params dict 사용 시 이중인코딩 발생."""
    qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in extra.items())
    return f"{base}?serviceKey={api_key_in}&{qs}"

_TTL = 300
_training_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    entry = _training_cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _training_cache[key] = (time.monotonic(), value)

# 훈련지역 코드 (Work24 기준)
TRAINING_REGION_CODES: dict[str, str] = {
    "서울": "11", "부산": "26", "대구": "27", "인천": "28",
    "광주": "29", "대전": "30", "울산": "31", "세종": "36",
    "경기": "41", "강원": "51", "충북": "43", "충남": "44",
    "전북": "45", "전남": "46", "경북": "47", "경남": "48", "제주": "50",
}

# NCS 1차 분류 코드
NCS_LEVEL1_CODES: dict[str, str] = {
    "사업관리":           "01",
    "경영/회계/사무":     "02",
    "금융/보험":          "03",
    "교육/자연/사회과학": "04",
    "법률/경찰/소방/교도/국방": "05",
    "보건/의료":          "06",
    "사회복지/종교":      "07",
    "문화/예술/디자인/방송": "08",
    "운전/운송":          "09",
    "영업판매":           "10",
    "경비/청소":          "11",
    "이용/숙박/여행/오락/스포츠": "12",
    "음식서비스":         "13",
    "건설":               "14",
    "기계":               "15",
    "재료":               "16",
    "화학/바이오":        "17",
    "섬유/의복":          "18",
    "전기/전자":          "19",
    "정보통신":           "20",
    "식품가공":           "21",
    "인쇄/목재/가구/공예": "22",
    "환경/에너지/안전":   "23",
    "농림어업":           "24",
}


def _parse_training_xml(xml_text: str) -> list[dict[str, Any]]:
    """Work24 훈련과정 XML 파싱. 응답 구조: <HRDNet><srchList><scn_list>...</scn_list></srchList></HRDNet>"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    courses: list[dict[str, Any]] = []
    for item in root.iter("scn_list"):
        course: dict[str, Any] = {}
        for child in item:
            course[child.tag] = (child.text or "").strip()
        courses.append(course)
    return courses


def _normalize_training_course(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "course_id":        raw.get("trprId") or raw.get("inst_base_id"),
        "course_name":      raw.get("title") or raw.get("trprNm"),
        "institution_name": raw.get("subTitle") or raw.get("traInstNm"),
        "institution_addr": raw.get("address") or raw.get("traAddr"),
        "course_url":       raw.get("titleLink"),
        "institution_url":  raw.get("subTitleLink"),
        "ncs_name":         raw.get("ncsCdNm"),
        "train_start":      raw.get("traStartDate") or raw.get("trStartDate"),
        "train_end":        raw.get("traEndDate")   or raw.get("trEndDate"),
        "train_hours":      raw.get("realTrainHr"),
        "cost":             raw.get("courseMan"),
        "support_amount":   raw.get("govSptAmt"),
        "satisfaction":     raw.get("eiEmplRate3"),
        "employment_rate":  raw.get("eiEmplRate6"),
        "capacity":         raw.get("totFxnum") or raw.get("yardMan"),
        "remaining":        raw.get("yremFxnum"),
        "tel":              raw.get("telNo"),
        "homepage":         raw.get("hpAddr") or raw.get("subTitleLink"),
    }


def get_training_courses(
    settings: Settings,
    region: str | None = None,
    ncs_category: str | None = None,
    course_name: str | None = None,
    course_type: str | None = None,
    page_size: int = 20,
) -> dict:
    """
    국민내일배움카드 훈련과정 목록 조회.
    region: 지역명 (예: "서울")
    ncs_category: NCS 1차 분류명 (예: "정보통신")
    course_name: 훈련과정명 검색어
    course_type: 훈련유형 코드 (예: "C0061" — 국민내일배움카드(일반))
    """
    api_key = settings.get_training_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "훈련과정 API 키가 설정되지 않았습니다.")

    today = date.today()
    # 조회 기간: 오늘 ~ 6개월 후 (더 넓은 기간으로 결과 확보)
    end_month = (today.month + 6 - 1) % 12 + 1
    end_year  = today.year + ((today.month + 6 - 1) // 12)
    train_end_dt = f"{end_year}{end_month:02d}01"

    params: dict[str, Any] = {
        "authKey":     api_key,
        "returnType":  "XML",
        "outType":     "1",
        "pageNum":     "1",
        "pageSize":    str(min(page_size, 100)),
        "srchTraStDt": today.strftime("%Y%m%d"),
        "srchTraEndDt": train_end_dt,
        "sort":        "DESC",
        "sortCol":     "3",  # 취업률 기준 정렬
    }

    if region:
        region_code = TRAINING_REGION_CODES.get(region, region if len(region) == 2 else None)
        if region_code:
            params["srchTraArea1"] = region_code

    if course_name:
        # 키워드가 있을 때는 NCS 필터 없이 키워드만 사용 (NCS+키워드 조합은 결과가 급감)
        params["srchTraProcessNm"] = course_name
    elif ncs_category:
        ncs_code = NCS_LEVEL1_CODES.get(ncs_category)
        if ncs_code:
            params["srchNcs1"] = ncs_code

    if course_type:
        params["crseTracseSe"] = course_type

    cache_key = f"training|{region}|{ncs_category}|{course_name}|{course_type}|{page_size}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        resp = httpx.get(
            _TRAINING_BASE,
            params=params,
            timeout=settings.training_api_timeout,
        )
        resp.raise_for_status()
        raw_courses = _parse_training_xml(resp.text)
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "훈련과정 API 응답 시간이 초과되었습니다.")
    except httpx.HTTPStatusError as e:
        return err_envelope("EXTERNAL_API_ERROR", f"훈련과정 API 오류: HTTP {e.response.status_code}")
    except Exception as e:
        logger.warning("training API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "훈련과정 조회 중 오류가 발생했습니다.")

    courses = [_normalize_training_course(c) for c in raw_courses]

    # 동일 과정이 회차별로 중복 조회되는 경우 제거 (course_name + institution_name 기준)
    seen: set[tuple[str, str]] = set()
    unique_courses: list[dict[str, Any]] = []
    for c in courses:
        key = (c.get("course_name") or "", c.get("institution_name") or "")
        if key not in seen:
            seen.add(key)
            unique_courses.append(c)
    courses = unique_courses

    result = ok_envelope({
        "query": {
            "region":       region,
            "ncs_category": ncs_category,
            "course_name":  course_name,
            "period_from":  today.strftime("%Y-%m-%d"),
            "period_to":    f"{end_year}-{end_month:02d}-01",
        },
        "courses": courses,
        "total":   len(courses),
    })
    _cache_set(cache_key, result)
    return result


def get_training_by_cert_id(
    cert_id: str,
    settings: Settings,
    region: str | None = None,
    page_size: int = 20,
) -> dict:
    """
    cert_id 기반 훈련과정 조회.
    cert_lookup_service → cert_id → NCS 대직무코드 → Work24 srchNcs1 파라미터 파생.
    직접 문자열 매칭 없이 canonical 데이터 체인으로 파라미터 생성.
    """
    from backend.app.services.cert_lookup_service import get_training_search_params, get_cert_info

    cert = get_cert_info(cert_id)
    if not cert:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")

    search_params = get_training_search_params(cert_id)

    result = get_training_courses(
        settings,
        region=region,
        ncs_category=search_params.get("ncs_category"),
        course_name=search_params.get("course_name"),
        page_size=page_size,
    )
    # course_name이 너무 구체적이면 결과 0건 → ncs_category 단독으로 재시도
    if (
        result.get("success")
        and result.get("data", {}).get("total", 0) == 0
        and search_params.get("course_name")
        and search_params.get("ncs_category")
    ):
        result = get_training_courses(
            settings,
            region=region,
            ncs_category=search_params.get("ncs_category"),
            course_name=None,
            page_size=page_size,
        )
        if result.get("success") and result.get("data"):
            result["data"]["fallback_note"] = "자격증명 검색 결과가 없어 NCS 분류로 조회했습니다."
    return result


def get_process_eval_courses(
    settings: Settings,
    keyword: str | None = None,
    page_size: int = 20,
) -> dict:
    """
    과정평가형 자격 종목 조회.
    openapi.q-net.or.kr/ProcessEvalService 폐지(2025), B490007 대체 없음.
    Q-Net 공식 웹페이지 링크와 안내 메시지를 반환.
    """
    return ok_envelope({
        "keyword":    keyword,
        "items":      [],
        "total":      0,
        "api_status": "unavailable",
        "note":       "과정평가형 자격은 교육 이수로 취득 가능 — 시험 부담이 낮습니다.",
        "qnet_url":   _QNET_PROCESS_EVAL_URL,
        "qnet_label": "Q-Net 과정평가형 자격 바로가기",
    })


def get_job_learner_courses(
    settings: Settings,
    keyword: str | None = None,
    page_size: int = 20,
) -> dict:
    """
    일학습병행 과정 지정평가 정보 조회.
    openapi.q-net.or.kr/ProcessEvalService 폐지(2025), B490007 대체 없음.
    Q-Net 공식 웹페이지 링크와 안내 메시지를 반환.
    """
    return ok_envelope({
        "keyword":    keyword,
        "items":      [],
        "total":      0,
        "api_status": "unavailable",
        "note":       "일학습병행은 기업 현장 훈련으로 자격을 취득하는 경로입니다.",
        "qnet_url":   _QNET_JOB_LEARNER_URL,
        "qnet_label": "Q-Net 일학습병행 바로가기",
    })
