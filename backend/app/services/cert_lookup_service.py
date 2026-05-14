# File: cert_lookup_service.py
# Last Updated: 2026-05-14
# Content Hash: SHA256:TBD
# Role: cert_id 기반 중앙 조회 서비스 — cert → NCS → WorkNet/Work24 데이터 연결
#
# 데이터 체인:
#   cert_id
#     ↓ cert_master.csv
#   cert_name, cert_grade_tier, avg_pass_rate_3yr, primary_domain
#     ↓ cert_ncs_mapping.csv
#   ncs_id
#     ↓ ncs_master.csv
#   대직무코드, 대직무분류, 중직무코드 (Work24 srchNcs1/2 파라미터로 직접 사용)
#     ↓ NCS_TO_WORKNET_OCCUPATION
#   WorkNet occupation 코드 (채용정보 검색용)
#
# 이 서비스는 외부 API를 호출하지 않는다. CSV 로컬 데이터만 사용한다.
from __future__ import annotations

import csv
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).parents[3]
_CERT_MASTER  = _PROJECT_ROOT / "data/processed/master/cert_master.csv"
_NCS_MASTER   = _PROJECT_ROOT / "data/processed/master/ncs_master.csv"
_CERT_NCS_MAP = _PROJECT_ROOT / "data/canonical/relations/cert_ncs_mapping.csv"
_CERT_JOB_MAP = _PROJECT_ROOT / "data/canonical/relations/cert_job_mapping.csv"
_JOB_MASTER   = _PROJECT_ROOT / "data/processed/master/job_master.csv"

# NCS 대직무코드 → WorkNet 직종코드 매핑
# WorkNet API의 occupation 파라미터 값 (직종코드)
# 출처: 워크넷 직종코드표 (표준산업분류 기반)
NCS_TO_WORKNET_OCCUPATION: dict[str, list[str]] = {
    "1":  ["030"],           # 사업관리 → 경영/기획직
    "2":  ["030", "031"],    # 경영/회계/사무 → 경영/회계/사무직
    "3":  ["023"],           # 금융/보험 → 금융직
    "4":  ["053"],           # 교육/자연/사회과학 → 교육직
    "5":  ["011"],           # 법률/경찰/소방/교도/국방 → 법률/행정직
    "6":  ["062"],           # 보건/의료 → 의료직
    "7":  ["072"],           # 사회복지/종교 → 복지직
    "8":  ["084"],           # 문화/예술/디자인/방송 → 디자인/방송직
    "9":  ["093"],           # 운전/운송 → 운전/운송직
    "10": ["101"],           # 영업판매 → 판매/영업직
    "11": ["111"],           # 경비/청소 → 서비스직
    "12": ["121"],           # 이용/숙박/여행/오락/스포츠 → 이용/숙박직
    "13": ["130"],           # 음식서비스 → 조리/서비스직
    "14": ["141"],           # 건설 → 건설직
    "15": ["151", "152"],    # 기계 → 기계직
    "16": ["161"],           # 재료 → 재료직
    "17": ["171"],           # 화학/바이오 → 화학직
    "18": ["181"],           # 섬유/의복 → 섬유직
    "19": ["190", "191"],    # 전기/전자 → 전기/전자직
    "20": ["200", "201"],    # 정보통신 → 정보통신직 (IT)
    "21": ["211"],           # 식품가공 → 식품가공직
    "22": ["221"],           # 인쇄/목재/가구/공예 → 인쇄/공예직
    "23": ["230"],           # 환경/에너지/안전 → 환경직
    "24": ["241"],           # 농림어업 → 농업직
}

# NCS 대직무분류 → Work24 srchNcs1 코드 (직접 일치)
# Work24 API는 NCS 대직무코드를 그대로 사용 ("01", "02", ..., "24")
NCS_LEVEL1_TO_WORK24_CODE: dict[str, str] = {
    "사업관리":           "01",
    "경영.회계.사무":     "02",
    "금융/보험":          "03",
    "교육/자연/사회과학": "04",
    "법률/경찰/소방/교도/국방": "05",
    "보건/의료":          "06",
    "사회복지/종교":      "07",
    "문화/예술/디자인/방송": "08",
    "운전/운송":          "09",
    "영업판매":           "10",
    "경비/청소":          "11",
    "이용/숙박/여행/오락/스포츠": "12",
    "음식서비스":         "13",
    "건설":               "14",
    "기계":               "15",
    "재료":               "16",
    "화학/바이오":        "17",
    "섬유/의복":          "18",
    "전기/전자":          "19",
    "정보통신":           "20",
    "식품가공":           "21",
    "인쇄/목재/가구/공예": "22",
    "환경/에너지/안전":   "23",
    "농림어업":           "24",
}


