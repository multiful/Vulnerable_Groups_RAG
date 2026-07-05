# DEV_LOG.md

> **파일명**: DEV_LOG.md  
> **최종 수정일**: 2026-07-05  
> **문서 해시**: SHA256:74c3b13d4ae85bc1f010a3f001cebf15698c343ef18cc6a846ab7db6ac855fac
> **문서 역할**: 날짜별 진행 로그, 변경 요약, 해결 이력  
> **문서 우선순위**: 14  
> **연관 문서**: CHANGE_CONTROL.md, PRD.md, DIRECTORY_SPEC.md, ERROR_ANALYSIS.md  
> **참조 규칙**: 구조·스캐폴딩·중요 결정은 날짜 역순으로 짧게 남긴다. 상세 실패 분석은 `ERROR_ANALYSIS.md`로 옮길 수 있다.

---

## 1. 문서 목적

구현과 문서 정렬 작업의 **타임라인**을 남겨, 이후 기여자가 맥락을 잃지 않게 한다.

---

## 2026-07-05 (4) — `recommended_risk_stages`/`_RISK_TIER_MIN`의 "5단계 취업안정권" 옛 정책 제거 — recall 0.730 → 1.000

### 배경
(3)의 LLM-judge recall 평가에서 PJ01(0.36)·PJ02(0.75)·PJ04(0.27)가 낮게 나온 원인을 추적. `scripts/build_cert_candidates.py`의 `recommended_risk_stages` 생성 정책(`relations/FOLDER.md` §P6-1)과 `recommendation_service._RISK_TIER_MIN`(§P6-2)이 둘 다 "risk_0001=취업 안정권, risk_0005=최고위험군"이라는 **옛 5단계 체계** 가정으로 설계돼 있었음(주석에 "취업 안정권" 문구 그대로 남아 있었음) — 2026-07-01 4단계(고립위험청년~은둔청년) 전환 시 갱신되지 않은 채 방치된 회귀. 그 결과 기능사·산업기사 등 접근 가능한 자격증이 risk_0001·risk_0002 쿼리에서 필터 단계에 원천 배제되고 있었다. 사용자가 "관련된거 전부 처리해줘"로 포괄 수정 지시.

### 수행
- `data/canonical/relations/FOLDER.md` §P6-1/P6-2/P6-3 재작성: "risk_0001=취업안정권" 가정 제거. 새 원칙 — 기술사·기능장(및 합격률 <10%)만 활동제한형·은둔청년(risk_0003·0004)에서 제외, 나머지는 전 단계(risk_0001~0004) 개방. 같은 위험군 안의 세부 난이도 우선순위는 이 하드 게이트가 아니라 F-03 §3.1 `_fit_score`의 `difficulty_fit`이 소프트하게 담당하도록 역할 분리.
- `scripts/build_cert_candidates.py`: `TIER_TO_RISK_STAGES`(1_기능사~3_기사 전 단계 개방, 4_기술사·5_기능장만 risk_0001·0002 한정) + `PASSRATE_TO_RISK_STAGES`(<10%만 risk_0001·0002 한정) + `DEFAULT_NONTECH_RISK_STAGES` 재정의. risk_0005는 신규 생성 시 더 이상 포함하지 않음. (부수 수정: 이 파일에 `from __future__ import annotations`가 없어 Python 3.9(`/usr/bin/python3`)에서 `pd.DataFrame | None` 타입힌트가 `TypeError`로 즉시 실행 불가였음 — 추가해서 해결.)
- `backend/app/services/recommendation_service.py`: `_RISK_TIER_MIN` 전부 0으로 전면 개방(하드 게이트 비활성화, 코드는 유지해 향후 재도입 가능하게 둠).
- `backend/app/services/risk_stage_service.py`: "1단계=관심군(취업안정권에 가까운 쪽)/5단계=은둔군" 주석을 4단계 체계로 정정.
- `PYTHONPATH=. python3 scripts/build_cert_candidates.py` 재실행 → `cert_candidates.jsonl` 1290행 중 1225행 갱신(`recommended_risk_stages` 필드 변경).

### 검증
백엔드 재기동 후 `scripts/llm_judge_golden_set.py` 재실행(동일 6개 페르소나, 새 gold set 재판정):
- recall_all: PJ01 0.36→**1.00**, PJ02 0.75→**1.00**, PJ03 1.00 유지, PJ04 0.27→**1.00**, PJ05 1.00 유지, PJ06 1.00 유지. **평균 0.730 → 1.000**.
- 회귀 확인: risk_0003(PJ03)·risk_0004(PJ06)의 실제 시스템 출력에 `4_기술사`/`5_기능장` tier 자격증이 섞여 들어오지 않았는지 별도 스크립트로 확인 — 0건, 하드 제외 정상 동작.
- recall@10은 여전히 낮은 편(0.14~1.00) — 이건 eligibility 문제가 아니라 같은 위험군 내 순위(Fit Score) 튜닝의 문제라 이번 수정 범위 밖으로 남김.

### 부가 검증 — 기존 `scripts/eval_golden_set.py` 회귀 확인
`docs/evaluation/golden_set.jsonl`(6개, risk_0001~0005 사용)로 재실행 → PASS RATE 91.1%(41/45), P15·P21 2건 FAIL. 둘 다 **예상된 결과**이지 새 버그가 아님:
- P15: "risk_0003 사용자는 4_기술사/5_기능장만 봐야 한다"는 기대 자체가 오늘 제거한 구 tier-게이트 전제 — 정책이 바뀌었으니 이 기대값이 무효화된 것.
- P21: risk_0005(구 5단계, 이미 백엔드 비활성) 페르소나. 이번 재생성으로 `recommended_risk_stages`에 risk_0005가 더 이상 태깅되지 않아 `fallback_used=True`로 전환됨 — risk_0005는애초 reserved라 이 결과가 오히려 일관적.
이 golden_set.jsonl은 모든 항목에 "_note: 전문가 검토 후 수정 필요 — 자동생성 베이스라인" 표시가 이미 있던 파일이라, 이번 정책 변경에 맞춰 기대값을 다시 쓰는 건 별도 검토 라운드로 남김(이번엔 수정하지 않음).

### 남은 이슈
- `golden_set.jsonl`의 P15·P21 `expected_*` 값을 새 정책에 맞춰 갱신할지 결정 필요(위 부가 검증 참고).
- recall@10 개선(Fit Score 가중치 재튜닝)은 별도 라운드로 남김.

---

## 2026-07-05 (3) — LLM-as-a-Judge 골든셋 생성 + recall 평가 (6개 신규 페르소나)

### 배경
`docs/evaluation/FOLDER.md` §5의 기존 Next-Step(감사 기록)에 "LLM-as-a-Judge 도입"이 이미 TODO로 명시돼 있었음. 사용자가 직접 6개 페르소나(위험군×도메인)를 지정하고 "LLM이 직접 정답지를 만들고, recall로 평가하겠다"고 요청:
1. 활동형고립청년(risk_0002)×소프트웨어개발, 2. 고립위험청년(risk_0001)×데이터/AI, 3. 활동제한형고립청년(risk_0003)×금융/회계, 4. 활동형고립청년(risk_0002)×디자인, 5. 고립위험청년(risk_0001)×교육, 6. 은둔청년(risk_0004)×법률.
난이도 정책: risk_0001은 난이도 있는 자격증도 허용, risk_0002 이상부터는 너무 어려운 자격증 지양.

### 수행
`scripts/llm_judge_golden_set.py` 신설:
- 각 페르소나의 도메인에 `related_domains`로 실제 연결된 `cert_candidates.jsonl` 후보 전체(할루시네이션 방지 — 실존 후보 중에서만 판정)를 GPT-4o-mini에 제시.
- 위험군 단계별 난이도 정책을 프롬프트에 명시하고, 각 후보의 relevant 여부를 이진 판정 → `expected_relevant_cert_ids` + 근거(`judge_reasoning`).
- 동일 쿼리로 `recommendation_service.recommendations()`를 호출해 실제 시스템 출력(`roadmap_sequence`)을 얻고, `recall_all`(전체 기준) · `recall_at_10`(top-10 기준) 계산.
- 결과를 `docs/evaluation/llm_judge_golden_set_2026-07-05.jsonl`에 저장(persona당 1줄: gold set, 실제 출력, recall 2종, judge reasoning).

### 결과 (recall_all / recall@10, gold건수/actual건수)
- PJ01 소프트웨어개발(risk_0002): 0.36 / 0.36 (14/24)
- PJ02 데이터AI(risk_0001): 0.75 / 0.75 (4/4)
- PJ03 금융회계(risk_0003): 1.00 / 0.55 (11/49)
- PJ04 디자인(risk_0002): 0.27 / 0.27 (11/9)
- PJ05 교육(risk_0001): 1.00 / 0.24 (17/33)
- PJ06 법률(risk_0004): 1.00 / 1.00 (1/3)
- 평균 recall_all = 0.730

### 핵심 발견 (범위 밖, 후속 검토 필요)
recall이 낮은 PJ01/PJ02/PJ04에서 gold로 판정된 기능사·준전문가급 자격증(예: `cert_0547` 정보기기운용기능사, `cert_1128` 데이터분석준전문가)이 실제 시스템 출력에 아예 없음. 원인 확인: 해당 후보들의 `recommended_risk_stages`가 `["risk_0003","risk_0004","risk_0005"]`로만 태깅돼 있어 `_filter_candidates`의 위험군 매칭에서 risk_0001·risk_0002 쿼리는 원천 배제됨. 즉 "쉬운 자격증은 심한 위험군에게만" 태깅된 기존 데이터 정책이, 이번에 사용자가 명시한 "risk_0002도 접근 가능한 난이도가 필요하다"는 정책과 충돌한다. `cert_candidates.jsonl`의 `recommended_risk_stages` 재태깅 여부는 별도 결정 필요 — 이번 작업에서는 진단만 하고 데이터는 건드리지 않음.

### 검증
6개 페르소나 모두 정상 실행, JSON 파싱 실패·API 오류 없음. gold set 크기(1~17건)와 judge reasoning을 육안 검토 — 도메인 관련성·난이도 정책 반영 방향은 합리적이나 `_note` 관례에 따라 전문가 검토 전 상태로 표시.

### 남은 이슈
- 이번 6개 페르소나는 `personas.json`의 기존 15종과 겹치지 않는 신규 세트 — 필요시 `personas.json`에 병합 여부 결정.
- gold set은 GPT-4o-mini 단일 판정(temperature 0.2, 재현성 확인 안 함) — 프로덕션 기준으로 쓰려면 사람 검토 또는 반복 샘플링으로 안정성 확인 권장.

---

## 2026-07-05 (2) — 위험군 "5단계" 잔존 표기 정리 — 현재 버전은 1~4단계로 통일

### 배경
사용자가 보사연(2022) 기준 4단계 분류 참고 이미지(`docs/references/지원 대상 유형 및 지원 목표에 따른 핵심 서비스.png` — 고립위험청년/활동형고립청년/활동제한형고립청년/은둔청년 4행)를 제시하며 "5단계로 되어 있는 건 다 이전 버전"이라고 명확히 함. 사업계획서·참가신청서 정정 작업 중 발견한 5단계 잔존 표기를 전체적으로 정리.

### 수행
- `사업계획서_작성내용.txt`: 10곳의 "5단계" 표기를 "4단계"로 수정. 【기능 1】 블록은 단순 치환을 넘어 실제 구현 로직(총점 비율 1·2단계 확정 → 정밀 3문항으로 3·4단계 구분)과 보사연 4단계 명칭(고립위험청년/활동형 고립청년/활동제한형 고립청년/은둔청년)에 맞춰 표·설명을 재작성. 기존 5단계 경계값 표(12.71/18.21/29.62/35.55/그이상)는 실제 미구현 설계였으므로 제거.
- `참가신청서_작성내용.txt`: "위험군 단계(1~5단계)" → "(1~4단계)".
- `PROJECT_SUMMARY.md`, `SUMMARY.md`: "위험군 단계(1~5)"/"1~5단계 산출" → "1~4". `SUMMARY.md`의 "로드맵 단계 5단계 타임라인"은 위험군과 무관한 **로드맵 단계**(roadmap_stage_0001~0005) 개념이라 그대로 둠 — 위험군(4단계)과 로드맵 단계(5단계)는 서로 다른 카운트라는 점에 유의.
- `DATA_SCHEMA.md` §5.1 RiskStage 제약: "현재 허용 범위는 1~5단계"를 "활성 위험군은 1~4단계, `risk_0005`(구 은둔군)는 `is_active=False`로 비활성 보존"으로 정정 — `risk_stage_master.csv`에 `risk_0005` 행이 실제로 존재(`is_active=False`)하므로 완전히 지우지 않고 정확한 상태로 명시. §18.2 CSV 갭 표의 "위험군(1~5단계)"도 "(1~4단계, risk_0005는 비활성 보존)"으로 정정.
- `FEATURE_SPEC.md`: F-01(목적/출력/처리규칙 — 판정 구간을 실제 코드(`RiskAssessment/index.tsx` `scoreToStage()`) 기준 "25% 미만 1단계, 50% 미만 2단계, 이후 정밀 3문항으로 3·4단계 구분"으로 재작성, 기존 5구간 %표는 코드와 불일치해 폐기), F-03 §처리규칙(4~5단계→4단계), F-14(4~5단계→4단계 ×2), F-17 처리규칙 표(위험군별 자원 게이팅, 4~5단계→4단계) + action 템플릿 설명(5단계→"1~4단계 활성, risk_0005 비활성 보존").
- `API_SPEC.md` §8.5, §8.7(위험군별 자원 게이팅 표): 4~5단계 → 4단계.
- `DIRECTORY_SPEC.md` §운영 원칙 6번, `SYSTEM_ARCHITECTURE.md`(cert_grade_tier 기반 추천 조정 규칙): 4~5단계/1~5단계 → 4단계.
- `README.md`, `CLAUDE.md`, `PRD.md`는 이미 이전 세션에서 4단계로 정정된 상태였음을 확인(추가 수정 불필요).

