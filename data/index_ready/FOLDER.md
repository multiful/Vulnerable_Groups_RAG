# FOLDER.md

> **파일명**: FOLDER.md  
> **폴더 경로**: `data/index_ready`  
> **최종 수정일**: 2026-05-12  
> **문서 해시**: SHA256:TBD  
> **문서 역할**: 디렉터리 스캐폴드 명시서 — 담는 내용·금지·다음 단계 연계  
> **문서 우선순위**: reference (충돌 시 루트 기준 문서 우선)  
> **연관 문서**: DIRECTORY_SPEC.md, RAG_PIPELINE.md

---

## 1. 용도

embedding·upload 직전 정제 산출물 보관 폴더.  
parse IR → chunk → (dense/sparse) → index_ready 순서로 흐른다.

## 2. 파일 및 하위 폴더 목록

| 경로 | 역할 |
|---|---|
| `chunks/chunks.jsonl` | 임베딩 대기 chunk 목록 (Supabase 업로드 원본) |
| `chunks/chunks.jsonl.example` | 스키마 예시 |
| `dense_input/` | dense embedding 입력 파일 |
| `sparse_input/` | sparse(BM25) 입력 파일 (reserved) |
| `parse_ir/` | parse 중간 결과물 |
| `metadata/` | chunk metadata 파일 |
| `private_cert_catalog.json` | 공인민간자격 정보자료집(2025) 파싱 결과 (cert_name → 응시료·활용현황·공인정보) |
| `national_cert_catalog.json` | 국가자격 정보집(2026) 파싱 결과 (cert_name → 도입목적·진로·응시료·시행기관·소관부처) |

## 3. 담지 않는 것

- 원본 PDF/HTML (`data/raw/`)
- canonical row / candidate row (`data/canonical/`)
- 임베딩 벡터 자체 (Supabase에만 보관)

## 4. private_cert_catalog.json 갱신

```
python -m scripts.parse.parse_private_cert_catalog
```

PDF 원본: `data/raw/pdf/붙임_2025년_공인민간자격_정보자료집(탑재용).pdf`

## 5. national_cert_catalog.json 갱신

```
python -m scripts.parse.parse_national_cert_catalog
```

PDF 원본: `data/raw/pdf/국가정보자격집_20260122-압축됨.pdf`
