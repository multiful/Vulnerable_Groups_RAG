# Content Hash: SHA256:TBD
"""
작업 1: cert_to_cert_relation.csv에 DAG 관계 추가
"""
import csv
import os

CSV_PATH = "/Users/baiohelseu/Desktop/Project/Vulnerable_Groups_RAG/data/canonical/relations/cert_to_cert_relation.csv"

# 추가할 관계 목록 (from_cert_id, to_cert_id, relation_type, reasoning_evidence)
NEW_RELATIONS_RAW = [
    # 미용/패션
    ("cert_0671", "cert_0457", "recommended_prior", "NCS 미용 자격 체계 기준"),
    ("cert_0685", "cert_0457", "recommended_prior", "NCS 미용 자격 체계 기준"),
    ("cert_0687", "cert_0457", "recommended_prior", "NCS 미용 자격 체계 기준"),
    ("cert_0689", "cert_0457", "recommended_prior", "NCS 미용 자격 체계 기준"),
    ("cert_0691", "cert_0457", "recommended_prior", "NCS 미용 자격 체계 기준"),
    ("cert_0457", "cert_0388", "next_step", "NCS 미용 자격 체계 기준"),
    ("cert_0672", "cert_0458", "recommended_prior", "NCS 이용 자격 체계 기준"),
    ("cert_0458", "cert_0389", "next_step", "NCS 이용 자격 체계 기준"),
    # 금융/회계
    ("cert_0896", "cert_0895", "next_step", "전산회계운용사 등급 체계"),
    ("cert_0895", "cert_0894", "next_step", "전산회계운용사 등급 체계"),
    ("cert_1037", "cert_1018", "next_step", "전산세무회계 등급 체계"),
    ("cert_1016", "cert_1015", "next_step", "전산세무회계 등급 체계"),
    ("cert_1018", "cert_1016", "recommended_prior", "회계 기반 세무 체계"),
    ("cert_1028", "cert_1026", "next_step", "세무회계 등급 체계"),
    ("cert_1026", "cert_1025", "next_step", "세무회계 등급 체계"),
    ("cert_1285", "cert_1284", "next_step", "회계관리 등급 체계"),
    ("cert_1033", "cert_1034", "recommended_prior", "신용 전문화 체계"),
    ("cert_1051", "cert_1167", "next_step", "보험심사평가사 등급 체계"),
    ("cert_1272", "cert_1273", "next_step", "외환전문역 등급 체계"),
    ("cert_1137", "cert_1136", "next_step", "TESAT 등급 체계"),
    ("cert_1136", "cert_1135", "next_step", "TESAT 등급 체계"),
    ("cert_1135", "cert_1134", "next_step", "TESAT 등급 체계"),
    ("cert_1118", "cert_1116", "next_step", "매경TEST 등급 체계"),
    ("cert_1243", "cert_1242", "next_step", "주니어TESAT 등급 체계"),
    ("cert_1242", "cert_1241", "next_step", "주니어TESAT 등급 체계"),
    ("cert_1241", "cert_1240", "next_step", "주니어TESAT 등급 체계"),
    ("cert_1132", "cert_1139", "recommended_prior", "보험심사역 전문화"),
    # 경영/사무
    ("cert_0922", "cert_0921", "next_step", "비서 등급 체계"),
    ("cert_0921", "cert_0920", "next_step", "비서 등급 체계"),
    ("cert_0901", "cert_0907", "recommended_prior", "전자상거래 체계"),
    ("cert_0907", "cert_0900", "next_step", "전자상거래 등급 체계"),
    ("cert_0699", "cert_0698", "next_step", "사회조사분석사 등급 체계"),
    ("cert_0701", "cert_0700", "next_step", "컨벤션기획사 등급 체계"),
    ("cert_0703", "cert_0702", "next_step", "소비자전문상담사 등급 체계"),
    ("cert_1102", "cert_1101", "next_step", "ERP 등급 체계"),
    ("cert_1098", "cert_1097", "next_step", "ERP 등급 체계"),
    ("cert_1096", "cert_1095", "next_step", "ERP 등급 체계"),
    ("cert_1107", "cert_1100", "next_step", "ERP 등급 체계"),
    ("cert_1129", "cert_1110", "next_step", "SMAT 등급 체계"),
    ("cert_1110", "cert_1109", "next_step", "SMAT 등급 체계"),
    ("cert_1283", "cert_1282", "next_step", "행정관리사 등급 체계"),
    ("cert_1282", "cert_1281", "next_step", "행정관리사 등급 체계"),
    # 사회복지/상담
    ("cert_0697", "cert_0696", "next_step", "직업상담사 등급 체계"),
    ("cert_0750", "cert_0749", "next_step", "장례지도사 등급 체계"),
    ("cert_0943", "cert_0754", "next_step", "장애인재활상담사 등급 체계"),
    ("cert_0754", "cert_0753", "next_step", "장애인재활상담사 등급 체계"),
    ("cert_0952", "cert_0951", "next_step", "청소년상담사 등급 체계"),
    ("cert_0951", "cert_0950", "next_step", "청소년상담사 등급 체계"),
    ("cert_1162", "cert_1260", "next_step", "가족상담사 등급 체계"),
    ("cert_1260", "cert_1259", "next_step", "가족상담사 등급 체계"),
    ("cert_1259", "cert_1155", "next_step", "가족상담사 등급 체계"),
    ("cert_0705", "cert_0704", "next_step", "임상심리사 등급 체계"),
    # 의료/보건
    ("cert_0775", "cert_0781", "next_step", "응급구조사 등급 체계"),
    ("cert_0737", "cert_0726", "next_step", "언어재활사 등급 체계"),
    ("cert_0965", "cert_0964", "next_step", "정신건강임상심리사 등급 체계"),
    # 교육
    ("cert_0959", "cert_0958", "next_step", "평생교육사 등급 체계"),
    ("cert_0958", "cert_0957", "next_step", "평생교육사 등급 체계"),
    ("cert_0962", "cert_0955", "next_step", "청소년지도사 등급 체계"),
    ("cert_0955", "cert_0953", "next_step", "청소년지도사 등급 체계"),
    ("cert_0746", "cert_0782", "next_step", "보건교육사 등급 체계"),
    ("cert_0782", "cert_0818", "next_step", "보건교육사 등급 체계"),
    ("cert_0763", "cert_0756", "next_step", "정사서 등급 체계"),
    ("cert_0948", "cert_0856", "next_step", "직업능력개발훈련교사 등급 체계"),
    ("cert_0856", "cert_0927", "next_step", "직업능력개발훈련교사 등급 체계"),
    ("cert_0928", "cert_0999", "next_step", "문화예술교육사 등급 체계"),
    ("cert_0985", "cert_0984", "next_step", "환경교육사 등급 체계"),
]

