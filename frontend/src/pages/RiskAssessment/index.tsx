import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Info } from 'lucide-react';

// §6: 1단계=취업 안정권, 5단계=고위험 확정. 2~4단계 세부 의미는 정책 확정 전 임의 정의 금지.
const RISK_STAGES = [
  {
    id: '1',
    riskId: 'risk_stage_1',
    label: '1단계',
    sublabel: '취업 안정권',
    desc: '취업 준비가 비교적 안정적으로 진행 중입니다.',
    dotColor: '#10b981',
    bgClass: 'stage-green',
  },
  {
    id: '2',
    riskId: 'risk_stage_2',
    label: '2단계',
    sublabel: '준비단계 (초기)',
    desc: '', // TODO: 세부 기준 정책 확정 후 업데이트 (CLAUDE.md §6)
    dotColor: '#6366f1',
    bgClass: 'stage-indigo',
  },
  {
    id: '3',
    riskId: 'risk_stage_3',
    label: '3단계',
    sublabel: '준비단계 (심화)',
    desc: '', // TODO: 세부 기준 정책 확정 후 업데이트 (CLAUDE.md §6)
    dotColor: '#6366f1',
    bgClass: 'stage-indigo',
  },
  {
    id: '4',
    riskId: 'risk_stage_4',
    label: '4단계',
    sublabel: '집중 케어 단계',
    desc: '', // TODO: 세부 기준 정책 확정 후 업데이트 (CLAUDE.md §6)
    dotColor: '#f59e0b',
    bgClass: 'stage-amber',
  },
  {
    id: '5',
    riskId: 'risk_stage_5',
    label: '5단계',
    sublabel: '고위험군',
    desc: '취업을 원하지만 현실적 장벽이 높은 단계입니다.',
    dotColor: '#f43f5e',
    bgClass: 'stage-red',
  },
] as const;

const RiskAssessment: React.FC = () => {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string>('');

  const handleNext = () => {
    if (!selected) return;
    navigate(`/recommendation?stage=${selected}`);
  };

  return (
    <div className="risk-wrap">
      <div className="page-header">
        <h1 className="page-title">위험군 진단</h1>
        <p className="page-desc">현재 상황에 가장 가까운 단계를 선택해주세요.</p>
      </div>

      <div className="card risk-card">
        <div className="info-banner">
          <Info size={16} />
          <span>선택한 단계에 따라 추천 자격증의 권장 등급이 달라집니다.</span>
        </div>

        <div className="stages-list">
          {RISK_STAGES.map(stage => (
            <button
              key={stage.id}
              className={`stage-btn ${selected === stage.id ? 'selected' : ''}`}
              onClick={() => setSelected(stage.id)}
              type="button"
            >
              <div className={`stage-indicator ${stage.bgClass}`} />
              <div className="stage-text">
                <div className="stage-labels">
                  <span className="stage-num">{stage.label}</span>
                  <span className="stage-sub">{stage.sublabel}</span>
                </div>
                {stage.desc && <p className="stage-desc">{stage.desc}</p>}
              </div>
              <div className={`stage-check ${selected === stage.id ? 'visible' : ''}`}>✓</div>
            </button>
          ))}
        </div>

        <div className="risk-actions">
          <button
            className="btn-primary"
            disabled={!selected}
            onClick={handleNext}
          >
            다음 단계로 <ArrowRight size={18} />
          </button>
        </div>
      </div>

      <style>{`
        .risk-wrap {
          max-width: 680px;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }
        .risk-card {
          padding: 1.75rem;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }
        .info-banner {
          display: flex;
          align-items: center;
          gap: 0.625rem;
          padding: 0.75rem 1rem;
          background: var(--primary-light);
          border-radius: var(--radius-sm);
          color: var(--primary);
          font-size: 0.875rem;
          font-weight: 500;
        }
        .stages-list {
          display: flex;
          flex-direction: column;
          gap: 0.625rem;
        }
        .stage-btn {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1.125rem 1.25rem;
          border-radius: var(--radius-sm);
          border: 1.5px solid var(--border);
          background: var(--surface);
          text-align: left;
          transition: var(--transition);
          width: 100%;
          cursor: pointer;
        }
        .stage-btn:hover {
          border-color: var(--border-strong);
          background: var(--surface-2);
        }
        .stage-btn.selected {
          border-color: var(--primary);
          background: linear-gradient(135deg, var(--primary-light), rgba(14,165,233,0.07));
          box-shadow: 0 4px 16px var(--primary-glow);
        }
        .stage-indicator {
          width: 6px;
          height: 44px;
          border-radius: 3px;
          flex-shrink: 0;
        }
        .stage-green  { background: #10b981; }
        .stage-indigo { background: #6366f1; }
        .stage-amber  { background: #f59e0b; }
        .stage-red    { background: #f43f5e; }

        .stage-text { flex: 1; display: flex; flex-direction: column; gap: 0.2rem; }
        .stage-labels { display: flex; align-items: baseline; gap: 0.625rem; }
        .stage-num {
          font-size: 0.875rem;
          font-weight: 700;
          color: var(--text-muted);
        }
        .stage-btn.selected .stage-num { color: var(--primary); }
        .stage-sub {
          font-size: 1rem;
          font-weight: 700;
          color: var(--text);
        }
        .stage-desc {
          font-size: 0.85rem;
          color: var(--text-muted);
          line-height: 1.5;
        }
        .stage-check {
          width: 22px;
          height: 22px;
          border-radius: 50%;
          background: var(--primary);
          color: #fff;
          font-size: 0.75rem;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          opacity: 0;
          transition: opacity 0.15s;
          flex-shrink: 0;
        }
        .stage-check.visible { opacity: 1; }

        .risk-actions {
          display: flex;
          justify-content: flex-end;
          padding-top: 0.5rem;
          border-top: 1px solid var(--border);
        }
      `}</style>
    </div>
  );
};

export default RiskAssessment;
