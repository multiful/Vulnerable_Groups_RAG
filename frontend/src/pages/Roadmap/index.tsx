import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Circle, Clock, ArrowLeft, Info, Loader2 } from 'lucide-react';

const RISK_STAGE_LABELS: Record<string, string> = {
  '1': '1단계',
  '2': '준비단계 (초기)',
  '3': '준비단계 (심화)',
  '4': '4단계',
  '5': '5단계',
};

const RISK_INTERNAL_MAP: Record<string, string> = {
  '1': 'risk_0001',
  '2': 'risk_0002',
  '3': 'risk_0003',
  '4': 'risk_0004',
  '5': 'risk_0005',
};

type StageStatus = 'completed' | 'current' | 'locked';

interface RoadmapStage {
  id: string;
  name: string;
  desc: string;
  status: StageStatus;
}

function StageIcon({ status }: { status: StageStatus }) {
  if (status === 'completed') return <CheckCircle2 size={22} className="icon-success" />;
  if (status === 'current') return <Clock size={22} className="icon-secondary" />;
  return <Circle size={22} className="icon-muted" />;
}

const Roadmap: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const certId = searchParams.get('cert') ?? 'cert_013';
  const stageParam = searchParams.get('stage') ?? '';
  
  const [stages, setStages] = useState<RoadmapStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchRoadmap() {
      try {
        setLoading(true);
        const riskId = RISK_INTERNAL_MAP[stageParam] || 'risk_0001';
        
        const response = await fetch('/api/v1/roadmaps', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ risk_stage_id: riskId })
        });
        
        if (!response.ok) throw new Error('API 호출에 실패했습니다.');
        
        const json = await response.json();
        if (json.status === 'ok' && json.data?.stages) {
          const apiStages = json.data.stages.map((s: any, idx: number) => ({
            id: s.id,
            name: s.name,
            desc: s.description,
            status: idx === 0 ? 'current' : 'locked'
          }));
          setStages(apiStages);
        } else {
          throw new Error(json.message || '데이터를 불러올 수 없습니다.');
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchRoadmap();
  }, [stageParam]);

  const riskLabel = stageParam ? (RISK_STAGE_LABELS[stageParam] ?? stageParam) : '';

  if (loading) {
    return (
      <div className="roadmap-loading">
        <Loader2 size={32} className="animate-spin" />
        <p>로드맵을 생성 중입니다...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="roadmap-error">
        <Info size={32} />
        <p>{error}</p>
        <button onClick={() => window.location.reload()} className="btn-secondary">다시 시도</button>
      </div>
    );
  }

  return (
    <div className="roadmap-wrap">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> 뒤로
        </button>
        <h1 className="page-title">성장 로드맵</h1>
        <p className="page-desc">
          {certId ? `${certId}` : '선택한 자격증'}{riskLabel ? ` · ${riskLabel}` : ''} 기준 단계별 학습 경로입니다.
        </p>
      </div>

      <div className="roadmap-notice">
        <CheckCircle2 size={14} />
        <span>진단된 {riskLabel} 상태에 맞춰 최적화된 로드맵입니다.</span>
      </div>

      <div className="card roadmap-card">
        <div className="timeline">
          {stages.map((stage, idx) => (
            <div key={stage.id} className={`tl-row ${stage.status}`}>
              {/* Left: connector */}
              <div className="tl-left">
                <StageIcon status={stage.status} />
                {idx < MOCK_STAGES.length - 1 && (
                  <div className={`tl-line ${stage.status === 'completed' ? 'done' : ''}`} />
                )}
              </div>

              {/* Right: content */}
              <div className="tl-content">
                <div className="tl-header">
                  <span className={`badge tl-badge ${stage.status === 'current' ? 'badge-secondary' : stage.status === 'completed' ? 'badge-success' : 'badge-neutral'}`}>
                    {stage.status === 'completed' ? '완료' : stage.status === 'current' ? '진행중' : '대기'}
                  </span>
                  <h3 className="tl-name">{stage.name}</h3>
                </div>
                <p className="tl-desc">{stage.desc}</p>
                {stage.status === 'current' && certId && (
                  <div className="tl-certs">
                    <span className="cert-chip cert-chip-target">★ {certId}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .roadmap-wrap {
          max-width: 680px;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }
        .back-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.375rem;
          font-size: 0.875rem;
          color: var(--text-muted);
          font-weight: 500;
          margin-bottom: 0.5rem;
          transition: var(--transition);
        }
        .back-btn:hover { color: var(--text); }

        .roadmap-notice {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.625rem 1rem;
          background: var(--warning-light);
          border-radius: var(--radius-sm);
          font-size: 0.825rem;
          color: #92400e;
          border: 1px solid rgba(245,158,11,0.25);
        }
        .roadmap-card { padding: 2rem 1.75rem; }
        .timeline { display: flex; flex-direction: column; gap: 0; }

        .tl-row {
          display: flex;
          gap: 1.25rem;
        }
        /* Left column: icon + vertical line */
        .tl-left {
          display: flex;
          flex-direction: column;
          align-items: center;
          flex-shrink: 0;
          width: 22px;
        }
        .tl-line {
          flex: 1;
          width: 2px;
          background: var(--border);
          margin: 4px 0;
          min-height: 32px;
        }
        .tl-line.done {
          background: linear-gradient(180deg, var(--success), var(--primary));
        }

        /* Right column: content */
        .tl-content {
          flex: 1;
          padding-bottom: 2rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        .tl-row:last-child .tl-content { padding-bottom: 0; }

        .tl-header {
          display: flex;
          align-items: center;
          gap: 0.625rem;
        }
        .tl-name { font-size: 1.05rem; font-weight: 700; color: var(--text); }
        .tl-row.locked .tl-name { color: var(--text-muted); }

        .tl-desc { font-size: 0.875rem; color: var(--text-muted); line-height: 1.6; }
        .tl-certs {
          display: flex;
          flex-wrap: wrap;
          gap: 0.375rem;
          margin-top: 0.25rem;
        }
        .cert-chip {
          padding: 0.2rem 0.6rem;
          border-radius: var(--radius-xs);
          border: 1px solid var(--border);
          font-size: 0.78rem;
          color: var(--text-muted);
          background: var(--surface-2);
        }
        .cert-chip-target {
          border-color: var(--primary);
          color: var(--primary);
          background: var(--primary-light);
          font-weight: 600;
        }

        /* Icon colors */
        .icon-success { color: var(--success); }
        .icon-secondary { color: var(--secondary); }
        .icon-muted { color: var(--text-light); }

        .roadmap-loading, .roadmap-error {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 300px;
          gap: 1rem;
          color: var(--text-muted);
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default Roadmap;
