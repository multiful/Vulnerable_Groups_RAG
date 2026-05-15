# PROJECT_SUMMARY.md

> **파일명**: PROJECT_SUMMARY.md  
> **최종 수정일**: 2026-05-15  
> **문서 해시**: SHA256:05b369f39d501b8b97271c19436dadac1491eb1abf3040612688ce50dbcdac86
> **문서 역할**: 저장소 한눈에 보기 — 목적·구조·문서 지도·청킹 개요  
> **문서 우선순위**: reference (세부 계약·스키마는 각 전용 문서가 우선)  
> **연관 문서**: README.md, PRD.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DATA_SCHEMA.md, DIRECTORY_SPEC.md  
> **참조 규칙**: 제품 범위·파이프라인 세부가 바뀌면 본 문서를 같은 턴에서 갱신한다.

---

## 1. 이 프로젝트가 하는 일

청년 **위험군 단계**(1~5단계)와 **관심 직무·도메인(taxonomy)** 을 입력으로, **자격증 후보**와 **로드맵**을 구조적으로 추천하고, **PDF/HTML 근거**로 설명(evidence)을 붙이는 시스템을 만든다.

- **구조적 추천**: canonical 데이터(엔티티·관계·candidate row). CSV는 여기로만 간다.
- **RAG**: 추천 엔진이 아니라 **설명 근거 검색** 레이어. PDF/HTML만 Parse→Chunk→Embed 경로.

---

## 2. 두 갈래 데이터 레인 (헷갈리지 않기)

| 레인 | 원본 | 하지 않는 것 | 산출(예) |
|------|------|--------------|----------|
| **CSV / structured** | `data/raw/csv/` | Parse IR·청킹·RAG 인덱스에 넣기 | `data/canonical/*` (영민·유빈 담당 범위는 `CSV_CANONICALIZATION_TEAM_GUIDE.md`) |
| **문서 PDF/HTML** | `data/raw/pdf/`, `data/raw/html/` | CSV처럼 canonical 테이블만으로 대체 | Parse IR → chunk JSONL → 임베딩 → 벡터 스토어 |

---

## 3. 기술 스택 (현재)

| 영역 | 선택 |
|------|------|
| 프론트 | React 19 + Vite 6 + TypeScript (`frontend/`) |
| API | FastAPI (`backend/`) |
| RAG 런타임 | LangChain + Supabase pgvector (`backend/rag/`) |
| 임베딩 | OpenAI `text-embedding-3-small` |
| LLM | OpenAI GPT-4o-mini (추천 이유·로드맵 분석) |
| 외부 API | Q-Net(시험일정), WorkNet(채용), Work24(훈련), YouTube Data API, 서울시 공공 API |
| 배포 | API: Render.com / 프론트: Vite dev(로컬) |

**reserved**: 지원 링크 실연동(Q-Net 원서접수 직링크), reranker, BM25 상시, parent-child chunk 고도화, 상담형 대화 에이전트 — `PRD.md`·`FEATURE_SPEC.md`와 동일.

---

## 4. 디렉터리 요약

| 경로 | 역할 |
|------|------|
| 루트 `*.md` | 제품·스키마·API·파이프라인 **단일 기준선** |
| `docs/slides`, `docs/references`, `docs/architecture`, `docs/meeting_notes` | 발표·**긴 기법 문서**·구조도·회의록 |
| `data/raw/` | 원본 (pdf/html/csv/api) |
| `data/taxonomy/` | 허용 도메인·직무 라벨 (`domain_v2.txt`, `prefer_job.txt`) |
| `data/canonical/` | 엔티티·관계·후보·검증 산출 |
| `data/processed/master/` | raw rows에서 정제된 master 중간 산출 |
| `data/processed/mappings/` | raw 자유 텍스트를 master ID로 연결한 매핑 중간 산출 |
| `data/processed/merged/` | canonical 기반 병합 중간 테이블/스냅 |
| `data/processed/snapshots/` | 시점 고정 스냅샷(재현·감사·실험용) |
| `data/index_ready/chunks/` | **RAG용 청크 JSONL** (한 줄 = 한 청크) |
| `backend/` | FastAPI, RAG, canonical 코드 |
| `frontend/` | UI |
| `scripts/` | parse / canonicalize / build_* 등 배치 진입 |
| `experiments/`, `infra/`, `shared/` | 실험·배포·공용 타입 |

