# SYSTEM_ARCHITECTURE.md

> **파일명**: SYSTEM_ARCHITECTURE.md  
> **최종 수정일**: 2026-05-07  
> **문서 해시**: SHA256:TBD
> **문서 역할**: 시스템 구성, 계층, 책임, 데이터 흐름 정의 문서  
> **문서 우선순위**: 3  
> **연관 문서**: README.md, CHANGE_CONTROL.md, PRD.md, FEATURE_SPEC.md, DATA_SCHEMA.md, API_SPEC.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md  
> **참조 규칙**: 시스템 계층, 모듈 책임, 데이터 흐름, 저장소 경계를 변경할 때 먼저 이 문서를 수정한다.

---

## 1. 문서 목적

이 문서는 시스템의 **구성 요소**, **계층별 책임**, **온라인 요청 흐름**, **오프라인 데이터 구축 흐름**, **저장소 경계**를 정의한다.  
이 문서는 확정된 제품 요구사항을 실제 구현 가능한 시스템 구조로 변환하는 기준 문서다.

이 문서는 다음을 정의한다.

- 프론트엔드 / 백엔드 / RAG / canonicalization 계층 구조
- 온라인 요청 처리 흐름
- 오프라인 인덱스 및 canonical data 구축 흐름
- 저장소 역할 분리
- 현재 활성 범위와 reserved 범위
- 문서 간 구조적 경계

이 문서는 다음을 직접 정의하지 않는다.

- 제품 문제 정의와 사용자 가치
- 기능별 입력/출력/예외처리 상세
- API endpoint 상세 계약
- DB 컬럼 단위 상세 정의
- Parse / Chunk / Retrieval 세부 알고리즘
- 평가 지표와 실험 절차
- 프롬프트 세부 내용

위 항목은 각각 `PRD.md`, `FEATURE_SPEC.md`, `API_SPEC.md`, `DATA_SCHEMA.md`, `RAG_PIPELINE.md`, `EVALUATION_GUIDELINE.md`, `PROMPT_DESIGN.md`에서 담당한다.

---

## 2. 시스템 경계

본 시스템은 크게 아래 두 영역으로 나뉜다.

### 2.1 Online Serving
사용자 요청을 받아 추천 결과, 로드맵, 설명 근거를 응답하는 런타임 계층

구성:
- Frontend
- Backend API / Service Layer
- Recommendation Core
- Evidence Retrieval
- Storage Access

**현재 구현 참고 (스택)**: 프론트는 React + Vite(`frontend/`). 백엔드는 FastAPI(`backend/`). Evidence retrieval 런타임은 **LangChain** 임베딩(OpenAI 또는 HuggingFace)과 **Supabase pgvector**(`backend/rag/`)를 사용한다. 벡터 DB는 팀·테넌트 Supabase 프로젝트 URL·service_role 키로만 연결한다. 배포 가정: 프론트 Vercel, API Railway 또는 Render — CORS·`VITE_API_BASE_URL` 등 환경변수로 출처를 맞춘다. **LlamaIndex** 전환 시 `backend/rag/llamaindex/` 및 `RAG_PIPELINE.md`를 선행 갱신한다.

### 2.2 Offline Build
추천과 검색이 가능하도록 데이터를 구축·정규화·인덱싱하는 배치 계층

구성:
- PDF / HTML ingest
- CSV canonicalization
- index build
- validation
- evaluation / reporting

즉, 시스템은 **실시간 응답 계층**과 **사전 구축 계층**을 분리해서 운영한다.

---

## 3. 아키텍처 원칙

### 3.1 역할 분리 원칙
시스템은 아래 3개 축을 분리해서 설계한다.

1. **Recommendation Core**
   - 추천 후보와 로드맵 단계를 계산하는 구조적 기반

2. **Evidence Retrieval**
   - PDF / HTML 문서에서 설명 근거를 검색하는 계층

3. **Delivery Layer**
   - 프론트 요청을 받아 결과를 조합해 응답하는 계층

