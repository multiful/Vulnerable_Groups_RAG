# FOLDER.md

> **파일명**: FOLDER.md  
> **폴더 경로**: `frontend/src/pages/Roadmap`  
> **최종 수정일**: 2026-05-25  
> **문서 해시**: SHA256:TBD  
> **문서 역할**: 디렉터리 스캐폴드 명시서 — 담는 내용·금지·다음 단계 연계  
> **문서 우선순위**: reference (충돌 시 루트 기준 문서 우선)  
> **연관 문서**: DIRECTORY_SPEC.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DATA_SCHEMA.md, PRD.md, PROJECT_SUMMARY.md, README.md, CHANGE_CONTROL.md  

> **참조 규칙**: 폴더 용도가 바뀌면 본 파일과 `DIRECTORY_SPEC.md`를 같은 작업에서 갱신한다. 실제 스키마·API 계약은 루트 `DATA_SCHEMA.md`, `API_SPEC.md`, `RAG_PIPELINE.md`가 우선한다.

---

## 1. 용도

**로드맵** 단계형 UI. 위험군 단계 × 도메인 × 직무 기반 자격증 로드맵과 취업지원 자원 번들을 함께 표시한다.

## 2. 담지 않는 것

일정 API 실연동(`FEATURE_SPEC` reserved). 취업지원 번들은 `/api/v1/support/bundle`에서 비동기 조회하며 실패해도 자격증 로드맵은 정상 표시된다.

## 3. 산출·연계

`roadmap` feature 모듈과 연계.

---

## 4. 비고

- 비어 있거나 `.gitkeep`만 둔 것은 **개발 스캐폴드**일 수 있다.
- 대용량 원본·산출물은 Git 정책(`.gitignore`)과 `HASH_INCREMENTAL_BUILD_GUIDE.md` 증분 원칙을 따른다.
