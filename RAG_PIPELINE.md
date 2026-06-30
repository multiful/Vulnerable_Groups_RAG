# RAG_PIPELINE.md

> **파일명**: RAG_PIPELINE.md  
> **최종 수정일**: 2026-06-30  
> **문서 해시**: SHA256:0180bf0424d7875c4b842e1ba76e6e3a49ef453bc362b28f4107210fc121c9e6
> **문서 역할**: RAG 인덱싱 및 evidence retrieval 파이프라인 정의 문서  
> **문서 우선순위**: 8  
> **연관 문서**: SYSTEM_ARCHITECTURE.md, DATA_SCHEMA.md, API_SPEC.md, PROMPT_DESIGN.md, EVALUATION_GUIDELINE.md  
> **참조 규칙**: Parse, Chunking, Metadata, Embedding, Retrieval, Fusion, Sparse/Dense 사용 기준을 변경할 때 먼저 이 문서를 수정한다.

---

## 1. 문서 목적

이 문서는 시스템의 **RAG 파이프라인**을 정의한다.  
여기서 RAG 파이프라인은 PDF / HTML 기반 공식 문서를 검색 가능한 상태로 변환하고, 추천 결과에 설명 근거를 결합하기 위해 검색하는 전체 흐름을 의미한다.

이 문서는 다음을 정의한다.

- source_type 기준 RAG 적용 범위
- Parse → Chunk → Metadata → Embedding → Store 흐름
- Retrieval 계층의 역할
- Dense / Sparse / Fusion의 사용 기준
- 현재 활성 범위와 reserved 범위
- 운영 및 품질 점검 포인트
- 인덱스 버전 관리 기준

이 문서는 다음을 직접 정의하지 않는다.

- 제품 문제 정의와 사용자 가치
- 기능별 입력/출력/예외처리
- API endpoint 계약 상세
- canonical entity / relation 구조
- 프롬프트 문구 자체
- 평가 지표의 최종 채택 기준

위 항목은 각각 `PRD.md`, `FEATURE_SPEC.md`, `API_SPEC.md`, `DATA_SCHEMA.md`, `PROMPT_DESIGN.md`, `EVALUATION_GUIDELINE.md`에서 담당한다.

### 1.1 참고: 심화 기준서(로컬)

인덱싱(Parse~Store)과 Pre-retrieval(질의)을 실무 수준으로 정리한 **외부 장문 기준서**를 개인 워크스페이스에 둘 수 있다. 팀 저장소에는 **파일명·경로를 두지 않으며**, 내용만 설계 판단에 반영한다. 자료는 `docs/references/_private/` 등 **Git 제외 경로**에 두는 것을 권장한다.

| 축 | 다루는 범위 | 이 프로젝트에 적용할 때 |
|------|-------------|-------------------------|
| **인덱싱** | Parse·Chunking·Embedding·Store 조건별 기본안, 확장 순서, 운영·스토어 | 공식 PDF/HTML·표·스캔 혼합 등 **인제스트 품질**과 **재색인 비용**을 설계할 때 참고한다. **계약·버전·증분 규칙**은 본 문서(`RAG_PIPELINE.md`)와 `HASH_INCREMENTAL_BUILD_GUIDE.md`가 우선한다. |
| **질의(Pre-retrieval)** | Retriever 직전까지의 질의 처리(정책·캐시·rewrite·라우팅·예산 등) | RAG가 **추천 엔진이 아니라 evidence 검색**인 점은 유지한 채, 질의 품질·지연·비용을 다룰 때 참고한다. Hybrid·RRF **튜닝·reranker** 등은 루트 규칙상 reserved면 **읽기만** 하고 범위를 임의 확장하지 않는다. |

위 축은 **범용 기준서**에서 흔히 나뉘는 틀이다. 제품 범위·reserved 여부는 `PRD.md`, `FEATURE_SPEC.md`, `CLAUDE.md`와 충돌 시 **루트 문서**를 따른다.

---

## 2. RAG의 역할

본 시스템에서 RAG는 **추천 자체를 계산하는 엔진**이 아니다.  
RAG의 역할은 아래로 한정한다.