즉, 구조적 추천과 설명 근거 검색은 같은 계층에서 처리하지 않는다.

### 3.2 source_type 분리 원칙
데이터는 source_type에 따라 다른 처리 경로를 사용한다.

- PDF / HTML → Parse 및 indexing 대상
- CSV → structured no-parse canonicalization 대상
- API → 후속 스프린트에서 canonical target schema 병합 대상

### 3.3 taxonomy 고정 원칙
추천 결과의 정합성을 위해 자유 텍스트 라벨을 허용하지 않는다.

- `related_domains`는 도메인 taxonomy 세부 라벨만 사용
- `related_jobs`는 희망 직무 taxonomy 세부 직무만 사용

### 3.4 단계적 활성화 원칙
최종 구조를 먼저 고정하되, 모든 계층을 동시에 활성화하지 않는다.

**시스템 전역**에서 당장 활성화하지 않는 기능의 목록은 본 문서 `§14. 현재 활성 범위`의 **reserved**를 기준으로 한다(중복 나열을 피한다).  
**RAG 인덱싱·검색**만의 세부 reserved(예: sparse 상시, parent-child 고도화)는 `RAG_PIPELINE.md` §15를 따른다.

---

## 4. 상위 구성 요소

시스템은 아래 6개 영역으로 구성된다.

1. **Frontend**
2. **Backend Application Layer**
3. **Recommendation Core**
4. **RAG Evidence Layer**
5. **Storage Layer**
6. **Offline Build / Evaluation Layer**

---

## 5. 상위 아키텍처 다이어그램

```text
[User]
   ↓
[Frontend]
   ↓
[Backend API / Service Layer]
   ├─ Recommendation Core
   │   └─ Canonical Relational Store
   │
   ├─ Roadmap Builder
   │   └─ Canonical Relational Store
   │
   └─ Evidence Retrieval
       ├─ Vector Store
       └─ Sparse/BM25 Store (optional)

────────────────────────────────────────────────────────

[Raw Knowledge Sources]
├─ Official PDF / HTML
├─ Structured CSV
└─ External API (후속 스프린트)

         ↓

[Offline Build Layer]
   ├─ PDF / HTML Ingest
   │  ├─ Parse
   │  ├─ Chunk
   │  ├─ Metadata
   │  └─ Embedding
   │
   ├─ CSV Canonicalization
   │  ├─ Schema Mapping
   │  ├─ Canonicalization
   │  ├─ Entity Build
   │  ├─ Relation Build
   │  └─ Candidate Build
   │
   └─ Validation / Index Build

         ↓

[Storage Layer]
├─ Canonical Relational Store
├─ Vector Store
└─ Sparse/BM25 Store (optional)
```

---

## 6. Frontend 아키텍처

프론트엔드는 사용자 입력과 결과 표시를 담당하는 계층이다.  
프론트는 가능한 한 얇게 유지하며, 도메인 판단과 추천 계산은 백엔드에 둔다.

### 핵심 사용자 흐름 (3단계)

```
Home
  → RiskAssessment  (STEP 1: 12문항 설문 → 위험군 판정)
  → InterestSelection  (STEP 2: 관심 도메인·직무 선택)
  → Roadmap  (STEP 3: 위험군×도메인 기반 단계형 로드맵)
       └→ Recommendation  (심화: 자격증 상세·설명 근거)
```

### 주요 책임
- 12문항 설문 제공 및 위험군 판정 UX
- 관심 도메인·직무 선택 수집 (taxonomy 기준)
- 로드맵 단계형 결과 렌더링
- 추천 자격증 결과 렌더링
- 설명 근거 표시
- 추후 일정/링크 화면 제공

### 현재 활성 범위
- Home
- RiskAssessment (12문항 설문 + 위험군 판정 + Safety Override)
- InterestSelection (도메인 선택, 직무 선택)
- Roadmap
- Recommendation

### reserved
- Schedule
- Admin

---

## 7. Backend Application Layer 아키텍처

