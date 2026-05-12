// Content Hash: SHA256:TBD
import React, { useRef, useEffect } from 'react';
import { Outlet, Link, useLocation, useSearchParams } from 'react-router-dom';
import { CheckCircle2 } from 'lucide-react';
import { loadPipeline } from '../../utils/pipelineState';

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

// 상단 네비 — 진단 흐름은 "진단 시작" CTA 통해서만 진입. 자유 탐색은 "전체 자격증".
const NAV_LINKS = [
  { label: '전체 자격증', path: '/certs' },
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
  // URL에 stage가 없어도 세션에서 복원하여 done 상태를 올바르게 표시
  const session = loadPipeline();
  const effectiveStage = stageParam || session.stage || '';
  const effectiveDomain = searchParams.get('domain') || session.domain || '';

  const currentIdx = FLOW_STEPS.findIndex(s => pathname.startsWith(s.path));
  if (currentIdx === -1) return null;

  const isDone = (idx: number) => {
    if (idx === 0) return currentIdx > 0 && !!effectiveStage;
    if (idx === 1) return currentIdx > 1 && !!effectiveDomain;
    if (idx === 2) return currentIdx > 2;
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

      {/* ── Header ── */}
      <header className="app-header">
        <div className="container header-inner">
          {/* Logo */}
          <Link to="/" className="logo">
            <img src="/logo.png?v=8" alt="디딤 로고" className="logo-img" />
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

            {/* 청년지원제도 드롭다운 탭 */}
            <div className="support-nav-wrap">
              <button type="button" className="header-nav-link support-nav-btn" aria-haspopup="true">
                청년지원제도 <span className="support-nav-arrow">▾</span>
              </button>
              <div className="support-mega-panel" role="menu">
                {SUPPORT_LINKS.map(item => (
                  <div key={item.url} className="support-mega-group">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="support-mega-title"
                      role="menuitem"
                    >
                      {item.label}
                    </a>
                    {item.subLinks.map(sub => (
                      <a
                        key={sub.url}
                        href={sub.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="support-mega-item"
                        role="menuitem"
                      >
                        {sub.label}
                      </a>
                    ))}
                  </div>
                ))}
              </div>
            </div>
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
        /* ── 청년지원제도 드롭다운 (헤더 내 탭) ── */
        .support-nav-wrap {
          position: relative;
        }
        .support-nav-btn {
          background: none;
          border: none;
          cursor: pointer;
          font-family: inherit;
          display: flex;
          align-items: center;
          gap: 0.25rem;
          color: var(--text-muted);
          transition: var(--transition);
        }
        .support-nav-btn:hover {
          color: #2563eb;
          background: #eff6ff;
        }
        .support-nav-arrow {
          font-size: 0.6rem;
          transition: transform 0.2s ease;
        }
        .support-nav-wrap:hover .support-nav-arrow {
          transform: rotate(180deg);
        }
        /* 메가 패널 */
        .support-mega-panel {
          display: none;
          position: absolute;
          top: calc(100% + 8px);
          left: 50%;
          transform: translateX(-50%);
          min-width: 640px;
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 14px;
          box-shadow: 0 12px 40px rgba(15,23,42,0.13);
          padding: 1.25rem;
          z-index: 500;
          grid-template-columns: repeat(4, 1fr);
          gap: 1rem;
        }
        .support-nav-wrap:hover .support-mega-panel {
          display: grid;
        }
        /* hover 갭 브릿지 */
        .support-mega-panel::before {
          content: '';
          position: absolute;
          top: -10px;
          left: 0; right: 0;
          height: 10px;
        }
        .support-mega-group {
          display: flex;
          flex-direction: column;
          gap: 0.15rem;
        }
        .support-mega-title {
          display: block;
          font-size: 0.8rem;
          font-weight: 700;
          color: #2563eb;
          text-decoration: none;
          padding: 0.35rem 0.6rem;
          border-radius: 6px;
          margin-bottom: 0.2rem;
          background: #eff6ff;
          white-space: nowrap;
          transition: background 0.12s;
        }
        .support-mega-title:hover {
          background: #dbeafe;
        }
        .support-mega-item {
          display: block;
          font-size: 0.76rem;
          color: #4b5563;
          text-decoration: none;
          padding: 0.3rem 0.6rem;
          border-radius: 6px;
          transition: all 0.12s ease;
          white-space: nowrap;
        }
        .support-mega-item:hover {
          background: #f0f9ff;
          color: #2563eb;
          padding-left: 0.85rem;
        }
        @media (max-width: 768px) {
          .support-nav-wrap { display: none; }
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
          background: var(--primary);
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
