// Content Hash: SHA256:TBD
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, BookOpen, GraduationCap, MapPin, ExternalLink, Loader2, AlertCircle, Clock, DollarSign } from 'lucide-react';

type Tab = 'courses' | 'process-eval' | 'job-learner';

interface TrainingCourse {
  course_id?: string;
  course_name?: string;
  institution_name?: string;
  institution_addr?: string;
  course_url?: string;
  institution_url?: string;
  ncs_name?: string;
  train_start?: string;
  train_end?: string;
  train_hours?: string;
  cost?: string;
  support_amount?: string;
  satisfaction?: string;
  employment_rate?: string;
  capacity?: string;
  remaining?: string;
  tel?: string;
  homepage?: string;
}

const REGIONS = ['전국', '서울', '경기', '인천', '부산', '대구', '광주', '대전', '울산', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'];

const NCS_CATEGORIES = [
  '정보통신', '전기/전자', '경영/회계/사무', '기계', '건설',
  '보건/의료', '사회복지/종교', '교육/자연/사회과학', '화학/바이오',
  '환경/에너지/안전', '금융/보험', '문화/예술/디자인/방송',
  '음식서비스', '이용/숙박/여행/오락/스포츠', '사업관리',
];

function CourseCard({ course }: { course: TrainingCourse }) {
  const name = course.course_name || '(과정명 없음)';
  const inst = course.institution_name || '';
  const ncs = course.ncs_name || '';
  const addr = course.institution_addr || '';
  const start = course.train_start || '';
  const end = course.train_end || '';
  const hours = course.train_hours || '';
  const cost = course.cost ? `${Number(course.cost).toLocaleString()}원` : '';
  const support = course.support_amount ? `${Number(course.support_amount).toLocaleString()}원` : '';
  const empRate = course.employment_rate || '';
  const remaining = course.remaining || '';
  const url = course.course_url || course.homepage || course.institution_url || '';

  const formatDate = (d: string) => {
    if (!d || d.length < 8) return d;
    return `${d.slice(0, 4)}.${d.slice(4, 6)}.${d.slice(6, 8)}`;
  };

  return (
    <div className="tc-card">
      <div className="tc-card-top">
        <span className="tc-course-name">{name}</span>
        {ncs && <span className="tc-ncs-badge">{ncs}</span>}
      </div>
      {inst && <span className="tc-inst-name">{inst}</span>}
      <div className="tc-meta-row">
        {addr && (
          <span className="tc-meta-item">
            <MapPin size={11} /> {addr.slice(0, 20)}{addr.length > 20 ? '…' : ''}
          </span>
        )}
        {(start || end) && (
          <span className="tc-meta-item">
            <Clock size={11} /> {formatDate(start)} ~ {formatDate(end)}
          </span>
        )}
        {hours && (
          <span className="tc-meta-item"><Clock size={11} /> {hours}h</span>
        )}
        {cost && (
          <span className="tc-meta-item tc-cost">
            <DollarSign size={11} />
            훈련비 {cost}
            {support && <span className="tc-support"> (지원 {support})</span>}
          </span>
        )}
        {empRate && (
          <span className="tc-meta-item tc-emp-rate">취업률 {empRate}%</span>
        )}
        {remaining && (
          <span className="tc-meta-item tc-remaining">잔여 {remaining}석</span>
        )}
      </div>
      {url && (
        <a className="tc-card-link" href={url} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={11} /> 과정 상세 보기
        </a>
      )}
    </div>
  );
}

const Training: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialTab = (['courses', 'process-eval', 'job-learner'].includes(searchParams.get('tab') ?? ''))
    ? (searchParams.get('tab') as Tab) : 'courses';
  const [tab, setTab] = useState<Tab>(initialTab);

  const [keyword, setKeyword] = useState(searchParams.get('keyword') || '');
  const [region, setRegion] = useState('');
  const [ncsCategory, setNcsCategory] = useState('');
  const [results, setResults] = useState<TrainingCourse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const cacheRef = useRef<Record<string, { courses: TrainingCourse[]; total: number }>>({});
  const didAutoSearch = useRef(false);

  const fetchCourses = useCallback(async (kw: string, reg: string, ncs: string) => {
    const cacheKey = `${kw}__${reg}__${ncs}`;
    if (cacheRef.current[cacheKey]) {
      const c = cacheRef.current[cacheKey];
      setResults(c.courses);
      setTotal(c.total);
      setSearched(true);
      return;
    }
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const params = new URLSearchParams({ page_size: '30' });
      if (kw.trim()) params.set('course_name', kw.trim());
      if (reg && reg !== '전국') params.set('region', reg);
      if (ncs) params.set('ncs_category', ncs);

      const r = await fetch(`/api/v1/training/courses?${params}`);
      const json = await r.json();
      if (json.success && json.data) {
        const courses: TrainingCourse[] = json.data.courses ?? [];
        const t: number = json.data.total ?? courses.length;
        cacheRef.current[cacheKey] = { courses, total: t };
        setResults(courses);
        setTotal(t);
      } else {
        setError(json.error?.message ?? '훈련과정 정보를 불러올 수 없습니다.');
      }
    } catch {
      setError('훈련과정 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
    setLoading(false);
  }, []);

  // keyword가 URL 파라미터로 넘어온 경우 자동 검색
  useEffect(() => {
    const kw = searchParams.get('keyword');
    if (kw && !didAutoSearch.current) {
      didAutoSearch.current = true;
      setKeyword(kw);
      fetchCourses(kw, '', '');
    }
  }, [searchParams, fetchCourses]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    fetchCourses(keyword, region, ncsCategory);
  }, [keyword, region, ncsCategory, fetchCourses]);

  return (
    <div className="tc-wrap">
      <div className="tc-header">
        <h1 className="tc-title">훈련과정</h1>
        <p className="tc-sub">국민내일배움카드 훈련과정, 과정평가형 자격, 일학습병행 경로를 한곳에서 확인하세요.</p>
      </div>

      {/* 탭 */}
      <div className="tc-tab-bar">
        <button className={`tc-tab-btn${tab === 'courses' ? ' active' : ''}`} onClick={() => setTab('courses')}>
          <BookOpen size={14} /> 훈련과정 검색
        </button>
        <button className={`tc-tab-btn${tab === 'process-eval' ? ' active' : ''}`} onClick={() => setTab('process-eval')}>
          <GraduationCap size={14} /> 과정평가형 자격
        </button>
        <button className={`tc-tab-btn${tab === 'job-learner' ? ' active' : ''}`} onClick={() => setTab('job-learner')}>
          <GraduationCap size={14} /> 일학습병행
        </button>
      </div>

      {/* 훈련과정 검색 탭 */}
      {tab === 'courses' && (
        <>
          <form className="tc-search-form" onSubmit={handleSubmit}>
            <div className="tc-search-row">
              <div className="tc-search-input-wrap">
                <Search size={15} className="tc-search-icon" />
                <input
                  className="tc-search-input"
                  type="text"
                  placeholder="훈련과정명 검색 (예: 파이썬, 간호조무사, 전기기사)"
                  value={keyword}
                  onChange={e => setKeyword(e.target.value)}
                />
              </div>
            </div>
            <div className="tc-filter-row">
              <select className="tc-filter-select" value={region} onChange={e => setRegion(e.target.value)}>
                {REGIONS.map(r => (
                  <option key={r} value={r === '전국' ? '' : r}>{r}</option>
                ))}
              </select>
              <select className="tc-filter-select" value={ncsCategory} onChange={e => setNcsCategory(e.target.value)}>
                <option value="">NCS 분야 전체</option>
                {NCS_CATEGORIES.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              <button type="submit" className="btn-primary tc-search-btn" disabled={loading}>
                {loading ? <Loader2 size={15} className="spin" /> : <><Search size={14} /> 검색</>}
              </button>
            </div>
          </form>

          {error && (
            <div className="tc-error-wrap">
              <AlertCircle size={15} className="tc-error-icon" />
              <div>
                <p className="tc-error-title">훈련과정 조회 실패</p>
                <p className="tc-error-msg">{error}</p>
              </div>
              <a
                href="https://www.work24.go.kr/cm/c/f/1100/selecSystInfo.do?systClId=SC00000254&systId=SI00000411"
                target="_blank" rel="noopener noreferrer"
                className="tc-fallback-btn"
              >
                <ExternalLink size={13} /> Work24에서 직접 조회
              </a>
            </div>
          )}

          {loading && (
            <div className="tc-loading">
              <Loader2 size={20} className="spin" />
              <span>Work24에서 훈련과정을 가져오는 중…</span>
            </div>
          )}

          {!loading && searched && results.length === 0 && !error && (
            <div className="tc-empty">
              <BookOpen size={36} className="tc-empty-icon" />
              <h3>검색 결과가 없습니다</h3>
              <p>다른 키워드나 NCS 분야로 다시 검색해보세요.<br />조건을 더 넓게 설정하면 더 많은 결과가 나타납니다.</p>
              <a
                href="https://www.work24.go.kr/cm/c/f/1100/selecSystInfo.do?systClId=SC00000254&systId=SI00000411"
                target="_blank" rel="noopener noreferrer"
                className="tc-ext-link"
              >
                Work24 훈련과정 바로가기 →
              </a>
            </div>
          )}

          {!searched && !loading && (
            <div className="tc-intro">
              <div className="tc-intro-card">
                <BookOpen size={26} className="tc-intro-icon" />
                <h3>국민내일배움카드</h3>
                <p>실업자·재직자 누구나 발급 가능. 최대 500만원 훈련비 지원. 직업훈련 포털 HRD-Net 연계 과정.</p>
              </div>
              <div className="tc-intro-card">
                <MapPin size={26} className="tc-intro-icon" />
                <h3>지역·NCS 필터</h3>
                <p>원하는 지역과 NCS 분야를 선택해 내게 맞는 훈련과정을 찾으세요. 자격증 추천에서 바로 연결도 됩니다.</p>
              </div>
              <div className="tc-intro-card">
                <GraduationCap size={26} className="tc-intro-icon" />
                <h3>취업률 기준 정렬</h3>
                <p>수료 후 취업률이 높은 과정 순으로 표시합니다. 훈련비 지원금과 잔여 정원도 함께 확인하세요.</p>
              </div>
            </div>
          )}

          {!loading && results.length > 0 && (
            <div className="tc-results">
              <p className="tc-result-count">총 {total.toLocaleString()}개 과정 · {results.length}개 표시</p>
              <div className="tc-course-list">
                {results.map((c, i) => (
                  <CourseCard key={c.course_id || i} course={c} />
                ))}
              </div>
              <div className="tc-ext-link-row">
                <a
                  href="https://www.work24.go.kr/cm/c/f/1100/selecSystInfo.do?systClId=SC00000254&systId=SI00000411"
                  target="_blank" rel="noopener noreferrer"
                  className="tc-ext-link"
                >
                  <ExternalLink size={13} /> Work24에서 더 보기
                </a>
              </div>
            </div>
          )}
        </>
      )}

      {/* 과정평가형 탭 */}
      {tab === 'process-eval' && (
        <div className="tc-info-section">
          <div className="tc-info-card">
            <div className="tc-info-icon-wrap">
              <GraduationCap size={32} className="tc-info-icon" />
            </div>
            <h2 className="tc-info-title">과정평가형 자격</h2>
            <p className="tc-info-desc">
              NCS 기반 교육훈련 과정을 이수하고 내부·외부 평가를 거쳐 자격을 취득하는 방식입니다.<br />
              필기·실기 시험 부담 없이 교육 이수만으로 자격 취득 가능 — 4~5단계 청년에게 권장 경로입니다.
            </p>
            <div className="tc-info-tags">
              <span className="tc-info-tag tc-tag-green">시험 부담 낮음</span>
              <span className="tc-info-tag tc-tag-blue">NCS 기반</span>
              <span className="tc-info-tag tc-tag-purple">교육 이수로 취득</span>
            </div>
            <a
              href="https://www.q-net.or.kr/man004.do?id=man00401&gSite=Q"
              target="_blank" rel="noopener noreferrer"
              className="tc-info-btn"
            >
              <ExternalLink size={14} /> Q-Net 과정평가형 자격 바로가기
            </a>
          </div>
          <div className="tc-info-steps">
            <h3 className="tc-info-steps-title">취득 절차</h3>
            {[
              { step: '1', label: '훈련기관 선택', desc: '과정평가형 승인된 훈련기관에서 과정 수강' },
              { step: '2', label: '내부 평가', desc: '훈련기관이 실시하는 역량 평가 (출석·과제·실습)' },
              { step: '3', label: '외부 평가', desc: '한국산업인력공단이 실시하는 표준 평가' },
              { step: '4', label: '자격증 발급', desc: '내부·외부 평가 합산 80점 이상 시 자격증 발급' },
            ].map(s => (
              <div key={s.step} className="tc-step-item">
                <div className="tc-step-num">{s.step}</div>
                <div className="tc-step-body">
                  <span className="tc-step-label">{s.label}</span>
                  <span className="tc-step-desc">{s.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 일학습병행 탭 */}
      {tab === 'job-learner' && (
        <div className="tc-info-section">
          <div className="tc-info-card">
            <div className="tc-info-icon-wrap">
              <GraduationCap size={32} className="tc-info-icon" />
            </div>
            <h2 className="tc-info-title">일학습병행</h2>
            <p className="tc-info-desc">
              기업에 취업해 일하면서 NCS 기반 현장훈련을 받고 자격을 취득하는 제도입니다.<br />
              취업과 자격 취득을 동시에 해결할 수 있는 고위험군(4~5단계) 청년을 위한 대안 경로입니다.
            </p>
            <div className="tc-info-tags">
              <span className="tc-info-tag tc-tag-green">취업 + 자격 동시</span>
              <span className="tc-info-tag tc-tag-blue">기업 현장훈련</span>
              <span className="tc-info-tag tc-tag-orange">고위험군 권장</span>
            </div>
            <a
              href="https://www.q-net.or.kr/ilhak001.do"
              target="_blank" rel="noopener noreferrer"
              className="tc-info-btn"
            >
              <ExternalLink size={14} /> Q-Net 일학습병행 바로가기
            </a>
          </div>
          <div className="tc-info-steps">
            <h3 className="tc-info-steps-title">참여 절차</h3>
            {[
              { step: '1', label: '일학습병행 기업 입사', desc: '고용24 또는 일학습병행 참여 기업에 지원·취업' },
              { step: '2', label: '현장훈련 이수', desc: '기업 내 현장훈련 + 외부 교육훈련기관 훈련 병행' },
              { step: '3', label: '학습근로자 평가', desc: '내부평가(과제·포트폴리오) + 외부평가 응시' },
              { step: '4', label: '자격·학위 취득', desc: '평가 통과 시 NCS 기반 자격 또는 학위 취득' },
            ].map(s => (
              <div key={s.step} className="tc-step-item">
                <div className="tc-step-num">{s.step}</div>
                <div className="tc-step-body">
                  <span className="tc-step-label">{s.label}</span>
                  <span className="tc-step-desc">{s.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{`
        .tc-wrap { display: flex; flex-direction: column; gap: 1.75rem; max-width: 860px; margin: 0 auto; }
        .tc-header { display: flex; flex-direction: column; gap: .35rem; }
        .tc-title { font-size: 1.75rem; font-weight: 900; color: var(--text); margin: 0; }
        .tc-sub { font-size: .9rem; color: var(--text-muted); margin: 0; }

        /* 탭 */
        .tc-tab-bar { display: flex; gap: .375rem; border-bottom: 2px solid var(--border); }
        .tc-tab-btn {
          display: flex; align-items: center; gap: .35rem;
          padding: .5rem 1rem; font-size: .85rem; font-weight: 600;
          color: var(--text-muted); background: none; border: none; cursor: pointer;
          border-bottom: 2px solid transparent; margin-bottom: -2px;
          transition: color .15s, border-color .15s;
        }
        .tc-tab-btn:hover { color: var(--primary); }
        .tc-tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); }

        /* 검색 폼 */
        .tc-search-form { display: flex; flex-direction: column; gap: .625rem; }
        .tc-search-row {
          display: flex; align-items: center;
          background: var(--surface-2); border: 1px solid var(--border);
          border-radius: var(--radius-sm); padding: .5rem .75rem;
          transition: border-color .15s;
        }
        .tc-search-row:focus-within { border-color: var(--primary); }
        .tc-search-input-wrap { display: flex; align-items: center; gap: .5rem; width: 100%; }
        .tc-search-icon { color: var(--text-light); flex-shrink: 0; }
        .tc-search-input {
          flex: 1; border: none; background: transparent;
          font-size: .9rem; color: var(--text); outline: none;
        }
        .tc-search-input::placeholder { color: var(--text-light); }
        .tc-filter-row { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }
        .tc-filter-select {
          padding: .4rem .65rem; font-size: .82rem;
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          background: var(--surface-2); color: var(--text-muted); cursor: pointer; outline: none;
        }
        .tc-filter-select:focus { border-color: var(--primary); }
        .tc-search-btn {
          display: flex; align-items: center; gap: .35rem;
          padding: .45rem 1rem; font-size: .85rem; margin-left: auto;
        }

        /* 카드 */
        .tc-results { display: flex; flex-direction: column; gap: .625rem; }
        .tc-result-count { font-size: .75rem; color: var(--text-light); margin: 0; }
        .tc-course-list { display: flex; flex-direction: column; gap: .5rem; }
        .tc-card {
          padding: .875rem 1rem; background: var(--surface-2);
          border: 1px solid var(--border); border-radius: var(--radius-sm);
          display: flex; flex-direction: column; gap: .375rem;
          transition: border-color .15s;
        }
        .tc-card:hover { border-color: var(--primary); }
        .tc-card-top { display: flex; align-items: flex-start; gap: .5rem; flex-wrap: wrap; }
        .tc-course-name { font-size: .9rem; font-weight: 700; color: var(--text); flex: 1; }
        .tc-ncs-badge {
          font-size: .68rem; background: #f0f4ff; color: #4338ca;
          padding: .1rem .45rem; border-radius: 20px; flex-shrink: 0; white-space: nowrap;
        }
        .tc-inst-name { font-size: .8rem; color: var(--text-muted); }
        .tc-meta-row { display: flex; gap: .625rem; flex-wrap: wrap; }
        .tc-meta-item {
          display: inline-flex; align-items: center; gap: .2rem;
          font-size: .72rem; color: var(--text-light);
        }
        .tc-cost { color: #059669; font-weight: 600; }
        .tc-support { color: var(--text-light); font-weight: 400; }
        .tc-emp-rate { color: #7c3aed; font-weight: 600; }
        .tc-remaining { color: #d97706; }
        .tc-card-link {
          display: inline-flex; align-items: center; gap: .3rem;
          font-size: .75rem; color: var(--primary); text-decoration: none;
          width: fit-content; transition: opacity .15s;
        }
        .tc-card-link:hover { opacity: .75; }

        /* 상태 */
        .tc-loading { display: flex; align-items: center; gap: .625rem; padding: 2.5rem; justify-content: center; color: var(--text-muted); font-size: .9rem; }
        .tc-error-wrap {
          display: flex; align-items: flex-start; gap: .625rem;
          padding: 1rem; background: #fffbeb; border: 1px solid #fde68a;
          border-radius: var(--radius-sm); flex-wrap: wrap;
        }
        .tc-error-icon { color: #d97706; flex-shrink: 0; margin-top: .1rem; }
        .tc-error-title { font-size: .85rem; font-weight: 700; color: #92400e; margin: 0 0 .2rem; }
        .tc-error-msg { font-size: .75rem; color: #b45309; margin: 0; }
        .tc-fallback-btn {
          display: inline-flex; align-items: center; gap: .35rem;
          padding: .4rem .8rem; background: #f59e0b; color: #fff;
          border-radius: var(--radius-sm); font-size: .8rem; font-weight: 600;
          text-decoration: none; margin-left: auto; transition: background .15s;
        }
        .tc-fallback-btn:hover { background: #d97706; }
        .tc-empty {
          display: flex; flex-direction: column; align-items: center; gap: .625rem;
          padding: 3rem 1.5rem; background: var(--surface-2);
          border: 1px dashed var(--border); border-radius: var(--radius-sm); text-align: center;
        }
        .tc-empty-icon { color: var(--border-strong); }
        .tc-empty h3 { font-size: .9rem; font-weight: 700; color: var(--text-muted); margin: 0; }
        .tc-empty p { font-size: .82rem; color: var(--text-light); margin: 0; line-height: 1.7; }

        /* 인트로 */
        .tc-intro { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
        @media (max-width: 640px) { .tc-intro { grid-template-columns: 1fr; } }
        .tc-intro-card {
          display: flex; flex-direction: column; gap: .5rem;
          padding: 1.25rem; background: var(--surface-2);
          border: 1px solid var(--border); border-radius: var(--radius-sm);
        }
        .tc-intro-icon { color: var(--primary); }
        .tc-intro-card h3 { font-size: .875rem; font-weight: 700; color: var(--text); margin: 0; }
        .tc-intro-card p { font-size: .78rem; color: var(--text-muted); margin: 0; line-height: 1.65; }

        /* 외부 링크 */
        .tc-ext-link-row { display: flex; justify-content: center; padding-top: .5rem; }
        .tc-ext-link {
          display: inline-flex; align-items: center; gap: .35rem;
          font-size: .8rem; color: var(--primary); text-decoration: none;
          padding: .375rem .875rem; border: 1px solid var(--primary);
          border-radius: var(--radius-sm); transition: background .15s;
        }
        .tc-ext-link:hover { background: var(--primary-light); }

        /* 정보 섹션 (과정평가형/일학습병행) */
        .tc-info-section { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
        @media (max-width: 640px) { .tc-info-section { grid-template-columns: 1fr; } }
        .tc-info-card {
          display: flex; flex-direction: column; gap: .875rem;
          padding: 1.5rem; background: var(--surface-2);
          border: 1px solid var(--border); border-radius: var(--radius-sm);
        }
        .tc-info-icon-wrap { display: flex; }
        .tc-info-icon { color: var(--primary); }
        .tc-info-title { font-size: 1.1rem; font-weight: 800; color: var(--text); margin: 0; }
        .tc-info-desc { font-size: .83rem; color: var(--text-muted); margin: 0; line-height: 1.7; }
        .tc-info-tags { display: flex; gap: .375rem; flex-wrap: wrap; }
        .tc-info-tag {
          font-size: .72rem; font-weight: 600; padding: .2rem .55rem;
          border-radius: 99px;
        }
        .tc-tag-green { background: #ecfdf5; color: #059669; }
        .tc-tag-blue { background: #eff6ff; color: #2563eb; }
        .tc-tag-purple { background: #f5f3ff; color: #7c3aed; }
        .tc-tag-orange { background: #fffbeb; color: #d97706; }
        .tc-info-btn {
          display: inline-flex; align-items: center; gap: .4rem;
          padding: .55rem 1.1rem; background: var(--primary); color: #fff;
          border-radius: var(--radius-sm); font-size: .85rem; font-weight: 600;
          text-decoration: none; width: fit-content; transition: background .15s;
          margin-top: auto;
        }
        .tc-info-btn:hover { background: #1d4ed8; }

        /* 절차 스텝 */
        .tc-info-steps {
          display: flex; flex-direction: column; gap: .75rem;
          padding: 1.25rem; background: var(--surface-2);
          border: 1px solid var(--border); border-radius: var(--radius-sm);
        }
        .tc-info-steps-title { font-size: .85rem; font-weight: 800; color: var(--text); margin: 0 0 .5rem; }
        .tc-step-item { display: flex; gap: .75rem; align-items: flex-start; }
        .tc-step-num {
          flex-shrink: 0; width: 24px; height: 24px;
          background: var(--primary); color: #fff;
          border-radius: 50%; display: flex; align-items: center; justify-content: center;
          font-size: .72rem; font-weight: 700;
        }
        .tc-step-body { display: flex; flex-direction: column; gap: .15rem; }
        .tc-step-label { font-size: .83rem; font-weight: 700; color: var(--text); }
        .tc-step-desc { font-size: .75rem; color: var(--text-muted); line-height: 1.55; }

        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default Training;
