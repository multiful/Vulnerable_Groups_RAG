// Content Hash: SHA256:TBD
import React, { useState, useMemo, useDeferredValue, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Map, FileText, ChevronDown, AlertCircle, Loader2 } from 'lucide-react';
import type { CertCandidate } from '../../types/cert';

const RISK_STAGE_LABELS: Record<string, string> = {
  '1': '1단계',
  '2': '2단계',
  '3': '3단계',
  '4': '4단계',
  '5': '5단계',
};

const RISK_INTERNAL_MAP: Record<string, string> = {
  '1': 'risk_0001',
  '2': 'risk_0002',
  '3': 'risk_0003',
  '4': 'risk_0004',
  '5': 'risk_0005',
};

function gradeBadgeClass(tier: string): string {
  if (tier.startsWith('5')) return 'badge-primary';
  if (tier.startsWith('4')) return 'badge-primary';
  if (tier.startsWith('3')) return 'badge-secondary';
  if (tier.startsWith('2')) return 'badge-success';
  if (tier.startsWith('1')) return 'badge-warning';
  return 'badge-neutral';
}

function gradeLabel(tier: string): string {
  const map: Record<string, string> = {
    '5_기능장': '기능장',
    '4_기술사': '기술사',
    '3_기사': '기사',
    '2_산업기사': '산업기사',
    '1_기능사': '기능사',
  };
  return map[tier] ?? (tier || '기타');
}

function extractJobs(text: string): string[] {
  const m = text.match(/관련 직무[:\s]+([^.]+)/);
  if (!m) return [];
  return m[1].split(/[,，]/).map(s => s.trim()).filter(Boolean).slice(0, 4);
}

