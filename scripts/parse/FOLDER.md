# FOLDER.md

> **파일명**: FOLDER.md  
> **폴더 경로**: `scripts/parse`  
> **최종 수정일**: 2026-05-12  
> **문서 해시**: SHA256:TBD  
> **문서 역할**: 디렉터리 스캐폴드 명시서 — 담는 내용·금지·다음 단계 연계  
> **문서 우선순위**: reference (충돌 시 루트 기준 문서 우선)  
> **연관 문서**: DIRECTORY_SPEC.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DATA_SCHEMA.md, PRD.md, PROJECT_SUMMARY.md, README.md, CHANGE_CONTROL.md  

> **참조 규칙**: 폴더 용도가 바뀌면 본 파일과 `DIRECTORY_SPEC.md`를 같은 작업에서 갱신한다. 실제 스키마·API 계약은 루트 `DATA_SCHEMA.md`, `API_SPEC.md`, `RAG_PIPELINE.md`가 우선한다.

---

## 1. 용도

`DIRECTORY_SPEC.md` 기준 **PDF/HTML parse** 배치 진입점. `run.py` 스텁.

## 2. 담지 않는 것

CSV canonicalize(그건 `scripts/canonicalize/`).

## 3. 파일 목록

| 파일 | 역할 |
|---|---|
| `run.py` | parse 배치 진입점 스텁 |
| `parse_private_cert_catalog.py` | 공인민간자격 정보자료집 PDF → `data/index_ready/private_cert_catalog.json` 변환 |
| `parse_national_cert_catalog.py` | 국가자격 정보집 PDF → `data/index_ready/national_cert_catalog.json` 변환 |

## 4. 산출·연계

산출은 `data/index_ready/parse_ir/` 또는 `data/index_ready/private_cert_catalog.json` 등으로 — `RAG_PIPELINE.md`.

---

## 4. 비고

- 비어 있거나 `.gitkeep`만 둔 것은 **개발 스캐폴드**일 수 있다.
- 대용량 원본·산출물은 Git 정책(`.gitignore`)과 `HASH_INCREMENTAL_BUILD_GUIDE.md` 증분 원칙을 따른다.
