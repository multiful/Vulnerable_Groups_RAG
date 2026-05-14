# FOLDER.md

> **파일명**: FOLDER.md
> **폴더 경로**: `backend/app/services/`
> **최종 수정일**: 2026-05-14
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
| `retrieval_service.py` | LangChain 기반 RAG Evidence 검색 | ✅ 활성 |
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