### 검증
`grep -rn "4~5단계\|1~5단계\|1단계 ~ 5단계"` 로 루트 md 전체 + 사업계획서/참가신청서 재확인 — 로드맵 단계(별개 개념, `roadmap_stage_0001~0005`)와 DEV_LOG 과거 기록을 제외하고 위험군 관련 "5단계" 잔존 표기 없음. 총 9개 파일 수정.

### 남은 이슈 (범위 밖, 이번엔 수정하지 않고 발견만 기록)
- **Safety Override 미구현 의심**: 문서들은 "자살·자해 항목 응답 시 최소 4단계로 강제 조정"이라 서술하지만, 실제 `RiskAssessment/index.tsx`의 `scoreToStage()`에는 `safetyFlag`를 반영해 단계를 올리는 코드가 없다 — `safetyFlag`는 위기 안내 배너(1393) 노출에만 쓰인다. 문서가 주장하는 안전 정책이 실제로 동작하는지 코드 재확인 필요.
- **F-17/API_SPEC §8.7 자원 게이팅 표의 `hiring` 표기**: 실제 `support_bundle_service.py`의 `_RESOURCE_TYPES`는 전 단계에서 `hiring`이 아니라 `job_fair`를 활성 자원으로 사용한다(오늘 앞서 채용행사 fallback 작업 중 확인). 표 이름과 실제 리소스 타입 키가 불일치.

---

## 2026-07-05 (1) — 적합도 지표(Fit Score) 정의·적용 — roadmap_stage 내부 정렬을 "쉬운 순"에서 "사용자에게 맞는 순"으로 변경

### 배경
발표 슬라이드에 "적합도 지표 산출을 통해 적합도가 높은 우선순위 추천"이라는 문구가 있었으나, 점검 결과 실제로는 `llm_cert_relevance_service.py`의 `relevance_delta_pct`가 자격증 상세의 "채용공고 매칭" 카드 한 곳에만 쓰이고 있었고, 로드맵의 실제 정렬(`recommendation_service._build_roadmap_sequence`)은 `(stage_order, level_score, 인기+응시빈도, pass_rate)` — 사실상 "쉽고 인기있는 순"이었지 사용자의 관심 도메인/직무·위험군 단계별 감당 가능한 난이도를 반영하지 않았다. 사용자가 "취업도 잘 되고 인기도 있으면서, 위험군 단계별 부담 정도에 맞는 난이도"를 반영한 우선순위 추천을 명시적으로 요청.

### 수행
- `FEATURE_SPEC.md` F-03에 §3.1 "적합도 지표(Fit Score)" 신설: 관심 일치도(0.45)+취업 실용성(0.35)+난이도 적합도(0.20) 가중합 정의. F-05에 stage 내부 정렬 기준으로 교차 참조 추가.
- `backend/app/services/recommendation_service.py`: `_interest_match_score`(도메인/직무 겹침 정도) · `_employability_score`(인기도+직무 폭+응시 접근성) · `_difficulty_fit_score`(위험군별 목표 합격률 근접도) · `_fit_score`(가중합) 추가.
- `_build_roadmap_sequence`에 `domain_ids`/`job_ids` 파라미터 추가, 전체 순서(`sequence`)와 stage별 목록(`by_stage.recommended_certs`) 정렬 키를 `(-fit_score, level_score)` 기준으로 교체(기존 `-(인기+빈도), -pass_rate` 대체). roadmap_stage 배정(난이도 서열) 자체는 변경하지 않음 — stage 내부 우선순위만 변경.
- 응답에 `fit_score`(0~100) 필드 노출(프론트 미연동, 추후 UI 표시용으로 남겨둠).

### 검증
- `python3 -m py_compile`(문법) + 로컬 서버 기동(`/api/v1/health` 200) 확인.
- `POST /api/v1/recommendations` (risk_0002, domain_0002 소프트웨어개발, job_0009 백엔드개발)로 확인: "실행 확대" 단계에서 job_0009와 실제로 매칭되는 정보처리기사(fit=93)·정보처리산업기사(fit=92)가 domain만 맞고 job은 안 맞는 사무자동화산업기사(fit=67)보다 확실히 상위로 이동.
- risk_0001(목표 합격률 40%) vs risk_0004(목표 합격률 68%) 비교: 동일 domain/job 조건에서 risk_0004는 고난도·저합격률 자격증의 fit_score가 상대적으로 낮아지고 합격률이 높은 자격증이 상대적으로 유리해짐 — "위험군이 심할수록 부담 낮은 난이도 우대" 의도대로 동작 확인.

### 남은 이슈 (범위 밖, 참고용 기록)
- `/api/v1/recommendations/llm` ("AI 맞춤 추천" 탭)은 `recommendation_service.py`와 별개인 `llm_roadmap_service.py`(`_select_diverse`/`_assign_stages`)를 사용 — 이번 fit_score가 아직 그쪽에는 적용되지 않음. 필요 시 별도 작업으로 확장.
- 가중치(0.45/0.35/0.20)와 위험군별 목표 합격률은 v1 기본값 — 골든셋 평가 후 조정 필요.

---

## 2026-07-02 (13) — (12) 가로 폭 흔들림 미해결 재확인 — 진짜 원인(.survey-wrap 누락) 수정

### 배경
사용자가 (12)의 `policy-card` width:100% 수정 이후에도 "연구근거 보기" 클릭 전/후 박스 가로 폭이 여전히 바뀐다고 스크린샷으로 재확인. `policy-card` 자체가 아니라 그 부모가 흔들리는 것으로 재조사 필요.

### 원인 (진짜 원인)
`RiskAssessment/index.tsx`는 `step`별로 조기 반환(early return)하며 각 분기가 자기만의 `<style>` 블록을 갖는 구조(이미 (11)에서 한 번 확인된 패턴)인데, `.survey-wrap`(`max-width:640px; display:flex; flex-direction:column; margin:0 auto`)을 정의하는 규칙이 파일 전체에서 메인 12문항 설문 분기의 `<style>` 블록에만 존재했음. `step === 'result'` 분기의 `<style>` 블록(`.result-card` 등이 정의된 곳)에는 `.survey-wrap` 규칙이 아예 없어서, 결과 화면에서는 `.survey-wrap`이 최대폭·flex 컬럼 제약 없이 렌더링되고 있었음. (12)에서 `policy-card`에 `width:100%`를 줘도, 기준이 되는 부모(`survey-wrap`) 자체의 폭이 콘텐츠에 따라 흔들리면 자식도 함께 흔들리므로 근본 해결이 안 됐던 것.

### 수행
`frontend/src/pages/RiskAssessment/index.tsx`의 결과 화면(`step === 'result'`) `<style>` 블록 맨 앞에 `.survey-wrap { max-width:640px; width:100%; box-sizing:border-box; display:flex; flex-direction:column; align-items:stretch; gap:1.5rem; margin:0 auto; }` 명시 추가 — 메인 설문 화면의 값과 동일하게 맞추되, `width:100%`와 `box-sizing:border-box`, `align-items:stretch`를 명시적으로 더해 콘텐츠 유무와 무관하게 항상 동일한 폭을 갖도록 함.

### 남은 이슈 (범위 밖, 참고용 기록)
(11)에서 남긴 것과 동일한 근본 원인 — 스텝별 `<style>` 블록 중복 분리 구조 자체가 이런 종류의 불일치를 계속 만들어낼 소지가 있음. 공유 레이아웃 규칙(`survey-wrap`, `survey-options`, `survey-opt` 등)을 `frontend/src/styles/index.css`로 이관하는 리팩터를 후속 과제로 재기록.

### 검증
`npx tsc --noEmit` (frontend): 통과, 0 에러.

---

## 2026-07-02 (12) — 추천 지원 제도 기본 펼침 + policy-card 가로 폭 흔들림 수정

### 배경
사용자가 결과 화면 하단을 재확인해 두 가지 결함 보고: (1) "추천 지원 제도" 섹션이 자체 내부 토글(`showPrograms`) 뒤에 숨어 있어 클릭해야만 목록이 보임(상위 게이트는 (10) Fix 4에서 이미 제거했으나 내부 토글 기본값은 그대로 `false`였음), (2) "연구근거 보기/접기" 버튼을 누를 때마다 `policy-card` 박스 자체의 가로 폭이 커졌다 줄었다 함(레이아웃 흔들림).

### 원인
(2)는 `.policy-card`가 `.survey-wrap`(`display:flex; flex-direction:column`)의 자식이면서 자기 자신도 `width`를 명시하지 않은 채 `display:flex; overflow:hidden`만 갖고 있어, 콘텐츠 양에 따라 가로 폭이 재계산되는 상태였음(표준 flex stretch가 기대대로 항상 적용되지 않는 케이스).

### 수행
`frontend/src/pages/RiskAssessment/index.tsx`
- `showPrograms` 초기값 `useState(false)` → `useState(true)`로 변경. 접기 옵션 자체는 유지(사용자가 다시 접을 수 있음).
- `.policy-card`에 `width: 100%; box-sizing: border-box; align-self: stretch;` 명시 추가 — 콘텐츠(연구근거 상세 노출 여부)와 무관하게 항상 부모(`.survey-wrap`) 폭에 고정되도록 함.

### 검증
`npx tsc --noEmit` (frontend): 통과, 0 에러.

---

## 2026-07-02 (11) — (10) Fix 1 정밀 판별 화면 선택지 간격 미적용 결함 수정

### 배경
(10) Fix 1에서 `.precision-q-card .survey-options { gap: 12px; }`를 추가했으나, 사용자가 실행 화면에서 재확인한 결과 여전히 선택지가 한 줄에 붙어 렌더링됨(`○오늘○2~3일 전○1주일 전●2주~1달 전○1달 이상 전`).

### 원인
`RiskAssessment/index.tsx`는 `step` 값에 따라 조기 반환(early return)하는 구조라, `step === 'precision'`일 때는 정밀 판별 화면 자체의 `<style>` 블록만 DOM에 존재하고, 메인 12문항 화면의 `<style>` 블록(`.survey-options { display:flex; flex-direction:column; gap:.5rem; }` 및 `.survey-opt` 외관 규칙 전체)은 애초에 렌더되지 않음. 즉 정밀 판별 화면에는 `.survey-options`를 세로 flex로 만드는 기본 규칙 자체가 없었고, `gap: 12px`만 추가해봤자 flex 컨테이너가 아니므로 적용될 대상이 없었음. 두 화면이 클래스명(`survey-options`/`survey-opt`)은 공유하면서 스타일 정의는 독립된 `<style>` 블록에 분리되어 있는 기존 구조의 허점.

### 수행
`frontend/src/pages/RiskAssessment/index.tsx`의 정밀 판별 화면 `<style>` 블록에 메인 설문 화면과 동일한 `.survey-options`(`display:flex; flex-direction:column; gap:.5rem;`) 및 `.survey-opt`/`.survey-opt:hover`/`.survey-opt.selected`/`.survey-opt-radio` 전체 규칙을 그대로 복제 추가. 기존 `.precision-q-card .survey-options { gap: 12px; }`는 유지(더 구체적인 선택자로 세로 간격을 12px로 재정의하는 용도로 정상 작동).

### 남은 이슈 (범위 밖, 참고용 기록)
같은 클래스명 스타일이 두 개의 독립된 `<style>` 블록에 중복 정의되는 구조라 향후 한쪽만 수정하면 다시 같은 종류의 불일치가 재발할 수 있음. 근본 해결은 공유 스타일을 `frontend/src/styles/index.css`(항상 로드됨)로 이관하는 것이나, 이번 요청 범위(간격 조정)를 벗어나 별도 리팩터로 미룸.

### 검증
`npx tsc --noEmit` (frontend): 통과, 0 에러.

---

## 2026-07-02 (10) — RiskAssessment 2라운드 코스메틱 UI 수정 + 결과 화면 구조 변경

