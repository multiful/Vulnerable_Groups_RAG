# Content Hash: SHA256:TBD
"""
작업 2: cert_candidates.jsonl
  2-A: exam_sessions_per_year 필드 추가
  2-B: related_jobs 없는 78개 자격증에 job 매핑 추가
"""
import json
import re

JSONL_PATH = "/Users/baiohelseu/Desktop/Project/Vulnerable_Groups_RAG/data/canonical/candidates/cert_candidates.jsonl"

# 2-B: cert_id -> related_jobs 매핑
JOB_MAPPING = {
    # 한국어교원
    "cert_0875": ["job_0104", "job_0101"],
    "cert_0876": ["job_0104", "job_0101"],
    "cert_0926": ["job_0104", "job_0101"],
    "cert_0960": ["job_0104", "job_0101"],
    # 번역/FLEX
    "cert_1048": ["job_0079", "job_0074"],
    "cert_1050": ["job_0079", "job_0074"],
    "cert_1069": ["job_0079", "job_0074"],
    "cert_1091": ["job_0079", "job_0074"],
    "cert_1092": ["job_0079", "job_0074"],
    "cert_1099": ["job_0079", "job_0074"],
    "cert_1103": ["job_0079", "job_0074"],
    "cert_1104": ["job_0079", "job_0074"],
    "cert_1105": ["job_0079", "job_0074"],
    "cert_1106": ["job_0079", "job_0074"],
    "cert_1159": ["job_0079", "job_0074"],
    "cert_1160": ["job_0079", "job_0074"],
    "cert_1161": ["job_0079", "job_0074"],
    "cert_1179": ["job_0079", "job_0074"],
    "cert_1217": ["job_0079", "job_0074"],
    # KBS/국어/글쓰기
    "cert_1080": ["job_0128", "job_0074"],
    "cert_1082": ["job_0128", "job_0074"],
    "cert_1083": ["job_0128", "job_0074"],
    "cert_1084": ["job_0128", "job_0074"],
    "cert_1085": ["job_0128", "job_0074"],
    "cert_1089": ["job_0128", "job_0074"],
    "cert_1163": ["job_0128", "job_0074"],
    "cert_1182": ["job_0128", "job_0074"],
    "cert_1183": ["job_0128", "job_0074"],
    "cert_1199": ["job_0128", "job_0074"],
    "cert_1202": ["job_0128", "job_0074"],
    "cert_1245": ["job_0128", "job_0074"],
    "cert_1246": ["job_0128", "job_0074"],
    "cert_1247": ["job_0128", "job_0074"],
    "cert_1248": ["job_0128", "job_0074"],
    "cert_1252": ["job_0128", "job_0074"],
    # 한글속기
    "cert_0913": ["job_0074", "job_0082"],
    "cert_0914": ["job_0074", "job_0082"],
    "cert_0915": ["job_0074", "job_0082"],
    # 워드프로세서
    "cert_0908": ["job_0074", "job_0073"],
    # 수화통역사
    "cert_1029": ["job_0094", "job_0100"],
    # 점역교정사
    "cert_1038": ["job_0094", "job_0100"],
    "cert_1054": ["job_0094", "job_0100"],
    "cert_1057": ["job_0094", "job_0100"],
    # 한자 관련
    "cert_1021": ["job_0101", "job_0104"],
    "cert_1022": ["job_0101", "job_0104"],
    "cert_1023": ["job_0101", "job_0104"],
    "cert_1220": ["job_0101", "job_0104"],
    "cert_1221": ["job_0101", "job_0104"],
    "cert_1222": ["job_0101", "job_0104"],
    "cert_1223": ["job_0101", "job_0104"],
    "cert_1224": ["job_0101", "job_0104"],
    "cert_1225": ["job_0101", "job_0104"],
    "cert_1226": ["job_0101", "job_0104"],
    "cert_1227": ["job_0101", "job_0104"],
    "cert_1228": ["job_0101", "job_0104"],
    "cert_1229": ["job_0101", "job_0104"],
    "cert_1230": ["job_0101", "job_0104"],
    "cert_1231": ["job_0101", "job_0104"],
    "cert_1232": ["job_0101", "job_0104"],
    "cert_1233": ["job_0101", "job_0104"],
    "cert_1234": ["job_0101", "job_0104"],
    "cert_1235": ["job_0101", "job_0104"],
    "cert_1236": ["job_0101", "job_0104"],
    "cert_1237": ["job_0101", "job_0104"],
    "cert_1244": ["job_0101", "job_0104"],
    "cert_1249": ["job_0101", "job_0104"],
    "cert_1250": ["job_0101", "job_0104"],
    "cert_1251": ["job_0101", "job_0104"],
    "cert_1253": ["job_0101", "job_0104"],
    "cert_1254": ["job_0101", "job_0104"],
    "cert_1255": ["job_0101", "job_0104"],
    "cert_1274": ["job_0101", "job_0104"],
    "cert_1275": ["job_0101", "job_0104"],
    "cert_1276": ["job_0101", "job_0104"],
    "cert_1277": ["job_0101", "job_0104"],
    "cert_1278": ["job_0101", "job_0104"],
    "cert_1279": ["job_0101", "job_0104"],
    "cert_1280": ["job_0101", "job_0104"],
}

