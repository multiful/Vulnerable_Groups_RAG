# File: map_service.py
# Last Updated: 2026-05-19
# Content Hash: SHA256:TBD
# Role: 지도 인프라 점 집계 — 일자리카페, 건강증진센터, 훈련기관 좌표 반환
#
# 데이터 체인:
#   일자리카페     → Seoul Open API → 실패 시 Kakao 키워드 검색 fallback
#   건강증진센터   → Seoul Open API → 실패 시 Kakao 키워드 검색 fallback
#   훈련기관       → Work24 → 주소 → Kakao REST 지오코딩
#
# Kakao REST APIs:
#   지오코딩:      GET https://dapi.kakao.com/v2/local/search/address.json
#   키워드 검색:   GET https://dapi.kakao.com/v2/local/search/keyword.json
#   카테고리 검색: GET https://dapi.kakao.com/v2/local/search/category.json
#   Authorization: KakaoAK {KAKAO_REST_API_KEY}
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import ok_envelope

logger = logging.getLogger(__name__)

_KAKAO_GEOCODE_URL  = "https://dapi.kakao.com/v2/local/search/address.json"
_KAKAO_KEYWORD_URL  = "https://dapi.kakao.com/v2/local/search/keyword.json"
_KAKAO_CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"

# 서울 직사각형 범위 (Kakao rect 파라미터용)
_SEOUL_RECT = "126.7516,37.4133,127.1837,37.7015"

_TTL = 600
_local_search_cache: dict[str, tuple[float, Any]] = {}

# 세션 내 지오코딩 캐시 (주소 → (lat, lng))
_geocode_cache: dict[str, tuple[float, float] | None] = {}


def _local_cache_get(key: str) -> Any | None:
    entry = _local_search_cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _local_cache_set(key: str, value: Any) -> None:
    _local_search_cache[key] = (time.monotonic(), value)


def _kakao_keyword_search(
    query: str,
    rest_key: str,
    *,
    rect: str | None = _SEOUL_RECT,
    size: int = 15,
    page: int = 1,
) -> list[dict[str, Any]]:
    """
    Kakao 키워드 로컬 검색.
    rect: "x1,y1,x2,y2" 직사각형 범위 (경도,위도 순).
    결과: place_name, address, lat, lng, phone, place_url.
    """
    if not query or not rest_key:
        return []
    params: dict[str, Any] = {
        "query": query,
        "size":  min(size, 15),
        "page":  page,
    }
    if rect:
        params["rect"] = rect
    try:
        r = httpx.get(
            _KAKAO_KEYWORD_URL,
            params=params,
            headers={"Authorization": f"KakaoAK {rest_key}"},
            timeout=8,
        )
        docs = r.json().get("documents", [])
        return docs
    except Exception as e:
        logger.debug("kakao_keyword_search failed for '%s': %s", query, e)
        return []


def _kakao_category_search(
    category_group_code: str,
    rest_key: str,
    *,
    rect: str | None = _SEOUL_RECT,
    size: int = 15,
    page: int = 1,
) -> list[dict[str, Any]]:
    """
    Kakao 카테고리 로컬 검색.
    category_group_code 예시: PO3=공공기관, SW8=지하철역, HP8=병원, PM9=약국
    """
    if not category_group_code or not rest_key:
        return []
    params: dict[str, Any] = {
        "category_group_code": category_group_code,
        "size": min(size, 15),
        "page": page,
    }
    if rect:
        params["rect"] = rect
    try:
        r = httpx.get(
            _KAKAO_CATEGORY_URL,
            params=params,
            headers={"Authorization": f"KakaoAK {rest_key}"},
            timeout=8,
        )
        docs = r.json().get("documents", [])
        return docs
    except Exception as e:
        logger.debug("kakao_category_search failed: %s", e)
        return []


