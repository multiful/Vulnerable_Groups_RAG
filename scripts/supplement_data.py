# File: supplement_data.py
# Last Updated: 2026-05-19
# Content Hash: SHA256:TBD
# Role: 데이터 보완 스크립트
#   1) cert_job_mapping.csv — thin job(풀스택/웹/클라이언트/클라우드/DevOps) 보강
#                           — 소방(domain_0014) job 추가
#                           — 섬유/공예/광업 job 추가
#   2) cert_major_mapping.csv — domain→major 매핑으로 related_majors 없는 352개 보충
#   3) cert_candidates.jsonl — related_jobs / related_majors 동기화
#   4) build_frontend_data.py 실행 → cert_candidates.json 재생성

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CERT_JOB_CSV   = ROOT / "data/canonical/relations/cert_job_mapping.csv"
CERT_MAJOR_CSV = ROOT / "data/canonical/relations/cert_major_mapping.csv"
JSONL          = ROOT / "data/canonical/candidates/cert_candidates.jsonl"
JOB_MASTER_CSV = ROOT / "data/processed/master/job_master.csv"
MAJOR_MASTER   = ROOT / "data/processed/master/major_master.csv"
MAJOR_TO_DOM   = ROOT / "data/canonical/relations/major_to_domain.csv"
CERT_DOM_CSV   = ROOT / "data/canonical/relations/cert_domain_mapping.csv"

# ──────────────────────────────────────────────────────────────────────
# §1. Job 추가 매핑 정의
# cert_id → 추가할 job_id 목록 (기존 job은 유지, 중복 방지)
# ──────────────────────────────────────────────────────────────────────

JOB_ADD: dict[str, list[str]] = {
    # ── thin IT jobs 보강 ──
    # job_0011(풀스택), job_0012(웹 개발), job_0017(클라이언트), job_0023(클라우드), job_0024(DevOps)
    "cert_0278": ["job_0011", "job_0023", "job_0024"],        # 정보처리산업기사
    "cert_0892": ["job_0011", "job_0012", "job_0017", "job_0023"],  # 컴퓨터시스템기사
    "cert_0551": ["job_0011", "job_0017"],                    # 프로그래밍기능사
    "cert_0906": ["job_0012", "job_0017"],                    # 정보처리기능사
    "cert_1115": ["job_0024"],                                # 리눅스마스터 2급 → DevOps 추가
    "cert_0135": ["job_0017", "job_0023", "job_0024"],        # 정보처리기사 (클라이언트/클라우드/DevOps)
    "cert_0045": ["job_0023", "job_0024"],                    # 컴퓨터시스템응용기술사
    "cert_0043": ["job_0023", "job_0024"],                    # 정보관리기술사

    # ── 소방 domain_0014 — job_0041(산업안전관리), job_0142(특수 안전관리) 추가 ──
    "cert_0728": ["job_0041", "job_0142"],  # 소방시설관리사
    "cert_0862": ["job_0041", "job_0142"],  # 소방안전관리자 특급
    "cert_0859": ["job_0041"],              # 소방안전관리자 1급
    "cert_0860": ["job_0041"],              # 소방안전관리자 2급
    "cert_0861": ["job_0041"],              # 소방안전관리자 3급
    "cert_0935": ["job_0041", "job_0142"],  # 화재조사관
    "cert_0942": ["job_0041", "job_0142"],  # 방재전문인력
    "cert_1044": ["job_0041", "job_0142"],  # 기업재난관리사
    "cert_1047": ["job_0041", "job_0142"],  # 방재안전관리사

    # ── 섬유/의류 domain_0032 — 생산관리/품질관리 추가 ──
    # 기술사급
    "cert_0038": ["job_0036", "job_0037", "job_0039"],  # 섬유기술사
    "cert_0039": ["job_0036", "job_0037", "job_0039"],  # 의류기술사
    # 기사급
    "cert_0130": ["job_0036", "job_0037", "job_0039"],  # 섬유기계기사
    "cert_0131": ["job_0036", "job_0039"],              # 염색가공기사
    "cert_0132": ["job_0036", "job_0037"],              # 방사기사
    "cert_0133": ["job_0036", "job_0039"],              # 섬유기사
    "cert_0134": ["job_0036", "job_0039", "job_0123"],  # 의류기사 + 산업디자인
    # 산업기사급
    "cert_0236": ["job_0036", "job_0039", "job_0123"],  # 패션머천다이징산업기사

    # ── 공예 domain_0035 — 산업디자인/생산관리 추가 ──
    "cert_0251": ["job_0036", "job_0123"],  # 가구제작산업기사
    "cert_0335": ["job_0123"],              # 귀금속가공산업기사
    "cert_0339": ["job_0123"],              # 보석디자인산업기사
    "cert_0336": ["job_0036"],              # 목공예산업기사

    # ── 광업/자원 domain_0039 — 산업안전관리 추가 ──
    "cert_0152": ["job_0041"],  # 광산보안기사
    "cert_0248": ["job_0041"],  # 광산보안산업기사
    "cert_0112": ["job_0041"],  # 화약류관리기사
    "cert_0247": ["job_0041"],  # 화약류관리산업기사
    "cert_0042": ["job_0041"],  # 화약류관리기술사

    # ── 섬유 산업기사 — 생산관리/품질관리 추가 ──
    "cert_0268": ["job_0036", "job_0039"],  # 방직산업기사
    "cert_0269": ["job_0036", "job_0039"],  # 섬유가공산업기사
    "cert_0270": ["job_0036"],              # 방사산업기사
    "cert_0271": ["job_0039", "job_0123"],  # 섬유디자인산업기사
    "cert_0272": ["job_0036", "job_0037"],  # 섬유기계산업기사
    "cert_0273": ["job_0036", "job_0039"],  # 편물산업기사
    "cert_0274": ["job_0039", "job_0123"],  # 양복산업기사
    "cert_0275": ["job_0039", "job_0123"],  # 한복산업기사
    "cert_0276": ["job_0036", "job_0039"],  # 섬유산업기사
    "cert_0280": ["job_0036", "job_0039", "job_0123"],  # 패션디자인산업기사
    "cert_0281": ["job_0036", "job_0039"],  # 신발산업기사
    "cert_0428": ["job_0036"],              # 방적산업기사
    "cert_0429": ["job_0036"],              # 제직산업기사
}

