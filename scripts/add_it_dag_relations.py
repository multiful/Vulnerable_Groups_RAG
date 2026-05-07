# File: add_it_dag_relations.py
# Last Updated: 2026-05-07
# Content Hash: SHA256:TBD
# Role: IT 도메인 자격증 DAG 관계 추가 (소프트웨어개발·데이터/AI·IT인프라/보안·정보통신/무선)
#
# 실행: python scripts/add_it_dag_relations.py
# 증분 처리: 이미 있는 (from, to) pair는 건너뜀. 재실행 안전.
from __future__ import annotations

import csv
import sys
from pathlib import Path

_ROOT = Path(__file__).parents[1]
_OUT_CSV = _ROOT / "data/canonical/relations/cert_to_cert_relation.csv"

# ──────────────────────────────────────────────
# IT 도메인 cert-to-cert 관계 정의
# (from_cert_id, to_cert_id, relation_type, evidence)
# relation_type: prerequisite | recommended_prior | next_step
# ──────────────────────────────────────────────
_IT_RELATIONS: list[tuple[str, str, str, str]] = [
    # ── 정보처리 계열 (소프트웨어개발) ──────────────────
    ("cert_0906", "cert_0278", "recommended_prior", "NCS 국가기술자격 등급 체계: 기능사→산업기사"),
    ("cert_0278", "cert_0135", "recommended_prior", "NCS 국가기술자격 등급 체계: 산업기사→기사"),
    ("cert_0135", "cert_0043", "recommended_prior", "NCS 국가기술자격 등급 체계: 기사→기술사(정보관리)"),
    ("cert_0135", "cert_0045", "recommended_prior", "NCS 국가기술자격 등급 체계: 기사→기술사(컴퓨터시스템응용)"),
    # 프로그래밍기능사·정보기기운용 → 정보처리 산업기사 (관련 계열 진입)
    ("cert_0551", "cert_0278", "recommended_prior", "프로그래밍 기초 취득 후 정보처리 계열 산업기사 권장"),
    ("cert_0547", "cert_0278", "recommended_prior", "정보기기운용 기능사 취득 후 정보처리 산업기사 권장"),

    # ── 컴퓨터시스템 계열 ────────────────────────────────
    ("cert_0897", "cert_0892", "recommended_prior", "NCS 국가기술자격 등급 체계: 전자계산기기능사→컴퓨터시스템기사"),
    ("cert_0892", "cert_0045", "recommended_prior", "NCS 국가기술자격 등급 체계: 기사→기술사(컴퓨터시스템응용)"),

    # ── 정보보안 계열 (IT인프라/보안) ──────────────────
    ("cert_0903", "cert_0905", "recommended_prior", "NCS 국가기술자격 등급 체계: 산업기사→기사(정보보안)"),
    ("cert_0906", "cert_0903", "recommended_prior", "정보처리기능사 취득 후 정보보안 산업기사 권장 진입"),
    ("cert_0278", "cert_0905", "recommended_prior", "정보처리 산업기사 이후 정보보안기사 진입 가능"),

    # ── 방송통신 계열 (정보통신/무선) ──────────────────
    ("cert_0628", "cert_0260", "recommended_prior", "NCS 국가기술자격 등급 체계: 기능사→산업기사(방송통신)"),
    ("cert_0260", "cert_0122", "recommended_prior", "NCS 국가기술자격 등급 체계: 산업기사→기사(방송통신)"),

    # ── 무선설비 계열 ────────────────────────────────────
    ("cert_0546", "cert_0261", "recommended_prior", "NCS 국가기술자격 등급 체계: 기능사→산업기사(무선설비)"),
    ("cert_0261", "cert_0123", "recommended_prior", "NCS 국가기술자격 등급 체계: 산업기사→기사(무선설비)"),

    # ── 전파전자통신 계열 ────────────────────────────────
    ("cert_1290", "cert_1093", "recommended_prior", "NCS 국가기술자격 등급 체계: 기능사→산업기사(전파전자통신)"),
    ("cert_1093", "cert_0902", "recommended_prior", "NCS 국가기술자격 등급 체계: 산업기사→기사(전파전자통신)"),

    # ── 정보통신 계열 ────────────────────────────────────
    ("cert_0258", "cert_0121", "recommended_prior", "NCS 국가기술자격 등급 체계: 산업기사→기사(정보통신)"),
    ("cert_0121", "cert_0044", "recommended_prior", "NCS 국가기술자격 등급 체계: 기사→기술사(정보통신)"),
    # 정보처리 계열 → 정보통신기사 연계
    ("cert_0278", "cert_0258", "recommended_prior", "정보처리 산업기사와 정보통신 산업기사 병행 취득 권장"),

    # ── 스마트공장 계열 ──────────────────────────────────
    ("cert_0925", "cert_0910", "recommended_prior", "NCS 국가기술자격 등급 체계: 기능사→산업기사(스마트공장)"),

    # ── 데이터/AI 민간자격 계열 ─────────────────────────
    ("cert_1128", "cert_1143", "recommended_prior", "ADsP 취득 후 ADP(데이터분석전문가) 권장 진입 경로"),
    ("cert_1128", "cert_0923", "recommended_prior", "ADsP 기초 취득 후 빅데이터분석기사 권장 진입 경로"),
    ("cert_1207", "cert_1127", "recommended_prior", "DAsP 취득 후 DAP(데이터아키텍처전문가) 권장 진입 경로"),
    ("cert_1131", "cert_1130", "recommended_prior", "SQLD 취득 후 SQLP(SQL전문가) 권장 진입 경로"),
    # 정보처리 → 데이터 계열 진입
    ("cert_0906", "cert_1128", "recommended_prior", "정보처리기능사 취득 후 ADsP 데이터 계열 진입 권장"),
    ("cert_0135", "cert_0923", "recommended_prior", "정보처리기사 취득 후 빅데이터분석기사 병행 권장"),

    # ── SW테스트전문가(CSTS) 계열 ───────────────────────
    ("cert_1158", "cert_1156", "recommended_prior", "CSTS 기본 취득 후 CSTS 일반 진입 (민간자격 등급 체계)"),
    ("cert_1156", "cert_1157", "recommended_prior", "CSTS 일반 취득 후 CSTS 고급 진입 (민간자격 등급 체계)"),
    ("cert_0906", "cert_1158", "recommended_prior", "정보처리기능사 취득 후 SW테스트전문가 기본 진입 권장"),
]


