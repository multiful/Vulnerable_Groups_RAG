# DEV_LOG.md

> **파일명**: DEV_LOG.md  
> **최종 수정일**: 2026-05-07  
> **문서 해시**: SHA256:TBD
> **문서 역할**: 날짜별 진행 로그, 변경 요약, 해결 이력  
> **문서 우선순위**: 14  
> **연관 문서**: CHANGE_CONTROL.md, PRD.md, DIRECTORY_SPEC.md, ERROR_ANALYSIS.md  
> **참조 규칙**: 구조·스캐폴딩·중요 결정은 날짜 역순으로 짧게 남긴다. 상세 실패 분석은 `ERROR_ANALYSIS.md`로 옮길 수 있다.

---

## 1. 문서 목적

구현과 문서 정렬 작업의 **타임라인**을 남겨, 이후 기여자가 맥락을 잃지 않게 한다.

---

## 2026-05-07 — 핵심 3단계 플로우 기준으로 기획 문서 전면 정렬

### 변경 문서
- `README.md`: 핵심 3단계 사용자 흐름(설문→도메인+직무선택→로드맵) 명시, 설문 방식·Safety Override 표기 추가, 온라인 서빙 계층 표 추가
- `PRD.md`: §2 제품 정의에 3단계 흐름 블록 추가, §7.1에 12문항 설문 구조표·Safety Override 명시, §8.1 설문 방식 명시, §11 시나리오 1을 3단계 순서 흐름으로 재작성
- `SYSTEM_ARCHITECTURE.md`: §6 Frontend 활성 범위에 InterestSelection 추가, 핵심 3단계 흐름도 추가, §12 Online Runtime Flow를 3단계 흐름으로 재작성
- `FEATURE_SPEC.md`: F-01을 "12문항 설문 방식" 명세로 전면 재작성(카테고리별 문항표·Safety Override·판정 로직), F-02를 "InterestSelection" 명세로 재작성(도메인 필수·직무 선택·URL 파라미터 전달), 기능 목록 테이블 업데이트

### 배경
- 실제 구현된 웹 플로우(RiskAssessment → InterestSelection → Roadmap)와 기획 문서 간 불일치 발견
- 특히 SYSTEM_ARCHITECTURE.md에 InterestSelection 페이지 누락, F-01·F-02 명세가 설문 방식과 도메인+직무 동시 선택 방식을 반영 안 함
- 사용자 확인 요구: "설문→진단→직무+도메인선택→로드맵 추천" 3단계 플로우가 맞는지 검토 후 문서 전면 업데이트

### 잔여 이슈 (코드 변경 필요)
- InterestSelection 직무(job) 선택 UI 미구현 → F-02에 "추가 구현 필요"로 표기
- components/Survey.tsx 미사용 파일 (RiskAssessment/index.tsx가 설문 직접 포함) → 별도 정리 필요
- Home 이용 흐름이 4단계로 표시 → 3단계 기준으로 UI 수정 검토 필요

---

## 2026-04-27 — 앱 진입 설문 12문항 + 1~5단계 위험도 스코어링 설계

### 개요
- 산출물 위치: `experiments/reports/2026-04-27_isolation_survey_design/` (입구는 `00_README.md`)
- 입력: `data/raw/csv/★TABLE_서울시 고립은둔청년 실태조사(청년조사)_전체_v1_230127.xlsx` (cross-tab, n=5513, 고립은둔 486 / 미해당 5027)
- 목적: B-01 위험군 자동 스코어링 부재(2026-04-27 운영 관찰)에 대응할 통계 근거 기반 설문/스코어링 초안.

### 분석
- 138문항 전체에 대해 옵션 단위 Cohen's h 와 문항 단위 max\|h\|·JS divergence 산출 (`discrim_full.json`).
- 변별력 1위 `A13_4` 직장·학교·동네 사람 대면 교류 max\|h\|=1.250, 정서지지 4문항 모두 max\|h\| ≥ 0.92.

### 설문 12문항
- 차원 7개(외출·교류 양·물리적 대면교류·정서적 지지·외로움·우울·자살사고·자기관리·가족·노동)를 커버하도록 12문항 선정.
- 각 문항에 옵션 단위 정수 점수(0~6) + 문항 가중치(=max\|h\|, Q9는 안전 가중 1.5배). 가중치 합 ≈ 10.34, 이론 최대 점수 ≈ 51.77.
- 5단계 컷오프(시뮬레이션 분포 기반): s1=12.71 / s2=18.21 / s3=29.62 / s4=35.55. Q9 ≥ 5인 경우 stage = max(stage, 4) safety override.

