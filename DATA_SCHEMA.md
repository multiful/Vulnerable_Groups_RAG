# DATA_SCHEMA.md

> **파일명**: DATA_SCHEMA.md  
> **최종 수정일**: 2026-05-12  
> **문서 해시**: SHA256:TBD
> **문서 역할**: 데이터 구조, 엔티티, 관계, 공통 필드, 제약조건 정의 문서  
> **문서 우선순위**: 5  
> **연관 문서**: PRD.md, SYSTEM_ARCHITECTURE.md, FEATURE_SPEC.md, API_SPEC.md, RAG_PIPELINE.md  
> **참조 규칙**: 데이터 구조, canonical schema, 엔티티/관계, 필수 필드, enum, 제약조건을 변경할 때 먼저 이 문서를 수정한다.

---

## 1. 문서 목적

이 문서는 시스템의 **데이터 구조 기준선**을 정의한다.  
주요 엔티티, 관계, recommendation candidate row, 문서형 chunk, validation 결과, reserved 일정/링크 필드 구조를 문서화하여, 기능 구현과 API 설계가 같은 데이터 기준을 사용하도록 하는 것이 목적이다.

이 문서는 다음을 정의한다.

- 핵심 엔티티
- 핵심 관계
- canonical entity / relation 구조
- recommendation candidate row 구조
- 문서형 chunk 구조
- validation 구조
- enum 허용값
- 필수/선택/nullable 기준
- reserved 필드

이 문서는 다음을 직접 정의하지 않는다.

- 제품 문제 정의와 기능 우선순위
- 시스템 계층 구조
- API endpoint 상세 계약
- retrieval 튜닝 전략
- 평가 기준과 실험 절차
- 프롬프트 세부 문구

위 항목은 각각 `PRD.md`, `SYSTEM_ARCHITECTURE.md`, `API_SPEC.md`, `RAG_PIPELINE.md`, `EVALUATION_GUIDELINE.md`, `PROMPT_DESIGN.md`에서 담당한다.

---

## 2. 데이터 설계 원칙

### 2.1 source_type 분리
데이터는 source_type에 따라 다른 구조로 다뤄진다.

- PDF / HTML → 문서형 지식 데이터
- CSV → structured no-parse canonical data
- API → 후속 최신성 데이터

### 2.2 canonical 중심 설계
추천의 구조적 기반은 canonical data를 중심으로 설계한다.

- 원본 CSV를 그대로 recommendation 입력으로 사용하지 않는다.
- canonical entity / relation / candidate row를 생성해 사용한다.

### 2.3 taxonomy 제한
다음 필드는 자유 텍스트를 허용하지 않는다.

- `related_domains`
- `related_jobs`
- `primary_domain`

### 2.4 ID 우선 설계
표시용 이름보다 안정적인 식별자를 우선 사용한다.

- row 간 연결은 이름보다 ID를 기준으로 수행한다.
- 이름은 표시용 또는 검색 보조용으로 사용한다.

### 2.5 reserved 필드 허용
현재 스프린트 범위 밖이지만 추후 API 병합을 위해 일정/링크 관련 필드를 reserved 상태로 유지할 수 있다.

---

## 3. 공통 타입 및 표기 규칙

### 3.1 날짜 형식
- `YYYY-MM-DD`

### 3.2 boolean 필드
- `true` / `false`

### 3.3 배열 필드
문서에서는 배열로 표기하되, 실제 저장 방식은 구현체에 따라 아래 중 하나를 사용한다.
- JSON 배열
- join table
- serialized field

구현체가 달라도 의미는 동일해야 한다.

### 3.4 quality_flags
`quality_flags`는 배열 또는 key-value 구조를 허용한다.  
구현체는 아래 둘 중 하나를 택할 수 있다.

- 문자열 배열
- JSON object

### 3.5 null 허용 원칙
다음 경우 null을 허용할 수 있다.

- 후속 스프린트 reserved 필드
- source_type 특성상 존재하지 않는 필드
- evidence/문서 provenance의 선택 메타 필드

### 3.6 ID 포맷(패딩) 규칙
식별자 컬럼은 타입 구분이 가능한 접두사 + 0패딩 숫자 형식을 권장한다.

- 권장 형식: `<prefix>_<4자리 이상 0패딩 번호>`
- 예시:
  - `domain_sub_label_id`: `domain_0001`
  - `job_role_id`: `job_0001`
  - `risk_stage_id`: `risk_0001`
  - `roadmap_stage_id`: `roadmap_0001`
  - `major_id`: `major_0001`
  - `cert_id`: `cert_0001` (외부 코드 기반일 경우 `cert_qnet_0011` 같은 혼합형 허용)

운영 원칙:
- 한 번 발급한 ID는 재번호하지 않는다.
- 표시 순서가 필요하면 별도 `*_order` 또는 `*_seq` 컬럼을 사용한다.
- 조인은 표시명보다 ID를 우선한다.

### 3.7 normalized_key 생성 규칙
`normalized_key`는 조인/중복 제거용 보조 키로, 아래 규칙으로 생성한다.

1. 소문자 변환 (`A-Z` -> `a-z`)
2. 좌우 공백 제거
3. 공백/하이픈/슬래시/점/특수기호를 `_`로 치환
4. 연속된 `_`는 하나로 축약
5. 시작/끝 `_` 제거

예시:
- `AI 서비스 기획` -> `ai_서비스_기획`
- `UI/UX 디자인` -> `ui_ux_디자인`
- `가스ㆍ수도ㆍ전기 계기 검침원 및 안전점검원` -> `가스_수도_전기_계기_검침원_및_안전점검원`
- `보험·금융-리스크` -> `보험_금융_리스크`

운영 원칙:
- `normalized_key`는 원문(`*_name`)을 대체하지 않는다.
- 충돌 가능성이 있으면 ID 조인을 우선하고 `normalized_key`는 보조 매칭에만 사용한다.

---

## 4. enum 허용값

### 4.1 source_type
허용값:
- `pdf`
- `html`
- `csv`
- `api`

