# File: action_service.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 오늘의 한 가지 행동 추천 — 위험군 단계 + 추천 자격증 + 지역 기반
#
# 구현 원칙:
# - 단계별로 사전 정의된 행동 템플릿 풀 사용 (환각 방지)
# - cert_id / region이 있으면 구체적 행동으로 채워넣기
# - 절대 "보장", "반드시" 등 단정적 표현 금지
# - 작은 성취 강조, 부드러운 어조
from __future__ import annotations

import csv
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.schemas.envelope import ok_envelope

_PROJECT_ROOT = Path(__file__).parents[3]
_CERT_MASTER_CSV = _PROJECT_ROOT / "data/processed/master/cert_master.csv"

# 위험군 단계별 행동 템플릿 풀
# {cert_name}, {region} 플레이스홀더 사용
_ACTION_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "risk_0001": [
        {
            "action_type": "apply",
            "title": "채용공고 지원",
            "description": "{cert_name} 관련 채용공고를 1개 찾아 지원해 보세요.",
            "cta": "워크넷에서 채용공고 보기",
            "cta_path": "/jobs/hiring",
            "effort_minutes": 30,
        },
        {
            "action_type": "study",
            "title": "자격증 시험 접수 확인",
            "description": "{cert_name} 다음 시험 접수일을 달력에 표시해 두세요.",
            "cta": "시험일정 확인하기",
            "cta_path": "/schedules/exams",
            "effort_minutes": 10,
        },
    ],
    "risk_0002": [
        {
            "action_type": "study",
            "title": "오늘 30분 공부",
            "description": "{cert_name} 관련 무료 강의 1강을 들어 보세요.",
            "cta": "관련 강의 찾기",
            "cta_path": "/certs/videos",
            "effort_minutes": 30,
        },
        {
            "action_type": "training",
            "title": "훈련과정 알아보기",
            "description": "{region}에서 {cert_name} 관련 국비지원 훈련과정을 찾아보세요.",
            "cta": "훈련과정 검색",
            "cta_path": "/training/courses",
            "effort_minutes": 20,
        },
    ],
    "risk_0003": [
        {
            "action_type": "training",
            "title": "국비 훈련과정 등록",
            "description": "가까운 {region} 훈련기관에서 {cert_name} 과정을 찾아보세요.",
            "cta": "훈련과정 보기",
            "cta_path": "/training/courses",
            "effort_minutes": 20,
        },
        {
            "action_type": "space",
            "title": "일자리카페 방문",
            "description": "{region} 근처 일자리카페에서 취업 상담을 받아 보세요.",
            "cta": "일자리카페 찾기",
            "cta_path": "/seoul/job-cafes",
            "effort_minutes": 60,
        },
        {
            "action_type": "study",
            "title": "자격증 소개 영상 보기",
            "description": "{cert_name}이 어떤 직무와 연결되는지 영상으로 확인해 보세요.",
            "cta": "관련 영상 보기",
            "cta_path": "/certs/videos",
            "effort_minutes": 15,
        },
    ],
    "risk_0004": [
        {
            "action_type": "process_eval",
            "title": "과정평가형 자격 알아보기",
            "description": "시험 없이 교육만으로 취득 가능한 자격증이 있습니다. {cert_name} 대신 도전해 볼 수 있어요.",
            "cta": "과정평가형 자격 보기",
            "cta_path": "/training/process-eval",
            "effort_minutes": 20,
        },
        {
            "action_type": "space",
            "title": "가까운 지원 공간 방문",
            "description": "{region} 근처 일자리카페나 청년 지원 공간을 한 번 방문해 보세요. 혼자 하지 않아도 됩니다.",
            "cta": "공간 찾기",
            "cta_path": "/seoul/job-cafes",
            "effort_minutes": 60,
        },
        {
            "action_type": "reservation",
            "title": "공공 학습 공간 예약",
            "description": "오늘 공공 학습 공간을 예약하고 자격증 정보를 1가지만 찾아보세요.",
            "cta": "공간 예약하기",
            "cta_path": "/seoul/reservations",
            "effort_minutes": 15,
        },
    ],
    "risk_0005": [
        {
            "action_type": "micro",
            "title": "오늘 한 가지 검색",
            "description": "{cert_name}의 이름과 합격률을 한 번 검색해 보는 것으로 오늘을 시작해 보세요.",
            "cta": "자격증 정보 보기",
            "cta_path": "/recommendations",
            "effort_minutes": 5,
        },
        {
            "action_type": "wellness",
            "title": "마음 지원 공간 알아보기",
            "description": "가까운 {region} 건강 지원 공간에 대해 알아보는 것도 좋은 한 걸음입니다.",
            "cta": "지원 공간 보기",
            "cta_path": "/seoul/health-centers",
            "effort_minutes": 10,
        },
        {
            "action_type": "micro",
            "title": "공부 공간 예약만 해두기",
            "description": "당장 가지 않아도 괜찮아요. 가까운 공공 공간을 예약만 해두는 것도 충분한 시작입니다.",
            "cta": "공간 예약",
            "cta_path": "/seoul/reservations",
            "effort_minutes": 5,
        },
    ],
}