백엔드 애플리케이션 계층은 전체 요청 흐름의 조정자다.  
프론트 요청을 받아 입력을 정리하고, recommendation core와 evidence retrieval 결과를 결합해 최종 응답을 만든다.

### 주요 책임
- API endpoint 제공
- request/response schema 검증
- 위험군 기준 반영
- recommendation orchestration
- roadmap 생성
- evidence retrieval 호출
- 응답 포맷 조립

### 핵심 서비스
- `risk_stage_service`
- `recommendation_service`
- `roadmap_service`
- `retrieval_service`
- `metadata_service`

### reserved
- `schedule_service`

---

## 8. Recommendation Core 아키텍처

Recommendation Core는 구조적 추천을 담당한다.  
이 계층은 문서 검색이 아니라 canonical data를 바탕으로 추천 후보와 로드맵 연결을 계산한다.

### 주요 입력
- `risk_stage_id`
- 정규화된 직무
- 정규화된 도메인
- canonical entity / relation
- recommendation candidate row

### 주요 출력
- 추천 후보 리스트
- 관련 직무/도메인 연결 정보
- 연결 가능한 roadmap stage 정보

### 원칙
- 자유 텍스트 추천 라벨을 직접 생성하지 않는다.
- recommendation core는 canonical data를 사실 기반으로 사용한다.
- 문서형 evidence는 이 계층이 아니라 retrieval 계층에서 가져온다.
- **위험군 단계가 높을수록(4~5단계) 낮은 등급(기능사·산업기사)을 우선 추천하고, 기사·기술사는 후순위로 조정한다.** 이 계층 조정은 Certificate 엔티티의 `cert_grade_tier` 필드 기반으로 수행한다. (`DATA_SCHEMA.md` §4.7, §5.3 참조)
- **로드맵은 flat list가 아니라 `cert_prerequisite` 관계(`DATA_SCHEMA.md` §6.8)를 방향 그래프(DAG)로 순회하여 생성한다.** 사용자 현재 위치에서 실제 이동 가능한 경로만 로드맵 단계 후보에 포함한다.

---

## 9. RAG Evidence Layer 아키텍처

RAG 계층은 PDF / HTML 기반 공식 문서를 검색 가능한 상태로 변환하고, 이후 설명 근거를 검색하는 역할을 담당한다.  
이 계층의 목적은 추천 계산이 아니라 **설명 근거 검색**이다.

### 입력 소스
- Official PDF
- Official HTML
- FAQ
- 공고문
- 공식 안내 페이지

### 계층 역할
- source profiling
- parse
- chunking
- metadata tagging
- embedding
- evidence retrieval

### 산출물
- evidence snippet
- provenance metadata
- optional score / validity metadata

### 상세 원칙
Parse, chunking, embedding, dense/sparse, fusion, reranker 세부 기준은 `RAG_PIPELINE.md`를 따른다.  
청크 빌더 직전 **parse IR**의 최소 필드 계약은 `RAG_PIPELINE.md` §6.7이고, 영속화되는 **문서형 chunk** 필드는 `DATA_SCHEMA.md`를 따른다.

---

## 10. CSV Canonicalization 아키텍처

CSV는 Parse IR을 만들지 않고, 구조화된 추천 기반 자산으로 변환한다.

### 주요 책임
- dataset type 판별
- schema mapping
- canonicalization
- entity 생성
- relation 생성
- candidate row 생성
- validation report 생성

### 입력 예시
- cert_master
- cert_alias
- cert_domain_mapping
- cert_job_mapping
- roadmap_stage_master
- risk_stage_master

### 핵심 산출물
- canonical entities
- canonical relations
- recommendation candidate rows

### 원칙
- CSV는 structured no-parse 경로를 따른다.
- 자유 텍스트 taxonomy 생성을 허용하지 않는다.
- recommendation core의 구조적 사실 기반을 만든다.

---

## 11. Storage Layer 아키텍처

저장 계층은 목적에 따라 분리한다.

### 11.1 Canonical Relational Store
구조화된 추천 기반 저장소