### 배경
사용자가 실행 화면을 재검토해 추가 결함을 보고: (1) 2차 정밀 판별 화면의 문구·박스·문항 카드·버튼 간 간격 부족, (2) 결과 화면 상단 부제와 흰 박스 사이 간격 부족, (3) 방사형 차트 상세 분석이 기본 접힘 상태, (4) 결과 화면 하단에서 "추천 지원 제도"가 "내 상황 분석" 토글 뒤에 숨겨져 있어 실제 지원 제도 정보 접근성이 낮음. 전부 정책·채점·카피 변경이 아닌 순수 스타일·상태초기화·렌더 순서 조정이라 루트 문서(PRD.md 등)는 갱신 대상이 아님.

### 수행

**[Fix 1] 2차 정밀 판별 화면 간격 보강 (`frontend/src/pages/RiskAssessment/index.tsx`)**
- 부제(`page-desc`)에 `marginBottom: '1.5rem'` 인라인 스타일 추가 — 아래 `연구 근거` 박스와의 간격 확보.
- `.precision-note`(연구 근거 박스)에 동일하게 `marginBottom: '1.5rem'` 추가 — 첫 `추가 1/3` 카드와의 간격 확보. 기존 `1.5rem` 갭 스케일 재사용, 새 값 없음.
- `.precision-q-card .survey-options`에 `gap: 12px` 추가 — 메인 12문항 화면의 `.survey-options`(`gap:.5rem`, 세로 스택)와 달리 정밀 판별 화면은 자체 `<style>` 블록에 해당 규칙이 없어 옵션 버튼이 완전히 붙어 있던 결함. 메인 화면 값(`.5rem` ≈ 8px)과 사용자 지정값(12px)이 달라 지시대로 12px 사용.
- `.survey-nav`(이전 문항으로 / 결과 보기 버튼 그룹)에 `gap: .75rem` 명시 추가 — 메인 설문 화면 스타일 블록의 동일 규칙과 같은 값 재사용.

**[Fix 2] 결과 화면 상단 간격 (`frontend/src/pages/RiskAssessment/index.tsx`)**
- 결과 화면 부제(`page-desc`)에 `marginBottom: '1.5rem'` 인라인 스타일 추가 — 아래 흰색 `result-card` 박스와의 간격 확보. `.page-desc`의 기존 전역 규칙은 `margin-top`만 정의해 충돌 없음.

**[Fix 3] 상세 분석 기본 펼침 (`frontend/src/pages/RiskAssessment/index.tsx`)**
- `showDetail` 상태 조사 결과 방사형 차트+차원 막대 토글 단일 용도로만 쓰임(다른 부수 효과 없음) 확인.
- `useState(false)` → `useState(true)`로 변경 — 페이지 진입 시 상세 분석이 기본 노출되고, 접기 옵션은 그대로 유지.

**[Fix 4] 결과 화면 하단 섹션 재구성 (`frontend/src/pages/RiskAssessment/index.tsx`)**
- 기존 구조: `내 상황 분석 · 지원 제도 보기` 단일 외부 토글(`showPolicyCard`)이 `연구 근거` 출처 + `지금 내 상황`/`지원 전략` + `추천 지원 제도`(자체 내부 토글 `showPrograms` 보유) 전체를 함께 접고 있었음 — 실제 지원 제도 목록이 두 겹 토글 뒤에 숨어 있었음.
- `추천 지원 제도` 섹션을 외부 게이트에서 빼내 항상 렌더링되도록 변경. 내부 목록 렌더링 로직(`showPrograms` 토글, `policy.programs.map` 등)은 그대로 유지.
- `연구 근거` 출처 헤더 + `지금 내 상황` 설명 + `지원 전략` 배지를 `추천 지원 제도` 아래로 이동하고, 새 토글로 감쌈. 라벨은 접힘 시 "연구근거 보기", 펼침 시 "연구근거 접기".
- 위기 단계(3·4단계) 안내(1393 링크 포함)는 `추천 지원 제도` 바로 아래, 새 토글 바깥에 위치시켜 항상 노출 유지 — 안전 관련 콘텐츠 노출 범위는 축소하지 않음.
- **상태 변수 처리**: 기존 `showPolicyCard`/`setShowPolicyCard`를 새 용도에 맞게 `showEvidenceDetail`/`setShowEvidenceDetail`로 이름만 변경해 재사용(가장 작은 diff). 이 상태는 원래도 이 외부 게이트 하나에만 쓰였고 다른 부수 효과가 없어, 새 상태 변수를 추가하는 대신 그대로 좁은 용도로 전환. 토글 버튼의 CSS 클래스(`policy-card-toggle`)는 기존 것을 그대로 재사용 — 새 클래스 없음.
- 카피·색상·1393 핫라인 문구(`1393 자살예방상담전화`)는 변경하지 않음 (범위 외).

### 검증
- `npx tsc --noEmit` (frontend/) 통과, 출력 없음(에러 없음).

### 범위 확인
- 채점 로직, taxonomy, API 계약, 안전 배너/핫라인 문구는 변경하지 않음.
- 변경 파일: `frontend/src/pages/RiskAssessment/index.tsx` 단일 파일.
- 파일 추가/삭제 없어 `FOLDER.md` 갱신 대상 아님 (`frontend/src/pages/RiskAssessment/FOLDER.md` 확인, 용도·파일 목록 변경 없음).

---

## 2026-07-02 (9) — RiskAssessment/InterestSelection 코스메틱 UI 수정 3건

### 배경
사용자가 실행 화면 스크린샷을 근거로 코스메틱 결함 3건을 보고: (1) 2차 정밀 판별 화면 문구·카드 간격, (2) 결과 화면 카드 간 간격 과밀, (3) 관심 분야 아코디언 기본 펼침 상태 불일치. 셋 다 정책·구조 변경이 아닌 순수 프론트엔드 카피/CSS/상태초기화 수준이라 루트 문서(PRD.md 등)는 갱신 대상이 아님.

### 수행

**[Fix 1] 2차 정밀 판별 화면 (`frontend/src/pages/RiskAssessment/index.tsx`)**
- 부제 문구에서 "1분도 안 걸립니다." 트레일링 문장 제거 (`page-desc`).
- `.precision-q-card`에 `margin-bottom: 1.5rem`(및 마지막 카드 예외 처리)을 명시 추가 — `.survey-wrap`이 이미 쓰는 `1.5rem` 갭 스케일을 그대로 재사용, 새 값 발명 없음.

**[Fix 2] 결과 화면 카드 간 간격 (`frontend/src/pages/RiskAssessment/index.tsx`)**
- `.result-actions`(버튼 그룹), `.safety-banner`(1393 안내), 정책 토글 래퍼 div에 각각 `marginTop: '1.5rem'` 인라인 스타일 추가 — 동일하게 `.survey-wrap`/`.result-card` 갭 스케일(`1.5rem`)을 재사용. 정책 토글 래퍼의 기존 `marginTop: '.5rem'`은 `1.5rem`으로 통일.
- 카피·색상·1393 핫라인 문구는 손대지 않음 (범위 외).

**[Fix 3] InterestSelection 아코디언 기본 펼침 상태 (`frontend/src/pages/InterestSelection/index.tsx`)**
- 조사 결과: `STAGE_PREOPEN`은 위험군 단계(stage)에 따라 관련 도메인 그룹을 미리 펼쳐 보여주는 의도된 로직으로, 그대로 유지.
- 문제는 `stage`가 없는 경우(첫 방문·이전 선택 없음)의 폴백이 `['IT/디지털']`로 하드코딩되어 있던 것 — 사전 선택 근거 없이 임의로 한 그룹만 열려 있어 "일부는 열리고 일부는 닫힌" 비일관 인상을 준 원인. 폴백을 `[]`(전부 닫힘)로 변경.
- 토글 클릭 동작(`toggleGroup`)은 변경하지 않음.

### 검증
- `npx tsc --noEmit` (frontend/) 통과, 출력 없음(에러 없음).

### 범위 확인
- 채점 로직, taxonomy, API 계약, 문구/색상/핫라인 콘텐츠는 변경하지 않음.
- 변경 파일: `frontend/src/pages/RiskAssessment/index.tsx`, `frontend/src/pages/InterestSelection/index.tsx` 2개.
- 파일 추가/삭제 없어 `FOLDER.md` 갱신 대상 아님 (`frontend/src/pages/RiskAssessment/FOLDER.md` 확인, `InterestSelection`에는 `FOLDER.md` 없음).

---

## 2026-07-02 (8) — 안전 문항 배치·게이트 지속성 수정 + 설문 UX 보강

### 배경
사용자 요청: "설문이 초기화 안 되게 해줘. 이전으로 돌아가도, 그리고 건너뛴다고 계속 질문해도 괜찮을까요? 질문을 마지막으로 넣는거 어때? 11, 12 순서만 바꿔서." 코드 확인 결과 두 가지 실제 결함을 확인:

1. **게이트 재노출 결함**: `safetyGatePassed`가 `localStorage`에 저장되지 않고 매 마운트 시 `current > 10`으로만 추정됨. 안전 인터스티셜(B12_9 진입 직전)을 통과한 직후 새로고침하면 `current`가 아직 그 문항이라 게이트가 다시 뜸.
2. **스킵 후 진행 막힘 결함**: 안전 문항(B12_9)을 건너뛴 뒤 "이전"으로 되돌아갔다가 다시 그 위치에 오면, `answered = answers[q.id] !== undefined`가 `false`가 되어 "다음/결과 보기" 버튼이 막힘 — 스킵의 의미가 무력화됨. 인터스티셜은 1회성이라 재스킵 수단도 없었음.

### 수행

**민감 문항을 설문 맨 마지막으로 이동** (`frontend/src/pages/RiskAssessment/index.tsx`)
- `QUESTIONS` 배열에서 `B12_9`(자살·자해 사고, safetyKey)를 `B9_4`(자기관리) 뒤, 즉 12번째(마지막)로 재배치.
- 하드코딩된 인덱스(`current === 10` 등) 전부 제거 — `SAFETY_Q_INDEX = QUESTIONS.findIndex(qq => qq.safetyKey)`로 안전 문항 위치를 배열에서 직접 도출하도록 변경. 이후 문항 순서가 다시 바뀌어도 게이트 로직이 깨지지 않음.
- 인터스티셜 문구를 "마지막 두 문항 전에 잠깐요" → "이제 마지막 질문이에요"로 갱신 (실제로 마지막 문항이 됨을 반영).

**게이트 통과 상태 영속화**
- `_saveProgress`에 `safetyGateSeen`, `skipped` 필드 추가 저장. `safetyGatePassed` 초기값을 `safetyGateSeen ?? (current > SAFETY_Q_INDEX)`로 변경해, 게이트를 이미 통과한 세션은 새로고침해도 재노출되지 않게 함.
- "괜찮아요" 클릭 시에도 `safetyGateSeen: true`를 즉시 저장.

**스킵 후 진행 막힘 수정**
- `skipped: Record<string, boolean>` 상태 신설(영속화 포함). `answered = answers[q.id] !== undefined || !!skipped[q.id]`로 변경해, 스킵한 문항으로 되돌아가도 다음/결과 버튼이 막히지 않음.
- 문항 카드 자체에도(인터스티셜뿐 아니라) "답변하지 않고 넘어갈게요" 링크를 상시 노출해, 어느 시점에 다시 방문해도 재스킵 가능.
- `select()`에서 실제로 답변하면 해당 문항의 `skipped` 상태를 해제하도록 처리(스킵 → 재답변 전환 지원).
- "다시 진단"(결과 화면)과 "처음부터"(복원 배너) 리셋 핸들러에 `setSkipped({})`, `setSafetyGatePassed(false)` 누락돼 있던 것을 추가 — 이전에는 재진단해도 게이트를 통과한 것으로 남아 있어 게이트가 다시는 뜨지 않는 결함이 있었음. "다시 진단" 핸들러에는 `setWasRestored(false)`도 함께 추가(재진단 직후 "이전 진행 상태 복원" 배너가 잘못 남아 있던 것도 같은 자리에서 수정).

### 검증
- `tsc --noEmit`, `vite build` 통과.
- 브라우저로 실제 플로우 확인: (1) 문항 순서 스왑 반영(11번=자기관리, 12번=안전 문항), (2) 12번 문항에서 새로고침 시 게이트 재노출 없이 실제 문항 카드로 복원, (3) 인터스티셜/카드 양쪽에서 스킵 → 결과 화면 직행 + 1393 안전 배너 정상 노출, (4) "다시 진단" 클릭 후 재응시 시 게이트가 다시 정상 노출(리셋 로직 검증), 스탤 배너 없음.

### 범위 확인
- Safety Override 점수 임계값(`FEATURE_SPEC.md` F-01), taxonomy, API 계약은 변경하지 않음 — 문항 배치·클라이언트 상태 영속화만 다룬 UI 레벨 변경으로, 루트 문서 갱신 대상 아님.
- 변경 파일: `frontend/src/pages/RiskAssessment/index.tsx` 단일 파일.

---

## 2026-07-02 (7) — critique 기반 P0 안전/데이터 무결성 수정 2건 (임상 라벨 노출, B12_9 스킵 채점 오류)