### 검증 결과
- 합성 응답자 시뮬레이션(고립 2,000 / 비고립 8,000, 문항 독립 가정).
- AUC 0.9915 (상한 추정), 평균 점수 차이 16.54점.
- 단계 분포: 비고립군 stage 1·2 = 90% / stage 4+ = 0%, 고립군 stage 3+ = 98.3% / stage 4+ = 50%.
- 한계: 독립 가정 → 실제 운영 AUC 0.85~0.95 예상. 라벨이 A7을 사용해 부여된 부분적 순환. PRD §7.1 stage 2~4 의미는 reserved 유지(컷오프는 후보값).

### 후속
- `02_survey_selection_rationale.md` §4 표를 `FEATURE_SPEC.md` 진입 설문 명세로 인용·승격 (B-01 P0).
- `03_scoring_design.md` §6 의사 코드를 `risk_stage_service` 입력 파라미터로 인입.
- 운영 응답 200~500건 모이면 컷오프 재추정. 새 날짜 폴더(`yyyy-mm-dd_isolation_score_retune/`)로 비교 분석 추가.
- 메타데이터: 본 폴더 보고서 md 5종은 SHA256 실계산값 기입(CLAUDE.md §11.4 준수). `FOLDER.md` 2개는 placeholder TBD 상태로 두며 후속 빌드에서 실해시로 교체.

---

## 2026-04-27 — backend/README 병목 리스트 추가 (운영 관찰)

### B-01~B-12 병목 정리
- 사용자 요청(위험군 1~5단계 자동 분류 가능 여부 + 시나리오별 쿼리 결과 + 파이프라인 병목 리스트)에 대응해 `backend/README.md` 끝에 §"파이프라인 병목"을 신설.
- 핵심 식별: B-01 위험군 자동 스코어링 부재(설문 CSV 미적재 + 스코어링 로직 0건, 프론트는 라디오), B-02/B-03 major_name·자유 텍스트 → domain_ids 정규화 계층 부재, B-04~B-08 추천/로드맵/RAG 단계 결함, B-09~B-12 정책 미확정·관측성 부채.
- 시나리오 추적 메모(2단계 전자공학/3단계 산업데이터공학/5단계 컴퓨터·IT) 표로 첨부. 실제 검증은 `scripts/eval_golden_set.py` 페르소나 추가로 일원화 권장.
- 본 작업은 운영 관찰 기록일 뿐이며 정책·구현 변경 없음. 후속 P0 항목(B-01~B-03)은 `PRD.md`/`FEATURE_SPEC.md`/`DATA_SCHEMA.md` 선수정 후 코드 수정.
- 메타데이터: `backend/README.md` 최종 수정일 2026-04-27, 문서 해시 SHA256:TBD (CLAUDE.md §11.4 placeholder 규칙 준수).

---

## 2026-04-19 — eval runner + bottleneck tier-relative + job_to_domain (R4)

### R4-1 — 골든셋 자동 평가 runner (`eval_golden_set.py`)
- `scripts/eval_golden_set.py` 신규 작성. 6 persona × evaluation_criteria 패턴 매칭(18개 패턴 정의).
- 구조적 체크(expected_entry_stage, entry_advanced, fallback_used, total_certs) + Jaccard + criteria 자동 검증.
- P21 hard-fail: J=0.33 → A1 이후 top-10 전부 기능사로 변경된 것 확인. `golden_set.jsonl` expected_cert_ids 갱신 후 J=1.00, P21 100%.
- 최종 PASS RATE 95.7% (P15 1건 FAIL 잔존 — stage_0005 tier 필터 미적용, R5 대상).
- 실행: `python scripts/eval_golden_set.py [--persona P21] [--fail-fast]`

### R4-3 — `is_bottleneck` tier-relative 판정
- `recommendation_service.py`에 `_BOTTLENECK_TIER_THRESHOLD` 추가: 기능사 20%/산업기사 15%/기사 10%/기술사·기능장 5%.
- `_build_roadmap_sequence` 내 is_bottleneck 계산 2곳 교체.
- 검증: 발송배전기술사(기술사, 1.9%) → bottleneck ✅. P21 기능사(45-65%) → bottleneck=0건 유지 ✅.