1. PDF / HTML 문서 기반 설명 근거 검색
2. 추천 결과에 대한 FAQ / 안내문 / 설명 텍스트 보강
3. 자격증, 직무, 도메인, 로드맵과 관련된 공식 문서 근거 제공

즉, 구조적 추천은 canonical data가 담당하고, RAG는 그 추천을 설명하는 **evidence layer** 역할을 한다.

---

## 3. 적용 범위

### 3.1 RAG 적용 대상
- Official PDF
- Official HTML
- FAQ
- 공고문
- 공식 안내 페이지
- 시험안내 브로슈어
- 문서형 설명 자료

### 3.2 RAG 비적용 대상
- CSV 원본
- canonical entity table
- canonical relation table
- recommendation candidate row
- 위험군 stage master
- roadmap stage master

CSV 계열은 RAG 인덱싱 대상이 아니라 structured no-parse canonicalization 대상이다.

---

## 4. 파이프라인 상위 구조

```text
[Raw Knowledge Sources]
├─ Official PDF
└─ Official HTML

        ↓

[Source Routing & Profiling]
- source_type
- doc_type
- freshness_level
- exact_sensitivity
- layout signals
  - text_density
  - image_ratio
  - table_count
  - multi_column
  - scan_page_ratio

        ↓

[Parse Layer]
- HTML Direct Path
- Primary PDF Parser
- Table Assist
- OCR(page-level)
- Fallback(document-level)
- Boilerplate Removal
- Reading Order Fix

        ↓

[Chunk Layer]
- markdown-aware chunking
- block chunking
- heading propagation
- atomic chunk rules

        ↓

[Metadata Layer]
- doc_id
- chunk_id
- source_type
- doc_type
- cert_id (optional)
- domain/job/risk metadata (optional)
- section_path
- source_loc
- valid_from / valid_to / doc_version

        ↓

[Embedding Layer]
- dense vector
- exact terms
- text_for_sparse(optional)

        ↓

[Index Store Layer]
- Vector Store
- Sparse/BM25 Store(optional)

        ↓

[Retrieval Layer]
- Dense Retriever
- Sparse Retriever(optional)
- Fusion
- Filters
- Reranker(optional)

        ↓

[Evidence Output]
- evidence snippets
- provenance metadata
```

---

## 5. Source Routing & Profiling

RAG 파이프라인은 수집 직후 모든 문서를 동일하게 처리하지 않는다.  
먼저 source profiling을 통해 처리 경로를 결정한다.

### 기본 신호
- `source_type`
- `doc_type`
- `freshness_level`
- `exact_sensitivity`

### layout signals
- `text_density`
- `image_ratio`
- `table_count`
- `multi_column`
- `scan_page_ratio`

### 목적
- HTML direct path 여부 결정
- PDF 기본 경로 여부 결정
- table assist 필요 여부 결정
- OCR 대상 페이지 결정
- fallback 필요 문서군 판정

---

## 6. Parse Layer

Parse 레이어는 **청크 빌더가 의존하는 중간 표현(parse IR)**을 만든다.  
아래 순서는 구현체가 달라도 **결과 계약**을 맞추기 위한 권장 실행 흐름이다.

### 6.0 실행 순서 (권장)

1. **소스 단위 식별·무결성**: 원본 파일(또는 HTML 응답)의 `file_hash`·수집 시각 등 증분 키 후보를 확보한다. 상세는 `HASH_INCREMENTAL_BUILD_GUIDE.md`·`DATA_SCHEMA.md` `SourceDocument`를 따른다.
2. **라우팅·프로파일링**: §5에 따라 `source_type`·layout signals·OCR·table assist·fallback 필요성을 판정한다.
3. **형식별 파싱**: HTML direct path, primary PDF, table assist, **페이지 단위** OCR, 문서 단위 fallback 중 해당 경로만 수행한다.
4. **정리(후처리)**: boilerplate 제거, reading order 복원, 표·리스트 구조 보존이 필요한 블록만 최소 보강한다.
5. **품질·계보**: `parse_quality_flags`(또는 §11 대응 구조)와 parse IR을 함께 산출한다.
6. **청크 레이어 전달**: IR이 §6.7 최소 필드를 만족하면 §7 chunking으로 넘긴다.

