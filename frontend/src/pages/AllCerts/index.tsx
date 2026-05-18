// Content Hash: SHA256:TBD
// Role: 전체 자격증 자유 탐색 페이지 (진단 흐름과 독립).
//   - 검색 (cert_name / 직무명)
//   - 등급 필터
//   - 도메인 필터
//   - 1290개 그리드 (스크롤)
//   - 카드 클릭 → 해당 자격증의 추천 페이지로 이동 (cert 파라미터 전달)
import React, { useState, useMemo, useEffect, useDeferredValue, memo } from 'react';
import { Link } from 'react-router-dom';
import { Search, ChevronDown, AlertCircle, Loader2, ArrowRight } from 'lucide-react';
import { getCertCandidates } from '../../api/client';
import type { CertCandidate } from '../../types/cert';

const DOMAIN_NAMES: Record<string, string> = {
  domain_0001:'데이터/AI', domain_0002:'소프트웨어개발', domain_0003:'IT인프라/보안',
  domain_0004:'정보통신/무선', domain_0005:'전기/전자', domain_0006:'기계/제조',
  domain_0007:'재료/금속', domain_0008:'화학/바이오', domain_0009:'에너지/원자력',
  domain_0010:'건축/실내건축', domain_0011:'토목/측량/공간정보', domain_0012:'환경/안전',
  domain_0013:'자동차/모빌리티정비', domain_0014:'소방/방재', domain_0015:'비파괴검사/품질검사',
  domain_0016:'금융/회계', domain_0017:'경영/사무', domain_0018:'유통/물류/무역',
  domain_0019:'영업/CS', domain_0020:'부동산/감정/주택관리', domain_0021:'공공/행정',
  domain_0022:'법률', domain_0023:'의료/보건', domain_0024:'사회복지/상담',
  domain_0025:'스포츠/레저/재활', domain_0026:'반려동물/생활케어', domain_0027:'교육',
  domain_0028:'언어/문서/속기', domain_0029:'관광/항공/호텔', domain_0030:'조리/식품',
  domain_0031:'미용/패션', domain_0032:'의류/패션제작', domain_0033:'디자인',
  domain_0034:'콘텐츠/미디어', domain_0035:'공예/목재/주얼리', domain_0036:'음악/공연',
  domain_0037:'문화유산/보존수리', domain_0038:'농림/축산/수산', domain_0039:'광산',
  domain_0040:'철도/교통운송', domain_0041:'선박/해양', domain_0042:'항공/조종',
  domain_0043:'국방/특수',
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

function buildSummary(cert: CertCandidate): string {
  const domain = DOMAIN_NAMES[cert.primary_domain] ?? '';
  const sessions = cert.exam_sessions_per_year;
  const parts: string[] = [];
  if (domain) parts.push(domain + ' 분야');
  if (sessions !== null && sessions !== undefined) {
    parts.push(sessions === 0 ? '상시 시험' : `연 ${sessions}회 시험`);
  }
  return parts.join(' · ');
}

function trendIcon(trend: string | null | undefined): string {
  if (trend === 'up') return '↑';
  if (trend === 'down') return '↓';
  return '→';
}

function trendClass(trend: string | null | undefined): string {
  if (trend === 'up') return 'trend-up';
  if (trend === 'down') return 'trend-down';
  return 'trend-flat';
}

// 카드 — 클릭 시 추천 페이지로 cert_id만 들고 이동
const CertCardSimple = memo(({ cert }: { cert: CertCandidate }) => {
  const summary = buildSummary(cert);
  const hasWritten = cert.written_avg_pass_rate !== null && cert.written_avg_pass_rate !== undefined;
  const hasPractical = cert.practical_avg_pass_rate !== null && cert.practical_avg_pass_rate !== undefined;
  const hasAvg = cert.avg_pass_rate_3yr !== null && cert.avg_pass_rate_3yr !== undefined;
  const hasTrend = cert.acq_trend !== null && cert.acq_trend !== undefined;

  return (
    <Link
      to={`/recommendation?from=certs&cert=${encodeURIComponent(cert.cert_id)}${cert.primary_domain ? `&domain=${cert.primary_domain}&domainName=${encodeURIComponent(DOMAIN_NAMES[cert.primary_domain] ?? '')}` : ''}`}
      className="card cert-card-ac"
    >
      <div className="cert-top">
        <div className="cert-top-row">
          <span className={`badge ${gradeBadgeClass(cert.cert_grade_tier)}`}>
            {GRADE_LABEL[cert.cert_grade_tier] ?? cert.cert_grade_tier}
          </span>
          <span className="cert-issuer">{cert.issuer}</span>
        </div>
        <h3 className="cert-name">{cert.cert_name}</h3>
        {summary && <p className="cert-summary">{summary}</p>}
        <div className="cert-rate-row">
          {hasWritten && (
            <span className="cert-rate-badge cert-rate-written">
              필기 {Math.round(cert.written_avg_pass_rate!)}%
            </span>
          )}
          {hasPractical && (
            <span className="cert-rate-badge cert-rate-practical">
              실기 {Math.round(cert.practical_avg_pass_rate!)}%
            </span>
          )}
          {!hasWritten && !hasPractical && hasAvg && (
            <span className="cert-rate-badge cert-rate-avg">
              합격률 {Math.round(cert.avg_pass_rate_3yr!)}%
            </span>
          )}
          {hasTrend && (
            <span className={`cert-trend ${trendClass(cert.acq_trend)}`}>
              {trendIcon(cert.acq_trend)}
            </span>
          )}
        </div>
      </div>
      <div className="cert-actions">
        <span className="cert-cta-hint">자세히 보기 <ArrowRight size={12} /></span>
      </div>
    </Link>
  );
});

const PAGE_SIZE = 60;

const AllCerts: React.FC = () => {
  const [allCerts, setAllCerts] = useState<CertCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGrade, setSelectedGrade] = useState('');
  const [selectedDomain, setSelectedDomain] = useState('');
  const [page, setPage] = useState(1);
  const deferredQuery = useDeferredValue(searchQuery);

  useEffect(() => {
    let cancelled = false;
    getCertCandidates()
      .then((data: CertCandidate[]) => {
        if (!cancelled) { setAllCerts(data); setLoading(false); }
      })
      .catch((err: Error) => {
        if (!cancelled) { setFetchError(err.message); setLoading(false); }
      });
    return () => { cancelled = true; };
  }, []);

  const filtered = useMemo(() => {
    setPage(1); // reset page on filter change
    return allCerts.filter(cert => {
      if (selectedGrade && cert.cert_grade_tier !== selectedGrade) return false;
      if (selectedDomain && cert.primary_domain !== selectedDomain) return false;
      const q = deferredQuery.trim();
      if (q && !cert.cert_name.includes(q) && !(cert.aliases ?? []).some(a => a.includes(q))) return false;
      return true;
    });
  }, [allCerts, selectedGrade, selectedDomain, deferredQuery]);

  const visibleCerts = useMemo(() => filtered.slice(0, page * PAGE_SIZE), [filtered, page]);
  const hasMore = filtered.length > page * PAGE_SIZE;

  // 도메인 정렬 (배지 형태 토글)
  const domainOptions = useMemo(() => {
    return Object.entries(DOMAIN_NAMES).sort((a, b) => a[1].localeCompare(b[1], 'ko'));
  }, []);

  return (
    <div className="ac-wrap">
      <div className="page-header">
        <h1 className="page-title">전체 자격증</h1>
        <p className="page-desc">
          진단 없이 관심 있는 자격증을 직접 검색하고 둘러보세요. 클릭하면 상세 정보와 로드맵을 볼 수 있어요.
        </p>
      </div>

      <div className="card filter-card-ac">
        <div className="search-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            className="input search-input"
            placeholder="자격증명 또는 별칭 검색…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="filter-row-ac">
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

          <div className="filter-group">
            <label className="filter-label">분야 필터</label>
            <div className="select-wrap">
              <select className="select" value={selectedDomain} onChange={e => setSelectedDomain(e.target.value)}>
                <option value="">전체 분야</option>
                {domainOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </select>
              <ChevronDown size={14} className="select-arrow" />
            </div>
          </div>
        </div>
      </div>

      <section>
        {loading ? (
          <div className="ac-loading"><Loader2 size={24} className="ac-spin" /><p>자격증 데이터를 불러오는 중…</p></div>
        ) : fetchError ? (
          <div className="ac-error card">
            <AlertCircle size={18} /><p>데이터 로드 실패: {fetchError}</p>
            <button className="btn-ghost" onClick={() => window.location.reload()}>다시 시도</button>
          </div>
        ) : (
          <>
            <div className="ac-result-row">
              <p className="result-count">
                전체 자격증 <span className="count-num">{filtered.length}</span>건
                {hasMore && (
                  <span className="result-hint"> · {visibleCerts.length}건 표시 중</span>
                )}
              </p>
              {(searchQuery || selectedGrade || selectedDomain) && (
                <button
                  type="button"
                  className="text-btn"
                  onClick={() => { setSearchQuery(''); setSelectedGrade(''); setSelectedDomain(''); setPage(1); }}
                >
                  필터 초기화
                </button>
              )}
            </div>
            <div className="cert-grid-ac">
              {visibleCerts.map(cert => (
                <CertCardSimple key={cert.candidate_id} cert={cert} />
              ))}
              {filtered.length === 0 && (
                <div className="no-results">
                  <p className="no-results-title">조건에 맞는 자격증이 없습니다.</p>
                  <p className="no-results-sub">검색어나 필터를 바꿔보세요.</p>
                </div>
              )}
            </div>
            {hasMore && (
              <div className="ac-load-more">
                <button
                  type="button"
                  className="btn-ghost ac-load-btn"
                  onClick={() => setPage(p => p + 1)}
                >
                  더 보기 ({filtered.length - visibleCerts.length}건 남음)
                </button>
              </div>
            )}
          </>
        )}
      </section>

      <style>{`
        .ac-wrap{display:flex;flex-direction:column;gap:1.5rem}
        .page-header{display:flex;flex-direction:column;gap:.375rem}
        .filter-card-ac{padding:1.25rem;display:flex;flex-direction:column;gap:.875rem}
        .filter-row-ac{display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end}
        .filter-group{display:flex;flex-direction:column;gap:.375rem;min-width:160px}
        .filter-label{font-size:.78rem;font-weight:600;color:var(--text-muted)}
        .select-wrap{position:relative;display:flex;align-items:center}
        .select-arrow{position:absolute;right:.75rem;color:var(--text-light);pointer-events:none}
        .ac-loading{display:flex;flex-direction:column;align-items:center;gap:.75rem;padding:3rem 1rem;color:var(--text-muted);font-size:.9rem}
        .ac-spin{animation:spin 1s linear infinite;color:var(--primary)}
        @keyframes spin{to{transform:rotate(360deg)}}
        .ac-error{display:flex;align-items:center;gap:.75rem;padding:1.25rem;color:var(--danger);flex-wrap:wrap}
        .ac-result-row{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:.875rem;flex-wrap:wrap}
        .result-count{font-size:.9rem;color:var(--text-muted)}
        .count-num{color:var(--primary);font-size:1.2rem;font-weight:800;margin:0 .15rem}
        .result-hint{font-size:.78rem;color:var(--text-light);margin-left:.4rem}
        .cert-grid-ac{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:.875rem;max-height:74vh;overflow-y:auto;padding-right:4px;scrollbar-width:thin;scrollbar-color:var(--border-strong) transparent}
        .cert-grid-ac::-webkit-scrollbar{width:5px}
        .cert-grid-ac::-webkit-scrollbar-thumb{background:var(--border-strong);border-radius:99px}
        .cert-card-ac{padding:1.125rem;display:flex;flex-direction:column;gap:.625rem;text-decoration:none;color:inherit;transition:box-shadow .2s,border-color .2s,transform .2s}
        .cert-card-ac:hover{box-shadow:0 6px 24px rgba(37,99,235,.14),var(--shadow-md);border-color:rgba(37,99,235,.3);transform:translateY(-3px)}
        .cert-top{display:flex;flex-direction:column;gap:.25rem}
        .cert-top-row{display:flex;align-items:center;gap:.5rem;justify-content:space-between}
        .cert-name{font-size:.975rem;font-weight:700;color:var(--text)}
        .cert-issuer{font-size:.72rem;color:var(--text-light)}
        .cert-summary{font-size:.79rem;color:var(--text-muted);line-height:1.55;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
        .cert-rate-row{display:flex;gap:.35rem;flex-wrap:wrap;margin-top:.35rem;align-items:center}
        .cert-rate-badge{font-size:.7rem;font-weight:600;padding:.15rem .45rem;border-radius:4px;white-space:nowrap}
        .cert-rate-written{background:#eef2ff;color:#4f46e5}
        .cert-rate-practical{background:#ecfeff;color:#0891b2}
        .cert-rate-avg{background:#f0fdf4;color:#16a34a}
        .cert-trend{font-size:.7rem;font-weight:700;padding:.15rem .45rem;border-radius:4px;white-space:nowrap;margin-left:auto}
        .trend-up{background:#fef3c7;color:#d97706}
        .trend-down{background:#fce7f3;color:#be185d}
        .trend-flat{background:#f3f4f6;color:#6b7280}
        .cert-actions{display:flex;gap:.75rem;padding-top:.625rem;border-top:1px solid var(--border);margin-top:auto;align-items:center}
        .cert-cta-hint{font-size:.78rem;font-weight:600;color:var(--primary);display:inline-flex;align-items:center;gap:.3rem}
        .no-results{grid-column:1/-1;text-align:center;padding:2.5rem 1.25rem;line-height:1.8;display:flex;flex-direction:column;gap:.5rem}
        .no-results-title{font-size:.95rem;font-weight:700;color:var(--text)}
        .no-results-sub{font-size:.85rem;color:var(--text-muted);line-height:1.65}
        .ac-load-more{display:flex;justify-content:center;padding:.75rem 0}
        .ac-load-btn{padding:.5rem 1.5rem;font-size:.85rem;font-weight:600}
      `}</style>
    </div>
  );
};

export default AllCerts;
