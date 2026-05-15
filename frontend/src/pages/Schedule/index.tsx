// Content Hash: SHA256:TBD
import React, { useState, useCallback, useRef } from 'react';
import { Search, Calendar, Clock, AlertCircle, Loader2, ExternalLink } from 'lucide-react';
import { getCertCandidates } from '../../api/client';

// ── types ──────────────────────────────────────────────────────────────────
interface ScheduleItem {
  impl_year: string | null;
  impl_seq: string | null;
  impl_seq_name: string | null;
  registration_start: string | null;
  registration_end: string | null;
  exam_start: string | null;
  exam_end: string | null;
  pass_announce_date: string | null;
  d_day_exam: number | null;
  d_day_registration: number | null;
}

interface CertSchedule {
  cert_id: string;
  cert_name: string;
  cert_type: 'tech' | 'private';
  year: string;
  schedules: ScheduleItem[];
  total: number;
}

interface ProfExamResult {
  cert_name: string;
  schedules: Record<string, unknown>[];
  total: number;
  source?: string;
}

type UnifiedResult =
  | { kind: 'tech' | 'private'; data: CertSchedule }
  | { kind: 'prof'; data: ProfExamResult };

// ── helpers ────────────────────────────────────────────────────────────────
const TECH_TIERS = ['기사', '산업기사', '기능사', '기능장', '기술사'];
function getTechType(tier: string): 'tech' | 'private' {
  return TECH_TIERS.some(t => tier.includes(t)) ? 'tech' : 'private';
}

function fmt(s: string | null): string {
  if (!s) return '-';
  const c = s.replace(/-/g, '');
  if (c.length === 8) return `${c.slice(0,4)}.${c.slice(4,6)}.${c.slice(6,8)}`;
  return s;
}

function DdayBadge({ dday }: { dday: number | null }) {
  if (dday === null) return null;
  if (dday < 0)  return <span className="sch-badge sch-badge-past">마감</span>;
  if (dday === 0) return <span className="sch-badge sch-badge-today">D-Day</span>;
  if (dday <= 7) return <span className="sch-badge sch-badge-urgent">D-{dday}</span>;
  if (dday <= 30) return <span className="sch-badge sch-badge-soon">D-{dday}</span>;
  return <span className="sch-badge sch-badge-future">D-{dday}</span>;
}

