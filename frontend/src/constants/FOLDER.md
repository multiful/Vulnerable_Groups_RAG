# FOLDER.md

> **파일명**: FOLDER.md  
> **폴더 경로**: `frontend/src/constants`  
> **최종 수정일**: 2026-07-02  
> **문서 해시**: SHA256:TBD  
> **문서 역할**: 디렉터리 스캐폴드 명시서 — 담는 내용·금지·다음 단계 연계  
> **문서 우선순위**: reference (충돌 시 루트 기준 문서 우선)  
> **연관 문서**: DIRECTORY_SPEC.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DATA_SCHEMA.md, PRD.md, PROJECT_SUMMARY.md, README.md, CHANGE_CONTROL.md  

> **참조 규칙**: 폴더 용도가 바뀌면 본 파일과 `DIRECTORY_SPEC.md`를 같은 작업에서 갱신한다. 실제 스키마·API 계약은 루트 `DATA_SCHEMA.md`, `API_SPEC.md`, `RAG_PIPELINE.md`가 우선한다.

---

## 1. 용도

UI 라벨·경로 상수 등.

## 2. 파일 목록

- `stageLabels.ts`: 위험군 단계(1~4단계) 표시용 비낙인/plain-language 라벨 (`STAGE_LABELS`). "은둔 청년" 등 임상 용어를 화면에 직접 노출하지 않기 위한 공용 상수 (critique 2026-07-02 P0 대응). 현재는 Recommendation이 import하며, InterestSelection의 기존 동일 문구(`RISK_STAGE_LABELS`)를 단일 출처로 흡수할 예정의 시작점이다.

## 3. 담지 않는 것

taxonomy 허용 값(그건 `data/taxonomy` + 서버 검증).

## 4. 산출·연계

- 라우트 경로는 `App`·라우터 설정과 일치.
- `stageLabels.ts`는 `frontend/src/pages/Recommendation/index.tsx`에서 import한다. `frontend/src/pages/InterestSelection/index.tsx`는 자체 `RISK_STAGE_LABELS`를 계속 유지한다(이번 변경 범위 밖 — 동일 문구를 별도 상수로 중복 보유 중, 후속 정리 대상).

---

## 5. 비고

- 대용량 원본·산출물은 Git 정책(`.gitignore`)과 `HASH_INCREMENTAL_BUILD_GUIDE.md` 증분 원칙을 따른다.
