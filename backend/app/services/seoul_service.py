# File: seoul_service.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 서울시 공공데이터 API — 일자리카페, 건강증진센터, 공공서비스 예약
#
# APIs (서울 열린데이터광장):
#   일자리카페:     https://openapi.seoul.go.kr:8088/{key}/json/jobCafe/1/100/
#   건강증진센터:   https://openapi.seoul.go.kr:8088/{key}/json/HealthCenterInfo/1/100/
#   공공서비스 예약: https://openapi.seoul.go.kr:8088/{key}/json/tvYeyakCOllect/1/100/
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_SEOUL_BASE = "https://openapi.seoul.go.kr:8088"

_TTL = 3600  # 서울시 시설 정보는 하루 단위로 바뀜 — 1시간 캐시
_seoul_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    entry = _seoul_cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _seoul_cache[key] = (time.monotonic(), value)


def _seoul_url(api_key: str, service_name: str, start: int = 1, end: int = 100) -> str:
    return f"{_SEOUL_BASE}/{api_key}/json/{service_name}/{start}/{end}/"


def _parse_seoul_response(data: dict, service_name: str) -> list[dict]:
    """서울 API 공통 응답 파싱. 서비스명 키로 items 추출."""
    svc_data = data.get(service_name, {})
    if isinstance(svc_data, dict):
        return svc_data.get("row", [])
    return []


def get_job_cafes(settings: Settings, gu: str | None = None) -> dict:
    """
    서울시 일자리카페 정보 조회.
    gu: 구 이름으로 필터 (예: "강남구")
    서비스: OA-15356
    """
    api_key = settings.seoul_api_key3
    if not api_key:
        return err_envelope("API_KEY_MISSING", "서울시 일자리카페 API 키가 설정되지 않았습니다.")

    cafe_cache_key = f"job_cafes|{gu}"
    cached = _cache_get(cafe_cache_key)
    if cached is not None:
        return cached

    url = _seoul_url(api_key, "jobCafe")
    try:
        resp = httpx.get(url, timeout=settings.seoul_api_timeout)
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "서울시 일자리카페 API 응답 시간이 초과되었습니다.")
    except Exception as e:
        logger.warning("job cafe API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "일자리카페 조회 중 오류가 발생했습니다.")

    rows = _parse_seoul_response(data, "jobCafe")

    # 구 필터
    if gu:
        rows = [r for r in rows if gu in (r.get("GU_NM", "") or r.get("ADDR", ""))]

    cafes = []
    for r in rows:
        cafes.append({
            "name":         r.get("CAFE_NM") or r.get("FCLTY_NM"),
            "address":      r.get("ADDR") or r.get("RDNMADR_NM"),
            "gu":           r.get("GU_NM"),
            "phone":        r.get("TELNO"),
            "open_hours":   r.get("OPERTN_HR") or r.get("OPER_TIME"),
            "services":     r.get("SERVC_CN") or r.get("SERVICE"),
            "lat":          r.get("LAT") or r.get("Y_COORD"),
            "lng":          r.get("LNG") or r.get("X_COORD"),
            "homepage":     r.get("HMPG_ADDR"),
        })

    result = ok_envelope({
        "filter_gu": gu,
        "cafes":     cafes,
        "total":     len(cafes),
    })
    _cache_set(cafe_cache_key, result)
    return result


def get_health_centers(settings: Settings, gu: str | None = None) -> dict:
    """
    서울시 건강증진센터(정신건강 포함) 정보 조회.
    고위험군 청년에게 돌봄 지원 연계용.
    서비스: OA-20438
    """
    api_key = settings.seoul_api_key2
    if not api_key:
        return err_envelope("API_KEY_MISSING", "서울시 건강증진센터 API 키가 설정되지 않았습니다.")

    health_cache_key = f"health_centers|{gu}"
    cached = _cache_get(health_cache_key)
    if cached is not None:
        return cached

    url = _seoul_url(api_key, "HealthCenterInfo")
    try:
        resp = httpx.get(url, timeout=settings.seoul_api_timeout)
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "건강증진센터 API 응답 시간이 초과되었습니다.")
    except Exception as e:
        logger.warning("health center API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "건강증진센터 조회 중 오류가 발생했습니다.")

    rows = _parse_seoul_response(data, "HealthCenterInfo")

    if gu:
        rows = [r for r in rows if gu in (r.get("GU_NM", "") or r.get("ADDR", ""))]

    centers = []
    for r in rows:
        centers.append({
            "name":       r.get("FCLTY_NM") or r.get("INST_NM"),
            "address":    r.get("RDNMADR_NM") or r.get("ADDR"),
            "gu":         r.get("GU_NM"),
            "phone":      r.get("TELNO"),
            "open_hours": r.get("OPERTN_HR"),
            "services":   r.get("SERVC_CN"),
            "lat":        r.get("LAT") or r.get("Y_COORD"),
            "lng":        r.get("LNG") or r.get("X_COORD"),
        })

    result = ok_envelope({
        "filter_gu": gu,
        "centers":   centers,
        "total":     len(centers),
        "note":      "도움이 필요할 때 언제든지 방문할 수 있는 가까운 지원 공간입니다.",
    })
    _cache_set(health_cache_key, result)
    return result


def get_public_reservations(
    settings: Settings,
    service_type: str | None = None,
    gu: str | None = None,
) -> dict:
    """
    서울시 공공서비스 예약 종합 정보 조회.
    service_type: 서비스 유형 (예: "체육시설", "문화시설")
    서비스: OA-20497
    """
    api_key = settings.seoul_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "서울시 공공서비스 예약 API 키가 설정되지 않았습니다.")

    resv_cache_key = f"public_resv|{gu}|{service_type}"
    cached = _cache_get(resv_cache_key)
    if cached is not None:
        return cached

    url = _seoul_url(api_key, "tvYeyakCOllect")
    try:
        resp = httpx.get(url, timeout=settings.seoul_api_timeout)
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "공공서비스 예약 API 응답 시간이 초과되었습니다.")
    except Exception as e:
        logger.warning("public reservation API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "공공서비스 예약 조회 중 오류가 발생했습니다.")

    rows = _parse_seoul_response(data, "tvYeyakCOllect")

    if gu:
        rows = [r for r in rows if gu in (r.get("AREANM", "") or r.get("ADDR", ""))]
    if service_type:
        rows = [r for r in rows if service_type in (r.get("MINCLASSNM", "") or r.get("MAXCLASSNM", ""))]

    reservations = []
    for r in rows:
        reservations.append({
            "service_name":   r.get("SVCNM"),
            "service_type":   r.get("MINCLASSNM") or r.get("MAXCLASSNM"),
            "institution":    r.get("PLACENM"),
            "address":        r.get("ADDR"),
            "area":           r.get("AREANM"),
            "reservation_url": r.get("SVCURL"),
            "start_date":     r.get("SVCOPNBGNDT"),
            "end_date":       r.get("SVCOPNENDDT"),
            "pay_type":       r.get("PAYATNM"),
            "detail_url":     r.get("DTLCONT"),
        })

    result = ok_envelope({
        "filter_gu":    gu,
        "service_type": service_type,
        "items":        reservations,
        "total":        len(reservations),
        "cta":          "지금 바로 예약하고 공간을 활용해 보세요.",
    })
    _cache_set(resv_cache_key, result)
    return result
