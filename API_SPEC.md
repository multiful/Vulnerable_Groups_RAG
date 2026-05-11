# API_SPEC.md

> **파일명**: API_SPEC.md  
> **최종 수정일**: 2026-05-12  
> **문서 해시**: SHA256:TBD
> **문서 역할**: API 계약, request/response, 오류 형식 정의 문서  
> **문서 우선순위**: 6  
> **연관 문서**: FEATURE_SPEC.md, DATA_SCHEMA.md, SYSTEM_ARCHITECTURE.md, PRD.md  
> **참조 규칙**: endpoint, request/response 형식, status code, 오류 응답 구조를 변경할 때 먼저 이 문서를 수정한다.

---

## 1. 문서 목적

이 문서는 프론트엔드와 백엔드 간의 **API 계약**을 정의한다.  
기능을 어떤 endpoint로 노출할지, 각 endpoint가 어떤 입력을 받고 어떤 출력을 반환하는지, 실패 시 어떤 오류 형식을 따르는지를 고정하는 것이 목적이다.

이 문서는 다음을 정의한다.

- API 버전과 공통 규칙
- endpoint 목록
- request / response 구조
- 공통 오류 형식
- status code 기준
- reserved endpoint

이 문서는 다음을 직접 정의하지 않는다.

- 제품 문제 정의와 기능 우선순위
- 시스템 내부 계층 구조
- DB 컬럼과 canonical schema 상세
- 프롬프트 내용
- retrieval 내부 튜닝 방식