### R4-6 — `job_to_domain.csv` 런타임 통합
- `_JOB_TO_DOMAIN` 경로 상수 + `_load_job_to_domain_map()` 함수 추가.
- `recommendations()` job-only 쿼리(domain_ids 빈 경우)에 domain_ids 자동 확장.
- `_invalidate_caches()`에 추가. 검증: job_0001 → domain_0001, total_certs=10 확인.

---

## 2026-04-19 — cert_to_cert_relation 버그 수정 + 방향 guard (R3: A1 + N6)

### A1 — `_RELATION_TYPE_MAP` 오매핑 제거
- `scripts/build_cert_to_cert_relation.py`에서 `_RELATION_TYPE_MAP = {"recommended_prior": "next_step", ...}` 딕셔너리 제거.
- `_load_prereq_rows()`의 `relation_type` 할당을 `r.get("relation_kind", "next_step")` 직접 사용으로 교체.
- 결과: NCS 775행 중 666행이 `next_step` → `recommended_prior`로 올바르게 복원. path_score 가중치 0.50→0.80 회복.
- P21 검증: `cert_paths[0].path_score = 0.9485` (> 0.78 기준 통과).

### N6 — `_TIER_ORDER` 기반 역방향 행 자동 swap/drop 빌드 가드
- `_cert_tier_map()` 함수 추가 (cert_id → cert_grade_tier).
- `build()`에 tier 비교 로직 추가: from_tier > to_tier 시 swap, 동일 tier 시 drop.
- 재빌드 결과: total 999행 (active 775 / inactive 224), swapped=8, dropped=19 (모두 parse_ir 단독).
- `data/canonical/relations/FOLDER.md` §2 파일 테이블 업데이트 (1,018→999, 설명 갱신).

---

## 2026-04-18 — 증분·게이트 3종 (C1/C2/C3)

### C2 — candidate 빌드 taxonomy 게이트 (build-time strict)
- `DATA_SCHEMA.md §9.1.1` 신설: `primary_domain` / `related_domains`는 `domain_master.csv`의 `domain_sub_label_id`, `related_jobs`는 `job_master.csv`의 `job_role_id` 집합에만 속해야 함.
- `scripts/build_cert_candidates.py`에 master CSV ID 기반 검증 단계 추가. 위반 시 기본 실패(exit 1), `--allow-violations`로 우회.
- 위반 리포트: `data/canonical/validation/candidates_taxonomy.json`. 현 데이터 1290/1290 통과 — 회귀 가드.
- `backend/canonical/candidate_jsonl.py` docstring 보정 (라벨 텍스트가 아닌 master CSV ID 기준임을 명시).

### C1 — embed 단계 증분 (manifest 기반)
- `backend/rag/ingest/cli.py`를 `PipelineManifest.is_embed_stale`와 연동. `embed_key_hash = chunk_hash + embed_version` 기준 스킵.
- `--force` 플래그로 전체 재임베딩 가능. 적재 직후 `update_embed` → manifest 저장.
- `RAG_PIPELINE.md §16.3` 신설로 계약 문서화. `embed_version` 상승 시 일괄 stale 동작 명시.

### C3 — candidate build row-level 증분 (content_hash diff)
- `scripts/build_cert_candidates.py`가 실행 시마다 `data/canonical/candidates/.build_manifest.json`(`{candidate_id: content_hash}`)을 읽고 `added/updated/removed/unchanged` diff를 stdout으로 출력, manifest를 갱신.
- downstream 인덱스 업데이트는 이 manifest를 읽어 **바뀐 candidate만** 반영하도록 설계(§7.6.1). 두 번째 실행에서 1290 unchanged 확인.
- `HASH_INCREMENTAL_BUILD_GUIDE.md §7.6.1` 보강, 후보 폴더 `FOLDER.md` 갱신.

---

## 2026-04-14 — 핵심 아키텍처 결정: cert_grade_tier 정렬 + 선수과목 DAG 로드맵

### 배경

청크·추천 테스트 및 고도화 논의 과정에서 두 가지 구조적 설계 결정을 확정.

### 결정 사항

