import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Info, CheckCircle2 } from 'lucide-react';

const RISK_STAGES = [
  {
    id: '1', label: '1단계', sublabel: '취업 안정권',
    desc: '취업 준비가 비교적 안정적으로 진행 중인 상태입니다.',
    hint: '기사·기술사 등 높은 등급의 자격증도 동등한 후보로 추천됩니다.',
    barClass: 'bar-green', hintClass: 'hint-green',
  },
  {
    id: '2', label: '2단계', sublabel: '준비 활성',
    desc: '취업을 위한 준비 활동이 활발하게 진행되는 상태입니다.',
    hint: '직무 매칭 기반 추천이 강화됩니다.',
    barClass: 'bar-sky', hintClass: 'hint-sky',
  },
  {
    id: '3', label: '3단계', sublabel: '준비 정체',
    desc: '방향은 있지만 구체적인 행동이 잘 이어지지 않는 상태입니다.',
    hint: '단계형 로드맵이 강조되어 다음 한 걸음을 명확히 제시합니다.',
    barClass: 'bar-indigo', hintClass: 'hint-indigo',
  },
  {
    id: '4', label: '4단계', sublabel: '관계망 약화',
    desc: '관계망이 줄고 일상 유지에 어려움이 있는 상태입니다.',
    hint: '낮은 등급의 자격증을 우선 추천하여 단기 성취를 지원합니다.',
    barClass: 'bar-amber', hintClass: 'hint-amber',
  },
  {
    id: '5', label: '5단계', sublabel: '고위험군',
    desc: '취업을 원하지만 현실적 장벽이 가장 높은 상태입니다.',
    hint: '기능사·국가기술자격 등 단기 달성 가능한 자격증을 우선 추천합니다.',
    barClass: 'bar-red', hintClass: 'hint-red',
  },
] as const;

