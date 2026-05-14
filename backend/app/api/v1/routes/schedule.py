# File: schedule.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: 시험일정·접수일정 API — reserved 해제, 실제 HRD Korea API 호출
from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.deps import SettingsDep
from backend.app.services import exam_schedule_service

router = APIRouter()


@router.get("/schedules/exams/{cert_id}")
def get_exam_schedule(cert_id: str, settings: SettingsDep) -> dict:
    """
    자격증 시험일정 조회.
    한국산업인력공단 Q-Net API를 통해 해당 연도 시험일정과 D-Day를 반환합니다.
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
            "qnet_search": f"https://www.q-net.or.kr/crf005.do?id=crf00503s&jmCd=&jmNm={encoded_name}",
            "qnet_schedule": "https://www.q-net.or.kr/crf005.do?id=crf00503s",
            "hrd_main": "https://www.hrdkorea.or.kr/",
        },
    })
