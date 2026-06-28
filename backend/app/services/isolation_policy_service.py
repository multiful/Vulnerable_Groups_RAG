# File: isolation_policy_service.py
# Last Updated: 2026-06-25
# Content Hash: SHA256:TBD
# Role: 고립군 청년 군집별 맞춤 정책 추천 오케스트레이션
#
# 파이프라인:
#   군집 분류 (1~4단계) → 서비스 매트릭스 필터 → API 병렬 호출 → 결과 조립
#
# 서비스 매트릭스 (이미지 "지원 대상 유형 및 지원 목표에 따른 핵심 서비스.png" 기준):
#   ✅=해당(보라색), ❌=미해당(흰색)
#
#   카테고리              | 1단계 | 2단계 | 3단계 | 4단계
#   ─────────────────────|──────|──────|──────|──────
#   자기이해및심리상담    |  ✅  |  ✅  |  ✅  |  ✅
#   치유적관계형성        |  ❌  |  ✅  |  ✅  |  ✅
#   일경험및사회활동      |  ✅  |  ✅  |  ❌  |  ❌
#   사후관리              |  ✅  |  ✅  |  ✅  |  ✅
#   경제생계주거지원      |  ✅  |  ✅  |  ✅  |  ✅
#   가족지원              |  ✅  |  ✅  |  ✅  |  ✅
#   통합된삶              |  ✅  |  ❌  |  ❌  |  ❌
#
# 군집 레이블:
#   1 = 고립위험청년
#   2 = 활동형고립청년
#   3 = 활동제한형고립청년
#   4 = 은둔청년
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from backend.app.core.config import Settings
from backend.app.schemas.envelope import err_envelope, ok_envelope
from backend.app.services.cluster_service_matrix import (
    CLUSTER_ACTIVATION,
    CLUSTER_TO_RISK_ID,
    DIDIM_SERVICES,
    get_active_services,
    get_inactive_services,
)

logger = logging.getLogger(__name__)

# ── 군집 메타 ───────────────────────────────────────────────────────────────
CLUSTER_META: dict[str, dict] = {
    "1": {
        "label":       "고립위험청년",
        "description": "사회적 관계망이 약화되고 있으나 일부 활동이 가능한 상태",
        "direction":   "자기이해와 사회참여 강화로 고립 예방",
    },
    "2": {
        "label":       "활동형고립청년",
        "description": "신체적 활동은 하지만 의미 있는 사회적 관계가 없는 상태",
        "direction":   "치유적 관계형성과 일 경험을 통한 사회통합",
    },
    "3": {
        "label":       "활동제한형고립청년",
        "description": "경제·환경적 제약으로 외부 활동이 어려운 상태",
        "direction":   "경제·주거 안정화와 치유적 관계형성 지원",
    },
    "4": {
        "label":       "은둔청년",
        "description": "사회적 관계망 거의 단절, 자기관리 어려움, 외출 최소화 상태",
        "direction":   "치유적 관계형성과 단계적 사회복귀 지원",
    },
}

# ── 서비스 매트릭스 ─────────────────────────────────────────────────────────
# True = 해당(보라색), False = 미해당(흰색)
CLUSTER_SERVICE_MATRIX: dict[str, dict[str, bool]] = {
    "1": {  # 고립위험청년
        "자기이해및심리상담": True,
        "치유적관계형성":     False,
        "일경험및사회활동":   True,
        "사후관리":          True,
        "경제생계주거지원":   True,
        "가족지원":          True,
        "통합된삶":          True,
    },
    "2": {  # 활동형고립청년
        "자기이해및심리상담": True,
        "치유적관계형성":     True,
        "일경험및사회활동":   True,
        "사후관리":          True,
        "경제생계주거지원":   True,
        "가족지원":          True,
        "통합된삶":          False,
    },
    "3": {  # 활동제한형고립청년
        "자기이해및심리상담": True,
        "치유적관계형성":     True,
        "일경험및사회활동":   False,
        "사후관리":          True,
        "경제생계주거지원":   True,
        "가족지원":          True,
        "통합된삶":          False,
    },
    "4": {  # 은둔청년
        "자기이해및심리상담": True,
        "치유적관계형성":     True,
        "일경험및사회활동":   False,
        "사후관리":          True,
        "경제생계주거지원":   True,
        "가족지원":          True,
        "통합된삶":          False,
    },
}