**결정 1: cert_grade_tier 기반 위험군 연동 정렬**
- 위험군 단계가 높을수록(4~5단계) 기능사·산업기사를 우선 추천하고, 기사·기술사는 후순위로 자동 조정한다.
- Certificate 엔티티에 `cert_grade_tier` 필드 추가 (`DATA_SCHEMA.md` §4.7, §5.3).
- 정렬 로직은 Recommendation Core 계층이 담당 (`SYSTEM_ARCHITECTURE.md` §8, §17 결정 8).
- FEATURE_SPEC.md F-03 처리 규칙에 정렬 기준 명시.

**결정 2: 선수과목 DAG 순회 로드맵 생성**
- flat list 대신 `cert_prerequisite` 관계(`DATA_SCHEMA.md` §6.8)를 방향 그래프(DAG)로 순회하여 로드맵 경로를 생성한다.
- 사용자 현재 위치에서 실제 이동 가능한 경로만 로드맵 단계 후보로 제시한다.
- FEATURE_SPEC.md F-05 처리 규칙에 DAG 순회 원칙 명시.
- `SYSTEM_ARCHITECTURE.md` §8 원칙, §17 결정 9에 반영.

### 수정 문서

- `DATA_SCHEMA.md`: §4.3에 `cert_to_cert_prerequisite` 추가, §4.7 `cert_grade_tier` enum 신규, §5.3 Certificate에 `cert_grade_tier` 필드 추가
- `FEATURE_SPEC.md`: F-03 처리 규칙에 tier 정렬 규칙 추가, F-05 처리 규칙에 DAG 순회 원칙 추가
- `SYSTEM_ARCHITECTURE.md`: §8 Recommendation Core 원칙에 두 결정 추가, §17 핵심 아키텍처 결정에 8·9번 추가

### 의도적으로 하지 않은 것

- cert_grade_tier 실제 값 채우기(CSV canonicalization 단계에서 수행)
- DAG 순회 구현 코드(구현은 다음 스프린트)
- feasibility_score, prerequisite_met 등 파생 필드 설계(후속 단계)

---

## 2026-04-03 — 정책: 준비만·실행 비강제 (추천 API 스텁 복귀)

### 배경

제품 단계를 **파이프라인 실행이 아니라 준비(계약·예시·문서)** 로 둔다.

### 수행

- **`POST /recommendations`**: JSONL 로더·`backend/canonical/*` 구현 **제거**, `NOT_IMPLEMENTED` 스텁 복귀(`details.prep`에 준비 참조 링크).
- **설정**: `candidates_jsonl_relative` 등 추천 전용 필드 **제거**.
- **문서**: `API_SPEC.md` §6·§7.2, `FEATURE_SPEC.md` F-03, `PROJECT_SUMMARY.md` §8~§9 — “실행 안 해도 됨”·스텁 명시.
- **`candidates.jsonl.example`**, 스키마·§8 표는 **준비물로 유지**.

### 과거 시도(참고)

- 동일 날짜에 잠시 JSONL 로더를 넣었으나 본 정책에 맞춰 되돌림.

---

## 2026-04-03 — 파이프라인 준비 전제(데이터 수집 후) 명시

### 수행

- **`PROJECT_SUMMARY.md`**: §8 레인별 준비 표·§9 구현 성숙도·§10 결론 번호 정리. “수집만으로 전 레인 자동 완주”가 아님을 명시.
- **`SYSTEM_ARCHITECTURE.md`**: §13.4 `PROJECT_SUMMARY` §8·§9 단일 참조.
- **`RAG_PIPELINE.md`**: §16.2 인제스트·Evidence 직전 체크리스트(cert_id·차원·재인제스트·증분).
- **`DATA_SCHEMA.md`**, **`API_SPEC.md`**: 현행 Evidence 필터와 `metadata.cert_id` 정합.
- **`chunk_loader.py`**: docstring 정합.
- **`data/index_ready/chunks/chunks.jsonl.example`**: JSONL 1줄 샘플.
- **`docs/architecture/supabase_langchain.sql`**: 재인제스트 중복 주석.
- **`data/index_ready/chunks/FOLDER.md`**, **`backend/README.md`**: 예시·요약 링크.

---

## 2026-04-03 — 아키텍처 문서 정렬·루트 md 문서 해시

### 수행