SESSIONS_PATTERN = re.compile(r"연간 검정 횟수:\s*(.+?)\.")

def parse_sessions(text_for_dense: str):
    """text_for_dense에서 exam_sessions_per_year 파싱"""
    if not text_for_dense:
        return None
    m = SESSIONS_PATTERN.search(text_for_dense)
    if not m:
        return None
    val = m.group(1).strip()
    if "상시" in val:
        return 0
    # "연 2회", "연 4회", "2회" 등 숫자 추출
    num_m = re.search(r"(\d+)", val)
    if num_m:
        return int(num_m.group(1))
    return None

def main():
    # 전체 레코드 로드
    records = []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"전체 레코드 수: {len(records)}")

    sessions_ok = 0
    sessions_fail = 0
    sessions_zero = 0
    jobs_updated = 0
    jobs_already_had = 0

    for rec in records:
        # 2-A: exam_sessions_per_year
        text = rec.get("text_for_dense", "")
        parsed = parse_sessions(text)
        rec["exam_sessions_per_year"] = parsed
        if parsed is None:
            sessions_fail += 1
        elif parsed == 0:
            sessions_zero += 1
            sessions_ok += 1
        else:
            sessions_ok += 1

        # 2-B: related_jobs 업데이트
        cert_id = rec.get("cert_id", "")
        if cert_id in JOB_MAPPING:
            existing = rec.get("related_jobs", [])
            if not existing:
                rec["related_jobs"] = JOB_MAPPING[cert_id]
                jobs_updated += 1
            else:
                jobs_already_had += 1

    print(f"\n[2-A] exam_sessions_per_year 파싱 결과:")
    print(f"  성공 (0 포함): {sessions_ok}")
    print(f"  상시(0): {sessions_zero}")
    print(f"  실패(null): {sessions_fail}")

    print(f"\n[2-B] related_jobs 업데이트 결과:")
    print(f"  업데이트됨: {jobs_updated}")
    print(f"  이미 값 있음 (스킵): {jobs_already_had}")
    print(f"  매핑 대상 cert_id 수: {len(JOB_MAPPING)}")

    # 전체 다시 쓰기
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 최종 행 수 확인
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        total = sum(1 for line in f if line.strip())
    print(f"\n최종 JSONL 행 수: {total}")

    # 샘플 확인
    print("\n[샘플] 파싱 결과 일부:")
    sample_ids = ["cert_0875", "cert_0908", "cert_1021", "cert_1037"]
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line.strip())
            if rec.get("cert_id") in sample_ids:
                print(f"  {rec['cert_id']} | {rec['cert_name']} | exam_sessions={rec.get('exam_sessions_per_year')} | related_jobs={rec.get('related_jobs')}")

if __name__ == "__main__":
    main()