# ── 카테고리 표시 정보 ───────────────────────────────────────────────────────
CATEGORY_META: dict[str, dict] = {
    "자기이해및심리상담": {
        "label":    "자기이해 및 심리상담",
        "icon":     "🧠",
        "desc":     "자기이해 워크숍, 심리상담, 정신건강 지원",
        "priority": 1,
    },
    "치유적관계형성": {
        "label":    "치유적 관계형성",
        "icon":     "🤝",
        "desc":     "사회적 관계 회복 프로그램, 자조모임, 관계형성 지원",
        "priority": 2,
    },
    "일경험및사회활동": {
        "label":    "일 경험 및 사회활동",
        "icon":     "💼",
        "desc":     "일경험 프로그램, 정부지원 일자리, 사회활동 참여",
        "priority": 3,
    },
    "사후관리": {
        "label":    "사후관리",
        "icon":     "📋",
        "desc":     "지속적 모니터링, 지역 기반 상담, 연계 관리",
        "priority": 4,
    },
    "경제생계주거지원": {
        "label":    "경제·생계·주거지원",
        "icon":     "🏠",
        "desc":     "생계급여, 긴급복지, 주거지원, 생활비 지원",
        "priority": 5,
    },
    "가족지원": {
        "label":    "가족지원",
        "icon":     "👨‍👩‍👧",
        "desc":     "가족상담, 가족교육, 보호자 상담, 가족관계 회복",
        "priority": 6,
    },
    "통합된삶": {
        "label":    "통합된 삶 (취업연계)",
        "icon":     "🌟",
        "desc":     "사회복귀 이후 취업·채용정보 연계",
        "priority": 7,
    },
}


def _active_categories(cluster_id: str) -> list[str]:
    """군집 ID → 활성 서비스 카테고리 목록 (보라색 칸만)."""
    matrix = CLUSTER_SERVICE_MATRIX.get(cluster_id, {})
    return [cat for cat, active in matrix.items() if active]


def _fetch_category_items(
    settings: Settings,
    category: str,
    region: str | None,
    page_size: int,
) -> tuple[str, list[dict], str | None]:
    """
    단일 카테고리에 대한 API 조회.
    반환: (category, items, error_message | None)
    """
    from backend.app.services import (
        welfare_central_service,
        welfare_local_service,
        family_center_service,
        gender_facility_service,
        worknet_govt_jobs_service,
    )

    items: list[dict] = []
    error: str | None = None

    try:
        if category == "자기이해및심리상담":
            # 1순위: 중앙부처복지 (심리상담, 정신건강)
            r = welfare_central_service.get_welfare_services(
                settings, service_category=category, region=region, page_size=page_size,
            )
            if r.get("success"):
                items.extend(r["data"].get("items", []))
            # 2순위: 여성가족시설 (청소년상담복지센터)
            r2 = gender_facility_service.get_gender_facilities(
                settings, service_category=category, region=region, page_size=max(1, page_size - len(items)),
            )
            if r2.get("success"):
                items.extend(r2["data"].get("items", []))

        elif category == "치유적관계형성":
            # 1순위: 지자체복지 (사회적 관계 회복, 자조모임)
            r = welfare_local_service.get_local_welfare_services(
                settings, service_category=category, region=region, page_size=page_size,
            )
            if r.get("success"):
                items.extend(r["data"].get("items", []))
            # 2순위: 여성가족시설
            r2 = gender_facility_service.get_gender_facilities(
                settings, service_category=category, region=region, page_size=max(1, page_size - len(items)),
            )
            if r2.get("success"):
                items.extend(r2["data"].get("items", []))

        elif category == "일경험및사회활동":
            # 워크넷 정부지원일자리 참여자모집
            r = worknet_govt_jobs_service.get_govt_job_recruitments(
                settings, region=region, keyword="청년도전", page_size=page_size,
            )
            if r.get("success"):
                items.extend(r["data"].get("items", []))

        elif category == "사후관리":
            # 지자체복지 (지역 기반 상담)
            r = welfare_local_service.get_local_welfare_services(
                settings, service_category=category, region=region, page_size=page_size,
            )
            if r.get("success"):
                items.extend(r["data"].get("items", []))

        elif category == "경제생계주거지원":
            # 1순위: 중앙부처복지 (생계급여, 긴급복지, 주거)
            r = welfare_central_service.get_welfare_services(
                settings, service_category=category, region=region, page_size=page_size,
            )
            if r.get("success"):
                items.extend(r["data"].get("items", []))
            # 2순위: 지자체복지 (지자체 긴급지원)
            r2 = welfare_local_service.get_local_welfare_services(
                settings, service_category=category, region=region, page_size=max(1, page_size - len(items)),
            )
            if r2.get("success"):
                items.extend(r2["data"].get("items", []))

        elif category == "가족지원":
            # 1순위: 건강가정지원센터
            r = family_center_service.get_family_centers(
                settings, region=region, page_size=page_size,
            )
            if r.get("success"):
                items.extend(r["data"].get("items", []))
            # 2순위: 여성가족시설 (가족지원센터)
            r2 = gender_facility_service.get_gender_facilities(
                settings, service_category=category, region=region, page_size=max(1, page_size - len(items)),
            )
            if r2.get("success"):
                items.extend(r2["data"].get("items", []))

        elif category == "통합된삶":
            # 기존 jobs_service 활용 (워크넷 채용정보)
            from backend.app.services.jobs_service import get_hiring_jobs
            r = get_hiring_jobs(settings, keyword="청년", region=region, display=page_size)
            if r.get("success"):
                items.extend(r["data"].get("jobs", []))

    except Exception as e:
        logger.warning("isolation_policy fetch error [%s]: %s", category, e)
        error = f"{category} 조회 중 오류가 발생했습니다."

    return category, items[:page_size], error