def _kakao_doc_to_point(doc: dict, point_type: str) -> dict[str, Any]:
    """Kakao document → 인프라 point dict."""
    return {
        "type":    point_type,
        "name":    doc.get("place_name", ""),
        "address": doc.get("road_address_name") or doc.get("address_name", ""),
        "phone":   doc.get("phone", ""),
        "lat":     float(doc["y"]) if doc.get("y") else None,
        "lng":     float(doc["x"]) if doc.get("x") else None,
        "place_url": doc.get("place_url", ""),
    }


def get_kakao_local_search(
    query: str,
    settings: Settings,
    rect: str | None = None,
    size: int = 15,
    page: int = 1,
) -> dict:
    """
    Kakao 키워드 로컬 검색 엔드포인트용.
    query: 검색어 (예: "일자리카페", "고용복지플러스센터", "정신건강증진센터")
    rect: "x1,y1,x2,y2" 형식 직사각형 범위 (기본값: 서울 전체)
    """
    from backend.app.schemas.envelope import err_envelope
    rest_key = settings.kakao_rest_api_key
    if not rest_key:
        return err_envelope("API_KEY_MISSING", "Kakao REST API 키가 설정되지 않았습니다.")
    if not query or not query.strip():
        return err_envelope("PARAM_MISSING", "query 파라미터가 필요합니다.")

    cache_key = f"kakao_local|{query}|{rect}|{size}|{page}"
    cached = _local_cache_get(cache_key)
    if cached is not None:
        return cached

    docs = _kakao_keyword_search(
        query.strip(),
        rest_key,
        rect=rect or _SEOUL_RECT,
        size=size,
        page=page,
    )
    places = [_kakao_doc_to_point(d, "kakao_local") for d in docs]

    from backend.app.schemas.envelope import ok_envelope as _ok
    result = _ok({
        "query":  query,
        "places": places,
        "total":  len(places),
        "source": "kakao_local_search",
    })
    _local_cache_set(cache_key, result)
    return result


def _geocode(address: str, rest_key: str) -> tuple[float, float] | None:
    """Kakao REST API로 한국 주소 → (위도, 경도) 변환. 실패 시 None."""
    if not address or not rest_key:
        return None
    if address in _geocode_cache:
        return _geocode_cache[address]
    try:
        r = httpx.get(
            _KAKAO_GEOCODE_URL,
            params={"query": address, "size": 1, "analyze_type": "similar"},
            headers={"Authorization": f"KakaoAK {rest_key}"},
            timeout=5,
        )
        docs = r.json().get("documents", [])
        if docs:
            result: tuple[float, float] = (float(docs[0]["y"]), float(docs[0]["x"]))
            _geocode_cache[address] = result
            return result
    except Exception as e:
        logger.debug("geocode failed for '%s': %s", address, e)
    _geocode_cache[address] = None
    return None


def _to_float(v: Any) -> float | None:
    try:
        return float(v) if v else None
    except (TypeError, ValueError):
        return None


