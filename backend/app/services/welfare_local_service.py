# File: welfare_local_service.py
# Last Updated: 2026-06-25
# Content Hash: SHA256:TBD
# Role: 복지로 OPEN API — 지자체복지서비스 목록 조회
#
# API: 한국사회보장정보원 복지로 OPEN API v2
#   목록 조회: GET https://apis.data.go.kr/B551537/wlfareSvc02/getWlfareSvcList02
#   인증키: BOKJIRO_API_KEY
#
# 활용 서비스 카테고리:
#   - 치유적 관계형성 (사회적 관계 회복, 자조모임)
#   - 사후관리 (지역 기반 상담)
#   - 경제·생계·주거지원 (지자체 긴급지원, 주거·생활지원)
#
# 지자체 코드: 지자체복지서비스_코드표(v1.0).doc 참조
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_LIST_URL = "https://apis.data.go.kr/B551537/wlfareSvc02/getWlfareSvcList02"

# 시도 코드 (복지로 API 기준)
SIDO_CODES: dict[str, str] = {
    "서울": "11", "부산": "26", "대구": "27", "인천": "28",
    "광주": "29", "대전": "30", "울산": "31", "세종": "36",
    "경기": "41", "강원": "42", "충북": "43", "충남": "44",
    "전북": "45", "전남": "46", "경북": "47", "경남": "48", "제주": "50",
}

CATEGORY_KEYWORD_MAP: dict[str, str] = {
    "치유적관계형성": "관계",
    "사후관리":       "상담",
    "경제생계주거지원": "긴급",
}

_TTL = 600
_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic(), value)


def _region_to_sido_code(region: str | None) -> str | None:
    if not region:
        return None
    for key, code in SIDO_CODES.items():
        if key in region:
            return code
    return None


def _parse_items(raw_items: list[dict]) -> list[dict]:
    result = []
    for item in raw_items:
        result.append({
            "id":        item.get("servId", ""),
            "name":      item.get("servNm", ""),
            "summary":   item.get("servDgst", ""),
            "provider":  item.get("jurMnofNm", ""),
            "area":      item.get("sigunguNm", ""),
            "apply_url": item.get("servDtlLink", ""),
            "source":    "지자체복지서비스",
        })
    return result


def get_local_welfare_services(
    settings: Settings,
    service_category: str,
    region: str | None = None,
    keyword: str | None = None,
    page_size: int = 5,
) -> dict:
    """
    지자체복지서비스 목록 조회.

    Args:
        service_category: 'therapeutic_relation' | 'followup' | 'economic'
        region: 거주 지역 이름 (예: '서울', '경기 수원')
        keyword: 추가 검색어
        page_size: 결과 수 (기본 5)
    """
    api_key = settings.bokjiro_api_key or settings.gender_welfare_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "BOKJIRO_API_KEY 환경변수가 설정되지 않았습니다.")

    srch_keyword = keyword or CATEGORY_KEYWORD_MAP.get(service_category, "청년")
    sido_code = _region_to_sido_code(region)
    cache_key = f"welfare_local:{service_category}:{sido_code}:{srch_keyword}:{page_size}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params: dict[str, Any] = {
        "serviceKey": api_key,
        "pageNo":     1,
        "numOfRows":  page_size,
        "callTp":     "L",
        "returnType": "json",
    }
    if sido_code:
        params["sidoCd"] = sido_code
    if srch_keyword:
        params["keyword"] = srch_keyword

    try:
        with httpx.Client(timeout=settings.bokjiro_api_timeout) as client:
            resp = client.get(_LIST_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning("복지로 지자체 API HTTP 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", f"복지로 지자체 API 오류: {e.response.status_code}")
    except Exception as e:
        logger.warning("복지로 지자체 API 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", str(e))

    try:
        body = data.get("body", {}) or data.get("response", {}).get("body", {})
        items_raw = body.get("items", {}).get("item", [])
        if isinstance(items_raw, dict):
            items_raw = [items_raw]
        items = _parse_items(items_raw)
    except Exception as e:
        logger.warning("복지로 지자체 API 파싱 오류: %s", e)
        return err_envelope("PARSE_ERROR", "복지로 지자체 API 응답 파싱 오류")

    result = ok_envelope({
        "service_category": service_category,
        "region":           region,
        "sido_code":        sido_code,
        "keyword":          srch_keyword,
        "count":            len(items),
        "items":            items,
        "source":           "한국사회보장정보원_지자체복지서비스",
    })
    _cache_set(cache_key, result)
    return result
