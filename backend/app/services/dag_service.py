# File: dag_service.py
# Last Updated: 2026-05-07
# Content Hash: SHA256:TBD
# Role: cert_to_cert_relation.csv 기반 DAG 조회 — 선행/후행 자격증 경로 반환
from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.schemas.envelope import err_envelope, ok_envelope

_PROJECT_ROOT = Path(__file__).parents[3]
_RELATION_CSV = _PROJECT_ROOT / "data/canonical/relations/cert_to_cert_relation.csv"
_CANDIDATES_JSONL = _PROJECT_ROOT / "data/canonical/candidates/cert_candidates.jsonl"


@lru_cache(maxsize=1)
def _load_relations() -> list[dict]:
    if not _RELATION_CSV.exists():
        return []
    with _RELATION_CSV.open(encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r.get("is_active", "True") == "True"]


@lru_cache(maxsize=1)
def _load_cert_info() -> dict[str, dict]:
    """cert_id → {cert_name, cert_grade_tier, primary_domain}"""
    if not _CANDIDATES_JSONL.exists():
        return {}
    out: dict[str, dict] = {}
    with _CANDIDATES_JSONL.open(encoding="utf-8") as f:
        for line in f:
            if s := line.strip():
                c = json.loads(s)
                out[c["cert_id"]] = {
                    "cert_id": c["cert_id"],
                    "cert_name": c.get("cert_name", c["cert_id"]),
                    "cert_grade_tier": c.get("cert_grade_tier") or "",
                    "primary_domain": c.get("primary_domain") or "",
                    "avg_pass_rate": _extract_pass_rate(c.get("text_for_dense", "")),
                }
    return out


def _extract_pass_rate(text: str) -> float | None:
    import re
    m = re.search(r"3년 평균 합격률:\s*([\d.]+)%", text)
    return float(m.group(1)) if m else None


_RELATION_LABEL = {
    "prerequisite": "필수 선행",
    "recommended_prior": "선행 권장",
    "next_step": "다음 단계",
}


def get_related_certs(cert_id: str) -> dict[str, Any]:
    """cert_id 기준 선행/후행 자격증 반환."""
    if not cert_id:
        return err_envelope("MISSING_REQUIRED_FIELD", "cert_id는 필수입니다.")

    relations = _load_relations()
    cert_info = _load_cert_info()

    def enrich(cid: str, rel_type: str, evidence: str) -> dict:
        info = cert_info.get(cid, {"cert_id": cid, "cert_name": cid, "cert_grade_tier": "", "primary_domain": "", "avg_pass_rate": None})
        return {
            **info,
            "relation_type": rel_type,
            "relation_label": _RELATION_LABEL.get(rel_type, rel_type),
            "reasoning_evidence": evidence,
        }

    # 이 cert가 to인 경우 → 선행(나보다 먼저 딸 것들)
    predecessors = [
        enrich(r["from_cert_id"], r["relation_type"], r.get("reasoning_evidence", ""))
        for r in relations
        if r["to_cert_id"] == cert_id
    ]

    # 이 cert가 from인 경우 → 후행(나를 딴 후 갈 것들)
    successors = [
        enrich(r["to_cert_id"], r["relation_type"], r.get("reasoning_evidence", ""))
        for r in relations
        if r["from_cert_id"] == cert_id
    ]

    current = cert_info.get(cert_id, {"cert_id": cert_id, "cert_name": cert_id})

    return ok_envelope({
        "cert_id": cert_id,
        "cert_name": current.get("cert_name", cert_id),
        "predecessors": predecessors,
        "successors": successors,
        "has_path": bool(predecessors or successors),
    })