def get_isolation_policy_bundle(
    settings: Settings,
    cluster_id: str,
    region: str | None = None,
    items_per_category: int = 3,
) -> dict:
    """
    고립군 청년 군집별 맞춤 정책 추천 번들.

    Args:
        cluster_id: '1'~'4' (고립위험청년~은둔청년)
        region: 거주 지역 이름 (지자체 서비스 필터링용)
        items_per_category: 카테고리당 서비스 수 (기본 3)

    Returns:
        {
          "cluster_id": "3",
          "cluster_meta": {...},
          "active_categories": ["자기이해및심리상담", ...],
          "excluded_categories": ["일경험및사회활동", ...],
          "bundles": [
            {
              "category": "자기이해및심리상담",
              "label": "자기이해 및 심리상담",
              "icon": "🧠",
              "count": 3,
              "items": [...],
            },
            ...
          ]
        }
    """
    if cluster_id not in CLUSTER_SERVICE_MATRIX:
        return err_envelope("INVALID_INPUT", f"cluster_id '{cluster_id}'는 유효하지 않습니다. (1~4)")

    active_cats = _active_categories(cluster_id)
    excluded_cats = [
        cat for cat, active in CLUSTER_SERVICE_MATRIX[cluster_id].items() if not active
    ]

    # 카테고리별 병렬 API 호출
    bundles: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(len(active_cats), 4)) as pool:
        futures = {
            pool.submit(
                _fetch_category_items,
                settings, cat, region, items_per_category,
            ): cat
            for cat in active_cats
        }
        results: dict[str, tuple[list[dict], str | None]] = {}
        for fut in as_completed(futures):
            cat = futures[fut]
            try:
                _, items, error = fut.result()
                results[cat] = (items, error)
            except Exception as e:
                logger.warning("isolation_policy executor error [%s]: %s", cat, e)
                results[cat] = ([], str(e))

    # 우선순위 순서로 정렬해서 bundles 조립
    for cat in sorted(active_cats, key=lambda c: CATEGORY_META.get(c, {}).get("priority", 99)):
        items, error = results.get(cat, ([], None))
        meta = CATEGORY_META.get(cat, {})
        entry: dict[str, Any] = {
            "category": cat,
            "label":    meta.get("label", cat),
            "icon":     meta.get("icon", ""),
            "desc":     meta.get("desc", ""),
            "count":    len(items),
            "items":    items,
        }
        if error:
            entry["error"] = error
        bundles.append(entry)

    cluster_meta = CLUSTER_META.get(cluster_id, {})

    return ok_envelope({
        "cluster_id":          cluster_id,
        "cluster_meta":        cluster_meta,
        "region":              region,
        "active_categories":   active_cats,
        "excluded_categories": excluded_cats,
        "excluded_reason":     (
            "서비스 매트릭스에서 해당 군집에 필요하지 않은 서비스로 분류된 항목"
            if excluded_cats else ""
        ),
        "bundles":             bundles,
        "total_items":         sum(b["count"] for b in bundles),
    })