### 6.1 HTML Direct Path
HTML은 DOM / Main Content Parser 경로로 처리한다.

#### 역할
- main content 추출
- heading / list / link 유지
- FAQ / 공식 안내 구조 보존

### 6.2 Primary PDF Parser
born-digital official PDF의 기본 경로다.

#### 역할
- 텍스트 레이어 기반 본문 추출
- heading 구조 보존
- block 단위 중간 표현 생성

#### 원칙
- 가능한 한 기본 경로로 유지한다.
- 문서 전체를 고비용 fallback으로 바로 보내지 않는다.

### 6.3 Table Assist
표 후보 페이지 보강 경로다.

#### 역할
- 일정표 / 격자표 / 회차표 구조 보존
- 행/열 관계 유지
- 표 block 단위 추출

#### 적용 기준
- `table_count`가 높은 페이지
- 표 문서로 판정된 페이지
- 행/열 구조 보존 필요 페이지

### 6.4 OCR
저텍스트 / 스캔 페이지 예외 처리 경로다.

#### 역할
- page-level 텍스트 복원
- 스캔 페이지 보강

#### 원칙
- 문서 전체 기본 경로가 아니라 페이지 단위 예외 처리다.
- born-digital PDF 전체에 OCR을 적용하지 않는다.

### 6.5 Document-level Fallback
기본 parse + 보강 이후에도 구조 보존 실패가 반복될 때만 사용하는 문서 단위 fallback이다.

#### 역할
- 복잡한 표/다단/순서 오류 문서군 재처리

#### 원칙
- 전체 문서 기본 경로로 사용하지 않는다.
- 실패 문서군에만 제한 적용한다.

### 6.6 Parse Cleanup
parse 이후 후처리를 수행한다.

#### 주요 처리
- boilerplate 제거
- reading order 복원
- parse quality flag 생성

#### 산출물
- parse IR
- parse_quality_flags
- optional provenance metadata

### 6.7 Parse IR 최소 구조 (청크 빌더 입력 계약)

청크 레이어는 **자유 형식 JSON**이 아니라, 아래를 만족하는 IR을 입력으로 받는다고 가정한다.  
필드명은 구현체에서 camelCase·snake_case로 매핑할 수 있으나 **의미는 동일**해야 한다.

| 구분 | 필드(또는 항목) | 필수 | 설명 |
|------|------------------|------|------|
| 문서 | `doc_id` | Y | `DATA_SCHEMA.md` 문서형 지식과 동일 식별자 체계 |
| 문서 | `blocks` | Y | 순서가 있는 블록 배열(reading order는 배열 순서 또는 블록별 인덱스로 표현) |
| 블록 | `block_id` | Y | 동일 `parse_hash` 내에서 안정적인 블록 식별자 |
| 블록 | `block_type` | Y | 예: `heading`, `paragraph`, `list`, `table`, `other` (구현체 enum은 확장 가능, 청킹 규칙과 문서화할 것) |
| 블록 | `text` | Y | 청킹 대상이 되는 정규화 텍스트(표는 markdown 또는 정규화된 텍스트 표현 중 하나로 통일) |
| 블록 | `reading_order_index` | N | 다단·재배열 시 원문 순서 복원·디버깅용 |
| 블록 | `heading_level` | N | 제목 단계(있을 경우) |
| 블록 | `section_path` | N | 상위 제목 경로(있으면 메타데이터 전파에 사용) |
| 블록 | `source_loc` | N | 페이지·오프셋 등 원문 위치(있을 경우) |

**원칙**

- IR은 **추천 후보 계산**에 쓰이지 않으며, 문서형 근거의 구조 보존과 청크 경계 결정에만 쓰인다.
- 표·스캔 등 특수 경로에서만 추가 필드를 허용하되, **dense 검색에 불필요한 바이너리 대용량 필드**는 IR에 넣지 않는다.

---

## 7. Chunk Layer

Chunk는 retrieval의 기본 검색 단위다.  
문서 유형별로 다른 chunking 규칙을 사용한다.

### 7.1 Markdown-aware Chunking
대상:
- guide
- FAQ
- 설명형 문서

