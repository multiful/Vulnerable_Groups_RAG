# File: isolation_policy.py
# Last Updated: 2026-06-25
# Content Hash: SHA256:TBD
# Role: GET /api/v1/isolation/* — 고립군 청년 군집별 정책 추천 + DIDIM 서비스 허브
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.config import Settings, get_settings
from backend.app.services import isolation_policy_service

router = APIRouter()


@router.get("/isolation/policy")
def get_isolation_policy(
    cluster_id: str,
    region: str | None = None,
    items_per_category: int = 3,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    고립군 청년 군집별 맞춤 정책 추천 번들.

    - cluster_id: '1'=고립위험청년, '2'=활동형고립청년, '3'=활동제한형고립청년, '4'=은둔청년
    - region: 거주 지역 (예: '서울', '경기') — 지자체 서비스 필터링에 사용
    - items_per_category: 카테고리당 서비스 수 (기본 3, 최대 10)

    서비스 매트릭스에 따라 해당 군집의 보라색 칸 서비스만 반환합니다.
    예) cluster_id=1(고립위험청년): 치유적관계형성 카테고리 제외
    예) cluster_id=3(활동제한형): 일경험및사회활동 카테고리 제외
    """
    items_per_category = min(max(1, items_per_category), 10)
    return isolation_policy_service.get_isolation_policy_bundle(
        settings=settings,
        cluster_id=cluster_id,
        region=region,
        items_per_category=items_per_category,
    )


@router.get("/isolation/dashboard")
def get_isolation_dashboard(
    cluster_id: str,
    region: str | None = None,
    survey_summary: str | None = None,
    with_llm: bool = True,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    고립군 진단 후 DIDIM 전체 서비스 통합 허브.

    cluster_id에 따라 didim.life가 보유한 모든 서비스(자격증·채용·훈련·복지 등)를
    활성/비활성으로 분류하고 LLM이 이유를 설명합니다.

    - cluster_id: '1'~'4'
    - region: 거주 지역 (예: '서울')
    - survey_summary: 설문 응답 요약 텍스트 (LLM 개인화 품질 향상용, 선택)
    - with_llm: LLM 설명 생성 여부 (기본 true)

    응답 구조:
    - active_services: 지금 이용 가능한 DIDIM 서비스 목록 + 설명
    - inactive_services: 지금은 아직인 서비스 목록 + 이유
    - today_action: 오늘 할 수 있는 행동 1가지
    """
    return isolation_policy_service.get_didim_service_hub(
        settings=settings,
        cluster_id=cluster_id,
        region=region,
        survey_summary=survey_summary,
        with_llm_explanation=with_llm,
    )


@router.get("/isolation/clusters")
def get_clusters() -> dict:
    """
    고립군 청년 군집 유형 목록 및 서비스 매트릭스 조회.
    welfare 카테고리 매트릭스 + DIDIM 서비스 매트릭스 모두 반환.
    (진단 결과 화면에서 클러스터 정보 렌더링용)
    """
    from backend.app.services.isolation_policy_service import (
        CLUSTER_META,
        CLUSTER_SERVICE_MATRIX,
        CATEGORY_META,
    )
    from backend.app.services.cluster_service_matrix import (
        CLUSTER_ACTIVATION,
        DIDIM_SERVICES,
    )
    return {
        "success": True,
        "data": {
            "clusters": [
                {
                    "id":               cid,
                    "label":            CLUSTER_META[cid]["label"],
                    "description":      CLUSTER_META[cid]["description"],
                    "direction":        CLUSTER_META[cid]["direction"],
                    # 복지 서비스 매트릭스 (welfare_central / local 등)
                    "welfare_active":   [
                        {
                            "category": cat,
                            "label":    CATEGORY_META.get(cat, {}).get("label", cat),
                            "icon":     CATEGORY_META.get(cat, {}).get("icon", ""),
                        }
                        for cat, active in CLUSTER_SERVICE_MATRIX[cid].items()
                        if active
                    ],
                    "welfare_excluded": [
                        {
                            "category": cat,
                            "label":    CATEGORY_META.get(cat, {}).get("label", cat),
                        }
                        for cat, active in CLUSTER_SERVICE_MATRIX[cid].items()
                        if not active
                    ],
                    # DIDIM 플랫폼 서비스 매트릭스 (자격증·채용·훈련 등)
                    "didim_active":    [
                        {
                            "id":       sid,
                            "name":     DIDIM_SERVICES[sid]["name"],
                            "category": DIDIM_SERVICES[sid]["category"],
                        }
                        for sid, active in CLUSTER_ACTIVATION[cid].items()
                        if active
                    ],
                    "didim_inactive":  [
                        {
                            "id":     sid,
                            "name":   DIDIM_SERVICES[sid]["name"],
                            "reason": DIDIM_SERVICES[sid].get("reason_inactive", ""),
                        }
                        for sid, active in CLUSTER_ACTIVATION[cid].items()
                        if not active
                    ],
                }
                for cid in sorted(CLUSTER_META.keys())
            ],
        },
    }
