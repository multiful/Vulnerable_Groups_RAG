# FOLDER.md

> **파일명**: FOLDER.md  
> **폴더 경로**: `data/processed/master`  
> **최종 수정일**: 2026-06-30  
> **문서 해시**: SHA256:TBD  
> **문서 역할**: 디렉터리 스캐폴드 명시서 — 담는 내용·금지·다음 단계 연계  
> **문서 우선순위**: reference (충돌 시 루트 기준 문서 우선)  
> **연관 문서**: DIRECTORY_SPEC.md, DATA_SCHEMA.md, CSV_CANONICALIZATION_TEAM_GUIDE.md, MASTER_MERGE_PLAN.md, README.md, CHANGE_CONTROL.md  

> **참조 규칙**: master 산출물 규칙이 바뀌면 본 파일과 `DIRECTORY_SPEC.md`, `MASTER_MERGE_PLAN.md`를 같은 작업에서 갱신한다.

---

## 1. 용도

raw CSV에서 정제된 **master 중간 산출물**을 둔다.

---

## 2. 파일 목록 (현황)

| 파일 | 행 수 | ID 형식 | 상태 |
|---|---|---|---|
| `cert_master.csv` | 1,290 | cert_0001~ | ✅ 22컬럼 (exam_frequency 재보강 필요) |
| `cert_alias.csv` | 159 | cert_id 재매핑 | ✅ |
| `domain_master.csv` | 43 | domain_0001~ | ✅ |
| `job_master.csv` | 142 | job_0001~ | ✅ |
| `major_master.csv` | 8,113 | major_qnet_XXXX | ✅ |
| `hosting_org_master.csv` | 61 | hosting_org_0001~ | ✅ |
| `ncs_master.csv` | 261 | ncs_0001~ | ✅ |
| `risk_stage_master.csv` | 5 | risk_0001~ | ✅ |
| `roadmap_stage_master.csv` | 5 | roadmap_stage_0001~ | ✅ |
| `target_group_master.csv` | 5 | tg_0001~ | ✅ 지원 대상 유형(고립위험청년~은둔청년+가족) |
| `support_program_master.csv` | 16 | sp_0001~ | ✅ 지원 제도(이미지 표 12 기준) |
| `MASTER_MERGE_PLAN.md` | — | — | 전체 빌드 진행 현황 체크리스트 |

---

## 3. cert_master.csv 컬럼 현황

| 컬럼 | 상태 |
|---|---|
| cert_id, cert_name, canonical_name, normalized_key | ✅ |
| aliases | ⬜ 미입력 |
| issuer, is_active, cert_type, grade_name | ✅ |
| cert_grade_tier | ✅ 718/1,290 (빈값 = 비기술자격) |
| primary_domain, top_domain, domain_name_raw | ✅ |
| source | ✅ |
| written_avg_pass_rate, practical_avg_pass_rate, avg_pass_rate_3yr | ✅ 부분 (소스 없는 자격증 빈값 허용) |
| exam_difficulty | 🔄 617/1,290 |
| exam_type_info | 🔄 669/1,290 |
| exam_subject_info | 🔄 669/1,290 |
| exam_pass_rate | 🔄 698/1,290 |
| exam_frequency | ❌ 14/1,290 — `검정 횟수` 매핑 수정 필요 (B-5 잔여) |

> 시험 일정·수수료·응시자격은 CSV 담지 않음 — RAG 레이어(PDF)에서 제공.

---

## 4. 담지 않는 것

- 원천 원본 rows 데이터 → `data/raw/csv/*_rows.csv`
- 엔티티/관계 canonical 최종본 → `data/canonical/*`
- 시험 일정, 수수료, 응시자격 상세 텍스트 → RAG 레이어 담당

## 5. 산출·연계

`data/processed/master` → `data/canonical/relations` → `data/canonical/candidates` 순으로 연계한다.

---

## 6. 비고

- 이 폴더의 변경 이력은 `MASTER_MERGE_PLAN.md`에서 관리한다.
- 대용량 원본·산출물은 Git 정책(`.gitignore`)과 `HASH_INCREMENTAL_BUILD_GUIDE.md` 증분 원칙을 따른다.