### 배경
`/impeccable critique`가 frontend에 P0 2건을 보고함 (`frontend/.impeccable/critique/2026-07-02T06-48-34Z__frontend.md`, `2026-07-02T07-03-49Z__frontend.md`). 둘 다 비주얼/코스메틱이 아니라 안전·데이터 무결성 문제:

1. Recommendation 결과 화면이 `RISK_LABEL`로 "4단계 (은둔 청년)" 같은 임상 문헌 용어를 `<strong>` 굵게 노출 — 사용자 여정의 peak-end 순간(최종 결과 화면)에서 가장 낙인 위험이 큰 문구가 그대로 보임.
2. RiskAssessment의 B12_9(PHQ-9 자살사고 문항)를 "건너뛸게요"로 스킵하면 `B12_9: 0`(가장 안전한 응답)으로 채점되고 `safetyFlag`도 세팅되지 않음 — 정서적으로 힘들어서 문항을 건너뛴 사용자가 "위기 없음"으로 오분류되는, 가능한 가장 위험한 오분류.

### 수행

**🔴 [Fix 1] Recommendation 임상 라벨 제거 (`frontend/src/pages/Recommendation/index.tsx`)**
- `RISK_LABEL` (`'4': '4단계 (은둔 청년)'` 등 임상 문자열 매핑) 삭제.
- InterestSelection에 이미 있던 비낙인 plain-language 문구(`RISK_STAGE_LABELS`: "지금 집에서 혼자 있는 시간이 많은 상황" 등)를 그대로 재사용. 새 카피를 만들지 않음.
- 단일 출처화를 위해 `frontend/src/constants/stageLabels.ts` 신설 (`STAGE_LABELS` export). 기존 `frontend/src/constants/` 스캐폴드(`FOLDER.md` "UI 라벨·경로 상수" 용도)에 부합하는 위치.
- Recommendation은 새 상수를 import하도록 변경. **InterestSelection의 자체 `RISK_STAGE_LABELS`는 이번 변경 범위 밖이라 그대로 둠** (동일 문구 중복 보유 — 후속 정리 대상으로 `constants/FOLDER.md`에 기록).
- Roadmap의 별도 `RISK_LABELS`(동일한 임상 문자열)는 이번 critique·작업 지시 범위 밖이라 의도적으로 손대지 않음.

**🔴 [Fix 2] B12_9 스킵 채점 버그 수정 (`frontend/src/pages/RiskAssessment/index.tsx`)**
- 스킵 버튼 핸들러: `B12_9: 0`을 answers에 넣던 것을 제거하고, 대신 해당 키를 `answers`에서 아예 비워둠(무응답 처리, 0점 미부여).
- `select()`에서 안전 항목 고위험 응답 시 `safetyFlag`를 세우는 것과 동일한 패턴을 그대로 적용해, 스킵 시에도 `safetyFlag = true`로 세팅 — 기존 safety banner(1393 안내)가 그대로 재사용되어 노출됨. 새 UI는 만들지 않음.
- `getEffectiveMax()` 헬퍼 추가: 스킵된 safetyKey 문항의 만점을 `TOTAL_MAX`에서 제외한 실효 분모를 계산. `finish()`의 진행 분기 판단과 결과 화면의 `pct` 계산 두 곳 모두 이 실효 분모를 사용하도록 교체 (기존 `totalScore` 분자 계산 로직·`scoreToStage` 자체는 변경하지 않음).

### 범위 확인
- auto-advance 타이밍, CertCard 접근성, safety banner 색상/배치, taxonomy 파일은 이번 작업에서 손대지 않음 (별도 트랙에서 처리 중).
- 변경 파일: `frontend/src/pages/Recommendation/index.tsx`, `frontend/src/pages/RiskAssessment/index.tsx`, 신규 `frontend/src/constants/stageLabels.ts`, `frontend/src/constants/FOLDER.md` 갱신.

---

## 2026-07-02 (6) — 진입 프레이밍 점검 + 재방문 이어가기(F-33) 구현

### 배경
"사용자 이탈 없이, 청년들이 진짜 쓸까?"라는 질문에 실제 첫 진입 경험을 점검. 두 가지 구조적 문제 확인:
1. `Home.tsx`가 100% "자격증 추천" 프레이밍 — 고립·은둔 관련 언급은 통계 한 줄(9.4%)뿐. `RiskAssessment` 결과 화면의 공감·안전 문구(안전 배너, 지원 프로그램)는 12문항을 다 풀어야만 보여서, 첫 진입 사용자에게는 전혀 노출되지 않음.
2. `RiskAssessment` 설문 진입 화면 타이틀이 "나에게 맞는 자격증 찾기"인데 Q1은 "조언을 구할 수 있는 사람이 있나요?" 같은 관계망 질문 — 사전 설명·안심 문구 없이 바로 개인적 질문으로 들어가 낙차가 큼.
3. `pipelineState.ts`가 `sessionStorage` 기반이라 완료된 진단 결과가 탭을 닫으면 사라짐 — 재방문 시 이어지는 경험이 구조적으로 불가능했음.

### 수행

**🔴 재방문 이어가기 신규 구현 (F-33, `frontend/src/utils/userHistory.ts` 신설)**
- `localStorage` 기반(60일 TTL) — `pipelineState.ts`(sessionStorage)와 역할 분리
- `recordDiagnosisComplete()`: `RiskAssessment` 결과 화면 진입 시 자동 기록
- `markTodayActionComplete()`: `IsolationDashboard` "오늘의 행동" 카드에 "오늘 했어요" 버튼 추가, 연속 방문 시 스트릭 증가(어제 완료 → +1, 오늘 중복 방지, 끊기면 리셋), 스트릭 2 이상이면 "🔥 N일째" 배지 표시
- `Home.tsx` 진입 시 이력 있으면 히어로 위에 "다시 오셨네요" 웰컴백 카드 표시 → `/isolation/dashboard`로 즉시 연결, "새로 진단하기"로 초기화 가능
- `frontend/src/utils/FOLDER.md` 갱신, `FEATURE_SPEC.md` F-33 추가(§4 목록 + §5 상세)

**🟡 진입 프레이밍 최소 개선 (전면 리브랜딩 아님 — 범위 한정)**
- `Home.tsx` 히어로에 안심 문구 1줄 추가: "취업 준비가 안 되어 있어도 괜찮아요. 정답은 없고, 지금 상황부터 편하게 확인해보세요."
- `RiskAssessment` 설문 첫 문항에서만(재방문 복원 아닐 때) 안심 문구 추가: "시험 성적이 아니라 지금 상황을 편하게 확인하는 질문이에요. 정답은 없고, 어떤 답을 골라도 괜찮습니다."
- 최초 카피 초안에 "응답은 서버로 전송되지 않는다"는 문구를 넣었다가, 실제로는 stage_id·dimPct 등 파생값이 evidence 검색을 위해 서버로 전송되는 것을 재확인하고 검증 불가능한 문구를 제거함(자체 피드백으로 발견).

### 검증
- `npx tsc --noEmit`: 프로젝트 전체 0 에러
- `npm run build` (vite): 정상 빌드 성공, 기존 코드 스플리팅 유지 확인
- 해시 계산을 수기 입력하다 3회 연속 마지막 글자 누락 오류 발생 — 이후 `sed`로 계산값을 직접 삽입하는 방식으로 전환해 재발 방지

### 남은 이슈 (범위 밖)
- 재방문 이력은 브라우저별 로컬 저장이라 기기를 바꾸면 이어지지 않음 — 계정/로그인 기반 영속화는 후속 범위.
- `Home.tsx`의 전면적인 톤·카피 리브랜딩(서비스 그리드, FLOW, PROMISES 등)은 이번 범위에서 하지 않음 — 최소 안심 문구만 추가.

---

## 2026-07-02 (5) — career_net.py 이벤트 루프 블로킹 버그 수정, 배포 상태 정정(이미 라이브)

### 수행

**🔴 career_net.py async/sync 블로킹 버그 수정**
"최고 성능으로 고도화" 4번째 트랙(응답 속도/비용 최적화)에서 백엔드 캐싱·N+1·비동기 패턴을 전수 점검. `backend/app/api/v1/routes/career_net.py`의 `list_jobs`/`get_job`/`list_majors` 3개 라우트가 `async def`로 선언되어 있으면서 내부적으로 `career_net_service`의 동기 `httpx.get()` 호출(비-async)을 그대로 호출하는 것을 발견.
- FastAPI에서 `async def` 라우트는 스레드풀로 오프로드되지 않고 이벤트 루프에서 직접 실행되므로, 이 3개 엔드포인트 호출 중에는 커리어넷 외부 API 응답이 올 때까지 **서버의 다른 모든 동시 요청이 멈춘다** (health check 포함).
- `schedule.py`/`jobs.py`/`training.py`/`seoul.py`는 이미 동일한 유형(동기 외부 API 호출)을 전부 `def`(비-async)로 올바르게 처리하고 있어, 이 파일만 예외적으로 빠져 있었던 것으로 확인.
- 수정: 3개 라우트를 `async def` → `def`로 변경 (FastAPI가 자동으로 스레드풀 오프로드). 나머지 async 라우트(`cert_info.py`, `ncs.py`)는 내부적으로 네트워크 호출이 전혀 없는 순수 로컬 CSV 조회(`lru_cache` 적용됨)라 실질적 영향이 미미해 변경하지 않음.

**🟢 백엔드 캐싱/배치 패턴 점검 (변경 없음)**
- `recommendation_service.py`의 CSV 로더 12개 전부 `@lru_cache(maxsize=1)` 적용 확인, `_invalidate_caches()`로 증분 재빌드 시 무효화 가능
- `llm_roadmap_service.llm_recommendations()`는 자격증별 개별 LLM 호출이 아니라 전체 후보를 하나의 배치 프롬프트로 묶어 단일 LLM 호출 — N+1 패턴 없음 확인
- `career_net_service.py`의 외부 API는 자체 TTL 캐시(5분) 사용 — lru_cache가 아닌 TTL 캐시를 쓴 것은 외부 데이터 최신성 때문으로, 의도된 설계로 판단해 변경 안 함
- 프론트 `App.tsx`는 이미 무거운 라우트(Roadmap·Recommendation·AllCerts 등 8개)를 `React.lazy`로 코드 스플리팅 중 — 추가 조치 불필요

**🟡 배포 상태 정정 — 이전 대화에서의 오판 수정**
이전 세션에서 "프론트엔드 공개 배포 미확인"으로 기록했으나, 이번 점검에서 `https://www.didim.life`가 이미 정상 배포·서빙 중임을 확인 (HTTP 200, `<title>디딤 · 청년 취업 자격증 로드맵</title>` 확인, `/api/v1/health` 프록시도 정상 응답). 당시 `*.vercel.app` 패턴만 검색하고 커스텀 도메인(`didim.life`) 배포를 놓쳤던 조사 누락이었음 — **배포 트랙은 이미 완료 상태**이며 추가 조치 불필요.

### 남은 트랙
- 없음 — 요청된 4개 트랙(신뢰성 가드레일, 이탈 방지 UX, 자체 피드백, 응답 속도/배포) 전부 점검 완료.

---

## 2026-07-02 (4) — 이탈 방지 UX 점검(변경 없음) + 자체 피드백 점검(링크 화이트리스트 보강)

### 수행

**🟢 이탈 방지 UX 점검 — Roadmap / Recommendation / InterestSelection**
"최고 성능으로 고도화" 3번째 트랙(이탈 방지 UX 확장)을 진행하며 세 페이지의 모든 fetch 경로(Roadmap 7곳, Recommendation 12곳)를 점검. 가설(다른 페이지들엔 IsolationDashboard 수준의 폴백이 부족할 것)과 달리, **이미 전 구간에 일관된 패턴이 적용되어 있음을 확인**:
- Roadmap 메인 로드: DB 우선(5초 timeout) → 실패 시 `buildLocalRoadmap` 로컬 폴백 → 그것도 실패해야만 에러 표시
- Recommendation 메인 리스트: 정적 JSON(`/data/cert_candidates.json`, 백엔드 무의존) 로드 + 실패 시 재시도 버튼
- 두 페이지의 보조 fetch(evidence·DAG·videos·exam·training 등 약 15개 함수) 전부 성공/실패/abort 각 분기에서 loading 상태를 명시적으로 해제 — 스피너가 멈추지 않는 경우 없음
- InterestSelection은 네트워크 호출이 전혀 없는 순수 클라이언트 상태 페이지라 애초에 이탈 위험 없음
- **결론: 코드 변경 없음.** 불필요한 변경을 만들지 않고 점검 결과만 기록.

**🟡 자체 피드백 점검 (chat_service.py)**
지시에 따라 이번 세션 변경분을 스스로 재검토. `_self_evaluate_reply`의 링크 화이트리스트 검사가 `domain in url` 부분 문자열 매칭이라 `work24.go.kr.evil.com` 같은 스푸핑 도메인을 허용 링크로 오판할 수 있는 결함 발견.
- `_is_allowed_link_domain()`으로 교체: `urllib.parse.urlparse`로 실제 hostname을 추출해 정확 일치 또는 서브도메인(`endswith(".domain")`)만 허용
- 6개 케이스(정상 서브도메인/apex, 스푸핑 도메인 2종, 정상 사례, 비허용 도메인)로 검증 완료, 이전 로직이 통과시켰을 스푸핑 케이스가 정확히 차단됨을 확인

