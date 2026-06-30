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

export async function fetchCertJobMatch(
  certName: string,
  jobDomain: string,
  riskStage: number,
  limit = 5,
): Promise<CertJobMatchResult> {
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
  return res.json();
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