_DEFAULT_ACTIONS: list[dict[str, str]] = [
    {
        "action_type": "study",
        "title": "자격증 정보 1가지 알아보기",
        "description": "관심 있는 자격증에 대해 오늘 1가지만 알아보세요.",
        "cta": "자격증 추천 보기",
        "cta_path": "/recommendations",
        "effort_minutes": 10,
    }
]

# 고립군 군집별 전용 행동 템플릿 (cluster_id 1~4)
# 취업·자격증 중심이 아닌 사회참여·치유·복지 중심
_ISOLATION_ACTION_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "1": [  # 고립위험청년 — 사회참여 동기 강화
        {
            "action_type": "connect",
            "title": "관심 분야 모임 1개 찾기",
            "description": "{region} 주변 관심 있는 모임이나 커뮤니티를 하나 검색해 보세요.",
            "cta": "지역 서비스 찾기",
            "cta_path": "/isolation/policy",
            "effort_minutes": 15,
        },
        {
            "action_type": "apply",
            "title": "일경험 프로그램 확인하기",
            "description": "청년도전지원사업 등 일경험 프로그램 1개의 모집 조건을 확인해 보세요.",
            "cta": "정부지원 일자리 보기",
            "cta_path": "/isolation/policy",
            "effort_minutes": 20,
        },
        {
            "action_type": "study",
            "title": "관심 자격증 강의 1강 보기",
            "description": "오늘 관심 자격증 관련 무료 강의를 1강만 들어보세요.",
            "cta": "관련 강의 찾기",
            "cta_path": "/certs/videos",
            "effort_minutes": 30,
        },
    ],
    "2": [  # 활동형고립청년 — 관계 형성 + 사회활동 연결
        {
            "action_type": "connect",
            "title": "자조모임 프로그램 알아보기",
            "description": "{region} 지역 청년 자조모임이나 관계 회복 프로그램을 찾아보세요.",
            "cta": "지역 복지서비스 보기",
            "cta_path": "/isolation/policy",
            "effort_minutes": 15,
        },
        {
            "action_type": "space",
            "title": "일자리카페 방문 계획 세우기",
            "description": "{region} 근처 일자리카페에 이번 주 한 번 방문해 보세요. 꼭 무언가를 하지 않아도 괜찮아요.",
            "cta": "일자리카페 찾기",
            "cta_path": "/seoul/job-cafes",
            "effort_minutes": 60,
        },
        {
            "action_type": "training",
            "title": "그룹 훈련과정 1개 검색",
            "description": "혼자 공부보다 여럿이 함께하는 훈련과정을 1개 찾아보세요.",
            "cta": "훈련과정 보기",
            "cta_path": "/training/courses",
            "effort_minutes": 15,
        },
    ],
    "3": [  # 활동제한형고립청년 — 온라인·집 기반 지원
        {
            "action_type": "welfare",
            "title": "온라인 복지서비스 신청 확인",
            "description": "지금 이용할 수 있는 복지서비스 1가지를 오늘 확인해 보세요. 신청은 나중에 해도 괜찮아요.",
            "cta": "복지서비스 보기",
            "cta_path": "/isolation/policy",
            "effort_minutes": 15,
        },
        {
            "action_type": "study",
            "title": "집에서 관련 영상 1개 보기",
            "description": "오늘 집에서 10분짜리 관심 분야 영상을 1개만 보세요.",
            "cta": "관련 강의 찾기",
            "cta_path": "/certs/videos",
            "effort_minutes": 15,
        },
        {
            "action_type": "family",
            "title": "가족지원 서비스 알아보기",
            "description": "건강가정지원센터의 프로그램 중 집에서 신청할 수 있는 것을 확인해 보세요.",
            "cta": "가족지원 서비스",
            "cta_path": "/isolation/policy",
            "effort_minutes": 10,
        },
    ],
    "4": [  # 은둔청년 — 아주 작은 첫 걸음
        {
            "action_type": "micro",
            "title": "심리상담 정보 1가지 보기",
            "description": "지금 당장 상담을 받지 않아도 괜찮아요. 어떤 상담이 있는지 1가지만 알아보는 것부터 시작해요.",
            "cta": "심리상담 서비스 보기",
            "cta_path": "/isolation/policy",
            "effort_minutes": 5,
        },
        {
            "action_type": "wellness",
            "title": "가까운 건강증진센터 위치 확인",
            "description": "{region} 근처 건강증진센터가 어디 있는지 오늘 확인만 해보세요. 방문은 준비되면 해요.",
            "cta": "건강증진센터 찾기",
            "cta_path": "/seoul/health-centers",
            "effort_minutes": 5,
        },
        {
            "action_type": "micro",
            "title": "오늘 창문 1번 열기",
            "description": "오늘 가장 작은 것 하나를 해보세요. 창문을 열거나 짧게 바깥 공기를 마시는 것도 충분합니다.",
            "cta": "복지서비스 안내",
            "cta_path": "/isolation/policy",
            "effort_minutes": 1,
        },
    ],
}


