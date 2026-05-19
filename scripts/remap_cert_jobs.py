# Content Hash: SHA256:TBD
"""
remap_cert_jobs.py
------------------
cert_job_mapping.csv의 mass-assignment 오류를 수정하는 스크립트.
cert별 정확한 직무 목록을 재정의하고, cert_candidates.jsonl의 related_jobs도 갱신한다.
마지막에 build_frontend_data.py를 실행한다.
"""

import csv
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJM_PATH = os.path.join(BASE_DIR, "data", "canonical", "relations", "cert_job_mapping.csv")
CDM_PATH = os.path.join(BASE_DIR, "data", "canonical", "relations", "cert_domain_mapping.csv")
CANDIDATES_PATH = os.path.join(BASE_DIR, "data", "canonical", "candidates", "cert_candidates.jsonl")
BUILD_SCRIPT = os.path.join(BASE_DIR, "scripts", "build_frontend_data.py")

# ---------------------------------------------------------------------------
# 1. cert별 명시적 직무 재매핑 테이블 (domain_0002, domain_0003 명시 정의)
# ---------------------------------------------------------------------------
EXPLICIT_REMAP = {
    # ── domain_0002 게임 개발 전문 ──────────────────────────────────────────
    "cert_0707": ["job_0015", "job_0016", "job_0017"],   # 게임프로그래밍전문가
    "cert_1042": ["job_0015", "job_0016", "job_0017"],   # 게임프로그래밍전문가 dup
    "cert_0708": ["job_0015", "job_0120", "job_0127"],   # 게임그래픽전문가
    "cert_0709": ["job_0015", "job_0016"],               # 게임기획전문가
    "cert_1041": ["job_0015", "job_0016"],               # 게임기획전문가 dup

    # ── domain_0002 정보처리 계열 ──────────────────────────────────────────
    "cert_0043": ["job_0009", "job_0014", "job_0019", "job_0020", "job_0083"],  # 정보관리기술사
    "cert_0045": ["job_0009", "job_0014", "job_0019", "job_0020", "job_0021"],  # 컴퓨터시스템응용기술사
    "cert_0135": ["job_0009", "job_0011", "job_0012", "job_0014", "job_0018", "job_0019"],  # 정보처리기사
    "cert_0278": ["job_0009", "job_0012", "job_0014", "job_0019"],              # 정보처리산업기사
    "cert_0892": ["job_0009", "job_0014", "job_0020", "job_0021"],              # 컴퓨터시스템기사
    "cert_0906": ["job_0009", "job_0074"],                                      # 정보처리기능사

    # ── domain_0002 프로그래밍 기초 ──────────────────────────────────────────
    "cert_0551": ["job_0009", "job_0012", "job_0018"],   # 프로그래밍기능사

    # ── domain_0002 사무/IT활용 자격 ──────────────────────────────────────────
    "cert_0259": ["job_0073", "job_0074"],   # 사무자동화산업기사
    "cert_0547": ["job_0073", "job_0074"],   # 정보기기운용기능사
    "cert_0897": ["job_0073", "job_0074"],   # 전자계산기기능사
    "cert_0911": ["job_0073", "job_0074"],   # 컴퓨터활용능력 1급
    "cert_0912": ["job_0073", "job_0074"],   # 컴퓨터활용능력 2급
    "cert_1058": ["job_0073", "job_0074"],   # ITQ A급
    "cert_1059": ["job_0073", "job_0074"],   # ITQ B급
    "cert_1060": ["job_0073", "job_0074"],   # ITQ C급
    "cert_1086": ["job_0073", "job_0074"],   # PC Master
    "cert_1087": ["job_0073", "job_0074", "job_0020"],  # PC정비사 1급
    "cert_1088": ["job_0073", "job_0074"],   # PC정비사 2급
    "cert_1111": ["job_0073", "job_0074"],   # DIAT 중급
    "cert_1112": ["job_0073", "job_0074"],   # DIAT 고급
    "cert_1117": ["job_0073", "job_0074"],   # DIAT 초급
    "cert_1203": ["job_0073", "job_0074"],   # e-Test 1급
    "cert_1204": ["job_0073", "job_0074"],   # e-Test 2급
    "cert_1205": ["job_0073", "job_0074"],   # e-Test 3급
    "cert_1206": ["job_0073", "job_0074"],   # e-Test 4급

    # ── domain_0002 인터넷 윤리 자격 ──────────────────────────────────────────
    "cert_1077": ["job_0073", "job_0074"],   # IEQ 2급
    "cert_1078": ["job_0073", "job_0074"],   # IEQ 3급
    "cert_1079": ["job_0101", "job_0103"],   # IEQ 지도사

    # ── domain_0002 SW 테스트 전문 ──────────────────────────────────────────
    "cert_1156": ["job_0019"],   # CSTS 일반
    "cert_1157": ["job_0019"],   # CSTS 고급
    "cert_1158": ["job_0019"],   # CSTS 기본

    # ── domain_0002 리눅스마스터 ──────────────────────────────────────────
    "cert_1114": ["job_0009", "job_0014", "job_0020", "job_0021", "job_0022", "job_0023", "job_0024"],  # 리눅스마스터 1급
    "cert_1115": ["job_0020", "job_0021", "job_0022", "job_0023"],              # 리눅스마스터 2급

    # ── domain_0002 스마트공장 ──────────────────────────────────────────
    "cert_0910": ["job_0018", "job_0036", "job_0037", "job_0038"],  # 스마트공장산업기사
    "cert_0925": ["job_0018", "job_0037", "job_0038"],              # 스마트공장기능사

    # ── domain_0002 멀티미디어콘텐츠 ──────────────────────────────────────────
    "cert_0710": ["job_0120", "job_0124", "job_0125", "job_0127"],  # 멀티미디어콘텐츠제작전문가

    # ── domain_0002 SW/IT 관리 자격 ──────────────────────────────────────────
    "cert_0853": ["job_0073", "job_0083"],   # 기술지도사 정보기술관리
    "cert_1035": ["job_0073", "job_0083"],   # 소프트웨어자산관리사 C-SAM
    "cert_1061": ["job_0073", "job_0083"],   # IT-PMP

    # ── domain_0003 보안/네트워크 ──────────────────────────────────────────
    "cert_0903": ["job_0020", "job_0021", "job_0022", "job_0025", "job_0026", "job_0029"],  # 정보보안산업기사
    "cert_0905": ["job_0020", "job_0021", "job_0022", "job_0025", "job_0026", "job_0029"],  # 정보보안기사
    "cert_1062": ["job_0020", "job_0021", "job_0025", "job_0026", "job_0083"],              # 정보시스템감리사
    "cert_1113": ["job_0020", "job_0022", "job_0025", "job_0026", "job_0029"],              # 디지털포렌식전문가
    "cert_1141": ["job_0020", "job_0021", "job_0022", "job_0023", "job_0025"],              # 네트워크관리사
    "cert_1149": ["job_0022", "job_0025", "job_0029"],                                      # 인터넷보안전문가
    "cert_1152": ["job_0020", "job_0022", "job_0025", "job_0026"],                          # 인터넷정보관리사 1급
    "cert_1153": ["job_0020", "job_0022", "job_0025", "job_0026"],                          # 인터넷정보관리사 전문가
    "cert_1168": ["job_0025", "job_0083"],                                                   # 산업보안관리사
    "cert_1286": ["job_0020", "job_0022", "job_0025"],                                       # 인터넷정보관리사 2급
    "cert_1287": ["job_0020", "job_0021", "job_0025", "job_0026", "job_0083"],              # 정보시스템감사사 CISA
}

