import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import Home from './pages/Home';
import RiskAssessment from './pages/RiskAssessment';
import InterestSelection from './pages/InterestSelection';
import Roadmap from './pages/Roadmap';
import Recommendation from './pages/Recommendation';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Home />} />
          <Route path="risk-assessment" element={<RiskAssessment />} />
          <Route path="interests" element={<InterestSelection />} />
          <Route path="roadmap" element={<Roadmap />} />
          <Route path="recommendation" element={<Recommendation />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