규칙:
- heading propagation 유지
- 문단 의미 단위 우선
- 과도한 길이 확장 금지

### 7.2 Block Chunking
대상:
- 표 중심 문서
- block 분리가 중요한 문서

규칙:
- block boundary 유지
- 표/리스트/단락을 섞지 않는다

### 7.3 Parent-Child
현재는 선택 사항이다.  
기본 MVP에서는 필수 활성화 대상이 아니다.

---

## 8. Metadata Layer

각 chunk에는 retrieval과 provenance를 위해 메타데이터를 부여한다.

### 최소 메타 필드
- `doc_id`
- `chunk_id`
- `source_type`
- `doc_type`
- `section_path`
- `source_loc`
- `chunk_hash`
- `valid_from`
- `valid_to`
- `doc_version`

### 선택 메타 필드
- `cert_id`
- `job_role_id`
- `domain_sub_label`
- `domain_top_label`
- `risk_stage_id`
- `roadmap_stage`
- `agency`

### 원칙
- recommendation candidate row와 같은 구조를 강제하지 않는다.
- 문서 provenance와 filter 가능성을 우선한다.
- metadata는 retrieval filter와 evidence trace에 모두 사용 가능해야 한다.

---

## 9. Embedding Layer

### 9.1 Dense Vector
기본 검색 수단이다.

#### 역할
- 의미 기반 검색
- FAQ / 설명 문서 검색
- 추천 결과에 대한 근거 검색

#### 산출물
- `dense_vector`
- `emb_model_version`
- `emb_prompt_version`

### 9.2 Exact Terms
exact match에 민감한 용어를 보조 필드로 유지할 수 있다.

예:
- 자격증명
- 기관명
- 도메인명
- 직무명
- 회차 표현
- 고정 용어

### 9.3 text_for_sparse
선택적 sparse 입력 텍스트다.

#### 원칙
- 항상 기본값으로 사용하지 않는다.
- exact miss가 실제로 재현될 때만 활성화한다.
- 활성화 시 BM25 / sparse store 입력으로 사용한다.

---

## 10. Index Store Layer

### 10.1 Vector Store
dense retrieval용 저장소

저장 대상 예:
- chunk text
- dense vector
- metadata

### 10.2 Sparse / BM25 Store
exact retrieval 보강용 선택 저장소

저장 대상 예:
- sparse text
- exact-sensitive terms
- metadata

#### 원칙
- optional이다.
- 초기 MVP에서는 dense 중심 운영 가능하다.

### 10.3 구현체와 계약의 구분

벡터 저장소의 **제품명**(예: Supabase pgvector)은 배포·스택 선택이다.  
**계약의 기준**은 본 문서의 메타·버전(§14), `DATA_SCHEMA.md`의 문서형 chunk 필드, 그리고 evidence 출력 필드(§12)다.  
저장소에 대한 코드 경로 매핑은 §16.1을 따른다.

---

## 11. Retrieval Layer

### 11.1 Dense Retriever
기본 검색기다.

#### 역할
- 의미 기반 evidence 검색
- 추천 이유 보강용 snippet 검색

### 11.2 Sparse Retriever
선택적 검색기다.

#### 역할
- alias
- 기관명
- 자격증명
- exact 용어 보강

### 11.3 Fusion
dense / sparse 결과를 결합한다.

#### 현재 원칙
- sparse가 비활성 상태면 dense 단독 운영 가능
- fusion 방식의 세부 튜닝은 후속 최적화 범위로 둔다

### 11.4 Filters
메타데이터 기반 검색 범위를 제한한다.

예:
- `source_type`
- `doc_type`
- `cert_id`
- `agency`
- `valid_from / valid_to`

### 11.5 Reranker
현재는 reserved 가능하다.

#### 역할
- 후보 정렬 개선
- 근거 우선순위 재조정

#### 원칙
- MVP 필수 기능은 아니다.

---

## 12. Evidence Output 구조

retrieval 결과는 evidence bundle 형태로 후단에 전달한다.

### 최소 필드
- `doc_id`
- `chunk_id`
- `source_type`
- `snippet`
- `section_path`
- `source_url`

