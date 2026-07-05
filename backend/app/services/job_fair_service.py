# File: job_fair_service.py
# Last Updated: 2026-07-05
# Content Hash: SHA256:TBD
# Role: Work24 채용행사 목록 조회 (개인 계정 사용 가능 — 공공기관 주최 행사)
#
# API: Work24 채용행사 목록
#   https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo100L01.do
#   authKey: GET_JOB_API_KEY
#   returnType: XML
#   채용행사 = 고용센터·지자체가 주최하는 공개 채용행사 (기업 전용 채용공고와 다름)
from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_JOB_FAIR_BASE = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo100L01.do"

_TTL = 600  # 채용행사는 10분 캐시
_cache: dict[str, tuple[float, Any]] = {}

REGION_CODES: dict[str, str] = {
    "서울": "11", "부산": "26", "대구": "27", "인천": "28",
    "광주": "29", "대전": "30", "울산": "31", "세종": "36",
    "경기": "41", "강원": "51", "충북": "43", "충남": "44",
    "전북": "45", "전남": "46", "경북": "47", "경남": "48", "제주": "50",
}


def _cache_get(key: str) -> Any | None:
    e = _cache.get(key)
    return e[1] if e and (time.monotonic() - e[0]) < _TTL else None


def _cache_set(key: str, val: Any) -> None:
    _cache[key] = (time.monotonic(), val)


def _parse_xml(xml_text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    error_el = root.find("error")
    if error_el is not None and error_el.text:
        raise ValueError(error_el.text.strip())

    items: list[dict[str, Any]] = []
    # 채용행사 응답 태그: <JfInfo> 안에 각 행사 항목
    for item in root.iter("JfInfo"):
        row: dict[str, Any] = {}
        for child in item:
            row[child.tag] = (child.text or "").strip()
        if row:
            items.append(row)
    # 태그 이름이 다를 경우 fallback
    if not items:
        for item in root.iter("item"):
            row = {}
            for child in item:
                row[child.tag] = (child.text or "").strip()
            if row:
                items.append(row)
    return items


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id":    raw.get("jfInfoNo") or raw.get("wantedAuthNo"),
        "event_name":  raw.get("jfInfoNm") or raw.get("eventNm") or raw.get("title", ""),
        "organizer":   raw.get("instNm") or raw.get("srvcPvdInstNm") or "",
        "region":      raw.get("jfInfoRegion") or raw.get("region") or "",
        "venue":       raw.get("jfInfoPlc") or raw.get("eventPlc") or "",
        "start_date":  raw.get("jfInfoSttDt") or raw.get("eventSttDt") or "",
        "end_date":    raw.get("jfInfoEndDt") or raw.get("eventEndDt") or "",
        "apply_method": raw.get("jfInfoAplyMthdNm") or raw.get("aplyMthdNm") or "",
        "url":         raw.get("jfInfoUrl") or raw.get("eventUrl") or raw.get("wantedInfoUrl") or "",
        "description": raw.get("jfInfoCn") or raw.get("contents") or "",
        "participant_count": raw.get("jfInfoPrtcpCnt") or "",
        "event_type":  raw.get("jfInfoPurNm") or raw.get("jfInfoTypNm") or "",
    }


