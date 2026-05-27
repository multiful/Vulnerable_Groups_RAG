// Content Hash: SHA256:TBD
// 채용행사 페이지 — Work24 공공 채용행사 (개인 계정 접근 가능)
// 기업 전용 채용공고(Work24 채용목록)와 달리 고용센터·지자체 주최 행사
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, CalendarDays, MapPin, ExternalLink, Loader2, AlertCircle, Building2, Users } from 'lucide-react';

interface JobFairEvent {
  event_id?: string;
  event_name?: string;
  organizer?: string;
  region?: string;
  venue?: string;
  start_date?: string;
  end_date?: string;
  apply_method?: string;
  url?: string;
  description?: string;
  participant_count?: string;
  event_type?: string;
}

const REGIONS = ['전국', '서울', '경기', '인천', '부산', '대구', '광주', '대전', '울산', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'];

function formatDate(d: string) {
  if (!d || d.length < 8) return d;
  return `${d.slice(0, 4)}.${d.slice(4, 6)}.${d.slice(6, 8)}`;
}

function EventCard({ event }: { event: JobFairEvent }) {
  const name = event.event_name || '(행사명 없음)';
  const org = event.organizer || '';
  const venue = event.venue || '';
  const region = event.region || '';
  const start = formatDate(event.start_date || '');
  const end = formatDate(event.end_date || '');
  const method = event.apply_method || '';
  const count = event.participant_count || '';
  const type = event.event_type || '';
  const url = event.url || '';
  const desc = event.description || '';

  const dateStr = start && end ? `${start} ~ ${end}` : (start || end || '');

  return (
    <div className="jf-card">
      <div className="jf-card-top">
        <div className="jf-card-title-row">
          <span className="jf-event-name">{name}</span>
          {type && <span className="jf-type-badge">{type}</span>}
        </div>
        {org && (
          <div className="jf-org-row">
            <Building2 size={11} className="jf-org-icon" />
            <span className="jf-organizer">{org}</span>
          </div>
        )}
      </div>
      <div className="jf-meta-row">
        {(venue || region) && (
          <span className="jf-meta-item">
            <MapPin size={11} /> {venue || region}
          </span>
        )}
        {dateStr && (
          <span className="jf-meta-item jf-meta-date">
            <CalendarDays size={11} /> {dateStr}
          </span>
        )}
        {method && (
          <span className="jf-meta-item">참가방법: {method}</span>
        )}
        {count && (
          <span className="jf-meta-item">
            <Users size={11} /> 참가 {count}명
          </span>
        )}
      </div>
      {desc && (
        <p className="jf-desc">{desc.slice(0, 100)}{desc.length > 100 ? '…' : ''}</p>
      )}
      {url ? (
        <a className="jf-card-link" href={url} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={11} /> 행사 상세 보기
        </a>
      ) : (
        <a className="jf-card-link" href="https://www.work24.go.kr/cm/c/f/1300/retrivewantedList.do" target="_blank" rel="noopener noreferrer">
          <ExternalLink size={11} /> Work24에서 확인
        </a>
      )}
    </div>
  );
}

const Jobs: React.FC = () => {
  const [searchParams] = useSearchParams();

  const [keyword, setKeyword] = useState(searchParams.get('keyword') || '');
  const [region, setRegion] = useState('');
  const [results, setResults] = useState<JobFairEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const cacheRef = useRef<Record<string, { events: JobFairEvent[]; total: number }>>({});
  const didAutoSearch = useRef(false);

  const fetchFairs = useCallback(async (kw: string, reg: string) => {
    const cacheKey = `${kw}__${reg}`;
    if (cacheRef.current[cacheKey]) {
      const c = cacheRef.current[cacheKey];
      setResults(c.events);
      setTotal(c.total);
      setSearched(true);
      return;
    }
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const params = new URLSearchParams({ days_ahead: '120', page_size: '30' });
      if (kw.trim()) params.set('keyword', kw.trim());
      if (reg && reg !== '전국') params.set('region', reg);

      const r = await fetch(`/api/v1/jobs/fairs?${params}`);
      const json = await r.json();
      if (json.success && json.data) {
        const events: JobFairEvent[] = json.data.events ?? [];
        const t: number = json.data.total ?? events.length;
        cacheRef.current[cacheKey] = { events, total: t };
        setResults(events);
        setTotal(t);
      } else {
        setError(json.error?.message ?? '채용행사 정보를 불러올 수 없습니다.');
      }
    } catch {
      setError('채용행사 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
    setLoading(false);
  }, []);

  // URL ?keyword= 파라미터로 자동 검색 (도메인 연결)
  useEffect(() => {
    const kw = searchParams.get('keyword');
    if (kw && !didAutoSearch.current) {
      didAutoSearch.current = true;
      setKeyword(kw);
      fetchFairs(kw, '');
    }
  }, [searchParams, fetchFairs]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    fetchFairs(keyword, region);
  }, [keyword, region, fetchFairs]);

  return (
    <div className="jf-wrap">
      <div className="jf-header">
        <h1 className="jf-title">채용행사</h1>
        <p className="jf-sub">
          고용센터·지자체가 주최하는 공개 채용행사를 검색하세요.
          <span className="jf-sub-note"> (개인 계정으로 조회 가능한 공공 채용행사입니다)</span>
        </p>
      </div>

      {/* 검색 폼 */}
      <form className="jf-search-form" onSubmit={handleSubmit}>
        <div className="jf-search-row">
          <div className="jf-search-input-wrap">
            <Search size={15} className="jf-search-icon" />
            <input
              className="jf-search-input"
              type="text"
              placeholder="행사명 검색 (예: IT, 의료, 제조, 채용박람회)"
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
            />
          </div>
        </div>
        <div className="jf-filter-row">
          <select className="jf-filter-select" value={region} onChange={e => setRegion(e.target.value)}>
            {REGIONS.map(r => (
              <option key={r} value={r === '전국' ? '' : r}>{r}</option>
            ))}
          </select>
          <button type="submit" className="btn-primary jf-search-btn" disabled={loading}>
            {loading ? <Loader2 size={15} className="spin" /> : <><Search size={14} /> 검색</>}
          </button>
        </div>
      </form>

      {/* 에러 */}
      {error && (
        <div className="jf-error-wrap">
          <AlertCircle size={15} className="jf-error-icon" />
          <div>
            <p className="jf-error-title">채용행사 조회 실패</p>
            <p className="jf-error-msg">{error}</p>
          </div>
          <a
            href="https://www.work24.go.kr/cm/c/f/1300/retrivewantedList.do"
            target="_blank" rel="noopener noreferrer"
            className="jf-fallback-btn"
          >
            <ExternalLink size={13} /> Work24 채용행사 바로가기
          </a>
        </div>
      )}

      {/* 로딩 */}
      {loading && (
        <div className="jf-loading">
          <Loader2 size={20} className="spin" />
          <span>Work24에서 채용행사를 가져오는 중…</span>
        </div>
      )}

      {/* 결과 없음 */}
      {!loading && searched && results.length === 0 && !error && (
        <div className="jf-empty">
          <CalendarDays size={36} className="jf-empty-icon" />
          <h3>현재 예정된 채용행사가 없습니다</h3>
          <p>다른 지역이나 키워드로 검색해보세요.<br />행사 일정이 없을 경우 Work24에서 직접 확인하실 수 있습니다.</p>
          <a
            href="https://www.work24.go.kr/cm/c/f/1300/retrivewantedList.do"
            target="_blank" rel="noopener noreferrer"
            className="jf-ext-link"
          >
            Work24 채용행사 바로가기 →
          </a>
        </div>
      )}

      {/* 첫 화면 안내 */}
      {!searched && !loading && (
        <div className="jf-intro">
          <div className="jf-intro-card">
            <CalendarDays size={26} className="jf-intro-icon" />
            <h3>공공 채용행사</h3>
            <p>고용센터·지자체가 주최하는 채용박람회, 취업설명회를 검색합니다. 개인 계정으로 조회 가능한 공공 데이터입니다.</p>
          </div>
          <div className="jf-intro-card">
            <MapPin size={26} className="jf-intro-icon" />
            <h3>지역별 필터</h3>
            <p>서울, 경기, 부산 등 지역별 채용행사를 확인하세요. 가까운 지역 행사를 찾아 직접 방문할 수 있습니다.</p>
          </div>
          <div className="jf-intro-card">
            <Building2 size={26} className="jf-intro-icon" />
            <h3>추천 연계</h3>
            <p>자격증 추천 결과에서 관련 채용행사를 바로 확인할 수 있습니다. 도메인별 행사를 키워드로 연결합니다.</p>
          </div>
        </div>
      )}

      {/* 결과 목록 */}
      {!loading && results.length > 0 && (
        <div className="jf-results">
          <p className="jf-result-count">총 {total.toLocaleString()}개 채용행사 · {results.length}개 표시</p>
          <div className="jf-list">
            {results.map((ev, i) => (
              <EventCard key={ev.event_id || i} event={ev} />
            ))}
          </div>
          <div className="jf-ext-link-row">
            <a
              href="https://www.work24.go.kr/cm/c/f/1300/retrivewantedList.do"
              target="_blank" rel="noopener noreferrer"
              className="jf-ext-link"
            >
              <ExternalLink size={13} /> Work24에서 더 보기
            </a>
          </div>
        </div>
      )}

      <style>{`
        .jf-wrap { display: flex; flex-direction: column; gap: 1.75rem; max-width: 860px; margin: 0 auto; }
        .jf-header { display: flex; flex-direction: column; gap: .35rem; }
        .jf-title { font-size: 1.75rem; font-weight: 900; color: var(--text); margin: 0; }
        .jf-sub { font-size: .9rem; color: var(--text-muted); margin: 0; }
        .jf-sub-note { font-size: .75rem; color: var(--text-light); }

        .jf-search-form { display: flex; flex-direction: column; gap: .625rem; }
        .jf-search-row {
          display: flex; align-items: center;
          background: var(--surface-2); border: 1px solid var(--border);
          border-radius: var(--radius-sm); padding: .5rem .75rem;
          transition: border-color .15s;
        }
        .jf-search-row:focus-within { border-color: var(--primary); }
        .jf-search-input-wrap { display: flex; align-items: center; gap: .5rem; width: 100%; }
        .jf-search-icon { color: var(--text-light); flex-shrink: 0; }
        .jf-search-input {
          flex: 1; border: none; background: transparent;
          font-size: .9rem; color: var(--text); outline: none;
        }
        .jf-search-input::placeholder { color: var(--text-light); }
        .jf-filter-row { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }
        .jf-filter-select {
          padding: .4rem .65rem; font-size: .82rem;
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          background: var(--surface-2); color: var(--text-muted); cursor: pointer; outline: none;
        }
        .jf-filter-select:focus { border-color: var(--primary); }
        .jf-search-btn {
          display: flex; align-items: center; gap: .35rem;
          padding: .45rem 1rem; font-size: .85rem; margin-left: auto;
        }

        .jf-card {
          padding: .875rem 1rem; background: var(--surface-2);
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          display: flex; flex-direction: column; gap: .375rem;
          transition: border-color .15s;
        }
        .jf-card:hover { border-color: var(--primary); }
        .jf-card-top { display: flex; flex-direction: column; gap: .2rem; }
        .jf-card-title-row { display: flex; align-items: flex-start; gap: .5rem; flex-wrap: wrap; }
        .jf-event-name { font-size: .9rem; font-weight: 700; color: var(--text); flex: 1; }
        .jf-type-badge {
          font-size: .67rem; background: #f0f4ff; color: #4338ca;
          padding: .1rem .4rem; border-radius: 20px; flex-shrink: 0; white-space: nowrap;
        }
        .jf-org-row { display: flex; align-items: center; gap: .3rem; }
        .jf-org-icon { color: var(--text-light); flex-shrink: 0; }
        .jf-organizer { font-size: .8rem; color: var(--text-muted); }
        .jf-meta-row { display: flex; gap: .625rem; flex-wrap: wrap; }
        .jf-meta-item {
          display: inline-flex; align-items: center; gap: .2rem;
          font-size: .72rem; color: var(--text-light);
        }
        .jf-meta-date { color: #2563eb; font-weight: 600; }
        .jf-desc { font-size: .78rem; color: var(--text-muted); margin: 0; line-height: 1.55; }
        .jf-card-link {
          display: inline-flex; align-items: center; gap: .3rem;
          font-size: .75rem; color: var(--primary); text-decoration: none;
          width: fit-content; transition: opacity .15s;
        }
        .jf-card-link:hover { opacity: .75; }

        .jf-results { display: flex; flex-direction: column; gap: .625rem; }
        .jf-result-count { font-size: .75rem; color: var(--text-light); margin: 0; }
        .jf-list { display: flex; flex-direction: column; gap: .5rem; }

        .jf-loading { display: flex; align-items: center; gap: .625rem; padding: 2.5rem; justify-content: center; color: var(--text-muted); font-size: .9rem; }

        .jf-error-wrap {
          display: flex; align-items: flex-start; gap: .625rem;
          padding: 1rem; background: #fffbeb; border: 1px solid #fde68a;
          border-radius: var(--radius-sm); flex-wrap: wrap;
        }
        .jf-error-icon { color: #d97706; flex-shrink: 0; margin-top: .1rem; }
        .jf-error-title { font-size: .85rem; font-weight: 700; color: #92400e; margin: 0 0 .2rem; }
        .jf-error-msg { font-size: .75rem; color: #b45309; margin: 0; }
        .jf-fallback-btn {
          display: inline-flex; align-items: center; gap: .35rem;
          padding: .4rem .8rem; background: #f59e0b; color: #fff;
          border-radius: var(--radius-sm); font-size: .8rem; font-weight: 600;
          text-decoration: none; margin-left: auto; transition: background .15s;
        }
        .jf-fallback-btn:hover { background: #d97706; }

        .jf-empty {
          display: flex; flex-direction: column; align-items: center; gap: .625rem;
          padding: 3rem 1.5rem; background: var(--surface-2);
          border: 1px dashed var(--border); border-radius: var(--radius-sm); text-align: center;
        }
        .jf-empty-icon { color: var(--border-strong); }
        .jf-empty h3 { font-size: .9rem; font-weight: 700; color: var(--text-muted); margin: 0; }
        .jf-empty p { font-size: .82rem; color: var(--text-light); margin: 0; line-height: 1.7; }

        .jf-intro { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
        @media (max-width: 640px) { .jf-intro { grid-template-columns: 1fr; } }
        .jf-intro-card {
          display: flex; flex-direction: column; gap: .5rem;
          padding: 1.25rem; background: var(--surface-2);
          border: 1px solid var(--border); border-radius: var(--radius-sm);
        }
        .jf-intro-icon { color: var(--primary); }
        .jf-intro-card h3 { font-size: .875rem; font-weight: 700; color: var(--text); margin: 0; }
        .jf-intro-card p { font-size: .78rem; color: var(--text-muted); margin: 0; line-height: 1.65; }

        .jf-ext-link-row { display: flex; justify-content: center; padding-top: .5rem; }
        .jf-ext-link {
          display: inline-flex; align-items: center; gap: .35rem;
          font-size: .8rem; color: var(--primary); text-decoration: none;
          padding: .375rem .875rem; border: 1px solid var(--primary);
          border-radius: var(--radius-sm); transition: background .15s;
        }
        .jf-ext-link:hover { background: var(--primary-light); }

        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default Jobs;
