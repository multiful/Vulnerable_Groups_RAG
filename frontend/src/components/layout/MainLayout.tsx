// Content Hash: SHA256:TBD
import React, { useRef, useEffect } from 'react';
import { Outlet, Link, useLocation, useSearchParams } from 'react-router-dom';
import { CheckCircle2 } from 'lucide-react';

const NAV_LINKS = [
  { label: '위험군 진단', path: '/risk-assessment' },
  { label: '자격증 추천', path: '/recommendation' },
  { label: '성장 로드맵', path: '/roadmap' },
];

const FLOW_STEPS = [
  { path: '/risk-assessment', label: '위험군 진단', step: 1 },
  { path: '/recommendation', label: '자격증 추천', step: 2 },
  { path: '/roadmap',        label: '성장 로드맵', step: 3 },
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

      {/* ── Header ── */}
      <header className="app-header">
        <div className="container header-inner">
          {/* Logo — text only, no icon */}
          <Link to="/" className="logo">
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
          align-items: baseline;
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
          max-width: 480px;
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