# ---------------------------------------------------------------------------
# 2. 키워드 기반 직무 매핑 함수 (domain_0016, domain_0027, domain_0030)
# ---------------------------------------------------------------------------

def resolve_domain_0016(cert_name: str) -> list:
    """금융/회계 domain_0016 cert_name 기반 직무 분리."""
    name = cert_name
    jobs = []
    if any(kw in name for kw in ["세무"]):
        jobs = ["job_0066", "job_0067", "job_0068"]
    elif any(kw in name for kw in ["회계"]):
        jobs = ["job_0067", "job_0068", "job_0069"]
    elif any(kw in name for kw in ["보험"]):
        jobs = ["job_0069", "job_0070", "job_0071", "job_0072"]
    elif any(kw in name for kw in ["금융투자", "증권", "펀드", "투자"]):
        jobs = ["job_0068", "job_0069", "job_0070", "job_0072"]
    elif any(kw in name for kw in ["FP", "재무설계"]):
        jobs = ["job_0068", "job_0069", "job_0070"]
    elif any(kw in name for kw in ["재경"]):
        jobs = ["job_0067", "job_0068"]
    elif any(kw in name for kw in ["감정평가"]):
        jobs = ["job_0086"]
    elif any(kw in name for kw in ["AFPK", "재무"]):
        jobs = ["job_0068", "job_0069", "job_0070"]
    elif any(kw in name for kw in ["신용", "여신"]):
        jobs = ["job_0069", "job_0070", "job_0072"]
    elif any(kw in name for kw in ["손해", "보상"]):
        jobs = ["job_0069", "job_0071", "job_0072"]
    elif any(kw in name for kw in ["원가분석"]):
        jobs = ["job_0067", "job_0068"]
    elif any(kw in name for kw in ["외환"]):
        jobs = ["job_0068", "job_0069", "job_0070"]
    elif any(kw in name for kw in ["TESAT", "테샛", "매경TEST", "경제이해", "경제.금융"]):
        jobs = ["job_0068", "job_0069"]
    else:
        # 기본: 금융사무 전반
        jobs = ["job_0066", "job_0067", "job_0068", "job_0069", "job_0070", "job_0071", "job_0072"]
    return jobs


