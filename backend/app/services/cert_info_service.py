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


@lru_cache(maxsize=1)
def _load_cert_name_map() -> dict[str, str]:
    if not _CERT_MASTER_CSV.exists():
        return {}
    out: dict[str, str] = {}
    with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["cert_id"]] = r["cert_name"]
    return out


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
