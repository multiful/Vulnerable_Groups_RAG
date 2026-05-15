// Content Hash: SHA256:TBD
import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, FileQuestion } from 'lucide-react';

const NotFound: React.FC = () => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', padding: '2rem', textAlign: 'center', gap: '1.5rem' }}>
    <style>{`
      .nf-icon{width:72px;height:72px;border-radius:var(--radius);background:var(--surface-2);display:flex;align-items:center;justify-content:center;color:var(--text-light)}
      .nf-code{font-size:3.5rem;font-weight:900;letter-spacing:-.05em;color:var(--primary);line-height:1}
      .nf-title{font-size:1.25rem;font-weight:700;color:var(--text);margin:0}
      .nf-sub{font-size:.9rem;color:var(--text-muted);max-width:320px;line-height:1.6;margin:0}
      .nf-actions{display:flex;gap:.75rem;flex-wrap:wrap;justify-content:center}
    `}</style>
    <div className="nf-icon"><FileQuestion size={36} /></div>
    <p className="nf-code">404</p>
    <p className="nf-title">페이지를 찾을 수 없습니다</p>
    <p className="nf-sub">요청하신 주소가 존재하지 않거나 이동되었습니다.</p>
    <div className="nf-actions">
      <Link to="/" className="btn-primary"><ArrowLeft size={15} /> 홈으로</Link>
      <Link to="/certs" className="btn-ghost">자격증 둘러보기</Link>
    </div>
  </div>
);

export default NotFound;