def resolve_domain_0027(cert_name: str) -> list:
    """교육 domain_0027 cert_name 기반 직무 분리."""
    name = cert_name
    if "한국어" in name:
        return ["job_0104"]
    if any(kw in name for kw in ["직업훈련", "훈련교사", "직업능력"]):
        return ["job_0103", "job_0097"]
    if "평생교육" in name:
        return ["job_0102"]
    if any(kw in name for kw in ["교육사", "교육전문가", "문화예술교육", "환경교육"]):
        return ["job_0101", "job_0102"]
    if any(kw in name for kw in ["사서", "기록"]):
        return ["job_0083", "job_0101"]
    if any(kw in name for kw in ["청소년", "유아", "어린이"]):
        return ["job_0096", "job_0101"]
    if any(kw in name for kw in ["이러닝운영"]):
        return ["job_0102", "job_0103"]
    if any(kw in name for kw in ["논술지도", "독서지도", "실천예절지도"]):
        return ["job_0101"]
    if any(kw in name for kw in ["산림교육", "목재교육", "유아숲"]):
        return ["job_0101", "job_0135"]
    if any(kw in name for kw in ["소방안전교육"]):
        return ["job_0101", "job_0042"]
    if any(kw in name for kw in ["한국사능력"]):
        return ["job_0083", "job_0101"]
    if any(kw in name for kw in ["문예창작"]):
        return ["job_0101", "job_0128"]
    if any(kw in name for kw in ["문화선교", "문화유산교육"]):
        return ["job_0101"]
    if any(kw in name for kw in ["보건교육", "가정생활교육"]):
        return ["job_0101", "job_0102"]
    # 교원/교사 등 일반
    return ["job_0101"]