def get_didim_service_hub(
    settings: Settings,
    cluster_id: str,
    region: str | None = None,
    survey_summary: str | None = None,
    with_llm_explanation: bool = True,
) -> dict:
    """
    고립군 진단 → DIDIM 전체 서비스 통합 허브.

    기존 자격증·채용·훈련·일자리카페 등 didim.life의 모든 서비스를
    군집(cluster_id 1~4) 기반으로 활성/비활성 분류하여 반환.

    파이프라인:
        cluster_id
          ↓ cluster_service_matrix.CLUSTER_ACTIVATION
        active_services / inactive_services (하드코딩 결정)
          ↓ llm_isolation_service (선택)
        LLM 설명 (왜 이 서비스가 지금 맞는가/맞지 않는가)
          ↓ action_service.get_isolation_action
        오늘의 행동 1가지

    Args:
        cluster_id: '1'~'4'
        region: 거주 지역
        survey_summary: 설문 요약 (LLM 개인화용, 선택)
        with_llm_explanation: LLM 설명 생성 여부 (기본 True)

    Returns:
        {
          "cluster_id": "2",
          "cluster_meta": {...},
          "active_services": [{id, name, category, frontend_path, explanation}, ...],
          "inactive_services": [{id, name, category, reason}, ...],
          "today_action": {...},
        }
    """
    if cluster_id not in CLUSTER_ACTIVATION:
        return err_envelope("INVALID_INPUT", f"cluster_id '{cluster_id}'는 유효하지 않습니다. (1~4)")

    active_ids   = get_active_services(cluster_id)
    inactive_ids = get_inactive_services(cluster_id)

    # LLM 설명 (선택)
    explanations: dict = {"active_explanations": {}, "inactive_explanations": {}}
    if with_llm_explanation:
        try:
            from backend.app.services.llm_isolation_service import explain_cluster_services
            explanations = explain_cluster_services(settings, cluster_id, survey_summary)
        except Exception as e:
            logger.warning("get_didim_service_hub LLM error: %s", e)

    # 오늘의 행동
    today_action_data: dict = {}
    try:
        from backend.app.services.action_service import get_isolation_action
        action_result = get_isolation_action(cluster_id=cluster_id, region=region)
        if action_result.get("success"):
            today_action_data = action_result["data"]
    except Exception as e:
        logger.warning("get_didim_service_hub action error: %s", e)

    # 활성 서비스 목록 조립
    active_services: list[dict] = []
    for sid in active_ids:
        svc = DIDIM_SERVICES.get(sid, {})
        active_services.append({
            "id":            sid,
            "name":          svc.get("name", sid),
            "desc":          svc.get("desc", ""),
            "category":      svc.get("category", ""),
            "frontend_path": svc.get("frontend_path", ""),
            "api_prefix":    svc.get("api_prefix", ""),
            "explanation":   explanations["active_explanations"].get(sid, svc.get("desc", "")),
        })

    # 비활성 서비스 목록 조립
    inactive_services: list[dict] = []
    for sid in inactive_ids:
        svc = DIDIM_SERVICES.get(sid, {})
        reason_hint = svc.get("reason_inactive") or ""
        inactive_services.append({
            "id":            sid,
            "name":          svc.get("name", sid),
            "category":      svc.get("category", ""),
            "reason":        explanations["inactive_explanations"].get(sid, reason_hint),
        })

    cluster_meta = CLUSTER_META.get(cluster_id, {})

    return ok_envelope({
        "cluster_id":         cluster_id,
        "cluster_meta":       cluster_meta,
        "region":             region,
        "active_services":    active_services,
        "inactive_services":  inactive_services,
        "today_action":       today_action_data,
        "active_count":       len(active_services),
        "inactive_count":     len(inactive_services),
        "llm_explanation_applied": with_llm_explanation,
    })