상세는 `DIRECTORY_SPEC.md`.  
리프 스캐폴드 폴더마다 역할 요약은 해당 디렉터리의 **`FOLDER.md`** (`DIRECTORY_SPEC.md` §7 원칙 8).

---

## 5. 문서 지도 (무엇을 먼저 읽나)

| 순서 | 문서 | 한 줄 |
|------|------|--------|
| 0 | `README.md` | 입구 |
| 1 | `CHANGE_CONTROL.md` | 문서 수정 규칙 |
| 2 | `PRD.md` | 문제·범위 |
| 3 | `SYSTEM_ARCHITECTURE.md` | 계층·흐름 |
| 이후 | `FEATURE_SPEC`, `DATA_SCHEMA`, `API_SPEC`, `PROMPT_DESIGN`, `RAG_PIPELINE`, `DIRECTORY_SPEC` | 작업 주제별 |
| 팀 CSV | `CSV_CANONICALIZATION_TEAM_GUIDE.md` | 영민·유빈 |
| 탐색 | `ROOT_DOC_GUIDE.md` | 문서 목록 안내 |

---

## 6. 청킹(Chunking) 단계 — 이 프로젝트에서 어떻게 하면 되나

### 6.1 전제

- 청킹 입력은 **CSV가 아니라 Parse 산출물(구조 보존 IR 또는 이에 준하는 중간 표현)** 이다.  
- Parse에서 **reading order·표 경계**가 무너지면, 청킹만으로는 회복이 어렵다 (`RAG_PIPELINE.md` Parse·Chunk 연결).

### 6.2 기준 문서

모든 규칙의 원본은 **`RAG_PIPELINE.md` §7 Chunk Layer**, §8 Metadata Layer 이다. 요약만 여기 적는다.

### 6.3 문서 유형별 전략 (프로젝트 고정안)

| 유형 | 청킹 방식 (`RAG_PIPELINE.md`) |
|------|--------------------------------|
| 안내·FAQ·설명형 (HTML/가이드) | **Markdown-aware**: heading propagation, 문단 의미 단위, 과도한 길이 확장 금지 |
| 표 중심 | **Block chunking**: 표/리스트/단락을 한 청크에 섞지 않음, block 경계 유지 |
| Parent–Child | **선택·MVP 비필수** (reserved 성격으로 단계적 도입) |

### 6.4 메타데이터 (청크마다 최소한)

`doc_id`, `chunk_id`, `source_type`, `doc_type`, `section_path`, `source_loc`, `chunk_hash`, `valid_from` / `valid_to`, `doc_version`  
선택: `cert_id`, 직무·도메인·위험군·기관 등 (`RAG_PIPELINE.md` §8).

### 6.5 이 저장소에서의 **실행 순서** (구현 관점)

1. **Parse** 완료 → IR 또는 정규화된 블록 시퀀스 확보.  
2. **Chunk builder** 실행: 위 §6.3 규칙에 따라 텍스트를 자르고 메타를 붙인다.  
3. **산출 파일**: `data/index_ready/chunks/chunks.jsonl` (또는 팀이 정한 동등 경로).  
   - 한 줄 = JSON 한 객체. 스키마는 `backend/rag/ingest/chunk_loader.py` 주석과 맞출 것 (`text`/`content`, `chunk_id`, `doc_id`, `metadata.cert_id` 등).  
4. **인제스트**: `python -m backend.rag.ingest.cli` (환경변수·Supabase 스키마는 `docs/architecture/supabase_langchain.sql`, `backend/README.md`).  
5. **버전**: `chunk_version` / `chunk_hash` 규칙은 `HASH_INCREMENTAL_BUILD_GUIDE.md` — 규칙이 바뀌면 버전 올리고 선택적 재처리.

### 6.6 심화 기법 문서와의 관계

