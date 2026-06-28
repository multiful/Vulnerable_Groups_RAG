# File: family_center_service.py
# Last Updated: 2026-06-25
# Content Hash: SHA256:TBD
# Role: 성평등가족부 — 건강가정지원센터 시설 조회
#
# API: 성평등가족부 OPEN API
#   시설 목록: GET https://apis.data.go.kr/B383000/gmis/hFthHomeSprnServiceV2
#   인증키: GENDER_WELFARE_API_KEY
#   포맷: JSON+XML (returnType=json)
#
# 활용 서비스 카테고리:
#   - 가족지원 (가족상담, 가족교육, 가족관계 회복, 보호자 상담)
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_BASE_URL = "https://apis.data.go.kr/B383000/gmis/hFthHomeSprnServiceV2"

# 시도 코드 (건강가정지원센터 API 기준)
SIDO_CODES: dict[str, str] = {
    "서울": "11", "부산": "26", "대구": "27", "인천": "28",
    "광주": "29", "대전": "30", "울산": "31", "세종": "36",
    "경기": "41", "강원": "42", "충북": "43", "충남": "44",
    "전북": "45", "전남": "46", "경북": "47", "경남": "48", "제주": "50",
}

_TTL = 3600  # 시설 정보는 1시간 캐시 (변동 적음)
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
            "id":       item.get("cntInstId", "") or item.get("instId", ""),
            "name":     item.get("instNm", "") or item.get("cntInstNm", ""),
            "address":  item.get("roadAddr", "") or item.get("addr", ""),
            "tel":      item.get("telNo", "") or item.get("tel", ""),
            "services": item.get("svcsNm", "") or item.get("instDtlInfo", ""),
            "area":     item.get("ctpvNm", "") or item.get("sidoNm", ""),
            "source":   "건강가정지원센터",
        })
    return result


def get_family_centers(
    settings: Settings,
    region: str | None = None,
    page_size: int = 5,
) -> dict:
    """
    건강가정지원센터 시설 목록 조회.

    Args:
        region: 거주 지역 이름 (예: '서울', '경기')
        page_size: 결과 수 (기본 5)
    """
    api_key = settings.gender_welfare_api_key or settings.bokjiro_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "GENDER_WELFARE_API_KEY 환경변수가 설정되지 않았습니다.")

    sido_code = _region_to_sido_code(region)
    cache_key = f"family_center:{sido_code}:{page_size}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params: dict[str, Any] = {
        "serviceKey": api_key,
        "pageNo":     1,
        "numOfRows":  page_size,
        "type":       "json",
    }
    if sido_code:
        params["ctpvCd"] = sido_code

    try:
        with httpx.Client(timeout=settings.gender_welfare_api_timeout) as client:
            resp = client.get(_BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning("건강가정지원센터 API HTTP 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", f"건강가정지원센터 API 오류: {e.response.status_code}")
    except Exception as e:
        logger.warning("건강가정지원센터 API 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", str(e))

    try:
        # 응답 구조: {response: {body: {items: {item: [...]}}}} 또는 {body: {items: [...]}}
        body = (
            data.get("response", {}).get("body", {})
            or data.get("body", {})
            or data
        )
        items_raw = body.get("items", {})
        if isinstance(items_raw, dict):
            items_raw = items_raw.get("item", [])
        if isinstance(items_raw, dict):
            items_raw = [items_raw]
        items = _parse_items(items_raw or [])
    except Exception as e:
        logger.warning("건강가정지원센터 API 파싱 오류: %s", e)
        return err_envelope("PARSE_ERROR", "건강가정지원센터 API 응답 파싱 오류")

    result = ok_envelope({
        "region":    region,
        "sido_code": sido_code,
        "count":     len(items),
        "items":     items,
        "source":    "성평등가족부_건강가정지원센터",
    })
    _cache_set(cache_key, result)
    return result