def resolve_domain_0030(cert_name: str) -> list:
    """조리/식품 domain_0030 cert_name 기반 직무 분리."""
    name = cert_name
    if any(kw in name for kw in ["제과"]):
        return ["job_0109"]
    if any(kw in name for kw in ["제빵"]):
        return ["job_0109"]
    if any(kw in name for kw in ["바리스타", "조주", "소믈리에"]):
        return ["job_0110"]
    if any(kw in name for kw in ["영양", "급식"]):
        return ["job_0112"]
    if any(kw in name for kw in ["식품기술사", "식품안전", "식품산업기사", "식품가공",
                                   "식품위생", "수산제조", "식육가공", "홍삼제조"]):
        return ["job_0111", "job_0112"]
    if any(kw in name for kw in ["식품"]):
        return ["job_0111"]
    if any(kw in name for kw in ["푸드코디"]):
        return ["job_0113"]
    # 떡제조, 조리 계열 일반
    return ["job_0108", "job_0113"]


# ---------------------------------------------------------------------------
# 3. cert_id → primary_domain, cert_name 인덱스 구축
# ---------------------------------------------------------------------------

def build_cert_index(candidates_path: str) -> dict:
    """cert_id → {cert_name, primary_domain} 인덱스."""
    index = {}
    with open(candidates_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            index[obj["cert_id"]] = {
                "cert_name": obj.get("cert_name", ""),
                "primary_domain": obj.get("primary_domain", ""),
            }
    return index


# ---------------------------------------------------------------------------
# 4. cert_id → 도메인 인덱스 (cert_domain_mapping.csv 기반)
# ---------------------------------------------------------------------------

def build_domain_index(cdm_path: str) -> dict:
    """cert_id → list of domain_id."""
    index = defaultdict(list)
    with open(cdm_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("is_active", "True") == "True":
                index[row["cert_id"]].append(row["domain_sub_label_id"])
    return dict(index)


# ---------------------------------------------------------------------------
# 5. cert_job_mapping.csv 로드
# ---------------------------------------------------------------------------

def load_cjm(cjm_path: str) -> list:
    with open(cjm_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


# ---------------------------------------------------------------------------
# 6. 새 직무 결정 로직
# ---------------------------------------------------------------------------

def determine_new_jobs(cert_id: str, cert_info: dict, existing_jobs: list) -> list:
    """
    cert_id에 대한 새 직무 목록을 반환한다.
    - EXPLICIT_REMAP에 있으면 그것을 사용
    - domain_0016 / domain_0027 / domain_0030이면 키워드 매칭 사용
    - 그 외는 existing_jobs 유지
    """
    if cert_id in EXPLICIT_REMAP:
        return EXPLICIT_REMAP[cert_id]

    domain = cert_info.get("primary_domain", "")
    cert_name = cert_info.get("cert_name", "")

    if domain == "domain_0016":
        return resolve_domain_0016(cert_name)
    if domain == "domain_0027":
        return resolve_domain_0027(cert_name)
    if domain == "domain_0030":
        return resolve_domain_0030(cert_name)

    # 변경 없음
    return existing_jobs


# ---------------------------------------------------------------------------
# 7. 메인 처리
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("cert_job_mapping.csv 재매핑 시작")
    print("=" * 60)

    # 파일 로드
    cert_index = build_cert_index(CANDIDATES_PATH)
    domain_index = build_domain_index(CDM_PATH)
    cjm_rows = load_cjm(CJM_PATH)

    # 백업
    bak_path = CJM_PATH + ".bak"
    shutil.copy2(CJM_PATH, bak_path)
    print(f"백업 생성: {bak_path}")

    # 기존 cert_id → job list 인덱스
    old_cert_jobs = defaultdict(list)
    for row in cjm_rows:
        old_cert_jobs[row["cert_id"]].append(row["job_role_id"])

    # 변경 대상 집계
    changed_certs = []
    unchanged_certs = []

    new_cert_jobs = {}  # cert_id → [job_id, ...]
    for cert_id, old_jobs in old_cert_jobs.items():
        info = cert_index.get(cert_id, {"cert_name": "", "primary_domain": ""})
        new_jobs = determine_new_jobs(cert_id, info, old_jobs)
        new_cert_jobs[cert_id] = new_jobs

        if sorted(new_jobs) != sorted(old_jobs):
            changed_certs.append(cert_id)
        else:
            unchanged_certs.append(cert_id)

    # 도메인별 통계 (변경 전)
    print("\n[변경 전] 도메인별 cert unique-job-set 수:")
    _print_domain_stats(old_cert_jobs, cert_index)

    # 새 행 생성 (기존 최대 번호 이후부터 신규 relation_id 부여)
    max_id = max(int(r["relation_id"].replace("cjm_", "")) for r in cjm_rows)

    # 변경 없는 cert 행은 기존 relation_id 재사용
    # 변경 있는 cert 행은 새 relation_id로 교체

    # 기존 cert_id → relation_id 목록 인덱스 (변경 없는 cert용)
    old_cert_relation_ids = defaultdict(list)
    for row in cjm_rows:
        old_cert_relation_ids[row["cert_id"]].append(row["relation_id"])

    new_rows = []
    next_id = max_id  # 변경 cert에 사용할 카운터

    all_cert_ids_in_order = list(dict.fromkeys(r["cert_id"] for r in cjm_rows))

    for cert_id in all_cert_ids_in_order:
        jobs = new_cert_jobs[cert_id]
        if cert_id in changed_certs:
            # 신규 relation_id 발당
            for job_id in jobs:
                next_id += 1
                new_rows.append({
                    "relation_id": f"cjm_{next_id:05d}",
                    "cert_id": cert_id,
                    "job_role_id": job_id,
                    "is_active": "True",
                })
        else:
            # 기존 행 순서대로 재사용 (job 순서 맞춤)
            old_rels = old_cert_relation_ids[cert_id]
            for i, job_id in enumerate(jobs):
                rel_id = old_rels[i] if i < len(old_rels) else f"cjm_{next_id + 1:05d}"
                if i >= len(old_rels):
                    next_id += 1
                new_rows.append({
                    "relation_id": rel_id,
                    "cert_id": cert_id,
                    "job_role_id": job_id,
                    "is_active": "True",
                })

    # CSV 저장
    with open(CJM_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["relation_id", "cert_id", "job_role_id", "is_active"])
        writer.writeheader()
        writer.writerows(new_rows)

    print(f"\ncert_job_mapping.csv 저장 완료: {len(new_rows)} 행")

    # 도메인별 통계 (변경 후)
    new_cert_jobs_for_stats = defaultdict(list, new_cert_jobs)
    print("\n[변경 후] 도메인별 cert unique-job-set 수:")
    _print_domain_stats(new_cert_jobs_for_stats, cert_index)

    # 변경 요약
    print(f"\n변경된 cert 수: {len(changed_certs)}")
    print(f"변경 없는 cert 수: {len(unchanged_certs)}")
    if changed_certs:
        print("\n변경된 cert 목록 (cert_id | cert_name | 이전→이후 직무수):")
        for cid in changed_certs:
            old_j = sorted(old_cert_jobs[cid])
            new_j = sorted(new_cert_jobs[cid])
            name = cert_index.get(cid, {}).get("cert_name", "?")
            print(f"  {cid} | {name:<40} | {len(old_j)} → {len(new_j)}")

    # ---------------------------------------------------------------------------
    # 8. cert_candidates.jsonl 업데이트
    # ---------------------------------------------------------------------------
    print("\ncert_candidates.jsonl 업데이트 중...")
    _update_candidates(CANDIDATES_PATH, new_cert_jobs, cert_index)

    # ---------------------------------------------------------------------------
    # 9. build_frontend_data.py 실행
    # ---------------------------------------------------------------------------
    print("\nbuild_frontend_data.py 실행 중...")
    result = subprocess.run(
        [sys.executable, BUILD_SCRIPT],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("[ERROR] build_frontend_data.py 실패:")
        print(result.stderr)
    else:
        print("build_frontend_data.py 완료.")

    print("\n완료.")


# ---------------------------------------------------------------------------
# 헬퍼: 도메인별 통계 출력
# ---------------------------------------------------------------------------

def _print_domain_stats(cert_jobs: dict, cert_index: dict):
    """도메인별 cert unique-job-set 집계."""
    domain_cert_job_sets = defaultdict(list)
    for cert_id, jobs in cert_jobs.items():
        domain = cert_index.get(cert_id, {}).get("primary_domain", "unknown")
        domain_cert_job_sets[domain].append(frozenset(jobs))

    for domain in sorted(domain_cert_job_sets.keys()):
        job_sets = domain_cert_job_sets[domain]
        unique_sets = len(set(job_sets))
        total_certs = len(job_sets)
        print(f"  {domain}: {total_certs} certs, {unique_sets} unique job-sets")


# ---------------------------------------------------------------------------
# 헬퍼: cert_candidates.jsonl related_jobs 갱신
# ---------------------------------------------------------------------------

JOB_LABEL_MAP = {
    "job_0001": "데이터분석", "job_0002": "데이터엔지니어", "job_0003": "데이터사이언스",
    "job_0004": "BI/리포팅", "job_0005": "AI개발", "job_0006": "머신러닝엔지니어",
    "job_0007": "MLOps", "job_0008": "AI서비스기획",
    "job_0009": "백엔드개발", "job_0010": "프론트엔드개발", "job_0011": "풀스택개발",
    "job_0012": "웹개발", "job_0013": "모바일앱개발", "job_0014": "API/서버개발",
    "job_0015": "게임개발", "job_0016": "게임서버개발", "job_0017": "클라이언트개발",
    "job_0018": "임베디드개발", "job_0019": "테스트/QA엔지니어",
    "job_0020": "시스템운영", "job_0021": "서버운영", "job_0022": "네트워크운영",
    "job_0023": "클라우드엔지니어", "job_0024": "DevOps엔지니어", "job_0025": "정보보안",
    "job_0026": "데이터베이스운영", "job_0027": "정보통신엔지니어", "job_0028": "무선통신운영",
    "job_0029": "디지털포렌식",
    "job_0030": "전기엔지니어", "job_0031": "전자엔지니어", "job_0032": "반도체장비",
    "job_0033": "제어/PLC엔지니어",
    "job_0034": "기계설계", "job_0035": "기계정비", "job_0036": "생산관리",
    "job_0037": "생산기술", "job_0038": "공정관리", "job_0039": "품질관리",
    "job_0040": "비파괴검사", "job_0041": "산업안전관리", "job_0042": "소방/방재관리",
    "job_0043": "환경관리", "job_0044": "에너지설비운영", "job_0045": "원자력기술",
    "job_0046": "건축설계", "job_0047": "건축시공", "job_0048": "실내건축",
    "job_0049": "토목설계", "job_0050": "도시계획", "job_0051": "측량/GIS",
    "job_0052": "현장관리", "job_0053": "건설안전관리", "job_0054": "국가유산보존수리",
    "job_0055": "철도운영/정비", "job_0056": "철도신호", "job_0057": "철도차량정비",
    "job_0058": "자동차정비", "job_0059": "자동차진단평가",
    "job_0060": "선박운항", "job_0061": "선박기관", "job_0062": "선박정비",
    "job_0063": "항공운항", "job_0064": "항공정비",
    "job_0065": "물류/운송운영",
    "job_0066": "세무", "job_0067": "회계", "job_0068": "재무", "job_0069": "금융사무",
    "job_0070": "자산관리", "job_0071": "보험보상", "job_0072": "리스크관리",
    "job_0073": "경영지원", "job_0074": "일반사무", "job_0075": "인사", "job_0076": "총무",
    "job_0077": "마케팅", "job_0078": "영업관리",
    "job_0079": "무역사무", "job_0080": "물류관리", "job_0081": "유통관리",
    "job_0082": "공공행정", "job_0083": "정책기획/평가",
    "job_0084": "법무사무",
    "job_0085": "부동산/주택관리", "job_0086": "감정평가",
    "job_0087": "간호사", "job_0088": "보건의료정보", "job_0089": "병원행정",
    "job_0090": "의무기록관리", "job_0091": "임상지원", "job_0092": "의료코디네이터",
    "job_0093": "응급구조",
    "job_0094": "사회복지사", "job_0095": "상담사", "job_0096": "청소년지도",
    "job_0097": "직업상담", "job_0098": "복지행정", "job_0099": "사례관리",
    "job_0100": "재활지원",
    "job_0101": "교육", "job_0102": "평생교육", "job_0103": "직업교육", "job_0104": "한국어교육",
    "job_0105": "호텔서비스", "job_0106": "관광통역", "job_0107": "여행기획",
    "job_0108": "조리", "job_0109": "제과/제빵", "job_0110": "바리스타",
    "job_0111": "식품품질관리", "job_0112": "영양/급식", "job_0113": "외식서비스운영",
    "job_0114": "헤어디자인", "job_0115": "메이크업", "job_0116": "피부관리",
    "job_0117": "반려동물관리",
    "job_0118": "스포츠지도", "job_0119": "생활건강관리",
    "job_0120": "시각디자인", "job_0121": "UI/UX디자인", "job_0122": "편집디자인",
    "job_0123": "산업디자인",
    "job_0124": "영상편집", "job_0125": "콘텐츠제작", "job_0126": "방송/미디어제작",
    "job_0127": "3D콘텐츠제작", "job_0128": "문예창작", "job_0129": "인쇄/출판제작",
    "job_0130": "공예/주얼리제작",
    "job_0131": "음악/공연실무",
    "job_0132": "패션제작",
    "job_0133": "농업기술", "job_0134": "스마트팜운영", "job_0135": "산림관리",
    "job_0136": "축산관리", "job_0137": "수산양식",
    "job_0138": "광업/자원개발",
    "job_0139": "국방사업관리", "job_0140": "무인기운용", "job_0141": "폭발물처리",
    "job_0142": "특수안전관리",
}


def _update_candidates(candidates_path: str, new_cert_jobs: dict, cert_index: dict):
    """cert_candidates.jsonl의 related_jobs 및 text 필드를 갱신."""
    updated_path = candidates_path + ".tmp"
    updated_count = 0

    with open(candidates_path, encoding="utf-8") as fin, \
         open(updated_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            cert_id = obj.get("cert_id", "")

            if cert_id in new_cert_jobs:
                old_jobs = obj.get("related_jobs", [])
                new_jobs = new_cert_jobs[cert_id]
                if sorted(old_jobs) != sorted(new_jobs):
                    obj["related_jobs"] = new_jobs
                    # text_for_dense / text_for_sparse 갱신 (직무명 부분)
                    job_labels = [JOB_LABEL_MAP.get(j, j) for j in new_jobs]
                    # text_for_dense: "관련 직무: A, B, C." 패턴 교체
                    old_dense = obj.get("text_for_dense", "")
                    job_str_ko = ", ".join(job_labels)
                    import re
                    obj["text_for_dense"] = re.sub(
                        r"관련 직무: [^.]+\.",
                        f"관련 직무: {job_str_ko}.",
                        old_dense,
                    )
                    # text_for_sparse: cert_name + 직무 + 학과
                    cert_name = obj.get("cert_name", "")
                    majors = " ".join(obj.get("related_majors", []))
                    obj["text_for_sparse"] = f"{cert_name} {' '.join(job_labels)} {majors}".strip()
                    obj["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                    updated_count += 1

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")

    os.replace(updated_path, candidates_path)
    print(f"cert_candidates.jsonl 업데이트 완료: {updated_count}개 항목 변경")


if __name__ == "__main__":
    main()
