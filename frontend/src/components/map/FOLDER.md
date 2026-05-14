# FOLDER.md

> **파일명**: FOLDER.md
> **폴더 경로**: `frontend/src/components/map/`
> **최종 수정일**: 2026-05-14
> **문서 해시**: SHA256:TBD
> **문서 역할**: 지도 컴포넌트 폴더 명세
> **문서 우선순위**: reference
> **연관 문서**: DIRECTORY_SPEC.md, frontend/src/pages/Recommendation/FOLDER.md, backend/app/api/v1/routes/map.py

---

## 1. 용도

Kakao Maps JS SDK 기반 지도 시각화 컴포넌트를 둔다.
`GET /api/v1/map/infra` 응답 데이터를 받아 훈련기관·일자리카페·건강증진센터를 지도 위에 표시한다.

---

## 2. 파일 목록

| 파일 | 역할 | 상태 |
|---|---|---|
| `KakaoMap.tsx` | Kakao Maps JS SDK 로드 + 인프라 MapPoint 마커 렌더링 | ✅ 활성 |

---

## 3. 담지 않는 것

- 지도 API 키 — 프론트엔드: `VITE_KAKAO_JAVASCRIPT_KEY` (`.env`), 백엔드 지오코딩: `KAKAO_REST_API_KEY` (`.env`)
- 인프라 집계 로직 → `backend/app/services/map_service.py`
- 인프라 엔드포인트 → `backend/app/api/v1/routes/map.py`

---

## 4. 연계

`KakaoMap.tsx` ← `Recommendation/index.tsx` (map 탭)
`MapPoint` 타입은 `KakaoMap.tsx`에서 export, `Recommendation/index.tsx`에서 import.