### 4.2 entity_type
예시 허용값:
- `certificate`
- `domain_sub_label`
- `job_sub_label`
- `risk_stage`
- `roadmap_stage`
- `source_document`

### 4.3 relation_type
허용값:
- `cert_to_domain`
- `cert_to_job`
- `cert_to_roadmap_stage`
- `cert_prerequisite`
- `risk_stage_to_roadmap_stage`
- `major_to_job`
- `job_to_domain`
- `cert_to_hosting_org`
- `major_to_domain`
- `cert_to_ncs`

> `risk_stage_to_domain`: ❌ 삭제됨 (2026-04-15) — §6.4 참조

### 4.7 cert_grade_tier
자격증 등급 계층 허용값 (낮은 숫자 = 진입 난이도 낮음):
- `1_기능사`
- `2_산업기사`
- `3_기사`
- `4_기술사`
- `5_기능장`
- `null` — 등급 계층 미분류(비기술사격, 민간자격 등)

### 4.4 row_type
현재 허용값:
- `certificate_candidate`

### 4.5 validation severity
허용값:
- `info`
- `warning`
- `error`

### 4.6 validation status
허용값:
- `passed`
- `failed`
- `skipped`

---

## 5. 핵심 엔티티

## 5.1 RiskStage

위험군 단계 엔티티

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `risk_stage_id` | string | Y | N | 위험군 고유 식별자 |
| `risk_stage_name` | string | Y | N | 표시용 단계명 |
| `risk_stage_order` | integer | Y | N | 단계 순서 |
| `description` | string | N | Y | 단계 설명 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- `risk_stage_id`는 유일해야 한다.
- 현재 허용 범위는 1단계 ~ 5단계다.
- `risk_stage_order`는 1~5의 정수다.

---

## 5.2 RoadmapStage

로드맵 단계 엔티티

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `roadmap_stage_id` | string | Y | N | 로드맵 단계 식별자 |
| `roadmap_stage_name` | string | Y | N | 표시용 단계명 |
| `stage_order` | integer | Y | N | 단계 순서 |
| `description` | string | N | Y | 단계 설명 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- `roadmap_stage_id`는 유일해야 한다.
- `stage_order`는 정수형으로 관리한다.

---

## 5.3 Certificate

자격증 엔티티

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `cert_id` | string | Y | N | 자격증 식별자 |
| `cert_name` | string | Y | N | 표시용 자격증명 |
| `canonical_name` | string | Y | N | 대표 정규명 |
| `normalized_key` | string | Y | N | 정규화 키 |
| `aliases` | array[string] | N | Y | alias 목록 |
| `issuer` | string | N | Y | 발급/주관 기관명 (표시용, cert_to_hosting_org 생성 전까지 대체) |
| `cert_type` | string | N | Y | 자격증 유형 (국가기술자격/국가전문자격/국가민간자격) |
| `grade_name` | string | N | Y | 원본 등급명 (Q-Net 원문 유지) |
| `cert_grade_tier` | enum/string | N | Y | 자격증 등급 계층 (§4.7 허용값) |
| `primary_domain` | string | N | Y | Q-Net 원본 도메인 코드 (cert_domain_mapping과 별도) |
| `top_domain` | string | N | Y | 9개 대분류 중 하나 |
| `domain_name_raw` | string | N | Y | Q-Net 원본 54개 소분류 값 (빈값 578개 허용) |
| `written_avg_pass_rate` | number | N | Y | 필기 평균 합격률 |
| `practical_avg_pass_rate` | number | N | Y | 실기 평균 합격률 |
| `avg_pass_rate_3yr` | number | N | Y | 최근 3년 평균 합격률 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- `cert_id`는 유일해야 한다.
- `canonical_name`은 추천 표시에 사용할 대표 이름이다.
- `normalized_key`는 중복 제거와 canonicalization 기준에 사용한다.
- `cert_grade_tier`는 §4.7 허용값만 사용한다. 등급 미분류인 경우 null을 허용한다.

---

## 5.4 DomainSubLabel

도메인 세부 라벨 엔티티

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `domain_sub_label_id` | string | Y | N | 도메인 세부 라벨 식별자 |
| `domain_sub_label_name` | string | Y | N | 세부 라벨명 |
| `domain_top_label_name` | string | Y | N | 상위 도메인명 |
| `normalized_key` | string | Y | N | 정규화 키 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- 허용 값은 domain taxonomy 기준만 사용한다.
- 세부 라벨은 상위 라벨에 매핑 가능해야 한다.

---

## 5.5 JobSubLabel

직무 세부 라벨 엔티티

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `job_role_id` | string | Y | N | 직무 식별자 |
| `job_role_name` | string | Y | N | 세부 직무명 |
| `job_top_group_name` | string | Y | N | 상위 직무 그룹명 |
| `normalized_key` | string | Y | N | 정규화 키 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- 허용 값은 희망 직무 taxonomy 기준만 사용한다.
- 자유 텍스트 직무명을 저장하지 않는다.

---

## 5.6 SourceDocument

문서형 지식 엔티티(PDF / HTML 중심)

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `doc_id` | string | Y | N | 문서 식별자 |
| `source_type` | enum | Y | N | `pdf`, `html`, `csv`, `api` |
| `doc_type` | string | Y | N | 문서 분류 |
| `title` | string | N | Y | 문서 제목 |
| `source_url` | string | N | Y | 원문 URL |
| `agency` | string | N | Y | 기관명 |
| `doc_version` | string | N | Y | 문서 버전 |
| `valid_from` | string(date) | N | Y | 유효 시작일 |
| `valid_to` | string(date) | N | Y | 유효 종료일 |
| `freshness_level` | string | N | Y | 신선도 레벨 |
| `exact_sensitivity` | string | N | Y | exact match 민감도 |
| `file_hash` | string | N | Y | 원본 바이트 해시(동일 파일 재파싱 스킵 등 증분 키; 계산 규칙은 `HASH_INCREMENTAL_BUILD_GUIDE.md`) |
| `fetched_at` | string(datetime) | N | Y | 수집 시각(HTTP/HTML 등에서 사용 가능할 때) |

