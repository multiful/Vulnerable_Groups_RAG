# File: cluster_service_matrix.py
# Last Updated: 2026-06-26 (일학습병행·컨소시엄·구직자취업역량강화 3종 서비스 추가)
# Content Hash: SHA256:TBD
# Role: 고립군 군집(1~4) × DIDIM 전체 서비스 활성/비활성 매트릭스
#
# 설계 원칙:
#   - 활성/비활성 결정은 이 파일의 하드코딩 값이 절대 기준
#   - LLM은 이유 설명만 담당 (어떤 서비스를 보여줄지는 절대 결정하지 않음)
#   - 서비스 추가 시 반드시 DIDIM_SERVICES + CLUSTER_ACTIVATION 모두 갱신
#
# 군집 정의:
#   1 = 고립위험청년   : 사회참여 의지 있음, 관계망 약화 시작
#   2 = 활동형고립청년  : 혼자 활동하지만 의미 있는 관계망 없음
#   3 = 활동제한형고립청년: 경제·환경적 제약으로 외부활동 어려움
#   4 = 은둔청년       : 사회 단절, 자기관리 어려움, 의지적 철수

from __future__ import annotations

# ── DIDIM 전체 서비스 카탈로그 ────────────────────────────────────────────
# category: 표시 그룹핑용 (취업준비 / 취업 / 복지지원 / 공간지원 / 실천 등)
# frontend_path: 프론트 라우팅 경로
# api_prefix: 백엔드 API prefix (참조용)
# reason_inactive_template: 비활성 시 LLM에 전달할 컨텍스트 힌트 (LLM이 다듬어서 출력)

