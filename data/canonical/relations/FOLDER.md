# FOLDER.md

> **파일명**: FOLDER.md  
> **폴더 경로**: `data/canonical/relations`  
> **최종 수정일**: 2026-04-19 (R4 완료: N2 eval runner + R4-3 is_bottleneck tier-relative + R4-6 job_to_domain 런타임; R5 대상: N1/N4/N5 + P15 tier 필터)  
> **문서 해시**: SHA256:TBD  
> **문서 역할**: 디렉터리 스캐폴드 명시서 — 담는 내용·금지·다음 단계 연계  
> **문서 우선순위**: reference (충돌 시 루트 기준 문서 우선)  
> **연관 문서**: DIRECTORY_SPEC.md, DATA_SCHEMA.md, MASTER_MERGE_PLAN.md, SYSTEM_ARCHITECTURE.md  

> **참조 규칙**: 파일이 추가·제거될 때 본 파일과 `MASTER_MERGE_PLAN.md §9`를 같은 작업에서 갱신한다.

---

[![Sylveon](https://img.pokemondb.net/sprites/sword-shield/normal/sylveon.png)](https://pokemondb.net/pokedex/sylveon)

## 1. 용도

엔티티 간 **관계(Relation) canonical 산출물**을 둔다. 추천 그래프·후보 생성의 직접 입력이 된다.

---

## 2. 파일 목록 (현황)

| 파일 | 행 수 | 상태 | 생성 스크립트 |
|---|---|---|---|
| `cert_domain_mapping.csv` | 1,290 | ✅ | `scripts/build_cert_domain_mapping.py` |
| `domain_adjacency.csv` | 18 | ✅ 교차 도메인 확장 규칙 (IT/의료/관광/디자인/금융/기계/환경 8클러스터) | 수동 작성; `scripts/build_frontend_data.py`가 runtime 로드 |
| `cert_to_roadmap_stage.csv` | 1,290 | ✅ | `scripts/build_all_relations.py` |
| `cert_prerequisite.csv` | 775 | ✅ cross-domain 이슈 해소 (subject_prefix 그룹, prefix+suffix union-find) | `scripts/build_cert_prerequisite.py` |
| `cert_ncs_mapping.csv` | 3,573 | ✅ cert 57.6% / ncs 95.0% | `scripts/build_all_relations.py` |
| `cert_job_mapping.csv` | 4,900+ | ✅ cert 100% / job 100% — 2026-05-20 보강 (소방/섬유/공예/광업/조리/법률/반려동물 등) | `scripts/supplement_data.py` |
| `cert_major_mapping.csv` | 10,000+ | ✅ 전체 1,287개 자격증 커버리지 달성 — 2026-05-20 도메인 기반 보충 | `scripts/supplement_data.py` |
| `major_to_domain.csv` | 5,268 | ✅ | — |
| `job_to_domain.csv` | 151 | ✅ job 100% / domain 42/43 | `scripts/build_all_relations.py` |
| `risk_stage_to_roadmap_stage.csv` | 5 | ✅ | `scripts/build_all_relations.py` |
| `cert_to_cert_relation.csv` | 999 (active 775 / inactive 224) | ✅ A1 recommended_prior 복원 + N6 방향 guard 적용 | `scripts/build_cert_to_cert_relation.py` |
| ~~`risk_stage_to_domain.csv`~~ | — | ❌ 삭제 — domain은 사용자 관심사로 결정 | — |

> 상세 생성 규칙·매핑 테이블은 `MASTER_MERGE_PLAN.md` 참조.

---

## 3. 담지 않는 것

- 원본 CSV 직접 복사본 → `data/raw/csv/`
- candidate row → `data/canonical/candidates/`
- 임베딩 벡터 파일

## 4. 산출·연계

`data/canonical/relations` → `data/canonical/candidates` → 추천 엔진 입력

---

## 5. 비고

- 각 파일의 스키마·의미는 `DATA_SCHEMA.md §6` 참조.
- 대용량 산출물은 Git 정책(`.gitignore`)과 `HASH_INCREMENTAL_BUILD_GUIDE.md` 증분 원칙을 따른다.

### 5.1 다음 진행 계획 (as of 2026-04-19)

**R2 완료 요약 (2026-04-18 ~ 2026-04-19):**
- P1 ✅ 다운스트림 증분 소비 hook (`reload_from_changed_jsonl`, `iter_changed_candidates`)
- P2 ✅ `cert_paths` 점수화(`_path_score`) + 전역 desc 정렬
- P3 ✅ `_effective_domain()` — `primary_domain` fallback
- P4 ✅ `cert_to_cert_relation` merge(parse_ir + NCS, `confidence` 컬럼). parse_ir 단독 행은 is_active=False 처리
- P5 ✅ `verified_ids.txt` 검증 우선순위 헤더 갱신
- P6 ✅ 위험군별 차등 (TIER/PASSRATE → risk_stages + `_RISK_TIER_MIN`)
- ✅ 골든셋 P21 (risk_0005 + domain_0005 = 전기/전자) 추가

**R3 완료 요약 (2026-04-19):**
- A1 ✅ `_RELATION_TYPE_MAP` 제거 — `recommended_prior → next_step` 오매핑 수정. 재빌드 후 `relation_type=recommended_prior: 666행` 복원 확인.
- N6 ✅ `_TIER_ORDER` 기반 방향 guard 추가 — `build_cert_to_cert_relation.py` 에 `swapped=8, dropped=19` 보고 확인.
- N3 ✅ A1 수정으로 자동 해소 — `recommended_prior` 커버리지 666행, `prerequisite` 109행으로 정상화.

**R4 완료 요약 (2026-04-19):**
- R4-1 ✅ N2 골든셋 자동 평가 runner — `scripts/eval_golden_set.py` 작성. P01~P21 6 persona 검증. PASS RATE 100%(P21), 전체 95.7%. MANUAL 0건.
- R4-3 ✅ `is_bottleneck` tier-relative — `_BOTTLENECK_TIER_THRESHOLD` 상수 추가(기능사 20%/산업기사 15%/기사 10%/기술사·기능장 5%). P21 is_bottleneck=0건 유지 확인.
- R4-6 ✅ `job_to_domain.csv` 런타임 통합 — `_load_job_to_domain_map()` + `recommendations()` job-only 확장 로직 추가. domain_ids 빈 경우만 확장.
- P21 baseline ✅ `golden_set.jsonl` expected_cert_ids 갱신 — A1 수정 후 top-10 기능사 10개로 변경 반영.

---

### 5.2 다음 라운드 (N1 ~ N6) — 구체 실행사항

| 우선순위 | 항목 | 정의 | 기대 산출물 | 상태 |
|---|---|---|---|---|
| **N1** | `parse_ir` reasoning_evidence 추출기 재설계 | 현재 로직은 키워드 근접성 검사 없이 한 블록 내 등장하는 모든 cert 이름을 인접쌍으로 연결 → 노이즈 높음. `_extract_parse_ir_evidence` 를 (a) 키워드 window ±80자 내 cert 이름 2개 이상, (b) cert 이름 간 거리 ≤50자, (c) 블록 전체 cert 이름 10개 이상이면 단순 나열 무효, (d) 관계 키워드 직전/직후 cert만 from/to 추정 — 으로 재설계. 수작업 샘플 20건 타당성 확인 후 is_active=True 승격. | parse_ir 행 50건 내외 + evidence 문장 실제 근거로 읽히는 상태 | ⬜ 미착수 |
| **N2** | 골든셋 자동 평가 runner | `docs/evaluation/golden_set.jsonl` 의 `evaluation_criteria` 를 코드로 검증하는 runner 작성. 각 persona 에 대해 `recommendations(input_query)` 호출 → (a) `starting_roadmap_stage` 일치, (b) `fallback_used` 일치, (c) `roadmap_sequence` 상위 N개가 `expected_roadmap_cert_ids` 와 Jaccard≥0.6, (d) `cert_paths` 의 start→end 패턴 포함 여부. | `scripts/eval_golden_set.py` + pytest 통합. 통과율 리포트 stdout. | ✅ R4-1 구현 완료 (2026-04-19). PASS 44/46, P21 100%. |
| **N3** | `recommended_prior` / `prerequisite` 커버리지 | `_RELATION_TYPE_MAP` 이 `recommended_prior → next_step` 으로 오매핑하던 버그 (A1). | `relation_type=recommended_prior: 666행`, `prerequisite: 109행` 복원 | ✅ A1 수정으로 해소 (2026-04-19) |
| **N4** | `cert_candidates` taxonomy 미매핑 78건 대책 | `primary_domain=domain_unknown` 으로 taxonomy 게이트에서 탈락 중인 78개 cert (language/속기 등 domain_0028 계열 주류). (a) `cert_domain_mapping.csv` 에 수동 매핑 행 추가, 또는 (b) `DATA_SCHEMA §9.1.2` 정책에 `taxonomy_fallback` 조항 신설해 제한적으로 `primary_domain=domain_0028` 등 카테고리 자체를 허용. | taxonomy 게이트 통과 candidate ≥ 1350 (현재 1290). 78건 정리 계획 로그. | ⬜ 미착수 |
| **N5** | `roadmap_by_stage` 단계 누락 완화 | 골든셋 P21 (risk_0005+domain_0005) 에서 `roadmap_stage_0001`·`_0002` 는 0 certs. `_cert_level` 에 pass_rate 보조 입력 써서 기능사 중 쉬운 자격(pass_rate ≥60%)은 stage_0002 로 내리는 세분화 정책 검토, 또는 roadmap_stage 정의에 "비자격 준비 과정" 포함. | risk_0005 로드맵에 stage_0001/0002 안내 문구 (또는 자격증) 1개 이상. | ⬜ 미착수 |
| **N6** | `cert_to_cert_relation` 역방향 검증 guard | `from_cert_id` 가 항상 하위(선행) 여야 함. `build_cert_to_cert_relation.py` 에 `_TIER_ORDER` 기반 방향 검증 추가 — `_TIER_ORDER(from) > _TIER_ORDER(to)` 인 행은 자동 swap, 동일 tier는 drop. | 빌드 로그에 `swapped=8, dropped=19` 리포트 확인. | ✅ 구현 완료 (2026-04-19) |

---

### 5.3 현재 확인된 데이터 품질 이슈

- **cert_to_cert_relation.csv parse_ir 행**: N1 대상. 현재 is_active=False 차단 (224행). `_extract_parse_ir_evidence` 재설계 전까지는 NCS 775행만 그래프에 반영. N6 guard 추가로 향후 복귀 시 역방향 혼입 방지됨 ✅.
- **recommended_prior 오매핑**: ✅ A1 수정으로 해소 (2026-04-19). `relation_type=recommended_prior: 666행` 정상 복원. `cert_paths` path_score 상위 0.94~0.95 범위 확인.
- **primary_domain=domain_unknown 78건**: N4 대상. 현재 taxonomy 게이트에서 제외.
- **roadmap_stage_0001/0002 공백**: N5 대상. 위험군 5 사용자에게 "취업 바로 전 단계" 안내 없음.
- **stage_0005 진입 후 하위 tier 노출 (P15 FAIL)**: 보유 자격 기반 advanced entry(stage_0005) 시 다른 domain의 기능사·산업기사·기사가 stage_0005 clamped로 여전히 노출됨. `is_redundant`는 동일 domain 내만 적용하므로 cross-domain 하위 tier 미필터. R5 대상 — `_build_roadmap_sequence` 에 `starting_order` 기반 tier 하한 필터 추가 검토.

---

### P6. 위험군별 차등 추천 정책 구현

**목적**: risk_0001(취업 안정권)과 risk_0005(최고 위험군) 사용자에게 실질적으로 다른 자격증 로드맵이 추천되도록 한다.

**현재 구조 및 문제:**
- `risk_stage_to_roadmap_stage.csv`로 진입 roadmap_stage만 결정 (risk_0001→stage_0003, risk_0005→stage_0001)
- `cert_candidates.jsonl` 미생성으로 `recommended_risk_stages` 필드가 비어 있음
- `starting_order` 미만 cert는 clamp만 하고 필터아웃하지 않아 risk_0001에도 기능사가 노출될 수 있음

---

#### P6-1. `recommended_risk_stages` 생성 정책 (`build_cert_candidates.py` 반영)

**기술자격 (cert_grade_tier 존재):**

| cert_grade_tier | recommended_risk_stages |
|---|---|
| `1_기능사` | `[risk_0003, risk_0004, risk_0005]` |
| `2_산업기사` | `[risk_0002, risk_0003, risk_0004, risk_0005]` |
| `3_기사` | `[risk_0001, risk_0002, risk_0003, risk_0004]` |
| `4_기술사` | `[risk_0001, risk_0002]` |
| `5_기능장` | `[risk_0001, risk_0002]` |

**비기술자격 (cert_grade_tier 없음, 합격률 기반):**

| avg_pass_rate_3yr | recommended_risk_stages |
|---|---|
| ≥50% | `[risk_0003, risk_0004, risk_0005]` |
| 30–50% | `[risk_0002, risk_0003, risk_0004]` |
| 10–30% | `[risk_0001, risk_0002, risk_0003]` |
| <10% | `[risk_0001, risk_0002]` |
| 합격률 없음 | keyword fallback 또는 기본값 `[risk_0002, risk_0003, risk_0004]` |

- 구현 위치: `scripts/build_cert_candidates.py` Phase 4 candidate row 생성 시
- 검증: risk_0001 필터 결과 집합 ≠ risk_0005 필터 결과 집합인지 diff 확인

---

#### P6-2. `_filter_candidates` tier_min 보강 (`recommendation_service.py`)

fallback 케이스(risk 제약 해제)에서도 risk_0001에 기능사가 주요 추천에 포함되지 않도록 tier 하한 필터 추가.

```python
# recommendation_service.py 추가 상수
_RISK_TIER_MIN: dict[str, int] = {
    "risk_0001": 20,  # 산업기사(20) 이상만 — 기능사(10) 제외
    "risk_0002": 15,  # 기능사 상위 이상
    "risk_0003": 10,  # 기능사 이상 전체
    "risk_0004": 10,
    "risk_0005": 10,  # 기능사부터 전체
}
```

- `_filter_candidates` fallback 분기에 `tier_min` 적용: tier가 있고 score < tier_min인 cert 제외
- 비기술자격(tier 없음)은 tier_min 적용 대상에서 제외하여 기존 pass_rate 기반 로직 유지
- 기존 `is_redundant` 로직과 중복 없음 — `is_redundant`는 보유 자격 기반, tier_min은 위험군 기반

---

#### P6-3. 전자공학 도메인 risk_0005 로드맵 예시

**입력**: `domain = 전기/전자 (domain_0005)`, `risk_stage = risk_0005`

| step | roadmap_stage | 자격증 | cert_grade_tier | 합격률 | 비고 |
|---|---|---|---|---|---|
| 1 | Stage 2 탐색 시작 | 전자기기기능사 | 1_기능사 | ~45% | 전자 분야 진입 최소 자격 |
| 2 | Stage 2 탐색 시작 | 전기기능사 | 1_기능사 | ~38% | 전기 기반, 실무 현장 진입 |
| 3 | Stage 3 역량 준비 | 전자기기산업기사 | 2_산업기사 | ~35% | prerequisite: 전자기기기능사 |
| 4 | Stage 3 역량 준비 | 전기산업기사 | 2_산업기사 | ~33% | prerequisite: 전기기능사 |
| 5 | Stage 4 실행 확대 | 전자기기기사 | 3_기사 | ~25% | 취업 핵심 자격 |
| 6 | Stage 4 실행 확대 | 전기기사 | 3_기사 | ~18% | ⚠️ bottleneck (합격률 <30%) — 반복 응시 고려 |
| 7 | Stage 5 유지·정착 | 전자응용기술사 | 4_기술사 | ~10% | prerequisite: 전자기기기사 + 실무 경험 4년 |

**DAG 경로 (cert_prerequisite.csv 기반):**
```
전자기기기능사 → 전자기기산업기사 → 전자기기기사 → 전자응용기술사
전기기능사 → 전기산업기사 → 전기기사
```

**risk_0001 동일 도메인 비교 (취업 안정권):**

| step | roadmap_stage | 자격증 | 비고 |
|---|---|---|---|
| 1 | Stage 3 역량 준비 (시작점) | 전자기기산업기사 | 기능사 불필요, tier_min=20으로 기능사 제외 |
| 2 | Stage 4 실행 확대 | 전자기기기사, 전기기사 | 고급 자격 직행 |
| 3 | Stage 5 유지·정착 | 전자응용기술사 | 전문화 |

**차이 요약:**
- risk_0005: 기능사부터 전 단계 이수, 총 7단계, achievability = near_term/long_term 혼합
- risk_0001: 산업기사 이상만 추천, 총 3단계, achievability = immediate/near_term
- 진입점 단계: risk_0005는 roadmap_stage_0001, risk_0001은 roadmap_stage_0003

---

#### P6-4. 구현 순서 — 상태

1. ✅ P6-1: `build_cert_candidates.py` `TIER_TO_RISK_STAGES` + `PASSRATE_TO_RISK_STAGES` 도입. Phase 4 실행 완료 → `cert_candidates.jsonl` 1201행 갱신.
2. ✅ P6-2: `recommendation_service._RISK_TIER_MIN` 상수 + `_tier_min_allows()`. `_filter_candidates` 의 direct/fallback 양쪽에 적용.
3. ✅ P6-3 검증 실행: risk_0001+domain_0005 → 기능사 0건, 기사 13 + 기술사 7 + 기능장 2. risk_0005+domain_0005 → 기능사 10 + 산업기사 11. 차등 확인.
4. ⬜ golden_set.jsonl 확장 — C-3 평가셋 커버리지 강화는 별도 라운드(추천 정책 검증 이후).

---

## 6. 미기재 파일 보충

| 파일 | 행 수 | 상태 | 비고 |
|---|---|---|---|
| `verified_ids.txt` | 37 | ✅ | 랜덤서치 검증 누적 목록(헤더 포함). 완료 ID 0건 — 재검증 재개 필요. |

---

## 7. 라운드 완료 이력 및 다음 라운드 (R5)

### R4 완료 (2026-04-19)

| 항목 | 상태 | 결과 |
|---|---|---|
| R4-1 N2 eval runner | ✅ 완료 | `scripts/eval_golden_set.py`. PASS 44/46 → P21 갱신 후 100%. |
| R4-3 is_bottleneck tier-relative | ✅ 완료 | `_BOTTLENECK_TIER_THRESHOLD` 상수. 기능사 20%/기사 10%/기술사 5%. P21 회귀 없음. |
| R4-6 job_to_domain 런타임 통합 | ✅ 완료 | `_load_job_to_domain_map()` + job-only 확장. job_0001 → domain_0001, total_certs=10 확인. |
| R4-2 N1 parse_ir 재설계 | ⏭ R5로 이동 | 현재 is_active=False 안전망 있음. |
| R4-4 N4 taxonomy 78건 | ⏭ R5로 이동 | candidate 커버리지 이슈, 기능 차단 아님. |
| R4-5 N5 stage_0001/0002 공백 | ⏭ R5로 이동 | 서비스 품질 이슈, 기능 차단 아님. |

---

### R5 우선순위 실행 계획

> R4 완료 상태 기준 (2026-04-19). 미착수 잔여: N1·N4·N5 + P15 tier 필터.

| 순위 | 항목 | 작업 위치 | 기대 효과 | 병목 여부 |
|---|---|---|---|---|
| **R5-1** | **P15 tier 필터** — stage_0005 진입 후 하위 tier 노출 | `recommendation_service._build_roadmap_sequence` — `starting_order`가 높을 때 `tier_min` 동적 상향 | eval P15 FAIL 해소 (기술사·기능장만 노출) | 🔴 eval FAIL — 회귀 감지됨 |
| **R5-2** | **N1** `parse_ir` 추출기 재설계 | `build_cert_to_cert_relation.py:_extract_parse_ir_evidence` — 키워드 window ±80자, cert 간 거리 ≤50자, 10개 이상 나열 무효 | parse_ir 행 50건 내외 is_active=True 승격 → cert_paths 품질 향상 | 🟡 N6 guard 있어 복귀 안전 |
| **R5-3** | **N4** taxonomy 미매핑 78건 | `cert_domain_mapping.csv` 수동 보강 또는 `DATA_SCHEMA §9.1.2` `taxonomy_fallback` 신설 | candidate 커버리지 +6% (1290 → 1350+) | 🟡 domain_0028 언어·속기 계열 주류 |
| **R5-4** | **N5** roadmap_stage_0001/0002 공백 | `_cert_level` 세분화 — pass_rate ≥60% 기능사 → stage_0002 | risk_0005 입문 단계 안내 | 🟢 서비스 품질 개선 |

### R5 착수 전 확인 사항

- R5-1: `_build_roadmap_sequence`에서 `starting_order` 기준 tier 하한 동적 계산 시 `_TIER_SCORE` 역방향 매핑 필요 (stage → 최소 tier_score).
- R5-2: `data/index_ready/parse_ir/*.json` 실제 블록 샘플 확인 필수 (heuristic 직접 작성 전).
- R5-3: `DATA_SCHEMA.md §6` 및 `DIRECTORY_SPEC.md` 신규 파일 추가 충돌 여부 확인.
- `python scripts/eval_golden_set.py` 로 R5 변경 전 baseline 재캡처 후 작업할 것.