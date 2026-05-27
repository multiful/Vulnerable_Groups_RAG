# File: schedule.py
# Last Updated: 2026-05-27
# Content Hash: SHA256:TBD
# Role: 시험일정·접수일정·자격종목코드 API — HRD Korea apis.data.go.kr/B490007
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.api.deps import SettingsDep
from backend.app.services import exam_schedule_service

router = APIRouter()


@router.get("/schedules/exams/{cert_id}")
def get_exam_schedule(cert_id: str, settings: SettingsDep) -> dict:
    """
    자격증 시험일정 조회.
    한국산업인력공단 Q-Net API를 통해 해당 연도 시험일정과 D-Day를 반환합니다.
    jmCd(종목코드)를 선조회하여 정확도를 높이고, 없으면 description 필터로 fallback합니다.
    """
    return exam_schedule_service.get_exam_schedule(cert_id, settings)


@router.get("/schedules/applications/{cert_id}")
def get_application_schedule(cert_id: str, settings: SettingsDep) -> dict:
    """
    자격증 접수일정 조회.
    현재 접수 가능한 회차와 접수 마감일·D-Day를 반환합니다.
    """
    return exam_schedule_service.get_application_schedule(cert_id, settings)


@router.get("/schedules/professional-exams")
def get_professional_exam_schedule(
    cert_name: str,
    settings: SettingsDep,
) -> dict:
    """
    국가전문자격 시험 시행일정 조회 (항목 14).
    Q-Net ProfExamScheduleService — 의사·건축사 등 국가전문자격 일정.
    """
    return exam_schedule_service.get_professional_exam_schedule(cert_name, settings)


@router.get("/cert-codes")
def get_cert_codes(
    settings: SettingsDep,
    keyword: str | None = Query(default=None, description="종목명 검색어 (부분 일치)"),
) -> dict:
    """
    자격종목 코드 목록 조회 (apis.data.go.kr/B490007/qualItlCd).
    jmCd + 종목명 + 등급명을 반환합니다. keyword로 부분 검색 가능.
    """
    return exam_schedule_service.get_cert_codes(settings, keyword=keyword)


@router.get("/links/support/{cert_id}")
def get_support_link(cert_id: str, settings: SettingsDep) -> dict:
    """
    자격증 지원 링크 조회.
    Q-Net 공식 페이지 링크를 반환합니다.
    """
    from backend.app.schemas.envelope import ok_envelope

    cert_names = exam_schedule_service._load_cert_name_map()
    cert_name = cert_names.get(cert_id, "")
    if not cert_name:
        from backend.app.schemas.envelope import err_envelope
        return err_envelope("CERT_NOT_FOUND", f"cert_id '{cert_id}'를 찾을 수 없습니다.")

    import urllib.parse
    encoded_name = urllib.parse.quote(cert_name)
    return ok_envelope({
        "cert_id":   cert_id,
        "cert_name": cert_name,
        "links": {
            "qnet_search": f"https://www.q-net.or.kr/crf005.do?id=crf00501&gSite=Q&jmNm={encoded_name}",
            "qnet_schedule": "https://www.q-net.or.kr/crf021.do?id=crf02101&scheType=03",
            "hrd_main": "https://www.hrdkorea.or.kr/",
        },
    })
