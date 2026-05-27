# File: exam_schedule_service.py
# Last Updated: 2026-05-20
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

_TTL = 3600  # 시험 일정은 하루 단위 변경 — 1시간 캐시 (페이지네이션 비용 상각)
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
    serviceKey를 URL에 삽입. 이미 URL-인코딩된 키와 raw 키 모두 처리:
    decode → encode 단계로 이중 인코딩을 방지하면서 항상 올바른 인코딩 보장.
    """
    try:
        key = urllib.parse.quote(urllib.parse.unquote(api_key_in), safe='')
    except Exception:
        key = api_key_in
    qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in extra.items())
    return f"{base}?serviceKey={key}&{qs}"


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
    """API 응답 item → 프론트 표시용 정제 dict (필기/실기 분리 포함)."""
    # 필기
    doc_reg_s  = item.get("docRegStartDt") or ""
    doc_reg_e  = item.get("docRegEndDt") or ""
    doc_exam_s = item.get("docExamStartDt") or ""
    doc_exam_e = item.get("docExamEndDt") or ""
    doc_pass   = item.get("docPassDt") or ""
    # 실기 (pracReg* 사용 — 구 코드의 recReg* 오타 수정)
    prac_reg_s  = item.get("pracRegStartDt") or ""
    prac_reg_e  = item.get("pracRegEndDt") or ""
    prac_exam_s = item.get("pracExamStartDt") or ""
    prac_exam_e = item.get("pracExamEndDt") or ""
    prac_pass   = item.get("pracPassDt") or ""

    has_written   = bool(doc_reg_s or doc_exam_s or doc_pass)
    has_practical = bool(prac_reg_s or prac_exam_s or prac_pass)

    # 통합 정렬/D-Day 기준: 필기 있으면 필기 시작, 없으면 실기 시작
    reg_start  = doc_reg_s or prac_reg_s
    exam_start = doc_exam_s or prac_exam_s
    pass_dt    = doc_pass or prac_pass

    return {
        "impl_year":     item.get("implYy"),
        "impl_seq":      item.get("implSeq"),
        "description":   item.get("description", ""),
        "impl_seq_name": item.get("description", ""),  # frontend compat alias
        # 필기 일정 (없으면 null)
        "written": {
            "registration_start": doc_reg_s or None,
            "registration_end":   doc_reg_e or None,
            "exam_start":         doc_exam_s or None,
            "exam_end":           doc_exam_e or None,
            "pass_announce_date": doc_pass or None,
            "d_day_exam":         _calc_dday(doc_exam_s),
            "d_day_registration": _calc_dday(doc_reg_s),
        } if has_written else None,
        # 실기 일정 (없으면 null)
        "practical": {
            "registration_start": prac_reg_s or None,
            "registration_end":   prac_reg_e or None,
            "exam_start":         prac_exam_s or None,
            "exam_end":           prac_exam_e or None,
            "pass_announce_date": prac_pass or None,
            "d_day_exam":         _calc_dday(prac_exam_s),
            "d_day_registration": _calc_dday(prac_reg_s),
        } if has_practical else None,
        # 하위 호환 통합 필드
        "registration_start": reg_start or None,
        "registration_end":   (doc_reg_e or prac_reg_e) or None,
        "exam_start":         exam_start or None,
        "exam_end":           (doc_exam_e or prac_exam_e) or None,
        "pass_announce_date": pass_dt or None,
        "d_day_exam":         _calc_dday(exam_start),
        "d_day_registration": _calc_dday(reg_start),
    }


def _dedup_by_seq(items: list[dict]) -> list[dict]:
    """같은 implSeq 내 등록 기간만 다른 중복 항목 제거.
    동일 회차(implSeq)에서 필기 접수 시작일이 가장 이른 항목을 대표로 선택."""
    seen: dict[int, dict] = {}
    for it in items:
        seq = int(it.get("implSeq") or 0)
        if seq not in seen:
            seen[seq] = it
        else:
            # 더 이른 접수 시작일 항목을 대표로 유지
            existing_reg = seen[seq].get("docRegStartDt") or seen[seq].get("pracRegStartDt") or "99999999"
            this_reg = it.get("docRegStartDt") or it.get("pracRegStartDt") or "99999999"
            if this_reg < existing_reg:
                seen[seq] = it
    return list(seen.values())


def _fetch_all_exam_schd(api_key: str, year: str, timeout: float) -> list[dict] | None:
    """연도별 전체 시험일정을 페이지네이션으로 수집.
    최대 50/page 제한 → totalCount 기준 자동 페이지 순회.
    오류 시 None 반환 (호출자가 fallback 처리)."""
    collected: list[dict] = []
    for page in range(1, 20):  # 안전 상한 20 pages
        url = _build_qnet_url(_EXAM_SCHD_BASE, api_key, {
            "dataFormat": "json",
            "numOfRows":  "50",
            "pageNo":     str(page),
            "implYy":     year,
        })
        try:
            resp = httpx.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("exam_schedule fetch page=%s error: %s", page, e)
            return None if not collected else collected

        header = data.get("header", {})
        if header.get("resultCode") not in ("00", None, ""):
            logger.warning("exam_schedule API error page=%s: %s", page, header.get("resultMsg"))
            break

        body = data.get("body", {})
        if not isinstance(body, dict):
            break
        items = body.get("items") or []
        if not isinstance(items, list):
            break
        collected.extend(items)

        total = int(body.get("totalCount") or 0)
        if total > 0 and len(collected) >= total:
            break
        if len(items) < 50:
            break

    return collected or None


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

    # hrdkorea_api_key_in(URL-인코딩 키) 우선, 없으면 hrdkorea_api_key_de(raw 키)를 인코딩해서 사용
    api_key = settings.hrdkorea_api_key_in
    if not api_key and settings.hrdkorea_api_key_de:
        api_key = urllib.parse.quote(settings.hrdkorea_api_key_de, safe='')
    if not api_key:
        return _fallback("key_missing")

    grade_name = cert_info.get("grade_name", "")  # 기능사 / 산업기사 / 기사 / 기능장 / 기술사

    sched_cache_key = f"exam_sched|{cert_id}|{current_year}"
    cached = _cache_get(sched_cache_key)
    if cached is not None:
        return cached

    # 전체 페이지 조회 (최대 50/page, totalCount 기준). 연도별 캐시 공유로 비용 상각.
    year_cache_key = f"exam_schd_all|{current_year}"
    all_items = _cache_get(year_cache_key)
    if all_items is None:
        all_items = _fetch_all_exam_schd(api_key, current_year, settings.hrdkorea_api_timeout)
        if all_items is None:
            return _fallback("unavailable")
        _cache_set(year_cache_key, all_items)

    try:
        item_list = list(all_items)
        # grade_name 기준 필터 — " 기사 " 공백 경계로 "산업기사"/"기술사" 오매칭 방지
        if grade_name:
            padded = f" {grade_name} "
            item_list = [it for it in item_list if padded in it.get("description", "")]
        item_list = _dedup_by_seq(item_list)
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
    if not api_key and settings.hrdkorea_api_key_de:
        api_key = urllib.parse.quote(settings.hrdkorea_api_key_de, safe='')
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

    # 연도 전체 캐시 공유 (cert_id 기반 exam_schedule와 동일 캐시 키)
    year_cache_key = f"exam_schd_all|{current_year}"
    all_items = _cache_get(year_cache_key)
    if all_items is None:
        all_items = _fetch_all_exam_schd(api_key, current_year, settings.hrdkorea_api_timeout)
        if all_items is None:
            return err_envelope("EXTERNAL_API_ERROR", "시험일정 조회 중 오류가 발생했습니다.")
        _cache_set(year_cache_key, all_items)

    try:
        kw = cert_name.strip()
        filtered = [it for it in all_items if kw in it.get("description", "")]
        item_list = filtered if filtered else all_items
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


# ── HRD Korea 합격자 통계 ─────────────────────────────────────────────────────
_PASS_STAT_BASE = "https://apis.data.go.kr/B490007/qualPassStat/getQualPassStatList"


def get_pass_stats(cert_id: str, settings: Settings) -> dict:
    """
    HRD Korea 합격자 통계 조회 (최근 3개 연도).
    필기/실기 응시·합격·합격률을 반환한다.
    """
    api_key = settings.hrdkorea_api_key_in
    if not api_key:
        return err_envelope("API_KEY_MISSING", "HRD Korea API 키가 설정되지 않았습니다.")

    cert_names = _load_cert_name_map()
    cert_name = cert_names.get(cert_id)
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")

    cache_key = f"pass_stat|{cert_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    current_year = str(date.today().year)
    years = [str(int(current_year) - i) for i in range(3)]  # 최근 3년

    all_stats: list[dict[str, Any]] = []
    for year in years:
        url = _build_qnet_url(_PASS_STAT_BASE, api_key, {
            "dataFormat": "json",
            "numOfRows":  "10",
            "pageNo":     "1",
            "implYy":     year,
        })
        try:
            resp = httpx.get(url, timeout=settings.hrdkorea_api_timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("pass_stat year=%s cert=%s error: %s", year, cert_id, e)
            continue

        items = data.get("body", {}).get("items", {})
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            continue

        for it in items:
            if cert_name in (it.get("description") or it.get("jmNm") or ""):
                raw_written_app  = it.get("docAplcntNm") or it.get("docAplcnt") or "0"
                raw_written_pass = it.get("docPassNm")   or it.get("docPass")   or "0"
                raw_prac_app     = it.get("pracAplcntNm")or it.get("pracAplcnt")or "0"
                raw_prac_pass    = it.get("pracPassNm")  or it.get("pracPass")  or "0"

                def _num(v: str) -> int | None:
                    try:
                        return int(str(v).replace(",", ""))
                    except (ValueError, AttributeError):
                        return None

                def _rate(p: int | None, a: int | None) -> float | None:
                    if p is not None and a and a > 0:
                        return round(p / a * 100, 1)
                    return None

                wa = _num(raw_written_app)
                wp = _num(raw_written_pass)
                pa = _num(raw_prac_app)
                pp = _num(raw_prac_pass)

                all_stats.append({
                    "year":              year,
                    "impl_seq":          it.get("implSeq") or it.get("implYy"),
                    "written_applicants": wa,
                    "written_pass":       wp,
                    "written_pass_rate":  _rate(wp, wa),
                    "practical_applicants": pa,
                    "practical_pass":       pp,
                    "practical_pass_rate":  _rate(pp, pa),
                })
                break  # 해당 연도 첫 번째 일치 항목

    result = ok_envelope({
        "cert_id":   cert_id,
        "cert_name": cert_name,
        "stats":     all_stats,
        "total":     len(all_stats),
        "note":      "HRD Korea 합격자 통계 (최근 3개 연도, apis.data.go.kr/B490007)",
    })
    _cache_set(cache_key, result)
    return result


# ── HRD Korea 취업현황 ───────────────────────────────────────────────────────
_HIRE_INFO_BASE = "https://apis.data.go.kr/B490007/qualHireInfo/getQualHireInfoList"


def get_hire_stats(cert_id: str, settings: Settings) -> dict:
    """
    HRD Korea 자격취득자 취업현황 조회.
    자격증 취득 후 취업률·고용보험 가입 현황을 반환한다.
    """
    api_key = settings.hrdkorea_api_key_in
    if not api_key:
        return err_envelope("API_KEY_MISSING", "HRD Korea API 키가 설정되지 않았습니다.")

    cert_names = _load_cert_name_map()
    cert_name = cert_names.get(cert_id)
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")

    cache_key = f"hire_stat|{cert_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    current_year = str(date.today().year - 1)  # 전년도 기준 (당해 데이터 미공개)
    url = _build_qnet_url(_HIRE_INFO_BASE, api_key, {
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
        return err_envelope("EXTERNAL_API_TIMEOUT", "취업현황 API 응답 시간이 초과되었습니다.")
    except Exception as e:
        logger.warning("hire_stat cert=%s error: %s", cert_id, e)
        return err_envelope("EXTERNAL_API_ERROR", "취업현황 조회 중 오류가 발생했습니다.")

    items = data.get("body", {}).get("items", {})
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        items = []

    matched: list[dict[str, Any]] = []
    for it in items:
        if cert_name in (it.get("description") or it.get("jmNm") or ""):
            matched.append({
                "year":             it.get("implYy") or current_year,
                "cert_name":        it.get("description") or cert_name,
                "grade_tier":       it.get("grdNm") or "",
                "acquirer_count":   it.get("acqrCnt") or it.get("acqrNm") or "",
                "employed_count":   it.get("emplCnt") or it.get("emplNm") or "",
                "employment_rate":  it.get("emplRate") or "",
                "insurance_enrolled": it.get("insrRgstCnt") or "",
                "note":             it.get("rmk") or "",
            })

    result = ok_envelope({
        "cert_id":   cert_id,
        "cert_name": cert_name,
        "year":      current_year,
        "hire_stats": matched,
        "total":     len(matched),
        "note":      "HRD Korea 자격취득자 취업현황 (apis.data.go.kr/B490007)",
    })
    _cache_set(cache_key, result)
    return result