### 선택 필드
- `score`
- `agency`
- `valid_from`
- `valid_to`
- `doc_version`

---

## 13. Runtime 흐름

### 13.1 Evidence Retrieval 요청 흐름
1. 백엔드 서비스가 `cert_id` 및 context를 전달한다.
2. retrieval 계층이 filter 조건을 구성한다.
3. dense retriever를 기본으로 검색한다.
4. sparse가 활성화되어 있으면 결합한다.
5. 필요 시 reranker를 적용한다.
6. evidence snippet과 provenance를 반환한다.

### 13.2 Recommendation과의 연결
- canonical recommendation 결과가 먼저 생성된다.
- 이후 RAG가 explanation/evidence를 보강한다.
- 구조적 추천과 evidence는 별도 계층에서 만들어진다.

### 13.3 질의 전처리·확장 (reserved)

현재 제품 범위에서 evidence 검색은 **구조적 context**(예: `cert_id`, 필터) 중심으로 설계한다.  
사용자 **자유 자연어 질의**를 1차 입력으로 받는 검색, HyDE, 다단계 쿼리 rewrite, 적응형 retrieval 예산 등은 **도입 시** `FEATURE_SPEC.md`·`API_SPEC.md`에서 활성 범위와 예외를 별도 정의하기 전까지 구현·문서에서 **완료된 기능처럼 다루지 않는다**.  
RAG가 추천 엔진이 아니라는 원칙(§2)은 그대로 유지한다.

---

## 14. 인덱스 버전 관리

RAG 파이프라인 산출물에는 최소 아래 버전 정보를 유지하는 것을 권장한다.

- `ingest_version`
- `chunk_version`
- `metadata_version`
- `embedding_version`

### 원칙
- Parse/Chunk 규칙이 바뀌면 `ingest_version` 또는 `chunk_version`을 갱신한다.
- 임베딩 모델 또는 프롬프트가 바뀌면 `embedding_version`을 갱신한다.
- 대규모 재색인이 필요한 변경은 `DEV_LOG.md`와 `EVALUATION.md`에도 반영한다.

---

## 15. 현재 활성 범위

### 활성화
- HTML direct path
- primary PDF parser
- table assist
- OCR page-level 예외 처리
- chunk builder
- metadata tagging
- dense embedding
- vector store
- dense retrieval
- optional filter 사용

### reserved
- sparse/BM25 상시 사용
- text_for_sparse 상시 사용
- reranker
- parent-child 고도화
- 일정/링크 문서 retrieval
- 코퍼스 규모 확대 시 **중복·유사 문서·유사 청크** 감사 및 정리 절차(오프라인)
- evidence·임베딩 API **rate limit·예산·쿼터** 정책(운영 정책으로 별도 정의 시 활성화)

---

## 16. 운영 원칙

1. born-digital PDF 전체에 OCR을 기본 적용하지 않는다.
2. CSV는 RAG Parse 대상이 아니다.
3. retrieval 결과가 0건이어도 추천 결과 자체는 실패로 간주하지 않는다.
4. exact miss가 문제로 재현되기 전까지 sparse를 강제하지 않는다.
5. reserved 기능은 문서 갱신 후 활성화한다.
6. retrieval 품질 평가는 `EVALUATION_GUIDELINE.md` 기준과 연결해 관리한다.

---

## 16.1 구현 스택 매핑 (코드·데이터 경로)

아래는 **문서 파이프라인 개념**과 저장소 내 **실행 경로**를 연결한 참조다. 상세 계약은 `API_SPEC.md`를 따른다.

| 단계 | 경로 / 진입점 |
|------|----------------|
| 청크 산출물 (오프라인) | `data/index_ready/chunks/chunks.jsonl` — 한 줄당 1청크, 스키마는 `backend/rag/ingest/chunk_loader.py` 주석 |
| 임베딩 | LangChain: `backend/rag/embeddings/factory.py` — `openai` 또는 `huggingface` |
| 벡터 저장·검색 | Supabase pgvector + `langchain_community.vectorstores.SupabaseVectorStore` (`backend/rag/store/supabase_vector.py`) |
| DB 함수·테이블 템플릿 | `docs/architecture/supabase_langchain.sql` |
| 인제스트 CLI | 저장소 루트에서 `PYTHONPATH=. python -m backend.rag.ingest.cli` |
| Evidence API | `POST /api/v1/recommendations/evidence` → `backend/app/services/retrieval_service.py` |

