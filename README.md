# README.md

> **파일명**: README.md  
> **최종 수정일**: 2026-05-07  
> **문서 해시**: SHA256:TBD
> **문서 역할**: 프로젝트 최상위 안내 문서 / 관문 문서  
> **문서 우선순위**: 0  
> **연관 문서**: CHANGE_CONTROL.md, PRD.md, SYSTEM_ARCHITECTURE.md, DIRECTORY_SPEC.md, PROJECT_SUMMARY.md, RAG_PIPELINE.md, Indexing_Architecture.txt  
> **참조 규칙**: 작업 시작 전 본 문서와 `CHANGE_CONTROL.md`를 먼저 읽고, 이후 관련 상세 문서를 확인한다.

---

# 청년 위험군 맞춤형 자격증·로드맵 추천 시스템

청년 위험군 단계와 관심 직무/도메인을 바탕으로, 관련 자격증을 추천하고 단계형 로드맵을 제안하는 시스템이다.  
추후 시험 일정, 접수 일정, 지원 링크까지 연결할 수 있는 확장 구조를 목표로 하지만, 현재 단계에서는 **추천 구조와 지식 파이프라인을 먼저 안정화하는 것**을 우선한다.

---

## 1. 프로젝트 요약

### 핵심 사용자 흐름 (3단계)

```
[1단계] 설문으로 위험군 진단
   12문항 설문(관계망·활동·노동경제·정신건강·자기관리) → 1~5단계 위험군 판정
        ↓
[2단계] 관심 직무 + 도메인 선택
   허용된 taxonomy 안에서 관심 도메인(및 직무) 선택
        ↓
[3단계] 로드맵 + 자격증 추천 확인
   위험군 단계 × 선택 도메인 기반으로 단계형 로드맵과 추천 자격증 제공
```

이 프로젝트는 위 3단계 흐름을 안정적으로 구현하는 것을 현재 최우선 목표로 한다.

---

이 프로젝트는 아래 4개 축을 연결한다.

1. **위험군 단계**
   - 청년 사용자의 현재 상태를 설문(12문항)으로 진단하여 1단계 ~ 5단계 구조로 관리한다.

2. **구조적 추천**
   - 자격증을 단독 객체가 아니라 직무, 도메인, 로드맵 단계와 연결된 후보로 추천한다.

3. **문서 기반 설명 근거**
   - PDF / HTML 기반 공식 문서에서 추천 결과를 설명할 근거를 검색한다.

4. **추후 일정 확장**
   - 후속 스프린트에서 시험 일정, 접수 일정, 지원 링크를 연결한다.

---

## 2. 핵심 개념

### 2.1 위험군 단계
- **진단 방식**: 12문항 설문(관계망 4·활동 2·노동경제 2·정신건강 3·자기관리 1)으로 판정
- **1단계**: 취업 안정권
- **5단계**: 취업을 하고 싶어도 하기 어려운 가장 높은 위험군
- **2~4단계**: 단계형 위험군 체계로 관리하며, 세부 의미는 후속 문서에서 확정
- **Safety Override**: 정신건강 항목(자살·자해)에 "일주일 이상" 이상 응답 시 최소 4단계로 조정

### 2.2 taxonomy 원칙
- `related_domains`는 **도메인 taxonomy의 세부 라벨만 사용**
- `related_jobs`는 **희망 직무 taxonomy의 세부 직무만 사용**
- 자유 텍스트 라벨 생성은 허용하지 않는다

### 2.3 데이터 처리 원칙
- **PDF / HTML**: 설명형 지식 소스, Parse 및 indexing 대상
- **CSV**: 구조화 데이터 소스, structured no-parse canonicalization 대상
- **API**: 일정/링크 최신성 소스, 현재는 reserved 상태

---

## 3. 현재 범위

현재 프로젝트는 아래 범위를 우선 대상으로 한다.

