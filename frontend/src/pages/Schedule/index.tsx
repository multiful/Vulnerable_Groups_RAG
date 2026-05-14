// Content Hash: SHA256:TBD
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Search, Calendar, Clock, AlertCircle, Loader2, ChevronDown, ChevronUp, ExternalLink, Star } from 'lucide-react';
import { getCertCandidates } from '../../api/client';

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
  year: string;
  schedules: ScheduleItem[];
  total: number;
}

const POPULAR_CERTS = [
  { id: 'cert_0063', name: '정보처리기사' },
  { id: 'cert_0064', name: '정보처리산업기사' },
  { id: 'cert_0065', name: '정보처리기능사' },
  { id: 'cert_0101', name: '컴퓨터활용능력1급' },
  { id: 'cert_0102', name: '컴퓨터활용능력2급' },
  { id: 'cert_0200', name: '한국사능력검정시험' },
  { id: 'cert_0510', name: '전기기사' },
  { id: 'cert_0511', name: '전기산업기사' },
  { id: 'cert_0512', name: '전기기능사' },
  { id: 'cert_0300', name: '건축기사' },
  { id: 'cert_0401', name: '지게차운전기능사' },
  { id: 'cert_0402', name: '굴삭기운전기능사' },
];

function formatDate(s: string | null): string {
  if (!s) return '-';
  const c = s.replace(/-/g, '');
  if (c.length === 8) return `${c.slice(0, 4)}.${c.slice(4, 6)}.${c.slice(6, 8)}`;
  return s;
}

function DdayBadge({ dday }: { dday: number | null }) {
  if (dday === null) return null;
  if (dday < 0) return <span className="sch-badge sch-badge-past">마감</span>;
  if (dday === 0) return <span className="sch-badge sch-badge-today">D-Day</span>;
  if (dday <= 7) return <span className="sch-badge sch-badge-urgent">D-{dday}</span>;
  if (dday <= 30) return <span className="sch-badge sch-badge-soon">D-{dday}</span>;
  return <span className="sch-badge sch-badge-future">D-{dday}</span>;
}

