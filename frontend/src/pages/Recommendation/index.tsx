// Content Hash: SHA256:TBD
import React, { useState, useMemo, useEffect, useCallback, useDeferredValue } from 'react';
import { CertFlowDiagram } from '../../components/charts/CertFlowDiagram';
import { getCertCandidates } from '../../api/client';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Search, Map, FileText, ChevronDown, AlertCircle,
  Loader2, ArrowLeft, ArrowRight, X, BookOpen, ExternalLink,
} from 'lucide-react';
import type { CertCandidate } from '../../types/cert';

const RISK_LABEL: Record<string, string> = {
  '1': '1단계', '2': '2단계', '3': '3단계', '4': '4단계', '5': '5단계',
};
const RISK_IDS: Record<string, string> = {
  '1': 'risk_0001', '2': 'risk_0002', '3': 'risk_0003',
  '4': 'risk_0004', '5': 'risk_0005',
};
const GRADE_LABEL: Record<string, string> = {
  '5_기능장': '기능장', '4_기술사': '기술사', '3_기사': '기사',
  '2_산업기사': '산업기사', '1_기능사': '기능사',
};
function gradeBadgeClass(tier: string): string {
  if (tier.startsWith('4') || tier.startsWith('5')) return 'badge-primary';
  if (tier.startsWith('3')) return 'badge-secondary';
  if (tier.startsWith('2')) return 'badge-success';
  if (tier.startsWith('1')) return 'badge-warning';
  return 'badge-neutral';
}
function gradeColor(tier: string): string {
  if (tier.startsWith('4') || tier.startsWith('5')) return '#6366f1';
  if (tier.startsWith('3')) return '#0ea5e9';
  if (tier.startsWith('2')) return '#10b981';
  if (tier.startsWith('1')) return '#f59e0b';
  return '#94a3b8';
}

interface EvidenceRow {
  doc_id: string;
  chunk_id: string;
  source_type: string;
  snippet: string;
  section_path: string[];
  source_url: string | null;
  cert_name?: string;
  similarity?: number | null;
}
interface EvidenceState {
  loading: boolean;
  rows: EvidenceRow[];
  error: string | null;
  fetched: boolean;
  certId: string;
}

interface RelatedCert {
  cert_id: string;
  cert_name: string;
  cert_grade_tier: string;
  relation_label: string;
  relation_type: string;
  avg_pass_rate: number | null;
}
interface DagState {
  loading: boolean;
  predecessors: RelatedCert[];
  successors: RelatedCert[];
  certId: string;
  fetched: boolean;
}

