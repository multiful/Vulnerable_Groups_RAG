# File: worknet_govt_jobs_service.py
# Last Updated: 2026-06-25
# Content Hash: SHA256:TBD
# Role: 워크넷 정부지원일자리정보 — 참여자모집상세정보 조회
#
# API: 한국고용정보원 워크넷 정부지원일자리정보 OPEN API
#   참여자모집상세정보:
#     GET https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo380L02.do
#   인증키: WORKNET_GOVT_JOBS_API_KEY (또는 GET_JOB_API_KEY 공유 가능)
#   포맷: XML
#
# 활용 서비스 카테고리:
#   - 일 경험 및 사회활동 (청년도전지원사업, 일경험 프로그램, 사회활동 프로그램)
#   → 고립위험청년(1단계), 활동형고립청년(2단계)에만 해당
from __future__ import annotations

import logging
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo380L02.do"

# 지역 코드 (워크넷 기준)
REGION_CODES: dict[str, str] = {
    "서울": "11", "부산": "26", "대구": "27", "인천": "28",
    "광주": "29", "대전": "30", "울산": "31", "세종": "36",
    "경기": "41", "강원": "51", "충북": "43", "충남": "44",
    "전북": "45", "전남": "46", "경북": "47", "경남": "48", "제주": "50",
}

# 정부지원사업 유형 중 고립·은둔 청년 관련 키워드
_YOUTH_ISOLATION_KEYWORDS = ["청년도전", "고립", "은둔", "사회참여", "일경험", "활동가"]

_TTL = 300
_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic(), value)


def _region_code(region: str | None) -> str | None:
    if not region:
        return None
    for key, code in REGION_CODES.items():
        if key in region:
            return code
    return None


def _parse_xml(xml_text: str) -> list[dict]:
    """워크넷 참여자모집 XML 응답 파싱."""
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.iter("item"):
            def _t(tag: str) -> str:
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else ""

            items.append({
                "id":           _t("recrutPblntSn") or _t("jobId"),
                "title":        _t("recrutPbancTtl") or _t("title"),
                "org":          _t("insttNm") or _t("company"),
                "region":       _t("workRgnNm") or _t("region"),
                "target":       _t("acbgCondNmLst") or _t("target"),
                "period":       f"{_t('recrutPdBegin')} ~ {_t('recrutPdEnd')}",
                "detail_url":   _t("detailUrl") or "",
                "program_type": _t("pbancClCdNm") or "정부지원일자리",
                "source":       "워크넷_정부지원일자리_참여자모집",
            })
    except ET.ParseError as e:
        logger.warning("워크넷 참여자모집 XML 파싱 오류: %s", e)
    return items


def get_govt_job_recruitments(
    settings: Settings,
    region: str | None = None,
    keyword: str | None = None,
    page_size: int = 5,
) -> dict:
    """
    워크넷 정부지원일자리 참여자모집 목록 조회.

    Args:
        region: 거주 지역 이름 (예: '서울', '경기')
        keyword: 검색어 (기본: '청년도전')
        page_size: 결과 수 (기본 5)
    """
    # GET_JOB_API_KEY 또는 전용 키 사용
    api_key = settings.worknet_govt_jobs_api_key or settings.get_job_api_key
    if not api_key:
        return err_envelope(
            "API_KEY_MISSING",
            "WORKNET_GOVT_JOBS_API_KEY 또는 GET_JOB_API_KEY 환경변수가 설정되지 않았습니다.",
        )

    srch_keyword = keyword or "청년"
    region_code = _region_code(region)
    cache_key = f"govt_jobs:{region_code}:{srch_keyword}:{page_size}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params: dict[str, Any] = {
        "authKey":    api_key,
        "returnType": "XML",
        "startPage":  1,
        "display":    page_size,
        "srchText":   srch_keyword,
    }
    if region_code:
        params["workRgnCd"] = region_code

    try:
        url = _BASE_URL + "?" + urllib.parse.urlencode(params)
        with httpx.Client(timeout=settings.worknet_govt_jobs_api_timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            items = _parse_xml(resp.text)
    except httpx.HTTPStatusError as e:
        logger.warning("워크넷 참여자모집 API HTTP 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", f"워크넷 API 오류: {e.response.status_code}")
    except Exception as e:
        logger.warning("워크넷 참여자모집 API 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", str(e))

    result = ok_envelope({
        "region":   region,
        "keyword":  srch_keyword,
        "count":    len(items),
        "items":    items,
        "source":   "한국고용정보원_워크넷_정부지원일자리_참여자모집",
    })
    _cache_set(cache_key, result)
    return result
