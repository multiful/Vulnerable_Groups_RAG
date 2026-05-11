// Content Hash: SHA256:TBD
import React, { useRef, useEffect } from 'react';
import { Outlet, Link, useLocation, useSearchParams } from 'react-router-dom';
import { CheckCircle2 } from 'lucide-react';

const SUPPORT_LINKS = [
  {
    label: '청년정책',
    url: 'https://www.youthcenter.go.kr/bbs03List/48?srchParam=&curPageNum=1&srchParamEtc1=&srchParamEtc2=9&srchParamEtc3=DESC&srchParamEtc4=1',
    subLinks: [
      { label: '청년정책 목록', url: 'https://www.youthcenter.go.kr/bbs03List/48?srchParam=&curPageNum=1&srchParamEtc1=&srchParamEtc2=9&srchParamEtc3=DESC&srchParamEtc4=1' },
      { label: '정책 통합검색', url: 'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch' },
      { label: '청년정책 바로가기', url: 'https://www.youthcenter.go.kr/youthPolicy/ythPlcyLinkMain' },
      { label: '일경험 지원', url: 'https://www.youthcenter.go.kr/youthPolicy/ythPlcyOverseasMain' },
    ],
  },
  {
    label: '고용24',
    url: 'https://www.work24.go.kr',
    subLinks: [
      { label: '고용24 홈', url: 'https://www.work24.go.kr' },
      { label: '실업급여 신청', url: 'https://www.work24.go.kr/cm/c/f/1100/selecSystInfo.do?systClId=SC00000254&systId=SI00000411' },
      { label: '국민내일배움카드', url: 'https://www.work24.go.kr' },
    ],
  },
  {
    label: '국민취업지원제도',
    url: 'https://www.work24.go.kr/ua/z/z/1300/selectEmssRqutIntro.do',
    subLinks: [
      { label: '신청 소개', url: 'https://www.work24.go.kr/ua/z/z/1300/selectEmssRqutIntro.do' },
      { label: '제도 안내', url: 'https://www.work24.go.kr/cm/c/f/1100/selecSystInfo.do?systId=SI00000316&systClId=SC00000206' },
      { label: '일경험 프로그램', url: 'https://www.work24.go.kr/cm/c/f/1100/selecSystInfo.do?systId=SI00000448&systClId=SC00000115' },
    ],
  },
  {
    label: 'Q-net 자격증',
    url: 'https://www.q-net.or.kr',
    subLinks: [
      { label: '자격증 정보', url: 'https://www.q-net.or.kr/man001.do' },
      { label: '원서접수', url: 'https://www.q-net.or.kr/rcv001.do?id=rcv00103' },
      { label: '시험일정', url: 'https://www.q-net.or.kr/crf021.do?id=crf02101&scheType=03' },
    ],
  },
];

const NAV_LINKS = [
  { label: '위험군 진단', path: '/risk-assessment' },
  { label: '관심 선택',   path: '/interests' },
  { label: '성장 로드맵', path: '/roadmap' },
  { label: '자격증 확인', path: '/recommendation' },
];

const FLOW_STEPS = [
  { path: '/risk-assessment', label: '위험군 진단', step: 1 },
  { path: '/interests',       label: '관심 선택',   step: 2 },
  { path: '/roadmap',         label: '성장 로드맵', step: 3 },
  { path: '/recommendation',  label: '자격증 확인', step: 4 },
];

