# DIRECTORY_SPEC.md

> **파일명**: DIRECTORY_SPEC.md  
> **최종 수정일**: 2026-07-05  
> **문서 해시**: SHA256:0c67d4b88f13473111773be05281fbe3f5eb131093d4c6f817d2b69edfa13358
> **문서 역할**: 프로젝트 디렉토리 구조와 파일/폴더 책임 정의 문서  
> **문서 우선순위**: 9  
> **연관 문서**: README.md, CHANGE_CONTROL.md, SYSTEM_ARCHITECTURE.md, PRD.md  
> **참조 규칙**: 디렉토리 구조를 수정하거나 새 파일/폴더를 추가하기 전에 먼저 이 문서를 확인한다.

---

## 1. 문서 목적

이 문서는 프로젝트의 **최종 디렉토리 구조**와 각 파일/폴더의 역할을 정의한다.  
문서, 데이터, 서비스 코드, 실험, 배치 스크립트, 배포 관련 자산이 서로 충돌하지 않도록 구조적 기준선을 제공하는 것이 목적이다.

이 문서는 다음을 정의한다.

- 최종 루트 디렉토리 구조
- 루트 파일 역할
- 하위 폴더 역할
- 즉시 생성 권장 영역
- reserved 가능 영역
- 디렉토리 운영 원칙

이 문서는 다음을 직접 정의하지 않는다.

- 문서 수정 절차
- 제품 문제 정의
- 시스템 계층 구조
- 기능 입출력
- 데이터 필드 상세

