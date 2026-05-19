# FOLDER.md

> **파일명**: FOLDER.md  
> **폴더 경로**: `data/canonical/candidates`  
> **최종 수정일**: 2026-04-17 (Phase 4 완료 반영)  
> **문서 해시**: SHA256:TBD  
> **문서 역할**: 디렉터리 스캐폴드 명시서 — 담는 내용·금지·다음 단계 연계  
> **문서 우선순위**: reference (충돌 시 루트 기준 문서 우선)  
> **연관 문서**: DIRECTORY_SPEC.md, DATA_SCHEMA.md, MASTER_MERGE_PLAN.md, FEATURE_SPEC.md  

> **참조 규칙**: 파일이 추가될 때 본 파일과 `MASTER_MERGE_PLAN.md §9`를 같은 작업에서 갱신한다.

---

## 1. 용도

**추천 candidate row** 구조적 추천 입력을 둔다. RAG chunk와 동일 구조로 취급하지 않는다.

---

## 2. 파일 목록 (현황)

| 파일 | 행 수 | 상태 |
|---|---|---|
| `candidates.jsonl.example` | — | 형식 참고용 예시 — 실제 데이터 아님 |
| `cert_candidates.csv` | 1,287행 | ✅ `scripts/build_cert_candidates.py` 생성 (21컬럼, content_hash 포함) |
| `cert_candidates.jsonl` | 1,287행 | ✅ Backend ingestion용 JSONL (중복 게임 자격증 3개 제거, 2026-05-20) |
| `.build_manifest.json` | — | 빌드 증분 manifest (`{candidate_id: content_hash}`) — `HASH_INCREMENTAL_BUILD_GUIDE.md §7.6.1` |

> 생성 스크립트: `scripts/build_cert_candidates.py` (경로 이식성 수정 완료)  
> 추천 동작 검증: `scripts/test_recommendation.py`  
> 스키마: `DATA_SCHEMA.md §9.1 certificate_candidate_row` 참조  
> 증분 재생성: `content_hash` 기반 — 변경 cert만 재처리 가능. 실행 시 `added/updated/removed/unchanged` diff를 stdout에 출력하고 `.build_manifest.json`을 갱신한다.  
> taxonomy 게이트: master CSV ID 기준 자동 검증 — 위반 시 기본 실패, `--allow-violations`로 우회 (`DATA_SCHEMA.md §9.1.1`). 위반 리포트는 `data/canonical/validation/candidates_taxonomy.json`.

---

## 3. 담지 않는 것

- 벡터 임베딩 파일
- 긴 설명 텍스트 단독 저장소
- RAG chunk

## 4. 산출·연계

`data/canonical/candidates` → 추천 API 입력 (`backend/app/services/recommendation_service.py`)

---

## 5. 비고

- 대용량 산출물은 Git 정책(`.gitignore`)과 `HASH_INCREMENTAL_BUILD_GUIDE.md` 증분 원칙을 따른다.

## Audit Findings (by Gemini CLI) - 2026-04-17
- **Issue**: `cert_candidates.jsonl`의 `recommended_risk_stages` 필드에 포함된 데이터가 `risk_stage_master.csv`의 ID와 완전히 일치하는지 검증하는 단계가 배포 전 프로세스에 누락되어 있음.
- **Required Action**: `scripts/evaluation/` 내에 canonical 데이터와 taxonomy 간의 ID 정합성을 체크하는 무결성 검사 스크립트(`check_id_integrity.py`) 구현 필요.
- **Note**: Claude Code는 `cert_candidates.jsonl` 생성 로직 수정 시, 정의되지 않은 `risk_id`가 유입되지 않도록 가드레일 코드를 추가할 것.

