# File: welfare_central_service.py
# Last Updated: 2026-06-25
# Content Hash: SHA256:TBD
# Role: 복지로 OPEN API — 중앙부처복지서비스 목록·상세 조회
#
# API: 한국사회보장정보원 복지로 OPEN API v2
#   목록 조회: GET https://apis.data.go.kr/B551537/wlfareSvc01/getWlfareSvcList01
#   상세 조회: GET https://apis.data.go.kr/B551537/wlfareSvc01/getWlfareSvcDetail01
#   인증키: BOKJIRO_API_KEY
#
# 활용 서비스 카테고리:
#   - 자기이해 및 심리상담 (심리상담, 정신건강 지원)
#   - 경제·생계·주거지원 (생계급여, 긴급복지, 주거지원)
#   - 가족지원 (가족상담·가족교육)
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_LIST_URL   = "https://apis.data.go.kr/B551537/wlfareSvc01/getWlfareSvcList01"
_DETAIL_URL = "https://apis.data.go.kr/B551537/wlfareSvc01/getWlfareSvcDetail01"

# 대상 그룹 코드 (복지로 API: interestedUser)
# 청소년·청년 관련 코드
_YOUTH_USER_CODE = "0010049"   # 청소년·청년

# 서비스 카테고리별 키워드 필터 (복지로 lifeEventCd)
CATEGORY_KEYWORD_MAP: dict[str, str] = {
    "자기이해및심리상담": "상담",
    "경제생계주거지원":   "긴급복지",
    "가족지원":          "가족",
}

_TTL = 600  # 10분 캐시
_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic(), value)


def _parse_items(raw_items: list[dict]) -> list[dict]:
    """복지로 API 응답 아이템을 DIDIM 표준 형태로 정규화."""
    result = []
    for item in raw_items:
        result.append({
            "id":           item.get("servId", ""),
            "name":         item.get("servNm", ""),
            "summary":      item.get("servDgst", ""),
            "provider":     item.get("jurMnofNm", ""),
            "target":       item.get("intrsUserAbrv", ""),
            "apply_url":    item.get("servDtlLink", ""),
            "area":         item.get("sigunguNm", ""),
            "source":       "중앙부처복지서비스",
        })
    return result


def get_welfare_services(
    settings: Settings,
    service_category: str,
    region: str | None = None,
    keyword: str | None = None,
    page_size: int = 5,
) -> dict:
    """
    중앙부처복지서비스 목록 조회.

    Args:
        service_category: 'self_understanding' | 'economic' | 'family'
        region: 시·도 이름 (예: '서울', '경기')
        keyword: 추가 검색어
        page_size: 결과 수 (기본 5)
    """
    api_key = settings.bokjiro_api_key or settings.gender_welfare_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "BOKJIRO_API_KEY 환경변수가 설정되지 않았습니다.")

    srch_keyword = keyword or CATEGORY_KEYWORD_MAP.get(service_category, "")
    cache_key = f"welfare_central:{service_category}:{region}:{srch_keyword}:{page_size}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params: dict[str, Any] = {
        "serviceKey":     api_key,
        "pageNo":         1,
        "numOfRows":      page_size,
        "callTp":         "L",
        "interestedUser": _YOUTH_USER_CODE,
        "returnType":     "json",
    }
    if srch_keyword:
        params["keyword"] = srch_keyword
    if region:
        params["sido"] = region

    try:
        with httpx.Client(timeout=settings.bokjiro_api_timeout) as client:
            resp = client.get(_LIST_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning("복지로 중앙부처 API HTTP 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", f"복지로 API 오류: {e.response.status_code}")
    except Exception as e:
        logger.warning("복지로 중앙부처 API 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", str(e))

    try:
        body = data.get("body", {}) or data.get("response", {}).get("body", {})
        items_raw = body.get("items", {}).get("item", [])
        if isinstance(items_raw, dict):
            items_raw = [items_raw]
        items = _parse_items(items_raw)
    except Exception as e:
        logger.warning("복지로 중앙부처 API 파싱 오류: %s | raw=%s", e, str(data)[:300])
        return err_envelope("PARSE_ERROR", "복지로 API 응답 파싱 오류")

    result = ok_envelope({
        "service_category": service_category,
        "region":           region,
        "keyword":          srch_keyword,
        "count":            len(items),
        "items":            items,
        "source":           "한국사회보장정보원_중앙부처복지서비스",
    })
    _cache_set(cache_key, result)
    return result