### 부가 검증 (교차 확인)
`llm_cert_relevance_service._pass_rate_to_difficulty_score()`(합격률 → 0~100 난이도, `100-rate` 선형)를 `llm_roadmap_service._passrate_to_difficulty()`(합격률 → 1~5 난이도 계단함수)와 경계값 기준으로 비교 — 두 함수가 서로 다른 스케일임에도 경계값(70%→30/30, 50%→50/50, 30%→70/70)이 거의 일치해 그라운딩 공식이 기존 코드베이스 관행과 합리적으로 정합함을 재확인.

### 남은 트랙
- 응답 속도/비용 최적화, 프로덕션 배포 완성은 아직 미착수.

---

## 2026-07-02 (3) — 자격증 연관성 분석 difficulty_score 실측 데이터 근거화 (환각 제거)

### 배경
"최고 성능으로 고도화" 요청에 따라 신뢰성 가드레일 확장 트랙을 진행하며 전체 LLM 호출 경로(`chat_service`, `llm_roadmap_service`, `hyde_evidence_service`, `llm_isolation_service`, `llm_cert_relevance_service`)를 점검. `llm_cert_relevance_service.py`가 검증 장치 없이 `difficulty_score`(0~100 난이도)를 LLM에게 그대로 추정시키고 있었고, 이 값이 `job_postings.py`의 `meets_threshold` 판단(위험군 단계별 자격증 추천 게이팅)에 직접 사용되고 있어 **근거 없는 LLM 추정치가 구조적 추천 결정에 관여하는** 가장 심각한 사례로 확인됨. 프론트 `CertJobCard.tsx`에도 "난이도 {N}%"로 그대로 노출됨.

### 수행

**🔴 difficulty_score 실측 근거화 (llm_cert_relevance_service.py)**
- `_load_pass_rate_by_name()` 추가: `cert_master.csv`의 실측 `avg_pass_rate_3yr`를 cert_name 기준으로 로드 (1290건)
- `_pass_rate_to_difficulty_score()` / `_ground_difficulty()` 추가: 실측 합격률이 있으면 `difficulty_score`를 실측 기반 값으로 덮어쓰고 `difficulty_grounded=True` 표시, 없으면 기존 LLM/고정 추정치를 유지하되 `difficulty_grounded=False`로 정직하게 표시
- 캐시 히트·LLM 성공·LLM 실패·API 키 미설정 4개 반환 경로 모두에 동일 적용
- 검증: "용접기술사"(실측 27.42%) → difficulty_score 73으로 그라운딩, 존재하지 않는 가짜 자격증명은 grounded=False로 정상 폴백 확인. 기존 `_FALLBACK_MAP` 하드코딩값(예: 빅데이터분석기사 65)이 실측 기반 값(45)과 상당히 달랐던 것도 확인 — 정확도 개선 확인
- `job_postings.py` 응답에 `difficulty_grounded` 필드 노출 (하위 호환, 추가 필드만)

### 미해결 (열린 이슈)
- `relevance_delta_pct`(직무 연관성 %)는 근거로 삼을 실측 데이터가 없어 계속 LLM 추정치로 남음 — `from_llm` 플래그로만 구분됨. 실제 채용공고 빈도 통계 소스가 생기면 별도 근거화 필요.
- `llm_isolation_service.py`(F-25 서비스 설명), `hyde_evidence_service.py`는 이미 "evidence 없으면 임의 사실 생성 금지" 원칙 + JSON 스키마 제약으로 설계되어 있어 이번 라운드에서 추가 조치하지 않음.
- 이탈 방지 UX 확장(Roadmap·Recommendation·InterestSelection에 RiskAssessment/IsolationDashboard 수준의 폴백·로딩 패턴 적용)은 아직 미착수.

---

## 2026-07-02 (2) — 위험군 단계 수 문서 정합(PRD/README 4단계 통일), 상담 챗봇 자체 검증 가드레일 + 문서화

### 배경
실사용 가능성 점검 중 두 가지 신뢰성 격차 발견:
1. `CLAUDE.md` §6·실제 코드(RiskAssessment)는 이미 2026-07-01 4단계(고립위험청년~은둔청년) 체계로 전환됐는데, `PRD.md`·`README.md`는 여전히 "1~5단계" 문구로 남아 문서-코드 불일치.
2. `chat_service.py`(상담 에이전트)가 `README.md`/`SYSTEM_ARCHITECTURE.md`/`PRD.md`에 reserved(미구현)로 명시된 "상담형 대화 에이전트"와 겹치는 상태로 이미 운영 중이면서도, `llm_roadmap_service.py`의 `_self_evaluate` 같은 사후 검증 장치 없이 시스템 프롬프트 지시에만 의존하고 있었고, `FEATURE_SPEC.md`/`API_SPEC.md`에 계약이 전혀 문서화되어 있지 않았음.

### 수행

**🔴 PRD.md / README.md 위험군 단계 수 정정**
- "1단계~5단계" → "1단계~4단계"로 전체 치환 (§2 흐름도, §6.1, §7.1, §8.1, §11 시나리오, README §2.1·§4.0)
- §7.1에 CLAUDE.md §6 기준 4단계 정의(고립위험청년/활동형 고립청년/활동제한형 고립청년/은둔청년) 명시, risk_0005 비활성 보존 안내 추가
- PRD §17 오픈이슈에서 "위험군 2~4단계의 세부 정의" 항목 제거(해결됨으로 표시)
- README `5단계 경로`(로드맵 stage, `roadmap_stage_master.csv` 기준 실제 5단계)는 위험군 단계와 무관한 별개 개념이므로 변경하지 않음

**🟡 chat_service.py 자체 검증 가드레일 추가**
- `_self_evaluate_reply()` 추가: 응답에서 (1) 구체적 날짜(연/월/일 — 일정 API 미연동 상태이므로 금지), (2) evidence 없이 등장한 %(합격률·수치), (3) 허용 도메인 목록 밖 링크를 휴리스틱으로 감지
- 문제 감지 시 `llm_roadmap_service._self_evaluate`와 동일한 self-refine 패턴으로 1회 재생성, 응답에 `eval.issues`/`eval.refined` 노출
- 재생성 실패는 조용히 무시하고 원본 응답 반환 (대화 흐름 유지 우선)

**🟢 상담 챗봇 문서화 (FEATURE_SPEC.md F-32, API_SPEC.md 8.11)**
- `FEATURE_SPEC.md`에 F-32 신규 추가: 목적·범위 경계·자체 검증 설계 원칙·입출력·예외 명시
- **범위 경계**를 명시적으로 좁힘: 자격증/진로/정부지원 Q&A 단일 세션 한정, 치료적 개입·장기 상담 이력 미포함 → reserved인 "완전한 상담형 대화 에이전트"와는 구분됨을 문서에 직접 기록
- `API_SPEC.md`에 `POST /chat` 계약 추가 (§6 목록, §8.11 상세)

### 미해결 (열린 이슈)
- `README.md`/`SYSTEM_ARCHITECTURE.md`/`PRD.md`의 Reserved/비범위 목록에는 여전히 "상담형 대화 에이전트"가 남아 있음 — F-32(범위 한정 Q&A)로 자동 승격 처리하지 않았다. reserved 목록을 이대로 유지할지, F-32 범위를 반영해 문구를 분리할지는 별도 결정 필요.
- 프론트엔드 공개 배포(Vercel) 여부 미확인 — `frontend/vercel.json`은 있으나 실제 배포 URL 미확인 상태로 남아 있음 (이번 작업 범위 밖).

---

## 2026-07-02 — UX 5대 개선 (실데이터 기반), 인트로 화면, 단계별 공감 문구, 행동 뱅크 확장

### 수행

**🔴 인트로 화면 추가 (RiskAssessment/index.tsx)**
- step 상태에 `'intro'` 추가 (로컬스토리지 복원 없을 때 진입)
- 서울시 실태조사 실데이터 통계 (54만명 / 55.7% / 1,287종) 사용
- 개인정보 뱅크 없음 배지, "내 상황 확인하기 (3분)" CTA

**🔴 결과 화면 실데이터 카드 (RiskAssessment/index.tsx)**
- 3~4단계: 55.7% 극복의향, 22% 일·공부 시작, 서울시 실태조사 당사자 인터뷰 2개
- 1~2단계: 42% 일자리 기회 원함, 54만명, 합격률 기반 자격증 통계
- 단계별 CTA 문구, 보사연 2022 연구기반 배지

**🔴 로드맵 단계별 행동 뱅크 확장 (Roadmap/index.tsx)**
- STAGE_ACTION_BANK: 단계별 5개 행동, 총 20개
- 4단계: 1~2분 초소형 행동 (청년이음센터 1601-0112 등)
- 3단계: 3~5분 제도 연결 행동
- 2단계: 10~15분 실행 행동
- 1단계: 10~20분 적극 준비 행동
- "다른 행동 보기" 순환, 링크 있는 행동엔 "바로 가기" 버튼

**🟡 자격증 카드 단계 공감 문구 (Recommendation/index.tsx)**
- `buildStageMessage()` 함수: `recommended_risk_stages` + `avg_pass_rate_3yr` 실데이터 기반
- 단계별 맞춤 문구 (가공 문구 아님, recommended_risk_stages 포함 여부로 분기)
- `CertCard`에 `userStage` prop 추가, 보라 배지로 표시

---

## 2026-07-01 (2) — 5단계→4단계 통합, 로드맵 시작점 코드 정합, cert_explain 단계명 교정

### 수행

**🔴 risk_stage_master.csv 단계명 교체 (SCRIPT.md 보사연 2022 기준)**
- 관심군→고립위험청년 / 고립 위험군→활동형 고립청년 / 고립군→활동제한형 고립청년 / 은둔 위험군→은둔청년
- risk_0005(은둔군) is_active=False — 프론트 미사용, cert_candidates는 모두 risk_0004와 중첩이므로 데이터 손실 없음
- cert_explain `risk_name` 자동 교정: "은둔 위험군인 지금" → "은둔청년인 지금"

**🔴 `_STARTING_STAGE` 코드 불일치 수정 (llm_roadmap_service.py)**
- risk_0003/0004 → roadmap_stage_0001 (CSV와 동기화)
- 이전: risk_0003/0004/0005 모두 roadmap_stage_0002를 반환 → 3·4단계 사용자가 `상태 인식` 단계 건너뛰는 버그

**🟡 risk_0005 비활성화 (연관 CSV 정리)**
- support_program_risk_stage_mapping.csv: 14개 risk_0005 행 is_active=False
- risk_stage_to_roadmap_stage.csv: rtr_00005 is_active=False
- target_group_master.csv: tg_0004/tg_0005 mapped_risk_stage_ids에서 risk_0005 제거

**🟢 CLAUDE.md §6 도메인 규칙 교체**
- 5단계 취업 안정권 체계 → SCRIPT.md 기반 4단계 고립·은둔 체계로 교체

**미구현 (reserved)**
- 실시간 WorkNet 채용 시장 데이터 cert_explain 통합 — 현재 cert_job_mapping 구조적 직무로 대체됨. 별도 설계 후 진행 예정.

---

## 2026-07-01 — 파이프라인 품질 강화 (환각 가드, grade 배치, HyDE 수치 인용, UX 용어 정제)

### 수행

**🔴 합격률 환각 감지 (llm_roadmap_service.py)**
- `_self_evaluate` S1 역방향 체크 추가: `has_pass_rate=False` 인데 `%` 수치 포함 시 issue 발생 → self-refine 트리거
- 시스템 프롬프트 S1 제약 강화: "합격률 없으면 % 수치 절대 사용 금지" 명시
- limited 케이스(cert_0130 섬유기계기사) 검증: % 미출력 + score 5/5 확인

**🟡 HyDE dim_score % 수치 인용 강제 (hyde_evidence_service.py)**
- `_synthesize_with_guardrail` 시스템 프롬프트 규칙 6 추가: "첫 문장에 주요 차원명과 수치 반드시 인용"
- user_prompt에 `{dim_summary}` 인용 강제 문구 추가
- 결과: "관계망(92%) / 활동(87%) / 심리(73%)에서의 높은 어려움으로..." 형태로 안정 출력

**🟢 cert_grade_tier 공백 배치 개선 (llm_roadmap_service.py)**
- `_parse_avg_pass_rate()` / `_passrate_to_difficulty()` 추가: 합격률 → 가상 난이도(1~5) 역산
- `_assign_stages` 빈 tier 처리 순서: ① 명시 난이도 → ② 합격률 역산 → ③ 기본값
- 549개 빈 tier 중 363개(66%)가 합격률로 적절한 단계에 분산 배치됨

