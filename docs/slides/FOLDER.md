# FOLDER.md

> **파일명**: FOLDER.md  
> **폴더 경로**: `docs/slides`  
> **최종 수정일**: 2026-05-14  
> **문서 해시**: SHA256:TBD  
> **문서 역할**: 디렉터리 스캐폴드 명시서 — 담는 내용·금지·다음 단계 연계  
> **문서 우선순위**: reference (충돌 시 루트 기준 문서 우선)  
> **연관 문서**: DIRECTORY_SPEC.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DATA_SCHEMA.md, PRD.md, PROJECT_SUMMARY.md, README.md, CHANGE_CONTROL.md  

> **참조 규칙**: 폴더 용도가 바뀌면 본 파일과 `DIRECTORY_SPEC.md`를 같은 작업에서 갱신한다. 실제 스키마·API 계약은 루트 `DATA_SCHEMA.md`, `API_SPEC.md`, `RAG_PIPELINE.md`가 우선한다.

---

## 1. 용도

발표·리뷰용 슬라이드 원본(PPT/PDF보내기 등)과 통계 차트 PNG를 둔다. 제품 계약·스키마의 근거 문서는 아니다.

## 1-1. 파일 목록 (2026-05-14 기준)

| 파일 | 내용 |
|---|---|
| `01_cert_grade_distribution.png` | 자격증 등급 분포 |
| `02_pass_rate_histogram.png` | 합격률 히스토그램 |
| `03_domain_distribution.png` | 도메인 분포 |
| `04_risk_stage_coverage.png` | 위험군 단계별 커버리지 |
| `05_pass_rate_by_grade.png` | 등급별 합격률 |
| `06_yearly_pass_rate_trend.png` | 연도별 합격률 추이 |
| `07_major_cert_acquisition.png` | 전공별 취득 현황 |
| `08_regional_distribution.png` | 지역별 분포 |
| `09_job_satisfaction_top20.png` | 직업만족도 상위 20개 |
| `10_top_bottom_pass_rate.png` | 합격률 상위/하위 |
| `11_data_coverage_summary.png` | 데이터 커버리지 요약 |
| `12_api_integration_status.png` | API 통합 현황 (원본, emoji 포함) |
| `12_api_integration_status_fixed.png` | API 통합 현황 (수정본, emoji 제거) |
| `13_goms_major_category.png` | GOMS 전공계열별 응답자 분포 (성별) |
| `14_goms_employment_by_major.png` | 전공계열별 취업 현황 (GOMS 2020) |
| `15_cert_exam_applicants.png` | 자격증 응시자 수 상위 20개 |
| `16_cert_major_connection.png` | 전공별 자격증 연계 현황 상위 12개 |
| `17_job_outlook_salary.png` | 직업별 임금 vs 직업만족도 scatter |
| `18_ncs_cert_mapping_coverage.png` | NCS 대직무별 자격증 매핑 현황 |
| `19_training_employment_rate.png` | 실업자 훈련 직종별 취업률 (2024년, 31개 직종) |
| `20_isolated_youth_survey.png` | 보건복지부 고립·은둔 청년 실태조사 — 연령/원인/취업불안/진로막막함 |
| `generate_charts_13_18.py` | 차트 13~18 + 12 수정본 생성 스크립트 |

## 2. 담지 않는 것

실행 코드, secrets, 대용량 미디어(팀 정책으로 제외한 것).

## 3. 산출·연계

`ROOT_DOC_GUIDE.md`에서 문서 탐색 시 참고 자료로만 연결한다.

---

## 4. 비고

- 비어 있거나 `.gitkeep`만 둔 것은 **개발 스캐폴드**일 수 있다.
- 대용량 원본·산출물은 Git 정책(`.gitignore`)과 `HASH_INCREMENTAL_BUILD_GUIDE.md` 증분 원칙을 따른다.