# ──────────────────────────────────────────────────────────────────────
# §2. domain→major 매핑 키워드 필터 (per domain)
# ──────────────────────────────────────────────────────────────────────

DOMAIN_MAJOR_KEYWORDS: dict[str, list[str]] = {
    "domain_0005": ["전기","전자","반도체","제어","전력","임베디드","회로","계측"],
    "domain_0006": ["기계","금속","설비","제조","주조","자동화","용접","냉동","공조","배관","메카","산업공학","생산"],
    "domain_0008": ["화학","바이오","생명","생물","고분자","환경공학","재료"],
    "domain_0010": ["토목","도시","측량","지적","교통","도로","건설"],
    "domain_0011": ["건축","인테리어","구조","시공","건축공학"],
    "domain_0012": ["환경","대기","수질","소음","폐기물"],
    "domain_0030": ["식품","조리","영양","외식","호텔","제과","제빵"],
    "domain_0032": ["섬유","의류","패션","의상","염색"],
    "domain_0033": ["디자인","시각","미술","광고"],
    "domain_0034": ["영상","방송","미디어","콘텐츠","애니메이션","사진"],
    "domain_0040": ["철도","교통","자동차","운송"],
}
# 키워드 없이 전체 사용 (소규모 도메인)
DOMAIN_MAJOR_ALL: list[str] = [
    "domain_0015",  # 비파괴검사 (11개)
    "domain_0039",  # 광업/자원 (2개)
]
MAX_MAJORS_PER_DOMAIN = 20

# major_to_domain.csv에 없는 도메인 → major_master.csv 직접 키워드 검색
# 형식: domain_id → [(major_name에 포함돼야 할 키워드 목록)]
DOMAIN_DIRECT_MAJOR_KEYWORDS: dict[str, list[str]] = {
    # 1차 패스에서 추가한 도메인들
    "domain_0002": ["소프트웨어공학","컴퓨터공학","게임공학","정보처리","IT정보"],
    "domain_0007": ["신소재","재료공학","세라믹","나노공학","금속재료"],
    "domain_0016": ["금융","세무","회계","경제학","금융공학"],
    "domain_0017": ["경영학","경영정보","행정학","경영대학"],
    "domain_0024": ["사회복지","상담심리","복지학","아동복지"],
    "domain_0028": ["어문","국어국문","영어영문","일어일문","중어중문","불어","독어"],
    "domain_0035": ["공예학","공예디자인","조형예술","공예미술"],
    "domain_0041": ["조선공학","선박해양","조선과","조선기계"],
    "domain_0043": ["항공공학","항공기계","항공우주","드론공학"],
    # 2차 패스 — 남은 225개 도메인 보충
    "domain_0038": ["산업안전","안전공학","보건위생","안전관리"],
    "domain_0027": ["교육학","교육공학","평생교육","유아교육"],
    "domain_0009": ["에너지공학","원자력공학","에너지환경","플랜트"],
    "domain_0023": ["의료공학","임상병리","방사선","물리치료","작업치료"],
    "domain_0013": ["건설기계","기계공학","중장비"],
    "domain_0025": ["체육학","스포츠","생활체육","운동재활"],
    "domain_0029": ["관광학","호텔관광","관광경영","항공서비스"],
    "domain_0021": ["공공행정","행정학","공무원","법학행정"],
    "domain_0037": ["문화재","전통예술","문화유산","보존복원"],
    "domain_0036": ["음악학","공연예술","음악교육","실용음악"],
    "domain_0004": ["통신공학","전기통신","정보통신공학","네트워크"],
    "domain_0001": ["데이터과학","인공지능","AI","머신러닝","빅데이터"],
    "domain_0031": ["미용학","뷰티","메이크업","헤어"],
    "domain_0022": ["법학","법률학","법무","법학전문"],
    "domain_0042": ["항공정비","항공기","항공전자","비행"],
    "domain_0018": ["물류학","유통학","무역학","국제물류","공급망"],
    "domain_0026": ["동물자원","반려동물","동물보건","애완동물"],
    "domain_0003": ["정보보안","보안공학","사이버보안","네트워크보안"],
    "domain_0014": ["소방학","소방안전","방재","재난관리"],
    "domain_0020": ["부동산학","감정평가","주택관리","부동산금융"],
}


