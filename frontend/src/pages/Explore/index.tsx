// Content Hash: SHA256:TBD
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, Briefcase, BookOpen, Grid3X3, Loader2, AlertCircle, ChevronRight, ExternalLink } from 'lucide-react';

type Tab = 'jobs' | 'majors' | 'ncs';

interface CareerJob {
  seq: string;
  name: string;
  description: string;
  tasks: string;
  salary_low: string;
  salary_high: string;
  employment_prospect: string;
  related_certs: string;
  related_majors: string;
}

interface CareerMajor {
  seq: string;
  name: string;
  description: string;
  category: string;
  related_jobs: string;
  related_certs: string;
  employment_rate: string;
}

interface NcsCert {
  cert_id: string;
  cert_name: string;
  cert_grade_tier: string;
  issuer: string;
  avg_pass_rate_3yr: number | null;
  primary_domain: string;
}

interface NcsItem {
  ncs_id: string;
  major_code: string;
  major_name: string;
  mid_name: string;
  minor_name: string;
}

function JobCard({ job }: { job: CareerJob }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="ex-card">
      <button className="ex-card-header" onClick={() => setOpen(v => !v)}>
        <div className="ex-card-title-row">
          <span className="ex-card-name">{job.name || '(이름 없음)'}</span>
          {job.salary_low && (
            <span className="ex-salary-badge">
              {job.salary_low}~{job.salary_high || '?'}만원
            </span>
          )}
        </div>
        {job.description && (
          <p className="ex-card-desc">{job.description.slice(0, 80)}{job.description.length > 80 ? '…' : ''}</p>
        )}
        <ChevronRight size={13} className={`ex-chevron${open ? ' open' : ''}`} />
      </button>
      {open && (
        <div className="ex-card-detail">
          {job.tasks && (
            <div className="ex-detail-row">
              <span className="ex-detail-key">주요 업무</span>
              <span className="ex-detail-val">{job.tasks}</span>
            </div>
          )}
          {job.employment_prospect && (
            <div className="ex-detail-row">
              <span className="ex-detail-key">취업 전망</span>
              <span className="ex-detail-val">{job.employment_prospect}</span>
            </div>
          )}
          {job.related_certs && (
            <div className="ex-detail-row">
              <span className="ex-detail-key">관련 자격증</span>
              <span className="ex-detail-val">{job.related_certs}</span>
            </div>
          )}
          {job.related_majors && (
            <div className="ex-detail-row">
              <span className="ex-detail-key">관련 학과</span>
              <span className="ex-detail-val">{job.related_majors}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MajorCard({ major }: { major: CareerMajor }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="ex-card">
      <button className="ex-card-header" onClick={() => setOpen(v => !v)}>
        <div className="ex-card-title-row">
          <span className="ex-card-name">{major.name || '(이름 없음)'}</span>
          {major.category && <span className="ex-cat-badge">{major.category}</span>}
          {major.employment_rate && (
            <span className="ex-emp-badge">취업률 {major.employment_rate}%</span>
          )}
        </div>
        {major.description && (
          <p className="ex-card-desc">{major.description.slice(0, 80)}{major.description.length > 80 ? '…' : ''}</p>
        )}
        <ChevronRight size={13} className={`ex-chevron${open ? ' open' : ''}`} />
      </button>
      {open && (
        <div className="ex-card-detail">
          {major.related_jobs && (
            <div className="ex-detail-row">
              <span className="ex-detail-key">관련 직업</span>
              <span className="ex-detail-val">{major.related_jobs}</span>
            </div>
          )}
          {major.related_certs && (
            <div className="ex-detail-row">
              <span className="ex-detail-key">관련 자격증</span>
              <span className="ex-detail-val">{major.related_certs}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function NcsCertCard({ cert }: { cert: NcsCert }) {
  const passRate = cert.avg_pass_rate_3yr != null ? `${cert.avg_pass_rate_3yr.toFixed(1)}%` : '-';
  const tierColor = cert.cert_grade_tier === '기사' || cert.cert_grade_tier === '산업기사'
    ? 'var(--primary)' : cert.cert_grade_tier === '기능사' ? '#10b981' : '#f59e0b';
  return (
    <div className="ex-ncs-cert-card">
      <div className="ex-ncs-cert-top">
        <span className="ex-ncs-cert-name">{cert.cert_name}</span>
        {cert.cert_grade_tier && (
          <span className="ex-ncs-tier-badge" style={{ color: tierColor }}>{cert.cert_grade_tier}</span>
        )}
      </div>
      <div className="ex-ncs-cert-meta">
        {cert.issuer && <span className="ex-ncs-meta-item">{cert.issuer}</span>}
        {cert.primary_domain && <span className="ex-ncs-meta-item">{cert.primary_domain}</span>}
        <span className="ex-ncs-meta-item">합격률 {passRate}</span>
      </div>
    </div>
  );
}

const Explore: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialTab = (['jobs', 'majors', 'ncs'].includes(searchParams.get('tab') ?? ''))
    ? (searchParams.get('tab') as Tab)
    : 'jobs';
  const [tab, setTab] = useState<Tab>(initialTab);
  const [query, setQuery] = useState('');

  useEffect(() => {
    const t = searchParams.get('tab');
    if (t && ['jobs', 'majors', 'ncs'].includes(t)) setTab(t as Tab);
  }, [searchParams]);

  const [jobResults, setJobResults] = useState<CareerJob[]>([]);
  const [jobTotal, setJobTotal] = useState(0);
  const [jobPage, setJobPage] = useState(1);
  const [jobLoading, setJobLoading] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);
  const jobCacheRef = useRef<Record<string, { jobs: CareerJob[]; total: number }>>({});

  const [majorResults, setMajorResults] = useState<CareerMajor[]>([]);
  const [majorTotal, setMajorTotal] = useState(0);
  const [majorPage, setMajorPage] = useState(1);
  const [majorLoading, setMajorLoading] = useState(false);
  const [majorError, setMajorError] = useState<string | null>(null);
  const majorCacheRef = useRef<Record<string, { majors: CareerMajor[]; total: number }>>({});

  const [ncsKeyword, setNcsKeyword] = useState('');
  const [ncsList, setNcsList] = useState<NcsItem[]>([]);
  const [ncsListLoading, setNcsListLoading] = useState(false);
  const [selectedNcs, setSelectedNcs] = useState<NcsItem | null>(null);
  const [ncsCerts, setNcsCerts] = useState<NcsCert[]>([]);
  const [ncsCertsLoading, setNcsCertsLoading] = useState(false);
  const [ncsCertsError, setNcsCertsError] = useState<string | null>(null);
  const ncsCertCacheRef = useRef<Record<string, NcsCert[]>>({});

  const PAGE_SIZE = 20;

  const fetchJobs = useCallback(async (q: string, page: number) => {
    const key = `${q}__${page}`;
    if (jobCacheRef.current[key]) {
      const cached = jobCacheRef.current[key];
      setJobResults(cached.jobs);
      setJobTotal(cached.total);
      setJobPage(page);
      return;
    }
    setJobLoading(true);
    setJobError(null);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (q) params.set('q', q);
      const r = await fetch(`/api/v1/career-net/jobs?${params}`);
      const json = await r.json();
      if (json.success && json.data) {
        const jobs: CareerJob[] = json.data.jobs ?? [];
        const total: number = json.data.total ?? 0;
        jobCacheRef.current[key] = { jobs, total };
        setJobResults(jobs);
        setJobTotal(total);
        setJobPage(page);
      } else {
        setJobError(json.error?.message ?? '직업 정보를 불러올 수 없습니다.');
      }
    } catch {
      setJobError('직업 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
    setJobLoading(false);
  }, []);

  const fetchMajors = useCallback(async (q: string, page: number) => {
    const key = `${q}__${page}`;
    if (majorCacheRef.current[key]) {
      const cached = majorCacheRef.current[key];
      setMajorResults(cached.majors);
      setMajorTotal(cached.total);
      setMajorPage(page);
      return;
    }
    setMajorLoading(true);
    setMajorError(null);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (q) params.set('q', q);
      const r = await fetch(`/api/v1/career-net/majors?${params}`);
      const json = await r.json();
      if (json.success && json.data) {
        const majors: CareerMajor[] = json.data.majors ?? [];
        const total: number = json.data.total ?? 0;
        majorCacheRef.current[key] = { majors, total };
        setMajorResults(majors);
        setMajorTotal(total);
        setMajorPage(page);
      } else {
        setMajorError(json.error?.message ?? '학과 정보를 불러올 수 없습니다.');
      }
    } catch {
      setMajorError('학과 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
    setMajorLoading(false);
  }, []);

  const fetchNcsList = useCallback(async (kw: string) => {
    setNcsListLoading(true);
    try {
      const params = new URLSearchParams();
      if (kw) params.set('keyword', kw);
      const r = await fetch(`/api/v1/ncs/list?${params}`);
      const json = await r.json();
      if (json.success && json.data) {
        setNcsList(json.data.ncs_list ?? []);
      }
    } catch { /* silent */ }
    setNcsListLoading(false);
  }, []);

  const fetchNcsCerts = useCallback(async (item: NcsItem) => {
    const key = item.ncs_id;
    if (ncsCertCacheRef.current[key]) {
      setNcsCerts(ncsCertCacheRef.current[key]);
      return;
    }
    setNcsCertsLoading(true);
    setNcsCertsError(null);
    try {
      const r = await fetch(`/api/v1/ncs/certs?ncs_id=${encodeURIComponent(item.ncs_id)}`);
      const json = await r.json();
      if (json.success && json.data) {
        const certs: NcsCert[] = json.data.certs ?? [];
        ncsCertCacheRef.current[key] = certs;
        setNcsCerts(certs);
      } else {
        setNcsCertsError('해당 NCS에 연결된 자격증이 없습니다.');
      }
    } catch {
      setNcsCertsError('NCS 자격증 조회 중 오류가 발생했습니다.');
    }
    setNcsCertsLoading(false);
  }, []);

  const handleJobSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs(query.trim(), 1);
  }, [query, fetchJobs]);

  const handleMajorSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    fetchMajors(query.trim(), 1);
  }, [query, fetchMajors]);

  const handleNcsSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    fetchNcsList(ncsKeyword.trim());
    setSelectedNcs(null);
    setNcsCerts([]);
  }, [ncsKeyword, fetchNcsList]);

  const handleNcsSelect = useCallback((item: NcsItem) => {
    setSelectedNcs(item);
    fetchNcsCerts(item);
  }, [fetchNcsCerts]);

  const handleTabChange = useCallback((t: Tab) => {
    setTab(t);
    setQuery('');
  }, []);

  const totalPages = tab === 'jobs'
    ? Math.ceil(jobTotal / PAGE_SIZE)
    : Math.ceil(majorTotal / PAGE_SIZE);
  const currentPage = tab === 'jobs' ? jobPage : majorPage;

  return (
    <div className="ex-wrap">
      <div className="ex-header">
        <h1 className="ex-title">직업·학과·NCS 탐색</h1>
        <p className="ex-sub">커리어넷 직업정보, 학과정보, NCS 능력단위 기반 자격증을 한곳에서 탐색하세요.</p>
        <p className="ex-datasrc">데이터 출처: 한국직업능력연구원 커리어넷 (career.go.kr) · NCS 국가직무능력표준</p>
      </div>

      {/* 탭 */}
      <div className="ex-tab-bar">
        <button
          className={`ex-tab-btn${tab === 'jobs' ? ' active' : ''}`}
          onClick={() => handleTabChange('jobs')}
        >
          <Briefcase size={14} /> 직업 탐색
        </button>
        <button
          className={`ex-tab-btn${tab === 'majors' ? ' active' : ''}`}
          onClick={() => handleTabChange('majors')}
        >
          <BookOpen size={14} /> 학과 탐색
        </button>
        <button
          className={`ex-tab-btn${tab === 'ncs' ? ' active' : ''}`}
          onClick={() => handleTabChange('ncs')}
        >
          <Grid3X3 size={14} /> NCS 자격증
        </button>
      </div>

      {/* 직업 / 학과 탭 공용 검색바 */}
      {(tab === 'jobs' || tab === 'majors') && (
        <form
          className="ex-search-form"
          onSubmit={tab === 'jobs' ? handleJobSearch : handleMajorSearch}
        >
          <div className="ex-search-inner">
            <Search size={15} className="ex-search-icon" />
            <input
              className="ex-search-input"
              type="text"
              placeholder={tab === 'jobs' ? '직업명 검색 (예: 소프트웨어, 간호사)' : '학과명 검색 (예: 컴퓨터공학, 간호학)'}
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
            <button
              type="submit"
              className="btn-primary ex-search-btn"
              disabled={tab === 'jobs' ? jobLoading : majorLoading}
            >
              {(tab === 'jobs' ? jobLoading : majorLoading)
                ? <Loader2 size={14} className="spin" />
                : '검색'}
            </button>
          </div>
        </form>
      )}

      {/* 직업 탭 */}
      {tab === 'jobs' && (
        <div className="ex-content">
          {jobError && (
            <div className="ex-error">
              <AlertCircle size={15} />
              <span>{jobError}</span>
            </div>
          )}
          {jobLoading && (
            <div className="ex-loading">
              <Loader2 size={18} className="spin" />
              <span>커리어넷에서 직업 정보를 가져오는 중…</span>
            </div>
          )}
          {!jobLoading && jobResults.length === 0 && !jobError && (
            <div className="ex-placeholder">
              <Briefcase size={36} className="ex-placeholder-icon" />
              <h3>직업 정보 탐색</h3>
              <p>검색어를 입력하거나 빈 검색으로 전체 목록을 조회하세요.<br />각 직업을 클릭하면 업무 내용, 취업 전망, 관련 자격증을 확인할 수 있습니다.</p>
              <a
                href="https://www.career.go.kr/cnet/front/main/main.do"
                target="_blank"
                rel="noopener noreferrer"
                className="ex-ext-link"
              >
                <ExternalLink size={13} /> 커리어넷 바로가기
              </a>
            </div>
          )}
          {!jobLoading && jobResults.length > 0 && (
            <>
              <p className="ex-result-count">총 {jobTotal.toLocaleString()}개 직업 · {jobResults.length}개 표시</p>
              <div className="ex-card-list">
                {jobResults.map(job => (
                  <JobCard key={job.seq} job={job} />
                ))}
              </div>
              {totalPages > 1 && (
                <div className="ex-pagination">
                  <button
                    className="ex-page-btn"
                    disabled={currentPage <= 1 || jobLoading}
                    onClick={() => fetchJobs(query.trim(), currentPage - 1)}
                  >이전</button>
                  <span className="ex-page-info">{currentPage} / {totalPages}</span>
                  <button
                    className="ex-page-btn"
                    disabled={currentPage >= totalPages || jobLoading}
                    onClick={() => fetchJobs(query.trim(), currentPage + 1)}
                  >다음</button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* 학과 탭 */}
      {tab === 'majors' && (
        <div className="ex-content">
          {majorError && (
            <div className="ex-error">
              <AlertCircle size={15} />
              <span>{majorError}</span>
            </div>
          )}
          {majorLoading && (
            <div className="ex-loading">
              <Loader2 size={18} className="spin" />
              <span>커리어넷에서 학과 정보를 가져오는 중…</span>
            </div>
          )}
          {!majorLoading && majorResults.length === 0 && !majorError && (
            <div className="ex-placeholder">
              <BookOpen size={36} className="ex-placeholder-icon" />
              <h3>학과 정보 탐색</h3>
              <p>학과명을 검색하거나 빈 검색으로 전체 학과를 조회하세요.<br />각 학과를 클릭하면 관련 직업과 자격증을 확인할 수 있습니다.</p>
            </div>
          )}
          {!majorLoading && majorResults.length > 0 && (
            <>
              <p className="ex-result-count">총 {majorTotal.toLocaleString()}개 학과 · {majorResults.length}개 표시</p>
              <div className="ex-card-list">
                {majorResults.map(major => (
                  <MajorCard key={major.seq} major={major} />
                ))}
              </div>
              {totalPages > 1 && (
                <div className="ex-pagination">
                  <button
                    className="ex-page-btn"
                    disabled={currentPage <= 1 || majorLoading}
                    onClick={() => fetchMajors(query.trim(), currentPage - 1)}
                  >이전</button>
                  <span className="ex-page-info">{currentPage} / {totalPages}</span>
                  <button
                    className="ex-page-btn"
                    disabled={currentPage >= totalPages || majorLoading}
                    onClick={() => fetchMajors(query.trim(), currentPage + 1)}
                  >다음</button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* NCS 탭 */}
      {tab === 'ncs' && (
        <div className="ex-content">
          <form className="ex-search-form" onSubmit={handleNcsSearch}>
            <div className="ex-search-inner">
              <Search size={15} className="ex-search-icon" />
              <input
                className="ex-search-input"
                type="text"
                placeholder="NCS 분야 검색 (예: 정보통신, 건설, 경영사무)"
                value={ncsKeyword}
                onChange={e => setNcsKeyword(e.target.value)}
              />
              <button type="submit" className="btn-primary ex-search-btn" disabled={ncsListLoading}>
                {ncsListLoading ? <Loader2 size={14} className="spin" /> : '검색'}
              </button>
            </div>
          </form>

          {ncsList.length === 0 && !ncsListLoading && (
            <div className="ex-placeholder">
              <Grid3X3 size={36} className="ex-placeholder-icon" />
              <h3>NCS 기반 자격증 탐색</h3>
              <p>NCS 분야를 검색하면 해당 능력단위와 연결된 자격증 목록을 볼 수 있습니다.<br />"정보통신", "건설", "경영사무" 등 분야명을 검색해보세요.</p>
            </div>
          )}

          {ncsListLoading && (
            <div className="ex-loading">
              <Loader2 size={18} className="spin" />
              <span>NCS 목록 조회 중…</span>
            </div>
          )}

          {ncsList.length > 0 && (
            <div className="ex-ncs-layout">
              <div className="ex-ncs-list-panel">
                <p className="ex-ncs-list-label">NCS 분류 ({ncsList.length}개)</p>
                <div className="ex-ncs-list">
                  {ncsList.slice(0, 100).map(item => (
                    <button
                      key={item.ncs_id}
                      className={`ex-ncs-item${selectedNcs?.ncs_id === item.ncs_id ? ' selected' : ''}`}
                      onClick={() => handleNcsSelect(item)}
                    >
                      <span className="ex-ncs-major">{item.major_name}</span>
                      <span className="ex-ncs-mid"> › {item.mid_name}</span>
                      {item.minor_name && (
                        <span className="ex-ncs-minor"> › {item.minor_name}</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              <div className="ex-ncs-certs-panel">
                {!selectedNcs && (
                  <div className="ex-ncs-cert-placeholder">
                    <p>왼쪽에서 NCS 분류를 선택하면<br />연결된 자격증 목록이 표시됩니다.</p>
                  </div>
                )}
                {selectedNcs && (
                  <>
                    <p className="ex-ncs-selected-label">
                      <strong>{selectedNcs.major_name} › {selectedNcs.mid_name}</strong>
                      {selectedNcs.minor_name && ` › ${selectedNcs.minor_name}`}
                      <span className="ex-ncs-id-badge">{selectedNcs.ncs_id}</span>
                    </p>
                    {ncsCertsLoading && (
                      <div className="ex-loading">
                        <Loader2 size={16} className="spin" />
                        <span>자격증 조회 중…</span>
                      </div>
                    )}
                    {ncsCertsError && (
                      <div className="ex-error">
                        <AlertCircle size={14} />
                        <span>{ncsCertsError}</span>
                      </div>
                    )}
                    {!ncsCertsLoading && ncsCerts.length === 0 && !ncsCertsError && (
                      <p className="ex-ncs-cert-empty">이 NCS에 연결된 자격증이 없습니다.</p>
                    )}
                    {!ncsCertsLoading && ncsCerts.length > 0 && (
                      <>
                        <p className="ex-result-count">{ncsCerts.length}개 자격증</p>
                        <div className="ex-ncs-cert-list">
                          {ncsCerts.map(cert => (
                            <NcsCertCard key={cert.cert_id} cert={cert} />
                          ))}
                        </div>
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <style>{`
        .ex-wrap { display: flex; flex-direction: column; gap: 1.5rem; max-width: 900px; margin: 0 auto; }
        .ex-header { display: flex; flex-direction: column; gap: .35rem; }
        .ex-title { font-size: 1.75rem; font-weight: 900; color: var(--text); margin: 0; }
        .ex-sub { font-size: .9rem; color: var(--text-muted); margin: 0; }
        .ex-datasrc { font-size: .72rem; color: var(--text-light); margin: 0; }

        /* 탭 */
        .ex-tab-bar { display: flex; gap: .375rem; border-bottom: 2px solid var(--border); padding-bottom: 0; }
        .ex-tab-btn {
          display: flex; align-items: center; gap: .35rem;
          padding: .5rem 1rem; font-size: .85rem; font-weight: 600;
          color: var(--text-muted); background: none; border: none; cursor: pointer;
          border-bottom: 2px solid transparent; margin-bottom: -2px;
          transition: color .15s, border-color .15s;
        }
        .ex-tab-btn:hover { color: var(--primary); }
        .ex-tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); }

        /* 검색 */
        .ex-search-form { }
        .ex-search-inner {
          display: flex; align-items: center; gap: .5rem;
          background: var(--surface-2); border: 1px solid var(--border);
          border-radius: var(--radius-sm); padding: .5rem .75rem;
          transition: border-color .15s;
        }
        .ex-search-inner:focus-within { border-color: var(--primary); }
        .ex-search-icon { color: var(--text-light); flex-shrink: 0; }
        .ex-search-input {
          flex: 1; border: none; background: transparent;
          font-size: .875rem; color: var(--text); outline: none;
        }
        .ex-search-input::placeholder { color: var(--text-light); }
        .ex-search-btn { padding: .4rem .9rem; font-size: .82rem; }

        /* 컨텐츠 영역 */
        .ex-content { display: flex; flex-direction: column; gap: 1rem; }
        .ex-result-count { font-size: .75rem; color: var(--text-light); margin: 0; }

        /* 카드 */
        .ex-card-list { display: flex; flex-direction: column; gap: .5rem; }
        .ex-card {
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          background: var(--surface-2); overflow: hidden;
        }
        .ex-card-header {
          width: 100%; display: flex; flex-direction: column; align-items: flex-start; gap: .25rem;
          padding: .75rem 1rem; background: none; border: none; cursor: pointer; text-align: left;
          position: relative; padding-right: 2rem;
        }
        .ex-card-header:hover { background: var(--surface-3, #f8fafc); }
        .ex-card-title-row { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
        .ex-card-name { font-size: .9rem; font-weight: 700; color: var(--text); }
        .ex-salary-badge {
          font-size: .7rem; font-weight: 600;
          background: #ecfdf5; color: #059669;
          padding: .1rem .45rem; border-radius: 20px;
        }
        .ex-cat-badge {
          font-size: .7rem; background: var(--primary-light); color: var(--primary);
          padding: .1rem .45rem; border-radius: 20px;
        }
        .ex-emp-badge {
          font-size: .7rem; background: #fef3c7; color: #d97706;
          padding: .1rem .45rem; border-radius: 20px;
        }
        .ex-card-desc { font-size: .78rem; color: var(--text-muted); margin: 0; line-height: 1.5; }
        .ex-chevron {
          position: absolute; right: .875rem; top: .875rem;
          color: var(--text-light); transition: transform .15s;
          flex-shrink: 0;
        }
        .ex-chevron.open { transform: rotate(90deg); }

        .ex-card-detail {
          border-top: 1px solid var(--border); padding: .75rem 1rem;
          display: flex; flex-direction: column; gap: .5rem;
        }
        .ex-detail-row { display: flex; gap: .625rem; font-size: .8rem; }
        .ex-detail-key { font-weight: 700; color: var(--text-muted); white-space: nowrap; min-width: 70px; }
        .ex-detail-val { color: var(--text-muted); line-height: 1.55; }

        /* NCS 레이아웃 */
        .ex-ncs-layout { display: grid; grid-template-columns: 280px 1fr; gap: 1rem; }
        @media (max-width: 640px) { .ex-ncs-layout { grid-template-columns: 1fr; } }
        .ex-ncs-list-panel {
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          background: var(--surface-2); overflow: hidden;
          display: flex; flex-direction: column;
          max-height: 600px;
        }
        .ex-ncs-list-label {
          font-size: .72rem; font-weight: 700; color: var(--text-muted);
          padding: .5rem .75rem; border-bottom: 1px solid var(--border); margin: 0;
        }
        .ex-ncs-list { overflow-y: auto; flex: 1; }
        .ex-ncs-item {
          width: 100%; display: block; padding: .45rem .75rem;
          font-size: .78rem; color: var(--text-muted);
          background: none; border: none; cursor: pointer; text-align: left;
          border-bottom: 1px solid var(--border);
          transition: background .12s;
          line-height: 1.5;
        }
        .ex-ncs-item:hover { background: var(--surface-3, #f8fafc); }
        .ex-ncs-item.selected { background: var(--primary-light); }
        .ex-ncs-major { font-weight: 700; color: var(--text); }
        .ex-ncs-mid { color: var(--text-muted); }
        .ex-ncs-minor { color: var(--text-light); }

        .ex-ncs-certs-panel {
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          background: var(--surface-2); padding: .875rem; min-height: 200px;
          display: flex; flex-direction: column; gap: .625rem;
        }
        .ex-ncs-cert-placeholder {
          flex: 1; display: flex; align-items: center; justify-content: center;
          color: var(--text-light); font-size: .85rem; text-align: center;
          line-height: 1.7;
        }
        .ex-ncs-selected-label {
          font-size: .8rem; color: var(--text-muted); margin: 0;
          display: flex; align-items: center; gap: .5rem; flex-wrap: wrap;
        }
        .ex-ncs-id-badge {
          font-size: .68rem; background: var(--border); color: var(--text-light);
          padding: .1rem .4rem; border-radius: 4px;
        }
        .ex-ncs-cert-empty { font-size: .82rem; color: var(--text-light); margin: 0; }
        .ex-ncs-cert-list { display: flex; flex-direction: column; gap: .375rem; }
        .ex-ncs-cert-card {
          padding: .5rem .75rem; background: var(--surface);
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          display: flex; flex-direction: column; gap: .2rem;
        }
        .ex-ncs-cert-top { display: flex; align-items: center; gap: .5rem; }
        .ex-ncs-cert-name { font-size: .85rem; font-weight: 700; color: var(--text); }
        .ex-ncs-tier-badge { font-size: .7rem; font-weight: 700; }
        .ex-ncs-cert-meta { display: flex; gap: .5rem; flex-wrap: wrap; }
        .ex-ncs-meta-item { font-size: .72rem; color: var(--text-light); }

        /* 상태 */
        .ex-loading { display: flex; align-items: center; gap: .625rem; padding: 2rem; justify-content: center; color: var(--text-muted); font-size: .875rem; }
        .ex-error { display: flex; align-items: center; gap: .5rem; padding: .875rem 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: var(--radius-sm); color: #dc2626; font-size: .82rem; }
        .ex-placeholder {
          display: flex; flex-direction: column; align-items: center; gap: .75rem;
          padding: 3rem 1.5rem; background: var(--surface-2);
          border: 1px dashed var(--border); border-radius: var(--radius-sm);
          text-align: center;
        }
        .ex-placeholder-icon { color: var(--border-strong); }
        .ex-placeholder h3 { font-size: .95rem; font-weight: 700; color: var(--text-muted); margin: 0; }
        .ex-placeholder p { font-size: .82rem; color: var(--text-light); margin: 0; line-height: 1.7; }
        .ex-ext-link {
          display: inline-flex; align-items: center; gap: .3rem;
          font-size: .78rem; color: var(--primary); text-decoration: none;
          padding: .3rem .7rem; border: 1px solid var(--primary); border-radius: var(--radius-sm);
          transition: background .15s;
        }
        .ex-ext-link:hover { background: var(--primary-light); }

        /* 페이지네이션 */
        .ex-pagination { display: flex; align-items: center; gap: .75rem; justify-content: center; }
        .ex-page-btn {
          padding: .35rem .85rem; font-size: .82rem; font-weight: 600;
          background: var(--surface-2); border: 1px solid var(--border);
          border-radius: var(--radius-sm); cursor: pointer; color: var(--text-muted);
          transition: all .15s;
        }
        .ex-page-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
        .ex-page-btn:disabled { opacity: .4; cursor: not-allowed; }
        .ex-page-info { font-size: .8rem; color: var(--text-muted); }

        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default Explore;