function StepIndicator({ pathname }: { pathname: string }) {
  const [searchParams] = useSearchParams();
  const stageParam = searchParams.get('stage');
  const certParam  = searchParams.get('cert');

  const currentIdx = FLOW_STEPS.findIndex(s => pathname.startsWith(s.path));
  if (currentIdx === -1) return null;

  const isDone = (idx: number) => {
    if (idx === 0) return currentIdx > 0 && !!stageParam;
    if (idx === 1) return currentIdx > 1 && !!certParam;
    return false;
  };

  return (
    <div className="step-bar">
      <div className="container">
        <div className="step-bar-inner">
          {FLOW_STEPS.map((s, idx) => (
            <React.Fragment key={s.path}>
              <div className={['step-item', idx === currentIdx ? 'active' : '', isDone(idx) ? 'done' : ''].filter(Boolean).join(' ')}>
                <div className="step-dot">
                  {isDone(idx) ? <CheckCircle2 size={13} /> : idx + 1}
                </div>
                <span className="step-label">{s.label}</span>
              </div>
              {idx < FLOW_STEPS.length - 1 && (
                <div className={['step-conn', isDone(idx) ? 'done' : ''].filter(Boolean).join(' ')} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

const MainLayout: React.FC = () => {
  const location = useLocation();
  const mainRef  = useRef<HTMLElement>(null);

  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
    mainRef.current?.focus();
  }, [location.pathname]);

  return (
    <div className="app-root">

      {/* ── 청년지원제도 배너 ── */}
      <div className="support-banner">
        <div className="support-banner-inner">
          <span className="support-banner-label">청년지원제도</span>
          <div className="support-banner-links">
            {SUPPORT_LINKS.map(item => (
              <div key={item.url} className="support-dropdown-wrap">
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="support-banner-link"
                >
                  {item.label} <span className="support-arrow">▾</span>
                </a>
                <div className="support-dropdown">
                  <div className="support-dropdown-title">{item.label}</div>
                  {item.subLinks.map(sub => (
                    <a
                      key={sub.url}
                      href={sub.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="support-dropdown-item"
                    >
                      {sub.label}
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Header ── */}
      <header className="app-header">
        <div className="container header-inner">
          {/* Logo */}
          <Link to="/" className="logo">
            <img src="/logo.svg" alt="디딤 로고" className="logo-img" />
            <span className="logo-text">디딤</span>
            <span className="logo-en">Didim</span>
          </Link>

          <nav className="header-nav" aria-label="주요 메뉴">
            {NAV_LINKS.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={['header-nav-link', isActive(item.path) ? 'active' : ''].filter(Boolean).join(' ')}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <Link to="/risk-assessment" className="btn-primary header-cta">
            진단 시작
          </Link>
        </div>
      </header>

      {/* ── Flow step indicator ── */}
      <StepIndicator pathname={location.pathname} />

      {/* ── Body — full width, no sidebar ── */}
      <div className="app-body container">
        <main className="main-content" ref={mainRef} tabIndex={-1}>
          <Outlet />
        </main>
      </div>

      {/* ── Mobile bottom nav ── */}
      <nav className="mobile-nav" aria-label="하단 메뉴">
        {[{ label: '홈', path: '/' }, ...NAV_LINKS].map(item => (
          <Link
            key={item.path}
            to={item.path}
            className={['mobile-nav-item', isActive(item.path) ? 'active' : ''].filter(Boolean).join(' ')}
          >
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <style>{`
        /* ── 청년지원제도 배너 ── */
        .support-banner {
          background: linear-gradient(90deg, #f0f7ff 0%, #e8f4fd 100%);
          border-bottom: 1px solid #c8e0f7;
          padding: 0.45rem 0;
          position: relative;
          z-index: 200;
        }
        .support-banner-inner {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 1.5rem;
          display: flex;
          align-items: center;
          gap: 1rem;
        }
        .support-banner-label {
          font-size: 0.72rem;
          font-weight: 700;
          color: #2563eb;
          white-space: nowrap;
          background: #dbeafe;
          padding: 0.2rem 0.6rem;
          border-radius: 99px;
          flex-shrink: 0;
        }
        .support-banner-links {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          flex-wrap: wrap;
        }
        /* 드롭다운 래퍼 */
        .support-dropdown-wrap {
          position: relative;
        }
        .support-banner-link {
          font-size: 0.75rem;
          font-weight: 500;
          color: #374151;
          text-decoration: none;
          padding: 0.2rem 0.7rem;
          border-radius: 99px;
          border: 1px solid #d1d5db;
          background: #fff;
          transition: all 0.15s ease;
          white-space: nowrap;
          display: flex;
          align-items: center;
          gap: 0.2rem;
        }
        .support-arrow {
          font-size: 0.6rem;
          color: #9ca3af;
        }
        .support-banner-link:hover {
          background: #2563eb;
          color: #fff;
          border-color: #2563eb;
        }
        .support-banner-link:hover .support-arrow {
          color: #fff;
        }
        /* 드롭다운 메뉴 */
        .support-dropdown {
          display: none;
          position: absolute;
          top: 100%;
          left: 0;
          min-width: 160px;
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          box-shadow: 0 8px 24px rgba(0,0,0,0.12);
          padding: 0.5rem 0;
          padding-top: 14px;
          margin-top: 0;
          z-index: 300;
        }
        /* 갭을 메워주는 가상 브릿지 */
        .support-dropdown::before {
          content: '';
          position: absolute;
          top: -10px;
          left: 0;
          right: 0;
          height: 10px;
        }
        .support-dropdown-wrap:hover .support-dropdown {
          display: block;
        }
        .support-dropdown-title {
          font-size: 0.7rem;
          font-weight: 700;
          color: #2563eb;
          padding: 0.4rem 1rem 0.3rem;
          border-bottom: 1px solid #f3f4f6;
          margin-bottom: 0.25rem;
        }
        .support-dropdown-item {
          display: block;
          font-size: 0.78rem;
          color: #374151;
          text-decoration: none;
          padding: 0.45rem 1rem;
          transition: all 0.12s ease;
          white-space: nowrap;
        }
        .support-dropdown-item:hover {
          background: #eff6ff;
          color: #2563eb;
          padding-left: 1.2rem;
        }
        @media (max-width: 768px) {
          .support-banner-inner { gap: 0.6rem; }
          .support-banner-links { gap: 0.2rem; }
          .support-banner-link { font-size: 0.68rem; padding: 0.15rem 0.5rem; }
        }

        /* ── Root ── */
        .app-root {
          display: flex;
          flex-direction: column;
          min-height: 100vh;
          padding-bottom: var(--mobile-nav-h);
        }
        @media (min-width: 769px) { .app-root { padding-bottom: 0; } }

        /* ── Header ── */
        .app-header {
          position: sticky;
          top: 0;
          z-index: 100;
          height: var(--header-h);
          background: rgba(255,255,255,0.93);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border-bottom: 1px solid var(--border-strong);
          box-shadow: 0 1px 6px rgba(15,23,42,0.06);
        }
        .header-inner {
          height: 100%;
          display: flex;
          align-items: center;
          gap: 2rem;
        }

        /* Logo */
        .logo {
          flex-shrink: 0;
          display: flex;
          align-items: center;
          gap: 0.45rem;
          text-decoration: none;
        }
        .logo-text {
          font-size: 1.25rem;
          font-weight: 900;
          letter-spacing: -0.04em;
          background: var(--gradient-primary);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .logo-en {
          font-size: 0.7rem;
          font-weight: 500;
          color: var(--text-light);
          letter-spacing: 0.06em;
        }
        .logo-img { width: 38px; height: 38px; border-radius: 9px; flex-shrink: 0; display: block; }
        @media (max-width: 480px) { .logo-en { display: none; } }

        /* Header nav */
        .header-nav {
          display: flex;
          gap: 0.125rem;
          flex: 1;
        }
        .header-nav-link {
          padding: 0.4rem 0.875rem;
          border-radius: var(--radius-sm);
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-muted);
          transition: var(--transition);
        }
        .header-nav-link:hover { color: var(--text); background: var(--surface-2); }
        .header-nav-link.active {
          color: var(--primary);
          background: var(--primary-light);
          font-weight: 700;
        }
        .header-cta { font-size: 0.875rem; padding: 0.5rem 1.125rem; white-space: nowrap; }
        @media (max-width: 768px) {
          .header-nav { display: none; }
          .header-cta { display: none; }
        }

        /* ── Step indicator ── */
        .step-bar {
          background: var(--surface);
          border-bottom: 1px solid var(--border);
          padding: 0.75rem 0;
        }
        .step-bar-inner {
          display: flex;
          align-items: center;
          max-width: 640px;
          margin: 0 auto;
        }
        .step-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.3rem;
          flex-shrink: 0;
        }
        .step-dot {
          width: 30px;
          height: 30px;
          border-radius: 50%;
          border: 2px solid var(--border-strong);
          background: var(--surface);
          color: var(--text-light);
          font-size: 0.75rem;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: var(--transition);
        }
        .step-item.active .step-dot {
          border-color: var(--primary);
          background: var(--primary);
          color: #fff;
          box-shadow: 0 2px 8px var(--primary-glow);
        }
        .step-item.done .step-dot {
          border-color: var(--success);
          background: var(--success);
          color: #fff;
        }
        .step-label {
          font-size: 0.68rem;
          font-weight: 500;
          color: var(--text-light);
          white-space: nowrap;
        }
        .step-item.active .step-label { color: var(--primary); font-weight: 700; }
        .step-item.done .step-label   { color: var(--success); }
        .step-conn {
          flex: 1;
          height: 2px;
          background: var(--border);
          margin: 0 0.375rem;
          margin-bottom: 16px;
          transition: background 0.4s ease;
          border-radius: 2px;
          min-width: 24px;
        }
        .step-conn.done {
          background: linear-gradient(90deg, var(--success), var(--primary));
        }

        /* ── Body (full-width, no sidebar) ── */
        .app-body {
          flex: 1;
          padding-top: 2.5rem;
          padding-bottom: 3rem;
        }

        /* ── Main content ── */
        .main-content {
          outline: none;
          animation: page-enter 0.2s ease;
        }
        @keyframes page-enter {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: none; }
        }
        .main-content:focus-visible {
          outline: 2px solid var(--primary);
          outline-offset: 3px;
          border-radius: var(--radius-sm);
        }

        /* ── Mobile bottom nav ── */
        .mobile-nav {
          display: none;
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          height: var(--mobile-nav-h);
          background: rgba(255,255,255,0.96);
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
          border-top: 1px solid var(--border);
          z-index: 100;
          box-shadow: 0 -2px 12px rgba(15,23,42,0.07);
        }
        @media (max-width: 768px) { .mobile-nav { display: flex; } }
        .mobile-nav-item {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 3px;
          color: var(--text-light);
          font-size: 0.68rem;
          font-weight: 500;
          transition: color 0.15s;
          text-decoration: none;
          padding-bottom: 2px;
        }
        .mobile-nav-item.active { color: var(--primary); font-weight: 700; }
      `}</style>
    </div>
  );
};

export default MainLayout;
