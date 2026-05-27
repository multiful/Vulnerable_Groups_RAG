# File: support_bundle_service.py
# Last Updated: 2026-05-26
# Content Hash: SHA256:TBD
# Role: 위험군 × 도메인/직무 기반 취업지원 자원 번들 조회 (F-17)
# 위험군 단계별 게이팅:
#   1단계 → job_fair 만 (partial)  ← hiring(기업전용) 대신 job_fair(공공)
#   2~3단계 → job_fair + training (standard)
#   4~5단계 → job_fair + training + job_cafe + process_eval (full)
from __future__ import annotations

import logging
from typing import Any

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope

logger = logging.getLogger(__name__)

# 도메인 taxonomy → NCS 1차 분류 매핑
# training_service.NCS_LEVEL1_CODES 기준
_DOMAIN_TO_NCS: dict[str, str] = {
    "데이터/AI":      "정보통신",
    "소프트웨어개발": "정보통신",
    "IT/정보통신":    "정보통신",
    "금융/핀테크":    "금융/보험",
    "건설/토목":      "건설",
    "기계/제조":      "기계",
    "화학/바이오":    "화학/바이오",
    "전기/전자":      "전기/전자",
    "경영/사무":      "경영/회계/사무",
    "보건/의료":      "보건/의료",
    "사회복지":       "사회복지/종교",
    "교육":           "교육/자연/사회과학",
    "환경/에너지":    "환경/에너지/안전",
    "문화/예술/디자인": "문화/예술/디자인/방송",
    "영업/판매":      "영업판매",
    "농림어업":       "농림어업",
    "음식서비스":     "음식서비스",
    "이용/숙박/여행": "이용/숙박/여행/오락/스포츠",
}

_SUPPORT_LEVEL: dict[int, str] = {
    1: "partial",
    2: "standard",
    3: "standard",
    4: "full",
    5: "full",
}

_RESOURCE_TYPES: dict[str, list[str]] = {
    "partial":  ["job_fair"],
    "standard": ["job_fair", "training"],
    "full":     ["job_fair", "training", "job_cafe", "process_eval"],
}

_RESOURCE_LABELS: dict[str, str] = {
    "job_fair":     "채용행사",
    "training":     "훈련과정",
    "job_cafe":     "일자리카페",
    "process_eval": "과정평가형 자격",
}


def _risk_num(risk_stage_id: str) -> int:
    """risk_0001 → 1 형태로 파싱."""
    try:
        return int(risk_stage_id.split("_")[-1])
    except (ValueError, IndexError):
        return 3  # 기본값 standard


def _build_bundle_entry(resource_type: str, items: list[dict], error: str | None = None) -> dict:
    entry: dict[str, Any] = {
        "resource_type": resource_type,
        "label":         _RESOURCE_LABELS.get(resource_type, resource_type),
        "color_theme":   "teal",
        "count":         len(items),
        "items":         items,
    }
    if error:
        entry["error"] = error
    return entry


def _fetch_job_fair(
    settings: Settings,
    domain_name: str | None,
    region: str | None,
) -> tuple[list[dict], str | None]:
    from backend.app.services.job_fair_service import get_job_fairs_by_domain, get_job_fairs

    try:
        if domain_name:
            resp = get_job_fairs_by_domain(settings, domain_name, region=region, page_size=5)
        else:
            resp = get_job_fairs(settings, region=region, page_size=5)
    except Exception as e:
        logger.warning("support_bundle job_fair error: %s", e)
        return [], "채용행사 조회 중 오류가 발생했습니다."

    if not resp.get("success"):
        err = resp.get("error", {})
        return [], err.get("message") if isinstance(err, dict) else str(err)

    return resp.get("data", {}).get("events", []), None


def _fetch_training(
    settings: Settings,
    domain_name: str | None,
    region: str | None,
) -> tuple[list[dict], str | None]:
    from backend.app.services.training_service import get_training_courses

    ncs_category = _DOMAIN_TO_NCS.get(domain_name or "", None) if domain_name else None

    try:
        resp = get_training_courses(
            settings,
            region=region,
            ncs_category=ncs_category,
            page_size=5,
        )
    except Exception as e:
        logger.warning("support_bundle training error: %s", e)
        return [], "훈련과정 조회 중 오류가 발생했습니다."

    if not resp.get("success"):
        err = resp.get("error", {})
        return [], err.get("message") if isinstance(err, dict) else str(err)

    return resp.get("data", {}).get("courses", [])[:5], None


def _fetch_job_cafe(
    settings: Settings,
    region: str | None,
) -> tuple[list[dict], str | None]:
    from backend.app.services.seoul_service import get_job_cafes

    gu: str | None = None
    # region이 "서울 강남구" 형태면 구만 추출, 아니면 None으로 전체 조회
    if region and "구" in region:
        for part in region.split():
            if part.endswith("구"):
                gu = part
                break

    try:
        resp = get_job_cafes(settings, gu=gu)
    except Exception as e:
        logger.warning("support_bundle job_cafe error: %s", e)
        return [], "일자리카페 조회 중 오류가 발생했습니다."

    if not resp.get("success"):
        err = resp.get("error", {})
        return [], err.get("message") if isinstance(err, dict) else str(err)

    return resp.get("data", {}).get("cafes", [])[:5], None


def _fetch_process_eval(settings: Settings) -> tuple[list[dict], str | None]:
    from backend.app.services.training_service import get_process_eval_courses

    # API 폐지 이후 graceful 처리 — URL 안내 카드 반환
    try:
        resp = get_process_eval_courses(settings)
        data = resp.get("data", {})
        info = {
            "label": data.get("note", "과정평가형 자격 — 교육 이수로 취득"),
            "url":   data.get("qnet_url", ""),
            "link_label": data.get("qnet_label", "Q-Net 과정평가형 바로가기"),
        }
        return [info], None
    except Exception as e:
        logger.warning("support_bundle process_eval error: %s", e)
        return [], "과정평가형 자격 정보를 불러오지 못했습니다."


def get_support_bundle(
    settings: Settings,
    risk_stage_id: str,
    domain_id: str | None = None,
    domain_name: str | None = None,
    job_ids: list[str] | None = None,
    job_names: list[str] | None = None,
    cert_ids: list[str] | None = None,
    region: str | None = None,
) -> dict:
    """
    GET /api/v1/support/bundle
    위험군 단계에 따라 취업지원 자원을 번들로 조회한다.
    """
    if not risk_stage_id:
        return err_envelope("MISSING_REQUIRED_FIELD", "risk_stage_id 필요")

    rnum = _risk_num(risk_stage_id)
    if rnum not in range(1, 6):
        return err_envelope("INVALID_INPUT", f"risk_stage_id '{risk_stage_id}'는 유효하지 않습니다.")

    level = _SUPPORT_LEVEL.get(rnum, "standard")
    resource_types = _RESOURCE_TYPES[level]
    bundles: list[dict] = []

    for rtype in resource_types:
        if rtype == "job_fair":
            items, error = _fetch_job_fair(settings, domain_name, region)
        elif rtype == "training":
            items, error = _fetch_training(settings, domain_name, region)
        elif rtype == "job_cafe":
            items, error = _fetch_job_cafe(settings, region)
        elif rtype == "process_eval":
            items, error = _fetch_process_eval(settings)
        else:
            items, error = [], None

        bundles.append(_build_bundle_entry(rtype, items, error))

    return ok_envelope({
        "risk_stage_id":  risk_stage_id,
        "support_level":  level,
        "resource_types": resource_types,
        "bundles":        bundles,
    })
