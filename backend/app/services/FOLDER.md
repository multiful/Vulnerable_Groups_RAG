# FOLDER.md

> **파일명**: FOLDER.md
> **폴더 경로**: `backend/app/services/`
> **최종 수정일**: 2026-07-01 (llm_roadmap_service: 지원제도 추천 함수 추가, risk_stage null 수정, cert_explain refine 강화)
> **문서 해시**: SHA256:TBD
> **문서 역할**: 백엔드 비즈니스 로직 서비스 계층 설명
> **연계 경로**: backend/app/api/v1/routes/

## 1. 개요

이 폴더는 애플리케이션의 핵심 비즈니스 로직을 처리하는 서비스 모듈을 포함한다.  
API 엔드포인트에서 전달된 요청을 처리하고, Supabase / 로컬 CSV / 외부 공공 API와 상호작용한다.  
외부 공공 API 연동 서비스는 **반드시 `cert_lookup_service`를 경유해 파라미터를 파생**한다 (직접 문자열 매칭 금지).

---

## 2. 파일 목록

### 2.1 추천 핵심 계층

| 파일 | 역할 | 상태 |
|---|---|---|
| `recommendation_service.py` | 위험군×도메인×직무 기반 자격증 추천 후보 조립 | ✅ 활성 |
| `risk_stage_service.py` | 위험군 단계 정보 조회 | ✅ 활성 |
| `roadmap_service.py` | 단계형 로드맵 생성 (DAG 순회) | ✅ 활성 |
| `retrieval_service.py` | LangChain 기반 RAG Evidence 검색 (BM25 keyword chunk fallback 포함) | ✅ 활성 |
| `chat_service.py` | 청년 진로 상담 에이전트 — GPT-4o-mini 기반 대화 Q&A | ✅ 활성 |
| `metadata_service.py` | 데이터 메타데이터 관리 및 조회 | ✅ 활성 |
| `dag_service.py` | cert_prerequisite DAG 순회 유틸리티 | ✅ 활성 |
| `youtube_service.py` | cert_id 기반 YouTube 강의 영상 추천 (30일 캐시) | ✅ 활성 |
| `llm_roadmap_service.py` | LLM 기반 로드맵 텍스트 조립 | ✅ 활성 |
| `health_service.py` | 헬스체크 응답 | ✅ 활성 |

### 2.2 Execution Layer (공공데이터 API 연동)

| 파일 | 역할 | 상태 |
|---|---|---|
| `cert_lookup_service.py` | cert_id → NCS → WorkNet/Work24 파라미터 파생 중심 서비스 (데이터 체인 진입점) | ✅ 활성 |
| `exam_schedule_service.py` | Q-Net 시험·접수 일정 조회, D-Day 계산 (hrdkorea_api_key_in) | ✅ 활성 |
| `jobs_service.py` | WorkNet 채용정보 XML 조회 + 고용24 직업정보 CSV 로컬 조회 | ✅ 활성 |
| `training_service.py` | Work24 훈련과정 XML 조회 + Q-Net 과정평가형 자격 JSON 조회 | ✅ 활성 |
| `seoul_service.py` | 서울시 공공데이터 (일자리카페·건강증진센터·공공예약) JSON 조회 | ✅ 활성 |
| `action_service.py` | 위험군 단계 기반 오늘의 한 가지 행동 제안 (단계별 템플릿) | ✅ 활성 |
| `schedule_service.py` | (legacy stub — exam_schedule_service로 대체됨) | ⚠️ 미사용 |
| `map_service.py` | 지도 인프라 점 집계 — Seoul API + Work24 + Kakao REST 지오코딩 | ✅ 활성 |
| `goms_service.py` | GOMS 분석 기반 자격증-직무-전공 연결 서비스 (job_raw_merged, ncs_mapping, 고용24 CSV 기반) | ✅ 활성 |
| `career_net_service.py` | 커리어넷 직업정보(JOB) + 학과정보(MAJOR) API 연동 (career_net_api_key) | ✅ 활성 |
| `cert_info_service.py` | 한국산업인력공단 Q-Net 국가자격 종목별 자격정보(항목 8) + 시험정보(항목 9) API 연동 (hrdkorea_api_key_in) | ✅ 활성 |
| `ncs_service.py` | NCS 능력단위별 자격 종목 조회 (항목 10) — cert_ncs_mapping.csv + ncs_master.csv 로컬 기반 | ✅ 활성 |
| `welfare_central_service.py` | 복지로 OPEN API — 중앙부처복지서비스 목록 조회 (bokjiro_api_key) | ✅ 활성 |
| `welfare_local_service.py` | 복지로 OPEN API — 지자체복지서비스 목록 조회 (bokjiro_api_key) | ✅ 활성 |
| `family_center_service.py` | 성평등가족부 — 건강가정지원센터 시설 조회 (gender_welfare_api_key) | ✅ 활성 |
| `gender_facility_service.py` | 성평등가족부 — 여성·가족·청소년·권익시설 조회 (gender_welfare_api_key) | ✅ 활성 |
| `worknet_govt_jobs_service.py` | 워크넷 정부지원일자리 참여자모집 조회 (worknet_govt_jobs_api_key) | ✅ 활성 |
| `isolation_policy_service.py` | 고립군 군집(1~4) → 서비스 매트릭스 필터 → 정책 추천 + DIDIM 서비스 허브 오케스트레이션 | ✅ 활성 |
| `cluster_service_matrix.py` | DIDIM 전체 서비스 카탈로그 + 군집별 활성/비활성 결정 매트릭스 (하드코딩, LLM 불관여) | ✅ 활성 |
| `llm_isolation_service.py` | 군집별 DIDIM 서비스 활성/비활성 이유를 GPT-4o-mini로 설명 생성 (결정은 matrix 담당) | ✅ 활성 |
| `youth_center_service.py` | 온통청년 OPEN API — 청년정책(F-26)·청년공간(F-27)·청년콘텐츠(F-28) 조회 + 대분류 카테고리 분류 | ✅ 활성 |
| `hrd_extended_service.py` | Work24 확장 훈련과정 — 일학습병행(F-29, 313L01)·국가인적자원개발컨소시엄(F-30, 312L01)·구직자취업역량강화(F-31, 키 발급완료/엔드포인트 승인대기) | ✅ 활성 |
| `job_crawling_service.py` | 국내 대기업 10개 채용공고 직접 크롤링 (Saramin API 승인 대기 중) — 캐시 TTL 2시간, 키워드 기반 자격증 매칭 | ✅ 활성 |
| `llm_cert_relevance_service.py` | 자격증 × 희망 직무 도메인 연관성 LLM 분석 — GPT-4o-mini JSON mode, 캐시 TTL 7일, fallback 포함 | ✅ 활성 |

