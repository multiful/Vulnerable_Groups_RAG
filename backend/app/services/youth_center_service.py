# File: youth_center_service.py
# Last Updated: 2026-06-26
# Content Hash: SHA256:TBD
# Role: 온통청년 OPEN API — 청년정책(F-26)·청년공간(F-27)·청년콘텐츠(F-28) 조회
#
# API: 온통청년 포털 (youthcenter.go.kr)
#   청년정책 목록: GET https://www.youthcenter.go.kr/go/ythip/getPlcy
#   청년공간 목록: GET https://www.youthcenter.go.kr/go/ythip/getSpace
#   청년콘텐츠 목록: GET https://www.youthcenter.go.kr/go/ythip/getContent
#   인증키: YOUTH_CENTER_API_KEY
#   응답 형식: JSON
#
# 정책대분류(lclsfNm) 허용값 — API코드정보.xlsx 정책대분류 시트 기준
#   일자리 / 주거 / 교육 / 복지문화 / 참여권리
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_POLICY_URL  = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
_SPACE_URL   = "https://www.youthcenter.go.kr/go/ythip/getSpace"
_CONTENT_URL = "https://www.youthcenter.go.kr/go/ythip/getContent"

# 정책대분류 허용값 (API코드정보.xlsx 정책대분류 시트)
ALLOWED_CATEGORIES: list[str] = ["일자리", "주거", "교육", "복지문화", "참여권리"]

_TTL = 600  # 10분 캐시
_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic(), value)


def _norm_category(raw: str | None) -> str:
    """정책대분류 값을 허용값으로 정규화. 허용값 밖이면 '기타'."""
    if not raw:
        return "기타"
    stripped = str(raw).strip()
    for allowed in ALLOWED_CATEGORIES:
        if allowed in stripped:
            return allowed
    return "기타"


# ── 청년정책 (getPlcy) ────────────────────────────────────────────────────────

def _parse_policy_items(items_raw: list[dict]) -> list[dict]:
    result = []
    for item in items_raw:
        result.append({
            "id":          item.get("plcyNo") or item.get("plcyId", ""),
            "name":        item.get("plcyNm", ""),
            "category":    _norm_category(item.get("lclsfNm")),
            "sub_category": item.get("mclsfNm", ""),
            "region":      item.get("areaNm") or item.get("plcyApplyRgnNm", ""),
            "period":      f"{item.get('plcyBizPrdBegin', '')} ~ {item.get('plcyBizPrdEnd', '')}",
            "apply_url":   item.get("plcyUrlAddr", "") or item.get("aplyUrl", ""),
            "summary":     item.get("plcyExplnCn", "") or item.get("plcyAbstCn", ""),
            "source":      "온통청년_청년정책",
        })
    return result


