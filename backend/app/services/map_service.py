# File: map_service.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 지도 인프라 점 집계 — 일자리카페, 건강증진센터, 훈련기관 좌표 반환
#
# 데이터 체인:
#   일자리카페     → Seoul Open API (seoul_service) → lat/lng 직접 반환
#   건강증진센터   → Seoul Open API (seoul_service) → lat/lng 직접 반환
#   훈련기관       → Work24 (training_service) → 주소 → Kakao REST 지오코딩
#
# Kakao 지오코딩: GET https://dapi.kakao.com/v2/local/search/address.json
#   Authorization: KakaoAK {KAKAO_REST_API_KEY}
from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import ok_envelope

logger = logging.getLogger(__name__)

_KAKAO_GEOCODE_URL = "https://dapi.kakao.com/v2/local/search/address.json"

# 세션 내 지오코딩 캐시 (주소 → (lat, lng))
_geocode_cache: dict[str, tuple[float, float] | None] = {}


def _geocode(address: str, rest_key: str) -> tuple[float, float] | None:
    """Kakao REST API로 한국 주소 → (위도, 경도) 변환. 실패 시 None."""
    if not address or not rest_key:
        return None
    if address in _geocode_cache:
        return _geocode_cache[address]
    try:
        r = httpx.get(
            _KAKAO_GEOCODE_URL,
            params={"query": address, "size": 1},
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

    # ── 1. 일자리카페 ──────────────────────────────────────────────────
    job_cafes: list[dict] = []
    cafe_result = get_job_cafes(settings, gu=gu)
    if cafe_result.get("success") and cafe_result.get("data"):
        for c in cafe_result["data"].get("cafes", []):
            lat = _to_float(c.get("lat"))
            lng = _to_float(c.get("lng"))
            # lat/lng 없으면 주소로 지오코딩 시도
            if (lat is None or lng is None) and settings.kakao_rest_api_key and c.get("address"):
                coords = _geocode(c["address"], settings.kakao_rest_api_key)
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
                })

    # ── 2. 건강증진센터 ────────────────────────────────────────────────
    health_centers: list[dict] = []
    health_result = get_health_centers(settings, gu=gu)
    if health_result.get("success") and health_result.get("data"):
        for c in health_result["data"].get("centers", []):
            lat = _to_float(c.get("lat"))
            lng = _to_float(c.get("lng"))
            if (lat is None or lng is None) and settings.kakao_rest_api_key and c.get("address"):
                coords = _geocode(c["address"], settings.kakao_rest_api_key)
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
                })

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
