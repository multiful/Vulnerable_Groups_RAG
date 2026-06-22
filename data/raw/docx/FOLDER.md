# FOLDER.md

> **파일명**: FOLDER.md  
> **폴더 경로**: `data/raw/docx`  
> **최종 수정일**: 2026-06-22  
> **문서 해시**: SHA256:TBD  
> **문서 역할**: 디렉터리 스캐폴드 명시서 — 담는 내용·금지·다음 단계 연계  
> **문서 우선순위**: reference (충돌 시 루트 기준 문서 우선)  
> **연관 문서**: DIRECTORY_SPEC.md, RAG_PIPELINE.md, DATA_SCHEMA.md

> **참조 규칙**: 폴더 용도가 바뀌면 본 파일과 `DIRECTORY_SPEC.md`를 같은 작업에서 갱신한다.

---

## 1. 용도

RAG 인덱싱 대상 **원본 DOCX 문서**. NCS 자격 종목, 국가기술자격 관련 공식 문서 등 Word 형식 근거 자료를 둔다.

## 2. 담지 않는 것

- CSV, PDF (각각 `data/raw/csv/`, `data/raw/pdf/` 사용)
- Parse IR JSON (`data/index_ready/parse_ir/`)
- 개인 참고 자료 (`docs/references/_private/`)

## 3. 산출·연계

`RAG_PIPELINE.md` Parse 단계 → docx_parser.py → `data/index_ready/` 산출로 이어진다.

---

## 4. 현재 파일 목록

| 파일명 | 출처 | doc_type |
|---|---|---|
| NCS_능력단위별_자격종목_조회.docx | 한국산업인력공단 | official_guide |
