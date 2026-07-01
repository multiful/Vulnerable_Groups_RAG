/**
 * API 베이스 URL.
 * 로컬: Vite proxy로 같은 오리진에서 /api 호출 가능.
 * Vercel 등: VITE_API_BASE_URL=https://your-api.railway.app
 */
import type { CertCandidate } from '../types/cert';

export function getApiBase(): string {
  const env = import.meta.env.VITE_API_BASE_URL;
  if (env && env.length > 0) return env.replace(/\/$/, "");
  return "";
}

export async function fetchHealth(): Promise<unknown> {
  const base = getApiBase();
  const url = base ? `${base}/api/v1/health` : "/api/v1/health";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`health ${res.status}`);
  return res.json();
}

/* ── cert_candidates.json 싱글턴 캐시 ──
 * 페이지 간 중복 fetch 방지. 에러 시 promise를 초기화해 재시도 허용.
 */
let _certCache: CertCandidate[] | null = null;
let _certCachePromise: Promise<CertCandidate[]> | null = null;

/* ── 채용공고 매칭 API ── */
export interface JobPostingMatch {
  company: string;
  title: string;
  url: string;
  department?: string;
  location?: string;
  match_score?: number;
  is_active?: boolean;
}

export interface CertJobMatchResult {
  cert_name: string;
  job_domain: string;
  risk_stage: number;
  difficulty_score: number;
  difficulty_threshold: number;
  meets_threshold: boolean;
  pass_rate: number | null;
  domain_relevance_delta: number;
  relevance_summary: string;
  job_demand_level: '상' | '중' | '하';
  job_postings: JobPostingMatch[];
  posting_count: number;
}

const _CERT_JOB_MOCK: Record<string, CertJobMatchResult['job_postings']> = {
  '정보처리기사': [
    {
      company: '(주)아이티벤처',
      title: 'IT 시스템 운영 및 유지보수 (정보처리기사 우대)',
      url: 'https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=54056812&location=ts&searchword=%EC%A0%95%EB%B3%B4%EC%B2%98%EB%A6%AC%EA%B8%B0%EC%82%AC&searchType=search&paid_fl=n&search_uuid=3e34fdda-3800-414b-bada-d3c19b035a98&t_ref=search&t_ref_content=generic',
      location: '서울',
      is_active: true,
    },
  ],
};

export async function fetchCertJobMatch(
  certName: string,
  jobDomain: string,
  riskStage: number,
  limit = 5,
): Promise<CertJobMatchResult> {
  let result: CertJobMatchResult | null = null;
  try {
    const base = getApiBase();
    const params = new URLSearchParams({
      cert_name: certName,
      job_domain: jobDomain,
      risk_stage: String(riskStage),
      limit: String(limit),
    });
    const url = `${base}/api/v1/job-postings/match?${params}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`job-postings/match ${res.status}`);
    result = await res.json();
  } catch {
    result = null;
  }

  const mockPostings = _CERT_JOB_MOCK[certName] ?? [];
  if (!result) {
    return {
      cert_name: certName,
      job_domain: jobDomain,
      risk_stage: riskStage,
      difficulty_score: 55,
      difficulty_threshold: 60,
      meets_threshold: false,
      pass_rate: null,
      domain_relevance_delta: 0,
      relevance_summary: '관련 채용 정보를 불러오는 중 오류가 발생했습니다.',
      job_demand_level: '중',
      job_postings: mockPostings,
      posting_count: mockPostings.length,
    };
  }
  // API 성공이더라도 목업 공고가 정의된 자격증은 항상 주입
  if (mockPostings.length > 0 && result.job_postings.length === 0) {
    result.job_postings = mockPostings;
    result.posting_count = mockPostings.length;
  }
  return result;
}

export async function triggerCrawlRefresh(): Promise<void> {
  const base = getApiBase();
  await fetch(`${base}/api/v1/job-postings/crawl-refresh`, { method: 'GET' });
}

export async function getCertCandidates(): Promise<CertCandidate[]> {
  if (_certCache) return _certCache;
  if (!_certCachePromise) {
    _certCachePromise = fetch('/data/cert_candidates.json')
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((data: CertCandidate[]) => { _certCache = data; return data; })
      .catch(err => { _certCachePromise = null; throw err; });
  }
  return _certCachePromise;
}

/* ── 군집 분류 근거 RAG 검색 ── */
export interface StageEvidenceItem {
  doc_id: string;
  chunk_id: string;
  snippet: string;
  section_path: string[];
  source_type: string;
}

export interface HydeEvidenceResult {
  synthesis: string | null;
  evidence: StageEvidenceItem[];
  hyde_used: boolean;
}

/** HyDE 기반 분류 근거 검색 (POST). dimension_scores를 함께 전송해 LLM 합성 포함 결과를 받음. */
export async function fetchHydeEvidence(
  clusterId: string,
  dimScores: Record<string, number>,
): Promise<HydeEvidenceResult> {
  const base = getApiBase();
  const url = `${base}/api/v1/risk/stage-evidence`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cluster_id: clusterId, dimension_scores: dimScores }),
    });
    if (!res.ok) return { synthesis: null, evidence: [], hyde_used: false };
    const json = await res.json();
    return {
      synthesis: (json?.data?.synthesis as string | null) ?? null,
      evidence: (json?.data?.evidence ?? []) as StageEvidenceItem[],
      hyde_used: !!(json?.data?.hyde_used),
    };
  } catch {
    return { synthesis: null, evidence: [], hyde_used: false };
  }
}

/** 레거시 GET (dimension_scores 없이 cluster_id만 전달). */
export async function fetchStageEvidence(clusterId: string): Promise<StageEvidenceItem[]> {
  const base = getApiBase();
  const url = `${base}/api/v1/risk/stage-evidence?cluster_id=${encodeURIComponent(clusterId)}`;
  try {
    const res = await fetch(url);
    if (!res.ok) return [];
    const json = await res.json();
    return (json?.data?.evidence ?? []) as StageEvidenceItem[];
  } catch {
    return [];
  }
}