function ScheduleCard({ data }: { data: CertSchedule }) {
  const [open, setOpen] = useState(false);
  const upcoming = data.schedules.filter(s => (s.d_day_exam ?? -1) >= 0);
  const nearest = upcoming[0] ?? data.schedules[0];

  return (
    <div className={`sch-card${open ? ' sch-card-open' : ''}`}>
      <button className="sch-card-header" onClick={() => setOpen(v => !v)}>
        <div className="sch-card-title-row">
          <span className="sch-cert-name">{data.cert_name}</span>
          {nearest && <DdayBadge dday={nearest.d_day_exam} />}
        </div>
        <div className="sch-card-meta">
          <span className="sch-year">{data.year}년</span>
          <span className="sch-count">{data.total}회차</span>
          {nearest && nearest.exam_start && (
            <span className="sch-nearest">
              <Clock size={11} /> 최근 시험: {formatDate(nearest.exam_start)}
            </span>
          )}
        </div>
        {open ? <ChevronUp size={15} className="sch-chevron" /> : <ChevronDown size={15} className="sch-chevron" />}
      </button>

      {open && (
        <div className="sch-detail">
          {data.schedules.length === 0 ? (
            <p className="sch-empty-text">이번 연도 시험 일정이 없습니다.</p>
          ) : (
            <div className="sch-table-wrap">
              <table className="sch-table">
                <thead>
                  <tr>
                    <th>회차</th>
                    <th>접수 기간</th>
                    <th>시험 기간</th>
                    <th>합격 발표</th>
                    <th>D-Day</th>
                  </tr>
                </thead>
                <tbody>
                  {data.schedules.map((s, i) => (
                    <tr key={i} className={s.d_day_exam !== null && s.d_day_exam < 0 ? 'sch-row-past' : ''}>
                      <td className="sch-td-seq">{s.impl_seq_name ?? `${s.impl_seq}회`}</td>
                      <td>
                        {formatDate(s.registration_start)}
                        {s.registration_end ? ` ~ ${formatDate(s.registration_end)}` : ''}
                      </td>
                      <td>
                        {formatDate(s.exam_start)}
                        {s.exam_end && s.exam_end !== s.exam_start ? ` ~ ${formatDate(s.exam_end)}` : ''}
                      </td>
                      <td>{formatDate(s.pass_announce_date)}</td>
                      <td><DdayBadge dday={s.d_day_exam} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <a
            className="sch-qnet-link"
            href={`https://www.q-net.or.kr/crf005.do?id=crf00503s&jmNm=${encodeURIComponent(data.cert_name)}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <ExternalLink size={12} /> Q-Net에서 원서접수
          </a>
        </div>
      )}
    </div>
  );
}

interface ProfExamItem {
  [key: string]: unknown;
}

interface ProfExamResult {
  cert_name: string;
  schedules: ProfExamItem[];
  total: number;
  source?: string;
}

function ProfExamCard({ data }: { data: ProfExamResult }) {
  const [open, setOpen] = useState(false);
  const keys = data.schedules.length > 0 ? Object.keys(data.schedules[0]).filter(k => k !== 'cert_name') : [];
  return (
    <div className={`sch-card${open ? ' sch-card-open' : ''}`}>
      <button className="sch-card-header" onClick={() => setOpen(v => !v)}>
        <div className="sch-card-title-row">
          <span className="sch-cert-name">{data.cert_name}</span>
          <span className="sch-prof-badge">국가전문</span>
        </div>
        <div className="sch-card-meta">
          <span className="sch-count">{data.total}건</span>
          {data.source && <span className="sch-year">{data.source}</span>}
        </div>
        {open ? <ChevronUp size={15} className="sch-chevron" /> : <ChevronDown size={15} className="sch-chevron" />}
      </button>
      {open && (
        <div className="sch-detail">
          {data.schedules.length === 0 ? (
            <p className="sch-empty-text">일정 정보가 없습니다.</p>
          ) : (
            <div className="sch-table-wrap">
              <table className="sch-table">
                <thead>
                  <tr>
                    {keys.map(k => <th key={k}>{k}</th>)}
                  </tr>
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
          )}
          <a
            className="sch-qnet-link"
            href={`https://www.q-net.or.kr/crf005.do?id=crf00503s&jmNm=${encodeURIComponent(data.cert_name)}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <ExternalLink size={12} /> Q-Net에서 원서접수
          </a>
        </div>
      )}
    </div>
  );
}

const Schedule: React.FC = () => {
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<CertSchedule[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const cacheRef = useRef<Record<string, CertSchedule>>({});
  const mountedRef = useRef(false);

  // 국가전문자격
  const [profSearch, setProfSearch] = useState('');
  const [profResults, setProfResults] = useState<ProfExamResult[]>([]);
  const [profLoading, setProfLoading] = useState(false);
  const [profError, setProfError] = useState<string | null>(null);
  const profCacheRef = useRef<Record<string, ProfExamResult>>({});

  const fetchSchedule = useCallback(async (certId: string, certName: string) => {
    if (cacheRef.current[certId]) return cacheRef.current[certId];
    try {
      const r = await fetch(`/api/v1/schedules/exams/${encodeURIComponent(certId)}`);
      const json = await r.json();
      if (json.success && json.data) {
        const item: CertSchedule = {
          cert_id: certId,
          cert_name: json.data.cert_name ?? certName,
          year: json.data.year ?? '',
          schedules: json.data.schedules ?? [],
          total: json.data.total ?? 0,
        };
        cacheRef.current[certId] = item;
        return item;
      }
    } catch { /* silent */ }
    return null;
  }, []);

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const q = search.trim().toLowerCase();
    if (!q) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const all = await getCertCandidates();
      const matched = all
        .filter(c => c.cert_name.toLowerCase().includes(q))
        .slice(0, 6);

      if (matched.length === 0) {
        setResults([]);
        setLoading(false);
        return;
      }

      const settled = await Promise.allSettled(
        matched.map(c => fetchSchedule(c.cert_id, c.cert_name))
      );
      const found: CertSchedule[] = settled
        .filter((r): r is PromiseFulfilledResult<CertSchedule> => r.status === 'fulfilled' && r.value !== null)
        .map(r => r.value);
      setResults(found);
    } catch {
      setError('자격증 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
    setLoading(false);
  }, [search, fetchSchedule]);

  const handlePopular = useCallback(async (_certId: string, certName: string) => {
    setLoading(true);
    setError(null);
    setSearched(true);
    setSearch(certName);
    try {
      const all = await getCertCandidates();
      const found = all.find(c => c.cert_name === certName || c.cert_name.includes(certName));
      if (found) {
        const item = await fetchSchedule(found.cert_id, found.cert_name);
        if (item) { setResults([item]); }
        else setError('시험 일정 정보를 불러올 수 없습니다.');
      } else {
        setError(`"${certName}" 자격증을 데이터에서 찾을 수 없습니다.`);
      }
    } catch {
      setError('자격증 정보를 불러올 수 없습니다.');
    }
    setLoading(false);
  }, [fetchSchedule]);

  const handleLoadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSearched(true);
    setSearch('');
    try {
      const all = await getCertCandidates();
      const targets = POPULAR_CERTS.slice(0, 6).map(p => {
        const found = all.find(c => c.cert_name === p.name || c.cert_name.includes(p.name));
        return found ? { cert_id: found.cert_id, cert_name: found.cert_name } : null;
      }).filter(Boolean) as Array<{ cert_id: string; cert_name: string }>;

      const settled = await Promise.allSettled(
        targets.map(c => fetchSchedule(c.cert_id, c.cert_name))
      );
      const found: CertSchedule[] = settled
        .filter((r): r is PromiseFulfilledResult<CertSchedule> => r.status === 'fulfilled' && r.value !== null)
        .map(r => r.value);
      setResults(found);
    } catch {
      setError('자격증 정보를 불러올 수 없습니다.');
    }
    setLoading(false);
  }, [fetchSchedule]);

  const handleProfSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const q = profSearch.trim();
    if (!q) return;
    if (profCacheRef.current[q]) {
      setProfResults([profCacheRef.current[q]]);
      return;
    }
    setProfLoading(true);
    setProfError(null);
    try {
      const r = await fetch(`/api/v1/schedules/professional-exams?cert_name=${encodeURIComponent(q)}`);
      const json = await r.json();
      if (json.success && json.data) {
        const item: ProfExamResult = {
          cert_name: json.data.cert_name ?? q,
          schedules: json.data.schedules ?? [],
          total: json.data.total ?? 0,
          source: json.data.source,
        };
        profCacheRef.current[q] = item;
        setProfResults([item]);
      } else {
        setProfError(json.error?.message ?? '국가전문자격 일정 조회에 실패했습니다.');
      }
    } catch {
      setProfError('국가전문자격 일정을 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
    setProfLoading(false);
  }, [profSearch]);

  // Auto-load top 6 popular certs on first mount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (mountedRef.current) return;
    mountedRef.current = true;
    handleLoadAll();
  }, [handleLoadAll]);

  return (
    <div className="sch-wrap">
      <div className="sch-header">
        <h1 className="sch-title">시험 일정</h1>
        <p className="sch-sub">
          Q-Net 공공데이터 API 실시간 연동 · 시험일·접수일·합격발표일 D-Day 표시
        </p>
        <p className="sch-datasrc">데이터 출처: 한국산업인력공단 Q-Net (openapi.q-net.or.kr)</p>
      </div>

      {/* 검색 */}
      <form className="sch-search-form" onSubmit={handleSearch}>
        <div className="sch-search-inner">
          <Search size={16} className="sch-search-icon" />
          <input
            className="sch-search-input"
            type="text"
            placeholder="자격증명 검색 (예: 정보처리기사, 전기기사)"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <button type="submit" className="btn-primary sch-search-btn" disabled={loading}>
            {loading ? <Loader2 size={15} className="spin" /> : '검색'}
          </button>
        </div>
      </form>

      {/* 인기 자격증 빠른 선택 */}
      <div className="sch-popular">
        <p className="sch-popular-label">인기 자격증 바로가기</p>
        <div className="sch-popular-list">
          {POPULAR_CERTS.map(c => (
            <button
              key={c.id}
              className="sch-popular-btn"
              onClick={() => handlePopular(c.id, c.name)}
              disabled={loading}
            >
              {c.name}
            </button>
          ))}
          <button className="sch-popular-btn sch-popular-all" onClick={handleLoadAll} disabled={loading}>
            <Calendar size={12} /> 인기 6종 한번에
          </button>
        </div>
      </div>

      {/* 결과 */}
      {error && (
        <div className="sch-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="sch-loading">
          <Loader2 size={20} className="spin" />
          <span>Q-Net에서 시험 일정을 가져오는 중…</span>
        </div>
      )}

      {!loading && searched && results.length === 0 && !error && (
        <div className="sch-empty">
          <AlertCircle size={18} />
          <p>검색 결과가 없습니다. 자격증명을 정확히 입력하거나 인기 자격증을 선택해주세요.</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="sch-results">
          {results.map(item => (
            <ScheduleCard key={item.cert_id} data={item} />
          ))}
        </div>
      )}

      {/* 국가전문자격 시험 일정 */}
      <div className="sch-prof-section">
        <div className="sch-prof-header">
          <Star size={15} className="sch-prof-icon" />
          <h2 className="sch-prof-title">국가전문자격 시험 일정</h2>
          <span className="sch-prof-badge-label">의사·건축사·변호사 등</span>
        </div>
        <p className="sch-prof-desc">의사, 약사, 건축사, 변호사 등 국가전문자격 시험 일정을 조회합니다.</p>
        <form className="sch-search-form" onSubmit={handleProfSearch}>
          <div className="sch-search-inner">
            <Search size={16} className="sch-search-icon" />
            <input
              className="sch-search-input"
              type="text"
              placeholder="국가전문자격명 검색 (예: 의사, 약사, 건축사, 변호사)"
              value={profSearch}
              onChange={e => setProfSearch(e.target.value)}
            />
            <button type="submit" className="btn-primary sch-search-btn" disabled={profLoading}>
              {profLoading ? <Loader2 size={15} className="spin" /> : '검색'}
            </button>
          </div>
        </form>
        {profError && (
          <div className="sch-error">
            <AlertCircle size={15} />
            <span>{profError}</span>
          </div>
        )}
        {profLoading && (
          <div className="sch-loading">
            <Loader2 size={18} className="spin" />
            <span>국가전문자격 일정 조회 중…</span>
          </div>
        )}
        {!profLoading && profResults.length > 0 && (
          <div className="sch-results">
            {profResults.map((item, i) => (
              <ProfExamCard key={i} data={item} />
            ))}
          </div>
        )}
      </div>

      {/* 안내 */}
      {!searched && !loading && (
        <div className="sch-guide">
          <div className="sch-guide-card">
            <Calendar size={28} className="sch-guide-icon" />
            <h3>실시간 시험 일정</h3>
            <p>Q-Net 공공데이터 API에서 실시간으로 가져오는 시험 일정입니다. 시험일·접수일·합격발표일 D-Day를 한눈에 확인하세요.</p>
          </div>
          <div className="sch-guide-card">
            <Clock size={28} className="sch-guide-icon" />
            <h3>D-Day 알림</h3>
            <p>접수 마감, 시험일이 가까울수록 다른 색상으로 표시됩니다. 30일 이내는 주황, 7일 이내는 빨강으로 강조됩니다.</p>
          </div>
          <div className="sch-guide-card">
            <ExternalLink size={28} className="sch-guide-icon" />
            <h3>Q-Net 원서접수</h3>
            <p>일정 확인 후 Q-Net 원서접수 링크로 바로 이동할 수 있습니다.</p>
          </div>
        </div>
      )}

      <style>{`
        .sch-wrap { display: flex; flex-direction: column; gap: 1.75rem; max-width: 860px; margin: 0 auto; }
        .sch-header { display: flex; flex-direction: column; gap: .4rem; }
        .sch-title { font-size: 1.75rem; font-weight: 900; color: var(--text); margin: 0; }
        .sch-sub { font-size: .9rem; color: var(--text-muted); margin: 0; }
        .sch-datasrc { font-size: .72rem; color: var(--text-light); margin: 0; }

        /* 검색 */
        .sch-search-form { }
        .sch-search-inner {
          display: flex; align-items: center; gap: .625rem;
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          padding: .5rem .75rem;
          transition: border-color .15s;
        }
        .sch-search-inner:focus-within { border-color: var(--primary); }
        .sch-search-icon { color: var(--text-light); flex-shrink: 0; }
        .sch-search-input {
          flex: 1; border: none; background: transparent;
          font-size: .9rem; color: var(--text);
          outline: none;
        }
        .sch-search-input::placeholder { color: var(--text-light); }
        .sch-search-btn { padding: .45rem 1rem; font-size: .85rem; }

        /* 인기 자격증 */
        .sch-popular { display: flex; flex-direction: column; gap: .625rem; }
        .sch-popular-label { font-size: .78rem; font-weight: 700; color: var(--text-muted); margin: 0; }
        .sch-popular-list { display: flex; flex-wrap: wrap; gap: .5rem; }
        .sch-popular-btn {
          padding: .35rem .75rem;
          font-size: .8rem; font-weight: 500;
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-radius: 20px;
          cursor: pointer; color: var(--text-muted);
          transition: all .15s;
          display: flex; align-items: center; gap: .3rem;
        }
        .sch-popular-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); background: var(--primary-light); }
        .sch-popular-btn:disabled { opacity: .5; cursor: not-allowed; }
        .sch-popular-all { background: var(--primary-light); border-color: var(--primary); color: var(--primary); font-weight: 700; }

        /* 결과 카드 */
        .sch-results { display: flex; flex-direction: column; gap: .75rem; }
        .sch-card {
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          overflow: hidden;
          background: var(--surface-2);
          transition: border-color .15s;
        }
        .sch-card-open { border-color: var(--primary); }
        .sch-card-header {
          width: 100%; display: flex; align-items: flex-start; justify-content: space-between; gap: .75rem;
          padding: .875rem 1rem;
          background: none; border: none; cursor: pointer;
          text-align: left;
        }
        .sch-card-header:hover { background: var(--surface-3, #f1f5f9); }
        .sch-card-title-row { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
        .sch-cert-name { font-size: .95rem; font-weight: 700; color: var(--text); }
        .sch-card-meta { display: flex; align-items: center; gap: .75rem; flex-wrap: wrap; margin-top: .2rem; }
        .sch-year { font-size: .75rem; color: var(--text-light); }
        .sch-count { font-size: .75rem; color: var(--text-light); }
        .sch-nearest { font-size: .75rem; color: var(--text-muted); display: flex; align-items: center; gap: .25rem; }
        .sch-chevron { color: var(--text-light); flex-shrink: 0; margin-top: .15rem; }

        /* D-Day 배지 */
        .sch-badge {
          display: inline-flex; align-items: center;
          padding: .15rem .5rem; border-radius: 20px;
          font-size: .7rem; font-weight: 700;
        }
        .sch-badge-past    { background: #f1f5f9; color: #94a3b8; }
        .sch-badge-today   { background: #fee2e2; color: #ef4444; }
        .sch-badge-urgent  { background: #fee2e2; color: #ef4444; }
        .sch-badge-soon    { background: #fef3c7; color: #d97706; }
        .sch-badge-future  { background: #e0f2fe; color: #0284c7; }

        /* 상세 테이블 */
        .sch-detail { border-top: 1px solid var(--border); padding: 1rem; display: flex; flex-direction: column; gap: .75rem; }
        .sch-table-wrap { overflow-x: auto; }
        .sch-table { width: 100%; border-collapse: collapse; font-size: .8rem; }
        .sch-table th {
          padding: .5rem .75rem; text-align: left;
          font-size: .72rem; font-weight: 700; color: var(--text-muted);
          background: var(--surface-3, #f8fafc);
          border-bottom: 1px solid var(--border);
          white-space: nowrap;
        }
        .sch-table td {
          padding: .5rem .75rem; color: var(--text-muted);
          border-bottom: 1px solid var(--border);
          white-space: nowrap;
        }
        .sch-table tr:last-child td { border-bottom: none; }
        .sch-row-past td { opacity: .5; }
        .sch-td-seq { font-weight: 600; color: var(--text); }
        .sch-qnet-link {
          display: inline-flex; align-items: center; gap: .35rem;
          font-size: .78rem; color: var(--primary);
          text-decoration: none;
          padding: .35rem .75rem;
          border: 1px solid var(--primary);
          border-radius: var(--radius-sm);
          width: fit-content;
          transition: background .15s;
        }
        .sch-qnet-link:hover { background: var(--primary-light); }
        .sch-empty-text { font-size: .85rem; color: var(--text-light); margin: 0; text-align: center; padding: 1rem; }

        /* 상태 */
        .sch-loading { display: flex; align-items: center; gap: .75rem; padding: 2.5rem; justify-content: center; color: var(--text-muted); font-size: .9rem; }
        .sch-error { display: flex; align-items: center; gap: .625rem; padding: 1rem 1.25rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: var(--radius-sm); color: #dc2626; font-size: .875rem; }
        .sch-empty { display: flex; align-items: flex-start; gap: .625rem; padding: 2rem; background: var(--surface-2); border: 1px dashed var(--border); border-radius: var(--radius-sm); color: var(--text-muted); font-size: .875rem; }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

        /* 국가전문자격 섹션 */
        .sch-prof-section {
          display: flex; flex-direction: column; gap: .875rem;
          padding: 1.25rem; background: var(--surface-2);
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          border-left: 3px solid var(--primary);
        }
        .sch-prof-header { display: flex; align-items: center; gap: .5rem; }
        .sch-prof-icon { color: var(--primary); flex-shrink: 0; }
        .sch-prof-title { font-size: 1rem; font-weight: 800; color: var(--text); margin: 0; }
        .sch-prof-badge-label {
          font-size: .7rem; color: var(--text-light);
          background: var(--surface); border: 1px solid var(--border);
          padding: .1rem .45rem; border-radius: 20px;
        }
        .sch-prof-desc { font-size: .8rem; color: var(--text-muted); margin: 0; }
        .sch-prof-badge {
          display: inline-flex; align-items: center;
          padding: .15rem .5rem; border-radius: 20px;
          font-size: .7rem; font-weight: 700;
          background: var(--primary-light); color: var(--primary);
        }

        /* 가이드 */
        .sch-guide { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
        @media (max-width: 640px) { .sch-guide { grid-template-columns: 1fr; } }
        .sch-guide-card {
          display: flex; flex-direction: column; gap: .625rem;
          padding: 1.25rem;
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
        }
        .sch-guide-icon { color: var(--primary); }
        .sch-guide-card h3 { font-size: .9rem; font-weight: 700; color: var(--text); margin: 0; }
        .sch-guide-card p { font-size: .8rem; color: var(--text-muted); margin: 0; line-height: 1.65; }
      `}</style>
    </div>
  );
};

export default Schedule;
