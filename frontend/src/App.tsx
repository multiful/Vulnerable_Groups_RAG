import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import { ErrorBoundary } from './components/ErrorBoundary';
// Core user flow — eager, these pages appear first
import Home from './pages/Home';
import RiskAssessment from './pages/RiskAssessment';
import InterestSelection from './pages/InterestSelection';
import Privacy from './pages/Privacy';
import Contact from './pages/Contact';
import NotFound from './pages/NotFound';
// Heavy routes — lazy-loaded to reduce initial bundle
const Roadmap           = lazy(() => import('./pages/Roadmap'));
const Recommendation    = lazy(() => import('./pages/Recommendation'));
const AllCerts          = lazy(() => import('./pages/AllCerts'));
const Schedule          = lazy(() => import('./pages/Schedule'));
const Explore           = lazy(() => import('./pages/Explore'));
const Training          = lazy(() => import('./pages/Training'));
const Jobs              = lazy(() => import('./pages/Jobs'));
const IsolationDashboard = lazy(() => import('./pages/IsolationDashboard'));

const PageFallback = () => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '40vh', color: 'var(--text-muted)', fontSize: '.9rem' }}>
    로딩 중…
  </div>
);

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Home />} />
              <Route path="risk-assessment" element={<RiskAssessment />} />
              <Route path="interests" element={<InterestSelection />} />
              <Route path="roadmap" element={<Roadmap />} />
              <Route path="recommendation" element={<Recommendation />} />
              <Route path="certs" element={<AllCerts />} />
              <Route path="schedule" element={<Schedule />} />
              <Route path="explore" element={<Explore />} />
              <Route path="training" element={<Training />} />
              <Route path="jobs" element={<Jobs />} />
              <Route path="privacy" element={<Privacy />} />
              <Route path="contact" element={<Contact />} />
              <Route path="isolation/dashboard" element={<IsolationDashboard />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </BrowserRouter>
  );
};

export default App;