const Recommendation: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const stageParam  = searchParams.get('stage') ?? '';
  const domainParam = searchParams.get('domain') ?? '';
  const domainName  = searchParams.get('domainName') ?? '';
  const certIdParam = searchParams.get('cert') ?? '';

  const [allCerts, setAllCerts] = useState<CertCandidate[]>([]);
  const [certsLoading, setCertsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGrade, setSelectedGrade] = useState('');
  const deferredQuery = useDeferredValue(searchQuery);

  const [evidence, setEvidence] = useState<EvidenceState>({
    loading: false, rows: [], error: null, fetched: false, certId: '',
  });
  const [showEvidence, setShowEvidence] = useState(false);
  const [dag, setDag] = useState<DagState>({
    loading: false, predecessors: [], successors: [], certId: '', fetched: false,
  });

  useEffect(() => {
    let cancelled = false;
    getCertCandidates()
      .then((data: CertCandidate[]) => { if (!cancelled) { setAllCerts(data); setCertsLoading(false); } })
      .catch((err: Error) => { if (!cancelled) { setFetchError(err.message); setCertsLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  const riskId    = RISK_IDS[stageParam] ?? '';
  const riskLabel = RISK_LABEL[stageParam] ?? '';

  const filtered = useMemo(() => {
    return allCerts.filter(cert => {
      if (riskId      && !cert.recommended_risk_stages.includes(riskId))  return false;
      if (domainParam && !cert.related_domains.includes(domainParam))      return false;
      if (selectedGrade && cert.cert_grade_tier !== selectedGrade)         return false;
      const q = deferredQuery;
      if (q && !cert.cert_name.includes(q)) return false;
      return true;
    });
  }, [allCerts, riskId, domainParam, selectedGrade, deferredQuery]);

  const featuredCert = useMemo(
    () => allCerts.find(c => c.cert_id === certIdParam) ?? null,
    [allCerts, certIdParam],
  );

  const fetchEvidence = useCallback(async (certId: string) => {
    setEvidence({ loading: true, rows: [], error: null, fetched: false, certId });
    setShowEvidence(true);
    try {
      const res = await fetch('/api/v1/recommendations/evidence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cert_id: certId }),
      });
      const json = await res.json();
      if (json.success) {
        setEvidence({ loading: false, rows: json.data?.evidence ?? [], error: null, fetched: true, certId });
      } else {
        setEvidence({ loading: false, rows: [], error: json.error?.message ?? '오류 발생', fetched: true, certId });
      }
    } catch {
      setEvidence({ loading: false, rows: [], error: '서버에 연결할 수 없습니다.', fetched: true, certId });
    }
  }, []);

  const fetchDag = useCallback(async (certId: string) => {
    setDag({ loading: true, predecessors: [], successors: [], certId, fetched: false });
    try {
      const res = await fetch(`/api/v1/recommendations/related?cert_id=${encodeURIComponent(certId)}`);
      const json = await res.json();
      if (json.success) {
        setDag({
          loading: false,
          predecessors: json.data?.predecessors ?? [],
          successors: json.data?.successors ?? [],
          certId,
          fetched: true,
        });
      } else {
        setDag({ loading: false, predecessors: [], successors: [], certId, fetched: true });
      }
    } catch {
      setDag({ loading: false, predecessors: [], successors: [], certId, fetched: true });
    }
  }, []);

  function goToRoadmap(certId: string) {
    const p = new URLSearchParams();
    if (stageParam)  p.set('stage', stageParam);
    if (domainParam) p.set('domain', domainParam);
    if (domainName)  p.set('domainName', domainName);
    p.set('cert', certId);
    navigate(`/roadmap?${p.toString()}`);
  }

  const evidenceCertName = allCerts.find(c => c.cert_id === evidence.certId)?.cert_name ?? evidence.certId;

  return (
    <div className="rec-wrap">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} /> 뒤로
        </button>
        <h1 className="page-title">자격증 확인</h1>
        <p className="page-desc">
          {domainName && riskLabel
            ? <><strong>{domainName}</strong> 분야에서 <strong>{riskLabel}</strong>에 맞는 자격증을 골랐습니다.</>
            : domainName
              ? <><strong>{domainName}</strong> 분야 추천 자격증입니다.</>
              : '추천 자격증을 확인하세요.'}
        </p>
      </div>

      {featuredCert && (
        <div className="featured-cert card" style={{ borderLeftColor: gradeColor(featuredCert.cert_grade_tier) }}>
          <div className="featured-tag-row"><span className="featured-tag">로드맵에서 선택</span></div>
          <div className="featured-body">
            <span className={`badge ${gradeBadgeClass(featuredCert.cert_grade_tier)}`}>
              {GRADE_LABEL[featuredCert.cert_grade_tier] ?? featuredCert.cert_grade_tier}
            </span>
            <h2 className="featured-name">{featuredCert.cert_name}</h2>
            <p className="featured-issuer">{featuredCert.issuer}</p>
            <p className="featured-summary">{featuredCert.text_for_dense}</p>
          </div>
          <div className="featured-actions">
            <button className="btn-primary" onClick={() => { fetchEvidence(featuredCert.cert_id); fetchDag(featuredCert.cert_id); }}>
              <FileText size={15} /> 왜 추천됐나요
            </button>
            <button className="btn-ghost" onClick={() => goToRoadmap(featuredCert.cert_id)}>
              <Map size={15} /> 로드맵 보기
            </button>
          </div>
        </div>
      )}

      {showEvidence && (
        <div className="evidence-panel card">
          <div className="ev-header">
            <div className="ev-header-left">
              <BookOpen size={15} style={{ color: 'var(--primary)', flexShrink: 0 }} />
              <span className="ev-title">{evidenceCertName}을 추천하는 이유</span>
            </div>
            <button className="ev-close" onClick={() => setShowEvidence(false)}><X size={15} /></button>
          </div>

          {/* DAG 경로 */}
          {dag.fetched && (dag.predecessors.length > 0 || dag.successors.length > 0) && (
            <div className="dag-panel">
              <p className="dag-panel-title">관련 자격증 경로</p>
              <div className="dag-flow-scroll">
                <CertFlowDiagram
                  current={{ cert_id: dag.certId, cert_name: evidenceCertName }}
                  predecessors={dag.predecessors}
                  successors={dag.successors}
                  onNodeClick={(id) => { fetchEvidence(id); fetchDag(id); }}
                />
              </div>
            </div>
          )}

          {/* Evidence 섹션 */}
          {evidence.loading && (
            <div className="ev-loading"><Loader2 size={18} className="ev-spin" /><span>근거 정보를 불러오는 중…</span></div>
          )}
          {!evidence.loading && evidence.error && (
            <div className="ev-empty"><AlertCircle size={16} style={{ flexShrink: 0 }} /><span>{evidence.error}</span></div>
          )}
          {!evidence.loading && evidence.fetched && evidence.rows.length === 0 && !evidence.error && (
            <div className="ev-empty">
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>현재 근거 문서가 없습니다.</span>
            </div>
          )}
          {!evidence.loading && evidence.rows.length > 0 && (
            <div className="ev-list">
              <p className="ev-intro">공식 문서에서 찾아낸 이 자격증 관련 내용입니다. 아래 자료를 바탕으로 추천이 이루어졌습니다.</p>
              {evidence.rows.map((row, i) => {
                const pct = row.similarity != null ? Math.round(row.similarity * 100) : null;
                const isLocal = row.source_type === 'candidate' || row.source_type === 'local_candidates';
                return (
                  <div key={row.chunk_id || i} className="ev-row">
                    <div className="ev-row-header">
                      <span className={`ev-src-tag ${isLocal ? 'ev-src-local' : 'ev-src-db'}`}>
                        {isLocal ? '로컬' : 'DB'}
                      </span>
                      {row.section_path?.length > 0 && (
                        <span className="ev-section-label">{row.section_path.join(' › ')}</span>
                      )}
                      {pct != null && (
                        <div className="ev-score-wrap">
                          <div className="ev-score-track">
                            <div className="ev-score-fill" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="ev-score-pct">{pct}%</span>
                        </div>
                      )}
                      {row.source_url && (
                        <a href={row.source_url} target="_blank" rel="noreferrer" className="ev-link">
                          <ExternalLink size={11} /> 원문
                        </a>
                      )}
                    </div>
                    <p className="ev-snippet">{row.snippet}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      <div className="card filter-card">
        <div className="search-wrapper">
          <Search size={16} className="search-icon" />
          <input type="text" className="input search-input" placeholder="자격증명 검색…"
            value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
        </div>
        <div className="filter-row">
          <div className="filter-group">
            <label className="filter-label">등급 필터</label>
            <div className="select-wrap">
              <select className="select" value={selectedGrade} onChange={e => setSelectedGrade(e.target.value)}>
                <option value="">전체 등급</option>
                <option value="1_기능사">기능사</option>
                <option value="2_산업기사">산업기사</option>
                <option value="3_기사">기사</option>
                <option value="4_기술사">기술사</option>
                <option value="5_기능장">기능장</option>
              </select>
              <ChevronDown size={14} className="select-arrow" />
            </div>
          </div>
          <div className="active-filters">
            {domainName && <span className="filter-chip">{domainName}</span>}
            {riskLabel  && <span className="filter-chip">{riskLabel}</span>}
          </div>
        </div>
      </div>

      <section>
        {certsLoading ? (
          <div className="rec-loading"><Loader2 size={24} className="rec-spin" /><p>자격증 데이터를 불러오는 중…</p></div>
        ) : fetchError ? (
          <div className="rec-error card">
            <AlertCircle size={18} /><p>데이터 로드 실패: {fetchError}</p>
            <button className="btn-ghost" onClick={() => window.location.reload()}>다시 시도</button>
          </div>
        ) : (
          <>
            <p className="result-count">추천 자격증 <span className="count-num">{filtered.length}</span>건</p>
            <div className="cert-grid-scroll">
              <div className="cert-grid">
                {filtered.slice(0, 60).map(cert => (
                  <div key={cert.candidate_id} className="card cert-card">
                    <div className="cert-top">
                      <div className="cert-top-row">
                        <span className={`badge ${gradeBadgeClass(cert.cert_grade_tier)}`}>
                          {GRADE_LABEL[cert.cert_grade_tier] ?? cert.cert_grade_tier}
                        </span>
                        <span className="cert-issuer">{cert.issuer}</span>
                      </div>
                      <h3 className="cert-name">{cert.cert_name}</h3>
                      <p className="cert-summary">{cert.text_for_dense}</p>
                    </div>
                    <div className="cert-actions">
                      <button className="text-btn evidence-btn"
                        onClick={() => { fetchEvidence(cert.cert_id); fetchDag(cert.cert_id); }}
                        style={{ color: gradeColor(cert.cert_grade_tier) }}>
                        <FileText size={13} /> 추천 이유
                      </button>
                      <button className="text-btn roadmap-btn" onClick={() => goToRoadmap(cert.cert_id)}>
                        <Map size={13} /> 로드맵 <ArrowRight size={12} />
                      </button>
                    </div>
                  </div>
                ))}
                {filtered.length === 0 && (
                  <div className="no-results"><p>조건에 맞는 자격증이 없습니다.</p><p>검색어나 필터를 변경해보세요.</p></div>
                )}
              </div>
            </div>
          </>
        )}
      </section>

      <style>{`
        .rec-wrap{display:flex;flex-direction:column;gap:1.5rem}
        .back-btn{display:inline-flex;align-items:center;gap:.35rem;font-size:.85rem;font-weight:500;color:var(--text-muted);margin-bottom:.25rem;background:none;border:none;cursor:pointer;padding:0;transition:color .15s;width:fit-content}
        .back-btn:hover{color:var(--primary)}
        .featured-cert{border-left-width:4px;padding:1.5rem;display:flex;flex-direction:column;gap:.75rem}
        .featured-tag-row{display:flex}
        .featured-tag{font-size:.68rem;font-weight:700;letter-spacing:.07em;padding:.2rem .625rem;background:var(--primary-light);color:var(--primary);border-radius:var(--radius-full);border:1px solid rgba(99,102,241,.2)}
        .featured-body{display:flex;flex-direction:column;gap:.3rem}
        .featured-name{font-size:1.3rem;font-weight:800;color:var(--text);margin-top:.2rem}
        .featured-issuer{font-size:.78rem;color:var(--text-light)}
        .featured-summary{font-size:.875rem;color:var(--text-muted);line-height:1.65;margin-top:.2rem}
        .featured-actions{display:flex;gap:.75rem;flex-wrap:wrap;padding-top:.25rem}
        .evidence-panel{padding:1.25rem;display:flex;flex-direction:column;gap:.875rem;border-left:3px solid var(--primary)}
        .ev-header{display:flex;align-items:center;justify-content:space-between;gap:.75rem}
        .ev-header-left{display:flex;align-items:center;gap:.5rem;flex:1;min-width:0}
        .ev-title{font-size:.875rem;font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .ev-close{background:none;border:none;cursor:pointer;color:var(--text-light);padding:.2rem;flex-shrink:0;transition:color .15s}
        .ev-close:hover{color:var(--danger)}
        .ev-loading{display:flex;align-items:center;gap:.5rem;font-size:.875rem;color:var(--text-muted)}
        .ev-spin{animation:spin 1s linear infinite;color:var(--primary)}
        @keyframes spin{to{transform:rotate(360deg)}}
        .ev-empty{display:flex;align-items:flex-start;gap:.5rem;font-size:.84rem;color:var(--text-muted);line-height:1.6}
        .ev-intro{font-size:.8rem;color:var(--text-muted);line-height:1.65;padding-bottom:.25rem}
        .ev-list{display:flex;flex-direction:column;gap:.75rem}
        .dag-panel{display:flex;flex-direction:column;gap:.625rem;padding:.875rem;background:var(--surface-2);border-radius:var(--radius-sm);border:1px solid var(--border)}
        .dag-panel-title{font-size:.7rem;font-weight:700;color:var(--text-light);letter-spacing:.05em;text-transform:uppercase}
        .dag-flow-scroll{overflow-x:auto;padding-bottom:.25rem}
        .ev-row{padding:.875rem;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-sm);display:flex;flex-direction:column;gap:.5rem}
        .ev-row-header{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}
        .ev-source-badge{padding:.15rem .5rem;background:var(--primary-light);color:var(--primary);border-radius:var(--radius-xs);font-size:.64rem;font-weight:700;letter-spacing:.06em}
        .ev-src-tag{padding:.1rem .4rem;border-radius:3px;font-size:.62rem;font-weight:700;letter-spacing:.05em;flex-shrink:0}
        .ev-src-db{background:#ede9fe;color:#6d28d9}
        .ev-src-local{background:#f1f5f9;color:#64748b}
        .ev-score-wrap{display:flex;align-items:center;gap:.3rem;margin-left:auto}
        .ev-score-track{width:44px;height:4px;background:var(--border);border-radius:99px;overflow:hidden}
        .ev-score-fill{height:100%;background:var(--primary);border-radius:99px}
        .ev-score-pct{font-size:.66rem;font-weight:700;color:var(--primary);white-space:nowrap}
        .ev-section-label{font-size:.75rem;font-weight:700;color:var(--primary);padding:.1rem .5rem;background:var(--primary-light);border-radius:var(--radius-xs)}
        .ev-section{font-size:.75rem;color:var(--text-light)}
        .ev-link{display:inline-flex;align-items:center;gap:.25rem;font-size:.75rem;color:var(--secondary);text-decoration:none;margin-left:auto}
        .ev-link:hover{text-decoration:underline}
        .ev-snippet{font-size:.855rem;color:var(--text-muted);line-height:1.7;border-left:3px solid var(--primary-light);padding-left:.75rem}
        .filter-card{padding:1.25rem;display:flex;flex-direction:column;gap:.875rem}
        .filter-row{display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end}
        .filter-group{display:flex;flex-direction:column;gap:.375rem}
        .filter-label{font-size:.78rem;font-weight:600;color:var(--text-muted)}
        .select-wrap{position:relative;display:flex;align-items:center}
        .select-arrow{position:absolute;right:.75rem;color:var(--text-light);pointer-events:none}
        .active-filters{display:flex;gap:.375rem;flex-wrap:wrap;align-items:center;margin-left:auto}
        .filter-chip{padding:.25rem .75rem;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-full);font-size:.75rem;color:var(--text-muted)}
        .rec-loading{display:flex;flex-direction:column;align-items:center;gap:.75rem;padding:3rem 1rem;color:var(--text-muted);font-size:.9rem}
        .rec-spin{animation:spin 1s linear infinite;color:var(--primary)}
        .rec-error{display:flex;align-items:center;gap:.75rem;padding:1.25rem;color:var(--danger);flex-wrap:wrap}
        .result-count{margin-bottom:.875rem;font-size:.9rem;color:var(--text-muted)}
        .count-num{color:var(--primary);font-size:1.2rem;font-weight:800}
        .cert-grid-scroll{max-height:72vh;overflow-y:auto;padding-right:4px;scrollbar-width:thin;scrollbar-color:var(--border-strong) transparent}
        .cert-grid-scroll::-webkit-scrollbar{width:5px}
        .cert-grid-scroll::-webkit-scrollbar-thumb{background:var(--border-strong);border-radius:99px}
        .cert-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:.875rem}
        .cert-card{padding:1.125rem;display:flex;flex-direction:column;gap:.625rem;transition:box-shadow .2s,border-color .2s,transform .2s}
        .cert-card:hover{box-shadow:0 6px 24px rgba(99,102,241,.12),var(--shadow-md);border-color:rgba(99,102,241,.2);transform:translateY(-3px)}
        .cert-top{display:flex;flex-direction:column;gap:.25rem}
        .cert-top-row{display:flex;align-items:center;gap:.5rem;justify-content:space-between}
        .cert-name{font-size:.975rem;font-weight:700;color:var(--text)}
        .cert-issuer{font-size:.72rem;color:var(--text-light)}
        .cert-summary{font-size:.79rem;color:var(--text-muted);line-height:1.55;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
        .cert-actions{display:flex;gap:.75rem;padding-top:.625rem;border-top:1px solid var(--border);margin-top:auto;align-items:center}
        .text-btn{display:inline-flex;align-items:center;gap:.35rem;font-size:.82rem;font-weight:600;background:none;border:none;cursor:pointer;padding:0;transition:opacity .15s}
        .text-btn:hover{opacity:.75}
        .evidence-btn{color:var(--primary)}
        .roadmap-btn{color:var(--secondary);margin-left:auto}
        .no-results{grid-column:1/-1;text-align:center;padding:3rem 1rem;color:var(--text-muted);line-height:1.8}
      `}</style>
    </div>
  );
};

export default Recommendation;
