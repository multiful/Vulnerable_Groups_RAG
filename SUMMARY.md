# SUMMARY.md

> **파일명**: SUMMARY.md  
> **최종 수정일**: 2026-05-15  
> **문서 해시**: SHA256:TBD  
> **문서 역할**: 구현된 기능·데이터 소스·API·기술 스택 핵심 요약 — 빠른 파악용  
> **문서 우선순위**: reference  
> **연관 문서**: README.md, PRD.md, FEATURE_SPEC.md, API_SPEC.md, RAG_PIPELINE.md  
> **참조 규칙**: 기능 구현 현황의 빠른 파악에만 사용한다. 정책·계약의 기준은 각 상세 문서를 따른다.

---

## 1. 한 줄 소개

> 청년 위험군 단계(1~5) + 관심 분야를 입력하면, 맞춤 자격증 로드맵과 공식 문서 기반 근거를 함께 제공하는 추천 시스템.

---

## 2. 사용자 파이프라인

```
위험군 진단 ──► 관심 분야 선택 ──► 성장 로드맵 ──► 자격증 상세 확인
  /risk-assessment   /interests       /roadmap        /recommendation
```

- 각 단계의 선택값(stage, domain, job)은 **sessionStorage**에 저장됨
- `/roadmap` 이후는 이전 진단 없이 직접 접근 불가 (pipeline guard)
- 헤더 내비게이션으로 이탈 후 복귀해도 컨텍스트 자동 복원

---

## 3. 페이지별 구현 기능

### 3.1 위험군 진단 (`/risk-assessment`)
| 항목 | 내용 |
|------|------|
| 문항 수 | 12문항 (관계망 4·활동 2·노동경제 2·정신건강 3·자기관리 1) |
| 판정 방식 | 총점 비율(%)로 1~5단계 산출 |
| Safety Override | 자해·자살 항목 "일주일 이상" 이상 응답 → 최소 4단계 강제 |
| 결과 화면 | 단계 뱃지 + 진행 바 + 5축 레이더 차트 + 카테고리별 막대 바 |
| 위기 안내 | Safety Override 발동 시 1393 상담전화 배너 표시 |

### 3.2 관심 분야 선택 (`/interests`)
| 항목 | 내용 |
|------|------|
| 도메인 taxonomy | 43개 도메인, 9개 대분류 그룹 |
| 직무 taxonomy | 142개 직무, 12개 대분류 그룹 |
| 도메인 선택 | 필수 (1개) |
| 직무 선택 | 선택 사항 (1개) — 접기/펼치기 UI |
| 단계 표시 | URL 또는 sessionStorage에서 복원한 위험군 단계 표시 |

### 3.3 성장 로드맵 (`/roadmap`)
| 항목 | 내용 |
|------|------|
| 로드맵 단계 | 5단계 타임라인 (상태 인식→탐색 시작→역량 준비→실행 확대→유지 및 정착) |
| 시작점 | 위험군에 따라 자동 결정 (1단계→역량준비, 4~5단계→상태인식) |
| 데이터 소스 | 백엔드 API 우선, 5초 타임아웃 후 로컬 candidates 폴백 |
| 탭 | 전체 추천 / ✦ AI 맞춤 추천 (LLM 30초 분석) |
| 자격증 카드 | 등급 뱃지, 합격률, 도전 난이도(바로/단기/장기), AI 추천 이유 |
| 인라인 드로어 | 자격증 클릭 → 자격 활용·소개·시험 정보·연결 경로 즉시 표시 |
| DAG | 선수·후속 자격증 흐름 다이어그램 (`CertFlowDiagram`) |
| Guard | stage 없이 직접 접근 시 `/risk-assessment`로 리디렉션 |

### 3.4 자격증 확인 (`/recommendation`)
| 항목 | 내용 |
|------|------|
| 자격증 목록 | 최대 60건 그리드, 위험군·도메인·직무 필터링 |
| 검색 | 자격증명·발급기관·도메인·직무 텍스트 검색 (디바운스) |
| 등급 필터 | 기능사 / 산업기사 / 기사 / 기술사 / 기능장 |
| Evidence 패널 | 자격증 클릭 → 슬라이딩 패널 표시 |
| — 자격 활용 현황 | 공인민간자격(+항목 목록) 또는 국가자격(진로·취업처) |
| — 자격증 소개 | 도입목적 (파란 박스) |
| — 직무·역할 | 관련 직무 목록 |
| — 시험 정보 | 난이도·합격률·연간 시험 횟수·시험 구성(필기/실기/면접) (pill 뱃지) |
| — AI 추천 이유 | GPT 기반 개인화 설명 — RAG evidence·exam_type_info 기반 (보라색 박스) |
| — 응시료·공인 정보 | 공인번호·주무부처·유효기간 |
| — 시험 일정 | Q-Net 실시간 조회 (국가기술자격·국가전문자격 통합) |
| — 채용공고 | WorkNet 실시간 채용공고 (cert_id → NCS 직종코드 파생) |
| — 훈련과정 | Work24 훈련과정 + 일학습병행 + 과정평가형 |
| DAG | 선수·후속 자격증 연결 경로 |
| 관련 동영상 | YouTube 강의 영상 썸네일 그리드 (캐시 지원) |
| browse 모드 | 진단 없이 홈 "자격증 둘러보기"로 접근 가능 |