> **llm_roadmap_service.py 추가 함수 (2026-07-01)**:  
> - `get_support_programs_for_risk(risk_stage_id)` — support_program_master.csv × support_program_risk_stage_mapping.csv 기반 지원 제도 반환 (카테고리별 그룹핑)

---

## 3. 데이터 체인 원칙

`cert_id` 기반 외부 API 호출은 반드시 `cert_lookup_service`를 경유한다.

```
cert_id
  ↓ cert_master.csv
cert_name, cert_grade_tier, avg_pass_rate_3yr
  ↓ cert_ncs_mapping.csv
ncs_id 목록
  ↓ ncs_master.csv
대직무코드, 대직무분류 (빈도 기반 우선순위)
  ↓ NCS_TO_WORKNET_OCCUPATION
WorkNet occupation 코드 (jobs_service에 전달)
  ↓ Work24 srchNcs1 2자리 코드
Work24 훈련과정 검색 (training_service에 전달)
```

---

## 4. 담지 않는 것

- API 라우트 핸들러 → `backend/app/api/v1/routes/`
- 데이터 스키마 정의 → `backend/app/schemas/`
- DB 접근 직접 → `backend/app/repositories/`
- CSV 원본 파일 → `data/raw/` 또는 `data/processed/`

---

## 5. Audit Findings (by Gemini CLI) — 2026-04-17

- **✅ Resolved (2026-04-18)**: `_domain_job_match` 함수를 `(domain_match OR job_match)` 명확한 OR 조건으로 리팩토링
- **✅ Resolved (2026-04-18)**: 정렬 키 `(stage_order, level_score, -pass_rate)` 확정, 단조 증가 검증 완료
- **✅ Resolved (2026-04-18)**: `is_bottleneck` 플래그 + `bottleneck_note` 텍스트 (pass_rate < 10%)
- **✅ Resolved (2026-04-18)**: `held_cert_ids` 동적 진입점 + 보유 자격증 결과 제외 구현
- **✅ Resolved (2026-05-14)**: `cert_lookup_service` NCS 우선순위 버그 — Counter 기반 빈도 분석으로 수정 (정보처리기사: 20 정보통신 정상 반환)
- **Deferred**: `risk_stage_id`에 따른 추천 가중치 고도화 — policy 확정 전 reserved
- **Blocked (data)**: `cert_to_cert_relation.csv` 생성 전까지 DAG 완전 순회 불가