def load_existing(path: Path) -> tuple[list[dict], set[tuple[str, str]], int]:
    rows = []
    existing_pairs: set[tuple[str, str]] = set()
    max_num = 0
    with path.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
            existing_pairs.add((r["from_cert_id"], r["to_cert_id"]))
            try:
                num = int(r["relation_id"].replace("c2c_", ""))
                max_num = max(max_num, num)
            except ValueError:
                pass
    return rows, existing_pairs, max_num


def main() -> None:
    if not _OUT_CSV.exists():
        print(f"ERROR: {_OUT_CSV} 없음. 먼저 build_cert_to_cert_relation.py를 실행하세요.")
        sys.exit(1)

    existing_rows, existing_pairs, max_num = load_existing(_OUT_CSV)
    print(f"기존 관계: {len(existing_rows)}개, max id: c2c_{max_num:05d}")

    new_rows = []
    skipped = 0
    counter = max_num + 1

    for from_id, to_id, rel_type, evidence in _IT_RELATIONS:
        if (from_id, to_id) in existing_pairs:
            skipped += 1
            continue
        new_rows.append({
            "relation_id": f"c2c_{counter:05d}",
            "from_cert_id": from_id,
            "to_cert_id": to_id,
            "relation_type": rel_type,
            "reasoning_evidence": evidence,
            "source": "it_domain_manual",
            "confidence": "0.90",
            "is_active": "True",
        })
        existing_pairs.add((from_id, to_id))
        counter += 1

    print(f"추가: {len(new_rows)}개, 건너뜀(중복): {skipped}개")

    if not new_rows:
        print("추가할 관계 없음. 종료.")
        return

    all_rows = existing_rows + new_rows
    fieldnames = ["relation_id", "from_cert_id", "to_cert_id", "relation_type",
                  "reasoning_evidence", "source", "confidence", "is_active"]

    with _OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"저장 완료: {_OUT_CSV} (총 {len(all_rows)}개)")
    print("\n추가된 관계 목록:")
    for r in new_rows:
        print(f"  {r['relation_id']} | {r['from_cert_id']} → {r['to_cert_id']} | {r['relation_type']}")


if __name__ == "__main__":
    main()