const Recommendation: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const stageParam = searchParams.get('stage') ?? '';

  const [certs, setCerts]       = useState<CertCandidate[]>([]);
  const [loading, setLoading]   = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery]   = useState('');
  const [selectedJob, setSelectedJob]   = useState('');
  const [selectedDomain, setSelectedDomain] = useState('');

  const deferredQuery = useDeferredValue(searchQuery);

  // Fetch JSON at runtime — avoids bundling 1.4 MB into the JS bundle
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch('/data/cert_candidates.json')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: CertCandidate[]) => {
        if (!cancelled) {
          setCerts(data);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setFetchError(err.message);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  const targetRiskInternal = stageParam ? RISK_INTERNAL_MAP[stageParam] : '';
  const riskLabel = stageParam ? (RISK_STAGE_LABELS[stageParam] ?? stageParam) : '';

  const filtered = useMemo(() => {
    return certs.filter(cert => {
      if (targetRiskInternal && !cert.recommended_risk_stages.includes(targetRiskInternal)) return false;
      const haystack = cert.text_for_dense;
      if (deferredQuery && !cert.cert_name.includes(deferredQuery) && !haystack.includes(deferredQuery)) return false;
      if (selectedJob && !haystack.includes(selectedJob)) return false;
      if (selectedDomain && !haystack.includes(selectedDomain)) return false;
      return true;
    });
  }, [certs, deferredQuery, selectedJob, selectedDomain, targetRiskInternal]);

  const handleRoadmap = (certId: string) => {
    const params = new URLSearchParams();
    params.set('cert', certId);
    if (stageParam) params.set('stage', stageParam);
    navigate(`/roadmap?${params.toString()}`);
  };

  return (
    <div className="rec-wrap">
      <div className="page-header">
        <h1 className="page-title">자격증 추천</h1>
        <p className="page-desc">
          {riskLabel
            ? `${riskLabel} 기준으로 적합한 자격증을 보여드립니다.`
            : '관심 직무와 도메인으로 자격증을 탐색하세요.'}
        </p>
      </div>

      {!stageParam && (
        <div className="empty-hint card">
          <AlertCircle size={20} />
          <div>
            <p className="empty-hint-title">위험군 진단을 먼저 해보세요</p>
            <p className="empty-hint-sub">진단 결과를 바탕으로 더 정확한 추천을 드릴 수 있습니다.</p>
          </div>
          <button className="btn-ghost" onClick={() => navigate('/risk-assessment')}>
            진단하러 가기
          </button>
        </div>
      )}

      <div className="card filter-card">
        <div className="search-wrapper">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            className="input search-input"
            placeholder="자격증명, 직무, 도메인으로 검색…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-row">
          <div className="filter-group">
            <label className="filter-label">관심 직무</label>
            <div className="select-wrap">
              <select className="select" value={selectedJob} onChange={e => setSelectedJob(e.target.value)}>
                <option value="">전체 직무</option>
                <option value="데이터">데이터 관련</option>
                <option value="개발">개발 (소프트웨어/웹/앱)</option>
                <option value="기계">기계/생산/제조</option>
                <option value="전기">전기/전자/통신</option>
                <option value="설계">설계/건축/토목</option>
                <option value="기획">경영/기획/사무</option>
              </select>
              <ChevronDown size={16} className="select-arrow" />
            </div>
          </div>
          <div className="filter-group">
            <label className="filter-label">관심 도메인</label>
            <div className="select-wrap">
              <select className="select" value={selectedDomain} onChange={e => setSelectedDomain(e.target.value)}>
                <option value="">전체 도메인</option>
                <option value="IT">IT/소프트웨어</option>
                <option value="기계">기계/제조</option>
                <option value="전기">전기/전자</option>
                <option value="건축">건축/토목</option>
                <option value="디자인">디자인/예술</option>
              </select>
              <ChevronDown size={16} className="select-arrow" />
            </div>
          </div>
        </div>
      </div>

      <section>
        {loading ? (
          <div className="rec-loading">
            <Loader2 size={26} className="rec-spin" />
            <p>자격증 데이터를 불러오는 중…</p>
          </div>
        ) : fetchError ? (
          <div className="rec-error card">
            <AlertCircle size={20} />
            <p>데이터 로드 실패: {fetchError}</p>
            <button className="btn-ghost" onClick={() => window.location.reload()}>다시 시도</button>
          </div>
        ) : (
          <>
            <p className="section-title result-count">
              추천 자격증 <span className="count-num">{filtered.length}</span>건
            </p>
            <div className="cert-grid">
              {filtered.slice(0, 50).map(cert => (
                <div key={cert.candidate_id} className="card cert-card">
                  <div className="cert-top">
                    <div className="cert-top-row">
                      <span className={`badge ${gradeBadgeClass(cert.cert_grade_tier)}`}>
                        {gradeLabel(cert.cert_grade_tier)}
                      </span>
                      <div className="cert-stages">
                        {cert.recommended_risk_stages.map(rs => {
                          const stageNum = rs.replace('risk_000', '');
                          return (
                            <span key={rs} className="badge badge-neutral stage-badge">
                              {stageNum}단계
                            </span>
                          );
                        })}
                      </div>
                    </div>
                    <h3 className="cert-name">{cert.cert_name}</h3>
                    <p className="cert-issuer">{cert.issuer}</p>
                  </div>

                  {(() => {
                    const jobs = extractJobs(cert.text_for_dense);
                    return jobs.length > 0 ? (
                      <div className="cert-jobs">
                        {jobs.map(j => <span key={j} className="job-chip">{j}</span>)}
                      </div>
                    ) : (
                      <p className="cert-summary">{cert.text_for_dense}</p>
                    );
                  })()}

                  <div className="cert-actions">
                    <span className="text-btn text-btn-disabled" title="설명 근거 검색은 준비 중입니다">
                      <FileText size={14} /> 설명 근거
                    </span>
                    <button className="text-btn roadmap-btn" onClick={() => handleRoadmap(cert.cert_id)}>
                      <Map size={14} /> 로드맵 보기
                    </button>
                  </div>
                </div>
              ))}

              {filtered.length === 0 && (
                <div className="no-results">
                  <p>조건에 맞는 자격증이 없습니다.</p>
                  <p>검색어나 필터를 변경해보세요.</p>
                </div>
              )}
            </div>
          </>
        )}
      </section>

      <style>{`
        .rec-wrap { display:flex; flex-direction:column; gap:1.5rem; }

        .empty-hint {
          display:flex; align-items:center; gap:1rem;
          padding:1rem 1.25rem; color:var(--text-muted); flex-wrap:wrap;
        }
        .empty-hint-title { font-weight:600; color:var(--text); font-size:0.9rem; }
        .empty-hint-sub { font-size:0.825rem; color:var(--text-muted); }
        .empty-hint > div { flex:1; min-width:180px; }

        .filter-card { padding:1.25rem; display:flex; flex-direction:column; gap:1rem; }
        .filter-row { display:flex; gap:1rem; flex-wrap:wrap; }
        .filter-group { display:flex; flex-direction:column; gap:0.375rem; flex:1; min-width:180px; }
        .filter-label { font-size:0.8rem; font-weight:600; color:var(--text-muted); }
        .select-wrap { position:relative; display:flex; align-items:center; }
        .select-arrow { position:absolute; right:0.75rem; color:var(--text-light); pointer-events:none; }

        .rec-loading {
          display:flex; flex-direction:column; align-items:center; gap:0.75rem;
          padding:4rem 1rem; color:var(--text-muted); font-size:0.9rem;
        }
        .rec-spin { animation:rec-spin-anim 1s linear infinite; color:var(--primary); }
        @keyframes rec-spin-anim { to { transform:rotate(360deg); } }

        .rec-error {
          display:flex; align-items:center; gap:0.75rem;
          padding:1.25rem; color:var(--danger); flex-wrap:wrap;
        }

        .result-count { margin-bottom:1rem; }
        .count-num { color:var(--primary); font-size:1.25rem; font-weight:800; }
        .cert-grid {
          display:grid;
          grid-template-columns:repeat(auto-fill, minmax(300px, 1fr));
          gap:1rem;
        }
        .cert-card {
          padding:1.25rem; display:flex; flex-direction:column; gap:0.75rem;
          transition:box-shadow 0.22s ease, border-color 0.22s ease, transform 0.22s ease;
        }
        .cert-card:hover {
          box-shadow:0 8px 28px rgba(99,102,241,0.14), var(--shadow-md);
          border-color:rgba(99,102,241,0.2);
          transform:translateY(-3px);
        }
        .cert-top { display:flex; flex-direction:column; gap:0.3rem; }
        .cert-top-row { display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap; }
        .cert-name { font-size:1.05rem; font-weight:700; color:var(--text); }
        .cert-issuer { font-size:0.78rem; color:var(--text-light); }
        .cert-summary {
          font-size:0.825rem; color:var(--text-muted); line-height:1.55;
          display:-webkit-box; -webkit-line-clamp:2;
          -webkit-box-orient:vertical; overflow:hidden;
        }
        .cert-stages { display:flex; flex-wrap:wrap; gap:0.3rem; margin-left:auto; }
        .stage-badge { font-size:0.68rem; }
        .cert-jobs { display:flex; flex-wrap:wrap; gap:0.375rem; }
        .job-chip {
          padding:0.175rem 0.6rem; border-radius:var(--radius-xs);
          background:var(--surface-2); border:1px solid var(--border);
          font-size:0.75rem; color:var(--text-muted);
        }
        .cert-actions {
          display:flex; gap:1rem; padding-top:0.75rem;
          border-top:1px solid var(--border); margin-top:auto; align-items:center;
        }
        .roadmap-btn { margin-left:auto; }
        .text-btn-disabled {
          display:inline-flex; align-items:center; gap:0.375rem;
          font-size:0.875rem; font-weight:500;
          color:var(--text-light); cursor:not-allowed; user-select:none;
        }
        .no-results {
          grid-column:1/-1; text-align:center;
          padding:3rem 1rem; color:var(--text-muted); line-height:1.8;
        }
      `}</style>
    </div>
  );
};

export default Recommendation;
