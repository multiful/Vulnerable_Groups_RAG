# FOLDER.md

> **파일명**: FOLDER.md
> **폴더 경로**: `docs/evaluation/`
> **최종 수정일**: 2026-07-05
> **문서 해시**: SHA256:TBD
> **문서 역할**: 추천 시스템 평가·골든셋 구축 산출물
> **문서 우선순위**: reference
> **연관 문서**: EVALUATION.md, EVALUATION_GUIDELINE.md, FEATURE_SPEC.md

---

## 1. 용도

추천 파이프라인의 품질 검증에 쓰이는 페르소나·베이스라인·골든셋 파일을 둔다.

---

## 2. 파일 목록

| 파일 | 설명 | 상태 |
|---|---|---|
| `personas.json` | 15개 대표 페르소나 — API 요청 본문 + 기대 결과 명세 | ✅ |
| `baseline_results.json` | 5개 핵심 페르소나 베이스라인 결과 (2026-04-18 생성) | ✅ |
| `golden_set.jsonl` | 5개 베이스라인 기반 초기 정답셋 (전문가 검토 필요) | ✅ 자동생성본 |
| `audit_integrity.md` | 데이터 무결성 감사 결과 | ✅ |
| `llm_judge_golden_set_2026-07-05.jsonl` | 신규 6개 페르소나 — GPT-4o-mini LLM-as-a-Judge 정답지 v1. **방법론 결함 있음**(§5 참고, `claude_judge_golden_set_2026-07-05.jsonl`로 대체) | ⚠️ 결함 있음 — 참고용만 |
| `claude_judge_golden_set_2026-07-05.jsonl` | 동일 6개 페르소나 — Claude + WebSearch로 실세계 관련성 검증한 정답지, **실제 배포 사이트**(`vulnerable-groups-rag.onrender.com`, 기본 top_n) 화면 노출 결과 대비 recall 산출. 정답 누수 없는 버전 | ✅ 자동생성본, 전문가 검토 전 |

---

## 3. 담지 않는 것

- 원본 CSV / JSONL 데이터
- 모델 가중치 / 임베딩 파일

## 4. 사용 방법

`personas.json`의 `api_request` 필드를 `POST /api/v1/recommendations` 본문으로 사용.

## 5. Next Steps (Audit Findings by Gemini CLI)

1. **전문가 정성 검토**: `golden_set.jsonl`·`llm_judge_golden_set_2026-07-05.jsonl` 모두 자동 생성본 — 실제 도메인 지식과 부합하는지 전문가 검토 및 수정 필요.
2. ~~**LLM-as-a-Judge 도입**~~ → 2026-07-05 `scripts/llm_judge_golden_set.py`로 구현 완료(6개 신규 페르소나, recall_all/recall@10 산출). 전체 15종 페르소나로 확장은 미실시.
3. **골든셋 확장**: 현재 6종(LLM-judge) + 5종(기존)인 골든셋을 `personas.json`의 전체 15종으로 확대 적용.
4. **Reasoning 품질 고도화**: `cert_to_cert_relation.csv`에 추출된 `reasoning_evidence` 문장이 사용자에게 자연스럽게 전달되는지 프롬프트 튜닝 및 검증.
5. ~~**`recommended_risk_stages` 정책 재검토**~~ → 2026-07-05 해결. `relations/FOLDER.md` §P6-1/P6-2 재정의(기술사·기능장·<10% 합격률만 활동제한형·은둔청년 제외, 나머지 전 단계 개방) + `cert_candidates.jsonl` 재생성 + `_RISK_TIER_MIN` 전면 개방. 재평가 결과 6개 페르소나 평균 recall_all 0.730 → **1.000**(`DEV_LOG.md` 2026-07-05 (4)).
6. **recall@10 개선**: eligibility는 해결됐으나 top-10 노출 순위(Fit Score 가중치)는 페르소나별로 0.14~1.00로 편차가 큼 — 별도 튜닝 라운드 필요.
7. ⚠️ **recall=1.000 방법론 결함 발견·수정** (2026-07-05, 사용자 지적): (4)의 recall=1.000은 gold set을 시스템과 동일한 도메인-필터 후보 풀에서만 뽑고, `actual`을 `top_n_per_stage=100`으로 인위적으로 부풀려 측정한 정답 누수였음. `claude_judge_golden_set_2026-07-05.jsonl`로 대체: Claude가 WebSearch로 실세계 관련성을 별도 검증하고, **실제 배포 사이트**(로컬 아님)의 기본 top_n(화면 노출 개수) 대비 recall 재계산 → 평균 **0.570**(0.36~1.00). 이 수치가 신뢰 가능한 기준선.