저장 대상 예:
- entities
- relations
- candidate rows
- risk stage / roadmap stage 기준 데이터

### 11.2 Vector Store
설명 근거 검색용 dense retrieval 저장소

저장 대상 예:
- FAQ chunk
- 안내문 chunk
- 공고문 chunk
- HTML 설명 chunk

### 11.3 Sparse / BM25 Store
exact match 보강용 선택 저장소

저장 대상 예:
- alias 기반 exact text
- 기관명 / 자격증명 / 직무명
- exact-sensitive 텍스트

현재는 optional이다.

---

## 12. Online Runtime Flow

### 12.1 핵심 사용자 흐름 (3단계)

**[STEP 1] 위험군 진단**  
1. 사용자가 RiskAssessment 화면에서 12문항 설문을 완료한다.  
2. 프론트가 응답 점수 합계로 위험군 단계(1~5)를 판정한다 (백엔드 호출 없음, 클라이언트 사이드).  
3. Safety Override: 정신건강 위기 응답 시 최소 4단계로 조정 및 위기 안내 배너 표시.  
4. 결과 화면에서 단계와 카테고리별 점수를 표시한다.

**[STEP 2] 관심 도메인·직무 선택**  
5. 사용자가 InterestSelection 화면으로 이동한다 (위험군 단계가 URL 파라미터로 전달됨).  
6. 허용된 domain taxonomy 세부 라벨에서 도메인을 선택한다.  
7. (직무 선택 UI가 있는 경우) 허용된 job taxonomy 세부 직무에서 직무를 선택한다.

**[STEP 3] 로드맵·추천 조회**  
8. 사용자가 Roadmap 화면으로 이동한다 (위험군·도메인·직무가 URL 파라미터로 전달됨).  
9. 프론트가 `/api/v1/recommendations` POST로 로드맵을 요청한다.  
10. API 미연결 시 로컬 cert_candidates.json fallback으로 로드맵을 구성한다.  
11. 자격증 클릭 시 Recommendation 화면으로 이동해 상세 정보와 설명 근거를 확인한다.

### 12.2 추천 요청 흐름 (백엔드 연결 후)
1. 프론트가 위험군·도메인·직무를 담아 recommendation API를 호출한다.
2. 백엔드는 위험군 기준을 적용한다.
3. recommendation core가 canonical store에서 candidate row를 조회한다.
4. 필요 시 evidence retrieval 계층이 설명 근거를 검색한다.
5. recommendation service가 추천 결과와 근거를 조합한다.
6. 프론트가 결과를 렌더링한다.

### 12.3 로드맵 요청 흐름
1. 사용자가 추천 결과 또는 위험군 기준으로 로드맵을 요청한다.
2. 백엔드는 canonical relation과 roadmap 기준을 조회한다.
3. roadmap service가 단계형 결과를 생성한다.
4. 프론트가 단계 순서와 관련 자격증/도메인을 표시한다.

---

## 13. Offline Build Flow

### 13.1 문서형 지식 구축 흐름
1. PDF / HTML 원본을 수집한다.
2. source profiling을 수행한다.
3. parse를 수행한다.
4. chunk를 생성한다.
5. metadata를 부여한다.
6. embedding을 생성한다.
7. vector store 및 optional sparse store에 적재한다.

### 13.2 구조화 추천 데이터 구축 흐름
1. CSV 원본을 수집한다.
2. dataset type을 판별한다.
3. schema mapping을 수행한다.
4. canonicalization을 수행한다.
5. entity / relation을 생성한다.
6. recommendation candidate row를 생성한다.
7. validation report를 생성한다.
8. canonical relational store에 적재한다.

### 13.3 운영자 갱신 흐름
1. 운영자가 CSV 마스터/매핑 데이터를 교체한다.
2. canonicalization pipeline이 실행된다.
3. entity / relation / candidate row를 재생성한다.
4. 필요 시 index-ready 데이터와 retrieval 인덱스를 갱신한다.

### 13.4 데이터 수집 완료 후 실행 전제(준비 vs 코드)