def get_youth_policy(
    settings: Settings,
    lclsf_nm: str | None = None,
    mclsf_nm: str | None = None,
    region: str | None = None,
    keyword: str | None = None,
    page_size: int = 5,
) -> dict:
    """
    온통청년 청년정책 조회 (F-26).

    Args:
        lclsf_nm: 정책대분류 (일자리|주거|교육|복지문화|참여권리)
        mclsf_nm: 정책중분류 (취업|재직자|창업|미래역량강화 등)
        region: 지역명 (예: 서울, 경기)
        keyword: 검색 키워드
        page_size: 결과 수 (기본 5)
    """
    if not settings.youth_center_api_key:
        return err_envelope("API_KEY_MISSING", "YOUTH_CENTER_API_KEY 환경변수가 설정되지 않았습니다.")

    # 허용값 검증
    if lclsf_nm and lclsf_nm not in ALLOWED_CATEGORIES:
        return err_envelope(
            "INVALID_CATEGORY",
            f"lclsf_nm 허용값: {', '.join(ALLOWED_CATEGORIES)}",
        )

    cache_key = f"youth_policy:{lclsf_nm}:{mclsf_nm}:{region}:{keyword}:{page_size}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params: dict[str, Any] = {
        "apiKey":    settings.youth_center_api_key,
        "pageIndex": 1,
        "pageSize":  page_size,
    }
    if lclsf_nm:
        params["lclsfNm"] = lclsf_nm
    if mclsf_nm:
        params["mclsfNm"] = mclsf_nm
    if region:
        params["areaNm"] = region
    if keyword:
        params["srchPolicyName"] = keyword

    try:
        with httpx.Client(timeout=settings.youth_center_api_timeout) as client:
            resp = client.get(_POLICY_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        msg = (
            "온통청년 API IP 미등록 또는 키 오류. "
            "youthcenter.go.kr 개발자 콘솔에서 서버 IP를 화이트리스트에 등록하세요."
            if e.response.status_code == 400 else
            f"온통청년 API 오류: {e.response.status_code}"
        )
        logger.warning("온통청년 정책 API HTTP 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", msg)
    except Exception as e:
        logger.warning("온통청년 정책 API 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", str(e))

    try:
        body = data if isinstance(data, dict) else {}
        items_raw = (
            body.get("result", {}).get("plcyList", [])
            or body.get("plcyList", [])
            or body.get("data", [])
            or []
        )
        if isinstance(items_raw, dict):
            items_raw = [items_raw]
        items = _parse_policy_items(items_raw)
    except Exception as e:
        logger.warning("온통청년 정책 파싱 오류: %s | raw=%s", e, str(data)[:300])
        return err_envelope("PARSE_ERROR", "온통청년 정책 API 응답 파싱 오류")

    result = ok_envelope({
        "category":     lclsf_nm,
        "sub_category": mclsf_nm,
        "region":       region,
        "keyword":      keyword,
        "count":        len(items),
        "items":        items,
        "source":       "온통청년_청년정책",
    })
    _cache_set(cache_key, result)
    return result


# ── 청년공간 (getSpace) ───────────────────────────────────────────────────────

def _parse_space_items(items_raw: list[dict]) -> list[dict]:
    result = []
    for item in items_raw:
        result.append({
            "id":           item.get("spaceId") or item.get("instId", ""),
            "name":         item.get("spaceNm") or item.get("instNm", ""),
            "address":      item.get("addrInfo") or item.get("instAddr", ""),
            "tel":          item.get("telNo") or item.get("phon", ""),
            "hours":        item.get("operTime") or item.get("operHour", ""),
            "homepage":     item.get("homepageUrl") or item.get("hmpgUrl", ""),
            "region":       item.get("areaNm") or item.get("ctpvNm", ""),
            "source":       "온통청년_청년공간",
        })
    return result


def get_youth_space(
    settings: Settings,
    region: str | None = None,
    page_size: int = 5,
) -> dict:
    """
    온통청년 청년공간(센터) 조회 (F-27).

    Args:
        region: 지역명 (예: 서울, 경기)
        page_size: 결과 수 (기본 5)
    """
    if not settings.youth_center_api_key:
        return err_envelope("API_KEY_MISSING", "YOUTH_CENTER_API_KEY 환경변수가 설정되지 않았습니다.")

    cache_key = f"youth_space:{region}:{page_size}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params: dict[str, Any] = {
        "apiKey":    settings.youth_center_api_key,
        "pageIndex": 1,
        "pageSize":  page_size,
    }
    if region:
        params["areaNm"] = region

    try:
        with httpx.Client(timeout=settings.youth_center_api_timeout) as client:
            resp = client.get(_SPACE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        msg = (
            "온통청년 API IP 미등록 또는 키 오류. youthcenter.go.kr 개발자 콘솔에서 서버 IP를 등록하세요."
            if e.response.status_code == 400 else
            f"온통청년 API 오류: {e.response.status_code}"
        )
        logger.warning("온통청년 공간 API HTTP 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", msg)
    except Exception as e:
        logger.warning("온통청년 공간 API 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", str(e))

    try:
        body = data if isinstance(data, dict) else {}
        items_raw = (
            body.get("result", {}).get("spaceList", [])
            or body.get("spaceList", [])
            or body.get("data", [])
            or []
        )
        if isinstance(items_raw, dict):
            items_raw = [items_raw]
        items = _parse_space_items(items_raw)
    except Exception as e:
        logger.warning("온통청년 공간 파싱 오류: %s | raw=%s", e, str(data)[:300])
        return err_envelope("PARSE_ERROR", "온통청년 공간 API 응답 파싱 오류")

    result = ok_envelope({
        "region": region,
        "count":  len(items),
        "items":  items,
        "source": "온통청년_청년공간",
    })
    _cache_set(cache_key, result)
    return result


# ── 청년콘텐츠 (getContent) ──────────────────────────────────────────────────

def _parse_content_items(items_raw: list[dict]) -> list[dict]:
    result = []
    for item in items_raw:
        result.append({
            "id":           item.get("cntnsId") or item.get("contentsId", ""),
            "title":        item.get("cntnsSj") or item.get("contentsSj", ""),
            "category":     _norm_category(item.get("lclsfNm") or item.get("cntnsCtgr")),
            "content_url":  item.get("cntnsUrl") or item.get("contentsUrl", ""),
            "thumbnail_url": item.get("thmbnlFileUrl") or item.get("thumbnailUrl", ""),
            "registered_at": item.get("registDt") or item.get("regDt", ""),
            "source":       "온통청년_청년콘텐츠",
        })
    return result


def get_youth_content(
    settings: Settings,
    category: str | None = None,
    keyword: str | None = None,
    page_size: int = 5,
) -> dict:
    """
    온통청년 청년콘텐츠 조회 (F-28). 대분류별로 그룹핑하여 반환.

    Args:
        category: 정책대분류 (일자리|주거|교육|복지문화|참여권리|전체)
        keyword: 검색 키워드
        page_size: 결과 수 (기본 5)
    """
    if not settings.youth_center_api_key:
        return err_envelope("API_KEY_MISSING", "YOUTH_CENTER_API_KEY 환경변수가 설정되지 않았습니다.")

    # "전체" 또는 None → 필터 없이 전체 조회
    lclsf_filter: str | None = None
    if category and category not in ("전체", "all"):
        if category not in ALLOWED_CATEGORIES:
            return err_envelope(
                "INVALID_CATEGORY",
                f"category 허용값: {', '.join(ALLOWED_CATEGORIES)} 또는 전체",
            )
        lclsf_filter = category

    cache_key = f"youth_content:{lclsf_filter}:{keyword}:{page_size}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params: dict[str, Any] = {
        "apiKey":    settings.youth_center_api_key,
        "pageIndex": 1,
        "pageSize":  page_size,
    }
    if lclsf_filter:
        params["lclsfNm"] = lclsf_filter
    if keyword:
        params["srchContents"] = keyword

    try:
        with httpx.Client(timeout=settings.youth_center_api_timeout) as client:
            resp = client.get(_CONTENT_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        msg = (
            "온통청년 API IP 미등록 또는 키 오류. youthcenter.go.kr 개발자 콘솔에서 서버 IP를 등록하세요."
            if e.response.status_code == 400 else
            f"온통청년 API 오류: {e.response.status_code}"
        )
        logger.warning("온통청년 콘텐츠 API HTTP 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", msg)
    except Exception as e:
        logger.warning("온통청년 콘텐츠 API 오류: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", str(e))

    try:
        body = data if isinstance(data, dict) else {}
        items_raw = (
            body.get("result", {}).get("cntsList", [])
            or body.get("cntsList", [])
            or body.get("contentsList", [])
            or body.get("data", [])
            or []
        )
        if isinstance(items_raw, dict):
            items_raw = [items_raw]
        items = _parse_content_items(items_raw)
    except Exception as e:
        logger.warning("온통청년 콘텐츠 파싱 오류: %s | raw=%s", e, str(data)[:300])
        return err_envelope("PARSE_ERROR", "온통청년 콘텐츠 API 응답 파싱 오류")

    # 카테고리별 그룹핑
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        grouped[item["category"]].append(item)

    result = ok_envelope({
        "category":            category or "전체",
        "keyword":             keyword,
        "count":               len(items),
        "items":               items,
        "categories":          sorted(grouped.keys()),
        "grouped_by_category": dict(grouped),
        "source":              "온통청년_청년콘텐츠",
    })
    _cache_set(cache_key, result)
    return result
