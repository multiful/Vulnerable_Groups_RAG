# File: gender_facility_service.py
# Last Updated: 2026-06-25
# Content Hash: SHA256:TBD
# Role: 성평등가족부 — 여성·가족·청소년·권익시설 정보 조회 (시설찾기 서비스)
#
# API: 성평등가족부 여성가족 OPEN API (시설찾기 조회 서비스)
#   참고: 여성가족부_Open API_조회_서비스_활용가이드_v1.0 (시설찾기 조회 서비스).docx
#   기관유형별 목록: GET https://apis.data.go.kr/B553530/GFacility01/getGFacility01
#   인증키: GENDER_WELFARE_API_KEY
#
# 활용 서비스 카테고리:
#   - 자기이해 및 심리상담 (청소년상담복지센터, 상담시설)
#   - 치유적 관계형성 (관계회복 지원기관)
#   - 가족지원 (가족지원센터)
#
# 기관유형 코드 (activeTy):
#   01: 가족센터, 02: 가정폭력상담소, 03: 청소년상담복지센터,
#   04: 한부모가족지원센터, 05: 다문화가족지원센터 등
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_BASE_URL = "https://apis.data.go.kr/B553530/GFacility01/getGFacility01"

# 카테고리별 기관유형 코드 매핑
CATEGORY_FACILITY_TYPES: dict[str, list[str]] = {
    "자기이해및심리상담": ["03"],        # 청소년상담복지센터
    "치유적관계형성":     ["01", "03"],   # 가족센터 + 청소년상담
    "가족지원":          ["01", "04"],   # 가족센터 + 한부모가족지원
}

# 시도 코드
SIDO_CODES: dict[str, str] = {
    "서울": "11", "부산": "26", "대구": "27", "인천": "28",
    "광주": "29", "대전": "30", "울산": "31", "세종": "36",
    "경기": "41", "강원": "42", "충북": "43", "충남": "44",
    "전북": "45", "전남": "46", "경북": "47", "경남": "48", "제주": "50",
}

_TTL = 3600
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
            "id":            item.get("instId", "") or item.get("fcltyId", ""),
            "name":          item.get("instNm", "") or item.get("fcltyNm", ""),
            "facility_type": item.get("activeTyNm", "") or item.get("instTyCdNm", ""),
            "address":       item.get("rdnmadr", "") or item.get("addr", ""),
            "tel":           item.get("phoneNumber", "") or item.get("telNo", ""),
            "area":          item.get("ctprvnNm", ""),
            "source":        "여성가족청소년시설",
        })
    return result


def get_gender_facilities(
    settings: Settings,
    service_category: str,
    region: str | None = None,
    page_size: int = 5,
) -> dict:
    """
    여성·가족·청소년·권익시설 목록 조회.

    Args:
        service_category: 'self_understanding' | 'therapeutic_relation' | 'family'
        region: 거주 지역 이름
        page_size: 결과 수 (기본 5)
    """
    api_key = settings.gender_welfare_api_key or settings.bokjiro_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "GENDER_WELFARE_API_KEY 환경변수가 설정되지 않았습니다.")

    facility_types = CATEGORY_FACILITY_TYPES.get(service_category, ["01"])
    sido_code = _region_to_sido_code(region)
    cache_key = f"gender_facility:{service_category}:{sido_code}:{page_size}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    all_items: list[dict] = []
    per_type = max(1, page_size // len(facility_types))

    for ftype in facility_types:
        params: dict[str, Any] = {
            "serviceKey": api_key,
            "pageNo":     1,
            "numOfRows":  per_type,
            "type":       "json",
            "activeTy":   ftype,
        }
        if sido_code:
            params["ctprvnCd"] = sido_code

        try:
            with httpx.Client(timeout=settings.gender_welfare_api_timeout) as client:
                resp = client.get(_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

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
            all_items.extend(_parse_items(items_raw or []))
        except Exception as e:
            logger.warning("여성가족시설 API 오류 (type=%s): %s", ftype, e)

    result = ok_envelope({
        "service_category":  service_category,
        "region":            region,
        "facility_types":    facility_types,
        "count":             len(all_items),
        "items":             all_items[:page_size],
        "source":            "성평등가족부_여성가족청소년시설",
    })
    _cache_set(cache_key, result)
    return result
