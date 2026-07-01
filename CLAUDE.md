# CLAUDE.md

> **파일명**: CLAUDE.md  
> **최종 수정일**: 2026-07-01  
> **문서 해시**: SHA256:7098e64dac0df0b090ecb9ff1dd5d67e76293962dc2201581e7738fd674f53a6
> **문서 역할**: Claude Code 작업 규칙 / 구현 및 문서화 실행 규칙 문서  
> **문서 우선순위**: 99  
> **연관 문서**: README.md, CHANGE_CONTROL.md, PRD.md, SYSTEM_ARCHITECTURE.md, FEATURE_SPEC.md, DATA_SCHEMA.md, API_SPEC.md, PROMPT_DESIGN.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md, HASH_INCREMENTAL_BUILD_GUIDE.md  
> **참조 규칙**: Claude가 새 문서, 코드, 스크립트, 구조 변경을 제안하거나 생성할 때 항상 먼저 따른다.

---

# 1. 프로젝트 목적

이 프로젝트는 청년 위험군 단계와 관심 직무/도메인을 바탕으로, 관련 자격증을 추천하고 단계형 로드맵을 제안하는 시스템이다.  
현재 우선 목표는 완성형 서비스가 아니라, 추천 구조와 지식 파이프라인을 안정적으로 구현하는 것이다.

---

# 2. 최우선 작업 원칙

- 항상 코드보다 루트 문서를 먼저 읽고 수정한다.
- 작업 시작 전 최소한 아래 문서를 먼저 읽는다.
  - `README.md`
  - `CHANGE_CONTROL.md`
  - `PRD.md`
  - `SYSTEM_ARCHITECTURE.md`
- 기능, 정책, 구조가 바뀌면 코드보다 먼저 관련 문서를 수정한다.
- 문서를 수정할 때는 문서 맨 위 메타데이터의 `최종 수정일`도 함께 갱신한다.
- 문서 간 충돌이 있으면 `CHANGE_CONTROL.md`의 우선순위를 따른다.
- 문서/스크립트 생성 시 메타데이터와 해시 라인을 반드시 함께 만든다.
- reserved 기능은 임의로 구현하거나 완료된 것처럼 다루지 않는다.
- 전체 재처리보다 증분 처리와 선택적 재처리를 우선한다.
- **폴더를 탐색하거나 그 안의 파일을 다룰 때는 해당 폴더의 `FOLDER.md`를 먼저 읽는다.** `FOLDER.md`는 용도·파일 목록·담지 않는 것·연계 경로를 명시한다. 파일 추가·제거 시 `FOLDER.md`도 함께 갱신한다.

---

# 3. 문서 우선순위

- 0: `README.md`
- 1: `CHANGE_CONTROL.md`
- 2: `PRD.md`
- 3: `SYSTEM_ARCHITECTURE.md`
- 4: `FEATURE_SPEC.md`
- 5: `DATA_SCHEMA.md`
- 6: `API_SPEC.md`
- 7: `PROMPT_DESIGN.md`
- 8: `RAG_PIPELINE.md`
- 9: `DIRECTORY_SPEC.md`

문서 우선순위 숫자는 중복되면 안 된다.  
문서 메타데이터 숫자가 `CHANGE_CONTROL.md`와 충돌하면 `CHANGE_CONTROL.md` 기준으로 즉시 수정한다.

---

# 4. 문서 역할 분리 규칙

- `README.md`: 프로젝트 입구 문서만 담당
- `CHANGE_CONTROL.md`: 문서 수정 규칙과 절차만 담당
- `PRD.md`: 현재 해결할 문제, 범위, 목표만 담당
- `SYSTEM_ARCHITECTURE.md`: 계층, 책임, 온라인/오프라인 흐름만 담당
- `FEATURE_SPEC.md`: 기능별 입력/출력/예외/상태만 담당
- `DATA_SCHEMA.md`: 엔티티/관계/필드/제약만 담당
- `API_SPEC.md`: endpoint / request / response / error contract만 담당
- `PROMPT_DESIGN.md`: 프롬프트 역할, 입력, 출력, 검증, fallback만 담당
- `RAG_PIPELINE.md`: parse/chunk/metadata/embedding/retrieval만 담당
- `DIRECTORY_SPEC.md`: 디렉토리와 파일 책임만 담당

