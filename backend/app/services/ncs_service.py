# File: ncs_service.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 항목 10 — NCS 능력단위별 자격 종목 조회 (cert_ncs_mapping.csv + cert_master.csv 기반)
#
# GET /api/v1/ncs/certs?ncs_code=XX  → NCS ID 또는 대직무코드로 연관 자격증 목록 반환
# GET /api/v1/ncs/list                → NCS 코드 목록 (검색용)
from __future__ import annotations

import csv
import logging
from functools import lru_cache
from pathlib import Path

from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

_PROJECT_ROOT  = Path(__file__).parents[3]
_CERT_NCS_MAP  = _PROJECT_ROOT / "data/canonical/relations/cert_ncs_mapping.csv"
_CERT_MASTER   = _PROJECT_ROOT / "data/processed/master/cert_master.csv"
_NCS_MASTER    = _PROJECT_ROOT / "data/processed/master/ncs_master.csv"


@lru_cache(maxsize=1)
def _load_cert_ncs_map() -> dict[str, list[str]]:
    """ncs_id → [cert_id, ...] 역방향 인덱스"""
    if not _CERT_NCS_MAP.exists():
        return {}
    idx: dict[str, list[str]] = {}
    with _CERT_NCS_MAP.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("is_active", "True").lower() == "false":
                continue
            ncs = r["ncs_id"]
            idx.setdefault(ncs, []).append(r["cert_id"])
    return idx


@lru_cache(maxsize=1)
def _load_cert_map() -> dict[str, dict]:
    """cert_id → cert row dict"""
    if not _CERT_MASTER.exists():
        return {}
    out: dict[str, dict] = {}
    with _CERT_MASTER.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["cert_id"]] = r
    return out


@lru_cache(maxsize=1)
def _load_ncs_list() -> list[dict]:
    """전체 NCS 목록"""
    if not _NCS_MASTER.exists():
        return []
    out = []
    with _NCS_MASTER.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out.append({
                "ncs_id":          r["ncsID"],
                "major_code":      r["대직무코드"],
                "major_name":      r["대직무분류"],
                "mid_code":        r["중직무코드"],
                "mid_name":        r["중직무분류"],
                "minor_code":      r.get("소직무코드", ""),
                "minor_name":      r.get("소직무분류", ""),
                "normalized_key":  r.get("normalized_key", ""),
            })
    return out


def get_certs_by_ncs(
    ncs_id: str | None = None,
    major_code: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 30,
) -> dict:
    """
    NCS 코드 또는 대직무코드, 키워드로 연관 자격증 조회.
    우선순위: ncs_id 직접 조회 > major_code > keyword 텍스트 검색.
    """
    cert_ncs_idx = _load_cert_ncs_map()
    cert_map     = _load_cert_map()
    ncs_list     = _load_ncs_list()

    # 1) ncs_id 직접 매칭
    if ncs_id:
        cert_ids = cert_ncs_idx.get(ncs_id, [])
        matched_ncs = [n for n in ncs_list if n["ncs_id"] == ncs_id]
        ncs_label = matched_ncs[0]["minor_name"] if matched_ncs else ncs_id

    # 2) major_code (대직무코드) — 해당 코드의 모든 ncs 합산
    elif major_code:
        relevant_ncs = [n["ncs_id"] for n in ncs_list if n["major_code"] == major_code]
        cert_ids_set: set[str] = set()
        for nid in relevant_ncs:
            cert_ids_set.update(cert_ncs_idx.get(nid, []))
        cert_ids = list(cert_ids_set)
        major_rows = [n for n in ncs_list if n["major_code"] == major_code]
        ncs_label = major_rows[0]["major_name"] if major_rows else major_code

    # 3) keyword 텍스트 매칭
    elif keyword:
        kl = keyword.lower()
        relevant_ncs = [
            n["ncs_id"] for n in ncs_list
            if kl in n["major_name"].lower()
            or kl in n["mid_name"].lower()
            or kl in n.get("minor_name", "").lower()
            or kl in n.get("normalized_key", "").lower()
        ]
        cert_ids_set = set()
        for nid in relevant_ncs:
            cert_ids_set.update(cert_ncs_idx.get(nid, []))
        cert_ids = list(cert_ids_set)
        ncs_label = keyword
    else:
        return err_envelope("PARAM_MISSING", "ncs_id, major_code, 또는 keyword 중 하나가 필요합니다.")

    total = len(cert_ids)
    start = (page - 1) * page_size
    paged_ids = cert_ids[start: start + page_size]

    certs = []
    for cid in paged_ids:
        row = cert_map.get(cid)
        if not row:
            continue
        certs.append({
            "cert_id":          cid,
            "cert_name":        row.get("cert_name", ""),
            "cert_grade_tier":  row.get("cert_grade_tier", ""),
            "issuer":           row.get("issuer", ""),
            "avg_pass_rate_3yr": _safe_float(row.get("avg_pass_rate_3yr")),
            "primary_domain":   row.get("primary_domain", ""),
        })

    # 합격률 기준 정렬 (높을수록 접근성 좋음)
    certs.sort(key=lambda c: -(c["avg_pass_rate_3yr"] or 0))

    return ok_envelope({
        "query": {
            "ncs_id":     ncs_id,
            "major_code": major_code,
            "keyword":    keyword,
            "ncs_label":  ncs_label,
        },
        "certs":     certs,
        "total":     total,
        "page":      page,
        "page_size": page_size,
    })


def get_ncs_list(keyword: str | None = None) -> dict:
    """NCS 코드 목록 조회 (자격증 검색 드롭다운용)."""
    ncs = _load_ncs_list()
    if keyword:
        kl = keyword.lower()
        ncs = [
            n for n in ncs
            if kl in n["major_name"].lower()
            or kl in n["mid_name"].lower()
            or kl in n.get("minor_name", "").lower()
        ]
    return ok_envelope({"ncs_list": ncs, "total": len(ncs)})


def _safe_float(v: str | None) -> float | None:
    if not v:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
