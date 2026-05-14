# File: exam_schedule_service.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 한국산업인력공단 Q-Net 시험일정 API 조회 — reserved → 활성화
#
# API: 국가자격 시험일정 조회 (Q-Net)
#   GET https://www.data.go.kr/data/15012808 계열
#   실제 엔드포인트: http://openapi.q-net.or.kr/api/service/rest/ExamScheduleService/getExamScheduleList
#   returnType: json
#   serviceKey: URL-encoded key (hrdkorea_api_key_in)
from __future__ import annotations

import csv
import logging
import time
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

_QNET_BASE      = "http://openapi.q-net.or.kr/api/service/rest/ExamScheduleService/getExamScheduleList"
_QNET_PROF_BASE = "http://openapi.q-net.or.kr/api/service/rest/ProfExamScheduleService/getProfExamScheduleList"

_TTL = 600  # 시험 일정은 자주 안 바뀜 — 10분 캐시
_sched_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    entry = _sched_cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _sched_cache[key] = (time.monotonic(), value)


@lru_cache(maxsize=1)
def _load_cert_name_map() -> dict[str, str]:
    if not _CERT_MASTER_CSV.exists():
        return {}
    out: dict[str, str] = {}
    with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["cert_id"]] = r["cert_name"]
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
    API 키 미설정 시 fallback 응답 반환.
    """
    api_key = settings.hrdkorea_api_key_in
    if not api_key:
        return err_envelope(
            "API_KEY_MISSING",
            "한국산업인력공단 API 키가 설정되지 않았습니다. 관리자에게 문의하세요.",
            {"cert_id": cert_id},
        )

    cert_names = _load_cert_name_map()
    cert_name = cert_names.get(cert_id)
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")

    current_year = str(date.today().year)

    sched_cache_key = f"exam_sched|{cert_id}|{current_year}"
    cached = _cache_get(sched_cache_key)
    if cached is not None:
        return cached

    params: dict[str, str] = {
        "serviceKey": api_key,
        "implYy":     current_year,
        "itemNm":     cert_name,
        "returnType": "json",
        "numOfRows":  "10",
        "pageNo":     "1",
    }

    try:
        resp = httpx.get(
            _QNET_BASE,
            params=params,
            timeout=settings.hrdkorea_api_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "시험일정 API 응답 시간이 초과되었습니다.")
    except httpx.HTTPStatusError as e:
        return err_envelope("EXTERNAL_API_ERROR", f"시험일정 API 오류: HTTP {e.response.status_code}")
    except Exception as e:
        logger.warning("exam_schedule API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "시험일정 조회 중 오류가 발생했습니다.")

    try:
        body = data.get("response", {}).get("body", {})
        items_raw = body.get("items", {})
        # API에 따라 items가 dict(단건) 또는 list일 수 있음
        if isinstance(items_raw, dict):
            item_list = items_raw.get("item", [])
            if isinstance(item_list, dict):
                item_list = [item_list]
        elif isinstance(items_raw, list):
            item_list = items_raw
        else:
            item_list = []
    except Exception:
        item_list = []

    schedules = [_format_schedule_item(it) for it in item_list]
    # 현재 연도 기준 가장 가까운 시험부터 정렬
    schedules.sort(key=lambda s: s.get("d_day_exam") or 9999)

    result = ok_envelope({
        "cert_id":   cert_id,
        "cert_name": cert_name,
        "year":      current_year,
        "schedules": schedules,
        "total":     len(schedules),
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

    params: dict[str, str] = {
        "serviceKey": api_key,
        "implYy":     current_year,
        "jmNm":       cert_name.strip(),
        "returnType": "json",
        "numOfRows":  "10",
        "pageNo":     "1",
    }

    try:
        resp = httpx.get(
            _QNET_PROF_BASE,
            params=params,
            timeout=settings.hrdkorea_api_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "국가전문자격 시험일정 API 응답 시간이 초과되었습니다.")
    except httpx.HTTPStatusError as e:
        return err_envelope("EXTERNAL_API_ERROR", f"국가전문자격 시험일정 API 오류: HTTP {e.response.status_code}")
    except Exception as e:
        logger.warning("prof_exam_schedule API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "국가전문자격 시험일정 조회 중 오류가 발생했습니다.")

    try:
        body = data.get("response", {}).get("body", {})
        items_raw = body.get("items", {})
        if isinstance(items_raw, dict):
            item_list = items_raw.get("item", [])
            if isinstance(item_list, dict):
                item_list = [item_list]
        elif isinstance(items_raw, list):
            item_list = items_raw
        else:
            item_list = []
    except Exception:
        item_list = []

    schedules = [_format_schedule_item(it) for it in item_list]
    schedules.sort(key=lambda s: s.get("d_day_exam") or 9999)

    result = ok_envelope({
        "cert_name": cert_name,
        "year":      current_year,
        "schedules": schedules,
        "total":     len(schedules),
        "note":      "국가전문자격 시험일정 — Q-Net ProfExamScheduleService",
    })
    _cache_set(prof_cache_key, result)
    return result
