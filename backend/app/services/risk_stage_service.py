# File: risk_stage_service.py
# Last Updated: 2026-07-05
# Content Hash: SHA256:TBD
# Role: 위험군 단계 목록 조회 — risk_stage_master.csv 기반
#
# NOTE (CLAUDE.md §6):
#   - 1단계 = 고립위험청년 (가장 경미) ~ 4단계 = 은둔청년 (가장 심각)
#   - risk_0005(구 은둔군, 구 5단계 체계)는 백엔드에 비활성 보존, 프론트엔드 미사용
#   - 2~4단계 세부 의미는 CSV의 description 그대로 노출한다.
#     "확정 전 임의 정의 금지" 원칙에 따라 CSV 값 외 추가 정의를 삽입하지 않는다.

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from backend.app.schemas.envelope import ok_envelope

_RISK_MASTER = Path(__file__).parents[3] / "data/processed/master/risk_stage_master.csv"
_RISK_TO_ROADMAP = Path(__file__).parents[3] / "data/canonical/relations/risk_stage_to_roadmap_stage.csv"


@lru_cache(maxsize=1)
def _load() -> list[dict]:
    if not _RISK_MASTER.exists():
        return []
    with _RISK_MASTER.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _load_risk_to_roadmap() -> dict[str, str]:
    if not _RISK_TO_ROADMAP.exists():
        return {}
    with _RISK_TO_ROADMAP.open(encoding="utf-8-sig") as f:
        return {r["risk_stage_id"]: r["roadmap_stage_id"] for r in csv.DictReader(f)}


def stages_list() -> dict:
    rows = _load()
    r2rm = _load_risk_to_roadmap()
    stages = [
        {
            "id": r["risk_stage_id"],
            "name": r["risk_stage_name"],
            "description": r.get("description", ""),
            "order": int(r.get("risk_stage_order", 0)),
            "starting_roadmap_stage_id": r2rm.get(r["risk_stage_id"]),
        }
        for r in sorted(rows, key=lambda x: int(x.get("risk_stage_order", 0)))
    ]
    return ok_envelope({"stages": stages, "total": len(stages)})