**LlamaIndex** 기반 대안은 `backend/rag/llamaindex/` 에 자리만 두었으며, 전환 시 본 절과 `SYSTEM_ARCHITECTURE.md`를 먼저 갱신한다.

### 16.2 데이터·런타임 준비 체크리스트 (인제스트·Evidence 직전)

1. **`chunks.jsonl`**: 한 줄당 1청크 JSON. `text`(또는 `content`), `chunk_id`, `doc_id` 필수.  
2. **`metadata.cert_id`**: 현행 `retrieval_service`·Supabase `@>` 필터 기준으로 **Evidence 검색에 필요** (요청 `cert_id`와 동일 값이 메타에 있어야 후보가 잡힌다).  
3. **임베딩 차원**: `embedding_provider`·모델과 `docs/architecture/supabase_langchain.sql`의 `vector(N)`·RPC 인자 차원이 일치할 것.  
4. **환경 변수**: `infra/env/.env.example` 기준 — `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, (OpenAI 경로면) `OPENAI_API_KEY` 등.  
5. **재인제스트**: `ingest.cli`는 동일 `chunk_id`에 대한 **삭제·멱등 업서트를 강제하지 않는다.** 전량 갱신 시 테이블 정리 정책을 운영 규칙으로 정한 뒤 실행한다.  
6. **증분·버전**: 장기 운영 시 `HASH_INCREMENTAL_BUILD_GUIDE.md`의 `file_hash` / `chunk_hash` / `embedding_version` 조합으로 재처리 범위를 줄인다.

### 16.3 embed 증분 규칙 (manifest 기반)

`ingest.cli`는 적재 전에 `data/index_ready/metadata/pipeline_manifest.json`의 `chunks[<chunk_id>].embed_key_hash`와 현재 `chunk_hash + embed_version`을 비교한다.

- `embed_key_hash`가 **동일**하면 해당 청크는 스킵한다 (재임베딩·재적재 안 함).
- `embed_key_hash`가 **다르거나** manifest에 기록이 없으면 재임베딩 대상이다.
- 청크 JSONL에 `metadata.chunk_hash`가 **없으면** 증분 판정 불가 → 안전을 위해 적재하고 manifest 기록은 건너뛴다.
- `--force` 플래그는 manifest를 무시하고 전체 재임베딩한다.
- 적재 성공 후 `PipelineManifest.update_embed(chunk_id, chunk_hash, embedded_at)`가 호출되어 manifest가 갱신된다.
- `embed_version`(`backend/rag/pipeline/manifest.py`의 `EMBED_VERSION`)이 올라가면 기존 모든 청크가 자동으로 stale 처리되어 일괄 재임베딩된다.

---

## 17. RAG 출처 카탈로그 (Source Catalog)

### 17.1 목적

RAG 검색 결과를 사용자에게 보여줄 때 **명확한 출처(출처명·기관·연도·페이지)**를 함께 제공한다.  
이를 위해 각 문서는 인덱싱 시 아래 provenance 메타데이터를 필수로 포함해야 한다.

### 17.2 출처 표시 형식

검색 결과에서 출처는 아래 형식으로 표시한다.

```
[출처] {doc_title} ({doc_agency}, {doc_pub_year}), p.{page}
```

예시:
```
[출처] 고립은둔 청년 지원사업 모형 개발 연구 (한국보건사회연구원, 2022), p.23
[출처] 서울시 고립·은둔청년 실태조사 (서울특별시, 2023), p.45
```

### 17.3 chunk 필수 provenance 필드

기존 `DATA_SCHEMA.md §10` 선택 메타 외에, 고립·은둔 청년 지원 문서군에는 아래 필드를 **필수**로 채운다.

| 필드 | 기존 schema 대응 | 설명 |
|---|---|---|
| `doc_title` | `title` | 문서 전체 제목 |
| `doc_agency` | `agency` | 발행 기관명 |
| `doc_pub_year` | `doc_version` 또는 별도 | 발행 연도 (YYYY) |
| `doc_page` | `source_loc` | 청크가 위치한 페이지 번호 |
| `doc_section` | `section_path` | 섹션 경로 (예: ["3장", "3.2절"]) |
| `support_program_ids` | 선택 | 해당 청크가 근거가 되는 `sp_*` ID 목록 |
| `target_group_ids` | 선택 | 해당 청크가 관련된 `tg_*` ID 목록 |

### 17.4 활성 RAG 출처 목록

아래 문서는 현재 인덱싱 대상이거나 인덱싱 예정인 출처다.

| doc_id | doc_title | doc_agency | doc_pub_year | 파일명 | 주요 활용 |
|---|---|---|---|---|---|
| `doc_support_001` | 고립은둔 청년 지원사업 모형 개발 연구 (정책 2022-35) | 한국보건사회연구원 | 2022 | `정책 2022-35(김성아) 고립은둔_청년_지원사업_모형_개발_연구_최종.pdf` | 4군집 분류 이론·지원 모형 |
| `doc_support_002` | 서울시 고립·은둔청년 실태조사 (설문지 포함) | 서울특별시 | 2023 | `서울시 고립·은둔청년 실태조사 (설문지 포함).pdf` | 설문 문항·통계 기반 |
| `doc_support_003` | 은둔청소년 판별을 위한 스크리닝 척도 개발 | 학술 논문 | TBD | `은둔청소년 판별을 위한 스크리닝 척도 개발.pdf` | 설문 척도 개발·신뢰도 |
| `doc_support_004` | 신뢰타당성분석 | TBD | TBD | `신뢰타당성분석.pdf` | Cronbach's α·타당도 방법론 |
| `doc_support_005` | 고립·은둔 청년 지원 방안 | 여성가족부 | TBD | `고립‧은둔 청년 지원 방안.pdf` | 정책·서비스 근거 |
| `doc_support_006` | 청년 페이스 메이커 실무 가이드북 | 생명의전화 종합사회복지관 청년이음센터 | 2021 | (별도 수집 예정) | 이미지 표 12 원출처 |
| `doc_support_007` | 가족돌봄·고립은둔청년 전담 지원사업 개시 | 여성가족부 | 2023 | `[8.14.수.조간]가족돌봄,+고립은둔청년+전담+지원사업+개시.pdf` | 지원사업 정책 근거 |

### 17.5 출처 연결 원칙

- 모든 RAG chunk는 `doc_id`(위 표)와 `doc_page`를 반드시 포함한다.
- 검색 결과를 사용자에게 반환할 때 `[출처]` 형식을 항상 포함한다.
- 설문 문항이나 분류 알고리즘의 근거를 보여줄 때 `doc_support_001`, `doc_support_002`, `doc_support_003`을 우선 참조한다.
- 임의 사실을 생성하지 않는다. 근거가 없으면 출처 없음을 명시한다.

---

## 18. 문서 경계

이 문서는 RAG 파이프라인만 정의하며 아래는 별도 문서에서 정의한다.

### `SYSTEM_ARCHITECTURE.md`
- 전체 계층 구조
- API orchestration
- frontend/backend 책임

### `DATA_SCHEMA.md`
- entity / relation / candidate 구조
- metadata 필드 기준

### `API_SPEC.md`
- evidence endpoint 계약

### `PROMPT_DESIGN.md`
- evidence summary prompt
- final response composer prompt

### `EVALUATION_GUIDELINE.md`
- parse / retrieval / chunk 품질 평가 기준

---

## 19. 최종 요약

본 시스템에서 RAG는 추천 엔진이 아니라 **설명 근거 검색 계층**이다.  
현재 파이프라인의 중심은 아래 두 가지다.

1. **문서형 소스를 검색 가능한 구조로 안정적으로 변환**
2. **추천 결과에 근거 snippet을 결합할 수 있도록 retrieval 제공**

즉, 현재 단계의 RAG는 dense 중심 evidence retrieval 구조를 먼저 안정화하는 것이 목표다.