---

## 4. 데이터 소스

| 소스 | 형태 | 항목 수 | 주요 필드 |
|------|------|---------|-----------|
| 공인민간자격 정보자료집 (2025) | PDF → JSON | 140종 | 자격 활용 현황, 응시료, 공인번호, 유효기간, 주무부처 |
| 국가자격 정보집 (2026) | PDF → JSON | 138종 | 진로(자격활용), 도입목적, 응시료, 시행기관 |
| cert_candidates.jsonl | JSONL | 1,290행 | cert_id, 도메인, 직무, 위험군 단계, 로드맵 단계, 합격률, 난이도 |
| cert_master.csv | CSV | 1,290행 | cert_id → cert_name, exam_type_info, exam_subject_info 등 |
| Supabase certificates_vectors | pgvector | — | 청크 임베딩 + section_path 메타데이터 |
| Q-Net ExamScheduleService | 실시간 API | 1,290종 | 시험·접수 일정, D-Day |
| WorkNet 채용정보 API | 실시간 API | — | 채용공고, 직종코드 파생 |
| Work24 훈련과정 API | 실시간 API | — | 훈련과정, 일학습병행, 과정평가형 |

### 카탈로그 매핑 로직
- 정확 일치 → 양방향 부분 일치 (공백·괄호 정규화 후)  
- 예: `정보기술자격(ITQ) C급` → 카탈로그 키 `정보기술자격(ITQ)` 매핑

---

## 5. 백엔드 API 요약

| 메서드 | 경로 | 역할 |
|--------|------|------|
| `POST` | `/api/v1/recommendations` | 위험군 × 도메인 기반 로드맵 데이터 반환 |
| `POST` | `/api/v1/recommendations/llm` | LLM AI 맞춤 로드맵 분석 |
| `POST` | `/api/v1/recommendations/evidence` | 자격증 evidence (자격활용·근거 청크) |
| `POST` | `/api/v1/recommendations/cert_explain` | 자격증 AI 추천 이유 생성 |
| `GET`  | `/api/v1/recommendations/related` | 자격증 DAG (선수·후속 관계) |
| `GET`  | `/api/v1/candidates` | 전체 cert candidates 목록 |
| `GET`  | `/api/v1/certs/{cert_id}/stats` | cert_master 통계 (합격률·시험횟수·exam_type_info) |
| `GET`  | `/api/v1/certs/{cert_id}/videos` | YouTube 관련 동영상 (캐시 포함) |
| `GET`  | `/api/v1/schedule/exam` | Q-Net 시험 일정 (국가기술자격·국가전문자격) |
| `GET`  | `/api/v1/jobs/hiring/by-cert/{cert_id}` | WorkNet 채용공고 (NCS 직종코드 파생) |
| `GET`  | `/api/v1/training/courses/by-cert/{cert_id}` | Work24 훈련과정 + 일학습병행 |
| `GET`  | `/api/v1/seoul/job-cafes` | 서울시 일자리카페 목록 |
| `GET`  | `/api/v1/actions/today` | 위험군 단계별 오늘의 한 가지 행동 제안 |

### Evidence 우선순위
```
국가자격 카탈로그 JSON  →  공인민간자격 카탈로그 JSON
         ↓                         ↓
    Supabase RAG 결과 병합   →   candidates text_for_dense (fallback)
```

---

## 6. 기술 스택

| 영역 | 기술 |
|------|------|
| 프론트엔드 | React 19, TypeScript, Vite 6, React Router v6 |
| 백엔드 | Python, FastAPI |
| 벡터 DB | Supabase pgvector (`match_certificates` RPC) |
| 임베딩 | OpenAI `text-embedding-3-small` |
| LLM | OpenAI GPT (로드맵 분석, 추천 이유) |
| 동영상 | YouTube Data API v3 + 서버 사이드 캐싱 |
| 배포 | API: Render.com / 프론트: Vite dev (로컬) |
| 상태 관리 | URL params + sessionStorage (`pipelineState.ts`) |

---

## 7. 프로젝트 구조 (핵심 경로)

```
project-root/
├─ frontend/src/
│   ├─ pages/
│   │   ├─ RiskAssessment/    위험군 진단 설문
│   │   ├─ InterestSelection/ 도메인·직무 선택
│   │   ├─ Roadmap/           단계형 로드맵
│   │   └─ Recommendation/    자격증 목록·evidence
│   ├─ components/
│   │   └─ charts/CertFlowDiagram.tsx  DAG 다이어그램
│   └─ utils/
│       └─ pipelineState.ts   파이프라인 세션 저장
│
├─ backend/app/
│   ├─ api/v1/routes/         FastAPI 라우터
│   └─ services/
│       ├─ retrieval_service.py   evidence + 카탈로그 매핑
│       ├─ recommendation_service.py
│       └─ dag_service.py
│
└─ data/
    ├─ canonical/candidates/cert_candidates.jsonl
    └─ index_ready/
        ├─ private_cert_catalog.json  공인민간자격 140종
        └─ national_cert_catalog.json 국가자격 138종
```

---

## 8. Reserved (미구현)

- 지원 링크 실연동 (Q-Net 원서접수 직링크)
- reranker, sparse/BM25 상시 사용
- parent-child chunk 고도화
- 상담형 대화 에이전트
- 위험군 2~4단계 세부 의미 확정
