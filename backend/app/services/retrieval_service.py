# File: retrieval_service.py
# Last Updated: 2026-05-15
# Content Hash: SHA256:TBD
# Role: evidence 검색 — Supabase certificates_vectors(primary) → 공인민간자격 카탈로그 → 로컬 candidates fallback
#
# Supabase가 미설정이거나 오류 시 cert_candidates.jsonl text_for_dense로 자동 폴백.
# match_certificates RPC 직접 호출 (supabase-py 2.30 호환, LangChain 우회).
# private_cert_catalog.json: 공인민간자격 정보자료집(2025) 파싱 결과 → 응시료·활용현황 로컬 조회.
# reserved: reranker, BM25 상시 사용은 별도 승인 전 구현하지 않는다.
from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

_PROJECT_ROOT = Path(__file__).parents[3]
_CANDIDATES_JSONL = _PROJECT_ROOT / "data/canonical/candidates/cert_candidates.jsonl"
_CERT_MASTER_CSV = _PROJECT_ROOT / "data/processed/master/cert_master.csv"
_PRIVATE_CATALOG_JSON = _PROJECT_ROOT / "data/index_ready/private_cert_catalog.json"

_NATIONAL_CATALOG_JSON = _PROJECT_ROOT / "data/index_ready/national_cert_catalog.json"
_GASANJEOM_INDEX_JSON = _PROJECT_ROOT / "data/index_ready/gasanjeom_index.json"

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


_DIFF_LABEL: dict[str, str] = {
    "1.0": "하 (쉬움)", "1": "하 (쉬움)",
    "1.5": "중하",
    "2.0": "중하", "2": "중하",
    "2.5": "중",
    "3.0": "중 (보통)", "3": "중 (보통)",
    "3.5": "중상",
    "4.0": "중상", "4": "중상",
    "4.5": "상",
    "5.0": "상 (어려움)", "5": "상 (어려움)",
}


def _parse_dense_sections(text: str) -> list[dict]:
    """text_for_dense를 섹션별로 분리해 evidence 목록으로 반환.

    합격률은 이미 UI에서 표시되므로 evidence에서 제외.
    난이도는 숫자 대신 라벨로 변환해서 표시.
    """
    results = []

    # 직무 · 역할
    m = re.search(r"관련 직무:\s*([^\.]+)", text)
    if m:
        results.append({"label": "직무 · 역할", "snippet": m.group(1).strip()[:300]})

    # 시험 정보: 난이도 라벨 + 합격률 + 연간 검정 횟수
    info_parts: list[str] = []
    dm = re.search(r"시험 난이도:\s*([0-9.]+)", text)
    if dm:
        raw = dm.group(1).rstrip(".")
        label = _DIFF_LABEL.get(raw, raw)
        info_parts.append(f"난이도: {label}")
    pm = re.search(r"3년 평균 합격률:\s*([0-9.]+)", text)
    if pm:
        info_parts.append(f"합격률: {int(round(float(pm.group(1))))}%")
    fm = re.search(r"연간 검정 횟수:\s*([^\.]+)", text)
    if fm:
        info_parts.append(f"연간 시험: {fm.group(1).strip()}")
    if info_parts:
        results.append({"label": "시험 정보", "snippet": " · ".join(info_parts)})

    # 시험 과목
    m = re.search(r"시험 과목:\s*([^\.]+)", text)
    if m:
        results.append({"label": "시험 과목", "snippet": m.group(1).strip()[:300]})

    if not results:
        results.append({"label": "자격증 개요", "snippet": text[:600]})
    return results


def _normalize_exam_row(row: dict) -> dict:
    """Supabase에서 온 '합격률·난이도' 섹션을 '시험 정보' 형식으로 정규화."""
    sec = (row.get("section_path") or [""])[0]
    if "합격률" not in sec and "난이도" not in sec:
        return row
    text = row.get("snippet", "")
    info_parts: list[str] = []
    dm = re.search(r"시험 난이도:\s*([0-9.]+)", text)
    if dm:
        raw = dm.group(1).rstrip(".")
        info_parts.append(f"난이도: {_DIFF_LABEL.get(raw, raw)}")
    pm = re.search(r"3년 평균 합격률:\s*([0-9.]+)", text)
    if pm:
        info_parts.append(f"합격률: {int(round(float(pm.group(1))))}%")
    fm = re.search(r"연간 검정 횟수:\s*([^\.]+)", text)
    if fm:
        info_parts.append(f"연간 시험: {fm.group(1).strip()}")
    if not info_parts:
        return row
    return {**row, "section_path": ["시험 정보"], "snippet": " · ".join(info_parts)}


