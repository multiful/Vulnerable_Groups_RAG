# File: exam_schedule_service.py
# Last Updated: 2026-05-19
# Content Hash: SHA256:TBD
# Role: 한국산업인력공단 시험일정 API 조회
#
# API: 국가자격 시험일정 (apis.data.go.kr/B490007)
#   GET https://apis.data.go.kr/B490007/qualExamSchd/getQualExamSchdList
#   serviceKey: URL-encoded key (hrdkorea_api_key_in)
#   필수 파라미터: implYy (연도), dataFormat=json
#   jmCd 미제공 시 전체 일정 반환 → grade_name(기능사/기사/산업기사 등)으로 클라이언트 필터링
#
# 구 엔드포인트(openapi.q-net.or.kr)는 2025년 폐지, 신규 apis.data.go.kr로 이전됨
from __future__ import annotations

import csv
import logging
import time
import urllib.parse
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parents[3]
_CERT_MASTER_CSV = _PROJECT_ROOT / "data/processed/master/cert_master.csv"

_EXAM_SCHD_BASE = "https://apis.data.go.kr/B490007/qualExamSchd/getQualExamSchdList"

_TTL = 600  # 시험 일정은 자주 안 바뀜 — 10분 캐시
_sched_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    entry = _sched_cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _sched_cache[key] = (time.monotonic(), value)


def _build_qnet_url(base: str, api_key_in: str, extra: dict[str, str]) -> str:
    """
    hrdkorea_api_key_in(이미 URL-인코딩된 키)를 URL에 직접 삽입하고
    나머지 파라미터는 별도 인코딩. httpx params dict로 넘기면 이중 인코딩 발생.
    """
    qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in extra.items())
    return f"{base}?serviceKey={api_key_in}&{qs}"


def _qnet_links(cert_name: str) -> dict[str, str]:
    encoded = urllib.parse.quote(cert_name)
    return {
        "qnet_search_url": f"https://www.q-net.or.kr/crf005.do?id=crf00501&gSite=Q&jmNm={encoded}",
        "qnet_schedule_url": "https://www.q-net.or.kr/crf021.do?id=crf02101&scheType=03",
        "qnet_apply_url": "https://www.q-net.or.kr/man001.do?gSite=Q",
    }


@lru_cache(maxsize=1)
def _load_cert_name_map() -> dict[str, str]:
    if not _CERT_MASTER_CSV.exists():
        return {}
    out: dict[str, str] = {}
    with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["cert_id"]] = r["cert_name"]
    return out


@lru_cache(maxsize=1)
def _load_cert_info_map() -> dict[str, dict[str, Any]]:
    """cert_id → {grade_tier, avg_pass_rate_3yr, primary_domain, exam_frequency, issuer}"""
    if not _CERT_MASTER_CSV.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                avg_pass = float(r.get("avg_pass_rate_3yr") or 0) or None
            except ValueError:
                avg_pass = None
            out[r["cert_id"]] = {
                "cert_grade_tier": r.get("cert_grade_tier", ""),
                "avg_pass_rate_3yr": avg_pass,
                "primary_domain": r.get("primary_domain", ""),
                "exam_frequency": r.get("exam_frequency", ""),
                "issuer": r.get("issuer", ""),
                "grade_name": r.get("grade_name", ""),
            }
    return out


def _calc_dday(target_str: str | None) -> int | None:
    """YYYYMMDD 또는 YYYY-MM-DD 형식 날짜 → D-Day 정수 (오늘 기준 남은 일수)."""
    if not target_str:
        return None
    clean = target_str.replace("-", "")
    try:
        target = datetime.strptime(clean, "%Y%m%d").date()
        delta = (target - date.today()).days
        return delta
    except ValueError:
        return None


def _format_schedule_item(item: dict[str, Any]) -> dict[str, Any]:
    """API 응답 item → 프론트 표시용 정제 dict."""
    reg_start = item.get("docRegStartDt") or item.get("recRegStartDt")
    reg_end   = item.get("docRegEndDt")   or item.get("recRegEndDt")
    exam_start = item.get("docExamStartDt") or item.get("pracExamStartDt")
    exam_end   = item.get("docExamEndDt")   or item.get("pracExamEndDt")
    pass_dt    = item.get("docPassDt")      or item.get("pracPassDt") or item.get("passAnnounDt")

    return {
        "impl_year":          item.get("implYy"),
        "impl_seq":           item.get("implSeq"),
        "impl_seq_name":      item.get("implSeqNm"),
        "registration_start": reg_start,
        "registration_end":   reg_end,
        "exam_start":         exam_start,
        "exam_end":           exam_end,
        "pass_announce_date": pass_dt,
        "d_day_exam":         _calc_dday(exam_start),
        "d_day_registration": _calc_dday(reg_start),
    }