@lru_cache(maxsize=1)
def _load_cert_master() -> dict[str, dict]:
    if not _CERT_MASTER.exists():
        return {}
    out: dict[str, dict] = {}
    with _CERT_MASTER.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["cert_id"]] = dict(r)
    return out


@lru_cache(maxsize=1)
def _load_ncs_master() -> dict[str, dict]:
    """ncs_id → ncs row"""
    if not _NCS_MASTER.exists():
        return {}
    out: dict[str, dict] = {}
    with _NCS_MASTER.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["ncsID"]] = dict(r)
    return out


@lru_cache(maxsize=1)
def _load_cert_to_ncs() -> dict[str, list[str]]:
    """cert_id → [ncs_id, ...] (is_active=True only)"""
    if not _CERT_NCS_MAP.exists():
        return {}
    out: dict[str, list[str]] = defaultdict(list)
    with _CERT_NCS_MAP.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("is_active", "True").strip().lower() not in ("true", "1"):
                continue
            out[r["cert_id"]].append(r["ncs_id"])
    return dict(out)


@lru_cache(maxsize=1)
def _load_cert_to_jobs() -> dict[str, list[str]]:
    """cert_id → [job_role_id, ...]"""
    if not _CERT_JOB_MAP.exists():
        return {}
    out: dict[str, list[str]] = defaultdict(list)
    with _CERT_JOB_MAP.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("is_active", "True").strip().lower() not in ("true", "1"):
                continue
            out[r["cert_id"]].append(r["job_role_id"])
    return dict(out)


@lru_cache(maxsize=1)
def _load_job_master() -> dict[str, dict]:
    if not _JOB_MASTER.exists():
        return {}
    out: dict[str, dict] = {}
    with _JOB_MASTER.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["job_role_id"]] = dict(r)
    return out


# ─────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────

def get_cert_info(cert_id: str) -> dict[str, Any] | None:
    """cert_id → cert_master row (None if not found)"""
    return _load_cert_master().get(cert_id)


def get_cert_ncs_rows(cert_id: str) -> list[dict]:
    """cert_id → NCS master 행 목록 (ncs_id 기준 중복 제거)"""
    ncs_master = _load_ncs_master()
    cert_to_ncs = _load_cert_to_ncs()
    ncs_ids = cert_to_ncs.get(cert_id, [])
    seen_ids: set[str] = set()
    result: list[dict] = []
    for nid in ncs_ids:
        if nid in seen_ids or nid not in ncs_master:
            continue
        seen_ids.add(nid)
        result.append(ncs_master[nid])
    return result


def _get_ncs_level1_frequency(cert_id: str) -> list[tuple[str, str, int]]:
    """
    cert_id → [(대직무코드, 대직무분류명, 빈도), ...] 빈도 내림차순.
    같은 대직무코드에 여러 소직무가 매핑된 경우 빈도가 높은 것이 더 연관성이 높다.
    """
    ncs_master = _load_ncs_master()
    cert_to_ncs = _load_cert_to_ncs()
    ncs_ids = cert_to_ncs.get(cert_id, [])

    from collections import Counter
    code_count: Counter = Counter()
    code_to_name: dict[str, str] = {}
    for nid in ncs_ids:
        row = ncs_master.get(nid)
        if not row:
            continue
        code = row.get("대직무코드", "").strip()
        name = row.get("대직무분류", "").strip()
        if code:
            code_count[code] += 1
            if code not in code_to_name:
                code_to_name[code] = name

    return [(c, code_to_name.get(c, ""), cnt) for c, cnt in code_count.most_common()]


def get_ncs_level1_codes(cert_id: str) -> list[str]:
    """
    cert_id → 고유 NCS 대직무코드 목록 (빈도 내림차순).
    Work24 srchNcs1 파라미터에 직접 사용 가능.
    예: ["20", "19"] for 정보처리기사 (정보통신이 가장 빈도 높음)
    """
    return [code for code, _, _ in _get_ncs_level1_frequency(cert_id)]