// ── Tech/Private cert card ─────────────────────────────────────────────────
function TechCard({ data }: { data: CertSchedule }) {
  const upcoming = data.schedules.filter(s => (s.d_day_exam ?? -1) >= 0);
  const nearest  = upcoming[0] ?? data.schedules[0];
  const typeLabel = data.cert_type === 'tech' ? '국가기술' : '국가자격';
  const typeCls   = data.cert_type === 'tech' ? 'sch-type-tech' : 'sch-type-private';

  return (
    <div className="sch-card">
      <div className="sch-card-header-info">
        <div className="sch-card-title-row">
          <span className="sch-cert-name">{data.cert_name}</span>
          <span className={`sch-type-badge ${typeCls}`}>{typeLabel}</span>
          {nearest && <DdayBadge dday={nearest.d_day_exam} />}
        </div>
        <div className="sch-card-meta">
          {data.year && <span className="sch-year">{data.year}년</span>}
          <span className="sch-count">총 {data.total}회차</span>
          {nearest?.exam_start && (
            <span className="sch-nearest"><Clock size={11} /> 최근 시험: {fmt(nearest.exam_start)}</span>
          )}
        </div>
      </div>

      {data.schedules.length === 0 ? (
        <p className="sch-empty-text">예정된 시험 일정이 없습니다.</p>
      ) : (
        <div className="sch-table-wrap">
          <table className="sch-table">
            <thead>
              <tr>
                <th>회차</th>
                <th>접수 기간</th>
                <th>시험 기간</th>
                <th>합격 발표</th>
                <th>시험 D-Day</th>
                <th>접수 D-Day</th>
              </tr>
            </thead>
            <tbody>
              {data.schedules.map((s, i) => (
                <tr key={i} className={(s.d_day_exam ?? 0) < 0 ? 'sch-row-past' : ''}>
                  <td className="sch-td-seq">{s.impl_seq_name ?? `${s.impl_seq}회`}</td>
                  <td>{fmt(s.registration_start)}{s.registration_end ? ` ~ ${fmt(s.registration_end)}` : ''}</td>
                  <td>{fmt(s.exam_start)}{s.exam_end && s.exam_end !== s.exam_start ? ` ~ ${fmt(s.exam_end)}` : ''}</td>
                  <td>{fmt(s.pass_announce_date)}</td>
                  <td><DdayBadge dday={s.d_day_exam} /></td>
                  <td>
                    {s.d_day_registration === null || s.d_day_registration === undefined
                      ? <span className="sch-badge-none">—</span>
                      : s.d_day_registration < 0
                        ? <span className="sch-badge sch-badge-past">접수마감</span>
                        : s.d_day_registration === 0
                          ? <span className="sch-badge sch-badge-today">접수오늘</span>
                          : <span className="sch-badge sch-badge-reg">접수 D-{s.d_day_registration}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <a
        className="sch-qnet-link"
        href={`https://www.q-net.or.kr/crf005.do?id=crf00503s&jmNm=${encodeURIComponent(data.cert_name)}`}
        target="_blank" rel="noopener noreferrer"
      >
        <ExternalLink size={12} /> Q-Net 원서접수
      </a>
      <p className="sch-source">한국산업인력공단 Q-Net</p>
    </div>
  );
}

// ── Professional cert card ─────────────────────────────────────────────────
function ProfCard({ data }: { data: ProfExamResult }) {
  const keys = data.schedules.length > 0
    ? Object.keys(data.schedules[0]).filter(k => k !== 'cert_name')
    : [];

  const FIELD_KO: Record<string, string> = {
    examNm: '시험명', implYy: '연도', jmFldNm: '종목명',
    wtmnYmd: '필기 시험일', ptmnYmd: '실기 시험일',
    docAplyStartDt: '필기 접수 시작', docAplyEndDt: '필기 접수 마감',
    pracAplyStartDt: '실기 접수 시작', pracAplyEndDt: '실기 접수 마감',
    docPassDt: '필기 합격 발표', pracPassDt: '실기 합격 발표',
    implSeq: '회차', entrsFee: '응시료',
  };

  return (
    <div className="sch-card">
      <div className="sch-card-header-info">
        <div className="sch-card-title-row">
          <span className="sch-cert-name">{data.cert_name}</span>
          <span className="sch-type-badge sch-type-prof">국가전문</span>
          {data.total > 0 && <span className="sch-badge sch-badge-future">{data.total}건</span>}
        </div>
        {data.source && <div className="sch-card-meta"><span className="sch-year">{data.source}</span></div>}
      </div>

      {data.schedules.length === 0 ? (
        <p className="sch-empty-text">일정 정보가 없습니다.</p>
      ) : keys.length > 0 ? (
        <div className="sch-table-wrap">
          <table className="sch-table">
            <thead>
              <tr>{keys.map(k => <th key={k}>{FIELD_KO[k] ?? k}</th>)}</tr>
            </thead>
            <tbody>
              {data.schedules.map((s, i) => (
                <tr key={i}>
                  {keys.map(k => <td key={k}>{String(s[k] ?? '-')}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="sch-prof-kv">
          {data.schedules.map((s, i) => (
            <div key={i} className="sch-prof-kv-row">
              {Object.entries(s).filter(([k]) => k !== 'cert_name').map(([k, v]) => (
                <div key={k} className="sch-prof-kv-item">
                  <span className="sch-prof-kv-label">{FIELD_KO[k] ?? k}</span>
                  <span className="sch-prof-kv-val">{String(v ?? '-')}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
      <a
        className="sch-qnet-link"
        href={`https://www.q-net.or.kr/crf005.do?id=crf00503s&jmNm=${encodeURIComponent(data.cert_name)}`}
        target="_blank" rel="noopener noreferrer"
      >
        <ExternalLink size={12} /> Q-Net 원서접수
      </a>
      <p className="sch-source">한국산업인력공단 Q-Net</p>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────
const Schedule: React.FC = () => {
  const [query, setQuery]     = useState('');
  const [results, setResults] = useState<UnifiedResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const techCacheRef = useRef<Record<string, CertSchedule>>({});
  const profCacheRef = useRef<Record<string, ProfExamResult | null>>({});

  const fetchTechSchedule = useCallback(async (certId: string, certName: string, tier: string): Promise<CertSchedule | null> => {
    if (techCacheRef.current[certId]) return techCacheRef.current[certId];
    try {
      const r    = await fetch(`/api/v1/schedules/exams/${encodeURIComponent(certId)}`);
      const json = await r.json();
      if (json.success && json.data) {
        const item: CertSchedule = {
          cert_id:   certId,
          cert_name: json.data.cert_name ?? certName,
          cert_type: getTechType(tier),
          year:      json.data.year ?? '',
          schedules: json.data.schedules ?? [],
          total:     json.data.total ?? 0,
        };
        techCacheRef.current[certId] = item;
        return item;
      }
    } catch { /* silent */ }
    return null;
  }, []);

  const fetchProfSchedule = useCallback(async (q: string): Promise<ProfExamResult | null> => {
    if (q in profCacheRef.current) return profCacheRef.current[q];
    try {
      const r    = await fetch(`/api/v1/schedules/professional-exams?cert_name=${encodeURIComponent(q)}`);
      const json = await r.json();
      if (json.success && json.data) {
        const item: ProfExamResult = {
          cert_name: json.data.cert_name ?? q,
          schedules: json.data.schedules ?? [],
          total:     json.data.total ?? 0,
          source:    json.data.source,
        };
        profCacheRef.current[q] = item;
        return item;
      }
    } catch { /* silent */ }
    profCacheRef.current[q] = null;
    return null;
  }, []);

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;

    setLoading(true);
    setError(null);
    setSearched(true);
    setResults([]);

    try {
      const [allCerts, profResult] = await Promise.all([
        getCertCandidates(),
        fetchProfSchedule(q),
      ]);

      const matched = allCerts
        .filter(c =>
          c.cert_name.includes(q) ||
          (c.aliases ?? []).some((a: string) => a.includes(q))
        )
        .slice(0, 8);

      const settled = await Promise.allSettled(
        matched.map(c => fetchTechSchedule(c.cert_id, c.cert_name, c.cert_grade_tier ?? ''))
      );

      const unified: UnifiedResult[] = [];

      // Professional result first if found
      if (profResult && profResult.total > 0) {
        unified.push({ kind: 'prof', data: profResult });
      }

      // Tech/private results
      for (const r of settled) {
        if (r.status === 'fulfilled' && r.value) {
          unified.push({ kind: r.value.cert_type, data: r.value });
        }
      }

      setResults(unified);
    } catch {
      setError('일정 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
    setLoading(false);
  }, [query, fetchTechSchedule, fetchProfSchedule]);

  return (
    <div className="sch-wrap">
      <div className="sch-header">
        <h1 className="sch-title">시험 일정</h1>
        <p className="sch-sub">Q-Net 국가기술자격·국가전문자격 시험 일정 통합 검색</p>
      </div>

      <form className="sch-search-form" onSubmit={handleSearch}>
        <div className="sch-search-inner">
          <Search size={16} className="sch-search-icon" />
          <input
            className="sch-search-input"
            type="text"
            placeholder="자격증명 검색 (예: 정보처리기사, 직업상담사, 건축사, 산업안전기사)"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
          <button type="submit" className="btn-primary sch-search-btn" disabled={loading}>
            {loading ? <Loader2 size={15} className="spin" /> : '검색'}
          </button>
        </div>
        <p className="sch-search-hint">국가기술·국가전문자격을 동시에 검색합니다 (Q-Net 데이터 기반)</p>
      </form>

      {error && (
        <div className="sch-error"><AlertCircle size={16} /><span>{error}</span></div>
      )}
      {loading && (
        <div className="sch-loading">
          <Loader2 size={20} className="spin" />
          <span>시험 일정을 조회하는 중…</span>
        </div>
      )}

      {!loading && searched && results.length === 0 && !error && (
        <div className="sch-empty">
          <AlertCircle size={18} />
          <p>"{query}"에 대한 시험 일정을 찾지 못했습니다. 자격증 이름을 정확히 입력해 주세요.</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="sch-results">
          <p className="sch-result-count">{results.length}개 자격증 일정</p>
          {results.map((r, i) =>
            r.kind === 'prof'
              ? <ProfCard key={`prof-${i}`} data={r.data} />
              : <TechCard key={(r.data as CertSchedule).cert_id} data={r.data as CertSchedule} />
          )}
        </div>
      )}

      {!searched && !loading && (
        <div className="sch-guide">
          <div className="sch-guide-card">
            <Calendar size={26} className="sch-guide-icon" />
            <h3>국가기술자격</h3>
            <p>기사·산업기사·기능사·기능장·기술사 등 한국산업인력공단 관할 자격증 시험 일정</p>
          </div>
          <div className="sch-guide-card">
            <Clock size={26} className="sch-guide-icon" />
            <h3>국가전문자격</h3>
            <p>의사·약사·건축사·변호사 등 국가전문자격 시험 일정 (Q-Net 국가전문자격 API)</p>
          </div>
          <div className="sch-guide-card">
            <ExternalLink size={26} className="sch-guide-icon" />
            <h3>공인민간자격</h3>
            <p>국가공인 민간자격증 시험 일정·접수일·합격 발표일 D-Day 표시</p>
          </div>
        </div>
      )}

      <style>{`
        .sch-wrap { display:flex; flex-direction:column; gap:1.5rem; max-width:860px; margin:0 auto; }
        .sch-header { display:flex; flex-direction:column; gap:.3rem; }
        .sch-title { font-size:1.75rem; font-weight:900; color:var(--text); margin:0; }
        .sch-sub { font-size:.875rem; color:var(--text-muted); margin:0; }

        .sch-search-form { display:flex; flex-direction:column; gap:.375rem; }
        .sch-search-inner {
          display:flex; align-items:center; gap:.625rem;
          background:var(--surface-2); border:1px solid var(--border);
          border-radius:var(--radius-sm); padding:.5rem .75rem;
          transition:border-color .15s;
        }
        .sch-search-inner:focus-within { border-color:var(--primary); }
        .sch-search-icon { color:var(--text-light); flex-shrink:0; }
        .sch-search-input { flex:1; border:none; background:transparent; font-size:.9rem; color:var(--text); outline:none; }
        .sch-search-input::placeholder { color:var(--text-light); }
        .sch-search-btn { padding:.45rem 1rem; font-size:.85rem; }
        .sch-search-hint { font-size:.72rem; color:var(--text-light); margin:0; }

        .sch-results { display:flex; flex-direction:column; gap:1rem; }
        .sch-result-count { font-size:.78rem; color:var(--text-muted); margin:0; font-weight:600; }

        .sch-card {
          border:1px solid var(--border); border-radius:var(--radius-sm);
          background:var(--surface-2); padding:1rem 1.125rem;
          display:flex; flex-direction:column; gap:.75rem;
        }
        .sch-card-header-info { display:flex; flex-direction:column; gap:.25rem; }
        .sch-card-title-row { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; }
        .sch-cert-name { font-size:1rem; font-weight:800; color:var(--text); }
        .sch-card-meta { display:flex; align-items:center; gap:.625rem; flex-wrap:wrap; }
        .sch-year { font-size:.73rem; color:var(--text-light); }
        .sch-count { font-size:.73rem; color:var(--text-light); }
        .sch-nearest { font-size:.73rem; color:var(--text-muted); display:flex; align-items:center; gap:.25rem; }

        .sch-type-badge {
          display:inline-flex; align-items:center; padding:.15rem .5rem;
          border-radius:20px; font-size:.66rem; font-weight:700; letter-spacing:.04em;
        }
        .sch-type-tech    { background:#dbeafe; color:#1e40af; }
        .sch-type-private { background:#fef3c7; color:#92400e; }
        .sch-type-prof    { background:#f3e8ff; color:#6d28d9; }

        .sch-badge { display:inline-flex; align-items:center; padding:.15rem .5rem; border-radius:20px; font-size:.7rem; font-weight:700; }
        .sch-badge-past    { background:#f1f5f9; color:#94a3b8; }
        .sch-badge-today   { background:#fee2e2; color:#ef4444; }
        .sch-badge-urgent  { background:#fee2e2; color:#ef4444; }
        .sch-badge-soon    { background:#fef3c7; color:#d97706; }
        .sch-badge-future  { background:#e0f2fe; color:#0284c7; }
        .sch-badge-reg     { background:#f0fdf4; color:#16a34a; }
        .sch-badge-none    { color:var(--text-light); font-size:.72rem; }

        .sch-table-wrap { overflow-x:auto; border:1px solid var(--border); border-radius:6px; }
        .sch-table { width:100%; border-collapse:collapse; font-size:.8rem; }
        .sch-table th {
          padding:.45rem .75rem; text-align:left;
          font-size:.72rem; font-weight:700; color:var(--text-muted);
          background:var(--surface-3,#f8fafc); border-bottom:1px solid var(--border);
          white-space:nowrap;
        }
        .sch-table td { padding:.45rem .75rem; color:var(--text-muted); border-bottom:1px solid var(--border); white-space:nowrap; }
        .sch-table tr:last-child td { border-bottom:none; }
        .sch-row-past td { opacity:.45; }
        .sch-td-seq { font-weight:700; color:var(--text); }

        .sch-prof-kv { display:flex; flex-direction:column; gap:.5rem; }
        .sch-prof-kv-row { display:flex; flex-wrap:wrap; gap:.375rem; }
        .sch-prof-kv-item { display:flex; gap:.35rem; align-items:baseline; }
        .sch-prof-kv-label { font-size:.7rem; font-weight:700; color:var(--text-muted); white-space:nowrap; }
        .sch-prof-kv-val   { font-size:.8rem; color:var(--text); }

        .sch-qnet-link {
          display:inline-flex; align-items:center; gap:.35rem;
          font-size:.78rem; color:var(--primary); text-decoration:none;
          padding:.3rem .75rem; border:1px solid var(--primary);
          border-radius:var(--radius-sm); width:fit-content; transition:background .15s;
        }
        .sch-qnet-link:hover { background:var(--primary-light); }
        .sch-empty-text { font-size:.85rem; color:var(--text-light); margin:0; }
        .sch-source { font-size:.65rem; color:#94a3b8; margin:0; }

        .sch-loading { display:flex; align-items:center; gap:.75rem; padding:2.5rem; justify-content:center; color:var(--text-muted); font-size:.9rem; }
        .sch-error { display:flex; align-items:center; gap:.625rem; padding:1rem 1.25rem; background:#fef2f2; border:1px solid #fecaca; border-radius:var(--radius-sm); color:#dc2626; font-size:.875rem; }
        .sch-empty { display:flex; align-items:flex-start; gap:.625rem; padding:2rem; background:var(--surface-2); border:1px dashed var(--border); border-radius:var(--radius-sm); color:var(--text-muted); font-size:.875rem; }
        .spin { animation:spin 1s linear infinite; }
        @keyframes spin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }

        .sch-guide { display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; }
        @media (max-width:640px) { .sch-guide { grid-template-columns:1fr; } }
        .sch-guide-card { display:flex; flex-direction:column; gap:.5rem; padding:1.125rem; background:var(--surface-2); border:1px solid var(--border); border-radius:var(--radius-sm); }
        .sch-guide-icon { color:var(--primary); }
        .sch-guide-card h3 { font-size:.9rem; font-weight:700; color:var(--text); margin:0; }
        .sch-guide-card p { font-size:.8rem; color:var(--text-muted); margin:0; line-height:1.65; }
      `}</style>
    </div>
  );
};

export default Schedule;