### 제약
- `source_type`은 정의된 enum만 허용한다.
- 현재 문서형 지식 엔티티는 주로 `pdf`, `html`에 사용한다.
- Parse 단계 **블록 단위 IR**의 필드 계약은 `RAG_PIPELINE.md` §6.7이 정의하고, 본 엔티티는 문서·출처 단위 카탈로그에 집중한다.

---

## 5.7 Major

전공 마스터(`major_master.csv`)를 canonical 레이어에서 관리하기 위한 엔티티다.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `major_id` | string | Y | N | 전공 식별자 |
| `major_name` | string | Y | N | 전공명 |
| `normalized_key` | string | Y | N | 전공 정규화 키 |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- `major_id`는 유일해야 한다.
- `major_name`은 원천 표기를 유지하되, 조인은 `normalized_key` 또는 `major_id`를 우선 사용한다.
- 도메인 연결은 `major_master.csv` 컬럼이 아니라 `major_domain_mapping.csv`에서 관리한다.

---

## 6. 핵심 관계

## 6.1 cert_to_domain

자격증과 도메인 세부 라벨의 관계

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 |
| `cert_id` | string | Y | N | 자격증 식별자 |
| `domain_sub_label_id` | string | Y | N | 도메인 세부 라벨 식별자 |
| `is_primary` | boolean | Y | N | domain_name_raw 직접 매핑 여부 (True=원본 기반, False=keyword/fallback) |
| `weight` | number | N | Y | 관계 가중치 |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- 하나의 자격증은 여러 도메인 세부 라벨과 연결될 수 있다.
- 최소 1개의 primary domain을 도출할 수 있어야 한다.
- `is_primary=True`: cert_master.domain_name_raw 직접 매핑 (712개)
- `is_primary=False`: keyword 규칙 또는 top_domain fallback (578개)

---

## 6.2 cert_to_job

자격증과 직무 세부 라벨의 관계

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 |
| `cert_id` | string | Y | N | 자격증 식별자 |
| `job_role_id` | string | Y | N | 직무 식별자 |
| `weight` | number | N | Y | 관계 가중치 |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- 허용된 희망 직무 taxonomy 범위 안의 값만 사용한다.

---

## 6.3 cert_to_roadmap_stage

자격증과 로드맵 단계의 관계

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 |
| `cert_id` | string | Y | N | 자격증 식별자 |
| `roadmap_stage_id` | string | Y | N | 로드맵 단계 식별자 |
| `weight` | number | N | Y | 관계 가중치 |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `is_active` | boolean | Y | N | 활성 여부 |

---

## 6.4 risk_stage_to_domain

> **상태**: ❌ 삭제됨 (2026-04-15)  
> risk_stage는 로드맵 시작점(§6.5)만 결정한다. 도메인 선택은 사용자 관심사(job/domain 입력)로 결정하며, risk_stage가 domain을 결정하는 관계는 설계 근거가 없다. 생성 파일 및 스크립트 로직 폐기. (MASTER_MERGE_PLAN §2.3·§8 참조)

---

## 6.5 risk_stage_to_roadmap_stage

위험군과 로드맵 단계의 관계

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 |
| `risk_stage_id` | string | Y | N | 위험군 식별자 |
| `roadmap_stage_id` | string | Y | N | 로드맵 단계 식별자 |
| `weight` | number | N | Y | 관계 가중치 |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `is_active` | boolean | Y | N | 활성 여부 |

---

## 6.6 major_to_job

전공과 직무 세부 라벨의 관계

> **상태**: defer — 현재 신뢰할 만한 소스 없음. `major_to_domain`(§6.10)과 `job_to_domain`(§6.7)의 역방향으로 간접 대체 가능.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 |
| `major_id` | string | Y | N | 전공 식별자 |
| `job_role_id` | string | Y | N | 직무 식별자 |
| `weight` | number | N | Y | 관계 가중치 |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- `major_id`는 `major_master.csv`에 존재해야 한다.
- `job_role_id`는 `job_master.csv`에 존재해야 한다.

---

## 6.7 job_to_domain

직무 세부 라벨과 도메인 세부 라벨의 관계

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 |
| `job_role_id` | string | Y | N | 직무 식별자 |
| `domain_sub_label_id` | string | Y | N | 도메인 세부 라벨 식별자 |
| `weight` | number | N | Y | 관계 가중치 |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- `job_role_id`는 `job_master.csv`에 존재해야 한다.
- `domain_sub_label_id`는 `domain_master.csv`에 존재해야 한다.

---

## 6.8 cert_prerequisite

자격증 선행/후속 관계 — `cert_id` 는 상위(advanced), `prerequisite_cert_id` 는 하위(prior) 자격증.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 (`prereq_00001` 형식) |
| `cert_id` | string | Y | N | 기준(상위) 자격증 식별자 |
| `prerequisite_cert_id` | string | Y | N | 선행(하위) 자격증 식별자 |
| `relation_kind` | string | Y | N | `prerequisite` / `recommended_prior` |
| `domain_name_raw` | string | Y | N | cert_master 기준 원본 도메인 라벨 (그룹 기준) |
| `subject_prefix` | string | Y | N | cert_name 에서 grade 접미사 제거한 과목 키. 접미어 `*` 는 prefix/suffix 병합 그룹을 의미 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- `cert_id`, `prerequisite_cert_id`는 `cert_master.csv`에 존재해야 한다.
- 두 자격증의 `cert_master.domain_name_raw` 는 동일해야 한다 (cross-domain 연결 금지).
- `subject_prefix` 는 `cert_name` 에서 `(기능사|산업기사|기능장|기술사|기사)$` 패턴 제거로 산출한다. 여러 과목이 prefix/suffix 포함관계로 묶인 경우 루트(가장 짧은 과목)에 `*` 를 덧붙여 표시한다.
- 허용 tier 전이: (1_기능사→2_산업기사|3_기사), (2_산업기사→3_기사), (3_기사→4_기술사|5_기능장) — MASTER_MERGE_PLAN §5 참조.

### 생성 스크립트
- `scripts/build_cert_prerequisite.py`

---

## 6.8.1 cert_to_cert_relation