문서 간 역할이 겹치지 않게 유지한다.  
이미 다른 문서에 정의된 내용을 새 문서에서 반복하지 않는다.

---

# 5. 구현 범위 규칙

## 현재 활성 범위
- 위험군 기반 추천 진입
- 관심 직무/도메인 기반 추천
- 자격증 후보 조회
- 설명 근거 조회
- 로드맵 조회
- CSV canonicalization
- entity / relation / candidate row 생성
- PDF / HTML evidence retrieval

## 현재 reserved 범위
- 시험 일정 API
- 접수 일정 API
- 지원 링크 실연동
- reranker
- sparse/BM25 상시 사용
- parent-child 고도화
- full infra 배포 구조
- 상담형 대화 에이전트

reserved 기능은 임의로 구현하거나 완료된 것처럼 다루지 않는다.

---

# 6. 도메인 규칙

- 위험군은 1단계 ~ 4단계 구조로만 다룬다 (SCRIPT.md 보사연 2022 검증 기반, N=5,513).
- 1단계 (고립위험청년): 고립 위험 신호가 일부 있으나 사회 기능을 부분적으로 유지하는 단계.
- 2단계 (활동형 고립청년): 외출·활동은 하지만 관계 어려움이 있고 사회 안착을 반복 탈락하는 단계.
- 3단계 (활동제한형 고립청년): 사회활동이 비자발적으로 극히 제한되고 고립 기간이 확인되는 단계.
- 4단계 (은둔청년): 가족 외 관계 단절, 외출 회피 장기화, 생활리듬 붕괴가 동반되는 단계.
- 기존 5단계(은둔군) 데이터(risk_0005)는 백엔드에 비활성 상태로 보존되며, 프론트엔드는 사용하지 않는다.

---

# 7. taxonomy 규칙

- `related_domains`는 허용된 도메인 taxonomy 세부 라벨만 사용한다.
- `related_jobs`는 허용된 희망 직무 taxonomy 세부 직무만 사용한다.
- `primary_domain`도 허용된 도메인 taxonomy 세부 라벨만 사용한다.
- 자유 텍스트 라벨을 새로 만들지 않는다.
- 추천 결과에 taxonomy 밖 값이 나오면 오류로 간주한다.

---

# 8. 데이터 처리 규칙

- PDF / HTML은 parse 및 indexing 대상이다.
- CSV는 Parse IR을 만들지 않는다.
- CSV는 structured no-parse canonicalization 경로만 사용한다.
- 원본 CSV를 recommendation 입력으로 직접 사용하지 않는다.
- canonical entity / relation / candidate row를 생성해서 사용한다.
- recommendation candidate row와 문서형 chunk를 같은 구조로 다루지 않는다.

---

# 9. RAG 규칙

- RAG는 추천 엔진이 아니라 설명 근거 검색 계층이다.
- 구조적 추천은 canonical data가 담당한다.
- born-digital PDF 전체에 OCR을 기본 적용하지 않는다.
- OCR은 page-level 예외 처리로만 사용한다.
- sparse/BM25는 exact miss가 실제 문제로 재현되기 전까지 강제하지 않는다.
- retrieval 결과가 0건이어도 추천 결과 자체는 실패로 간주하지 않는다.

---

# 10. API / 프롬프트 규칙

- API 응답 형식은 `API_SPEC.md`를 기준으로 유지한다.
- 프롬프트는 추천을 계산하지 않고 설명/요약/조립만 담당한다.
- 프롬프트는 canonical data와 retrieval evidence만 근거로 사용한다.
- evidence가 없으면 임의 사실을 생성하지 않는다.
- 일정/링크 미연동 상태에서 날짜/링크를 지어내지 않는다.

---

# 11. 메타데이터 및 해시 라인 규칙