원본 파일만 채워 넣었다고 해서 **두 레인이 모두 자동 실행되는 것은 아니다.**  
폴더·스키마·환경·DB·청크 JSONL 형식 등 **준비 체크리스트**와, 레인별 **현재 코드 연결 여부(스텁 포함)** 는 `PROJECT_SUMMARY.md` §8·§9를 단일 참조로 본다.

---

## 14. 현재 활성 범위

### 활성화
- 위험군 기반 recommendation 진입
- certificate candidate row 기반 추천
- roadmap 제안
- PDF / HTML evidence retrieval
- CSV canonicalization
- parse / chunk / metadata / embedding 기본 파이프라인

### reserved
- 시험 일정 API
- 접수 일정 API
- 지원 링크 실연동
- reranker 활성화
- shared 공용 타입 계층
- full infra 배포 구조

---

## 15. 시스템 경계

이 문서는 시스템 구조만 정의하며, 아래 항목은 별도 문서에서 정의한다.

### `PRD.md`
- 해결할 문제
- 타깃 사용자
- 제품 범위 / 비범위

### `FEATURE_SPEC.md`
- 기능별 입력 / 출력 / 예외처리

### `API_SPEC.md`
- endpoint / request / response

### `DATA_SCHEMA.md`
- 실제 컬럼, 엔티티, 관계, schema 구조

### `RAG_PIPELINE.md`
- parse / chunk / embedding / retrieval 세부 전략
- fusion / sparse / dense 운영 기준

### `EVALUATION_GUIDELINE.md`
- metric
- baseline
- 채택 / 기각 기준

### `DIRECTORY_SPEC.md`
- 폴더와 파일 구조

---

## 16. 디렉토리 매핑

시스템 구조는 다음 디렉토리와 대응된다.

- `frontend/` → 사용자 인터페이스
- `backend/app/` → API / 서비스 조정 계층
- `backend/rag/` → parse / retrieval 계층
- `backend/canonical/` → CSV canonicalization 계층
- `data/` → raw / canonical / index-ready 저장소
- `scripts/` → 배치 실행
- `experiments/` → 실험 / 로그 / 보고서

---

## 17. 핵심 아키텍처 결정

1. 구조적 추천과 설명 근거 검색을 분리한다.
2. source_type에 따라 처리 경로를 분리한다.
3. CSV는 Parse IR 대상이 아니다.
4. taxonomy 밖 자유 라벨 생성을 허용하지 않는다.
5. API 최신성 정보는 후속 병합 대상으로 둔다.
6. 온라인 서빙 계층과 오프라인 구축 계층을 분리한다.
7. MVP에서는 구조 안정화가 우선이며, 고도화 기능은 reserved로 둔다.
8. 위험군 단계가 높을수록 낮은 등급(기능사·산업기사)이 우선 추천되도록 `cert_grade_tier` 기반 정렬을 적용한다. 기사·기술사는 고위험군 사용자에게 후순위다.
9. 로드맵은 flat list가 아니라 `cert_prerequisite` 관계를 DAG로 순회하여 생성한다. 사용자 현재 위치에서 실제 이동 가능한 경로만 제시한다.

---

## 18. 오픈 이슈

1. 위험군 2~4단계의 세부 의미와 판정 기준
2. roadmap stage의 최종 단계명과 단계 수
3. 일정 API 병합 시 canonical target schema 세부 구조
4. reranker 활성화 조건
5. sparse store 상시 사용 여부

---

## 19. 최종 요약

본 시스템은 아래 3개 계층의 결합으로 이해할 수 있다.

- **Canonical Recommendation Layer**
- **RAG Evidence Layer**
- **API Orchestration Layer**

즉, 구조적 추천은 canonicalization 계층이 담당하고, 설명 근거는 RAG 계층이 담당하며, 최종 사용자 응답은 backend application layer가 조립한다.

현재 MVP의 목표는 이 3개 계층을 먼저 안정적으로 연결하는 것이다.