`cert_prerequisite.csv` (NCS 공식 체계) 와 `parse_ir/` 텍스트 증거를 병합한 **추천 그래프용 통합 관계 테이블**이다. `cert_paths` 생성과 DAG 순회의 입력이다.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 (`c2c_00001` 형식) |
| `from_cert_id` | string | Y | N | 선행(하위) 자격증 식별자 |
| `to_cert_id` | string | Y | N | 상위/후속 자격증 식별자 |
| `relation_type` | enum/string | Y | N | `prerequisite` / `recommended_prior` / `next_step` |
| `reasoning_evidence` | string | Y | N | 자연어 근거 문장 (parse_ir 원문 또는 "NCS 공식 자격 체계 기준") |
| `source` | string | Y | N | `cert_prerequisite`, `parse_ir:<doc>`, 또는 병합 시 `parse_ir\|cert_prerequisite` |
| `confidence` | number | Y | N | 0.80 (parse_ir 단독) / 1.00 (NCS 단독 또는 양측 확인) |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약 및 병합 규칙 (§P4)
- 동일 (`from_cert_id`, `to_cert_id`) pair 는 1행으로 병합한다.
- 두 소스 모두에 존재하는 경우:
  - `relation_type` 은 강한 타입 우선 (`prerequisite` > `recommended_prior` > `next_step`).
  - `source` 는 `parse_ir|cert_prerequisite` 형식으로 합본.
  - `reasoning_evidence` 는 parse_ir 원문을 유지 (구체성 우선).
  - `confidence` = 1.00.
- `_path_score` (recommendation_service) 는 `relation_type` 가중치 + 길이 페널티 + pass_rate 가산으로 계산한다.

### 생성 스크립트
- `scripts/build_cert_to_cert_relation.py`

---

## 6.9 cert_to_hosting_org

자격증과 주관기관 관계

> **상태**: defer — `cert_master.issuer` 컬럼으로 현재 단계 대체 가능. 별도 파일 생성 시 아래 스키마 사용.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 |
| `cert_id` | string | Y | N | 자격증 식별자 |
| `hosting_org_id` | string | Y | N | 주관기관 식별자 (`hosting_org_master.csv` 기준) |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- `cert_id`는 `cert_master.csv`에 존재해야 한다.
- `hosting_org_id`는 `hosting_org_master.csv`에 존재해야 한다.

---

## 6.10 major_to_domain

전공과 도메인 세부 라벨의 관계

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 |
| `major_id` | string | Y | N | 전공 식별자 |
| `domain_sub_label_id` | string | Y | N | 도메인 세부 라벨 식별자 |
| `weight` | number | N | Y | 관계 가중치 |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- `major_id`는 `major_master.csv`에 존재해야 한다.
- `domain_sub_label_id`는 `domain_master.csv`에 존재해야 한다.

---

## 6.11 cert_to_ncs

