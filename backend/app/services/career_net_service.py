# File: career_net_service.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 커리어넷(한국직업능력연구원) 직업정보 + 학과정보 API 연동
#
# API base: https://www.career.go.kr/cnet/openapi/getOpenApi.do
# svcCode=JOB   → 직업정보 (gubunCode=5: 직업별 상세)
# svcCode=MAJOR → 학과정보 (gubunCode=B: 학과 목록)
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_BASE = "https://www.career.go.kr/cnet/openapi/getOpenApi.do"

# TTL cache: key → (timestamp, data). Avoids hammering the external API on repeated calls.
_TTL_SECONDS = 300
_ttl_cache: dict[str, tuple[float, Any]] = {}


def _ttl_get(key: str) -> Any | None:
    entry = _ttl_cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _TTL_SECONDS:
        return entry[1]
    return None


def _ttl_set(key: str, value: Any) -> None:
    _ttl_cache[key] = (time.monotonic(), value)


def _params_base(api_key: str, svc_code: str, gubun_code: str, page: int, page_size: int) -> dict:
    return {
        "apiKey":      api_key,
        "svcType":     "api",
        "svcCode":     svc_code,
        "contentType": "json",
        "gubunCode":   gubun_code,
        "pageIndex":   str(page),
        "pageCount":   str(page_size),
    }


def get_job_list(
    q: str | None,
    page: int,
    page_size: int,
    settings: Settings,
) -> dict:
    """커리어넷 직업정보 목록 조회.
    q: 직업명 검색어 (선택). 미입력 시 전체 목록 반환.
    """
    api_key = settings.career_net_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "커리어넷 API 키가 설정되지 않았습니다.")

    cache_key = f"job_list|{q}|{page}|{page_size}"
    cached = _ttl_get(cache_key)
    if cached is not None:
        return cached

    params = _params_base(api_key, "JOB", "5", page, page_size)
    if q and q.strip():
        params["searchFilter"] = q.strip()

    try:
        resp = httpx.get(_BASE, params=params, timeout=settings.career_net_api_timeout)
        resp.raise_for_status()
        raw = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "커리어넷 API 응답 시간이 초과됐습니다.")
    except httpx.HTTPStatusError as e:
        return err_envelope("EXTERNAL_API_ERROR", f"커리어넷 API 오류: HTTP {e.response.status_code}")
    except Exception as e:
        logger.warning("career_net job API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "직업정보 조회 중 오류가 발생했습니다.")

    items = _extract_items(raw)
    jobs = [_normalize_job(it) for it in items]

    result = ok_envelope({
        "jobs":  jobs,
        "total": _extract_total(raw),
        "page":  page,
        "page_size": page_size,
        "query": q or "",
    })
    _ttl_set(cache_key, result)
    return result


def get_major_list(
    q: str | None,
    page: int,
    page_size: int,
    settings: Settings,
) -> dict:
    """커리어넷 학과정보 목록 조회."""
    api_key = settings.career_net_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "커리어넷 API 키가 설정되지 않았습니다.")

    cache_key = f"major_list|{q}|{page}|{page_size}"
    cached = _ttl_get(cache_key)
    if cached is not None:
        return cached

    params = _params_base(api_key, "MAJOR", "B", page, page_size)
    if q and q.strip():
        params["searchFilter"] = q.strip()

    try:
        resp = httpx.get(_BASE, params=params, timeout=settings.career_net_api_timeout)
        resp.raise_for_status()
        raw = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "커리어넷 API 응답 시간이 초과됐습니다.")
    except httpx.HTTPStatusError as e:
        return err_envelope("EXTERNAL_API_ERROR", f"커리어넷 API 오류: HTTP {e.response.status_code}")
    except Exception as e:
        logger.warning("career_net major API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "학과정보 조회 중 오류가 발생했습니다.")

    items = _extract_items(raw)
    majors = [_normalize_major(it) for it in items]

    result = ok_envelope({
        "majors": majors,
        "total":  _extract_total(raw),
        "page":   page,
        "page_size": page_size,
        "query":  q or "",
    })
    _ttl_set(cache_key, result)
    return result


def get_job_detail(job_seq: str, settings: Settings) -> dict:
    """커리어넷 직업 상세 정보 조회 (gubunCode=1: 단건)."""
    api_key = settings.career_net_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "커리어넷 API 키가 설정되지 않았습니다.")

    params = {
        "apiKey":      api_key,
        "svcType":     "api",
        "svcCode":     "JOB",
        "contentType": "json",
        "gubunCode":   "1",
        "seq":         job_seq,
    }

    try:
        resp = httpx.get(_BASE, params=params, timeout=settings.career_net_api_timeout)
        resp.raise_for_status()
        raw = resp.json()
    except httpx.TimeoutException:
        return err_envelope("EXTERNAL_API_TIMEOUT", "커리어넷 API 응답 시간이 초과됐습니다.")
    except Exception as e:
        logger.warning("career_net job detail API error: %s", e)
        return err_envelope("EXTERNAL_API_ERROR", "직업 상세 조회 중 오류가 발생했습니다.")

    items = _extract_items(raw)
    if not items:
        return err_envelope("NOT_FOUND", f"job_seq '{job_seq}'를 찾을 수 없습니다.")
    return ok_envelope({"job": _normalize_job(items[0])})


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_items(raw: dict) -> list[dict]:
    try:
        data = raw.get("dataSearch", raw.get("dataMajors", raw))
        content = data.get("content", [])
        if isinstance(content, dict):
            return [content]
        return content if isinstance(content, list) else []
    except Exception:
        return []


def _extract_total(raw: dict) -> int:
    try:
        data = raw.get("dataSearch", raw.get("dataMajors", raw))
        return int(data.get("total", 0))
    except Exception:
        return 0


def _normalize_job(item: dict) -> dict:
    return {
        "seq":          item.get("seq", ""),
        "name":         item.get("job", item.get("jobNm", "")),
        "description":  item.get("jobDsc", ""),
        "tasks":        item.get("task", ""),
        "knowledge":    item.get("knowledge", ""),
        "skills":       item.get("skill", ""),
        "work_env":     item.get("workEnv", ""),
        "salary_low":   item.get("salaryLow", ""),
        "salary_high":  item.get("salaryHigh", ""),
        "employment_prospect": item.get("jobPspt", ""),
        "related_certs": item.get("relCert", item.get("relatedCert", "")),
        "related_majors": item.get("relMajor", item.get("relatedMajor", "")),
        "image_url":    item.get("img", ""),
        "career_path":  item.get("careerPath", ""),
    }


def _normalize_major(item: dict) -> dict:
    return {
        "seq":          item.get("seq", ""),
        "name":         item.get("major", item.get("majorNm", "")),
        "description":  item.get("majorDsc", ""),
        "category":     item.get("gubun", ""),
        "related_jobs":  item.get("relJob", ""),
        "related_certs": item.get("relCert", ""),
        "employment_rate": item.get("emplRate", ""),
    }