def get_job_fairs(
    settings: Settings,
    region: str | None = None,
    keyword: str | None = None,
    days_ahead: int = 90,
    page_size: int = 20,
) -> dict:
    """
    Work24 채용행사 목록 조회.
    - 개인 계정으로 접근 가능 (공공기관 주최 행사)
    - 오늘 ~ days_ahead일 이내 예정 행사 반환
    """
    api_key = settings.get_job_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "채용행사 API 키가 설정되지 않았습니다.")

    today = date.today()
    end_date = today + timedelta(days=days_ahead)

    region_code: str | None = None
    if region and region != "전국":
        region_code = REGION_CODES.get(region)

    cache_key = f"fair|{region}|{keyword}|{days_ahead}|{page_size}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params: dict[str, Any] = {
        "authKey":         api_key,
        "returnType":      "XML",
        "pageNum":         "1",
        "pageSize":        str(min(page_size, 100)),
        "srchEventSttDt":  today.strftime("%Y%m%d"),
        "srchEventEndDt":  end_date.strftime("%Y%m%d"),
    }
    if region_code:
        params["srchRegion"] = region_code
    if keyword:
        params["srchEventNm"] = keyword

    try:
        resp = httpx.get(_JOB_FAIR_BASE, params=params, timeout=settings.worknet_api_timeout)
        resp.raise_for_status()
        raw_items = _parse_xml(resp.text)
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "채용행사 API 응답 시간이 초과되었습니다.")
    except httpx.HTTPStatusError as e:
        return err_envelope("EXTERNAL_API_ERROR", f"채용행사 API 오류: HTTP {e.response.status_code}")
    except ValueError as e:
        logger.warning("job_fair API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", f"채용행사 API 오류: {e}")
    except Exception as e:
        logger.warning("job_fair unexpected error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "채용행사 정보 조회 중 오류가 발생했습니다.")

    events = [_normalize(r) for r in raw_items]
    # 날짜 정렬 (시작일 오름차순)
    events.sort(key=lambda x: x.get("start_date") or "")

    result = ok_envelope({
        "query": {
            "region": region,
            "keyword": keyword,
            "period_from": today.isoformat(),
            "period_to": end_date.isoformat(),
        },
        "events": events,
        "total": len(events),
    })
    _cache_set(cache_key, result)
    return result


def get_job_fairs_by_domain(
    settings: Settings,
    domain_name: str,
    region: str | None = None,
    page_size: int = 10,
) -> dict:
    """도메인명을 키워드로 채용행사 조회 — 추천 연결용."""
    # 도메인 → 검색 키워드 간소화
    _DOMAIN_KEYWORDS: dict[str, str] = {
        "데이터/AI": "IT", "소프트웨어개발": "IT", "IT/정보통신": "IT",
        "금융/핀테크": "금융", "건설/토목": "건설", "보건/의료": "의료",
        "사회복지": "복지", "경영/사무": "사무", "전기/전자": "전기",
        "기계/제조": "제조", "환경/에너지": "환경",
    }
    keyword = _DOMAIN_KEYWORDS.get(domain_name, domain_name.split("/")[0])
    resp = get_job_fairs(settings, region=region, keyword=keyword, page_size=page_size)
    if not resp.get("success"):
        fallback = _MANUAL_FALLBACK_EVENTS.get(domain_name)
        if fallback:
            return ok_envelope({
                "query": {"region": region, "keyword": keyword},
                "events": fallback,
                "total": len(fallback),
            })
    return resp


# Work24 채용행사 API(callOpenApiSvcInfo100L01.do)가 "고용24" 개편 이후 HTTP 404 응답 —
# 정식 엔드포인트 확인 전까지 도메인별 확인된 실제 행사를 graceful fallback으로 제공한다.
_MANUAL_FALLBACK_EVENTS: dict[str, list[dict[str, Any]]] = {
    "소프트웨어개발": [
        {
            "event_id": "48798",
            "event_name": "취업준비콘서트 일자리톡톡_한국관광공사 서울",
            "organizer": "한국관광공사",
            "region": "서울",
            "venue": "서울고용복지플러스센터 1층 청년on라운지",
            "start_date": "",
            "end_date": "",
            "apply_method": "",
            "url": "https://m.work24.go.kr/wk/a/f/1100/retrieveEmpEventDtl.do?currentPageNo=1&recordCountPerPage=12&subCurrentPageNo=1&subRecordCountPerPage=12&eventMegaRegionCd=51&newsDataSeqno=48798&writeNo=&startDt=20260705&endDt=20260805&selectAreaList=&searchText=&eventClcd=all%2C01%2C02%2C03%2C04%2C05&searchTermGbn=",
            "description": "기업이념·조직문화·인재상·채용트렌드·직무설명 Q&A. 취업을 준비하는 청년 누구나 참여 가능.",
            "participant_count": "",
            "event_type": "직무설명회",
        },
    ],
}