def _bm25_chunk_fallback(cert_id: str, query_text: str) -> list[dict]:
    """text_for_dense를 문장 단위로 분할한 뒤 query token overlap 상위 5문장 반환.

    overlap > 0 이고 최소 20자 이상인 문장만 후보로 삼는다.
    결과가 없으면 빈 리스트를 반환하며, 이때 _candidate_fallback으로 재폴백한다.
    """
    cands = _load_candidates()
    cand = cands.get(cert_id)
    if not cand:
        return []
    text = (cand.get("text_for_dense") or "").strip()
    if not text:
        return []

    cert_name = cand.get("cert_name", "")

    # 문장 분할
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if s.strip()]

    # query 토큰 추출 (한글/영문/숫자)
    query_tokens = set(re.findall(r"[가-힣a-zA-Z0-9]+", query_text.lower()))
    if not query_tokens:
        return []

    # 각 문장에 overlap 점수 부여
    scored: list[tuple[float, str]] = []
    for sent in sentences:
        if len(sent) < 20:
            continue
        sent_tokens = set(re.findall(r"[가-힣a-zA-Z0-9]+", sent.lower()))
        if not sent_tokens:
            continue
        overlap = len(query_tokens & sent_tokens) / len(query_tokens)
        if overlap > 0:
            scored.append((overlap, sent))

    if not scored:
        return []

    # overlap 내림차순 정렬 후 상위 5개 선택
    scored.sort(key=lambda x: x[0], reverse=True)
    top_sentences = scored[:5]

    rows = []
    for i, (_, sent) in enumerate(top_sentences):
        rows.append({
            "doc_id": f"cand_{cert_id}",
            "chunk_id": f"cand_{cert_id}_kw{i}",
            "source_type": "candidate_keyword",
            "snippet": sent,
            "section_path": ["keyword_search"],
            "source_url": None,
            "cert_name": cert_name,
            "similarity": None,
        })
    return rows


def _candidate_fallback(cert_id: str) -> list[dict]:
    """cert_candidates.jsonl의 text_for_dense를 섹션별 evidence로 반환."""
    cands = _load_candidates()
    cand = cands.get(cert_id)
    if not cand:
        return []
    text = (cand.get("text_for_dense") or "").strip()
    if not text:
        return []

    cert_name = cand.get("cert_name", "")
    sections = _parse_dense_sections(text)
    rows = []
    for i, sec in enumerate(sections):
        rows.append({
            "doc_id": f"cand_{cert_id}",
            "chunk_id": f"cand_{cert_id}_sec{i}",
            "source_type": "candidate",
            "snippet": sec["snippet"],
            "section_path": [sec["label"]],
            "source_url": None,
            "cert_name": cert_name,
        })
    return rows


@lru_cache(maxsize=1)
def _load_private_catalog() -> dict[str, dict]:
    """공인민간자격 카탈로그 JSON 로드. cert_name 인덱스 반환."""
    if not _PRIVATE_CATALOG_JSON.exists():
        return {}
    try:
        with _PRIVATE_CATALOG_JSON.open(encoding="utf-8") as f:
            data = json.load(f)
        return data.get("index", {})
    except Exception:
        return {}


