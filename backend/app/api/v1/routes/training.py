# File: training.py
# Last Updated: 2026-05-27
# Content Hash: SHA256:TBD
# Role: GET /api/v1/training/courses, /courses/detail, /institutions, /process-eval, /job-learner
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.api.deps import SettingsDep
from backend.app.services import training_service

router = APIRouter(prefix="/training")


@router.get("/courses")
def get_training_courses(
    settings: SettingsDep,
    region: str | None = Query(default=None, description="지역명 (예: 서울)"),
    ncs_category: str | None = Query(default=None, description="NCS 1차 분류명 (예: 정보통신)"),
    course_name: str | None = Query(default=None, description="훈련과정명 검색어"),
    course_type: str | None = Query(default=None, description="훈련유형 코드 (예: C0061)"),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """국민내일배움카드 훈련과정 목록 조회."""
    return training_service.get_training_courses(
        settings,
        region=region,
        ncs_category=ncs_category,
        course_name=course_name,
        course_type=course_type,
        page_size=page_size,
    )


@router.get("/courses/by-cert/{cert_id}")
def get_training_by_cert(
    cert_id: str,
    settings: SettingsDep,
    region: str | None = Query(default=None, description="지역명 (예: 서울)"),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """
    cert_id 기반 훈련과정 조회.
    cert_id → NCS 대직무코드 → Work24 srchNcs1 파라미터 자동 파생 (canonical 데이터 체인).
    직접 문자열 매칭 없이 구조화 데이터만 사용.
    """
    return training_service.get_training_by_cert_id(cert_id, settings, region=region, page_size=page_size)


@router.get("/courses/detail/{course_id}")
def get_training_course_detail(
    course_id: str,
    settings: SettingsDep,
    degree: str = Query(default="1", description="차수 (기본값 1)"),
) -> dict:
    """
    훈련과정 상세 조회 (callOpenApiSvcInfo310L02).
    과정 목록에서 받은 course_id(trprId)로 커리큘럼·강사·수강료 등 상세 정보를 조회합니다.
    """
    return training_service.get_training_course_detail(course_id, settings, degree=degree)


@router.get("/institutions")
def get_training_institutions(
    settings: SettingsDep,
    region: str | None = Query(default=None, description="지역명 (예: 서울)"),
    ncs_category: str | None = Query(default=None, description="NCS 1차 분류명 (예: 정보통신)"),
    institution_name: str | None = Query(default=None, description="기관명 검색어"),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """
    훈련기관 목록 조회 (callOpenApiSvcInfo320L01).
    지역·NCS 분류로 국민내일배움카드 훈련을 제공하는 기관을 검색합니다.
    """
    return training_service.get_training_institutions(
        settings,
        region=region,
        ncs_category=ncs_category,
        institution_name=institution_name,
        page_size=page_size,
    )


@router.get("/process-eval")
def get_process_eval_courses(
    settings: SettingsDep,
    keyword: str | None = Query(default=None, description="종목명 검색어"),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """
    과정평가형 자격 종목 조회.
    시험 부담이 큰 4~5단계 청년에게 교육 이수형 취득 경로를 안내합니다.
    """
    return training_service.get_process_eval_courses(
        settings,
        keyword=keyword,
        page_size=page_size,
    )


@router.get("/job-learner")
def get_job_learner_courses(
    settings: SettingsDep,
    keyword: str | None = Query(default=None, description="종목명 검색어"),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """
    일학습병행 과정 지정평가 정보 조회 (항목 11).
    기업 현장훈련으로 자격 취득 — 고위험군(4~5단계) 대안 경로.
    """
    return training_service.get_job_learner_courses(
        settings,
        keyword=keyword,
        page_size=page_size,
    )