DIDIM_SERVICES: dict[str, dict] = {
    # ── 취업준비 계층 (자격증·로드맵·일정·훈련) ─────────────────────────
    "certification_roadmap": {
        "name":            "자격증 추천 · 로드맵",
        "desc":            "관심 분야 자격증 추천과 단계별 로드맵 제안",
        "category":        "취업준비",
        "priority":        1,
        "frontend_path":   "/roadmap",
        "api_prefix":      "/api/v1/recommendations/llm",
        "reason_inactive": "은둔 상태에서는 자격증·취업 준비보다 기본 생활 회복과 관계 형성이 우선입니다.",
    },
    "exam_schedule": {
        "name":            "시험 일정 조회",
        "desc":            "Q-Net 국가자격 시험 일정 및 접수 정보",
        "category":        "취업준비",
        "priority":        2,
        "frontend_path":   "/schedules",
        "api_prefix":      "/api/v1/schedule/exam",
        "reason_inactive": "시험 준비 단계에 진입하기 전 사회참여 기반을 먼저 다지는 것이 중요합니다.",
    },
    "youtube_lectures": {
        "name":            "자격증 관련 강의",
        "desc":            "자격증별 YouTube 강의 영상 추천",
        "category":        "취업준비",
        "priority":        3,
        "frontend_path":   "/certs/videos",
        "api_prefix":      "/api/v1/cert-videos",
        "reason_inactive": "혼자 온라인 학습보다 대면 지원과 관계 형성이 지금 단계에서 더 효과적입니다.",
    },
    "training_courses": {
        "name":            "훈련과정",
        "desc":            "국민내일배움카드 국비지원 훈련과정 조회",
        "category":        "취업준비",
        "priority":        4,
        "frontend_path":   "/training",
        "api_prefix":      "/api/v1/training/courses",
        "reason_inactive": "집 밖 훈련 참여가 어려운 상태입니다. 먼저 복지서비스를 통한 지원을 받아보세요.",
    },

    # ── 취업 실행 계층 (채용공고) ─────────────────────────────────────────
    "job_listings": {
        "name":            "채용정보",
        "desc":            "워크넷 실시간 채용공고 조회",
        "category":        "취업",
        "priority":        5,
        "frontend_path":   "/jobs",
        "api_prefix":      "/api/v1/jobs/hiring",
        "reason_inactive": "지금은 직접 취업 지원보다 사회적 관계 회복과 자신감 형성이 먼저입니다.",
    },

    # ── 사회참여 계층 (정부지원일자리) ───────────────────────────────────
    "govt_job_programs": {
        "name":            "정부지원 일자리 프로그램",
        "desc":            "청년도전지원사업, 일경험 프로그램 등 참여자 모집",
        "category":        "사회참여",
        "priority":        6,
        "frontend_path":   "/isolation/policy",
        "api_prefix":      "/api/v1/isolation/policy",
        "reason_inactive": "활동이 제한된 상태에서는 치유적 관계 형성을 먼저 경험한 뒤 사회참여를 늘려가는 것이 좋습니다.",
    },

    # ── 공간지원 계층 (일자리카페·건강증진센터) ──────────────────────────
    "job_cafes": {
        "name":            "일자리카페",
        "desc":            "서울시 일자리카페 위치 및 취업 상담 서비스",
        "category":        "공간지원",
        "priority":        7,
        "frontend_path":   "/seoul/job-cafes",
        "api_prefix":      "/api/v1/seoul/job-cafes",
        "reason_inactive": "외출이 어려운 상태에서는 지역 복지기관의 방문 지원 서비스를 먼저 이용해 보세요.",
    },
    "health_centers": {
        "name":            "건강증진센터",
        "desc":            "서울시 건강증진센터 위치 및 건강 프로그램",
        "category":        "공간지원",
        "priority":        8,
        "frontend_path":   "/seoul/health-centers",
        "api_prefix":      "/api/v1/seoul/health-centers",
        "reason_inactive": None,  # 모든 군집 활성
    },

    # ── 복지지원 계층 (복지로·가족지원) ──────────────────────────────────
    "welfare_central": {
        "name":            "중앙부처 복지서비스",
        "desc":            "심리상담, 생계급여, 주거지원, 가족지원 복지서비스",
        "category":        "복지지원",
        "priority":        9,
        "frontend_path":   "/isolation/policy",
        "api_prefix":      "/api/v1/isolation/policy",
        "reason_inactive": None,  # 모든 군집 활성
    },
    "welfare_local": {
        "name":            "지자체 복지서비스",
        "desc":            "지역 기반 관계 회복 프로그램, 자조모임, 긴급지원",
        "category":        "복지지원",
        "priority":        10,
        "frontend_path":   "/isolation/policy",
        "api_prefix":      "/api/v1/isolation/policy",
        "reason_inactive": None,
    },
    "family_centers": {
        "name":            "건강가정지원센터",
        "desc":            "가족상담, 가족교육, 보호자 상담, 가족관계 회복",
        "category":        "가족지원",
        "priority":        11,
        "frontend_path":   "/isolation/policy",
        "api_prefix":      "/api/v1/isolation/policy",
        "reason_inactive": None,
    },
    "gender_facilities": {
        "name":            "여성·가족·청소년 시설",
        "desc":            "청소년상담복지센터, 가족지원센터, 관계회복 지원기관",
        "category":        "상담지원",
        "priority":        12,
        "frontend_path":   "/isolation/policy",
        "api_prefix":      "/api/v1/isolation/policy",
        "reason_inactive": None,
    },

    # ── 실천 계층 (오늘의 행동) ───────────────────────────────────────────
    "today_action": {
        "name":            "오늘의 행동 제안",
        "desc":            "현재 상태에 맞는 작은 실천 행동 1가지 제안",
        "category":        "실천",
        "priority":        13,
        "frontend_path":   "/action",
        "api_prefix":      "/api/v1/action",
        "reason_inactive": None,  # 모든 군집 활성
    },

    # ── Work24 확장 훈련과정 (일학습병행·컨소시엄·구직자취업역량강화) ────────
    "workstudy_courses": {
        "name":            "일학습병행 훈련과정",
        "desc":            "기업 채용 후 일하며 배우는 일학습병행 훈련과정 조회",
        "category":        "취업준비",
        "priority":        17,
        "frontend_path":   "/training/workstudy",
        "api_prefix":      "/api/v1/training/workstudy",
        "reason_inactive": "일학습병행은 기업 채용이 전제되어 있어, 지금 단계에서는 먼저 기초 역량을 쌓는 것이 좋습니다.",
    },
    "consortium_courses": {
        "name":            "국가인적자원개발 컨소시엄",
        "desc":            "기업 컨소시엄 기반 국비지원 훈련과정 조회",
        "category":        "취업준비",
        "priority":        18,
        "frontend_path":   "/training/consortium",
        "api_prefix":      "/api/v1/training/consortium",
        "reason_inactive": "집 밖 훈련 참여가 어려운 상태입니다. 복지서비스를 통한 지원을 먼저 받아보세요.",
    },
    "jobseeker_program": {
        "name":            "구직자취업역량 강화프로그램",
        "desc":            "구직자 취업역량 강화 및 고용 지원 프로그램 조회",
        "category":        "취업준비",
        "priority":        19,
        "frontend_path":   "/training/jobseeker-program",
        "api_prefix":      "/api/v1/training/jobseeker-program",
        "reason_inactive": "취업 활동보다 사회참여 기반과 자신감 형성이 지금 단계에서 더 우선입니다.",
    },

    # ── 온통청년 계층 (정책·공간·콘텐츠) ────────────────────────────────
    "youth_policy": {
        "name":            "청년정책 찾기",
        "desc":            "온통청년 포털 기반 일자리·주거·교육·복지 청년정책 조회",
        "category":        "청년정책",
        "priority":        14,
        "frontend_path":   "/youth/policy",
        "api_prefix":      "/api/v1/youth/policy",
        "reason_inactive": None,  # 모든 군집 활성
    },
    "youth_space": {
        "name":            "청년공간(센터) 찾기",
        "desc":            "가까운 청년센터·청년공간 위치 및 프로그램 조회",
        "category":        "청년정책",
        "priority":        15,
        "frontend_path":   "/youth/space",
        "api_prefix":      "/api/v1/youth/space",
        "reason_inactive": "외출이 어려운 상태에서는 온라인 콘텐츠나 방문 지원 서비스를 먼저 활용해 보세요.",
    },
    "youth_content": {
        "name":            "청년 콘텐츠",
        "desc":            "온통청년 포털 기반 청년 대상 교육·정보 콘텐츠 (대분류별 분류 제공)",
        "category":        "청년정책",
        "priority":        16,
        "frontend_path":   "/youth/content",
        "api_prefix":      "/api/v1/youth/content",
        "reason_inactive": None,  # 온라인 콘텐츠 — 모든 군집 활성
    },
}

