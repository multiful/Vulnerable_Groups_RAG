import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import * as amplitude from '@amplitude/unified';
import './styles/index.css';
import App from './App.tsx';

const amplitudeApiKey = import.meta.env.VITE_AMPLITUDE_API_KEY;

const funnelStepByPath: Record<string, string> = {
  '/': '01_home',
  '/risk-assessment': '02_risk_assessment',
  '/interests': '03_interest_selection',
  '/roadmap': '04_roadmap',
  '/recommendation': '05_recommendation',
  '/certs': '06_cert_exploration',
  '/jobs': '07_job_exploration',
  '/contact': '08_contact',
};

if (amplitudeApiKey) {
  amplitude.initAll(amplitudeApiKey, {
    analytics: {
      autocapture: true,
    },
    sessionReplay: {
      sampleRate: 1,
    },
  });

  const trackPageView = () => {
    const path = window.location.pathname;
    const funnelStep = funnelStepByPath[path] ?? 'other';

    amplitude.track('didim_page_viewed', {
      path,
      host: window.location.host,
      funnel_step: funnelStep,
      url: window.location.href,
      referrer: document.referrer || null,
    });

    if (funnelStep !== 'other') {
      amplitude.track('didim_funnel_step', {
        path,
        funnel_step: funnelStep,
      });
    }
  };

  amplitude.track('didim_site_loaded', {
    path: window.location.pathname,
    host: window.location.host,
  });

  trackPageView();

  const wrapHistoryMethod = (methodName: 'pushState' | 'replaceState') => {
    const original = window.history[methodName];

    window.history[methodName] = function (...args) {
      const result = original.apply(this, args);
      window.dispatchEvent(new Event('didim:navigation'));
      return result;
    };
  };

  wrapHistoryMethod('pushState');
  wrapHistoryMethod('replaceState');
  window.addEventListener('popstate', trackPageView);
  window.addEventListener('didim:navigation', trackPageView);

  window.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const clickable = target?.closest('button, a, [role="button"]');

    if (!clickable) {
      return;
    }

    amplitude.track('didim_element_clicked', {
      label: clickable.textContent?.trim().replace(/\s+/g, ' ').slice(0, 80) || null,
      tag: clickable.tagName.toLowerCase(),
      path: window.location.pathname,
      href: clickable instanceof HTMLAnchorElement ? clickable.href : null,
    });
  });

  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      amplitude.track('didim_session_hidden', {
        path: window.location.pathname,
      });
    }
  });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