**UX 전문 용어 정제 (API 응답)**
- `grade_display` 필드 추가: `"1_기능사"` → `"기능사"`, 등급 없음 → `"전문자격"`
- `achievability_display` 추가: `"immediate"` → `"지금 바로 도전"`, `"near_term"` → `"단계 준비 후 도전"`
- 지원제도 `category_display`: `"자기이해_및_심리상담"` → `"자기이해 및 심리상담"` 등
- 지원제도 `phase_display`: `"고립된_삶"` → `"고립 단계"` 등

---

## 2026-06-30 — RAG 출처 카탈로그, F-18 다차원 분류 설계, 사후관리 sp_0014 수정

### 수행

**sp_0014 수정**
- `support_program_master.csv`: 생계급여·긴급복지 연계 `service_category` → `사후관리`에서 `별도_지원`으로 수정 (이미지 표 12 "별도 지원" 항목으로 분리)
- `DATA_SCHEMA.md §4.9`: `별도_지원` enum 값 추가 (사후관리 = 지역기반 관계 형성·자조모임 운영만)

**F-18 군집 분류 로직 개선 (FEATURE_SPEC.md)**
- 기존 단순 총점 구간 → 다차원 판별 규칙으로 교체
- 차원: D_관계망(max 12) · D_활동(max 6) · D_노동경제(max 6) · D_자기관리(max 3)
- 의사결정 트리: ① 은둔청년(D_관계망≥8 AND D_활동≥5) → ② 활동제한형(D_관계망≥6) → ③ 활동형(D_노동경제≥3) → 고립위험
- 유효성 검증 계획 추가: Cronbach's α · EFA · k-means 실루엣 · Cohen's κ (목표 기준 명시)

**RAG_PIPELINE.md §17 신규 추가**
- 출처 카탈로그(doc_support_001~007): 한국보건사회연구원·서울시·여성가족부·생명의전화 실무 가이드북 포함
- chunk 필수 provenance 필드: doc_title, doc_agency, doc_pub_year, doc_page, doc_section
- 출처 표시 형식: `[출처] {doc_title} ({doc_agency}, {doc_pub_year}), p.{page}`
- 이미지 표 12 원출처(청년이음센터 2021 가이드북)도 doc_support_006으로 등록

### 근거
- 사후관리는 지역기반사회적관계형성프로그램참여·자조모임운영및참여만 해당 (이미지 표 12 직접 확인)
- F-18 분류 이론 근거: 고립은둔 청년 지원사업 모형 개발 연구(한국보건사회연구원 2022), 서울시 실태조사, 생명의전화 가이드북 2021

## 2026-06-30 — 지원 제도(SupportProgram) 스키마 및 마스터 데이터 추가

### 수행

**DATA_SCHEMA.md 확장**
- §4.8~4.11: `target_group_type`, `service_category`, `lifecycle_phase`, `support_strategy` enum 추가
- §4.3: relation_type에 `support_program_to_target_group`, `support_program_to_risk_stage` 추가
- §5.8: `TargetGroup` 엔티티 정의 (대상 유형 5종)
- §5.9: `SupportProgram` 엔티티 정의 (16개 지원 제도)
- §6.13~6.14: 두 새 relation 스키마 정의

**신규 master CSV (data/processed/master/)**
- `target_group_master.csv` — 5행: 고립위험청년·활동형·활동제한형·은둔청년·가족. `mapped_risk_stage_ids` 컬럼으로 risk_stage 직접 참조
- `support_program_master.csv` — 16행: 이미지 표 12 기준 서비스 항목. `service_category`, `lifecycle_phase` 1차 분류 적용

**신규 relation CSV (data/canonical/relations/)**
- `support_program_target_mapping.csv` — 40행: 지원 제도 ↔ 대상 유형 다대다 매핑
- `support_program_risk_stage_mapping.csv` — 62행: 지원 제도 ↔ 위험군 단계 매핑 (target_group의 mapped_risk_stage_ids에서 파생)

**FOLDER.md 갱신**: `data/processed/master/FOLDER.md`, `data/canonical/relations/FOLDER.md`

### 근거
이미지 표 12 (지원 대상 유형 및 지원목표에 따른 핵심 서비스) 기준. `service_category`(자기이해_및_심리상담/치유적_관계형성/일_경험_및_사회활동/사후관리)가 1차 분류, `target_group_type`이 대상 분류.

---

## 2026-05-27 — Schedule 페이지 빈도 라벨 중복 렌더 버그 수정

### 수행

**버그 수정**

- `frontend/src/pages/Schedule/index.tsx` — `CertInfoRow`에서 `exam_frequency` 칩이 `"연 연 3회회"`로 이중 렌더되던 문제 수정
  - 원인: `data.exam_frequency`는 backend(`backfill_cert_master.py`)에서 이미 `"연 3회"` 형태 완성 문자열로 내려오는데, 프론트가 다시 `연 {freq}회`로 감쌌음
  - 수정: `exam_frequency`(문자열)는 그대로 출력하고, `exam_sessions_per_year`(숫자) fallback일 때만 `연 N회`로 포맷하는 `freqLabel`로 분리
  - 영향 범위: Schedule 페이지 카드의 보라색 빈도 chip만 변경. Recommendation/Roadmap은 이미 raw 출력 방식이라 무관

---

## 2026-05-15 — Recommendation 패널 UX 개선 + exam_type_info 연동 + 루트 문서 갱신

### 수행

**버그 수정**

- `frontend/src/pages/Recommendation/index.tsx` — `fetchEvidence` useCallback deps 배열 TDZ 버그 수정
  - 원인: `useCallback` deps에 이후 선언된 `const` (`fetchSessionRates`, `fetchCertJobs`, `fetchCertInfo`, `fetchCertStats`, `fetchExecData`)가 포함 → React 렌더 시 TDZ ReferenceError → 페이지 완전 공백
  - 수정: deps를 `[stageParam, domainParam, allCerts]`로 축소 (이 함수들은 `[]` stable refs라 deps 생략 safe)

**프론트엔드 (`frontend/src/pages/`)**

- `Recommendation/index.tsx`
  - Exec 패널: 탭 조건부 렌더링 → 항상 표시되는 stacked 섹션으로 전환 (시험 일정 / 채용공고 / 훈련과정 / 자격 정보 4개 섹션)
  - `CertStatsData` 인터페이스에 `exam_type_info`, `exam_subject_info` 추가
  - "시험 구성" 초록 chip 추가: `exam_type_info` 값(필기+실기, 필기+실기+면접 등) 표시
  - 데이터 출처 배너 제거 (data-src-footer), 출처 표기를 "한국산업인력공단" 단순 텍스트로 간소화
  - CSS: `.exec-section`, `.exec-section-title`, `.exec-loading`, `.exec-empty`, `.certinfo-stat-type` 추가
- `Schedule/index.tsx`
  - empty-tier 자격증 뱃지 레이블 수정: "공인민간" → "국가자격" (1,290개 모두 Q-Net 등록 국가자격)
  - 부제목·힌트 텍스트에서 "공인민간자격" 제거, "(Q-Net 데이터 기반)" 명시
- `Jobs/index.tsx` — 데이터 출처 배너 제거
- `Explore/index.tsx` — 데이터 출처 배너 제거

**백엔드 (`backend/app/services/`)**

- `cert_info_service.py` — `_load_cert_master_details()`에 `exam_type_info` 필드 추가, `get_cert_master_stats()` 응답에 포함
- `llm_roadmap_service.py` — `_enrich_cert_context()`: `exam_type_info` 컨텍스트 주입 (step 3 신설). `explain_cert()` 프롬프트에 "시험 구성 항목에 없는 시험 방식 절대 언급 금지" 규칙 추가

**문서 갱신**

- `README.md`: 최종 수정일 2026-05-15, API 상태 reserved→실연동, 구현완료 항목 갱신 (Q-Net/WorkNet/Work24/YouTube/서울시 공공 API, DB 1,290종)
- `SUMMARY.md`: 3.4 exec 패널 섹션 반영, 데이터 소스 표 갱신 (1,290행, 외부 API 추가), API 요약 표 갱신, Reserved에서 시험일정 제거
- `PROJECT_SUMMARY.md`: 기술 스택 표 갱신 (외부 API 명시), reserved 목록 현행화, 9절 구현 단계 요약 갱신

### 핵심 결정

- exam_type_info 기반 시험 구성 chip: cert_master.csv 원본 값을 그대로 노출 (자유 문자열 생성 금지 정책 일관 유지)
- AI 프롬프트 시험 방식 제약: "시험 구성" 컨텍스트에 없는 필기/실기/면접 언급을 하드 금지 — 데이터 없는 자격증에서 잘못된 시험 방식 노출 차단
- empty-tier 뱃지 "국가자격" 통일: 실제 데이터가 전부 Q-Net 등록임을 코드에 반영 (공인민간자격과 혼동 방지)

---

## 2026-05-14 — Execution Layer 전면 활성화 + 루트 문서 정렬

### 수행

**신규 서비스 구현 (모두 `backend/app/services/`)**

- `cert_lookup_service.py` — cert_id → NCS → WorkNet/Work24 파라미터 파생 중심 서비스
  - `NCS_TO_WORKNET_OCCUPATION` 매핑 테이블 (NCS 대직무코드 → WorkNet 직종코드)
  - `_get_ncs_level1_frequency()`: cert_id의 NCS 매핑에서 대직무코드 빈도 Counter 기반 정렬 (가장 연관성 높은 코드 우선)
  - `get_worknet_search_params()`, `get_training_search_params()` — 각 API 파라미터 세트 자동 생성
  - `get_cert_summary()` — cert + NCS + 직무 + API 파라미터 종합 요약
- `exam_schedule_service.py` — Q-Net 시험·접수 일정 조회, D-Day 계산
- `jobs_service.py` — WorkNet 채용정보 (XML), 고용24 직업정보 CSV 조회
- `training_service.py` — Work24 훈련과정 (XML), 과정평가형 자격 (Q-Net JSON)
- `seoul_service.py` — 서울시 공공데이터 (일자리카페·건강증진센터·공공예약)
- `action_service.py` — 위험군 단계별 오늘의 한 가지 행동 제안 (5단계 × 다유형 템플릿)

**신규 라우트 등록 (`backend/app/api/v1/routes/`)**

- `jobs.py`: `GET /jobs/hiring`, `GET /jobs/hiring/by-cert/{cert_id}`, `GET /jobs/cert-summary/{cert_id}`, `GET /jobs/detail`
- `training.py`: `GET /training/courses`, `GET /training/courses/by-cert/{cert_id}`, `GET /training/process-eval`
- `seoul.py`: `GET /seoul/job-cafes`, `GET /seoul/health-centers`, `GET /seoul/reservations`
- `action.py`: `GET /actions/today`
- `schedule.py` — 501 stub → Q-Net API 실연동으로 전환

**설정 변경 (`backend/app/core/config.py`)**

- 신규 API 키 필드 추가: `hrdkorea_api_key_in/de`, `get_job_api_key`, `get_training_api_key`, `seoul_api_key/2/3`, `career_net_api_key`
- 각 외부 API별 timeout 설정 필드 추가

**버그 수정**

- `cert_lookup_service.py` NCS 우선순위 버그: `정보처리기사`에서 `정보통신(20)`이 아닌 `법률(05)`가 반환되던 문제
  - 원인: `get_cert_ncs_rows()`가 35개 중복 NCS 행을 반환하고, Counter 없이 첫 번째 코드를 사용
  - 수정: Counter 기반 빈도 분석 → 가장 많이 매핑된 대직무코드를 1순위로

**문서 갱신**

- `API_SPEC.md`: 11 → 24+ 엔드포인트, F-12~F-19 추가, §9 reserved 섹션 삭제
- `SYSTEM_ARCHITECTURE.md`: Execution Layer 섹션 추가, §7 서비스 목록 갱신, §14 활성/reserved 범위 갱신, §19 최종 요약 4개 계층으로 업데이트
- `PRD.md`: §9.1~9.2 완료 표시, §10 비범위에서 완료 항목 제거, §18 최종 요약 갱신
- `FEATURE_SPEC.md`: F-08/F-09 reserved→활성, F-12~F-16 신규 추가, §3/§4/§8/§10 갱신
- `backend/app/services/FOLDER.md`: 신규 서비스 6개 추가
- `backend/app/api/v1/routes/FOLDER.md`: 신규 라우트 4개 추가, schedule.py 활성 상태로 갱신

### 핵심 아키텍처 결정

- cert_id → NCS → API 파라미터 데이터 체인을 `cert_lookup_service`가 단일 진입점으로 관리
- WorkNet/Work24는 직접 문자열 매칭 금지 — canonical CSV 관계만 사용
- NCS 대직무코드 빈도 기반 우선순위: 한 cert에 여러 NCS가 매핑된 경우 가장 빈도 높은 대직무코드를 API 파라미터 1순위로 사용

---

## 2026-05-09 — 백엔드 Render 배포 완료

### 수행

- **Render Web Service 생성**: `Vulnerable_Groups_RAG` 서비스
  - Root Directory: (비움 — 저장소 루트 기준)
  - Build Command: `pip install -r backend/requirements.txt`
  - Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **배포 URL**: `https://vulnerable-groups-rag.onrender.com`
