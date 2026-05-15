import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import { ErrorBoundary } from './components/ErrorBoundary';
import Home from './pages/Home';
import RiskAssessment from './pages/RiskAssessment';
import InterestSelection from './pages/InterestSelection';
import Roadmap from './pages/Roadmap';
import Recommendation from './pages/Recommendation';
import AllCerts from './pages/AllCerts';
import Schedule from './pages/Schedule';
import Explore from './pages/Explore';
import Jobs from './pages/Jobs';
import Privacy from './pages/Privacy';
import Contact from './pages/Contact';
import NotFound from './pages/NotFound';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ErrorBoundary>
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
            <Route path="jobs" element={<Jobs />} />
            <Route path="privacy" element={<Privacy />} />
            <Route path="contact" element={<Contact />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
};

export default App;