- **`SYSTEM_ARCHITECTURE.md`**: §3.4는 §14·`RAG_PIPELINE.md` §15로 위임(중복 목록 제거), §9에 parse IR(`RAG_PIPELINE.md` §6.7)·문서형 chunk(`DATA_SCHEMA.md`) 교차 참조.
- **누락 메타**: `API_SPEC.md`, `PROMPT_DESIGN.md`, `ROOT_DOC_GUIDE.md`, `HASH_INCREMENTAL_BUILD_GUIDE.md`에 `문서 해시` 줄 추가.
- **루트 `*.md`**: 메타데이터 영역(첫 `## ` 이전)에서 `문서 해시`·`최종 수정일` 줄을 제외한 본문 기준으로 SHA256 재계산 → `scripts/maintenance/update_root_md_hashes.py`로 일괄 반영(하위 `FOLDER.md`는 제외).

---

## 2026-04-03 — RAG 보완(문서만): Parse 순서·IR 계약·평가 후보

### 수행

- **`RAG_PIPELINE.md`**: §6.0 Parse 실행 순서, §6.7 parse IR 최소 계약(청크 빌더 입력), §10.3 스토어 구현 vs 계약 구분, §13.3 질의 확장 reserved(MVP 비적용 명시), §15 reserved에 코퍼스 감사·rate limit 후보.
- **`DATA_SCHEMA.md`**: `SourceDocument`에 `file_hash`·`fetched_at`, §5.6·§11과 `RAG_PIPELINE` §6.7 역할 분리 명시, 메타데이터 블록에 `문서 해시` 줄 추가.
- **`EVALUATION_GUIDELINE.md`**: §4 Parse·인덱스 품질 측정 후보 표(채택 전).

### 비적용(의도적)

- HyDE·다단계 pre-retrieval·vendor 전환 등은 제품 목적·MVP 범위 밖이거나 별도 계약 필요 → 문서에 **reserved/후속**만 명시.

---

## 2026-04-03 — RAG 심화 참고(로컬) 정리

- 루트 문서: 인덱싱·Pre-retrieval **축 설명**만 유지, **특정 파일명·경로**는 적지 않음. 계약은 `RAG_PIPELINE.md` 우선, reserved는 범위 자동 확장 금지.
- `.gitignore`: `docs/references/_private/` 무시(개인·팀 미공유 참고 자료용).

---

## 2026-04-03 — 데모 제출용 임시 절 (PRD §19, FEATURE_SPEC §11)

### 수행

- **PRD.md**: `문서 해시` 줄 추가; **§19 데모 제출용 범위·단계 (임시)** — 목적, 최소 시연 흐름, 얇게 둘 항목, D1~D6 체크리스트, 데모 완료 조건, 제출 후 조치.
- **FEATURE_SPEC.md**: `문서 해시` 줄 추가; **§11 데모 제출용 기능 단계 (임시)** — 단계·F-xx 매핑, 허용 스텁, 금지, 제출 후 정리.

---

## 2026-04-03 — 리프 폴더 `FOLDER.md` 스캐폴드 명시서

### 수행

- **`FOLDER.md`**: `docs/`, `data/`(리프), `frontend/src/`(리프), `scripts/*`, `experiments/*`, `infra/*`, `shared/*`, `data/taxonomy` 등 **63개** 리프 경로에 동일 메타데이터 양식(루트 md와 계열)으로 용도·금지·연계·비고 기술.
- **`scripts/maintenance/generate_folder_md.py`**: 위 경로 일괄 생성기. 저장소 루트는 `DIRECTORY_SPEC.md` 존재로 탐색.
- **`DIRECTORY_SPEC.md`**: §7 원칙 8번·§8 요약에 `FOLDER.md` 규칙 반영.

---

## 2026-04-03 — PROJECT_SUMMARY 및 청킹·레퍼런스 문서 위치 안내

### 수행

- **신규** `PROJECT_SUMMARY.md`: 프로젝트 목적, CSV vs 문서 레인, 스택·폴더 요약, 문서 지도, 청킹 절차(`RAG_PIPELINE.md` §7 연계, `chunks.jsonl`·인제스트 CLI), 긴 방법론 문서는 `docs/references/` 권장.
- **README.md**, **DIRECTORY_SPEC.md** §2·§3, **ROOT_DOC_GUIDE.md** §3·§4.1: `PROJECT_SUMMARY.md` 링크·트리 반영.

---

## 2026-04-03 — 문서·디렉터리 정렬 및 최소 스캐폴딩