- **환경변수 설정**: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_TABLE_NAME`, `SUPABASE_MATCH_RPC`, `EMBEDDING_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL` 등 주입 완료
- **최초 배포 실패 원인**: Root Directory를 `backend`로 설정했을 때 `from backend.app...` import 경로 불일치 → Root Directory 제거 후 해결

### 프론트 배포 시 추가 필요 작업

- `frontend/vercel.json` 생성 완료: `/api/*` → Render 프록시 + SPA fallback 포함
  - `VITE_API_BASE_URL` 환경변수 불필요 (vercel.json 프록시로 대체)
- 프론트 배포 후 Render 환경변수 `CORS_ORIGINS`에 Vercel 배포 URL 추가 필요
  - Settings → Environment → `CORS_ORIGINS` 값에 `,https://<your-app>.vercel.app` 추가

### 검증

- `https://vulnerable-groups-rag.onrender.com/api/v1/health` 에서 응답 확인 필요

---

## 2026-05-07 — 핵심 3단계 플로우 기준으로 기획 문서 전면 정렬

### 변경 문서
- `README.md`: 핵심 3단계 사용자 흐름(설문→도메인+직무선택→로드맵) 명시, 설문 방식·Safety Override 표기 추가, 온라인 서빙 계층 표 추가
- `PRD.md`: §2 제품 정의에 3단계 흐름 블록 추가, §7.1에 12문항 설문 구조표·Safety Override 명시, §8.1 설문 방식 명시, §11 시나리오 1을 3단계 순서 흐름으로 재작성
- `SYSTEM_ARCHITECTURE.md`: §6 Frontend 활성 범위에 InterestSelection 추가, 핵심 3단계 흐름도 추가, §12 Online Runtime Flow를 3단계 흐름으로 재작성
- `FEATURE_SPEC.md`: F-01을 "12문항 설문 방식" 명세로 전면 재작성(카테고리별 문항표·Safety Override·판정 로직), F-02를 "InterestSelection" 명세로 재작성(도메인 필수·직무 선택·URL 파라미터 전달), 기능 목록 테이블 업데이트

### 배경
- 실제 구현된 웹 플로우(RiskAssessment → InterestSelection → Roadmap)와 기획 문서 간 불일치 발견
- 특히 SYSTEM_ARCHITECTURE.md에 InterestSelection 페이지 누락, F-01·F-02 명세가 설문 방식과 도메인+직무 동시 선택 방식을 반영 안 함
- 사용자 확인 요구: "설문→진단→직무+도메인선택→로드맵 추천" 3단계 플로우가 맞는지 검토 후 문서 전면 업데이트

### 잔여 이슈 (코드 변경 필요)
- InterestSelection 직무(job) 선택 UI 미구현 → F-02에 "추가 구현 필요"로 표기
- components/Survey.tsx 미사용 파일 (RiskAssessment/index.tsx가 설문 직접 포함) → 별도 정리 필요
- Home 이용 흐름이 4단계로 표시 → 3단계 기준으로 UI 수정 검토 필요

---

## 2026-04-27 — 앱 진입 설문 12문항 + 1~5단계 위험도 스코어링 설계

### 개요
- 산출물 위치: `experiments/reports/2026-04-27_isolation_survey_design/` (입구는 `00_README.md`)
- 입력: `data/raw/csv/★TABLE_서울시 고립은둔청년 실태조사(청년조사)_전체_v1_230127.xlsx` (cross-tab, n=5513, 고립은둔 486 / 미해당 5027)
- 목적: B-01 위험군 자동 스코어링 부재(2026-04-27 운영 관찰)에 대응할 통계 근거 기반 설문/스코어링 초안.

### 분석
- 138문항 전체에 대해 옵션 단위 Cohen's h 와 문항 단위 max\|h\|·JS divergence 산출 (`discrim_full.json`).
- 변별력 1위 `A13_4` 직장·학교·동네 사람 대면 교류 max\|h\|=1.250, 정서지지 4문항 모두 max\|h\| ≥ 0.92.

### 설문 12문항
- 차원 7개(외출·교류 양·물리적 대면교류·정서적 지지·외로움·우울·자살사고·자기관리·가족·노동)를 커버하도록 12문항 선정.
- 각 문항에 옵션 단위 정수 점수(0~6) + 문항 가중치(=max\|h\|, Q9는 안전 가중 1.5배). 가중치 합 ≈ 10.34, 이론 최대 점수 ≈ 51.77.
- 5단계 컷오프(시뮬레이션 분포 기반): s1=12.71 / s2=18.21 / s3=29.62 / s4=35.55. Q9 ≥ 5인 경우 stage = max(stage, 4) safety override.

### 검증 결과
- 합성 응답자 시뮬레이션(고립 2,000 / 비고립 8,000, 문항 독립 가정).
- AUC 0.9915 (상한 추정), 평균 점수 차이 16.54점.
- 단계 분포: 비고립군 stage 1·2 = 90% / stage 4+ = 0%, 고립군 stage 3+ = 98.3% / stage 4+ = 50%.
- 한계: 독립 가정 → 실제 운영 AUC 0.85~0.95 예상. 라벨이 A7을 사용해 부여된 부분적 순환. PRD §7.1 stage 2~4 의미는 reserved 유지(컷오프는 후보값).

### 후속
- `02_survey_selection_rationale.md` §4 표를 `FEATURE_SPEC.md` 진입 설문 명세로 인용·승격 (B-01 P0).
- `03_scoring_design.md` §6 의사 코드를 `risk_stage_service` 입력 파라미터로 인입.
- 운영 응답 200~500건 모이면 컷오프 재추정. 새 날짜 폴더(`yyyy-mm-dd_isolation_score_retune/`)로 비교 분석 추가.
- 메타데이터: 본 폴더 보고서 md 5종은 SHA256 실계산값 기입(CLAUDE.md §11.4 준수). `FOLDER.md` 2개는 placeholder TBD 상태로 두며 후속 빌드에서 실해시로 교체.

---

## 2026-04-27 — backend/README 병목 리스트 추가 (운영 관찰)

### B-01~B-12 병목 정리
- 사용자 요청(위험군 1~5단계 자동 분류 가능 여부 + 시나리오별 쿼리 결과 + 파이프라인 병목 리스트)에 대응해 `backend/README.md` 끝에 §"파이프라인 병목"을 신설.
- 핵심 식별: B-01 위험군 자동 스코어링 부재(설문 CSV 미적재 + 스코어링 로직 0건, 프론트는 라디오), B-02/B-03 major_name·자유 텍스트 → domain_ids 정규화 계층 부재, B-04~B-08 추천/로드맵/RAG 단계 결함, B-09~B-12 정책 미확정·관측성 부채.
- 시나리오 추적 메모(2단계 전자공학/3단계 산업데이터공학/5단계 컴퓨터·IT) 표로 첨부. 실제 검증은 `scripts/eval_golden_set.py` 페르소나 추가로 일원화 권장.
- 본 작업은 운영 관찰 기록일 뿐이며 정책·구현 변경 없음. 후속 P0 항목(B-01~B-03)은 `PRD.md`/`FEATURE_SPEC.md`/`DATA_SCHEMA.md` 선수정 후 코드 수정.
- 메타데이터: `backend/README.md` 최종 수정일 2026-04-27, 문서 해시 SHA256:TBD (CLAUDE.md §11.4 placeholder 규칙 준수).

---

## 2026-04-19 — eval runner + bottleneck tier-relative + job_to_domain (R4)

### R4-1 — 골든셋 자동 평가 runner (`eval_golden_set.py`)
- `scripts/eval_golden_set.py` 신규 작성. 6 persona × evaluation_criteria 패턴 매칭(18개 패턴 정의).
- 구조적 체크(expected_entry_stage, entry_advanced, fallback_used, total_certs) + Jaccard + criteria 자동 검증.
- P21 hard-fail: J=0.33 → A1 이후 top-10 전부 기능사로 변경된 것 확인. `golden_set.jsonl` expected_cert_ids 갱신 후 J=1.00, P21 100%.
- 최종 PASS RATE 95.7% (P15 1건 FAIL 잔존 — stage_0005 tier 필터 미적용, R5 대상).
- 실행: `python scripts/eval_golden_set.py [--persona P21] [--fail-fast]`

### R4-3 — `is_bottleneck` tier-relative 판정
- `recommendation_service.py`에 `_BOTTLENECK_TIER_THRESHOLD` 추가: 기능사 20%/산업기사 15%/기사 10%/기술사·기능장 5%.
- `_build_roadmap_sequence` 내 is_bottleneck 계산 2곳 교체.
- 검증: 발송배전기술사(기술사, 1.9%) → bottleneck ✅. P21 기능사(45-65%) → bottleneck=0건 유지 ✅.

### R4-6 — `job_to_domain.csv` 런타임 통합
- `_JOB_TO_DOMAIN` 경로 상수 + `_load_job_to_domain_map()` 함수 추가.
- `recommendations()` job-only 쿼리(domain_ids 빈 경우)에 domain_ids 자동 확장.
- `_invalidate_caches()`에 추가. 검증: job_0001 → domain_0001, total_certs=10 확인.

---

## 2026-04-19 — cert_to_cert_relation 버그 수정 + 방향 guard (R3: A1 + N6)

### A1 — `_RELATION_TYPE_MAP` 오매핑 제거
- `scripts/build_cert_to_cert_relation.py`에서 `_RELATION_TYPE_MAP = {"recommended_prior": "next_step", ...}` 딕셔너리 제거.
- `_load_prereq_rows()`의 `relation_type` 할당을 `r.get("relation_kind", "next_step")` 직접 사용으로 교체.
- 결과: NCS 775행 중 666행이 `next_step` → `recommended_prior`로 올바르게 복원. path_score 가중치 0.50→0.80 회복.
- P21 검증: `cert_paths[0].path_score = 0.9485` (> 0.78 기준 통과).

### N6 — `_TIER_ORDER` 기반 역방향 행 자동 swap/drop 빌드 가드
- `_cert_tier_map()` 함수 추가 (cert_id → cert_grade_tier).
- `build()`에 tier 비교 로직 추가: from_tier > to_tier 시 swap, 동일 tier 시 drop.
- 재빌드 결과: total 999행 (active 775 / inactive 224), swapped=8, dropped=19 (모두 parse_ir 단독).
- `data/canonical/relations/FOLDER.md` §2 파일 테이블 업데이트 (1,018→999, 설명 갱신).

---

## 2026-04-18 — 증분·게이트 3종 (C1/C2/C3)

### C2 — candidate 빌드 taxonomy 게이트 (build-time strict)
- `DATA_SCHEMA.md §9.1.1` 신설: `primary_domain` / `related_domains`는 `domain_master.csv`의 `domain_sub_label_id`, `related_jobs`는 `job_master.csv`의 `job_role_id` 집합에만 속해야 함.
- `scripts/build_cert_candidates.py`에 master CSV ID 기반 검증 단계 추가. 위반 시 기본 실패(exit 1), `--allow-violations`로 우회.
- 위반 리포트: `data/canonical/validation/candidates_taxonomy.json`. 현 데이터 1290/1290 통과 — 회귀 가드.
- `backend/canonical/candidate_jsonl.py` docstring 보정 (라벨 텍스트가 아닌 master CSV ID 기준임을 명시).

### C1 — embed 단계 증분 (manifest 기반)
- `backend/rag/ingest/cli.py`를 `PipelineManifest.is_embed_stale`와 연동. `embed_key_hash = chunk_hash + embed_version` 기준 스킵.
- `--force` 플래그로 전체 재임베딩 가능. 적재 직후 `update_embed` → manifest 저장.
- `RAG_PIPELINE.md §16.3` 신설로 계약 문서화. `embed_version` 상승 시 일괄 stale 동작 명시.

### C3 — candidate build row-level 증분 (content_hash diff)
- `scripts/build_cert_candidates.py`가 실행 시마다 `data/canonical/candidates/.build_manifest.json`(`{candidate_id: content_hash}`)을 읽고 `added/updated/removed/unchanged` diff를 stdout으로 출력, manifest를 갱신.
- downstream 인덱스 업데이트는 이 manifest를 읽어 **바뀐 candidate만** 반영하도록 설계(§7.6.1). 두 번째 실행에서 1290 unchanged 확인.
- `HASH_INCREMENTAL_BUILD_GUIDE.md §7.6.1` 보강, 후보 폴더 `FOLDER.md` 갱신.

---

## 2026-04-14 — 핵심 아키텍처 결정: cert_grade_tier 정렬 + 선수과목 DAG 로드맵

### 배경

청크·추천 테스트 및 고도화 논의 과정에서 두 가지 구조적 설계 결정을 확정.

### 결정 사항

**결정 1: cert_grade_tier 기반 위험군 연동 정렬**
- 위험군 단계가 높을수록(4~5단계) 기능사·산업기사를 우선 추천하고, 기사·기술사는 후순위로 자동 조정한다.
- Certificate 엔티티에 `cert_grade_tier` 필드 추가 (`DATA_SCHEMA.md` §4.7, §5.3).
- 정렬 로직은 Recommendation Core 계층이 담당 (`SYSTEM_ARCHITECTURE.md` §8, §17 결정 8).
- FEATURE_SPEC.md F-03 처리 규칙에 정렬 기준 명시.

**결정 2: 선수과목 DAG 순회 로드맵 생성**
- flat list 대신 `cert_prerequisite` 관계(`DATA_SCHEMA.md` §6.8)를 방향 그래프(DAG)로 순회하여 로드맵 경로를 생성한다.
- 사용자 현재 위치에서 실제 이동 가능한 경로만 로드맵 단계 후보로 제시한다.
- FEATURE_SPEC.md F-05 처리 규칙에 DAG 순회 원칙 명시.
- `SYSTEM_ARCHITECTURE.md` §8 원칙, §17 결정 9에 반영.

### 수정 문서

- `DATA_SCHEMA.md`: §4.3에 `cert_to_cert_prerequisite` 추가, §4.7 `cert_grade_tier` enum 신규, §5.3 Certificate에 `cert_grade_tier` 필드 추가
- `FEATURE_SPEC.md`: F-03 처리 규칙에 tier 정렬 규칙 추가, F-05 처리 규칙에 DAG 순회 원칙 추가
- `SYSTEM_ARCHITECTURE.md`: §8 Recommendation Core 원칙에 두 결정 추가, §17 핵심 아키텍처 결정에 8·9번 추가

### 의도적으로 하지 않은 것

- cert_grade_tier 실제 값 채우기(CSV canonicalization 단계에서 수행)
- DAG 순회 구현 코드(구현은 다음 스프린트)
- feasibility_score, prerequisite_met 등 파생 필드 설계(후속 단계)

---

## 2026-04-03 — 정책: 준비만·실행 비강제 (추천 API 스텁 복귀)

### 배경

제품 단계를 **파이프라인 실행이 아니라 준비(계약·예시·문서)** 로 둔다.

### 수행

- **`POST /recommendations`**: JSONL 로더·`backend/canonical/*` 구현 **제거**, `NOT_IMPLEMENTED` 스텁 복귀(`details.prep`에 준비 참조 링크).
- **설정**: `candidates_jsonl_relative` 등 추천 전용 필드 **제거**.
- **문서**: `API_SPEC.md` §6·§7.2, `FEATURE_SPEC.md` F-03, `PROJECT_SUMMARY.md` §8~§9 — “실행 안 해도 됨”·스텁 명시.
- **`candidates.jsonl.example`**, 스키마·§8 표는 **준비물로 유지**.

### 과거 시도(참고)

- 동일 날짜에 잠시 JSONL 로더를 넣었으나 본 정책에 맞춰 되돌림.

---

## 2026-04-03 — 파이프라인 준비 전제(데이터 수집 후) 명시

### 수행

- **`PROJECT_SUMMARY.md`**: §8 레인별 준비 표·§9 구현 성숙도·§10 결론 번호 정리. “수집만으로 전 레인 자동 완주”가 아님을 명시.
- **`SYSTEM_ARCHITECTURE.md`**: §13.4 `PROJECT_SUMMARY` §8·§9 단일 참조.
- **`RAG_PIPELINE.md`**: §16.2 인제스트·Evidence 직전 체크리스트(cert_id·차원·재인제스트·증분).
- **`DATA_SCHEMA.md`**, **`API_SPEC.md`**: 현행 Evidence 필터와 `metadata.cert_id` 정합.
- **`chunk_loader.py`**: docstring 정합.
- **`data/index_ready/chunks/chunks.jsonl.example`**: JSONL 1줄 샘플.
- **`docs/architecture/supabase_langchain.sql`**: 재인제스트 중복 주석.
- **`data/index_ready/chunks/FOLDER.md`**, **`backend/README.md`**: 예시·요약 링크.

---

## 2026-04-03 — 아키텍처 문서 정렬·루트 md 문서 해시

### 수행

- **`SYSTEM_ARCHITECTURE.md`**: §3.4는 §14·`RAG_PIPELINE.md` §15로 위임(중복 목록 제거), §9에 parse IR(`RAG_PIPELINE.md` §6.7)·문서형 chunk(`DATA_SCHEMA.md`) 교차 참조.
- **누락 메타**: `API_SPEC.md`, `PROMPT_DESIGN.md`, `ROOT_DOC_GUIDE.md`, `HASH_INCREMENTAL_BUILD_GUIDE.md`에 `문서 해시` 줄 추가.
- **루트 `*.md`**: 메타데이터 영역(첫 `## ` 이전)에서 `문서 해시`·`최종 수정일` 줄을 제외한 본문 기준으로 SHA256 재계산 → `scripts/maintenance/update_root_md_hashes.py`로 일괄 반영(하위 `FOLDER.md`는 제외).

---

## 2026-04-03 — RAG 보완(문서만): Parse 순서·IR 계약·평가 후보

### 수행

- **`RAG_PIPELINE.md`**: §6.0 Parse 실행 순서, §6.7 parse IR 최소 계약(청크 빌더 입력), §10.3 스토어 구현 vs 계약 구분, §13.3 질의 확장 reserved(MVP 비적용 명시), §15 reserved에 코퍼스 감사·rate limit 후보.
- **`DATA_SCHEMA.md`**: `SourceDocument`에 `file_hash`·`fetched_at`, §5.6·§11과 `RAG_PIPELINE` §6.7 역할 분리 명시, 메타데이터 블록에 `문서 해시` 줄 추가.
- **`EVALUATION_GUIDELINE.md`**: §4 Parse·인덱스 품질 측정 후보 표(채택 전).

### 비적용(의도적)

- HyDE·다단계 pre-retrieval·vendor 전환 등은 제품 목적·MVP 범위 밖이거나 별도 계약 필요 → 문서에 **reserved/후속**만 명시.

---

## 2026-04-03 — RAG 심화 참고(로컬) 정리

- 루트 문서: 인덱싱·Pre-retrieval **축 설명**만 유지, **특정 파일명·경로**는 적지 않음. 계약은 `RAG_PIPELINE.md` 우선, reserved는 범위 자동 확장 금지.
- `.gitignore`: `docs/references/_private/` 무시(개인·팀 미공유 참고 자료용).

---

## 2026-04-03 — 데모 제출용 임시 절 (PRD §19, FEATURE_SPEC §11)

### 수행

- **PRD.md**: `문서 해시` 줄 추가; **§19 데모 제출용 범위·단계 (임시)** — 목적, 최소 시연 흐름, 얇게 둘 항목, D1~D6 체크리스트, 데모 완료 조건, 제출 후 조치.
- **FEATURE_SPEC.md**: `문서 해시` 줄 추가; **§11 데모 제출용 기능 단계 (임시)** — 단계·F-xx 매핑, 허용 스텁, 금지, 제출 후 정리.

---

## 2026-04-03 — 리프 폴더 `FOLDER.md` 스캐폴드 명시서

### 수행

- **`FOLDER.md`**: `docs/`, `data/`(리프), `frontend/src/`(리프), `scripts/*`, `experiments/*`, `infra/*`, `shared/*`, `data/taxonomy` 등 **63개** 리프 경로에 동일 메타데이터 양식(루트 md와 계열)으로 용도·금지·연계·비고 기술.
- **`scripts/maintenance/generate_folder_md.py`**: 위 경로 일괄 생성기. 저장소 루트는 `DIRECTORY_SPEC.md` 존재로 탐색.
- **`DIRECTORY_SPEC.md`**: §7 원칙 8번·§8 요약에 `FOLDER.md` 규칙 반영.

---

## 2026-04-03 — PROJECT_SUMMARY 및 청킹·레퍼런스 문서 위치 안내

### 수행

- **신규** `PROJECT_SUMMARY.md`: 프로젝트 목적, CSV vs 문서 레인, 스택·폴더 요약, 문서 지도, 청킹 절차(`RAG_PIPELINE.md` §7 연계, `chunks.jsonl`·인제스트 CLI), 긴 방법론 문서는 `docs/references/` 권장.
- **README.md**, **DIRECTORY_SPEC.md** §2·§3, **ROOT_DOC_GUIDE.md** §3·§4.1: `PROJECT_SUMMARY.md` 링크·트리 반영.

---

## 2026-04-03 — 문서·디렉터리 정렬 및 최소 스캐폴딩

### 수행

- **DIRECTORY_SPEC.md**: §2 루트 트리에 `ROOT_DOC_GUIDE.md`, `HASH_INCREMENTAL_BUILD_GUIDE.md` 추가; §3에 해당 파일 역할 및 Cursor 규칙(`.cursor/rules/`) 안내; §5 권장 루트 파일 목록 동기화; 문서 해시 라인 추가.
- **신규 루트 문서**: `EVALUATION_GUIDELINE.md`(10), `EVALUATION.md`(11), `EXPERIMENT_GUIDE.md`(12), `ERROR_ANALYSIS.md`(13), `DEV_LOG.md`(14) — 메타데이터 및 `SHA256:TBD`.
- **README.md**: 문서 해시 라인; §5 표에 `ROOT_DOC_GUIDE`, `HASH_INCREMENTAL_BUILD_GUIDE`, Cursor 규칙 위치; §7 트리 동기화.
- **Git**: `gitignore` → `.gitignore` 로 이름 정리(내용 유지).
- **디렉터리**: `docs/*`, `data/raw|canonical|index_ready|processed` 하위(기존 `data/taxonomy/*.txt` 유지), `experiments/*`, `infra/*`, `shared/*` — 비어 있는 leaf에는 Git 추적용 `.gitkeep`만 둠(데이터 파일 아님).
- **frontend**: `DIRECTORY_SPEC` §4.3 트리 + 각 leaf `.gitkeep`, `frontend/README.md`(후속 Next/Vite 안내).
- **backend**: FastAPI `backend.app.main:app`, `/api/v1/health` 활성(envelope 준수); `recommendations`/`roadmaps`/`admin`/`risk/stages`는 `NOT_IMPLEMENTED` envelope; 일정·링크 라우트는 HTTP **501** + envelope; `backend/rag/*`, `backend/canonical/*`, `services`, `requirements.txt`, `backend/README.md`, `backend/tests/test_health.py`.
- **scripts**: `parse`, `canonicalize`, `build_entities`, `build_relations`, `build_candidates`, `evaluation`, `maintenance` 각 `run.py` 스텁.

### 검증

- `PYTHONPATH=<저장소 루트>` 기준 `pytest backend/tests -q` — `test_health_ok` 통과.

### 의도적으로 하지 않은 것

- `risk_stage_master.csv` 및 기타 원본·taxonomy 파일의 임의 생성·더미 row
- raw PDF/HTML/CSV/API 실파일 추가
- reranker, BM25 상시, 일정 API 실연동, 프론트 완성 UI
- `docs/references` 내 참고 자료는 사용자 수동 배치

---

## 2026-04-03 — 스택 정렬 (Vite·LangChain·Supabase·파이프라인 연결)

### 수행

- **프론트**: React 19 + Vite 6 + TS — `frontend/package.json`, `vite.config.ts`(`/api`→8000 프록시), `src/` 홈에서 헬스 호출.
- **백엔드**: `pydantic-settings` 기반 `backend/app/core/config.py`, CORS, `POST /api/v1/recommendations/evidence` + `retrieval_service` + LangChain `SupabaseVectorStore` 경로(`backend/rag/store/supabase_vector.py`).
- **인제스트**: `backend/rag/ingest/chunk_loader.py`, `python -m backend.rag.ingest.cli` (JSONL만 사용, 더미 데이터 생성 없음).
- **SQL 템플릿**: `docs/architecture/supabase_langchain.sql`.
- **환경 템플릿**: `infra/env/.env.example`; `.gitignore`에 `!.env.example` 예외.
- **LlamaIndex**: `backend/rag/llamaindex/` 자리만.
- **문서**: `RAG_PIPELINE.md` §16.1, `SYSTEM_ARCHITECTURE.md` §2.1 스택 문단, `README.md` §10, `backend/README.md` / `frontend/README.md` 갱신.

### 검증

- `pytest backend/tests` (health + evidence missing cert_id).
- `frontend` `npm run build`.

---

## 2026-04-03 — CSV 담당 팀 지침서

- 루트에 `CSV_CANONICALIZATION_TEAM_GUIDE.md` 추가 (영민·유빈: 데이터 수집 슬라이드·Parse 슬라이드 기준 CSV 레인 전담 절차).
- `README.md` §5 표에 해당 문서 링크 한 줄 추가.



넌 당신은 Level2-4가 아니고 예를 들어 보기 좋게 3단계 군으로 자격증 난이도 60%  이상 자격증이 추천되며 취업 연관이 높은 자격증이 추천됩니다. 이런 자격증이
  나온 이유는 ~~~ 입니다. (ex 합격률이 67% 이며, 희망 분야와 연관성이 평균에 비해 27%높으며, [네이버, 카카오뱅크, .... 등 실제 시간에 맞게 채용 중인 공고들
  분석 후] 채용 공고 에서 많이 요구되는 자격증입니다. 그래서 추천했습니다.) 라고 나오면 좋겠어.