def _catalog_lookup(cert_name: str) -> list[dict]:
    """공인민간자격 카탈로그에서 cert_name 으로 evidence 목록 생성.
    정확 일치 → 부분 일치(공백 정규화) 순으로 시도."""
    index = _load_private_catalog()
    if not index:
        return []

    rec = index.get(cert_name)
    if not rec:
        # 공백·특수문자 정규화 후 양방향 부분 일치 탐색
        # cert_name이 key를 포함(예: "ITQ C급" ⊃ "ITQ") 또는 key가 cert_name을 포함
        norm = re.sub(r'[\s\(\)\[\]（）]', '', cert_name).lower()
        for key, val in index.items():
            key_norm = re.sub(r'[\s\(\)\[\]（）]', '', key).lower()
            if norm and key_norm and (norm in key_norm or key_norm in norm):
                rec = val
                break

    if not rec:
        return []

    rows: list[dict] = []
    found_name = rec.get("cert_name", cert_name)
    source_id = f"private_catalog_{re.sub(r'[^a-zA-Z0-9가-힣]', '_', found_name)}"

    def _row(section: str, snippet: str) -> dict:
        return {
            "doc_id": "private_cert_catalog_2025",
            "chunk_id": f"{source_id}_{section}",
            "source_type": "private_cert_catalog",
            "snippet": snippet,
            "section_path": [section],
            "source_url": None,
            "cert_name": found_name,
            "similarity": None,
        }

    # 응시료
    if rec.get("exam_fee"):
        rows.append(_row("응시료", f"응시료: {rec['exam_fee']}"))

    # 자격 활용 현황 (빈 줄 제거)
    usage_raw = rec.get("usage_status", "")
    if usage_raw:
        usage_clean = "\n".join(
            line for line in usage_raw.split("\n")
            if line.strip().replace("+", "").strip()
        )
        if usage_clean:
            rows.append(_row("자격 활용 현황", usage_clean))

    # 공인번호 · 주무부처 · 유효기간 (노이즈 값 제외)
    meta_parts = []
    if rec.get("gong_in_no"):
        meta_parts.append(f"공인번호: {rec['gong_in_no']}")
    if rec.get("ministry"):
        meta_parts.append(f"주무부처: {rec['ministry']}")
    validity = rec.get("validity", "")
    if validity and len(validity) < 40 and "직무" not in validity and "내용" not in validity:
        meta_parts.append(f"자격 유효기간: {validity}")
    if meta_parts:
        rows.append(_row("공인 정보", " · ".join(meta_parts)))

    # 응시 자격 (제한없음 이외만)
    eligibility = rec.get("eligibility", "")
    if eligibility and eligibility not in ("제한없음", "없음"):
        rows.append(_row("응시 자격", f"응시 자격: {eligibility}"))

    # 검정 현황 요약 (있으면)
    if rec.get("exam_history_summary"):
        rows.append(_row("검정 현황", rec["exam_history_summary"]))

    return rows


@lru_cache(maxsize=1)
def _load_national_catalog() -> dict[str, dict]:
    """국가자격 정보집 JSON 로드. cert_name 인덱스 반환."""
    if not _NATIONAL_CATALOG_JSON.exists():
        return {}
    try:
        with _NATIONAL_CATALOG_JSON.open(encoding="utf-8") as f:
            data = json.load(f)
        return data.get("index", {})
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _load_gasanjeom_index() -> dict[str, dict]:
    """공무원 가산점 인덱스 JSON 로드. cert_name → info dict 반환."""
    if not _GASANJEOM_INDEX_JSON.exists():
        return {}
    try:
        with _GASANJEOM_INDEX_JSON.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _gasanjeom_lookup(cert_id: str, cert_name: str, cert_grade_tier: str) -> list[dict]:
    """
    가산점 인덱스에서 cert_name으로 조회해 evidence row 반환.
    정확 매칭 → 부분 매칭 → grade tier 기반 fallback 순.
    """
    rows: list[dict] = []

    # ── 1. 정확 매칭 또는 부분 매칭 ──
    index = _load_gasanjeom_index()
    info: dict | None = index.get(cert_name) if cert_name else None

    if not info and cert_name:
        norm = re.sub(r'[\s\(\)\[\]（）]', '', cert_name).lower()
        for key, val in index.items():
            key_norm = re.sub(r'[\s\(\)\[\]（）]', '', key).lower()
            if norm and key_norm and (norm == key_norm or norm in key_norm or key_norm in norm):
                info = val
                break

    if info:
        serial_str = ", ".join(info.get("직렬", [])[:3]) or "-"
        rate7 = info.get("rate_7급", 0)
        rate9 = info.get("rate_9급", 0)
        if rate7 > 0:
            rate_text = f"7급 {rate7}%, 9급 {rate9}%"
        else:
            rate_text = f"9급 {rate9}%"
        rows.append({
            "chunk_id": f"gasanjeom_{cert_id}",
            "source_type": "gasanjeom",
            "section_path": ["가산점"],
            "snippet": (
                f"7·9급 기술직 공무원 가산점 항목 — {rate_text} "
                f"(직렬: {serial_str})"
            ),
            "similarity": 1.0,
            "source_url": None,
        })
        return rows

    # ── 2. grade tier 기반 fallback ──
    tier_map: dict[str, str] = {
        "4_기술사":   "해당 분야 기술사 — 7급·9급 각 5% 가산점 대상",
        "5_기능장":   "해당 분야 기능장 — 7급·9급 각 5% 가산점 대상",
        "3_기사":     "해당 분야 기사 — 7급 5%, 9급 3% 가산점 대상일 수 있음",
        "2_산업기사": "해당 분야 산업기사 — 7급·9급 각 3% 가산점 대상일 수 있음",
        "1_기능사":   "해당 분야 기능사 — 9급 3% 가산점 대상일 수 있음",
    }

    if cert_grade_tier and cert_grade_tier in tier_map:
        rows.append({
            "chunk_id": f"gasanjeom_inferred_{cert_id}",
            "source_type": "gasanjeom_inferred",
            "section_path": ["가산점"],
            "snippet": tier_map[cert_grade_tier],
            "similarity": None,
            "source_url": None,
        })

    return rows


