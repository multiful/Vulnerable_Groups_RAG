# File: cert_info_service.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 한국산업인력공단 국가자격 종목별 자격정보(8) + 국가기술자격 종목별 시험정보(9) API 연동
#
# API 8: 국가자격 종목별 자격정보
#   GET http://openapi.q-net.or.kr/api/service/rest/InstitutionInfoService/getItemInfo
#   params: serviceKey, itemNm (자격증명), returnType=json
#
# API 9: 국가기술자격 종목별 시험정보
#   GET http://openapi.q-net.or.kr/api/service/rest/InstitutionInfoService/getExmInfo
#   params: serviceKey, itemNm (자격증명), returnType=json
from __future__ import annotations

import csv
import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parents[3]
_CERT_MASTER_CSV = _PROJECT_ROOT / "data/processed/master/cert_master.csv"

_QNET_ITEM_INFO = "http://openapi.q-net.or.kr/api/service/rest/InstitutionInfoService/getItemInfo"
_QNET_EXAM_INFO = "http://openapi.q-net.or.kr/api/service/rest/InstitutionInfoService/getExmInfo"

_TTL = 3600  # 자격정보는 거의 안 바뀜 — 1시간 캐시
_cert_info_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    entry = _cert_info_cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _cert_info_cache[key] = (time.monotonic(), value)


_REGION_ACQUI_CSV   = _PROJECT_ROOT / "data/raw/csv/행정구역별연도별성별 취득현황_rows.csv"
_CERT_PREREQ_CSV    = _PROJECT_ROOT / "data/canonical/relations/cert_prerequisite.csv"
_SESSION_PASS_CSV   = _PROJECT_ROOT / "data/raw/csv/한국산업인력공단_연도별 회별 국가기술자격 _rows.csv"
_DATA_CERT_ROWS_CSV = _PROJECT_ROOT / "data/raw/csv/data_cert_rows.csv"
_MAJOR_NCS_CSV      = _PROJECT_ROOT / "data/raw/csv/한국산업인력공단_국가기술자격 학과별 직무정_rows.csv"
_RAW_CERT_MASTER    = _PROJECT_ROOT / "data/raw/csv/cert_master.csv"


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
def _load_cert_master_details() -> dict[str, dict]:
    """cert_id → cert_master 확장 필드 (written/practical 합격률, 빈도, 난이도 등)."""
    if not _CERT_MASTER_CSV.exists():
        return {}
    out: dict[str, dict] = {}
    def _f(v: str) -> float | None:
        try:
            return float(v) if v and v.strip() else None
        except ValueError:
            return None
    with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["cert_id"]] = {
                "written_avg_pass_rate":   _f(r.get("written_avg_pass_rate", "")),
                "practical_avg_pass_rate": _f(r.get("practical_avg_pass_rate", "")),
                "avg_pass_rate_3yr":       _f(r.get("avg_pass_rate_3yr", "")),
                "exam_frequency":          (r.get("exam_frequency") or "").strip() or None,
                "exam_difficulty":         _f(r.get("exam_difficulty", "")),
                "exam_fee_info":           (r.get("exam_fee_info") or "").strip() or None,
                "exam_eligibility_info":   (r.get("exam_eligibility_info") or "").strip() or None,
                "exam_subject_info":       (r.get("exam_subject_info") or "").strip() or None,
                "exam_type_info":          (r.get("exam_type_info") or "").strip() or None,
                "cert_grade_tier":         (r.get("cert_grade_tier") or "").strip() or None,
                "primary_domain":          (r.get("primary_domain") or "").strip() or None,
            }
    return out