def get_exam_schedule(cert_id: str, settings: Settings) -> dict:
    """
    cert_id → cert_name 변환 후 Q-Net 시험일정 API 조회.
    API 실패 시에도 ok_envelope로 cert 정보 + Q-Net 링크를 함께 반환 (api_status 필드로 구분).
    """
    cert_names = _load_cert_name_map()
    cert_name = cert_names.get(cert_id)
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")

    cert_info = _load_cert_info_map().get(cert_id, {})
    links = _qnet_links(cert_name)
    current_year = str(date.today().year)

    def _fallback(api_status: str) -> dict:
        return ok_envelope({
            "cert_id":   cert_id,
            "cert_name": cert_name,
            "year":      current_year,
            "schedules": [],
            "total":     0,
            "api_status": api_status,
            **cert_info,
            **links,
        })

    api_key = settings.hrdkorea_api_key_in
    if not api_key:
        return _fallback("key_missing")

    grade_name = cert_info.get("grade_name", "")  # 기능사 / 산업기사 / 기사 / 기능장 / 기술사

    sched_cache_key = f"exam_sched|{cert_id}|{current_year}"
    cached = _cache_get(sched_cache_key)
    if cached is not None:
        return cached

    # serviceKey는 이미 URL-인코딩된 값(_IN) → URL에 직접 삽입 (이중인코딩 방지)
    url = _build_qnet_url(_EXAM_SCHD_BASE, api_key, {
        "dataFormat": "json",
        "numOfRows":  "50",
        "pageNo":     "1",
        "implYy":     current_year,
    })

    try:
        resp = httpx.get(url, timeout=settings.hrdkorea_api_timeout)
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        logger.warning("exam_schedule API timeout: cert_id=%s", cert_id)
        return _fallback("unavailable")
    except httpx.HTTPStatusError as e:
        logger.warning("exam_schedule API HTTP error: %s cert_id=%s", e.response.status_code, cert_id)
        return _fallback("unavailable")
    except Exception as e:
        logger.warning("exam_schedule API error: %s cert_id=%s", e, cert_id)
        return _fallback("unavailable")

    try:
        # 신규 apis.data.go.kr 응답 구조: {"header":{...},"body":{"items":[...]}}
        header = data.get("header", {})
        if header.get("resultCode") not in ("00", None, ""):
            logger.warning("exam_schedule API result error: %s", header.get("resultMsg"))
            return _fallback("unavailable")
        item_list = data.get("body", {}).get("items", []) or []
        if not isinstance(item_list, list):
            item_list = []
        # grade_name이 있으면 description 필터 (기능사/기사/산업기사 등)
        if grade_name:
            item_list = [it for it in item_list if grade_name in it.get("description", "")]
    except Exception:
        item_list = []

    schedules = [_format_schedule_item(it) for it in item_list]
    schedules.sort(key=lambda s: s.get("d_day_exam") or 9999)

    result = ok_envelope({
        "cert_id":    cert_id,
        "cert_name":  cert_name,
        "year":       current_year,
        "schedules":  schedules,
        "total":      len(schedules),
        "api_status": "ok",
        **cert_info,
        **links,
    })
    _cache_set(sched_cache_key, result)
    return result


def get_application_schedule(cert_id: str, settings: Settings) -> dict:
    """접수 일정 — 시험일정 API에서 registration 필드만 강조하여 반환."""
    result = get_exam_schedule(cert_id, settings)
    if not result.get("success"):
        return result

    schedules = result["data"].get("schedules", [])
    # 접수 기간이 아직 열려 있는 항목만
    today = date.today()
    open_registrations = []
    for s in schedules:
        reg_end = s.get("registration_end")
        if reg_end:
            clean = reg_end.replace("-", "")
            try:
                end_dt = datetime.strptime(clean, "%Y%m%d").date()
                if end_dt >= today:
                    open_registrations.append(s)
            except ValueError:
                open_registrations.append(s)

    result["data"]["open_registrations"] = open_registrations
    result["data"]["open_count"] = len(open_registrations)
    return result


def get_professional_exam_schedule(
    cert_name: str,
    settings: Settings,
) -> dict:
    """
    국가전문자격 시험 시행일정 조회 (항목 14).
    국가기술자격(ExamScheduleService)과 다른 ProfExamScheduleService 사용.
    의사·변호사·건축사 등 국가전문자격 시험일정 조회.
    """
    api_key = settings.hrdkorea_api_key_in
    if not api_key:
        return err_envelope(
            "API_KEY_MISSING",
            "한국산업인력공단 API 키가 설정되지 않았습니다.",
        )
    if not cert_name or not cert_name.strip():
        return err_envelope("PARAM_MISSING", "cert_name이 필요합니다.")

    current_year = str(date.today().year)

    prof_cache_key = f"prof_sched|{cert_name.strip()}|{current_year}"
    cached = _cache_get(prof_cache_key)
    if cached is not None:
        return cached

    url = _build_qnet_url(_EXAM_SCHD_BASE, api_key, {
        "dataFormat": "json",
        "numOfRows":  "50",
        "pageNo":     "1",
        "implYy":     current_year,
    })

    try:
        resp = httpx.get(url, timeout=settings.hrdkorea_api_timeout)
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "시험일정 API 응답 시간이 초과되었습니다.")
    except httpx.HTTPStatusError as e:
        return err_envelope("EXTERNAL_API_ERROR", f"시험일정 API 오류: HTTP {e.response.status_code}")
    except Exception as e:
        logger.warning("prof_exam_schedule API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "시험일정 조회 중 오류가 발생했습니다.")

    try:
        item_list = data.get("body", {}).get("items", []) or []
        if not isinstance(item_list, list):
            item_list = []
        # cert_name 키워드로 description 필터
        kw = cert_name.strip()
        filtered = [it for it in item_list if kw in it.get("description", "")]
        item_list = filtered if filtered else item_list
    except Exception:
        item_list = []

    schedules = [_format_schedule_item(it) for it in item_list]
    schedules.sort(key=lambda s: s.get("d_day_exam") or 9999)

    result = ok_envelope({
        "cert_name": cert_name,
        "year":      current_year,
        "schedules": schedules,
        "total":     len(schedules),
        "note":      "국가자격 시험일정 (apis.data.go.kr/B490007)",
    })
    _cache_set(prof_cache_key, result)
    return result