위 항목은 각각 `CHANGE_CONTROL.md`, `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `FEATURE_SPEC.md`, `DATA_SCHEMA.md`에서 담당한다.

---

## 2. 최종 루트 디렉토리

프로젝트의 최종 루트 디렉토리는 아래를 기준으로 한다.

```text
project-root/
├─ .gitignore
├─ README.md
├─ PROJECT_SUMMARY.md
├─ CHANGE_CONTROL.md
├─ DIRECTORY_SPEC.md
├─ ROOT_DOC_GUIDE.md
├─ HASH_INCREMENTAL_BUILD_GUIDE.md
├─ Indexing_Architecture.txt
├─ PRD.md
├─ SYSTEM_ARCHITECTURE.md
├─ FEATURE_SPEC.md
├─ API_SPEC.md
├─ PROMPT_DESIGN.md
├─ DATA_SCHEMA.md
├─ CSV_CANONICALIZATION_TEAM_GUIDE.md
├─ RAG_PIPELINE.md
├─ EVALUATION_GUIDELINE.md
├─ EVALUATION.md
├─ EXPERIMENT_GUIDE.md
├─ ERROR_ANALYSIS.md
├─ DEV_LOG.md
│
├─ docs/
├─ data/
├─ frontend/
├─ backend/
├─ scripts/
├─ experiments/
├─ infra/
└─ shared/
```

---

## 3. 루트 파일 역할

### `.gitignore`
Git 추적 제외 대상 정의

### `README.md`
프로젝트 최상위 안내 문서  
프로젝트 목적, 핵심 개념, 범위, 연관 문서 안내를 담당한다.

### `PROJECT_SUMMARY.md`
저장소 전체 요약 — 두 데이터 레인(CSV vs 문서), 스택, 디렉터리·문서 지도, 청킹 절차 요약, `docs/references/` 등 긴 방법론 문서 배치 안내.

### `CHANGE_CONTROL.md`
문서 갱신 규칙, 작업 절차, 메타데이터 갱신 원칙을 담당한다.

### `DIRECTORY_SPEC.md`
프로젝트 디렉토리 구조와 파일/폴더 책임 정의를 담당한다.

### `ROOT_DOC_GUIDE.md`
루트 md 문서 탐색 순서와 상황별 참조 안내를 담당한다.

### `HASH_INCREMENTAL_BUILD_GUIDE.md`
입력·단계별 해시 키와 증분 재처리 원칙을 담당한다.

### Cursor 프로젝트 규칙
저장소 루트가 아니라 **`.cursor/rules/`** 아래에 둔다. (예: `CURSOR-PROJECT-RULES-md.mdc`.) 동일 본문을 루트 md로 중복하지 않는 것을 권장한다.

### `Indexing_Architecture.txt`
인덱싱/지식 파이프라인 관련 참고 구조 문서 또는 아키텍처 초안이다.  
루트 문서 설계 시 참고 기준으로 사용한다.

### `PRD.md`
문제 정의, 타깃 사용자, 제품 목표, 범위/비범위를 정의한다.

### `SYSTEM_ARCHITECTURE.md`
계층 구조, 책임 분리, 데이터 흐름, 모듈 경계를 정의한다.

### `FEATURE_SPEC.md`
기능별 입력/출력/예외처리를 정의한다.

### `API_SPEC.md`
API endpoint 계약과 request/response 구조를 정의한다.

### `PROMPT_DESIGN.md`
프롬프트 역할, 입력 슬롯, 출력 계약, 가드레일을 정의한다.

### `DATA_SCHEMA.md`
데이터 구조, canonical schema, 주요 엔티티/관계/필드를 정의한다.

### `CSV_CANONICALIZATION_TEAM_GUIDE.md`
CSV 레인(데이터 수집·스키마 매핑·canonical·엔티티/관계 산출) 담당자용 실행 지침서이다.  
계약 필드는 `DATA_SCHEMA.md`가 우선한다.

### `RAG_PIPELINE.md`
Parse, Chunking, Metadata, Embedding, Retrieval 구조를 정의한다.

### `EVALUATION_GUIDELINE.md`
평가 기준, metric 선택 이유, baseline 정의, 비교 기준을 정의한다.

### `EVALUATION.md`
실제 평가 결과와 실험 결과를 기록한다.

### `EXPERIMENT_GUIDE.md`
실험 세팅, 파라미터, 재현 방식, 로그 기록 방법을 정의한다.

### `ERROR_ANALYSIS.md`
오류 사례, 실패 패턴, 개선 방향을 기록한다.

### `DEV_LOG.md`
날짜별 진행 로그, 문제 및 해결 이력을 기록한다.

---

## 4. 하위 디렉토리 구조

### 4.1 docs/

```text
docs/
├─ slides/
├─ references/
├─ architecture/
└─ meeting_notes/
```

#### 역할
- `slides/`: 발표 자료
- `references/`: 논문, 참고문헌, 기준 자료
- `architecture/`: 구조도, 설계도, 흐름도
- `meeting_notes/`: 회의 기록, 의사결정 메모

---

### 4.2 data/

```text
data/
├─ raw/
│  ├─ pdf/
│  ├─ html/
│  ├─ csv/
│  └─ api/
│
├─ taxonomy/
│  ├─ domain_v2.txt
│  ├─ prefer_job.txt
│  └─ risk_stage_master.csv
│
├─ canonical/
│  ├─ entities/
│  ├─ relations/
│  ├─ candidates/
│  └─ validation/
│
├─ index_ready/
│  ├─ parse_ir/
│  ├─ chunks/
│  ├─ metadata/
│  ├─ dense_input/
│  └─ sparse_input/
│
└─ processed/
   ├─ master/
   ├─ mappings/
   ├─ merged/
   └─ snapshots/