# ── 군집별 서비스 활성/비활성 매트릭스 ──────────────────────────────────
# True = 활성(표시), False = 비활성(숨기거나 "지금은 아직" 안내)
#
# 결정 근거:
#   1(고립위험): 취업 의지·사회참여 의지 있음 → 전 서비스 활성
#   2(활동형):  혼자 활동 가능, 관계망 없음 → 직접 채용 제외, 사회참여형 서비스 활성
#   3(활동제한): 외출 어려움 → 집 밖 활동 서비스 제외, 자격증/훈련은 동기 부여로 유지
#   4(은둔):    사회 단절 → 취업·자격증 계층 전체 비활성, 복지·치유 계층만 활성

CLUSTER_ACTIVATION: dict[str, dict[str, bool]] = {
    "1": {  # 고립위험청년 — 모든 서비스 활성
        "certification_roadmap": True,
        "exam_schedule":         True,
        "youtube_lectures":      True,
        "training_courses":      True,
        "job_listings":          True,
        "govt_job_programs":     True,
        "job_cafes":             True,
        "health_centers":        True,
        "welfare_central":       True,
        "welfare_local":         True,
        "family_centers":        True,
        "gender_facilities":     True,
        "today_action":          True,
        "workstudy_courses":     True,
        "consortium_courses":    True,
        "jobseeker_program":     True,
        "youth_policy":          True,
        "youth_space":           True,
        "youth_content":         True,
    },
    "2": {  # 활동형고립청년 — 직접 채용 제외
        "certification_roadmap": True,
        "exam_schedule":         True,
        "youtube_lectures":      True,
        "training_courses":      True,
        "job_listings":          False,   # 직접 취업보다 사회참여 먼저
        "govt_job_programs":     True,    # 사회활동형 일경험은 OK
        "job_cafes":             True,
        "health_centers":        True,
        "welfare_central":       True,
        "welfare_local":         True,
        "family_centers":        True,
        "gender_facilities":     True,
        "today_action":          True,
        "workstudy_courses":     True,
        "consortium_courses":    True,
        "jobseeker_program":     True,
        "youth_policy":          True,
        "youth_space":           True,
        "youth_content":         True,
    },
    "3": {  # 활동제한형고립청년 — 외출 필요 서비스 + 직접 채용 제외
        "certification_roadmap": True,    # 목표·동기 부여 역할
        "exam_schedule":         True,
        "youtube_lectures":      True,    # 집에서 학습 가능
        "training_courses":      True,    # 온라인 훈련 가능
        "job_listings":          False,
        "govt_job_programs":     False,   # 외출·사회활동 제한
        "job_cafes":             False,   # 외출 어려움
        "health_centers":        True,
        "welfare_central":       True,
        "welfare_local":         True,
        "family_centers":        True,
        "gender_facilities":     True,
        "today_action":          True,
        "workstudy_courses":     False,   # 기업 채용 전제 → 외출 어려움
        "consortium_courses":    True,    # 온라인 위탁훈련 가능
        "jobseeker_program":     False,   # 적극적 구직활동 어려움
        "youth_policy":          True,    # 정책 정보 조회는 온라인 가능
        "youth_space":           False,   # 외출 어려움
        "youth_content":         True,    # 온라인 콘텐츠
    },
    "4": {  # 은둔청년 — 취업준비 계층 전체 비활성, 복지·치유만 활성
        "certification_roadmap": False,   # 지금은 아직
        "exam_schedule":         False,
        "youtube_lectures":      False,
        "training_courses":      False,
        "job_listings":          False,
        "govt_job_programs":     False,
        "job_cafes":             False,
        "health_centers":        True,
        "welfare_central":       True,
        "welfare_local":         True,
        "family_centers":        True,
        "gender_facilities":     True,
        "today_action":          True,
        "workstudy_courses":     False,
        "consortium_courses":    False,
        "jobseeker_program":     False,
        "youth_policy":          True,    # 복지·주거 정책 정보는 접근 가능
        "youth_space":           False,   # 외출 불가
        "youth_content":         True,    # 집에서 콘텐츠 접근 가능
    },
}

