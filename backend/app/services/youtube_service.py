# File: youtube_service.py
# Last Updated: 2026-05-12
# Content Hash: SHA256:TBD
# Role: F-11 관련 동영상 추천 — YouTube Data API v3 호출 + Supabase 캐시 (TTL 30일)
#
# 흐름:
#   1. cert_id → candidates에서 cert_name 조회 (없으면 CERT_NOT_FOUND)
#   2. Supabase cert_video_cache 조회 — fetched_at 30일 이내 + query_version 일치 → 캐시 반환
#   3. 캐시 미스/만료 → YouTube search.list 호출 → 5개 영상 추출 → upsert
#   4. quota 초과 시 캐시 fallback (오래된 캐시라도 반환), 캐시 없으면 빈 배열 + quota_exceeded
#
# 외부 의존:
#   - httpx (requirements.txt 기존 포함)
#   - supabase-py (requirements.txt 기존 포함)
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from backend.app.core.config import Settings, get_settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

_PROJECT_ROOT = Path(__file__).parents[3]
_CANDIDATES_JSONL = _PROJECT_ROOT / "data/canonical/candidates/cert_candidates.jsonl"

_YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_REQUEST_TIMEOUT_SEC = 8.0


# ---------- cert_id → cert_name 조회 ----------
@lru_cache(maxsize=1)
def _load_cert_name_map() -> dict[str, str]:
    if not _CANDIDATES_JSONL.exists():
        return {}
    out: dict[str, str] = {}
    with _CANDIDATES_JSONL.open(encoding="utf-8") as f:
        for line in f:
            if s := line.strip():
                c = json.loads(s)
                cid = c.get("cert_id")
                cname = c.get("cert_name") or ""
                if cid and cname:
                    out[cid] = cname
    return out


def _build_search_query(cert_name: str) -> str:
    """검색 쿼리: "{cert_name} 강의" OR "{cert_name} 인강" OR "{cert_name} 합격"
    YouTube search는 따옴표 + | 로 OR 표현 가능.
    """
    return f'"{cert_name} 강의" | "{cert_name} 인강" | "{cert_name} 합격"'


# ---------- Supabase 클라이언트 (필요 시 lazy 생성) ----------
def _get_supabase_client(settings: Settings):
    if not settings.supabase_url or not settings.supabase_service_key:
        return None
    try:
        from supabase import create_client  # type: ignore

        return create_client(settings.supabase_url, settings.supabase_service_key)
    except Exception:
        return None


def _read_cache(sb, table: str, cert_id: str) -> dict | None:
    if sb is None:
        return None
    try:
        res = sb.table(table).select("*").eq("cert_id", cert_id).limit(1).execute()
        rows = getattr(res, "data", None) or []
        return rows[0] if rows else None
    except Exception:
        return None