인덱싱(Parse~Store) **조건별 기본안**·확장 순서·운영 판단, 그리고 **Retriever 입력 직전**까지의 질의 처리(정책·캐시·rewrite·예산 등)는 외부 **장문 RAG 기준서**에 흔히 정리되어 있다. 본 제품에서 RAG는 **evidence 검색**이므로 질의 축은 **품질·비용** 관점에서만 선택적으로 참고한다. 그런 자료는 **로컬 전용**으로 두고(`docs/references/_private/` 등, Git 제외), 팀 저장소에는 파일을 올리지 않는다.

**이 프로젝트에서 우선할 것**: `RAG_PIPELINE.md` + 루트 reserved 규칙(BM25 상시·reranker 등). 기준선을 바꿀 때는 `RAG_PIPELINE.md`(및 필요 시 `PROMPT_DESIGN.md`)를 먼저 고친다.

---

## 7. 긴 기법·방법론 문서는 어디에 두나

`DIRECTORY_SPEC.md` 기준:

| 위치 | 넣기 좋은 것 |
|------|----------------|
| **`docs/references/`** | 논문·블로그·**일반론 레퍼런스** Markdown. 팀 공유가 아닌 심화 자료는 `_private/` 등 Git 제외 경로에 둔다. 제품 계약은 루트 `RAG_PIPELINE.md` 우선 |
| **`docs/architecture/`** | **이 저장소 전용** 다이어그램·시퀀스·“우리 파이프라인 결정” 요약 (슬라이드 PNG와 짝지은 짧은 설명 등) |
| **`docs/slides/`** | 발표용 원본 |
| **`docs/meeting_notes/`** | 회의·의사결정 |

**루트에는 두지 않는 것을 권장**: 루트는 `CHANGE_CONTROL`이 정한 **기준선 md**만 두고, 수십~수백 KB 방법론은 `docs/references/`로 분리하면 목록이 깨끗해진다.

**Git**: PNG·대형 MD도 `.gitignore`에 특별 제외가 없으면 일반적으로 추적 가능. 팀 공유용이면 `docs/references/`에 두고 `git add` 하면 된다.

---

## 8. 데이터 수집이 끝난 뒤 — 레인별 “준비 완료”와 실행 전제

**목표**: 원본만 올바른 위치·형식으로 두었다고 해서 **저장소 안의 모든 자동화가 한 번에 끝나는 상태는 아니다.** 아래를 구분한다.

- **준비(계약·폴더·환경·DB·산출물 형식)**: 문서·스키마·예시 파일로 고정 가능한 것.  
- **실행(코드 경로)**: 레인마다 **이미 연결된 CLI/API**가 있는지 여부가 다르다.

### 8.1 문서 레인 (PDF/HTML → Evidence 검색)

| # | 준비 항목 | 비고 |
|---|-----------|------|
| 1 | 원본 위치 | `data/raw/pdf/`, `data/raw/html/` (또는 팀 규칙과 동일한 수집 경로). |
| 2 | Parse → Chunk 산출 | `RAG_PIPELINE.md` §6·§7·§6.7(IR 계약). 저장소의 `scripts/parse/run.py`는 **진입 스텁**이므로, **실제 Parse·청크 빌드는 오프라인 도구/후속 스크립트로 산출**해야 한다. |
| 3 | 청크 JSONL | `data/index_ready/chunks/chunks.jsonl` (또는 `CHUNKS_JSONL_RELATIVE`). **한 줄 = JSON 1건.** 필수 키·예시는 `chunks.jsonl.example`·`chunk_loader.py` 주석. |
| 4 | Evidence API 필터 정합 | 현행 `retrieval_service`는 벡터 메타에 `cert_id`가 있다고 가정하고 `@>` 필터한다. **JSONL의 `metadata` 안에 `cert_id`를 넣는 것이 사실상 필수** (없으면 검색 결과 0건). |
| 5 | 임베딩 ↔ DB 차원 | `EMBEDDING_PROVIDER`에 맞춰 `docs/architecture/supabase_langchain.sql`의 `vector(N)`·`match_documents` 시그니처를 맞출 것 (OpenAI 기본 1536, HF MiniLM 384 등). |
| 6 | 환경 변수 | `infra/env/.env.example` → 루트 또는 `backend/.env`에 복사. `SUPABASE_*`, 인제스트·검색에 쓰는 키·모델명. |
| 7 | 인제스트(실행 단계) | **준비만 할 때는 실행하지 않아도 된다.** 실행 시 저장소 루트에서 `PYTHONPATH=. python -m backend.rag.ingest.cli`. 재실행 시 중복 가능 — `RAG_PIPELINE.md` §16.2·`HASH_INCREMENTAL_BUILD_GUIDE.md` 참고. |