@lru_cache(maxsize=1)
def _load_cert_prereqs() -> dict[str, list[dict]]:
    """cert_id → 선수 자격증 목록 (cert_prerequisite.csv)."""
    if not _CERT_PREREQ_CSV.exists():
        return {}
    names = _load_cert_name_map()
    out: dict[str, list[dict]] = {}
    with _CERT_PREREQ_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("is_active", "True").strip().lower() not in ("true", "1", "yes"):
                continue
            cid = r.get("cert_id", "")
            pre = r.get("prerequisite_cert_id", "")
            if not cid or not pre:
                continue
            out.setdefault(cid, []).append({
                "prerequisite_cert_id":   pre,
                "prerequisite_cert_name": names.get(pre, pre),
                "relation_kind":          r.get("relation_kind", ""),
                "domain_name_raw":        r.get("domain_name_raw", ""),
                "subject_prefix":         r.get("subject_prefix", ""),
            })
    return out


@lru_cache(maxsize=1)
def _load_region_stats() -> dict[str, list[dict]]:
    """grdNm → [{sido, genderNm, yy1AcquCnt, ..., accumAcquCnt}] 지역별 취득 현황."""
    if not _REGION_ACQUI_CSV.exists():
        return {}
    out: dict[str, list[dict]] = {}
    with _REGION_ACQUI_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            grade = (r.get("grdNm") or "").strip()
            if not grade:
                continue
            out.setdefault(grade, []).append({
                "sido":         r.get("sido", ""),
                "genderNm":     r.get("genderNm", ""),
                "accumAcquCnt": int(r.get("accumAcquCnt") or 0),
                "yy1AcquCnt":   int(r.get("yy1AcquCnt") or 0),
                "yy2AcquCnt":   int(r.get("yy2AcquCnt") or 0),
                "yy3AcquCnt":   int(r.get("yy3AcquCnt") or 0),
            })
    return out


def get_cert_master_stats(cert_id: str) -> dict:
    """cert_master CSV 기반 필기/실기 합격률·시험빈도·난이도 통계 — 외부 API 불필요."""
    names = _load_cert_name_map()
    cert_name = names.get(cert_id)
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")
    detail = _load_cert_master_details().get(cert_id, {})
    return ok_envelope({
        "cert_id":   cert_id,
        "cert_name": cert_name,
        **detail,
    })


def get_cert_prerequisites(cert_id: str) -> dict:
    """cert_prerequisite.csv 기반 선수 자격증 목록."""
    names = _load_cert_name_map()
    cert_name = names.get(cert_id)
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")
    prereqs = _load_cert_prereqs().get(cert_id, [])
    return ok_envelope({
        "cert_id":       cert_id,
        "cert_name":     cert_name,
        "prerequisites": prereqs,
        "total":         len(prereqs),
    })


def get_region_stats(cert_grade: str | None = None) -> dict:
    """행정구역별연도별성별 취득현황 조회.
    cert_grade: 등급명 (예: '기능사', '기사') — 미지정 시 전체 집계 반환."""
    stats = _load_region_stats()
    if cert_grade:
        rows = stats.get(cert_grade, [])
        if not rows:
            return err_envelope("NOT_FOUND", f"'{cert_grade}'에 해당하는 지역 통계가 없습니다.")
        return ok_envelope({"grade": cert_grade, "rows": rows, "total": len(rows)})
    # 전체: grade별 총 취득자 수 집계
    summary = []
    for grade, rows in stats.items():
        total_accum = sum(r["accumAcquCnt"] for r in rows)
        summary.append({"grade": grade, "total_acquired": total_accum})
    summary.sort(key=lambda x: -x["total_acquired"])
    return ok_envelope({"grades": summary, "total_grades": len(summary)})