## 11.1 md 파일 규칙
모든 새 md 파일에는 아래 메타데이터를 반드시 포함한다.

- 파일명
- 최종 수정일
- 문서 해시
- 문서 역할
- 문서 우선순위
- 연관 문서
- 참조 규칙

md 파일의 해시 라인은 아래 형식을 사용한다.

- `> **문서 해시**: SHA256:<AUTO_HASH_OR_TBD>`

md 파일에서 `문서 해시` 라인은 `최종 수정일` 바로 아래에 둔다.

## 11.2 스크립트 파일 규칙
모든 새 스크립트 파일에는 언어별 주석 메타데이터를 반드시 포함한다.

- Python: `# Content Hash: SHA256:<AUTO_HASH_OR_TBD>`
- JS/TS: `// Content Hash: SHA256:<AUTO_HASH_OR_TBD>`
- Shell: `# Content Hash: SHA256:<AUTO_HASH_OR_TBD>`
- SQL: `-- Content Hash: SHA256:<AUTO_HASH_OR_TBD>`

## 11.3 해시 계산 규칙
- 해시는 해시 라인 자신을 포함해서 계산하지 않는다.
- 필요하면 `최종 수정일` 또는 `Last Updated` 라인은 해시 계산에서 제외한다.
- 목적은 의미 내용이 바뀌었을 때만 해시가 바뀌게 하는 것이다.

## 11.4 실제 해시값 처리 규칙
- 실제 해시를 계산할 수 있으면 계산된 값으로 넣는다.
- 현재 단계에서 실제 계산이 불가능하면 `SHA256:TBD` 또는 `SHA256:<AUTO_HASH_OR_TBD>`를 넣고, 후속 스크립트/빌드 단계에서 갱신하도록 표시한다.
- 해시를 계산하지 않았는데 임의의 가짜 해시값을 넣는 것은 금지한다.

---

# 12. 증분 빌드 / 실행속도 최적화 규칙

- 변경되지 않은 입력은 재처리하지 않는다.
- 전체 rebuild보다 selective rebuild를 우선한다.
- 캐시 키는 항상 `input_hash + rule_version` 조합으로 설계한다.
- PDF / HTML ingest는 원본 file hash가 안 바뀌면 재파싱하지 않는다.
- parse hash가 안 바뀌면 rechunk 하지 않는다.
- chunk hash가 안 바뀌면 re-embed 하지 않는다.
- embedding version이 안 바뀌면 unchanged chunk 재임베딩을 금지한다.
- CSV canonicalization은 file hash 또는 row hash가 달라진 row만 재처리한다.
- entity/relation hash가 안 바뀌면 candidate rebuild를 스킵한다.
- candidate content hash가 안 바뀌면 recommendation index update를 스킵한다.
- OCR는 unchanged scanned page에 재적용하지 않는다.
- parser/chunker/embedding 규칙이 바뀌면 반드시 version을 올린다.
- build 결과는 가능하면 manifest로 남긴다.
- 전체 재빌드는 마지막 수단으로만 사용한다.

---

# 13. 권장 해시 종류

- `file_hash`: 원본 파일 전체 기준
- `parse_hash`: parse 결과 기준
- `chunk_hash`: chunk 단위 기준
- `row_hash`: CSV row 기준
- `content_hash`: canonical row / candidate row 기준
- `embedding_key_hash`: chunk hash + embedding version 기준

---

# 14. 인덱스 / 파이프라인 버전 규칙

- ingest 규칙이 바뀌면 `ingest_version`을 갱신한다.
- chunk 규칙이 바뀌면 `chunk_version`을 갱신한다.
- metadata 규칙이 바뀌면 `metadata_version`을 갱신한다.
- embedding 모델 또는 입력 프롬프트가 바뀌면 `embedding_version`을 갱신한다.
- 버전이 바뀌면 해당 단계 이후만 재빌드하는 것을 우선 고려한다.

---

# 15. 구현 방식 규칙