# 군집 → action_service의 risk_stage_id 매핑 (기존 템플릿 재사용)
CLUSTER_TO_RISK_ID: dict[str, str] = {
    "1": "risk_0002",
    "2": "risk_0003",
    "3": "risk_0004",
    "4": "risk_0005",
}


def get_active_services(cluster_id: str) -> list[str]:
    """군집 ID → 활성 서비스 ID 목록 (priority 순)."""
    activation = CLUSTER_ACTIVATION.get(cluster_id, {})
    active_ids = [sid for sid, on in activation.items() if on]
    return sorted(active_ids, key=lambda s: DIDIM_SERVICES.get(s, {}).get("priority", 99))


def get_inactive_services(cluster_id: str) -> list[str]:
    """군집 ID → 비활성 서비스 ID 목록."""
    activation = CLUSTER_ACTIVATION.get(cluster_id, {})
    return [sid for sid, on in activation.items() if not on]


def build_service_context_for_llm(cluster_id: str) -> dict:
    """
    LLM 프롬프트 구성용 컨텍스트 빌드.
    active/inactive 서비스 목록 + 각각의 이름·설명·비활성 이유를 반환.
    """
    active = get_active_services(cluster_id)
    inactive = get_inactive_services(cluster_id)
    return {
        "active": [
            {
                "id":   sid,
                "name": DIDIM_SERVICES[sid]["name"],
                "desc": DIDIM_SERVICES[sid]["desc"],
            }
            for sid in active
        ],
        "inactive": [
            {
                "id":             sid,
                "name":           DIDIM_SERVICES[sid]["name"],
                "reason_hint":    DIDIM_SERVICES[sid].get("reason_inactive", ""),
            }
            for sid in inactive
            if DIDIM_SERVICES[sid].get("reason_inactive")
        ],
    }
