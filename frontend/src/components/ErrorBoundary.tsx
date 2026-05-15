// Content Hash: SHA256:TBD
import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props { children: React.ReactNode; }
interface State { hasError: boolean; message: string; }

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, message: '' };

  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, message: err.message || '알 수 없는 오류가 발생했습니다.' };
  }

  componentDidCatch(err: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', err, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh', padding: '2rem', gap: '1rem', textAlign: 'center' }}>
        <style>{`
          .eb-icon{color:var(--warning)}
          .eb-title{font-size:1.1rem;font-weight:700;color:var(--text);margin:0}
          .eb-msg{font-size:.85rem;color:var(--text-muted);max-width:400px;word-break:break-all;margin:0}
        `}</style>
        <AlertTriangle size={36} className="eb-icon" />
        <p className="eb-title">화면을 불러오는 중 오류가 발생했습니다</p>
        <p className="eb-msg">{this.state.message}</p>
        <button className="btn-ghost" onClick={() => window.location.reload()}>새로고침</button>
      </div>
    );
  }
}
