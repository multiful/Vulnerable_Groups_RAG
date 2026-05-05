import React, { useRef, useEffect } from 'react';
import { Outlet, Link, useLocation, useSearchParams } from 'react-router-dom';
import { Home, ShieldAlert, Award, Map } from 'lucide-react';

const NAV_ITEMS = [
  { icon: <Home size={20} />, label: '홈', path: '/' },
  { icon: <ShieldAlert size={20} />, label: '위험군 진단', path: '/risk-assessment' },
  { icon: <Award size={20} />, label: '자격증 추천', path: '/recommendation' },
  { icon: <Map size={20} />, label: '성장 로드맵', path: '/roadmap' },
];

const FLOW_STEPS = [
  { path: '/risk-assessment', label: '위험군 진단', step: 1 },
  { path: '/recommendation', label: '자격증 추천', step: 2 },
  { path: '/roadmap', label: '성장 로드맵', step: 3 },
];

function StepIndicator({ pathname }: { pathname: string }) {
  const [searchParams] = useSearchParams();
  const stageParam = searchParams.get('stage');
  const certParam = searchParams.get('cert');

  const currentIdx = FLOW_STEPS.findIndex(s => pathname.startsWith(s.path));
  if (currentIdx === -1) return null;

  const isDone = (stepIdx: number): boolean => {
    if (stepIdx === 0) return currentIdx > 0 && !!stageParam;
    if (stepIdx === 1) return currentIdx > 1 && !!certParam;
    return false;
  };

  return (
    <div className="step-bar container">
      <div className="step-bar-inner">
        {FLOW_STEPS.map((s, idx) => (
          <React.Fragment key={s.path}>
            <div className={`step-item ${idx === currentIdx ? 'active' : ''} ${isDone(idx) ? 'done' : ''}`}>
              <div className="step-dot">
                {isDone(idx) ? '✓' : idx + 1}
              </div>
              <span className="step-label">{s.label}</span>
            </div>
            {idx < FLOW_STEPS.length - 1 && (
              <div className={`step-connector ${isDone(idx) ? 'done' : ''}`} />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

const MainLayout: React.FC = () => {
  const location = useLocation();
  const mainRef = useRef<HTMLElement>(null);

  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);

  useEffect(() => {
    window.scrollTo(0, 0);
    mainRef.current?.focus();
  }, [location.pathname]);

  return (
    <div className="app-root">
      {/* Header */}
      <header className="app-header">
        <div className="container header-inner">
          <Link to="/" className="logo">
            <span className="logo-mark-icon">C</span>
            <span className="logo-text">청로드</span>
            <span className="logo-en">CheongRoad</span>
          </Link>
          <nav className="header-nav">
            {NAV_ITEMS.slice(1).map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={`header-nav-link ${isActive(item.path) ? 'active' : ''}`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <Link to="/risk-assessment" className="btn-primary header-cta">
            시작하기
          </Link>
        </div>
      </header>

      {/* Flow step indicator */}
      <StepIndicator pathname={location.pathname} />

      {/* Body */}
      <div className="app-body container">
        <aside className="sidebar">
          <nav className="sidebar-nav">
            {NAV_ITEMS.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={`sidebar-link ${isActive(item.path) ? 'active' : ''}`}
              >
                {item.icon}
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>
        </aside>

        <main className="main-content" ref={mainRef} tabIndex={-1}>
          <Outlet />
        </main>
      </div>

      {/* Mobile bottom nav */}
      <nav className="mobile-nav">
        {NAV_ITEMS.map(item => (
          <Link
            key={item.path}
            to={item.path}
            className={`mobile-nav-item ${isActive(item.path) ? 'active' : ''}`}
          >
            {item.icon}
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <style>{`
        .app-root {
          display: flex;
          flex-direction: column;
          min-height: 100vh;
          padding-bottom: var(--mobile-nav-h);
        }
        @media (min-width: 769px) {
          .app-root { padding-bottom: 0; }
        }

        /* ── Header ── */
        .app-header {
          position: sticky;
          top: 0;
          z-index: 100;
          height: var(--header-h);
          background: rgba(255, 255, 255, 0.94);
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
          border-bottom: 1px solid var(--border-strong);
          box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
        }
        .header-inner {
          height: 100%;
          display: flex;
          align-items: center;
          gap: 2rem;
        }
        .logo {
          flex-shrink: 0;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          text-decoration: none;
        }
        .logo-mark-icon {
          width: 28px;
          height: 28px;
          border-radius: 7px;
          background: var(--gradient-primary);
          color: #fff;
          font-size: 0.9rem;
          font-weight: 800;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 8px var(--primary-glow);
          flex-shrink: 0;
        }
        .logo-text {
          font-size: 1.1rem;
          font-weight: 800;
          letter-spacing: -0.03em;
          background: var(--gradient-primary);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .logo-en {
          font-size: 0.7rem;
          font-weight: 500;
          color: var(--text-light);
          letter-spacing: 0.03em;
        }
        @media (max-width: 480px) {
          .logo-en { display: none; }
        }
        .header-nav {
          display: flex;
          gap: 0.25rem;
          flex: 1;
        }
        .header-nav-link {
          padding: 0.4rem 0.75rem;
          border-radius: var(--radius-sm);
          font-size: 0.9rem;
          font-weight: 500;
          color: var(--text-muted);
          transition: var(--transition);
        }
        .header-nav-link:hover { color: var(--text); background: var(--surface-2); }
        .header-nav-link.active { color: var(--primary); background: var(--primary-light); font-weight: 600; }
        .header-cta { font-size: 0.875rem; padding: 0.5rem 1rem; }

        @media (max-width: 768px) {
          .header-nav { display: none; }
          .header-cta { display: none; }
        }

        /* ── Step indicator ── */
        .step-bar {
          padding: 0.875rem 1.5rem;
          border-bottom: 1px solid var(--border);
          background: var(--surface);
        }
        .step-bar-inner {
          display: flex;
          align-items: center;
          gap: 0;
          max-width: 480px;
        }
        .step-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.25rem;
          flex-shrink: 0;
        }
        .step-dot {
          width: 28px;
          height: 28px;
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
        }
        .step-item.done .step-dot {
          border-color: var(--success);
          background: var(--success);
          color: #fff;
        }
        .step-label {
          font-size: 0.7rem;
          font-weight: 500;
          color: var(--text-light);
          white-space: nowrap;
        }
        .step-item.active .step-label { color: var(--primary); font-weight: 700; }
        .step-item.done .step-label { color: var(--success); }
        .step-connector {
          flex: 1;
          height: 2px;
          background: var(--border);
          margin: 0 0.375rem;
          margin-bottom: 14px;
          transition: background 0.4s ease;
          border-radius: 2px;
        }
        .step-connector.done {
          background: linear-gradient(90deg, var(--success), var(--primary));
        }

        /* ── Sidebar ── */
        .app-body {
          display: grid;
          grid-template-columns: var(--sidebar-w) 1fr;
          gap: 2rem;
          flex: 1;
          padding-top: 1.5rem;
          padding-bottom: 2rem;
          align-items: start;
        }
        .sidebar {
          position: sticky;
          top: calc(var(--header-h) + 1rem);
          background: rgba(255, 255, 255, 0.72);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1px solid rgba(255, 255, 255, 0.85);
          border-radius: var(--radius);
          padding: 0.5rem;
          box-shadow: var(--shadow-sm);
        }
        .sidebar-nav {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .sidebar-link {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.625rem 0.875rem;
          border-radius: var(--radius-sm);
          color: var(--text-muted);
          font-size: 0.9rem;
          font-weight: 500;
          transition: var(--transition);
        }
        .sidebar-link:hover { background: var(--surface-2); color: var(--text); }
        .sidebar-link.active {
          background: linear-gradient(135deg, var(--primary-light), rgba(14,165,233,0.08));
          color: var(--primary);
          font-weight: 600;
          box-shadow: inset 0 0 0 1px rgba(99,102,241,0.15);
        }

        @media (max-width: 768px) {
          .app-body { grid-template-columns: 1fr; }
          .sidebar { display: none; }
        }

        /* ── Main content ── */
        .main-content {
          min-width: 0;
          outline: none;
        }
        .main-content:focus-visible {
          outline: 2px solid var(--primary);
          outline-offset: 2px;
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
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border-top: 1px solid var(--border);
          z-index: 100;
        }
        @media (max-width: 768px) {
          .mobile-nav { display: flex; }
        }
        .mobile-nav-item {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 3px;
          color: var(--text-light);
          font-size: 0.65rem;
          font-weight: 500;
          transition: var(--transition);
        }
        .mobile-nav-item.active { color: var(--primary); }
        .mobile-nav-item span { line-height: 1; }
      `}</style>
    </div>
  );
};

export default MainLayout;
          left: 0;
          right: 0;
          height: var(--mobile-nav-h);
          background: rgba(255,255,255,0.96);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border-top: 1px solid var(--border);
          z-index: 100;
        }
        @media (max-width: 768px) {
          .mobile-nav { display: flex; }
        }
        .mobile-nav-item {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 3px;
          color: var(--text-light);
          font-size: 0.65rem;
          font-weight: 500;
          transition: var(--transition);
        }
        .mobile-nav-item.active { color: var(--primary); }
        .mobile-nav-item span { line-height: 1; }
      `}</style>
    </div>
  );
};

export default MainLayout;