@lru_cache(maxsize=1)
def _load_cert_names() -> dict[str, str]:
    if not _CERT_MASTER_CSV.exists():
        return {}
    out: dict[str, str] = {}
    with _CERT_MASTER_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["cert_id"]] = r["cert_name"]
    return out


def get_today_action(
    risk_stage_id: str | None = None,
    cert_ids: list[str] | None = None,
    region: str | None = None,
) -> dict:
    """
    위험군 단계 + 추천 자격증 + 지역 기반으로 오늘의 한 가지 행동을 추천.
    반드시 실행 가능한 작은 행동 하나만 반환.
    """
    stage = (risk_stage_id or "").strip()
    region_str = region or "서울"

    cert_names = _load_cert_names()
    cert_name = "자격증"
    if cert_ids:
        for cid in cert_ids:
            if name := cert_names.get(cid):
                cert_name = name
                break

    templates = _ACTION_TEMPLATES.get(stage, _DEFAULT_ACTIONS)
    chosen = random.choice(templates)

    # 플레이스홀더 채우기
    filled: dict[str, Any] = {}
    for k, v in chosen.items():
        if isinstance(v, str):
            filled[k] = v.replace("{cert_name}", cert_name).replace("{region}", region_str)
        else:
            filled[k] = v

    return ok_envelope({
        "risk_stage_id": stage or None,
        "cert_name":     cert_name,
        "region":        region_str,
        "action":        filled,
        "motivation":    _get_motivation_message(stage),
    })


def _get_motivation_message(stage: str) -> str:
    messages = {
        "risk_0001": "지금의 경로를 유지하면서 한 단계씩 나아가고 있습니다.",
        "risk_0002": "작은 행동들이 쌓여 큰 변화가 됩니다. 오늘도 한 걸음씩.",
        "risk_0003": "속도보다 방향이 중요합니다. 오늘 한 가지만 해보세요.",
        "risk_0004": "완벽하지 않아도 괜찮아요. 오늘 작은 것 하나로 충분합니다.",
        "risk_0005": "지금 이 순간 여기 있는 것만으로도 충분히 잘 하고 있습니다.",
    }
    return messages.get(stage, "오늘 하루도 조금씩 앞으로 나아가고 있습니다.")


_ISOLATION_MOTIVATION: dict[str, str] = {
    "1": "사회참여의 문을 조금씩 열어가고 있습니다. 오늘도 한 걸음씩.",
    "2": "혼자가 아닌 함께하는 경험이 쌓여갑니다. 천천히 가도 괜찮아요.",
    "3": "지금 상황에서 할 수 있는 것부터, 작은 것부터 시작해요.",
    "4": "오늘 여기 있는 것만으로도 충분합니다. 아주 작은 것 하나면 됩니다.",
}


def get_isolation_action(
    cluster_id: str,
    region: str | None = None,
) -> dict:
    """
    고립군 군집별 오늘의 한 가지 행동 제안.
    기존 risk_stage_id 기반 get_today_action과 독립적으로 동작.

    Args:
        cluster_id: '1'~'4' (고립위험청년~은둔청년)
        region: 거주 지역 (기본 '서울')
    """
    region_str = region or "서울"
    templates = _ISOLATION_ACTION_TEMPLATES.get(cluster_id)
    if not templates:
        templates = _DEFAULT_ACTIONS

    chosen = random.choice(templates)
    filled: dict[str, Any] = {}
    for k, v in chosen.items():
        if isinstance(v, str):
            filled[k] = v.replace("{region}", region_str)
        else:
            filled[k] = v

    return ok_envelope({
        "cluster_id": cluster_id,
        "region":     region_str,
        "action":     filled,
        "motivation": _ISOLATION_MOTIVATION.get(cluster_id, "오늘 하루도 조금씩 앞으로 나아가고 있습니다."),
    })