def get_ncs_level1_names(cert_id: str) -> list[str]:
    """cert_id → 고유 NCS 대직무분류명 목록 (빈도 내림차순)"""
    return [name for _, name, _ in _get_ncs_level1_frequency(cert_id)]


def get_worknet_occupation_codes(cert_id: str) -> list[str]:
    """
    cert_id → WorkNet 직종코드 목록 (NCS 대직무코드 경유).
    WorkNet API의 occupation 파라미터에 사용.
    """
    ncs_codes = get_ncs_level1_codes(cert_id)
    result: list[str] = []
    seen: set[str] = set()
    for code in ncs_codes:
        for occ in NCS_TO_WORKNET_OCCUPATION.get(code, []):
            if occ not in seen:
                seen.add(occ)
                result.append(occ)
    return result


def get_work24_ncs_code(cert_id: str) -> str | None:
    """
    cert_id → Work24 API srchNcs1 파라미터 값 (가장 연관성 높은 1개).
    Work24 NCS 코드는 2자리 0-padded 문자열 (예: "20", "19")
    """
    codes = get_ncs_level1_codes(cert_id)
    if not codes:
        return None
    # 가장 첫 번째 NCS 대직무코드를 2자리로 패딩
    raw = codes[0]
    try:
        return f"{int(raw):02d}"
    except ValueError:
        return raw.zfill(2)


def get_worknet_search_params(cert_id: str) -> dict[str, Any]:
    """
    WorkNet 채용정보 API 파라미터 세트를 cert_id로부터 생성.
    반환값을 jobs_service.get_hiring_jobs()에 그대로 전달 가능.
    """
    cert = get_cert_info(cert_id)
    if not cert:
        return {}

    cert_name = cert.get("cert_name", "")
    occ_codes = get_worknet_occupation_codes(cert_id)

    params: dict[str, Any] = {}
    if cert_name:
        params["keyword"] = cert_name
    if occ_codes:
        # WorkNet은 다중 직종 검색 시 | 구분 (최대 20개 권장)
        params["occupation"] = "|".join(occ_codes[:5])

    return params


def get_training_search_params(cert_id: str) -> dict[str, Any]:
    """
    Work24 훈련과정 API 파라미터 세트를 cert_id로부터 생성.
    반환값을 training_service.get_training_courses()에 그대로 전달 가능.
    """
    cert = get_cert_info(cert_id)
    if not cert:
        return {}

    ncs_code = get_work24_ncs_code(cert_id)
    ncs_names = get_ncs_level1_names(cert_id)
    cert_name = cert.get("cert_name", "")

    params: dict[str, Any] = {}
    if ncs_names:
        # 대직무분류명을 Work24 ncs_category로 전달
        params["ncs_category"] = ncs_names[0]
    if cert_name:
        params["course_name"] = cert_name

    return params


def get_cert_job_roles(cert_id: str) -> list[dict]:
    """cert_id → 관련 job_master 행 목록"""
    cert_to_jobs = _load_cert_to_jobs()
    job_master = _load_job_master()
    job_ids = cert_to_jobs.get(cert_id, [])
    return [job_master[jid] for jid in job_ids if jid in job_master]


def get_cert_summary(cert_id: str) -> dict[str, Any]:
    """
    cert_id에 대한 종합 요약.
    - cert 기본 정보
    - NCS 분류
    - 관련 직무
    - WorkNet/Work24 파라미터
    """
    cert = get_cert_info(cert_id)
    if not cert:
        return {"found": False, "cert_id": cert_id}

    ncs_rows = get_cert_ncs_rows(cert_id)
    job_roles = get_cert_job_roles(cert_id)

    return {
        "found":           True,
        "cert_id":         cert_id,
        "cert_name":       cert.get("cert_name"),
        "cert_grade_tier": cert.get("cert_grade_tier"),
        "avg_pass_rate":   cert.get("avg_pass_rate_3yr"),
        "primary_domain":  cert.get("primary_domain"),
        "ncs_categories":  [
            {"code": r.get("대직무코드"), "name": r.get("대직무분류")}
            for r in ncs_rows
        ],
        "related_jobs":    [
            {"id": j.get("job_role_id"), "name": j.get("job_role_name")}
            for j in job_roles[:10]
        ],
        "worknet_params":  get_worknet_search_params(cert_id),
        "training_params": get_training_search_params(cert_id),
    }
