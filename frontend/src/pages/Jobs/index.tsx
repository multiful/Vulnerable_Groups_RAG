// Content Hash: SHA256:TBD
import React, { useState, useCallback, useRef } from 'react';
import { Search, Briefcase, MapPin, GraduationCap, ExternalLink, Loader2, AlertCircle } from 'lucide-react';

interface HiringJob {
  title?: string;
  company?: string;
  location?: string;
  salary?: string;
  education?: string;
  deadline?: string;
  url?: string;
  job_type?: string;
  experience?: string;
  [key: string]: unknown;
}

interface HiringResponse {
  jobs: HiringJob[];
  total: number;
  keyword?: string;
  region?: string;
}

const REGIONS = ['전국', '서울', '경기', '인천', '부산', '대구', '광주', '대전', '울산', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'];
const EDU_OPTIONS = [
  { code: '', label: '학력 무관' },
  { code: '02', label: '고졸' },
  { code: '03', label: '대졸(2년)' },
  { code: '05', label: '대졸(4년)' },
  { code: '06', label: '석사' },
  { code: '07', label: '박사' },
];
const CAREER_OPTIONS = [
  { code: '', label: '경력 무관' },
  { code: 'N', label: '신입' },
  { code: 'E', label: '경력' },
];

function JobCard({ job }: { job: HiringJob }) {
  const title = (job.title as string) || '(제목 없음)';
  const company = (job.company as string) || '';
  const companyType = (job.company_type as string) || '';
  const region = (job.region as string) || '';
  const salary = (job.salary as string) || '';
  const salType = (job.sal_type as string) || '';
  const education = (job.education as string) || '';
  const career = (job.career as string) || '';
  const employmentType = (job.employment_type as string) || '';
  const closeDate = (job.close_date as string) || '';
  const url = (job.url as string) || '';

  return (
    <div className="job-card">
      <div className="job-card-top">
        <span className="job-card-title">{title}</span>
        <div className="job-card-company-row">
          {company && <span className="job-card-company">{company}</span>}
          {companyType && <span className="job-company-type-badge">{companyType}</span>}
        </div>
      </div>
      <div className="job-card-meta">
        {region && (
          <span className="job-meta-item">
            <MapPin size={11} /> {region}
          </span>
        )}
        {salary && (
          <span className="job-meta-item job-meta-salary">
            {salType && <span className="job-sal-type">{salType}</span>} {salary}
          </span>
        )}
        {education && (
          <span className="job-meta-item">
            <GraduationCap size={11} /> {education}
          </span>
        )}
        {career && (
          <span className="job-meta-item">{career}</span>
        )}
        {employmentType && (
          <span className="job-meta-item job-emp-type">{employmentType}</span>
        )}
        {closeDate && (
          <span className="job-meta-item job-meta-deadline">마감: {closeDate}</span>
        )}
      </div>
      {url && (
        <a className="job-card-link" href={url} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={11} /> 채용 상세 보기
        </a>
      )}
    </div>
  );
}

const Jobs: React.FC = () => {
  const [keyword, setKeyword] = useState('');
  const [region, setRegion] = useState('');
  const [education, setEducation] = useState('');
  const [career, setCareer] = useState('');
  const [results, setResults] = useState<HiringJob[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const cacheRef = useRef<Record<string, HiringResponse>>({});

  const fetchJobs = useCallback(async () => {
    const cacheKey = `${keyword}__${region}__${education}__${career}`;
    if (cacheRef.current[cacheKey]) {
      const cached = cacheRef.current[cacheKey];
      setResults(cached.jobs);
      setTotal(cached.total);
      setSearched(true);
      return;
    }

    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const params = new URLSearchParams({ display: '30' });
      if (keyword.trim()) params.set('keyword', keyword.trim());
      if (region && region !== '전국') params.set('region', region);
      if (education) params.set('education', education);
      if (career) params.set('career', career);

      const r = await fetch(`/api/v1/jobs/hiring?${params}`);
      const json = await r.json();

      if (json.success && json.data) {
        const jobs: HiringJob[] = json.data.jobs ?? [];
        const t: number = json.data.total ?? jobs.length;
        cacheRef.current[cacheKey] = { jobs, total: t };
        setResults(jobs);
        setTotal(t);
      } else {
        setError(json.error?.message ?? '채용 정보를 불러올 수 없습니다. WorkNet API 상태를 확인해주세요.');
      }
    } catch {
      setError('채용 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
    setLoading(false);
  }, [keyword, region, education, career]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs();
  }, [fetchJobs]);

  return (
    <div className="jobs-wrap">
      <div className="jobs-header">
        <h1 className="jobs-title">채용 정보</h1>
        <p className="jobs-sub">
          키워드, 지역, 학력 조건으로 원하는 공고를 찾아보세요.
        </p>
      </div>

      {/* 검색 폼 */}
      <form className="jobs-search-form" onSubmit={handleSubmit}>
        <div className="jobs-search-row">
          <div className="jobs-search-input-wrap">
            <Search size={15} className="jobs-search-icon" />
            <input
              className="jobs-search-input"
              type="text"
              placeholder="직종 키워드 검색 (예: 소프트웨어, 간호사, 회계)"
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
            />
          </div>
        </div>
        <div className="jobs-filter-row">
          <select
            className="jobs-filter-select"
            value={region}
            onChange={e => setRegion(e.target.value)}
          >
            {REGIONS.map(r => (
              <option key={r} value={r === '전국' ? '' : r}>{r}</option>
            ))}
          </select>
          <select
            className="jobs-filter-select"
            value={education}
            onChange={e => setEducation(e.target.value)}
          >
            {EDU_OPTIONS.map(e => (
              <option key={e.code} value={e.code}>{e.label}</option>
            ))}
          </select>
          <select
            className="jobs-filter-select"
            value={career}
            onChange={e => setCareer(e.target.value)}
          >
            {CAREER_OPTIONS.map(c => (
              <option key={c.code} value={c.code}>{c.label}</option>
            ))}
          </select>
          <button type="submit" className="btn-primary jobs-search-btn" disabled={loading}>
            {loading ? <Loader2 size={15} className="spin" /> : <><Search size={14} /> 채용 검색</>}
          </button>
        </div>
      </form>

      {/* 에러 */}
      {error && (
        <div className="jobs-error">
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* 로딩 */}
      {loading && (
        <div className="jobs-loading">
          <Loader2 size={20} className="spin" />
          <span>WorkNet에서 채용 정보를 가져오는 중…</span>
        </div>
      )}

      {/* 결과 없음 */}
      {!loading && searched && results.length === 0 && !error && (
        <div className="jobs-empty">
          <Briefcase size={36} className="jobs-empty-icon" />
          <h3>검색 결과가 없습니다</h3>
          <p>다른 키워드나 조건으로 다시 검색해보세요.<br />조건을 더 넓게 설정하면 더 많은 결과가 나타납니다.</p>
        </div>
      )}

      {/* 안내 (첫 화면) */}
      {!searched && !loading && (
        <div className="jobs-intro">
          <div className="jobs-intro-card">
            <Briefcase size={26} className="jobs-intro-icon" />
            <h3>실시간 채용 정보</h3>
            <p>WorkNet에서 실시간으로 제공하는 채용 공고를 검색합니다. 지역·학력 조건을 설정해 원하는 채용 정보를 찾아보세요.</p>
          </div>
          <div className="jobs-intro-card">
            <MapPin size={26} className="jobs-intro-icon" />
            <h3>지역 필터</h3>
            <p>서울, 경기, 부산 등 지역별로 필터링할 수 있습니다. 전국으로 설정하면 전체 채용 공고를 볼 수 있습니다.</p>
          </div>
          <div className="jobs-intro-card">
            <GraduationCap size={26} className="jobs-intro-icon" />
            <h3>학력 조건</h3>
            <p>학력 요건에 맞는 채용 공고만 필터링합니다. 위험군 단계와 상황에 맞는 현실적인 채용 정보를 찾아보세요.</p>
          </div>
        </div>
      )}

      {/* 결과 목록 */}
      {!loading && results.length > 0 && (
        <div className="jobs-results">
          <p className="jobs-result-count">
            총 {total.toLocaleString()}개 채용 공고 · {results.length}개 표시
          </p>
          <div className="jobs-list">
            {results.map((job, i) => (
              <JobCard key={i} job={job} />
            ))}
          </div>
          <div className="jobs-worknet-link-row">
            <a
              href="https://www.work24.go.kr/wk/a/b/1200/retrivewantedList.do"
              target="_blank"
              rel="noopener noreferrer"
              className="jobs-ext-link"
            >
              <ExternalLink size={13} /> WorkNet에서 더 보기
            </a>
          </div>
        </div>
      )}

      <style>{`
        .jobs-wrap { display: flex; flex-direction: column; gap: 1.75rem; max-width: 860px; margin: 0 auto; }
        .jobs-header { display: flex; flex-direction: column; gap: .35rem; }
        .jobs-title { font-size: 1.75rem; font-weight: 900; color: var(--text); margin: 0; }
        .jobs-sub { font-size: .9rem; color: var(--text-muted); margin: 0; }
        .jobs-datasrc { font-size: .72rem; color: var(--text-light); margin: 0; }

        /* 검색 폼 */
        .jobs-search-form { display: flex; flex-direction: column; gap: .625rem; }
        .jobs-search-row {
          display: flex; align-items: center;
          background: var(--surface-2); border: 1px solid var(--border);
          border-radius: var(--radius-sm); padding: .5rem .75rem;
          transition: border-color .15s;
        }
        .jobs-search-row:focus-within { border-color: var(--primary); }
        .jobs-search-input-wrap { display: flex; align-items: center; gap: .5rem; width: 100%; }
        .jobs-search-icon { color: var(--text-light); flex-shrink: 0; }
        .jobs-search-input {
          flex: 1; border: none; background: transparent;
          font-size: .9rem; color: var(--text); outline: none;
        }
        .jobs-search-input::placeholder { color: var(--text-light); }
        .jobs-filter-row { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }
        .jobs-filter-select {
          padding: .4rem .65rem; font-size: .82rem;
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          background: var(--surface-2); color: var(--text-muted); cursor: pointer;
          outline: none;
        }
        .jobs-filter-select:focus { border-color: var(--primary); }
        .jobs-search-btn {
          display: flex; align-items: center; gap: .35rem;
          padding: .45rem 1rem; font-size: .85rem;
          margin-left: auto;
        }

        /* 결과 */
        .jobs-results { display: flex; flex-direction: column; gap: .625rem; }
        .jobs-result-count { font-size: .75rem; color: var(--text-light); margin: 0; }
        .jobs-list { display: flex; flex-direction: column; gap: .5rem; }
        .job-card {
          padding: .875rem 1rem; background: var(--surface-2);
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          display: flex; flex-direction: column; gap: .375rem;
          transition: border-color .15s;
        }
        .job-card:hover { border-color: var(--primary); }
        .job-card-top { display: flex; flex-direction: column; gap: .15rem; }
        .job-card-title { font-size: .9rem; font-weight: 700; color: var(--text); }
        .job-card-company-row { display: flex; align-items: center; gap: .4rem; flex-wrap: wrap; }
        .job-card-company { font-size: .8rem; color: var(--text-muted); }
        .job-company-type-badge {
          font-size: .68rem; background: var(--primary-light); color: var(--primary);
          padding: .1rem .4rem; border-radius: 20px;
        }
        .job-sal-type { font-size: .68rem; opacity: .8; }
        .job-emp-type { color: #7c3aed; }
        .job-card-meta { display: flex; gap: .625rem; flex-wrap: wrap; }
        .job-meta-item {
          display: inline-flex; align-items: center; gap: .2rem;
          font-size: .72rem; color: var(--text-light);
        }
        .job-meta-salary { color: #059669; font-weight: 600; }
        .job-meta-deadline { color: #d97706; }
        .job-card-link {
          display: inline-flex; align-items: center; gap: .3rem;
          font-size: .75rem; color: var(--primary); text-decoration: none;
          width: fit-content; transition: opacity .15s;
        }
        .job-card-link:hover { opacity: .75; }

        /* 상태 */
        .jobs-loading { display: flex; align-items: center; gap: .625rem; padding: 2.5rem; justify-content: center; color: var(--text-muted); font-size: .9rem; }
        .jobs-error { display: flex; align-items: flex-start; gap: .5rem; padding: .875rem 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: var(--radius-sm); color: #dc2626; font-size: .82rem; }
        .jobs-empty {
          display: flex; flex-direction: column; align-items: center; gap: .625rem;
          padding: 3rem 1.5rem; background: var(--surface-2);
          border: 1px dashed var(--border); border-radius: var(--radius-sm); text-align: center;
        }
        .jobs-empty-icon { color: var(--border-strong); }
        .jobs-empty h3 { font-size: .9rem; font-weight: 700; color: var(--text-muted); margin: 0; }
        .jobs-empty p { font-size: .82rem; color: var(--text-light); margin: 0; line-height: 1.7; }

        .jobs-intro { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
        @media (max-width: 640px) { .jobs-intro { grid-template-columns: 1fr; } }
        .jobs-intro-card {
          display: flex; flex-direction: column; gap: .5rem;
          padding: 1.25rem; background: var(--surface-2);
          border: 1px solid var(--border); border-radius: var(--radius-sm);
        }
        .jobs-intro-icon { color: var(--primary); }
        .jobs-intro-card h3 { font-size: .875rem; font-weight: 700; color: var(--text); margin: 0; }
        .jobs-intro-card p { font-size: .78rem; color: var(--text-muted); margin: 0; line-height: 1.65; }

        .jobs-worknet-link-row { display: flex; justify-content: center; padding-top: .5rem; }
        .jobs-ext-link {
          display: inline-flex; align-items: center; gap: .35rem;
          font-size: .8rem; color: var(--primary); text-decoration: none;
          padding: .375rem .875rem; border: 1px solid var(--primary);
          border-radius: var(--radius-sm); transition: background .15s;
        }
        .jobs-ext-link:hover { background: var(--primary-light); }

        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default Jobs;