const RiskAssessment: React.FC = () => {
  const navigate  = useNavigate();
  const [selected, setSelected] = useState<string>('');

  const handleNext = () => {
    if (!selected) return;
    navigate(`/recommendation?stage=${selected}`);
  };

  const selectedStage = RISK_STAGES.find(s => s.id === selected);

  return (
    <div className="risk-wrap">
      <div className="page-header">
        <h1 className="page-title">위험군 진단</h1>
        <p className="page-desc">현재 상황에 가장 가까운 단계를 선택하세요. 단계에 따라 추천 자격증 등급과 로드맵 구조가 달라집니다.</p>
      </div>

      <div className="card risk-card">
        <div className="info-banner">
          <Info size={15} />
          <span>1단계(안정권) → 5단계(고위험군) 순으로 위험도가 높아집니다.</span>
        </div>

        <div className="stages-list">
          {RISK_STAGES.map(stage => {
            const isSel = selected === stage.id;
            return (
              <button
                key={stage.id}
                className={`stage-btn ${isSel ? 'selected' : ''}`}
                onClick={() => setSelected(stage.id)}
                type="button"
              >
                <div className={`stage-bar ${stage.barClass}`} />
                <div className="stage-text">
                  <div className="stage-labels">
                    <span className="stage-num">{stage.label}</span>
                    <span className="stage-sub">{stage.sublabel}</span>
                  </div>
                  <p className="stage-desc">{stage.desc}</p>
                  {isSel && (
                    <p className={`stage-hint ${stage.hintClass}`}>
                      <CheckCircle2 size={12} />
                      {stage.hint}
                    </p>
                  )}
                </div>
                <div className={`stage-check ${isSel ? 'visible' : ''}`}>&#10003;</div>
              </button>
            );
          })}
        </div>

        {selectedStage && (
          <div className="selected-summary">
            <span className="summary-label">선택됨</span>
            <span className="summary-text">
              <strong>{selectedStage.label} · {selectedStage.sublabel}</strong>에 적합한 자격증 목록을 안내합니다.
            </span>
          </div>
        )}

        <div className="risk-actions">
          <button className="btn-primary" disabled={!selected} onClick={handleNext}>
            자격증 추천 보기 <ArrowRight size={17} />
          </button>
        </div>
      </div>

      <style>{`
        .risk-wrap { max-width:680px; display:flex; flex-direction:column; gap:1.5rem; }
        .risk-card { padding:1.75rem; display:flex; flex-direction:column; gap:1.25rem; }
        .info-banner {
          display:flex; align-items:center; gap:.625rem;
          padding:.7rem 1rem; background:var(--primary-light);
          border-radius:var(--radius-sm); color:var(--primary);
          font-size:.85rem; font-weight:500;
          border:1px solid rgba(99,102,241,.18);
        }
        .stages-list { display:flex; flex-direction:column; gap:.5rem; }
        .stage-btn {
          display:flex; align-items:flex-start; gap:1rem;
          padding:1rem 1.125rem; border-radius:var(--radius-sm);
          border:1.5px solid var(--border); background:var(--surface);
          text-align:left; transition:var(--transition); width:100%; cursor:pointer;
        }
        .stage-btn:hover { border-color:var(--border-strong); background:var(--surface-2); transform:translateX(2px); }
        .stage-btn.selected {
          border-color:var(--primary);
          background:linear-gradient(135deg,var(--primary-light),rgba(14,165,233,.06));
          box-shadow:0 4px 18px var(--primary-glow); transform:translateX(0);
        }
        .stage-bar { width:5px; min-height:44px; border-radius:3px; flex-shrink:0; margin-top:2px; }
        .bar-green  { background:#10b981; }
        .bar-sky    { background:#0ea5e9; }
        .bar-indigo { background:#6366f1; }
        .bar-amber  { background:#f59e0b; }
        .bar-red    { background:#f43f5e; }
        .stage-text  { flex:1; display:flex; flex-direction:column; gap:.25rem; }
        .stage-labels{ display:flex; align-items:baseline; gap:.5rem; flex-wrap:wrap; }
        .stage-num   { font-size:.78rem; font-weight:700; color:var(--text-light); }
        .stage-btn.selected .stage-num { color:var(--primary); }
        .stage-sub   { font-size:.975rem; font-weight:700; color:var(--text); }
        .stage-desc  { font-size:.845rem; color:var(--text-muted); line-height:1.5; }
        .stage-hint  {
          display:flex; align-items:center; gap:.35rem;
          font-size:.8rem; font-weight:500; margin-top:.35rem;
          padding:.3rem .6rem; border-radius:var(--radius-xs);
          width:fit-content; animation:hint-in .18s ease;
        }
        @keyframes hint-in { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:none} }
        .hint-green  { background:#d1fae5; color:#065f46; }
        .hint-sky    { background:var(--secondary-light); color:#0369a1; }
        .hint-indigo { background:var(--primary-light); color:var(--primary-dark); }
        .hint-amber  { background:var(--warning-light); color:#92400e; }
        .hint-red    { background:var(--danger-light); color:#9f1239; }
        .stage-check {
          width:20px; height:20px; border-radius:50%;
          background:var(--primary); color:#fff;
          font-size:.7rem; font-weight:700;
          display:flex; align-items:center; justify-content:center;
          opacity:0; transition:opacity .15s,transform .15s;
          flex-shrink:0; transform:scale(.7); margin-top:3px;
        }
        .stage-check.visible { opacity:1; transform:scale(1); }
        .selected-summary {
          display:flex; align-items:center; gap:.75rem;
          padding:.75rem 1rem; background:var(--surface-2);
          border-radius:var(--radius-sm); border:1px solid var(--border);
          animation:hint-in .2s ease;
        }
        .summary-label {
          font-size:.72rem; font-weight:700; letter-spacing:.06em;
          color:var(--primary); background:var(--primary-light);
          padding:.15rem .5rem; border-radius:var(--radius-xs); white-space:nowrap;
        }
        .summary-text { font-size:.85rem; color:var(--text-muted); line-height:1.4; }
        .summary-text strong { color:var(--text); }
        .risk-actions {
          display:flex; justify-content:flex-end;
          padding-top:.75rem; border-top:1px solid var(--border);
        }
      `}</style>
    </div>
  );
};

export default RiskAssessment;