- PDF / HTML / CSV 소스 구조 정리
- CSV canonicalization 및 entity / relation 구축
- recommendation candidate row 설계
- RAG 파이프라인 기반 설명 근거 검색 구조 설계
- 위험군 맞춤 추천 + 로드맵 제안 흐름 고정
- 루트 문서 기준선 정리

### 현재 제외 범위
- 일정 API 실연동
- 시험일정 / 접수일정 실데이터 연결
- reranker 학습
- hybrid 가중치 최적화
- generation prompt 고도화
- 위험군 2~4단계 세부 의미 확정

제품 목표와 범위의 상세 정의는 `PRD.md`를 따른다.

---

## 4. 시스템 개요

### 4.0 온라인 서빙 계층 (사용자 흐름)

| 단계 | 페이지 | 역할 |
|:---:|---|---|
| 1 | RiskAssessment | 12문항 설문 → 위험군 단계(1~5) 판정 |
| 2 | InterestSelection | 관심 도메인 + 직무 선택 (taxonomy 기준) |
| 3 | Roadmap | 위험군 × 도메인 기반 단계형 로드맵 제공 |
| 심화 | Recommendation | 자격증 상세·설명 근거 검색 |

### 4.1 PDF / HTML Lane
- HTML Direct Path
- Primary PDF Parser
- Table Assist / OCR / Fallback
- Chunk Builder
- Metadata Tagging
- Embedding / Retrieval

### 4.2 CSV / API Lane
- Dataset Type Registry
- Schema Mapping
- Canonicalization
- Entity Builder
- Relation Builder
- Candidate Row Builder

이 두 흐름은 이후 canonical merge, retrieval, recommendation 계층에서 연결된다.  
전체 구조의 상세 정의는 `SYSTEM_ARCHITECTURE.md`와 `RAG_PIPELINE.md`를 따른다.

---

## 5. 루트 문서 안내

이 프로젝트는 루트 md 문서를 기준선으로 운영한다.

| 문서명 | 역할 |
|---|---|
| `README.md` | 프로젝트 입구 문서 |
| `PROJECT_SUMMARY.md` | 저장소 한눈에 보기 — 목적·두 레인·스택·청킹 개요·긴 기법 문서 보관 위치 |
| `CHANGE_CONTROL.md` | 문서 수정 규칙, 메타데이터 갱신 원칙, 작업 절차 |
| `DIRECTORY_SPEC.md` | 디렉토리 구조와 파일/폴더 책임 |
| `ROOT_DOC_GUIDE.md` | 루트 문서 탐색·읽기 순서 안내 |
| `HASH_INCREMENTAL_BUILD_GUIDE.md` | 해시 키·증분 재처리 원칙 |
| `Indexing_Architecture.txt` | 인덱싱/지식 파이프라인 참고 구조 문서 |
| `PRD.md` | 문제 정의, 타깃 사용자, 제품 범위 |
| `SYSTEM_ARCHITECTURE.md` | 시스템 계층, 책임, 데이터 흐름 |
| `FEATURE_SPEC.md` | 기능별 입력/출력/예외처리 |
| `DATA_SCHEMA.md` | 엔티티, 관계, candidate row, 메타데이터 구조 |
| `CSV_CANONICALIZATION_TEAM_GUIDE.md` | CSV 레인 담당자(영민·유빈)용 수집·매핑·canonical 지침 |
| `API_SPEC.md` | API 계약, request/response, 오류 형식 |
| `PROMPT_DESIGN.md` | 프롬프트 역할, 입력 슬롯, 출력 계약 |
| `RAG_PIPELINE.md` | Parse / Chunk / Embedding / Retrieval 파이프라인 |
| `EVALUATION_GUIDELINE.md` | 평가 기준, baseline, 비교 원칙 |
| `EVALUATION.md` | 평가 결과 |
| `EXPERIMENT_GUIDE.md` | 실험 세팅과 재현 방법 |
| `ERROR_ANALYSIS.md` | 실패 사례와 개선 방향 |
| `DEV_LOG.md` | 진행 로그와 변경 이력 |