def get_infra_points(
    settings: Settings,
    gu: str | None = None,
    cert_id: str | None = None,
) -> dict:
    """
    지도 표시용 인프라 점(Point) 집계.
    cert_id가 있으면 해당 자격증 관련 훈련기관도 포함.
    gu로 서울시 구 단위 필터 가능.
    """
    from backend.app.services.seoul_service import get_job_cafes, get_health_centers

    rest_key = settings.kakao_rest_api_key

    # ── 1. 일자리카페 ──────────────────────────────────────────────────
    job_cafes: list[dict] = []
    cafe_result = get_job_cafes(settings, gu=gu)
    if cafe_result.get("success") and cafe_result.get("data"):
        for c in cafe_result["data"].get("cafes", []):
            lat = _to_float(c.get("lat"))
            lng = _to_float(c.get("lng"))
            if (lat is None or lng is None) and rest_key and c.get("address"):
                coords = _geocode(c["address"], rest_key)
                if coords:
                    lat, lng = coords
            if lat and lng:
                job_cafes.append({
                    "type":    "job_cafe",
                    "name":    c.get("name") or "일자리카페",
                    "address": c.get("address") or "",
                    "phone":   c.get("phone"),
                    "lat":     lat,
                    "lng":     lng,
                    "source":  "seoul_api",
                })
    # Seoul API 실패 시 Kakao 키워드 검색 fallback
    if not job_cafes and rest_key:
        kw = f"일자리카페 {gu}" if gu else "일자리카페"
        docs = _kakao_keyword_search(kw, rest_key, size=15)
        for doc in docs:
            lat = _to_float(doc.get("y"))
            lng = _to_float(doc.get("x"))
            if lat and lng:
                job_cafes.append({
                    "type":      "job_cafe",
                    "name":      doc.get("place_name", "일자리카페"),
                    "address":   doc.get("road_address_name") or doc.get("address_name", ""),
                    "phone":     doc.get("phone", ""),
                    "lat":       lat,
                    "lng":       lng,
                    "place_url": doc.get("place_url", ""),
                    "source":    "kakao_fallback",
                })

    # ── 2. 건강증진센터 ────────────────────────────────────────────────
    health_centers: list[dict] = []
    health_result = get_health_centers(settings, gu=gu)
    if health_result.get("success") and health_result.get("data"):
        for c in health_result["data"].get("centers", []):
            lat = _to_float(c.get("lat"))
            lng = _to_float(c.get("lng"))
            if (lat is None or lng is None) and rest_key and c.get("address"):
                coords = _geocode(c["address"], rest_key)
                if coords:
                    lat, lng = coords
            if lat and lng:
                health_centers.append({
                    "type":    "health_center",
                    "name":    c.get("name") or "건강증진센터",
                    "address": c.get("address") or "",
                    "phone":   c.get("phone"),
                    "lat":     lat,
                    "lng":     lng,
                    "source":  "seoul_api",
                })
    # Seoul API 실패 시 Kakao fallback: 정신건강증진센터 + 건강증진센터
    if not health_centers and rest_key:
        for kw_base in ("정신건강증진센터", "건강증진센터"):
            kw = f"{kw_base} {gu}" if gu else kw_base
            docs = _kakao_keyword_search(kw, rest_key, size=15)
            for doc in docs:
                lat = _to_float(doc.get("y"))
                lng = _to_float(doc.get("x"))
                if lat and lng:
                    health_centers.append({
                        "type":      "health_center",
                        "name":      doc.get("place_name", kw_base),
                        "address":   doc.get("road_address_name") or doc.get("address_name", ""),
                        "phone":     doc.get("phone", ""),
                        "lat":       lat,
                        "lng":       lng,
                        "place_url": doc.get("place_url", ""),
                        "source":    "kakao_fallback",
                    })
            if health_centers:
                break

    # ── 3. 훈련기관 (cert_id 기반, geocode) ──────────────────────────
    training_institutes: list[dict] = []
    if cert_id:
        from backend.app.services.training_service import get_training_by_cert_id
        train_result = get_training_by_cert_id(cert_id, settings, region="서울", page_size=15)
        if train_result.get("success") and train_result.get("data"):
            seen: set[str] = set()
            for course in train_result["data"].get("courses", []):
                addr = course.get("institution_addr") or ""
                name = course.get("institution_name") or "훈련기관"
                if not addr or addr in seen:
                    continue
                seen.add(addr)
                coords: tuple[float, float] | None = None
                if settings.kakao_rest_api_key:
                    coords = _geocode(addr, settings.kakao_rest_api_key)
                if coords:
                    training_institutes.append({
                        "type":        "training_institute",
                        "name":        name,
                        "address":     addr,
                        "phone":       course.get("tel"),
                        "course_name": course.get("course_name"),
                        "lat":         coords[0],
                        "lng":         coords[1],
                    })

    all_points = job_cafes + health_centers + training_institutes

    return ok_envelope({
        "job_cafes":          job_cafes,
        "health_centers":     health_centers,
        "training_institutes": training_institutes,
        "all_points":         all_points,
        "total":              len(all_points),
        "filter_gu":          gu,
        "cert_id":            cert_id,
    })
