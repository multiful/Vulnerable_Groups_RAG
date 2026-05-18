# File: career_net_service.py
# Last Updated: 2026-05-19
# Content Hash: SHA256:TBD
# Role: 커리어넷(한국직업능력연구원) 직업정보 + 학과정보 API 연동
#
# API base: https://www.career.go.kr/cnet/openapi/getOpenApi.do
# svcCode=JOB   → 직업정보 (gubunCode=5: 직업별 상세)
# svcCode=MAJOR → 학과정보 (gubunCode=B: 학과 목록)
#
# 지역 제한: 한국 IP에서는 summary/salery/equalemployment 등 전체 필드 반환.
#            해외 IP(Render)에서는 job(직업명) 필드만 반환, 나머지 빈값.
#            → description/salary 등 비어있으면 goms_service 로컬 CSV로 보완.
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

# Full job list cache (loaded once, used for client-side search since API ignores searchFilter)
_full_job_cache: dict[str, tuple[float, list]] = {}
_FULL_JOB_TTL = 300


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


def _load_all_jobs(api_key: str, timeout: int) -> list[dict]:
    """전체 직업 목록을 로드하고 5분간 캐싱. 커리어넷 API가 searchFilter를 무시하므로 클라이언트 필터링에 사용."""
    cache_key = "__all_jobs__"
    entry = _full_job_cache.get(cache_key)
    if entry and (time.monotonic() - entry[0]) < _FULL_JOB_TTL:
        return entry[1]

    all_items: list[dict] = []
    page_size = 100
    page = 1
    while page <= 6:  # max 600 items (실제 약 454개)
        params = _params_base(api_key, "JOB", "5", page, page_size)
        try:
            resp = httpx.get(_BASE, params=params, timeout=timeout)
            resp.raise_for_status()
            raw = resp.json()
        except Exception as e:
            logger.warning("career_net full job load page=%s error: %s", page, e)
            break
        items = _extract_items(raw)
        if not items:
            break
        all_items.extend(items)
        total = int(items[0].get("totalCount", 0))
        if len(all_items) >= total:
            break
        page += 1

    _full_job_cache[cache_key] = (time.monotonic(), all_items)
    return all_items


def get_job_list(
    q: str | None,
    page: int,
    page_size: int,
    settings: Settings,
) -> dict:
    """커리어넷 직업정보 목록 조회.
    q: 직업명 검색어 — API가 서버사이드 검색을 지원하지 않으므로 전체 목록 로드 후 클라이언트 필터링.
    """
    api_key = settings.career_net_api_key
    if not api_key:
        return err_envelope("API_KEY_MISSING", "커리어넷 API 키가 설정되지 않았습니다.")

    cache_key = f"job_list|{q}|{page}|{page_size}"
    cached = _ttl_get(cache_key)
    if cached is not None:
        return cached

    if q and q.strip():
        # 검색어 있음: 전체 목록 로드 후 직업명으로 클라이언트 필터링
        all_items = _load_all_jobs(api_key, settings.career_net_api_timeout)
        q_lower = q.strip().lower()
        filtered = [it for it in all_items if q_lower in (it.get("job") or "").lower()]
        total = len(filtered)
        start = (page - 1) * page_size
        page_items = filtered[start:start + page_size]
        jobs = [_normalize_job(it) for it in page_items]
    else:
        # 검색어 없음: 표준 페이지네이션
        params = _params_base(api_key, "JOB", "5", page, page_size)
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
        total = _extract_total(raw)
        jobs = [_normalize_job(it) for it in items]

    result = ok_envelope({
        "jobs":  jobs,
        "total": total,
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
    # API returns totalCount inside each content item, not as a separate field
    try:
        data = raw.get("dataSearch", raw.get("dataMajors", raw))
        content = data.get("content", [])
        if isinstance(content, list) and content:
            return int(content[0].get("totalCount", 0))
        return 0
    except Exception:
        return 0


def _supplement_from_local(job_name: str) -> dict:
    """커리어넷이 빈값 반환 시(해외 IP) goms_service 로컬 CSV로 보완."""
    try:
        from backend.app.services.goms_service import get_job_info
        info = get_job_info(job_name)
        if info:
            return {
                "description":         info.get("work_content") or "",
                "salary_low":          info.get("salary_summary") or info.get("salary") or "",
                "employment_prospect": info.get("outlook") or "",
                "pay_score":           info.get("pay_score"),
                "growth_score":        info.get("growth_score"),
                "similar_jobs":        info.get("similar_jobs") or "",
                "aptitude":            info.get("aptitude") or "",
                "source":              "local_goms",
            }
    except Exception:
        pass
    return {}


def _normalize_job(item: dict) -> dict:
    name = item.get("job", "")
    description = item.get("summary", "")
    salary = item.get("salery", "")  # API 오타 "salery"
    prospect = item.get("possibility", "")

    base = {
        "seq":                 item.get("jobdicSeq", ""),
        "name":                name,
        "description":         description,
        "tasks":               item.get("similarJob", ""),
        "salary_low":          salary,
        "salary_high":         "",
        "employment_rate":     item.get("equalemployment", ""),
        "employment_prospect": prospect,
        "profession":          item.get("profession", ""),
        "knowledge":    "",
        "skills":       "",
        "work_env":     "",
        "related_certs": "",
        "related_majors": "",
        "image_url":    "",
        "career_path":  "",
        "personality":  "",
        "interest":     "",
        "job_value":    "",
        "source":       "career_net",
    }

    # 해외 IP geo-restriction: API가 직업명만 반환할 때 로컬 데이터로 보완
    if name and not description and not salary:
        local = _supplement_from_local(name)
        if local:
            base.update(local)

    return base


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