def _national_catalog_lookup(cert_name: str) -> list[dict]:
    """국가자격 정보집에서 cert_name 으로 evidence 목록 생성.
    정확 일치 → 부분 일치(공백 정규화) 순으로 시도."""
    index = _load_national_catalog()
    if not index:
        return []

    rec = index.get(cert_name)
    if not rec:
        # 양방향 부분 일치: cert_name이 key를 포함하거나 key가 cert_name을 포함
        norm = re.sub(r'[\s\(\)\[\]（）]', '', cert_name).lower()
        for key, val in index.items():
            key_norm = re.sub(r'[\s\(\)\[\]（）]', '', key).lower()
            if norm and key_norm and (norm in key_norm or key_norm in norm):
                rec = val
                break

    if not rec:
        return []

    rows: list[dict] = []
    found_name = rec.get("cert_name", cert_name)
    source_id = f"national_catalog_{re.sub(r'[^a-zA-Z0-9가-힣]', '_', found_name)}"

    def _row(section: str, snippet: str) -> dict:
        return {
            "doc_id": "national_cert_catalog_2026",
            "chunk_id": f"{source_id}_{section}",
            "source_type": "national_cert_catalog",
            "snippet": snippet,
            "section_path": [section],
            "source_url": None,
            "cert_name": found_name,
            "similarity": None,
        }

    if rec.get("purpose"):
        rows.append(_row("도입목적", rec["purpose"]))

    if rec.get("career"):
        rows.append(_row("진로(자격활용)", f"진로(자격활용): {rec['career']}"))

    if rec.get("exam_fee"):
        rows.append(_row("응시료", f"응시료: {rec['exam_fee']}"))

    meta_parts = []
    if rec.get("agency"):
        meta_parts.append(f"시행기관: {rec['agency']}")
    if rec.get("ministry"):
        meta_parts.append(f"소관부처: {rec['ministry']}")
    if meta_parts:
        rows.append(_row("시행기관·소관부처", " · ".join(meta_parts)))

    return rows


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

    # cert_grade_tier: candidates에서 조회
    cands_all = _load_candidates()
    cert_grade_tier: str = cands_all.get(cert_id, {}).get("cert_grade_tier", "") or ""

    # 쿼리 텍스트: cert_name + 관련 도메인/직무
    parts = [cert_name] if cert_name else [cert_id]
    parts.extend(body.get("related_domains") or [])
    parts.extend(body.get("related_jobs") or [])
    query_text = " ".join(p for p in parts if p).strip() or "자격증 공식 안내"

    # 공인민간자격 카탈로그 조회 (cert_name 기반 직접 매핑)
    catalog_rows = _catalog_lookup(cert_name) if cert_name else []
    # 국가자격 정보집 카탈로그 조회
    national_rows = _national_catalog_lookup(cert_name) if cert_name else []
    # 공무원 가산점 조회
    gasanjeom_rows = _gasanjeom_lookup(cert_id, cert_name, cert_grade_tier)

    local_catalog_rows = national_rows + catalog_rows + gasanjeom_rows  # 국가자격 우선

    # 1. Supabase certificates_vectors (match_certificates RPC)
    db_rows = _search_supabase(cert_name, query_text, settings)
    if db_rows:
        db_rows = [_normalize_exam_row(r) for r in db_rows]
        combined = local_catalog_rows + db_rows
        return ok_envelope({"cert_id": cert_id, "evidence": combined, "source": "supabase"})

    # 2. 카탈로그만 있어도 반환
    if local_catalog_rows:
        cand_rows = _candidate_fallback(cert_id)
        combined = local_catalog_rows + cand_rows
        return ok_envelope({
            "cert_id": cert_id,
            "evidence": combined,
            "source": "catalog",
        })

    # 3. 로컬 cert_candidates — BM25 keyword chunk 우선, 없으면 전체 text_for_dense fallback
    rows = _bm25_chunk_fallback(cert_id, query_text)
    if not rows:
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
