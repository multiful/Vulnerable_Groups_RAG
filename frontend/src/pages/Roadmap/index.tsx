import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  CheckCircle2, Clock, ArrowLeft, Info,
  Loader2, Lock, ArrowRight, AlertTriangle,
} from 'lucide-react';

const RISK_STAGE_LABELS: Record<string, string> = {
  '1': '1단계 · 취업 안정권',
  '2': '2단계 · 준비 활성',
  '3': '3단계 · 준비 정체',
  '4': '4단계 · 관계망 약화',
  '5': '5단계 · 고위험군',
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
  order: number;
  is_starting_point?: boolean;
}

function StageIcon({ status }: { status: StageStatus }) {
  if (status === 'completed') return <CheckCircle2 size={20} className="icon-success" />;
  if (status === 'current')   return <Clock size={20} className="icon-current" />;
  return <Lock size={18} className="icon-muted" />;
}

function stageBadge(status: StageStatus) {
  if (status === 'completed') return { cls: 'badge-success',   label: '완료' };
  if (status === 'current')   return { cls: 'badge-secondary', label: '시작점' };
  return { cls: 'badge-neutral', label: '대기' };
}

const Roadmap: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const certId    = searchParams.get('cert')  ?? '';
  const stageParam = searchParams.get('stage') ?? '';

  const [stages, setStages] = useState<RoadmapStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchRoadmap() {
      try {
        setLoading(true);
        setError(null);
        const riskId = RISK_INTERNAL_MAP[stageParam] || 'risk_0001';

        const response = await fetch('/api/v1/roadmaps', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ risk_stage_id: riskId }),
        });

        if (!response.ok) {
          throw new Error(`서버 오류 (${response.status})`);
        }

        const json = await response.json();
        if (cancelled) return;

        if (json.success === true && Array.isArray(json.data?.stages)) {
          const mapped: RoadmapStage[] = json.data.stages.map((s: any, idx: number) => ({
            id:               s.id,
            name:             s.name,
            desc:             s.description || '',
            order:            s.order ?? idx + 1,
            is_starting_point: s.is_starting_point ?? idx === 0,
            // First item = current starting point, rest = locked ahead
            status:           (idx === 0 ? 'current' : 'locked') as StageStatus,
          }));
          setStages(mapped);
        } else {
          throw new Error(json.message || '데이터를 불러올 수 없습니다.');
        }
      } catch (err: any) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchRoadmap();
    return () => { cancelled = true; };
  }, [stageParam]);

  const riskLabel = stageParam ? (RISK_STAGE_LABELS[stageParam] ?? stageParam) : '';

  /* ── Loading ─────────────────────────────────────── */
  if (loading) {
    return (
      <div className="rm-state">
        <div className="rm-spinner">
          <Loader2 size={28} className="spin-icon" />
        </div>
        <p className="rm-state-title">로드맵을 불러오는 중…</p>
        <p className="rm-state-sub">잠시만 기다려 주세요</p>
      </div>
    );
  }

  /* ── Error ───────────────────────────────────────── */
  if (error) {
    return (
      <div className="rm-state rm-error-state">
        <div className="rm-error-icon"><AlertTriangle size={28} /></div>
        <p className="rm-state-title">로드맵을 불러올 수 없습니다</p>
        <p className="rm-state-sub">{error}</p>
        <div className="rm-error-actions">
          <button className="btn-ghost" onClick={() => navigate(-1)}>
            <ArrowLeft size={14} /> 뒤로
          </button>
          <button className="btn-primary" onClick={() => window.location.reload()}>
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  /* ── Empty ───────────────────────────────────────── */
  if (stages.length === 0) {
    return (
      <div className="rm-state">
        <div className="rm-error-icon"><Info size={28} /></div>
        <p className="rm-state-title">로드맵 데이터가 없습니다</p>
        <p className="rm-state-sub">해당 위험군에 대한 로드맵 데이터가 준비되지 않았습니다.</p>
        <button className="btn-ghost" onClick={() => navigate(-1)}>
          <ArrowLeft size={14} /> 뒤로가기
        </button>
      </div>
    );
  }

  /* ── Main ────────────────────────────────────────── */
  const currentStage = stages.find(s => s.status === 'current');

  return (
    <div className="rm-wrap">

      {/* ── Header ── */}
      <div className="rm-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} /> 뒤로
        </button>
        <div className="rm-title-row">
          <h1 className="page-title">성장 로드맵</h1>
          {riskLabel && <span className="rm-stage-chip">{riskLabel}</span>}
        </div>
        {certId && (
          <p className="page-desc">
            <span className="cert-highlight">★ {certId}</span> 기준 단계별 학습 경로입니다.
          </p>
        )}
      </div>

      {/* ── Notice ── */}
      {currentStage && (
        <div className="rm-notice">
          <ArrowRight size={13} />
          <span>
            현재 위치: <strong>{currentStage.name}</strong>에서 시작하는 경로입니다.
            위로 올라갈수록 더 높은 등급의 자격증에 도전합니다.
          </span>
        </div>
      )}

      {/* ── Timeline ── */}
      <div className="card rm-card">
        <div className="rm-legend">
          <span className="legend-item"><span className="legend-dot dot-current" />시작점</span>
          <span className="legend-item"><span className="legend-dot dot-locked" />이후 단계</span>
        </div>

        <div className="timeline">
          {stages.map((stage, idx) => {
            const badge = stageBadge(stage.status);
            const isLast = idx === stages.length - 1;
            return (
              <div key={stage.id} className={`tl-row tl-${stage.status}`}>
                {/* Left: icon + connector */}
                <div className="tl-left">
                  <div className={`tl-icon-wrap tl-icon-${stage.status}`}>
                    <StageIcon status={stage.status} />
                  </div>
                  {!isLast && (
                    <div className={`tl-line ${stage.status === 'completed' ? 'tl-line-done' : ''}`} />
                  )}
                </div>

                {/* Right: content */}
                <div className="tl-body">
                  <div className="tl-top">
                    <div className="tl-top-row">
                      <span className="tl-order">STEP {stage.order}</span>
                      <span className={`badge ${badge.cls}`}>{badge.label}</span>
                    </div>
                    <h3 className="tl-name">{stage.name}</h3>
                  </div>
                  {stage.desc && <p className="tl-desc">{stage.desc}</p>}

                  {stage.status === 'current' && certId && (
                    <div className="tl-cert-row">
                      <span className="cert-chip cert-chip-star">★ {certId}</span>
                      <span className="cert-chip-hint">지금 이 단계에서 도전 가능</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Footer actions ── */}
      <div className="rm-footer">
        <button className="btn-ghost" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} /> 자격증 목록으로
        </button>
        {!stageParam && (
          <button className="btn-primary" onClick={() => navigate('/risk-assessment')}>
            위험군 진단하기 <ArrowRight size={15} />
          </button>
        )}
      </div>

      <style>{`
        .rm-wrap{max-width:700px;display:flex;flex-direction:column;gap:1.5rem}
        .rm-header{display:flex;flex-direction:column;gap:.375rem}
        .back-btn{display:inline-flex;align-items:center;gap:.35rem;font-size:.85rem;font-weight:500;color:var(--text-muted);margin-bottom:.25rem;transition:color .15s;width:fit-content}
        .back-btn:hover{color:var(--primary)}
        .rm-title-row{display:flex;align-items:center;gap:.75rem;flex-wrap:wrap}
        .rm-stage-chip{padding:.2rem .75rem;background:var(--primary-light);color:var(--primary);border-radius:var(--radius-full);font-size:.78rem;font-weight:700;border:1px solid rgba(99,102,241,.2)}
        .cert-highlight{color:var(--primary);font-weight:700}
        .rm-notice{display:flex;align-items:flex-start;gap:.5rem;padding:.75rem 1rem;background:linear-gradient(135deg,#eff6ff,#f0f9ff);border:1px solid rgba(14,165,233,.22);border-radius:var(--radius-sm);font-size:.85rem;color:#0369a1;line-height:1.5}
        .rm-notice svg{flex-shrink:0;margin-top:2px}
        .rm-notice strong{color:#0c4a6e}
        .rm-card{padding:1.75rem}
        .rm-legend{display:flex;gap:1.25rem;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px solid var(--border)}
        .legend-item{display:flex;align-items:center;gap:.4rem;font-size:.78rem;color:var(--text-muted)}
        .legend-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
        .dot-current{background:var(--secondary)}
        .dot-locked{background:var(--border-strong)}
        .timeline{display:flex;flex-direction:column}
        .tl-row{display:flex;gap:1rem}
        .tl-left{display:flex;flex-direction:column;align-items:center;flex-shrink:0;width:36px}
        .tl-icon-wrap{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;border:2px solid var(--border);background:var(--surface);transition:var(--transition);position:relative;z-index:1}
        .tl-icon-completed{border-color:var(--success);background:var(--success-light)}
        .tl-icon-current{border-color:var(--secondary);background:var(--secondary-light);box-shadow:0 0 0 4px rgba(14,165,233,.12)}
        .tl-icon-locked{opacity:.55}
        .tl-line{flex:1;width:2px;background:var(--border);margin:3px 0;min-height:28px;border-radius:2px}
        .tl-line-done{background:linear-gradient(180deg,var(--success),var(--primary))}
        .tl-body{flex:1;padding-bottom:1.75rem;display:flex;flex-direction:column;gap:.5rem;min-width:0}
        .tl-row:last-child .tl-body{padding-bottom:0}
        .tl-top{display:flex;flex-direction:column;gap:.25rem}
        .tl-top-row{display:flex;align-items:center;gap:.5rem}
        .tl-order{font-size:.68rem;font-weight:700;letter-spacing:.08em;color:var(--text-light)}
        .tl-name{font-size:1rem;font-weight:700;color:var(--text);line-height:1.3}
        .tl-locked .tl-name{color:var(--text-muted)}
        .tl-desc{font-size:.855rem;color:var(--text-muted);line-height:1.65}
        .tl-cert-row{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin-top:.25rem}
        .cert-chip{padding:.2rem .65rem;border-radius:var(--radius-xs);border:1px solid var(--border);font-size:.78rem;color:var(--text-muted);background:var(--surface-2)}
        .cert-chip-star{border-color:var(--primary);color:var(--primary);background:var(--primary-light);font-weight:700}
        .cert-chip-hint{font-size:.75rem;color:var(--text-light);font-style:italic}
        .icon-success{color:var(--success)}
        .icon-current{color:var(--secondary)}
        .icon-muted{color:var(--text-light)}
        .rm-state{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:320px;gap:.875rem;text-align:center;color:var(--text-muted);padding:2rem}
        .rm-spinner{width:56px;height:56px;border-radius:50%;background:var(--primary-light);display:flex;align-items:center;justify-content:center;color:var(--primary)}
        .spin-icon{animation:rm-spin 1s linear infinite}
        @keyframes rm-spin{to{transform:rotate(360deg)}}
        .rm-error-state{color:var(--danger)}
        .rm-error-icon{width:56px;height:56px;border-radius:50%;background:var(--danger-light);display:flex;align-items:center;justify-content:center;color:var(--danger)}
        .rm-state-title{font-size:1.1rem;font-weight:700;color:var(--text)}
        .rm-state-sub{font-size:.9rem;color:var(--text-muted);max-width:360px}
        .rm-error-actions{display:flex;gap:.75rem;margin-top:.5rem;flex-wrap:wrap;justify-content:center}
        .rm-footer{display:flex;gap:.75rem;align-items:center;flex-wrap:wrap}
      `}</style>
    </div>
  );
};

export default Roadmap;