# ──────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────

def load_major_names() -> dict[str, str]:
    out: dict[str, str] = {}
    with MAJOR_MASTER.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            out[row["major_id"]] = row["major_name"]
    return out


def load_domain_to_majors() -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    with MAJOR_TO_DOM.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("is_active","") == "True":
                out[row["domain_sub_label_id"]].append(row["major_id"])
    return out


def load_cert_domain() -> dict[str, str]:
    """cert_id → primary_domain"""
    out: dict[str, str] = {}
    with CERT_DOM_CSV.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("is_active","") == "True":
                out[row["cert_id"]] = row["domain_sub_label_id"]
    return out


def load_job_mapping() -> dict[str, set[str]]:
    """cert_id → {job_ids} (is_active=True)"""
    out: dict[str, set[str]] = defaultdict(set)
    with CERT_JOB_CSV.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("is_active","") == "True":
                out[row["cert_id"]].add(row["job_role_id"])
    return out


def load_major_mapping() -> dict[str, set[str]]:
    """cert_id → {major_ids} (is_active=True)"""
    out: dict[str, set[str]] = defaultdict(set)
    with CERT_MAJOR_CSV.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("is_active","") == "True":
                out[row["cert_id"]].add(row["major_id"])
    return out


def write_job_csv(rows: list[dict]) -> None:
    fieldnames = ["relation_id","cert_id","job_role_id","is_active"]
    with CERT_JOB_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_major_csv(rows: list[dict]) -> None:
    fieldnames = ["relation_id","cert_id","major_id","is_active"]
    with CERT_MAJOR_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


# ──────────────────────────────────────────────────────────────────────
# §3. Cert ID → name (for verification)
# ──────────────────────────────────────────────────────────────────────

def load_cert_names_from_jsonl() -> dict[str, str]:
    out: dict[str, str] = {}
    with JSONL.open(encoding="utf-8") as f:
        for line in f:
            if s := line.strip():
                rec = json.loads(s)
                out[rec["cert_id"]] = rec.get("cert_name","")
    return out