위 항목은 각각 `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `DATA_SCHEMA.md`, `PROMPT_DESIGN.md`, `RAG_PIPELINE.md`에서 담당한다.

---

## 2. API 설계 원칙

### 2.1 버전 고정
현재 API는 `/api/v1`를 기준으로 한다.

### 2.2 계약 우선
프론트는 API 응답 형식을 직접 추론하지 않고, 이 문서에 정의된 response envelope를 기준으로 구현한다.

### 2.3 구조적 추천과 설명 근거 분리
추천 결과와 설명 근거는 같은 화면 흐름에서 결합될 수 있지만, 내부적으로는 다른 계층에서 만들어진다.  
API 계약은 이 두 결과를 명시적으로 구분할 수 있어야 한다.

### 2.4 taxonomy 밖 값 금지
API 응답의 `related_domains`, `related_jobs`, `primary_domain`은 사전 정의된 taxonomy 값만 반환해야 한다.

### 2.5 reserved 기능 명시
일정/접수/링크 endpoint는 현재 reserved 상태이며, 활성화 전까지는 계약만 유지한다.

---

## 3. 공통 규칙

### 3.1 Base URL
```text
/api/v1
```

### 3.2 Content-Type
```text
application/json
```

### 3.3 시간 형식
- 날짜: `YYYY-MM-DD`
- 시각: ISO 8601 권장

### 3.4 ID 원칙
대표 ID 예시는 아래와 같다.

- `risk_stage_id`
- `roadmap_stage_id`
- `cert_id`
- `candidate_id`
- `doc_id`
- `chunk_id`

---

## 4. 공통 Response Envelope

모든 API는 아래 구조를 기본으로 사용한다.

```json
{
  "success": true,
  "data": {},
  "meta": {
    "request_id": "req_001",
    "version": "v1"
  },
  "error": null
}
```

### 필드 설명
- `success`: 요청 성공 여부
- `data`: 실제 응답 payload
- `meta`: 요청 메타데이터
- `error`: 실패 시 오류 객체, 성공 시 `null`

---

## 5. 공통 Error Envelope

오류 발생 시 아래 구조를 사용한다.

```json
{
  "success": false,
  "data": null,
  "meta": {
    "request_id": "req_001",
    "version": "v1"
  },
  "error": {
    "code": "INVALID_INPUT",
    "message": "risk_stage_id가 허용 범위를 벗어났습니다.",
    "details": {
      "field": "risk_stage_id"
    }
  }
}
```

### 공통 오류 코드
- `INVALID_INPUT`
- `MISSING_REQUIRED_FIELD`
- `NOT_FOUND`
- `TAXONOMY_MAPPING_FAILED`
- `NO_CANDIDATE_FOUND`
- `RETRIEVAL_EMPTY`
- `INTERNAL_ERROR`
- `NOT_IMPLEMENTED`

---

## 6. Endpoint 목록

| 기능 ID | Method | Endpoint | 상태 | 용도 |
|---|---|---|---|---|
| - | GET | `/health` | 활성 | 서버 상태 확인 |
| F-01/F-02/F-03 | POST | `/recommendations` | 스텁(준비만) | 추천 후보 조회 — 계약·예시는 갖춤, 런타임 실행은 후속 |
| F-04 | POST | `/recommendations/evidence` | 활성 | 설명 근거 조회 |
| F-05 | POST | `/roadmaps` | 활성 | 로드맵 조회 |
| F-06 | POST | `/admin/canonicalize` | 활성 | canonicalization 실행 |
| F-07 | POST | `/admin/candidates/rebuild` | 활성 | candidate 재생성 |
| F-07 | GET | `/admin/validation` | 활성 | validation 결과 조회 |
| F-08 | GET | `/schedules/exams/{cert_id}` | reserved | 시험 일정 조회 |
| F-09 | GET | `/schedules/applications/{cert_id}` | reserved | 접수 일정 조회 |
| F-09 | GET | `/links/support/{cert_id}` | reserved | 지원 링크 조회 |
| F-11 | GET | `/certs/{cert_id}/videos` | 활성 | 관련 YouTube 동영상 조회 |

---

## 7. 활성 Endpoint 상세

## 7.1 GET /health

### 목적
서버 상태 확인

### Request
없음

### Response 예시
```json
{
  "success": true,
  "data": {
    "status": "ok"
  },
  "meta": {
    "request_id": "req_health_001",
    "version": "v1"
  },
  "error": null
}
```

---

## 7.2 POST /recommendations

### 목적
위험군 단계와 관심 직무/도메인 입력을 바탕으로 추천 후보를 반환한다.

### Request Body
```json
{
  "risk_stage_id": "risk_stage_1",
  "interested_jobs": ["데이터 분석"],
  "interested_domains": ["데이터/AI"],
  "query_text": "데이터 분석 쪽으로 갈 때 도움이 되는 자격증 추천"
}
```

### Request 필드
| 필드명 | 필수 | 타입 | 설명 |
|---|---:|---|---|
| `risk_stage_id` | Y | string | 위험군 식별자 |
| `interested_jobs` | N | array[string] | 관심 직무 배열 |
| `interested_domains` | N | array[string] | 관심 도메인 배열 |
| `query_text` | N | string | 자유 텍스트 입력 |

### 처리 규칙
- `risk_stage_id`는 필수다.
- 자유 텍스트가 있더라도 내부적으로 taxonomy 정규화 결과를 우선 사용한다.
- 추천 결과가 0건이어도 시스템 오류와 구분해야 한다.

### 준비(실행 전 고정 사항)

- 현재 단계에서는 **실행하지 않는다**(`NOT_IMPLEMENTED`). 응답 계약·요청 필드는 본 절과 `FEATURE_SPEC.md`를 기준으로 유지한다.
- **후속 실행** 시 후보 소스는 canonical 저장소 또는 `DATA_SCHEMA.md` §9.1 형식의 **JSONL** 등으로 정한다. 산출물 형식 참고: `data/canonical/candidates/candidates.jsonl.example`.
- 요청 `interested_*`·행 데이터는 `data/taxonomy/` 허용 라벨과 맞출 것(`DATA_SCHEMA.md` taxonomy 제약).

### Response Body 예시
```json
{
  "success": true,
  "data": {
    "request_context": {
      "risk_stage_id": "risk_stage_1",
      "normalized_jobs": ["데이터 분석"],
      "normalized_domains": ["데이터/AI"]
    },
    "candidates": [
      {
        "candidate_id": "cand_cert_013",
        "cert_id": "cert_013",
        "cert_name": "정보처리기사",
        "primary_domain": "데이터/AI",
        "related_jobs": ["데이터 분석", "백엔드 개발"],
        "related_domains": ["데이터/AI", "소프트웨어개발"],
        "roadmap_stages": ["기초", "실무"],
        "summary": "데이터/AI 및 소프트웨어개발 영역으로 연결되는 대표 자격증입니다."
      }
    ]
  },
  "meta": {
    "request_id": "req_rec_001",
    "version": "v1"
  },
  "error": null
}
```

### 주요 오류
- `INVALID_INPUT`
- `TAXONOMY_MAPPING_FAILED`
- `NO_CANDIDATE_FOUND`

---

## 7.3 POST /recommendations/evidence

### 목적
추천 후보에 대한 설명 근거를 PDF / HTML 문서에서 검색한다.

### Request Body
```json
{
  "cert_id": "cert_013",
  "risk_stage_id": "risk_stage_1",
  "related_domains": ["데이터/AI"],
  "related_jobs": ["데이터 분석"]
}
```

### Request 필드
| 필드명 | 필수 | 타입 | 설명 |
|---|---:|---|---|
| `cert_id` | Y | string | 자격증 식별자 |
| `risk_stage_id` | N | string | 위험군 식별자 |
| `related_domains` | N | array[string] | 관련 도메인 배열 |
| `related_jobs` | N | array[string] | 관련 직무 배열 |

### Response Body 예시
```json
{
  "success": true,
  "data": {
    "cert_id": "cert_013",
    "evidence": [
      {
        "doc_id": "doc_001",
        "chunk_id": "chunk_001",
        "source_type": "pdf",
        "snippet": "정보처리기사는 정보 시스템 구축과 소프트웨어 개발 역량을 검증하는 국가기술자격이다.",
        "section_path": ["자격 개요"],
        "source_url": null
      }
    ]
  },
  "meta": {
    "request_id": "req_evd_001",
    "version": "v1"
  },
  "error": null
}
```

### 주요 오류
- `MISSING_REQUIRED_FIELD`
- `RETRIEVAL_EMPTY`
- `NOT_FOUND`

### 인제스트·메타데이터 전제 (준비)

벡터 스토어에 적재된 각 청크의 `metadata`(JSONB)에 **요청 `cert_id`와 동일한 키 `cert_id`** 가 포함되어 있어야, 현행 구현의 메타 필터(`@>`)로 검색된다.  
JSONL·인제스트 계약은 `DATA_SCHEMA.md` §10, `RAG_PIPELINE.md` §16.2, `data/index_ready/chunks/chunks.jsonl.example`를 본다.

---

## 7.4 POST /roadmaps

### 목적
위험군 단계와 추천 맥락을 바탕으로 로드맵 결과를 생성한다.

### Request Body
```json
{
  "risk_stage_id": "risk_stage_1",
  "cert_id": "cert_013",
  "related_domains": ["데이터/AI"],
  "related_jobs": ["데이터 분석"]
}
```

### Request 필드
| 필드명 | 필수 | 타입 | 설명 |
|---|---:|---|---|
| `risk_stage_id` | Y | string | 위험군 식별자 |
| `cert_id` | N | string | 자격증 식별자 |
| `related_domains` | N | array[string] | 관련 도메인 배열 |
| `related_jobs` | N | array[string] | 관련 직무 배열 |

### Response Body 예시
```json
{
  "success": true,
  "data": {
    "risk_stage_id": "risk_stage_1",
    "roadmap": [
      {
        "roadmap_stage_id": "roadmap_stage_01",
        "roadmap_stage_name": "기초",
        "description": "기본 개념과 직무 연관성을 이해하는 단계입니다.",
        "related_cert_ids": ["cert_013"]
      },
      {
        "roadmap_stage_id": "roadmap_stage_02",
        "roadmap_stage_name": "실무",
        "description": "실무 적용 가능성을 높이는 단계입니다.",
        "related_cert_ids": ["cert_013"]
      }
    ]
  },
  "meta": {
    "request_id": "req_roadmap_001",
    "version": "v1"
  },
  "error": null
}
```

### 주요 오류
- `INVALID_INPUT`
- `NOT_FOUND`

---

## 7.5 POST /admin/canonicalize

### 목적
CSV canonicalization 배치를 실행한다.

### Request Body 예시
```json
{
  "dataset_types": ["cert_master", "cert_alias", "cert_domain_mapping"],
  "run_validation": true
}
```

### Request 필드
| 필드명 | 필수 | 타입 | 설명 |
|---|---:|---|---|
| `dataset_types` | N | array[string] | 실행 대상 dataset 목록 |
| `run_validation` | N | boolean | validation 동시 실행 여부 |

### Response Body 예시
```json
{
  "success": true,
  "data": {
    "job_id": "job_canon_001",
    "status": "started"
  },
  "meta": {
    "request_id": "req_admin_001",
    "version": "v1"
  },
  "error": null
}
```

### 주요 오류
- `INVALID_INPUT`
- `NOT_IMPLEMENTED`
- `INTERNAL_ERROR`

---

## 7.6 POST /admin/candidates/rebuild

### 목적
entity / relation 결과를 기준으로 recommendation candidate row를 재생성한다.

### Request Body 예시
```json
{
  "rebuild_all": true
}
```

### Request 필드
| 필드명 | 필수 | 타입 | 설명 |
|---|---:|---|---|
| `rebuild_all` | N | boolean | 전체 재생성 여부 |

### Response Body 예시
```json
{
  "success": true,
  "data": {
    "job_id": "job_candidate_001",
    "status": "started"
  },
  "meta": {
    "request_id": "req_admin_002",
    "version": "v1"
  },
  "error": null
}
```

---

## 7.7 GET /admin/validation

### 목적
최근 validation 결과를 조회한다.

### Query Parameters
| 필드명 | 필수 | 타입 | 설명 |
|---|---:|---|---|
| `dataset_type` | N | string | dataset 유형 필터 |
| `status` | N | string | 검증 상태 필터 |

### Response Body 예시
```json
{
  "success": true,
  "data": {
    "reports": [
      {
        "dataset_type": "cert_master",
        "check_name": "taxonomy_validation",
        "severity": "error",
        "row_count": 3,
        "status": "failed"
      }
    ]
  },
  "meta": {
    "request_id": "req_admin_003",
    "version": "v1"
  },
  "error": null
}
```

---

## 7.8 GET /certs/{cert_id}/videos

### 목적
자격증명 기반으로 YouTube 강의·인강·합격 영상을 최대 5개 반환한다. (F-11)

### Path Parameters
| 필드명 | 필수 | 타입 | 설명 |
|---|---:|---|---|
| `cert_id` | Y | string | 자격증 식별자 |

### Query Parameters
없음

### 처리 규칙
- 서버는 Supabase `cert_video_cache` 테이블을 먼저 조회한다.
- `fetched_at`이 30일 이내면 캐시 결과를 반환하고 외부 호출을 생략한다.
- 캐시 미스/만료 시에만 YouTube Data API v3 `search.list`를 호출한다.
- 추천 핵심 흐름과 분리된 부가 endpoint이므로 본 호출 실패가 다른 API에 영향을 주지 않는다.

### Response Body 예시
```json
{
  "success": true,
  "data": {
    "cert_id": "cert_0123",
    "cert_name": "정보처리기사",
    "videos": [
      {
        "video_id": "abc123XYZ",
        "title": "정보처리기사 필기 합격 강의",
        "channel": "코딩채널",
        "thumbnail_url": "https://i.ytimg.com/vi/abc123XYZ/mqdefault.jpg",
        "url": "https://www.youtube.com/watch?v=abc123XYZ"
      }
    ],
    "cache_hit": true,
    "fetched_at": "2026-05-12T01:00:00Z"
  },
  "meta": {
    "request_id": "req_videos_001",
    "version": "v1"
  },
  "error": null
}
```

### 주요 오류
| Status | code | 의미 |
|---|---|---|
| 404 | `CERT_NOT_FOUND` | `cert_id`가 candidates에 없음 |
| 500 | `YOUTUBE_API_KEY_MISSING` | 서버에 YouTube API 키 미설정 |
| 502 | `YOUTUBE_QUOTA_EXCEEDED` | YouTube 일일 quota 초과 (캐시도 없음) |
| 503 | `YOUTUBE_TIMEOUT` | YouTube API 호출 시간 초과 |

### 빈 결과
검색 결과가 0건이어도 200 OK로 응답하며, `data.videos = []`로 반환한다. (오류 아님)

---

## 8. reserved Endpoint

## 8.1 GET /schedules/exams/{cert_id}
시험 일정 조회  
현재 상태: reserved

## 8.2 GET /schedules/applications/{cert_id}
접수 일정 조회  
현재 상태: reserved

## 8.3 GET /links/support/{cert_id}
지원 링크 조회  
현재 상태: reserved

### reserved 처리 원칙
- 현재는 `NOT_IMPLEMENTED` 응답을 반환할 수 있다.
- API 실연동 이후 활성화한다.

---

## 9. Status Code 기준

| Status Code | 의미 |
|---|---|
| 200 | 정상 처리 |
| 400 | 입력 오류 |
| 404 | 대상 없음 |
| 422 | 형식 검증 실패 |
| 500 | 내부 오류 |
| 501 | reserved / 미구현 기능 |

---

## 10. 인증/권한

현재 MVP 범위에서는 인증/권한을 필수로 가정하지 않는다.  
단, 관리자 배치 endpoint는 추후 인증 계층 추가를 전제로 한다.

현재 문서 기준:
- 일반 추천 endpoint → 인증 없음
- 관리자 endpoint → 내부/제한 환경 전제
- 인증 설계는 후속 문서에서 확정

---

## 11. API 버전 관리 원칙

1. breaking change가 생기면 버전을 올린다.
2. 응답 필드 추가는 backward compatible 방식으로 수행한다.
3. 필드 제거는 버전 업 없이 수행하지 않는다.
4. reserved endpoint가 활성화될 때는 이 문서를 먼저 갱신한다.

---

## 12. 후속 문서 연결

- 기능 기준 → `FEATURE_SPEC.md`
- 데이터 구조 기준 → `DATA_SCHEMA.md`
- 시스템 흐름 → `SYSTEM_ARCHITECTURE.md`
- 프롬프트 설계 → `PROMPT_DESIGN.md`

---

## 13. 최종 요약

이 문서는 프론트엔드와 백엔드 사이의 API 계약을 정의한다.  
현재 활성 API는 추천, 설명 근거, 로드맵, canonicalization, candidate rebuild, validation 조회이며, 일정/링크 API는 reserved 상태다.

즉, 현재 API 중심은 아래 두 가지다.

1. **추천/로드맵 사용자 흐름 제공**
2. **canonical data 갱신 및 점검 지원**