### 수행

- **DIRECTORY_SPEC.md**: §2 루트 트리에 `ROOT_DOC_GUIDE.md`, `HASH_INCREMENTAL_BUILD_GUIDE.md` 추가; §3에 해당 파일 역할 및 Cursor 규칙(`.cursor/rules/`) 안내; §5 권장 루트 파일 목록 동기화; 문서 해시 라인 추가.
- **신규 루트 문서**: `EVALUATION_GUIDELINE.md`(10), `EVALUATION.md`(11), `EXPERIMENT_GUIDE.md`(12), `ERROR_ANALYSIS.md`(13), `DEV_LOG.md`(14) — 메타데이터 및 `SHA256:TBD`.
- **README.md**: 문서 해시 라인; §5 표에 `ROOT_DOC_GUIDE`, `HASH_INCREMENTAL_BUILD_GUIDE`, Cursor 규칙 위치; §7 트리 동기화.
- **Git**: `gitignore` → `.gitignore` 로 이름 정리(내용 유지).
- **디렉터리**: `docs/*`, `data/raw|canonical|index_ready|processed` 하위(기존 `data/taxonomy/*.txt` 유지), `experiments/*`, `infra/*`, `shared/*` — 비어 있는 leaf에는 Git 추적용 `.gitkeep`만 둠(데이터 파일 아님).
- **frontend**: `DIRECTORY_SPEC` §4.3 트리 + 각 leaf `.gitkeep`, `frontend/README.md`(후속 Next/Vite 안내).
- **backend**: FastAPI `backend.app.main:app`, `/api/v1/health` 활성(envelope 준수); `recommendations`/`roadmaps`/`admin`/`risk/stages`는 `NOT_IMPLEMENTED` envelope; 일정·링크 라우트는 HTTP **501** + envelope; `backend/rag/*`, `backend/canonical/*`, `services`, `requirements.txt`, `backend/README.md`, `backend/tests/test_health.py`.
- **scripts**: `parse`, `canonicalize`, `build_entities`, `build_relations`, `build_candidates`, `evaluation`, `maintenance` 각 `run.py` 스텁.

### 검증

- `PYTHONPATH=<저장소 루트>` 기준 `pytest backend/tests -q` — `test_health_ok` 통과.

### 의도적으로 하지 않은 것

- `risk_stage_master.csv` 및 기타 원본·taxonomy 파일의 임의 생성·더미 row
- raw PDF/HTML/CSV/API 실파일 추가
- reranker, BM25 상시, 일정 API 실연동, 프론트 완성 UI
- `docs/references` 내 참고 자료는 사용자 수동 배치

---

## 2026-04-03 — 스택 정렬 (Vite·LangChain·Supabase·파이프라인 연결)

### 수행

- **프론트**: React 19 + Vite 6 + TS — `frontend/package.json`, `vite.config.ts`(`/api`→8000 프록시), `src/` 홈에서 헬스 호출.
- **백엔드**: `pydantic-settings` 기반 `backend/app/core/config.py`, CORS, `POST /api/v1/recommendations/evidence` + `retrieval_service` + LangChain `SupabaseVectorStore` 경로(`backend/rag/store/supabase_vector.py`).
- **인제스트**: `backend/rag/ingest/chunk_loader.py`, `python -m backend.rag.ingest.cli` (JSONL만 사용, 더미 데이터 생성 없음).
- **SQL 템플릿**: `docs/architecture/supabase_langchain.sql`.
- **환경 템플릿**: `infra/env/.env.example`; `.gitignore`에 `!.env.example` 예외.
- **LlamaIndex**: `backend/rag/llamaindex/` 자리만.
- **문서**: `RAG_PIPELINE.md` §16.1, `SYSTEM_ARCHITECTURE.md` §2.1 스택 문단, `README.md` §10, `backend/README.md` / `frontend/README.md` 갱신.

### 검증

- `pytest backend/tests` (health + evidence missing cert_id).
- `frontend` `npm run build`.

---

## 2026-04-03 — CSV 담당 팀 지침서

- 루트에 `CSV_CANONICALIZATION_TEAM_GUIDE.md` 추가 (영민·유빈: 데이터 수집 슬라이드·Parse 슬라이드 기준 CSV 레인 전담 절차).
- `README.md` §5 표에 해당 문서 링크 한 줄 추가.