- 기존 패턴과 파일 구조를 우선 따른다.
- 새 파일 추가 전 `DIRECTORY_SPEC.md`와 충돌 여부를 확인한다.
- 코드 변경 시 영향받는 문서를 함께 수정한다.
- 큰 작업은 아래 순서로 진행한다.
  1. 관련 문서 확인
  2. 문서 수정
  3. 구현
  4. 검증
  5. `DEV_LOG.md` 반영

---

# 16. 응답 방식 규칙

- 작업 전 무엇을 바꿀지 짧게 요약한다.
- 여러 파일을 수정할 때는 변경 이유를 먼저 설명한다.
- 문서와 충돌하는 요청이면 바로 구현하지 말고 문서 수정부터 제안한다.
- 확정되지 않은 정책은 추정하지 말고 reserved 또는 TODO로 남긴다.
- 과도하게 장황한 설명보다, 바로 적용 가능한 변경안을 제시한다.

---

# 17. 금지 사항

- README를 PRD처럼 길게 확장하지 않는다.
- FEATURE_SPEC에 DB 컬럼 상세를 넣지 않는다.
- DATA_SCHEMA에 사용자 시나리오를 넣지 않는다.
- API_SPEC에 시스템 구조 설명을 넣지 않는다.
- RAG_PIPELINE에 제품 문제 정의를 넣지 않는다.
- DIRECTORY_SPEC에 문서 운영 절차를 넣지 않는다.
- 문서 우선순위 숫자를 중복되게 두지 않는다.
- unchanged 입력에 대해 전체 재처리를 습관적으로 수행하지 않는다.
- reserved 기능을 완료된 것처럼 응답하지 않는다.
- 실제 계산하지 않은 해시를 계산된 값처럼 기입하지 않는다.

---

# 18. 로컬 Python 인터프리터 (Windows)

이 프로젝트의 유일한 기본 Python 인터프리터:

```text
C:\Users\rlaeh\envs\fastapi\.venv\Scripts\python.exe
```

- `uv`, `uv run`, `uv pip` 등은 이 프로젝트에서 제안·실행하지 않는다.
- `pip`, `pytest`, `uvicorn` 등은 전부 `python.exe -m` 형태로만 제안한다.
  - 예: `& "C:\Users\rlaeh\envs\fastapi\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt`
  - 예: `& "C:\Users\rlaeh\envs\fastapi\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --reload`
  - 예: `& "C:\Users\rlaeh\envs\fastapi\.venv\Scripts\python.exe" -m pytest backend\tests -q`
- PowerShell에서는 호출 연산자 `&`와 경로를 따옴표로 감싼 형태를 우선한다.
- 커밋되는 파일에 이 절대 경로를 넣는 제안은 하지 않는다.

---

# 19. 폴더 탐색 규칙

어떤 폴더를 탐색하거나 그 안의 파일을 읽을 때, 해당 폴더에 `FOLDER.md`가 있으면 **먼저 읽는다**.

- `FOLDER.md`는 해당 폴더의 용도·파일 목록·담지 않는 것·연계 경로를 명시한다.
- 파일을 새로 추가하거나 제거할 때는 같은 폴더의 `FOLDER.md`도 함께 갱신한다.
- `FOLDER.md`의 내용이 실제 파일 목록과 다르면 실제 파일 기준으로 `FOLDER.md`를 수정한다.
- `FOLDER.md`가 없는 폴더에 파일을 추가할 때는 `FOLDER.md`를 함께 생성한다.

---

# 20. 작업 완료 체크

작업 완료 전 아래를 반드시 확인한다. 작업 전 후 모두 /advisor을 참고한다.
11
- 관련 문서가 최신인지
- 수정한 문서의 `최종 수정일`을 갱신했는지
- 수정한 md/스크립트에 해시 라인이 있는지
- 해시 라인이 형식 규칙을 따르는지
- 실제 해시 미계산 시 placeholder/TBD 규칙을 따랐는지
- reserved 기능을 실수로 활성 기능처럼 작성하지 않았는지
- taxonomy 밖 값이 생기지 않았는지
- 증분 처리 가능한 작업을 전체 재처리로 구현하지 않았는지
- `DEV_LOG.md` 반영이 필요한지
