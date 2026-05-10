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
