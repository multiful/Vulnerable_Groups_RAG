# File: retrieval_service.py
# Last Updated: 2026-05-07
# Content Hash: SHA256:TBD
# Role: evidence 검색 — Supabase certificates_vectors(primary) → 로컬 candidates fallback
#
# Supabase가 미설정이거나 오류 시 cert_candidates.jsonl text_for_dense로 자동 폴백.
# match_certificates RPC 직접 호출 (supabase-py 2.30 호환, LangChain 우회).
# reserved: reranker, BM25 상시 사용은 별도 승인 전 구현하지 않는다.
from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

_PROJECT_ROOT = Path(__file__).parents[3]
_CANDIDATES_JSONL = _PROJECT_ROOT / "data/canonical/candidates/cert_candidates.jsonl"
_CERT_MASTER_CSV = _PROJECT_ROOT / "data/processed/master/cert_master.csv"

_SUPABASE_MATCH_RPC = "match_certificates"


@lru_cache(maxsize=1)
def _load_candidates() -> dict[str, dict]:
    """cert_id → candidate dict"""
    if not _CANDIDATES_JSONL.exists():
        return {}
    out: dict[str, dict] = {}
    with _CANDIDATES_JSONL.open(encoding="utf-8") as f:
        for line in f:
            if s := line.strip():
                c = json.loads(s)
                out[c["cert_id"]] = c
    return out


@lru_cache(maxsize=1)
def _load_cert_names() -> dict[str, str]:
    """cert_id → cert_name"""
    if not _CERT_MASTER_CSV.exists():
        return {}
    out: dict[str, str] = {}
    with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["cert_id"]] = r["cert_name"]
    return out


def _candidate_fallback(cert_id: str) -> list[dict]:
    """cert_candidates.jsonl의 text_for_dense를 로컬 evidence로 반환."""
    cands = _load_candidates()
    cand = cands.get(cert_id)
    if not cand:
        return []
    text = (cand.get("text_for_dense") or "").strip()
    if not text:
        return []
    return [{
        "doc_id": f"cand_{cert_id}",
        "chunk_id": f"cand_{cert_id}_dense",
        "source_type": "candidate",
        "snippet": text[:1500],
        "section_path": [],
        "source_url": None,
        "cert_name": cand.get("cert_name", ""),
    }]


def _supabase_configured(settings: Settings) -> bool:
    return bool(
        settings.supabase_url
        and settings.supabase_service_key
        and settings.supabase_service_key != "your_service_role_key_here"
    )


def _search_supabase(cert_name: str, query_text: str, settings: Settings) -> list[dict] | None:
    """Supabase match_certificates RPC 직접 호출. 실패 시 None 반환."""
    if not _supabase_configured(settings):
        return None
    try:
        from openai import OpenAI
        from supabase import create_client

        oai = OpenAI(api_key=settings.openai_api_key)
        emb_resp = oai.embeddings.create(
            model=settings.openai_embedding_model or "text-embedding-3-small",
            input=query_text,
        )
        query_vector: list[float] = emb_resp.data[0].embedding

        sb = create_client(settings.supabase_url, settings.supabase_service_key)
        res = sb.rpc(
            _SUPABASE_MATCH_RPC,
            {
                "query_embedding": query_vector,
                "filter_cert_name": cert_name or None,
                "match_count": settings.rag_top_k,
            },
        ).execute()

        rows = []
        for item in res.data or []:
            meta = item.get("metadata") or {}
            rows.append({
                "doc_id": str(meta.get("qual_id") or item.get("qual_id", "")),
                "chunk_id": str(item.get("id", "")),
                "source_type": "supabase_cert",
                "snippet": (item.get("content") or "")[:1500],
                "section_path": [meta.get("section_path", "")] if meta.get("section_path") else [],
                "source_url": meta.get("source_url") or None,
                "cert_name": item.get("name", ""),
                "similarity": item.get("similarity"),
            })
        return rows if rows else None
    except Exception:
        return None


def search_evidence(body: dict[str, Any], settings: Settings) -> dict[str, Any]:
    cert_id = body.get("cert_id")
    if not cert_id:
        return err_envelope("MISSING_REQUIRED_FIELD", "cert_id는 필수입니다.", {"field": "cert_id"})

    cert_id = str(cert_id)
    cert_names = _load_cert_names()
    cert_name = cert_names.get(cert_id, "")

    # 쿼리 텍스트: cert_name + 관련 도메인/직무
    parts = [cert_name] if cert_name else [cert_id]
    parts.extend(body.get("related_domains") or [])
    parts.extend(body.get("related_jobs") or [])
    query_text = " ".join(p for p in parts if p).strip() or "자격증 공식 안내"

    # 1. Supabase certificates_vectors (match_certificates RPC)
    rows = _search_supabase(cert_name, query_text, settings)
    if rows:
        return ok_envelope({"cert_id": cert_id, "evidence": rows, "source": "supabase"})

    # 2. 로컬 cert_candidates text_for_dense fallback
    rows = _candidate_fallback(cert_id)
    source_note = (
        "Supabase 미연결 — cert_candidates text_for_dense를 근거로 사용합니다."
        if not _supabase_configured(settings)
        else "Supabase에서 결과 없음 — cert_candidates text_for_dense를 근거로 사용합니다."
    )
    return ok_envelope({
        "cert_id": cert_id,
        "evidence": rows,
        "source": "local_candidates",
        "note": source_note,
    })