```

#### 역할
- `raw/`: 원본 수집 데이터
- `taxonomy/`: 허용 taxonomy 기준 파일
- `canonical/`: CSV canonicalization 결과
- `index_ready/`: 검색/추천 입력용 산출물
- `processed/master/`: raw rows에서 정제된 master 중간 산출물
- `processed/mappings/`: raw 자유 텍스트를 master ID로 연결한 매핑 중간 산출물
- `processed/merged/`: canonical 기반 병합 중간 테이블/스냅
- `processed/snapshots/`: 시점 고정 데이터 스냅샷(재현/감사/실험용)

#### 원칙
- PDF / HTML은 Parse 및 indexing 대상이다.
- CSV는 Parse IR 대상이 아니라 canonicalization 대상이다.
- API는 현재 reserved이며 후속 스프린트에서 연결한다.

---

### 4.3 frontend/

```text
frontend/
├─ public/
│  └─ assets/
│
├─ src/
│  ├─ app/
│  ├─ pages/
│  │  ├─ Home/
│  │  ├─ RiskAssessment/
│  │  ├─ Recommendation/
│  │  ├─ Roadmap/
│  │  ├─ Schedule/
│  │  └─ Admin/
│  │
│  ├─ components/
│  │  ├─ layout/
│  │  ├─ cards/
│  │  ├─ charts/
│  │  ├─ forms/
│  │  └─ feedback/
│  │
│  ├─ features/
│  │  ├─ risk-stage/
│  │  ├─ recommendation/
│  │  ├─ roadmap/
│  │  └─ schedule/
│  │
│  ├─ api/
│  ├─ hooks/
│  ├─ store/
│  ├─ types/
│  ├─ utils/
│  ├─ constants/
│  └─ styles/
│
├─ tests/
└─ package.json
```

#### 역할
사용자 입력, 위험군 결과, 추천 결과, 로드맵 결과, 추후 일정 화면을 담당한다.

#### 현재 핵심 페이지
- `Home`
- `RiskAssessment`
- `Recommendation`
- `Roadmap`

#### reserved 가능
- `Schedule`
- `Admin`

---

### 4.4 backend/

```text
backend/
├─ app/
│  ├─ main.py
│  ├─ core/
│  ├─ api/
│  │  ├─ deps.py
│  │  └─ v1/
│  │     ├─ routes/
│  │     │  ├─ health.py
│  │     │  ├─ risk.py
│  │     │  ├─ recommendation.py
│  │     │  ├─ roadmap.py
│  │     │  ├─ schedule.py
│  │     │  └─ admin.py
│  │     └─ schemas/
│  │
│  ├─ services/
│  │  ├─ risk_stage_service.py
│  │  ├─ recommendation_service.py
│  │  ├─ roadmap_service.py
│  │  ├─ schedule_service.py
│  │  ├─ retrieval_service.py
│  │  └─ metadata_service.py
│  │
│  ├─ repositories/
│  ├─ models/
│  ├─ schemas/
│  └─ utils/
│
├─ rag/
│  ├─ ingest/
│  ├─ retrieval/
│  ├─ prompts/
│  └─ evaluation/
│
├─ canonical/
│  ├─ registry/
│  ├─ pipeline/
│  ├─ schemas/
│  └─ outputs/
│
├─ tests/
└─ requirements.txt
```

#### 역할
- `backend/app/`: API, 서비스 조정 계층
- `backend/rag/`: PDF / HTML parse 및 retrieval 계층
- `backend/canonical/`: CSV canonicalization 계층

---

### 4.5 scripts/

```text
scripts/
├─ parse/
├─ canonicalize/
├─ build_entities/
├─ build_relations/
├─ build_candidates/
├─ evaluation/
└─ maintenance/
```

#### 역할
일회성 실행, 배치, 점검, 재처리 스크립트를 담당한다.

- `parse/`: PDF / HTML parse 실행
- `canonicalize/`: CSV canonicalization 실행
- `build_entities/`: entity 생성
- `build_relations/`: relation 생성
- `build_candidates/`: candidate row 생성
- `evaluation/`: 평가 실행
- `maintenance/`: 문서/데이터 일관성 점검
  - `generate_folder_md.py`: 리프 `FOLDER.md` 일괄 생성
  - `update_root_md_hashes.py`: 루트 `*.md` 상단 `문서 해시` 재계산·반영

---

### 4.6 experiments/

```text
experiments/
├─ configs/
├─ logs/
├─ reports/
├─ baselines/
└─ notebooks/
```

#### 역할
실험 설정, 로그, 결과 보고서, baseline 비교, 분석 노트북을 관리한다.

---

### 4.7 infra/

```text
infra/
├─ docker/
├─ deploy/
└─ env/
```

#### 역할
배포 및 실행 환경 설정을 담당한다.

#### 상태
현재는 reserved 가능

---

### 4.8 shared/

```text
shared/
├─ constants/
├─ schemas/
└─ types/
```

#### 역할
frontend / backend 공용 상수, schema, 타입을 저장한다.

#### 상태
현재는 필수 아님  
공용 구조가 많아질 때 활성화한다.

---

## 5. 즉시 생성 권장 영역

### 루트 파일
- `.gitignore`
- `README.md`
- `PROJECT_SUMMARY.md`
- `CHANGE_CONTROL.md`
- `DIRECTORY_SPEC.md`
- `ROOT_DOC_GUIDE.md`
- `HASH_INCREMENTAL_BUILD_GUIDE.md`
- `Indexing_Architecture.txt`
- `PRD.md`
- `SYSTEM_ARCHITECTURE.md`
- `FEATURE_SPEC.md`
- `API_SPEC.md`
- `PROMPT_DESIGN.md`
- `DATA_SCHEMA.md`
- `CSV_CANONICALIZATION_TEAM_GUIDE.md`
- `RAG_PIPELINE.md`
- `EVALUATION_GUIDELINE.md`
- `EVALUATION.md`
- `EXPERIMENT_GUIDE.md`
- `ERROR_ANALYSIS.md`
- `DEV_LOG.md`

### 핵심 디렉토리
- `docs/slides`
- `docs/references`
- `docs/architecture`
- `data/raw/pdf`
- `data/raw/html`
- `data/raw/csv`
- `data/taxonomy`
- `data/canonical`
- `data/index_ready`
- `data/processed/master`
- `data/processed/mappings`
- `frontend/src`
- `backend/app`
- `backend/rag`
- `backend/canonical`
- `scripts/parse`
- `scripts/canonicalize`
- `experiments/logs`
- `experiments/reports`

---

## 6. reserved 가능 영역

- `data/raw/api`
- `frontend/src/pages/Schedule`
- `frontend/src/pages/Admin`
- `backend/app/api/v1/routes/schedule.py`
- `backend/app/services/schedule_service.py`
- `backend/rag/retrieval/reranker.py`
- `infra/`
- `shared/`
- `experiments/baselines/`
- `experiments/notebooks/`
- `docs/meeting_notes/`

---

## 7. 디렉토리 운영 원칙

1. 구조 변경 시 먼저 `DIRECTORY_SPEC.md`를 수정한다.
2. 새 파일 추가 전 기존 역할과 충돌이 없는지 확인한다.
3. CSV는 Parse IR 대상으로 처리하지 않는다.
4. `related_domains`는 도메인 taxonomy 세부 라벨만 허용한다.
5. `related_jobs`는 희망 직무 taxonomy 세부 직무만 허용한다.
6. 위험군은 1단계 ~ 4단계 구조로 관리한다 (`risk_0005`는 백엔드에 비활성 보존, 프론트엔드 미사용).
7. API 일정/링크는 후속 스프린트에서 canonical target schema에 병합한다.
8. 스캐폴드용 **리프 폴더**(`docs/*`, `data/*` 리프, `frontend/src/*` 리프, `scripts/*`, `experiments/*`, `infra/*`, `shared/*`)에는 역할 설명용 **`FOLDER.md`** 를 둔다. 상단 메타데이터·`문서 해시: SHA256:TBD` 형식은 루트 md와 동일 계열을 따르며, 용도 변경 시 본 파일과 본 `DIRECTORY_SPEC.md`를 함께 갱신한다. 일괄 생성·재생성은 `python scripts/maintenance/generate_folder_md.py` (저장소 루트에서 실행).

---

## 8. 최종 요약

이 문서의 핵심은 아래 세 가지다.

1. 프로젝트의 최종 루트 디렉토리 구조를 고정한다.
2. 각 파일/폴더의 책임을 분리하여 구조 충돌 없이 확장할 수 있게 한다.
3. 리프 폴더의 `FOLDER.md`로 스캐폴드 의도를 코드와 동시에 읽을 수 있게 한다.
