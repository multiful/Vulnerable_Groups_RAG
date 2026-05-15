# FOLDER.md

> **파일명**: FOLDER.md
> **폴더 경로**: `backend/app/api/v1/routes/`
> **최종 수정일**: 2026-05-15
> **문서 해시**: SHA256:TBD
> **문서 역할**: API v1 라우트 핸들러 폴더 명세
> **문서 우선순위**: reference
> **연관 문서**: API_SPEC.md, DIRECTORY_SPEC.md, backend/app/api/v1/router.py

---

## 1. 용도

FastAPI 라우트 핸들러를 모듈별로 둔다. 각 파일은 `APIRouter`를 노출하며 `router.py`에서 집결한다.

---

## 2. 파일 목록

### 2.1 추천 핵심 라우트

| 파일 | 엔드포인트 | 상태 |
|---|---|---|
| `recommendation.py` | `POST /api/v1/recommendations`, `POST /api/v1/recommendations/evidence` | ✅ |
| `roadmap.py` | `POST /api/v1/roadmaps` | ✅ |
| `risk.py` | `GET /api/v1/risk-stages` | ✅ |
| `health.py` | `GET /api/v1/health` | ✅ |
| `admin.py` | 내부 관리용 (캐시 flush 등) | ✅ |
| `cert_videos.py` | `GET /api/v1/cert-videos/{cert_id}` | ✅ |
| `chat.py` | `POST /api/v1/chat` — GPT-4o-mini 진로 상담 에이전트 | ✅ |

### 2.2 Execution Layer 라우트

| 파일 | 엔드포인트 | 상태 |
|---|---|---|
| `schedule.py` | `GET /api/v1/schedules/exams/{cert_id}`, `GET /api/v1/schedules/applications/{cert_id}`, `GET /api/v1/links/support/{cert_id}` | ✅ 활성 (Q-Net API 연동) |
| `jobs.py` | `GET /api/v1/jobs/hiring`, `GET /api/v1/jobs/hiring/by-cert/{cert_id}`, `GET /api/v1/jobs/cert-summary/{cert_id}`, `GET /api/v1/jobs/detail` | ✅ |
| `training.py` | `GET /api/v1/training/courses`, `GET /api/v1/training/courses/by-cert/{cert_id}`, `GET /api/v1/training/process-eval` | ✅ |
| `seoul.py` | `GET /api/v1/seoul/job-cafes`, `GET /api/v1/seoul/health-centers`, `GET /api/v1/seoul/reservations` | ✅ |
| `action.py` | `GET /api/v1/actions/today` | ✅ |
| `map.py` | `GET /api/v1/map/infra` | ✅ |
| `jobs_info.py` | `GET /api/v1/jobs/cert-jobs/{cert_name}`, `GET /api/v1/jobs/info/{job_name}`, `GET /api/v1/jobs/major-certs/{major_name}` | ✅ |
| `career_net.py` | `GET /api/v1/career-net/jobs`, `GET /api/v1/career-net/jobs/{seq}`, `GET /api/v1/career-net/majors` | ✅ |
| `cert_info.py` | `GET /api/v1/certs/{cert_id}/info`, `GET /api/v1/certs/{cert_id}/exam-info`, `GET /api/v1/certs/{cert_id}/full-info` | ✅ |
| `ncs.py` | `GET /api/v1/ncs/certs`, `GET /api/v1/ncs/list` | ✅ |

---

## 3. 엔드포인트 총계 (2026-05-14 기준)

| 그룹 | 수 |
|---|---:|
| 추천 핵심 | 6 |
| 일정/링크 (Q-Net) | 3 |
| 채용정보 (WorkNet) | 4 |
| 훈련과정 (Work24) | 3 |
| 서울시 공공데이터 | 3 |
| 오늘의 행동 | 1 |
| 기타 (health, admin) | 3 |
| GOMS/NCS 직업정보 | 3 |
| 커리어넷 직업/학과 | 3 |
| Q-Net 자격/시험 상세 | 3 |
| NCS 능력단위 조회 | 2 |
| **합계** | **34** |

---

## 4. 담지 않는 것

- 비즈니스 로직 → `backend/app/services/`
- 데이터 스키마 정의 → `backend/app/schemas/`
- DB 접근 → `backend/app/repositories/`

---

## 5. 연계

`routes/` → `services/` → `cert_lookup_service` → `data/canonical/` (cert_ncs_mapping, ncs_master 등)  
`routes/` → `services/` → External Public APIs (Q-Net, WorkNet, Work24, Seoul Open API)