1~7은 **실행 직전에 갖출 준비 목록**이다. 준비 단계에서는 폴더·형식·문서 정합만 맞추면 된다.

### 8.2 구조 레인 (CSV → 추천 후보)

| # | 준비 항목 | 비고 |
|---|-----------|------|
| 1 | 원본 위치 | `data/raw/csv/` 및 팀 CSV 가이드 (`CSV_CANONICALIZATION_TEAM_GUIDE.md`). |
| 2 | Taxonomy | `data/taxonomy/` 허용 라벨과 수집 데이터가 **충돌 없이** 맞아야 한다 (`DATA_SCHEMA.md` taxonomy 제약). |
| 3 | 산출물 위치 | `data/canonical/entities/`, `relations/`, `candidates/`, `validation/` 등 (`DIRECTORY_SPEC.md`). |
| 4 | master 중간 산출 | 정제된 master(`cert/domain/job/major`)는 `data/processed/master/`에 두고, 이후 매핑 단계 입력으로 사용. |
| 5 | 매핑 중간 산출 | alias/mapping 결과는 `data/processed/mappings/`에 두고, 검수 통과본만 `data/canonical/relations/` 생성에 사용. |
| 6 | 실행 순서(설계상) | canonicalize(master+mapping) → entity → relation → candidate 빌드 → 검증 → 추천 입력 소비. `scripts/*/run.py`는 현재 **스텁**이므로, **데이터만 쌓여서는 이 레인이 자동 완주하지 않는다.** |
| 7 | API·산출 형식 | `POST /api/v1/recommendations`는 **현재 스텁**(실행 없음). 후보 데이터 형식은 `DATA_SCHEMA.md` §9.1·`candidates.jsonl.example`로 준비해 둔다. |

### 8.3 한 줄 정리

- **준비만** 할 때는 원본·taxonomy·스키마·예시 JSONL·문서(§8 표)만 갖추면 된다. **실행(인제스트·추천 API 연결)은 하지 않아도 된다.**  
- **추천 후보**는 API 스텁을 유지하고, **데이터 형식·폴더**만 맞춰 둔다. CSV→canonical 배치는 후속.

---

## 9. 현재 구현 단계 (요약)

- **추천 파이프라인 전체 활성**: `POST /recommendations` → 로드맵 데이터 반환, LLM AI 맞춤 분석 모두 실제 동작.
- **Execution Layer 전면 활성** (2026-05-14): Q-Net 시험일정·WorkNet 채용공고·Work24 훈련과정·YouTube·서울시 공공 API 실연동.
- **자격증 DB**: cert_master.csv 1,290종 (exam_type_info, exam_subject_info 포함).
- **Evidence API**: Supabase pgvector RAG + 카탈로그 JSON 병합 방식으로 동작.
- **Parse→Chunk·CSV canonical 배치**: 스텁·후속 (인덱스는 별도 수동 인제스트).
- “준비 완료”의 의미는 **§8 표**의 **형식·위치·문서** 정합이지, 파이프라인을 돌린 여부가 아니다.

---

## 10. 한 페이지 결론

1. **CSV** → canonical까지 (청킹 없음).  
2. **PDF/HTML** → Parse → **Chunk(`RAG_PIPELINE` §7)** → JSONL → Embed → Store.  
3. **법적·계약 기준**은 루트 `DATA_SCHEMA.md`, `API_SPEC.md`, `RAG_PIPELINE.md`.  
4. **긴 방법론**은 `docs/references/` (또는 아키텍처 전용 요약은 `docs/architecture/`).