@lru_cache(maxsize=1)
def _load_session_pass_rates() -> dict[str, list[dict]]:
    """cert_name → [{year, session, exam_type, applicants, passed, pass_rate}]
    Primary: data_cert_rows.csv (1086 certs, 2022-2024 per session columns)
    Supplement: 연도별 회별 CSV (79 certs, official row format)
    """
    out: dict[str, list[dict]] = {}

    # ── Primary: data_cert_rows.csv ───────────────────────────────────────────
    if _DATA_CERT_ROWS_CSV.exists():
        try:
            with _DATA_CERT_ROWS_CSV.open(encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    name = (r.get("자격증명") or "").strip()
                    if not name:
                        continue
                    # Columns: 2022년 1차 응시자 수, 2022년 1차 합격률, ..., 2024년 3차
                    for yr in ("2022", "2023", "2024"):
                        for sess in ("1차", "2차", "3차"):
                            app_key = f"{yr}년 {sess} 응시자 수" if sess == "1차" else f"{yr}년 {sess} 응시자수"
                            # try both key formats
                            app_raw = r.get(app_key) or r.get(f"{yr}년 {sess} 응시자 수") or ""
                            rate_raw = r.get(f"{yr}년 {sess} 합격률") or ""
                            if not app_raw and not rate_raw:
                                continue
                            try:
                                applicants = int(app_raw) if app_raw.strip() else 0
                                pass_rate = float(rate_raw) if rate_raw.strip() else 0.0
                            except (ValueError, TypeError):
                                continue
                            if applicants == 0 and pass_rate == 0.0:
                                continue
                            out.setdefault(name, []).append({
                                "year":       yr,
                                "session":    sess,
                                "exam_type":  r.get("시험종류", ""),
                                "grade":      r.get("등급_분류", ""),
                                "applicants": applicants,
                                "passed":     round(applicants * pass_rate / 100),
                                "pass_rate":  pass_rate,
                            })
        except Exception as e:
            logger.warning("data_cert_rows.csv 로드 실패: %s", e)

    # ── Supplement: 연도별 회별 CSV (richer official data, overrides if present) ─
    if _SESSION_PASS_CSV.exists():
        try:
            with _SESSION_PASS_CSV.open(encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    name = (r.get("jmFldNm") or "").strip()
                    if not name:
                        continue
                    try:
                        pass_rate = float(r.get("passRateNum") or 0)
                        applicants = int(r.get("recptNoCnt") or 0)
                        passed = int(r.get("examPassCnt") or 0)
                    except (ValueError, TypeError):
                        continue
                    # Official data takes precedence — replace if already have this cert
                    if name not in out:
                        out[name] = []
                    out[name].append({
                        "year":       r.get("implYy", ""),
                        "session":    r.get("implSeq", ""),
                        "exam_type":  r.get("examTypCcd", ""),
                        "grade":      r.get("grdNm", ""),
                        "applicants": applicants,
                        "passed":     passed,
                        "pass_rate":  pass_rate,
                    })
        except Exception as e:
            logger.warning("연도별 회별 CSV 로드 실패: %s", e)

    return out


@lru_cache(maxsize=1)
def _load_major_ncs_map() -> dict[str, list[dict]]:
    """udeptnm(학과명) → [{ncs_major_code, ncs_major_name, ncs_minor_code, ncs_minor_name}]
    Source: 한국산업인력공단_국가기술자격 학과별 직무정_rows.csv
    """
    if not _MAJOR_NCS_CSV.exists():
        return {}
    out: dict[str, list[dict]] = {}
    try:
        with _MAJOR_NCS_CSV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                major = (r.get("udeptnm") or "").strip()
                if not major:
                    continue
                entry = {
                    "ncs_major_code": r.get("udeptmdobligcd", ""),
                    "ncs_major_name": r.get("udeptmdoblignm", ""),
                    "ncs_minor_code": r.get("udeptobligcd", ""),
                    "ncs_minor_name": r.get("udeptoblignm", ""),
                }
                existing = out.setdefault(major, [])
                if entry not in existing:
                    existing.append(entry)
    except Exception as e:
        logger.warning("학과별 직무정 CSV 로드 실패: %s", e)
    return out


@lru_cache(maxsize=1)
def _load_raw_cert_name_map() -> dict[str, str]:
    """cert_name → cert_id (raw cert_master.csv 기준, 정확 매칭용)."""
    if not _RAW_CERT_MASTER.exists():
        return {}
    out: dict[str, str] = {}
    try:
        with _RAW_CERT_MASTER.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                name = (r.get("cert_name") or "").strip()
                cid = (r.get("cert_id") or "").strip()
                if name and cid:
                    out[name] = cid
    except Exception as e:
        logger.warning("raw cert_master.csv 로드 실패: %s", e)
    return out


def get_session_pass_rates(cert_id: str) -> dict:
    """연도별 회별 시험 합격률 — cert_id로 조회, cert_name으로 CSV 매칭."""
    names = _load_cert_name_map()
    cert_name = names.get(cert_id)
    if not cert_name:
        # fallback: raw cert_master
        for name, cid in _load_raw_cert_name_map().items():
            if cid == cert_id:
                cert_name = name
                break
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")

    sessions_map = _load_session_pass_rates()
    rows = sessions_map.get(cert_name, [])

    # Split written vs practical
    written = [r for r in rows if "필기" in r.get("exam_type", "")]
    practical = [r for r in rows if "실기" in r.get("exam_type", "")]
    other = [r for r in rows if r not in written and r not in practical]

    return ok_envelope({
        "cert_id":   cert_id,
        "cert_name": cert_name,
        "written":   sorted(written, key=lambda x: (x["year"], x["session"])),
        "practical": sorted(practical, key=lambda x: (x["year"], x["session"])),
        "other":     other,
        "total":     len(rows),
    })


def get_major_ncs(major_name: str) -> dict:
    """학과명 → NCS 직무 매핑 (학과별 직무정_rows.csv 기반)."""
    if not major_name or not major_name.strip():
        return err_envelope("INVALID_INPUT", "major_name이 비어 있습니다.")
    ncs_map = _load_major_ncs_map()
    # 정확 일치 → 부분 일치
    results = ncs_map.get(major_name.strip())
    if results is None:
        q = major_name.strip().lower()
        results = []
        seen: set[tuple] = set()
        for key, entries in ncs_map.items():
            if q in key.lower():
                for e in entries:
                    sig = (e["ncs_major_code"], e["ncs_minor_code"])
                    if sig not in seen:
                        seen.add(sig)
                        results.append(e)
    return ok_envelope({
        "major_name": major_name.strip(),
        "ncs_duties": results,
        "total":      len(results),
    })


def get_cert_item_info(cert_id: str, settings: Settings) -> dict:
    """국가자격 종목별 자격정보 (응시자격·취득방법·수수료 등)."""
    api_key = settings.hrdkorea_api_key_in
    if not api_key:
        return err_envelope("API_KEY_MISSING", "한국산업인력공단 API 키가 설정되지 않았습니다.")

    cert_names = _load_cert_name_map()
    cert_name = cert_names.get(cert_id)
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")

    item_cache_key = f"cert_item|{cert_id}"
    cached = _cache_get(item_cache_key)
    if cached is not None:
        return cached

    params = {
        "serviceKey": api_key,
        "itemNm":     cert_name,
        "returnType": "json",
    }

    try:
        resp = httpx.get(_QNET_ITEM_INFO, params=params, timeout=settings.hrdkorea_api_timeout)
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "자격정보 API 응답 시간이 초과됐습니다.")
    except httpx.HTTPStatusError as e:
        return err_envelope("EXTERNAL_API_ERROR", f"자격정보 API 오류: HTTP {e.response.status_code}")
    except Exception as e:
        logger.warning("cert_item_info API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "자격정보 조회 중 오류가 발생했습니다.")

    item = _extract_single_item(data)
    if not item:
        return ok_envelope({"cert_id": cert_id, "cert_name": cert_name, "info": None})

    result = ok_envelope({
        "cert_id":   cert_id,
        "cert_name": cert_name,
        "info":      _normalize_item_info(item),
    })
    _cache_set(item_cache_key, result)
    return result


def get_cert_exam_info(cert_id: str, settings: Settings) -> dict:
    """국가기술자격 종목별 시험정보 (시험과목·출제기준·합격기준 등)."""
    api_key = settings.hrdkorea_api_key_in
    if not api_key:
        return err_envelope("API_KEY_MISSING", "한국산업인력공단 API 키가 설정되지 않았습니다.")

    cert_names = _load_cert_name_map()
    cert_name = cert_names.get(cert_id)
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")

    exam_cache_key = f"cert_exam|{cert_id}"
    cached = _cache_get(exam_cache_key)
    if cached is not None:
        return cached

    params = {
        "serviceKey": api_key,
        "itemNm":     cert_name,
        "returnType": "json",
    }

    try:
        resp = httpx.get(_QNET_EXAM_INFO, params=params, timeout=settings.hrdkorea_api_timeout)
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "시험정보 API 응답 시간이 초과됐습니다.")
    except httpx.HTTPStatusError as e:
        return err_envelope("EXTERNAL_API_ERROR", f"시험정보 API 오류: HTTP {e.response.status_code}")
    except Exception as e:
        logger.warning("cert_exam_info API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "시험정보 조회 중 오류가 발생했습니다.")

    item = _extract_single_item(data)
    if not item:
        return ok_envelope({"cert_id": cert_id, "cert_name": cert_name, "exam_info": None})

    result = ok_envelope({
        "cert_id":   cert_id,
        "cert_name": cert_name,
        "exam_info": _normalize_exam_info(item),
    })
    _cache_set(exam_cache_key, result)
    return result


def get_cert_full_info(cert_id: str, settings: Settings) -> dict:
    """자격정보 + 시험정보를 합쳐서 단일 응답으로 반환."""
    item_result = get_cert_item_info(cert_id, settings)
    exam_result = get_cert_exam_info(cert_id, settings)

    cert_name = _load_cert_name_map().get(cert_id, cert_id)

    return ok_envelope({
        "cert_id":   cert_id,
        "cert_name": cert_name,
        "info":      item_result.get("data", {}).get("info") if item_result.get("success") else None,
        "exam_info": exam_result.get("data", {}).get("exam_info") if exam_result.get("success") else None,
    })


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_single_item(data: dict) -> dict | None:
    try:
        body = data.get("response", {}).get("body", {})
        items_raw = body.get("items", {})
        if isinstance(items_raw, dict):
            item = items_raw.get("item")
            if isinstance(item, list):
                return item[0] if item else None
            return item if isinstance(item, dict) else None
        if isinstance(items_raw, list):
            return items_raw[0] if items_raw else None
    except Exception:
        pass
    return None


def _normalize_item_info(item: dict) -> dict:
    return {
        "qualification_type":    item.get("qualgbNm", ""),          # 자격 구분 (국가기술 / 전문)
        "level":                 item.get("jmfldnm", ""),           # 등급
        "related_occupation":    item.get("relJobNm", ""),          # 관련 직업
        "acquisition_method":    item.get("acqMethCd", ""),         # 취득방법
        "exam_fee_written":      item.get("docFee", ""),            # 필기 응시수수료
        "exam_fee_practical":    item.get("pracFee", ""),           # 실기 응시수수료
        "issuance_fee":          item.get("issuFee", ""),           # 자격증 발급수수료
        "eligibility":           item.get("aplfmtNm", ""),          # 응시자격
        "description":           item.get("jmNm", item.get("itemNm", "")),
        "issuer":                item.get("insttNm", ""),           # 발급기관
        "website":               item.get("hmpgAddr", ""),          # 홈페이지
    }


def _normalize_exam_info(item: dict) -> dict:
    return {
        "written_subjects":     item.get("docSubjNm", ""),          # 필기 시험과목
        "practical_subjects":   item.get("pracSubjNm", ""),         # 실기 시험과목
        "written_pass_score":   item.get("docPassScr", ""),         # 필기 합격기준
        "practical_pass_score": item.get("pracPassScr", ""),        # 실기 합격기준
        "written_exam_time":    item.get("docExmTime", ""),         # 필기 시험시간
        "practical_exam_time":  item.get("pracExmTime", ""),        # 실기 시험시간
        "exam_method":          item.get("exmMthNm", ""),           # 시험방법
        "outline_url":          item.get("jmNm", ""),               # 출제기준 URL (항목명으로 대체)
    }