def main():
    # 기존 관계 로드 (중복 확인용)
    existing_pairs = set()
    last_id_num = 1037

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        for row in rows:
            key = (row["from_cert_id"], row["to_cert_id"], row["relation_type"])
            existing_pairs.add(key)
            # 마지막 relation_id 번호 추출
            rid = row["relation_id"]
            num = int(rid.split("_")[1])
            if num > last_id_num:
                last_id_num = num

    print(f"기존 관계 수: {len(existing_pairs)}, 마지막 ID: c2c_{last_id_num:05d}")

    # 중복 제거 후 추가할 관계 필터링
    # 먼저 추가할 목록 자체에서 중복 제거
    seen_new = set()
    deduped_new = []
    for item in NEW_RELATIONS_RAW:
        key = (item[0], item[1], item[2])
        if key not in seen_new:
            seen_new.add(key)
            deduped_new.append(item)

    to_add = []
    skipped = []
    for item in deduped_new:
        key = (item[0], item[1], item[2])
        if key in existing_pairs:
            skipped.append(item)
        else:
            to_add.append(item)

    print(f"추가할 관계 수 (중복 제거 후): {len(to_add)}")
    print(f"이미 존재하여 스킵: {len(skipped)}")
    if skipped:
        for s in skipped:
            print(f"  SKIP: {s}")

    # 새 rows 생성
    new_rows = []
    current_id = last_id_num
    for item in to_add:
        current_id += 1
        new_rows.append({
            "relation_id": f"c2c_{current_id:05d}",
            "from_cert_id": item[0],
            "to_cert_id": item[1],
            "relation_type": item[2],
            "reasoning_evidence": item[3],
            "source": "domain_manual",
            "confidence": "0.85",
            "is_active": "True",
        })

    if not new_rows:
        print("추가할 새 관계가 없습니다.")
        return

    # CSV append
    fieldnames = ["relation_id", "from_cert_id", "to_cert_id", "relation_type",
                  "reasoning_evidence", "source", "confidence", "is_active"]

    with open(CSV_PATH, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for row in new_rows:
            writer.writerow(row)

    # 결과 확인
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        total_lines = sum(1 for _ in f)
    print(f"최종 CSV 행 수 (헤더 포함): {total_lines}")
    print(f"추가된 관계: {len(new_rows)}개 (c2c_{last_id_num+1:05d} ~ c2c_{current_id:05d})")

if __name__ == "__main__":
    main()