# ──────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=== supplement_data.py 시작 ===")

    # backup
    for src in [CERT_JOB_CSV, CERT_MAJOR_CSV, JSONL]:
        bak = src.with_suffix(src.suffix + ".bak2")
        shutil.copy2(src, bak)
    print("백업 완료 (.bak2)")

    cert_names = load_cert_names_from_jsonl()

    # ── §1. cert_job_mapping.csv 보강 ──────────────────────────────────
    print("\n[1/4] cert_job_mapping.csv 보강...")

    # 현재 전체 행 로드
    all_job_rows: list[dict] = []
    with CERT_JOB_CSV.open(encoding="utf-8-sig") as f:
        all_job_rows = list(csv.DictReader(f))

    existing_pairs: set[tuple[str, str]] = set()
    for row in all_job_rows:
        if row.get("is_active","") == "True":
            existing_pairs.add((row["cert_id"], row["job_role_id"]))

    next_rid = max(
        int(re.sub(r"\D","",row["relation_id"]) or 0) for row in all_job_rows
    ) + 1

    added_jobs = 0
    skipped_unknown = 0
    for cert_id, job_ids in JOB_ADD.items():
        cert_name = cert_names.get(cert_id, "")
        if not cert_name:
            print(f"  SKIP (cert_id 없음): {cert_id}")
            skipped_unknown += 1
            continue
        for job_id in job_ids:
            if (cert_id, job_id) in existing_pairs:
                continue
            all_job_rows.append({
                "relation_id": f"cj_{next_rid:05d}",
                "cert_id": cert_id,
                "job_role_id": job_id,
                "is_active": "True",
            })
            existing_pairs.add((cert_id, job_id))
            next_rid += 1
            added_jobs += 1

    write_job_csv(all_job_rows)
    print(f"  추가 행 수: {added_jobs}, cert_id 불명: {skipped_unknown}")

    # ── §2. cert_major_mapping.csv 보충 ────────────────────────────────
    print("\n[2/4] cert_major_mapping.csv 보충 (도메인 기반)...")

    major_names_map = load_major_names()
    dom_to_majors   = load_domain_to_majors()
    cert_domain_map = load_cert_domain()

    # 도메인별 대표 전공 목록 계산 (major_to_domain.csv 기반)
    domain_selected_majors: dict[str, list[str]] = {}
    for dom, kws in DOMAIN_MAJOR_KEYWORDS.items():
        all_m = dom_to_majors.get(dom, [])
        filtered = [m for m in all_m if any(k in major_names_map.get(m,"") for k in kws)]
        domain_selected_majors[dom] = filtered[:MAX_MAJORS_PER_DOMAIN]
    for dom in DOMAIN_MAJOR_ALL:
        domain_selected_majors[dom] = dom_to_majors.get(dom, [])[:MAX_MAJORS_PER_DOMAIN]

    # major_to_domain에 없는 도메인 → major_master.csv 직접 키워드 검색
    for dom, kws in DOMAIN_DIRECT_MAJOR_KEYWORDS.items():
        if dom in domain_selected_majors:
            continue  # 이미 처리됨
        matched = [mid for mid, name in major_names_map.items()
                   if any(k in name for k in kws)]
        domain_selected_majors[dom] = matched[:MAX_MAJORS_PER_DOMAIN]

    # 현재 cert_major_mapping 전체 행 로드
    all_major_rows: list[dict] = []
    with CERT_MAJOR_CSV.open(encoding="utf-8-sig") as f:
        all_major_rows = list(csv.DictReader(f))

    existing_major_pairs: set[tuple[str, str]] = set()
    for row in all_major_rows:
        if row.get("is_active","") == "True":
            existing_major_pairs.add((row["cert_id"], row["major_id"]))

    next_mrid = max(
        int(re.sub(r"\D","",row["relation_id"]) or 0) for row in all_major_rows
    ) + 1

    # 이미 매핑된 cert
    already_mapped = {row["cert_id"] for row in all_major_rows if row.get("is_active","") == "True"}

    added_majors = 0
    certs_supplemented = 0

    for cert_id, dom in cert_domain_map.items():
        if cert_id in already_mapped:
            continue
        selected = domain_selected_majors.get(dom, [])
        if not selected:
            continue
        cert_added = 0
        for mid in selected:
            if (cert_id, mid) in existing_major_pairs:
                continue
            all_major_rows.append({
                "relation_id": f"cmj_{next_mrid:05d}",
                "cert_id": cert_id,
                "major_id": mid,
                "is_active": "True",
            })
            existing_major_pairs.add((cert_id, mid))
            next_mrid += 1
            added_majors += 1
            cert_added += 1
        if cert_added > 0:
            certs_supplemented += 1

    write_major_csv(all_major_rows)
    print(f"  보충된 cert 수: {certs_supplemented}, 추가 행 수: {added_majors}")

    # ── §3. jsonl 동기화 ────────────────────────────────────────────────
    print("\n[3/4] cert_candidates.jsonl 동기화...")

    # 최신 job/major 매핑 다시 로드
    final_job_map  = load_job_mapping()
    final_major_map = load_major_mapping()

    # major_id → major_name
    major_id_to_name: dict[str, str] = major_names_map

    updated_jobs   = 0
    updated_majors = 0
    lines_out: list[str] = []

    with JSONL.open(encoding="utf-8") as f:
        for line in f:
            if not (s := line.strip()):
                continue
            rec = json.loads(s)
            cid = rec.get("cert_id","")
            changed = False

            # related_jobs
            new_jobs = sorted(final_job_map.get(cid, set()))
            if set(rec.get("related_jobs") or []) != set(new_jobs):
                rec["related_jobs"] = new_jobs
                updated_jobs += 1
                changed = True

            # related_majors
            new_major_ids = final_major_map.get(cid, set())
            new_major_names = sorted(
                major_id_to_name.get(mid,"") for mid in new_major_ids
                if major_id_to_name.get(mid,"")
            )
            old_majors = rec.get("related_majors") or []
            if set(old_majors) != set(new_major_names):
                rec["related_majors"] = new_major_names
                updated_majors += 1
                changed = True

            lines_out.append(json.dumps(rec, ensure_ascii=False))

    JSONL.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    print(f"  related_jobs 갱신: {updated_jobs}개")
    print(f"  related_majors 갱신: {updated_majors}개")

    # ── §4. rebuild frontend JSON ───────────────────────────────────────
    print("\n[4/4] build_frontend_data.py 실행...")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_frontend_data.py")],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr, file=sys.stderr)
        return 1

    print("=== supplement_data.py 완료 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