Cursor IDE용 작업 규칙은 `.cursor/rules/`에 둔다. (루트에 동일 본문 md를 두지 않는 것을 권장한다.)

**심화 참고(인덱싱·질의)**: 이 저장소의 **파이프라인 계약**은 `RAG_PIPELINE.md`가 우선한다. 인덱싱(Parse→Chunk→Embed·Store)과 evidence 검색 **질의·Pre-retrieval**을 실무 수준으로 정리한 **외부 장문 기준서**가 있다면 로컬에서만 참고하고, 설계 반영 시에는 루트 문서와 `PRD.md`·reserved 규칙을 따른다. 팀 공유가 필요 없는 자료는 `docs/references/_private/`에 두며 해당 경로는 Git에서 제외한다.

---

## 6. 문서 읽는 순서

작업 시작 시 아래 순서로 문서를 확인한다.

1. `README.md`
2. `CHANGE_CONTROL.md`
3. `PRD.md`
4. `SYSTEM_ARCHITECTURE.md`
5. 작업에 직접 관련된 상세 문서
   - 기능 수정 → `FEATURE_SPEC.md`
   - 데이터 구조 수정 → `DATA_SCHEMA.md`
   - API 수정 → `API_SPEC.md`
   - 프롬프트 수정 → `PROMPT_DESIGN.md`
   - RAG 파이프라인 수정 → `RAG_PIPELINE.md`
   - 디렉토리 수정 → `DIRECTORY_SPEC.md`

---

## 7. 최종 루트 디렉토리

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

세부 폴더 설명은 `DIRECTORY_SPEC.md`를 따른다.

---

## 8. 운영 원칙

이 프로젝트는 **루트 문서 리팩토링을 거친 뒤 구현하는 방식**으로 진행한다.

- 기능, 정책, 구조가 바뀌면 먼저 관련 루트 문서를 수정한다.
- 문서를 수정할 때는 상단 메타데이터의 `최종 수정일`도 함께 갱신한다.
- 해결된 문제는 PRD에 그대로 방치하지 않는다.
- 문서 간 충돌이 생기면 `CHANGE_CONTROL.md`의 우선순위를 따른다.
- 구조 변경 전에는 `DIRECTORY_SPEC.md`, 시스템 변경 전에는 `SYSTEM_ARCHITECTURE.md`를 먼저 수정한다.

자세한 운영 규칙은 `CHANGE_CONTROL.md`를 따른다.

---

## 9. 최종 요약

이 프로젝트는 아래 두 축을 먼저 안정화하는 것을 목표로 한다.

1. **CSV canonicalization 기반 추천 구조 정비**
2. **PDF / HTML 기반 설명 근거 검색 구조 정비**

즉, 현재 단계의 핵심은  
완성형 일정 연동 서비스가 아니라  
**위험군 맞춤 추천 + 로드맵 제안 + 설명 근거 결합이 가능한 기준 구조를 만드는 것**이다.

---

## 10. 기술 스택 (개발 중)

| 영역 | 선택 |
|------|------|
| 프론트 | React 19 + Vite 6 (`frontend/`) |
| API | FastAPI (`backend/`) |
| RAG 런타임 | LangChain (LlamaIndex 대안은 `backend/rag/llamaindex/` 자리만) |
| 벡터 DB | Supabase pgvector (URL·키는 환경변수, `docs/architecture/supabase_langchain.sql` 참고) |
| 임베딩 | OpenAI 또는 HuggingFace (`EMBEDDING_PROVIDER`) |
| 배포 | 프론트 Vercel / API Railway·Render (예시) |

로컬 실행 요약은 `backend/README.md`, `frontend/README.md`, `infra/env/.env.example` 를 본다.
