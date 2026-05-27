> **파일명**: FOLDER.md
> **최종 수정일**: 2026-05-26
> **문서 해시**: SHA256:TBD
> **문서 역할**: frontend/src/pages/Training 폴더 설명
> **문서 우선순위**: N/A
> **연관 문서**: DIRECTORY_SPEC.md, API_SPEC.md

# pages/Training

## 용도
국민내일배움카드 훈련과정 탐색 페이지 (`/training`).
Work24 훈련과정 API · 과정평가형 자격 · 일학습병행 경로를 탭으로 제공한다.

## 파일 목록
| 파일 | 역할 |
|------|------|
| `index.tsx` | 훈련과정 메인 페이지 컴포넌트 |
| `FOLDER.md` | 이 문서 |

## 담지 않는 것
- 백엔드 API 로직 (→ `backend/app/services/training_service.py`)
- 라우터 등록 (→ `frontend/src/App.tsx`)

## 연계 경로
- API: `GET /api/v1/training/courses`
- URL 파라미터: `?keyword=` (Explore 직업/NCS 카드에서 넘어올 때 자동 검색)
- 이전 페이지: `/pages/Jobs` 제거 후 이 페이지로 대체 (2026-05-26)