자격증과 NCS 소직무의 관계

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_id` | string | Y | N | 관계 식별자 |
| `cert_id` | string | Y | N | 자격증 식별자 |
| `ncs_id` | string | Y | N | NCS 소직무 식별자 (`ncs_master.csv` 기준) |
| `source_id` | string | N | Y | 원천 소스 식별자 (ncs_mapping_rows 기준) |
| `is_active` | boolean | Y | N | 활성 여부 |

### 제약
- `cert_id`는 `cert_master.csv`에 존재해야 한다.
- `ncs_id`는 `ncs_master.csv`에 존재해야 한다.
- 하나의 자격증은 여러 NCS 소직무와 연결될 수 있다.
- join 기준: `ncs_mapping_rows`의 대직무코드 + 중직무코드 + 소직무코드 → `ncs_master.ncsID`
- 현재 커버리지: cert 743/1,290 (57.6%), ncs 248/261 (95.0%)

---

## 6.12 cert_video_cache (Supabase 캐시)

자격증별 YouTube 영상 검색 결과 캐시 (F-11). canonical relation은 아니지만 운영용 부속 테이블로 본 문서에서 함께 정의한다.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `cert_id` | string (PK) | Y | N | 자격증 식별자 (candidates의 `cert_id`와 동일) |
| `cert_name` | string | Y | N | 호출 시점의 자격증명 (디버깅용 기록) |
| `search_query` | string | Y | N | 실제 호출한 검색 쿼리 (OR 조합 결과) |
| `videos` | jsonb | Y | N | 영상 리스트. 각 요소는 `{video_id, title, channel, thumbnail_url, url}` |
| `query_version` | int | Y | N | 검색 쿼리 구성 정책 버전 (기본 1). 정책 변경 시 증가 → 캐시 무효화 |
| `fetched_at` | timestamptz | Y | N | 외부 API 호출 시각. TTL 비교 기준 |
| `quota_exceeded_at` | timestamptz | N | Y | 마지막 quota 초과 발생 시각 (운영 모니터링용) |

### 제약
- `cert_id`는 PK. 자격증당 1행 유지 (upsert).
- `videos` 최대 5개 (F-11 정책).
- TTL: `fetched_at + interval '30 days' < now()` 인 경우 캐시 만료로 간주, 재호출 후 upsert.
- `query_version`이 application 코드의 현재 버전과 다르면 캐시 미스로 취급.
- 본 테이블은 candidates / canonical relation 빌드에 영향을 주지 않는다. 부속 운영 데이터로만 사용.

### Supabase DDL
`docs/architecture/supabase_cert_video_cache.sql` 참고.

---

## 7. canonical entity table 구조

canonical entity table은 정규화된 엔티티를 저장하는 공통 구조다.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `entity_type` | enum/string | Y | N | 엔티티 타입 |
| `entity_id` | string | Y | N | 엔티티 식별자 |
| `canonical_name` | string | Y | N | 대표 이름 |
| `normalized_key` | string | Y | N | 정규화 키 |
| `aliases` | array[string] | N | Y | alias 목록 |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `source_row_no` | integer | N | Y | 원천 row 번호 |
| `canonical_fields_json` | object | N | Y | 타입별 추가 속성 |
| `quality_flags` | array/object | N | Y | 품질 플래그 |
| `updated_at` | string(datetime) | Y | N | 갱신 시각 |
| `content_hash` | string | N | Y | 내용 해시 |

### `entity_type` 허용 값 예시
- `certificate`
- `domain_sub_label`
- `job_sub_label`
- `major`
- `risk_stage`
- `roadmap_stage`

### 원칙
- 원본 CSV 컬럼을 그대로 저장하는 것이 아니라 정규화된 대표 필드를 저장한다.
- `canonical_fields_json`에는 타입별 추가 속성을 담을 수 있다.

---

## 8. canonical relation table 구조

canonical relation table은 정규화된 관계를 저장하는 공통 구조다.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `relation_type` | enum/string | Y | N | 관계 타입 |
| `src_entity_type` | enum/string | Y | N | 출발 엔티티 타입 |
| `src_entity_id` | string | Y | N | 출발 엔티티 식별자 |
| `dst_entity_type` | enum/string | Y | N | 도착 엔티티 타입 |
| `dst_entity_id` | string | Y | N | 도착 엔티티 식별자 |
| `weight` | number | N | Y | 관계 가중치 |
| `source_id` | string | N | Y | 원천 소스 식별자 |
| `source_row_no` | integer | N | Y | 원천 row 번호 |
| `quality_flags` | array/object | N | Y | 품질 플래그 |
| `updated_at` | string(datetime) | Y | N | 갱신 시각 |

### `relation_type` 허용 값 (§4.3과 동일)
- `cert_to_domain`
- `cert_to_job`
- `cert_to_roadmap_stage`
- `cert_prerequisite`
- `risk_stage_to_roadmap_stage`
- `major_to_job`
- `job_to_domain`
- `cert_to_hosting_org`
- `major_to_domain`
- `cert_to_ncs`

---

## 9. recommendation candidate row 구조

recommendation candidate row는 recommendation core의 기본 검색 단위다.

## 9.1 certificate_candidate_row

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `row_type` | enum/string | Y | N | 현재 `certificate_candidate` |
| `candidate_id` | string | Y | N | 추천 row 식별자 |
| `cert_id` | string | Y | N | 자격증 식별자 |
| `cert_name` | string | Y | N | 표시용 자격증명 |
| `aliases` | array[string] | N | Y | alias 목록 |
| `issuer` | string | N | Y | 기관명 |
| `primary_domain` | string | Y | N | 대표 도메인 세부 라벨 |
| `related_domains` | array[string] | Y | N | 관련 도메인 배열 |
| `related_jobs` | array[string] | N | Y | 관련 직무 배열 |
| `recommended_risk_stages` | array[string] | N | Y | 연결 위험군 배열 |
| `roadmap_stages` | array[string] | N | Y | 연결 로드맵 단계 배열 |
| `text_for_dense` | string | Y | N | 의미 요약 텍스트 |
| `text_for_sparse` | string | N | Y | exact 보강 텍스트 |
| `valid_from` | string(date) | N | Y | 유효 시작일 |
| `valid_to` | string(date) | N | Y | 유효 종료일 |
| `source_ids` | array[string] | N | Y | 관련 원천 소스 목록 |
| `quality_flags` | array/object | N | Y | 품질 플래그 |
| `updated_at` | string(datetime) | Y | N | 갱신 시각 |
| `content_hash` | string | N | Y | 내용 해시 |

### 제약
- `cert_id`, `cert_name`, `primary_domain`, `related_domains`, `text_for_dense`는 필수다.
- `primary_domain`은 도메인 taxonomy 세부 라벨만 허용한다.
- `related_domains`는 최소 1개 이상이어야 한다.
- `related_jobs`는 비어 있을 수 있으나, 추천 품질상 가능한 한 채운다.
- `text_for_sparse`는 optional이며 exact miss 대응 시 활성화한다.
- reserved 일정 필드는 현재 row 기본 필드에 포함하지 않는다.

### 9.1.2 `recommended_risk_stages` 생성 정책 (§P6-1)
- **기술자격** (`cert_grade_tier` 존재): `data/canonical/relations/FOLDER.md §P6-1 표 1` tier→risk 매핑 고정.
- **비기술자격** (`cert_grade_tier` 빈값): `avg_pass_rate_3yr` 기반 구간 매핑 (`≥50%`, `30~50%`, `10~30%`, `<10%`) — FOLDER.md §P6-1 표 2.
- **합격률도 tier도 없는 경우**: 기본값 `[risk_0002, risk_0003, risk_0004]`.
- 위 정책은 `scripts/build_cert_candidates.py` 의 `_risk_stages_for()` 에 구현되어 있으며, 변경 시 본 절과 FOLDER.md 를 동시 갱신한다.

### 9.1.1 build-time taxonomy 게이트 (ID 기반)
`primary_domain` / `related_domains` / `related_jobs` 값은 **런타임 소스 오브 트루스인 master CSV의 ID**와 반드시 일치해야 한다.

- `primary_domain` / `related_domains` ∈ `data/processed/master/domain_master.csv`의 `domain_sub_label_id` 집합
- `related_jobs` ∈ `data/processed/master/job_master.csv`의 `job_role_id` 집합
- 위 집합 밖의 값(`domain_unknown` 같은 placeholder 포함)은 **candidate row로 저장하지 않는다**. §18.5 원칙대로 해당 row를 스킵하고 validation report에 기록한다.
- 빌드 스크립트(`scripts/build_cert_candidates.py`)는 JSONL/CSV 출력 전에 이 게이트를 통과시킨다. 위반이 있으면 기본 동작은 **실패(raise)** 이며, 명시적 `--allow-violations` 플래그로만 우회 가능하다.
- validation 결과는 `data/canonical/validation/candidates_taxonomy.json`에 저장한다(필드: §12 validation row 스키마).
- 이 게이트 덕분에 런타임 추천 서비스는 JSONL을 신뢰하며 별도 taxonomy 검증을 수행하지 않는다.

> taxonomy 라벨의 **사람이 읽는 이름 정의**는 `data/taxonomy/domain_v2.txt`, `data/taxonomy/prefer_job.txt`에 유지한다. 이 텍스트 파일은 master CSV의 상위 정의 소스이며, 런타임 검증에는 사용하지 않는다.

---

## 10. 문서형 chunk 구조

PDF / HTML 지식 검색용 chunk 구조다.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `doc_id` | string | Y | N | 문서 식별자 |
| `chunk_id` | string | Y | N | 청크 식별자 |
| `source_type` | enum | Y | N | `pdf` / `html` 등 |
| `doc_type` | string | Y | N | 문서 분류 |
| `text` | string | Y | N | 청크 본문 |
| `section_path` | array[string] | N | Y | 섹션 경로 |
| `source_loc` | string/object | N | Y | 원문 위치 |
| `chunk_hash` | string | Y | N | 청크 해시 |
| `valid_from` | string(date) | N | Y | 유효 시작일 |
| `valid_to` | string(date) | N | Y | 유효 종료일 |
| `doc_version` | string | N | Y | 문서 버전 |

### optional 메타 필드
- `cert_id`
- `job_role_id`
- `domain_sub_label`
- `domain_top_label`
- `risk_stage_id`
- `roadmap_stage`
- `agency`

### 현행 런타임 주의 (`cert_id`)

스키마상 `cert_id`는 optional 메타에 속하지만, **현재 구현**의 Evidence 검색(`API_SPEC.md` §7.3, `backend/app/services/retrieval_service.py`)은 벡터 행 `metadata`에 `cert_id`가 있다고 가정하고 필터한다.  
인제스트·JSONL 작성 시 **해당 청크가 귀속될 자격증 ID를 `metadata.cert_id`에 넣는 것을 준비 완료 조건으로 본다.**

### 원칙
- 문서형 chunk는 설명 근거 검색용이다.
- recommendation candidate row와 직접 동일 구조로 취급하지 않는다.

---

## 11. parse quality / provenance 구조

문서형 데이터에는 parse 품질과 provenance 메타를 유지한다.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `has_text_layer` | boolean | N | Y | 텍스트 레이어 존재 여부 |
| `ocr_applied_pages` | array[int] | N | Y | OCR 적용 페이지 |
| `table_assisted_pages` | array[int] | N | Y | table assist 적용 페이지 |
| `reading_order_rebuilt` | boolean | N | Y | reading order 재구성 여부 |
| `fallback_used` | boolean | N | Y | 문서 fallback 사용 여부 |
| `parse_quality_flags` | array/object | N | Y | parse 품질 플래그 |

### 목적
- parse 결과 품질 점검
- provenance 유지
- retrieval 결과 해석 보조

블록 수준 중간 표현(parse IR)의 **최소 필드 계약**은 `RAG_PIPELINE.md` §6.7을 따른다.

---

## 12. validation 구조

canonicalization 및 candidate 생성 과정의 품질 검증 결과를 저장한다.

| 필드명 | 타입 | 필수 | nullable | 설명 |
|---|---|---:|---:|---|
| `dataset_type` | string | Y | N | 대상 dataset 유형 |
| `check_name` | string | Y | N | 검증 항목명 |
| `severity` | enum | Y | N | `info` / `warning` / `error` |
| `row_count` | integer | N | Y | 영향 row 수 |
| `sample_rows` | array/object | N | Y | 샘플 row |
| `status` | enum | Y | N | `passed` / `failed` / `skipped` |
| `generated_at` | string(datetime) | Y | N | 생성 시각 |

### 주요 검증 항목
- PK 누락
- FK 연결 실패
- taxonomy 밖 값
- alias 충돌
- 날짜 역전
- invalid URL
- required field 누락
- 중복 candidate 생성

---

## 13. reserved 일정/링크 필드

현재는 후속 스프린트 범위지만, 추후 API 병합을 위해 아래 필드를 reserved로 유지할 수 있다.

### 일정 관련
- `exam_date`
- `exam_round`
- `apply_start_date`
- `apply_end_date`

### 링크 관련
- `support_url`
- `official_url`
- `apply_url`

### 원칙
- 현재 MVP 단계에서는 이 필드를 null 또는 비활성 상태로 둘 수 있다.
- 필드명을 미리 고정하면 후속 병합이 쉬워진다.

---

## 14. 주요 키 구조

대표 식별자 예시는 아래와 같다.

- `risk_stage_id`
- `roadmap_stage_id`
- `cert_id`
- `domain_sub_label_id`
- `job_role_id`
- `doc_id`
- `chunk_id`
- `candidate_id`
- `relation_id`

### 원칙
- 식별자는 안정적이고 재생성 가능해야 한다.
- row 생성 시 임시 표시용 이름보다 ID를 우선한다.

---

## 15. 데이터 제약 요약

1. CSV는 Parse IR을 만들지 않는다.
2. taxonomy 밖 라벨을 저장하지 않는다.
3. recommendation candidate row는 canonical data를 기반으로 생성한다.
4. 문서형 chunk와 recommendation candidate row는 같은 구조로 다루지 않는다.
5. 일정/링크 필드는 reserved 상태를 허용한다.
6. source_type에 따라 허용되는 필드 조합이 달라질 수 있다.
7. `최종 수정일`이 오래된 문서 기준으로 schema를 임의 변경하지 않는다.

---

## 16. 후속 문서 연결

- 기능별 사용 위치 → `FEATURE_SPEC.md`
- 시스템 흐름 위치 → `SYSTEM_ARCHITECTURE.md`
- API 계약 → `API_SPEC.md`
- retrieval / indexing 세부 → `RAG_PIPELINE.md`

---

## 17. 최종 요약

이 문서는 시스템이 사용하는 핵심 데이터 구조를 정의한다.  
현재 데이터 구조의 중심은 아래 두 가지다.

1. **canonical entity / relation**
2. **recommendation candidate row**

즉, 이 문서는 추천과 검색이 같은 기준 데이터 위에서 동작하도록 만드는 데이터 기준선이다.

---

## 18. 초기 원천 CSV 적재 범위와 한계

본 절은 **참고용으로 제공된 CSV 세트**(학과·통합학과·자격증·직업·NCS 매핑 등)를 **시작 입력**으로 쓸 때, **어떤 스키마 필드를 CSV만으로 채울 수 있는지**와 **반드시 변환·외부 정의가 필요한지**를 구분한다. 원본 CSV는 오염·누락·자유 서술이 있을 수 있으므로, 본 문서의 제약(taxonomy, ID 우선)을 만족시키려면 **canonicalization·검증 파이프라인**이 선행된다.

### 18.1 CSV에서 직접·준직접으로 채울 수 있는 항목

| 스키마 대상 | 주요 필드 | 원천(파일 성격) | 비고 |
|---|---|---|---|
| `Certificate` | `cert_id`, `cert_name`, `canonical_name` 후보 | `data_cert1` (`자격증ID`, `자격증명`) | `canonical_name`·`normalized_key`는 규칙 기반 정규화로 확정 |
| `Certificate` | 분류·등급·시험 구조 등 확장 속성 | `data_cert1` (분류·등급·합격률·시험종류 등) | `canonical_fields_json` 등에 적재 가능 |
| `Certificate` | `issuer` | CSV에 **단일 기관 컬럼이 없음** | `자격증_분류` 등으로 **요약 라벨만** 넣거나 null·별도 마스터로 보강 |
| 관계 `cert_to_*` (중간 키) | `cert_id` + 학과/통합학과 축 | `integrated_major_certificate1` (`integrated_code`, `cert_id`) | 자격증↔통합학과 코드 연결 |
| 통합학과 단위 텍스트·지표 | (엔티티로 둘 경우) 이름·취업률 등 | `integrated_major1` | 제품 taxonomy와 **이름 정합**은 별도 매핑 필요 |
| 세부학과 목록 | `detail_id`, 표시명 | `detail_major1` | `integrated_code` 연결은 `detail_major_integrated1` |
| 직업↔학과↔자격증 (행 단위) | 원천 행 | `data_jobs` | `자격증ID` 누락 행 다수·동일 직업 다행 가능 |
| NCS·직무·학과·자격증 나열 | 원천 행 | `ncs_mapping1` | 한 셀에 **쉼표 구분 다중값** → 파싱·정규화 필수; `자격증ID` 빈 칸 행 존재 가능 |

### 18.2 CSV만으로는 채울 수 없거나, CSV에 없는 항목

| 스키마 대상 | 이유 |
|---|---|
| `RiskStage` 전체, `risk_stage_to_domain`, `risk_stage_to_roadmap_stage` | 제공 CSV에 **위험군(1~5단계)** 정의·가중 관계가 없음. **정책/별도 시드 파일**로 관리 |
| `RoadmapStage` 전체, `cert_to_roadmap_stage` | 로드맵 단계 정의가 CSV에 없음. **별도 시드 또는 규칙** |
| `DomainSubLabel` / `JobSubLabel`의 **taxonomy 준수 ID·상위 라벨** | CSV의 학과명·직업명·NCS 문구는 **자유 텍스트**. `primary_domain`, `related_domains`, `related_jobs`에 넣으려면 **허용 taxonomy 표 → 매핑 테이블**(수동·규칙·검수) 필요 |
| `recommendation candidate` 의 `primary_domain`, `related_domains` | 위 매핑·집계 없이는 **스키마 제약 위반** 또는 품질 플래그 다량 |
| `recommended_risk_stages`, `roadmap_stages` (candidate row) | 원천 CSV에 없음. 정책·시드·추후 규칙으로만 채움 |
| `text_for_dense` / `text_for_sparse` | **생성 필드**. CSV 텍스트를 조합·요약해 채움(파이프라인 산출) |
| `job_info` 기반 풍부 메타 | 직업 설명 등은 **근거 텍스트**로는 유용하나, multiline 필드로 **CSV 파싱 난이도** 높음. 별도 escape 규칙·TSV·JSONL 전환 권장 |

### 18.3 데이터 품질·구현 시 주의 (초기 CSV)

- **ID 일관성**: `자격증ID`는 `data_cert1`·`integrated_major_certificate1`·`data_jobs`·`ncs_mapping1` 간 **조인 키**로 쓰인다. 한쪽에만 있거나 빈 ID인 행은 `quality_flags`·검증(§12) 대상이다.
- **통합학과 코드 `integrated_code`**: `integrated_major_certificate1` ↔ `integrated_major1` ↔ `detail_major_integrated1` ↔ `detail_major1` 체인으로 확장 가능하나, **도메인 taxonomy로의 투영**은 별도 단계다.
- **추천 후보(`certificate_candidate_row`)**: `cert_id`·`cert_name` 등은 CSV에서 모으되, **필수**인 `primary_domain`·`related_domains`는 §2.3을 만족하는 값만 남기고, 매핑 실패 시 **해당 row 생성 스킵 또는 `error` 검증**으로 처리하는 계약을 권장한다.

이 절은 특정 파일명에 고정되지 않으며, 동일 논리 구조의 후속 CSV가 오면 표를 갱신한다.

**팀 실행 절차**: 원본 넣기·전처리·canonical 폴더 반영의 **운영 순서**는 `CSV_CANONICALIZATION_TEAM_GUIDE.md`를 따른다. 본 절(§18)은 **스키마 대비 원천의 들어맞음/부족**을 정의한다.

### 18.4 마스터 CSV 채움 가이드라인 (실무 기준선)

본 절은 `data/raw/csv/*_master.csv`를 채울 때, 어떤 컬럼을 **필수(Required)** 로 채우고 어떤 컬럼을 **권장(Optional)** 으로 채울지 정리한다.  
아래 표의 필수 컬럼은 canonicalization과 ID 조인의 기준선으로 본다.

#### 18.4.1 `cert_master.csv`

| 구분 | 컬럼 | 채움 규칙 |
|---|---|---|
| Required | `cert_id` | 안정 식별자(중복 금지). 원천 코드가 있으면 규칙 기반 생성 |
| Required | `cert_name` | 표시용 원문 자격증명 |
| Required | `canonical_name` | 대표 정규명(동의어 통합) |
| Required | `normalized_key` | 조인/중복 제거용 정규화 키 |
| Required | `is_active` | 기본 `TRUE` (운영 비활성 시 `FALSE`) |
| Optional | `issuer` | 발급/주관 기관 |
| Optional | `aliases` | 별칭 목록(직렬화 문자열 또는 별도 alias 테이블) |
| Optional | `avg_pass_rate` | 필기/실기 평균 합격률(계산 필드) |
| Optional | `avg_receipts` | 필기/실기 평균 응시자 수(계산 필드) |

#### 18.4.2 `domain_master.csv`

| 구분 | 컬럼 | 채움 규칙 |
|---|---|---|
| Required | `domain_sub_label_id` | 세부 도메인 안정 ID(중복 금지) |
| Required | `domain_sub_label_name` | `data/taxonomy/domain_v2.txt` 세부 라벨만 허용 |
| Required | `domain_top_label_name` | 상위 라벨과 일관 매핑 |
| Required | `normalized_key` | 세부 라벨 정규화 키 |
| Required | `is_active` | 기본 `TRUE` |
| Optional | `display_order` | UI/리포트 정렬 순서 |
| Optional | `source_id` | 출처 추적 식별자 |
| Optional | `updated_at` | ISO8601 datetime |

#### 18.4.3 `job_master.csv`

| 구분 | 컬럼 | 채움 규칙 |
|---|---|---|
| Required | `job_role_id` | 세부 직무 안정 ID(중복 금지) |
| Required | `job_role_name` | `data/taxonomy/prefer_job.txt` 세부 직무만 허용 |
| Required | `job_top_group_name` | 상위 직무군과 일관 매핑 |
| Required | `normalized_key` | 세부 직무 정규화 키 |
| Required | `is_active` | 기본 `TRUE` |
| Optional | `display_order` | UI/리포트 정렬 순서 |
| Optional | `source_id` | 출처 추적 식별자 |
| Optional | `updated_at` | ISO8601 datetime |

#### 18.4.4 `major_master.csv`

| 구분 | 컬럼 | 채움 규칙 |
|---|---|---|
| Required | `major_id` | 전공 안정 ID(중복 금지) |
| Required | `major_name` | 전공명(표시용) |
| Required | `normalized_key` | 전공명 정규화 키(신규 생성 권장) |
| Required | `is_active` | 기본 `TRUE` |
| Optional | `domain_sub_label_id` | 도메인 세부 라벨과 연결 가능한 경우 채움 |
| Optional | `source_id` | 출처 추적 식별자 |
| Optional | `updated_at` | ISO8601 datetime |

### 18.5 `data_jobs_rows.csv`를 `job_master.csv`에 활용하는 규칙

`data_jobs_rows.csv`는 품질이 높은 원천이지만, `job_master.csv`를 **직접 대체하는 파일은 아니다**.  
이유는 `job_master`가 taxonomy 고정(`prefer_job.txt`) 기반의 표준 직무 사전이고, `data_jobs_rows.csv`의 `직업명`은 자유 텍스트(동의어/장문/복합명) 성격이기 때문이다.

권장 사용 방식:

1. `job_master.csv`는 taxonomy 세부 직무를 기준으로 먼저 고정한다.  
2. `data_jobs_rows.csv`는 `job_domain_mapping`, `cert_job_mapping`, `job_alias`(또는 동등 매핑 테이블) 생성에 사용한다.  
3. `직업명` 원문은 canonical `job_role_name`으로 직접 저장하지 말고, 매핑/별칭 레이어에서 정규화한다.

즉, `data_jobs_rows.csv`는 **job master 생성의 보강 근거**로는 매우 유용하지만, master의 기준값 자체는 taxonomy를 우선한다.

### 18.6 매핑 CSV 권장 기준 (`data_ingestion` 정렬)

아래 매핑 파일은 구조적 추천 레인에서 우선 관리한다.

| dataset_type(권장 파일명) | 최소 컬럼(Required) | 목적 |
|---|---|---|
| `cert_domain_mapping.csv` | `cert_id`, `domain_sub_label_id`, `source_id`, `is_active` | 자격증-도메인 연결 |
| `cert_job_mapping.csv` | `cert_id`, `job_role_id`, `source_id`, `is_active` | 자격증-직무 연결 |
| `major_job_mapping.csv` | `major_id`, `job_role_id`, `source_id`, `is_active` | 전공-직무 연결 |
| `major_domain_mapping.csv` | `major_id`, `domain_sub_label_id`, `source_id`, `is_active` | 전공-도메인 연결 |
| `job_domain_mapping.csv` | `job_role_id`, `domain_sub_label_id`, `source_id`, `is_active` | 직무-도메인 연결 |
| `job_alias_mapping.csv` | `job_alias_id`, `raw_job_name`, `normalized_key`, `job_role_id`, `match_status`, `source_dataset`, `is_active` | 원천 직무명·별칭 → `job_master` (`alternate_raw_labels`로 동일 키의 표기 변형 보존) |
| `job_row_alias_bridge.csv` | `relation_id`, `source_dataset`, `source_row_id`, `raw_job_name`, `normalized_key`, `job_alias_id` | `job_raw_merged_rows` 등 **행 단위** → alias FK (`job_role_id`는 alias 조인으로만 획득) |
| `domain_risk_roadmap_mapping.csv` | `risk_stage_id`, `domain_sub_label_id`, `roadmap_stage_id`, `source_id`, `is_active` | 위험군-도메인-로드맵 연결 |
| `cert_prerequisite.csv` | `cert_id`, `prerequisite_cert_id`, `relation_kind`, `domain_name_raw`, `subject_prefix`, `is_active` | 선행/후속 자격증 연결 (동일 `domain_name_raw` + `subject_prefix` 병합그룹 내) |
| `cert_hosting_org.csv` | `cert_id`, `issuer`, `source_id`, `is_active` | 자격증-주관기관 연결 |

원칙:
- master csv는 엔티티 기준 사전만 관리하고, 엔티티 간 연결은 매핑 csv에서 관리한다.
- 모든 FK 컬럼은 해당 master(`cert_master`, `domain_master`, `job_master`, `major_master`)의 ID와 연결 가능해야 한다.
- 매핑 파일도 `is_active`를 유지해 soft-delete 운영을 허용한다.