def _write_cache(
    sb,
    table: str,
    cert_id: str,
    cert_name: str,
    search_query: str,
    videos: list[dict],
    query_version: int,
    quota_exceeded: bool = False,
) -> None:
    if sb is None:
        return
    payload: dict[str, Any] = {
        "cert_id": cert_id,
        "cert_name": cert_name,
        "search_query": search_query,
        "videos": videos,
        "query_version": query_version,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    if quota_exceeded:
        payload["quota_exceeded_at"] = datetime.now(timezone.utc).isoformat()
    try:
        sb.table(table).upsert(payload).execute()
    except Exception:
        # 캐시 쓰기 실패는 응답에 영향 주지 않음
        pass


def _cache_is_fresh(row: dict, ttl_days: int, query_version: int) -> bool:
    if not row:
        return False
    if int(row.get("query_version", 0) or 0) != query_version:
        return False
    fetched_at = row.get("fetched_at")
    if not fetched_at:
        return False
    try:
        ts = datetime.fromisoformat(str(fetched_at).replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - ts < timedelta(days=ttl_days)
    except Exception:
        return False


# ---------- 숏츠 / 너무 짧은 영상 제외 헬퍼 ----------
_SHORTS_TITLE_MARKERS = ("#shorts", "#short", "#쇼츠", "#숏츠", "shorts", "쇼츠")


def _is_likely_shorts(title: str) -> bool:
    t = (title or "").lower()
    return any(m in t for m in _SHORTS_TITLE_MARKERS)


# ---------- YouTube API 호출 ----------
def _call_youtube_search(api_key: str, query: str, max_results: int) -> tuple[list[dict], str | None]:
    """Returns (videos, error_code). error_code: None | "quota_exceeded" | "timeout" | "api_error".

    숏츠 제외 전략:
      1) videoDuration=medium (4–20분) — YouTube API 단에서 1차 필터
      2) 제목에 '#shorts' / '쇼츠' 포함 시 제외 — 클라이언트 단에서 2차 필터
      3) 더 많이 요청해서(10) 필터 후 max_results개로 추리기
    """
    fetch_count = min(max_results * 2, 50)  # 여유분 요청 후 필터
    params = {
        "key": api_key,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": fetch_count,
        "regionCode": "KR",
        "relevanceLanguage": "ko",
        "safeSearch": "moderate",
        "videoDuration": "medium",  # 4–20분 → 숏츠(<60초) 자동 제외
    }
    try:
        with httpx.Client(timeout=_REQUEST_TIMEOUT_SEC) as client:
            resp = client.get(_YOUTUBE_SEARCH_URL, params=params)
    except httpx.TimeoutException:
        return [], "timeout"
    except Exception:
        return [], "api_error"

    if resp.status_code == 403:
        # quota / disabled / forbidden — 본문 안의 reason 확인
        body = resp.text.lower()
        if "quota" in body or "ratelimit" in body:
            return [], "quota_exceeded"
        return [], "api_error"
    if resp.status_code != 200:
        return [], "api_error"

    data = resp.json()
    items = data.get("items", []) or []
    videos: list[dict] = []
    for it in items:
        vid = (it.get("id") or {}).get("videoId")
        sn = it.get("snippet") or {}
        if not vid:
            continue
        title = sn.get("title", "")
        if _is_likely_shorts(title):
            continue  # 제목에 #shorts/쇼츠 포함 시 제외
        thumbs = (sn.get("thumbnails") or {})
        thumb = (thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
        videos.append({
            "video_id": vid,
            "title": title,
            "channel": sn.get("channelTitle", ""),
            "thumbnail_url": thumb,
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
        if len(videos) >= max_results:
            break
    return videos, None


# ---------- 공개 API ----------
def get_cert_videos(cert_id: str, settings: Settings | None = None) -> dict:
    """F-11 endpoint 진입점. envelope dict를 반환한다."""
    settings = settings or get_settings()
    cert_name = _load_cert_name_map().get(cert_id)
    if not cert_name:
        return err_envelope("CERT_NOT_FOUND", f"cert_id={cert_id} 에 해당하는 자격증이 없습니다.")

    if not settings.youtube_api_key:
        return err_envelope(
            "YOUTUBE_API_KEY_MISSING",
            "서버에 YouTube API 키가 설정되지 않았습니다. 운영자에게 문의하세요.",
        )

    sb = _get_supabase_client(settings)
    table = settings.youtube_video_cache_table
    qv = settings.youtube_query_version
    ttl = settings.youtube_video_cache_ttl_days

    # 1. 캐시 조회
    cached = _read_cache(sb, table, cert_id)
    if cached and _cache_is_fresh(cached, ttl, qv):
        return ok_envelope({
            "cert_id": cert_id,
            "cert_name": cert_name,
            "videos": cached.get("videos", []) or [],
            "cache_hit": True,
            "fetched_at": cached.get("fetched_at"),
        })

    # 2. 외부 호출
    query = _build_search_query(cert_name)
    videos, error = _call_youtube_search(
        api_key=settings.youtube_api_key,
        query=query,
        max_results=settings.youtube_video_max_results,
    )

    if error == "quota_exceeded":
        # quota fallback — 만료 캐시라도 있으면 반환
        if cached:
            _write_cache(sb, table, cert_id, cert_name,
                         cached.get("search_query") or query,
                         cached.get("videos") or [],
                         qv, quota_exceeded=True)
            return ok_envelope({
                "cert_id": cert_id,
                "cert_name": cert_name,
                "videos": cached.get("videos", []) or [],
                "cache_hit": True,
                "fetched_at": cached.get("fetched_at"),
                "warning": "quota_exceeded_using_stale_cache",
            })
        return err_envelope(
            "YOUTUBE_QUOTA_EXCEEDED",
            "오늘 YouTube 검색 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
        )

    if error == "timeout":
        if cached:
            return ok_envelope({
                "cert_id": cert_id,
                "cert_name": cert_name,
                "videos": cached.get("videos", []) or [],
                "cache_hit": True,
                "fetched_at": cached.get("fetched_at"),
                "warning": "timeout_using_stale_cache",
            })
        return err_envelope("YOUTUBE_TIMEOUT", "YouTube API 응답이 지연되고 있습니다.")

    if error == "api_error":
        if cached:
            return ok_envelope({
                "cert_id": cert_id,
                "cert_name": cert_name,
                "videos": cached.get("videos", []) or [],
                "cache_hit": True,
                "fetched_at": cached.get("fetched_at"),
                "warning": "api_error_using_stale_cache",
            })
        return err_envelope("YOUTUBE_API_ERROR", "YouTube API 호출 중 오류가 발생했습니다.")

    # 3. 정상 응답 — 캐시 upsert
    _write_cache(sb, table, cert_id, cert_name, query, videos, qv)
    return ok_envelope({
        "cert_id": cert_id,
        "cert_name": cert_name,
        "videos": videos,
        "cache_hit": False,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    })
