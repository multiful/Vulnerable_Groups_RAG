// Content Hash: SHA256:TBD
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, Loader2, AlertTriangle,
  CheckCircle2, Clock, Lock, ChevronDown, ChevronUp,
  Info,
} from 'lucide-react';

/* ── Types ── */
interface RecommendedCert {
  step: number | null;
  cert_id: string;
  cert_name: string;
  cert_grade_tier: string;
  avg_pass_rate: number | null;
  is_bottleneck: boolean;
  bottleneck_note: string | null;
  is_redundant: boolean;
  achievability: string;
  related_jobs: string[];
}

interface StageInfo {
  id: string;
  name: string;
  description: string;
  order: number;
}

interface ByStageItem {
  stage: StageInfo;
  is_starting_point: boolean;
  recommended_certs: RecommendedCert[];
}

interface RoadmapData {
  roadmap_by_stage: ByStageItem[];
  roadmap_sequence: Array<{ cert_id: string; cert_name: string }>;
  fallback_used: boolean;
  fallback_note: string | null;
  starting_roadmap_stage: { name: string; id: string } | null;
  total_certs_in_roadmap: number;
}

interface ApiResponse {
  success: boolean;
  data?: RoadmapData;
  error?: { code: string; message: string };
}

/* ── Grade helpers ── */
const GRADE_LABEL: Record<string, string> = {
  '5_기능장': '기능장', '4_기술사': '기술사', '3_기사': '기사',
  '2_산업기사': '산업기사', '1_기능사': '기능사',
};
function gradeColor(tier: string): string {
  if (tier.startsWith('4') || tier.startsWith('5')) return '#6366f1';
  if (tier.startsWith('3')) return '#0ea5e9';
  if (tier.startsWith('2')) return '#10b981';
  if (tier.startsWith('1')) return '#f59e0b';
  return '#94a3b8';
}
function achievabilityLabel(a: string): string {
  return a === 'immediate' ? '바로 도전 가능' : a === 'near_term' ? '단기 목표' : '장기 목표';
}
function achievabilityColor(a: string): string {
  return a === 'immediate' ? '#10b981' : a === 'near_term' ? '#0ea5e9' : '#f59e0b';
}

const RISK_LABELS: Record<string, string> = {
  '1': '1단계 · 취업 안정권', '2': '2단계 · 준비 활성',
  '3': '3단계 · 준비 정체',   '4': '4단계 · 관계망 약화',
  '5': '5단계 · 고위험군',
};
const RISK_IDS: Record<string, string> = {
  '1': 'risk_0001', '2': 'risk_0002', '3': 'risk_0003',
  '4': 'risk_0004', '5': 'risk_0005',
};

/* ── Local fallback helpers ── */
const LOCAL_STAGES: StageInfo[] = [
  { id: 'roadmap_stage_0001', name: '진입 준비',   order: 1, description: '현재 생활 패턴과 진로 준비 수준을 점검합니다.' },
  { id: 'roadmap_stage_0002', name: '탐색 · 계획', order: 2, description: '관심 도메인 내 입문 자격증을 탐색하고 학습 계획을 세웁니다.' },
  { id: 'roadmap_stage_0003', name: '기초 취득',   order: 3, description: '기초 자격증을 취득하고 실무 기초 역량을 쌓습니다.' },
  { id: 'roadmap_stage_0004', name: '전문성 강화', order: 4, description: '중·상급 자격증으로 전문성을 높이고 취업 활동을 시작합니다.' },
  { id: 'roadmap_stage_0005', name: '전문가 도달', order: 5, description: '기술사·기능장 등 최상위 자격증으로 전문가 포지션에 도달합니다.' },
];

const STARTING_STAGE_MAP: Record<number, string> = {
  1: 'roadmap_stage_0004',
  2: 'roadmap_stage_0003',
  3: 'roadmap_stage_0002',
  4: 'roadmap_stage_0002',
  5: 'roadmap_stage_0001',
};

function extractPassRate(text: string): number | null {
  const m = text.match(/합격률:\s*([\d.]+)%/);
  return m ? parseFloat(m[1]) : null;
}

function calcAchievability(tier: string, riskNum: number): string {
  const t = parseInt(tier.charAt(0)) || 3;
  if (t <= 1) return riskNum >= 4 ? 'immediate' : 'near_term';
  if (t <= 2) return riskNum >= 3 ? 'immediate' : 'near_term';
  if (t <= 3) return riskNum <= 2 ? 'near_term' : 'long_term';
  return 'long_term';
}

interface RawCert {
  cert_id: string;
  cert_name: string;
  cert_grade_tier: string;
  primary_domain: string;
  related_domains: string[];
  related_jobs: string[];
  recommended_risk_stages: string[];
  roadmap_stages: string[];
  text_for_dense: string;
}

async function buildLocalRoadmap(riskId: string, domainId: string, riskNum: number): Promise<RoadmapData> {
  const resp = await fetch('/data/cert_candidates.json');
  const all: RawCert[] = await resp.json();

  const filtered = all.filter(c => {
    const domainOk = !domainId || (c.related_domains ?? []).includes(domainId) || c.primary_domain === domainId;
    const riskOk   = !riskId   || (c.recommended_risk_stages ?? []).includes(riskId);
    return domainOk && riskOk;
  });

  const byStage: Record<string, RawCert[]> = {};
  for (const c of filtered) {
    for (const sid of (c.roadmap_stages ?? ['roadmap_stage_0003'])) {
      if (!byStage[sid]) byStage[sid] = [];
      byStage[sid].push(c);
    }
  }

  const startingId = STARTING_STAGE_MAP[riskNum] ?? 'roadmap_stage_0003';

  const roadmap_by_stage: ByStageItem[] = LOCAL_STAGES.map(stage => {
    const certs = (byStage[stage.id] ?? []).slice(0, 6).map((c, i) => ({
      step: i + 1,
      cert_id: c.cert_id,
      cert_name: c.cert_name,
      cert_grade_tier: c.cert_grade_tier ?? '3_기사',
      avg_pass_rate: extractPassRate(c.text_for_dense ?? ''),
      is_bottleneck: false,
      bottleneck_note: null,
      is_redundant: false,
      achievability: calcAchievability(c.cert_grade_tier ?? '3_기사', riskNum),
      related_jobs: c.related_jobs ?? [],
    }));
    return {
      stage,
      is_starting_point: stage.id === startingId,
      recommended_certs: certs,
    };
  });

  const totalCerts = roadmap_by_stage.reduce((s, r) => s + r.recommended_certs.length, 0);
  const startStage = LOCAL_STAGES.find(s => s.id === startingId) ?? null;

  return {
    roadmap_by_stage,
    roadmap_sequence: roadmap_by_stage.flatMap(s =>
      s.recommended_certs.map(c => ({ cert_id: c.cert_id, cert_name: c.cert_name }))
    ),
    fallback_used: true,
    fallback_note: '백엔드 서버에 연결되지 않아 로컬 데이터로 표시합니다.',
    starting_roadmap_stage: startStage ? { id: startStage.id, name: startStage.name } : null,
    total_certs_in_roadmap: totalCerts,
  };
}

/* ── Component ── */
const Roadmap: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const stageParam  = searchParams.get('stage') ?? '';
  const domainParam = searchParams.get('domain') ?? '';
  const domainName  = searchParams.get('domainName') ?? domainParam;

  const [data, setData]       = useState<RoadmapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const riskId    = RISK_IDS[stageParam] ?? '';
  const riskNum   = parseInt(stageParam) || 0;
  const riskLabel = RISK_LABELS[stageParam] ?? '';

  const fetchRoadmap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { top_n_per_stage: 6 };
      if (riskId)    body.risk_stage_id = riskId;
      if (domainParam) body.domain_ids  = [domainParam];

      const res = await fetch('/api/v1/recommendations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const json: ApiResponse = await res.json();
      if (json.success && json.data) {
        setData(json.data);
        return;
      }
    } catch {
      /* fall through to local fallback */
    }

    /* ── Local fallback ── */
    try {
      const local = await buildLocalRoadmap(riskId, domainParam, riskNum);
      setData(local);
    } catch {
      setError('데이터를 불러오지 못했습니다. 새로고침 해주세요.');
    } finally {
      setLoading(false);
    }
  }, [riskId, domainParam, riskNum]);

  useEffect(() => { fetchRoadmap(); }, [fetchRoadmap]);

  function toggleExpand(id: string) {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  }

  function goToCert(certId: string, certName: string) {
    const p = new URLSearchParams();
    if (stageParam)  p.set('stage', stageParam);
    if (domainParam) p.set('domain', domainParam);
    if (domainName)  p.set('domainName', domainName);
    p.set('cert', certId);
    p.set('certName', certName);
    navigate(`/recommendation?${p.toString()}`);
  }

  function goToAll() {
    const p = new URLSearchParams();
    if (stageParam)  p.set('stage', stageParam);
    if (domainParam) p.set('domain', domainParam);
    if (domainName)  p.set('domainName', domainName);
    navigate(`/recommendation?${p.toString()}`);
  }

  /* ── Loading ── */
  if (loading) return (
    <div className="rm-state">
      <Loader2 size={30} className="rm-spin" />
      <p className="rm-state-title">로드맵을 구성하는 중…</p>
      <p className="rm-state-sub">위험군 단계와 관심 도메인을 분석하고 있습니다</p>
    </div>
  );

  /* ── Error ── */
  if (error || !data) return (
    <div className="rm-error-wrap">
      <div className="rm-error card">
        <AlertTriangle size={22} style={{ color: 'var(--warning)', flexShrink: 0 }} />
        <div>
          <p className="rm-error-title">로드맵을 불러오지 못했습니다</p>
          <p className="rm-error-sub">{error ?? '알 수 없는 오류'}</p>
        </div>
        <button className="btn-ghost" onClick={fetchRoadmap}>다시 시도</button>
      </div>
      <div className="rm-error-actions">
        <button className="btn-ghost" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} /> 관심 분야 다시 선택
        </button>
      </div>
    </div>
  );

  const stages     = data.roadmap_by_stage ?? [];
  const startingIdx = stages.findIndex(s => s.is_starting_point);

  return (
    <div className="rm-wrap">

      {/* Header */}
      <div className="rm-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} /> 뒤로
        </button>
        <div className="rm-title-row">
          <h1 className="page-title">성장 로드맵</h1>
          <div className="rm-chips">
            {riskLabel && <span className="rm-chip rm-chip-risk">{riskLabel}</span>}
            {domainName && <span className="rm-chip rm-chip-domain">{domainName}</span>}
          </div>
        </div>
        <p className="page-desc">
          {domainName
            ? <><strong>{domainName}</strong> 분야의 단계별 자격증 학습 경로입니다.</>
            : '단계별 자격증 학습 경로를 확인하세요.'}
        </p>
        {data.fallback_used && data.fallback_note && (
          <div className="fallback-notice">
            <Info size={13} />
            <span>{data.fallback_note}</span>
          </div>
        )}
      </div>

      {/* Stats bar */}
      <div className="rm-stats">
        <div className="rm-stat">
          <span className="rm-stat-num">{data.total_certs_in_roadmap}</span>
          <span className="rm-stat-label">전체 추천 자격증</span>
        </div>
        <div className="rm-stat-divider" />
        <div className="rm-stat">
          <span className="rm-stat-num">{stages.filter(s => s.recommended_certs.length > 0).length}</span>
          <span className="rm-stat-label">활성 단계</span>
        </div>
        <div className="rm-stat-divider" />
        <div className="rm-stat">
          <span className="rm-stat-num">{data.starting_roadmap_stage?.name ?? '-'}</span>
          <span className="rm-stat-label">시작점</span>
        </div>
      </div>

      {/* Timeline */}
      <div className="card rm-card">
        <div className="timeline">
          {stages.map((item, idx) => {
            const isStart  = item.is_starting_point;
            const isLocked = idx < startingIdx;
            const isLast   = idx === stages.length - 1;
            const status   = isLocked ? 'locked' : isStart ? 'current' : 'next';
            const certs    = item.recommended_certs;
            const PREVIEW  = 3;
            const isExp    = !!expanded[item.stage.id];
            const shown    = isExp ? certs : certs.slice(0, PREVIEW);
            const extra    = certs.length - PREVIEW;

            return (
              <div key={item.stage.id} className={`tl-row tl-${status}`}>
                {/* Icon + line */}
                <div className="tl-left">
                  <div className={`tl-icon tl-icon-${status}`}>
                    {status === 'locked'  && <Lock size={14} />}
                    {status === 'current' && <Clock size={16} />}
                    {status === 'next'    && <CheckCircle2 size={16} />}
                  </div>
                  {!isLast && <div className={`tl-line ${isStart || !isLocked ? 'tl-line-active' : ''}`} />}
                </div>

                {/* Content */}
                <div className="tl-body">
                  <div className="tl-top">
                    <div className="tl-step-row">
                      <span className="tl-step-label">STEP {item.stage.order}</span>
                      {isStart && <span className="badge badge-secondary">현재 시작점</span>}
                      {isLocked && <span className="badge badge-neutral">이전 단계</span>}
                    </div>
                    <h3 className="tl-name">{item.stage.name}</h3>
                    <p className="tl-desc">{item.stage.description}</p>
                  </div>

                  {/* Certs */}
                  {certs.length > 0 ? (
                    <div className="tl-certs">
                      <p className="tl-certs-label">추천 자격증 ({certs.length}개)</p>
                      <div className="tl-cert-list">
                        {shown.map(cert => {
                          const color  = gradeColor(cert.cert_grade_tier);
                          const aColor = achievabilityColor(cert.achievability);
                          return (
                            <button
                              key={cert.cert_id}
                              className="tl-cert-row"
                              onClick={() => goToCert(cert.cert_id, cert.cert_name)}
                              type="button"
                            >
                              <span
                                className="tl-cert-badge"
                                style={{ background: color + '18', color }}
                              >
                                {GRADE_LABEL[cert.cert_grade_tier] ?? '비기술'}
                              </span>
                              <span className="tl-cert-name">{cert.cert_name}</span>
                              <div className="tl-cert-meta">
                                {cert.avg_pass_rate !== null && (
                                  <span className={`tl-pass-rate ${cert.is_bottleneck ? 'tl-bottleneck' : ''}`}>
                                    합격률 {cert.avg_pass_rate}%
                                    {cert.is_bottleneck && ' ⚠'}
                                  </span>
                                )}
                                <span className="tl-achievability" style={{ color: aColor }}>
                                  {achievabilityLabel(cert.achievability)}
                                </span>
                              </div>
                              <ArrowRight size={13} style={{ color: 'var(--text-light)', flexShrink: 0 }} />
                            </button>
                          );
                        })}
                      </div>
                      {extra > 0 && (
                        <button className="tl-expand-btn" onClick={() => toggleExpand(item.stage.id)}>
                          {isExp
                            ? <><ChevronUp size={13} /> 접기</>
                            : <><ChevronDown size={13} /> {extra}개 더 보기</>}
                        </button>
                      )}
                    </div>
                  ) : (
                    <p className="tl-empty">이 단계에 해당하는 추천 자격증이 없습니다.</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="rm-footer">
        <button className="btn-ghost" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} /> 관심 분야 변경
        </button>
        <button className="btn-primary" onClick={goToAll}>
          전체 자격증 목록 보기 <ArrowRight size={15} />
        </button>
      </div>

      <style>{`
        .rm-wrap { max-width: 780px; display: flex; flex-direction: column; gap: 1.5rem; }

        .back-btn {
          display: inline-flex; align-items: center; gap: .35rem;
          font-size: .85rem; font-weight: 500; color: var(--text-muted);
          margin-bottom: .25rem; background: none; border: none;
          cursor: pointer; padding: 0; transition: color .15s; width: fit-content;
        }
        .back-btn:hover { color: var(--primary); }

        .rm-header { display: flex; flex-direction: column; gap: .5rem; }
        .rm-title-row { display: flex; align-items: center; gap: .75rem; flex-wrap: wrap; }
        .rm-chips { display: flex; gap: .375rem; flex-wrap: wrap; }
        .rm-chip {
          padding: .2rem .75rem; border-radius: var(--radius-full);
          font-size: .75rem; font-weight: 700; border: 1px solid;
        }
        .rm-chip-risk {
          background: var(--primary-light); color: var(--primary);
          border-color: rgba(99,102,241,.25);
        }
        .rm-chip-domain {
          background: var(--secondary-light); color: var(--secondary);
          border-color: rgba(14,165,233,.25);
        }

        .fallback-notice {
          display: flex; align-items: flex-start; gap: .5rem;
          padding: .625rem .875rem;
          background: #fffbeb; border: 1px solid rgba(245,158,11,.25);
          border-radius: var(--radius-xs);
          font-size: .8rem; color: #92400e; line-height: 1.5;
        }
        .fallback-notice svg { flex-shrink: 0; margin-top: 1px; color: #f59e0b; }

        /* Stats */
        .rm-stats {
          display: flex; align-items: center; gap: 0;
          background: var(--surface); border: 1px solid var(--border);
          border-radius: var(--radius-sm); overflow: hidden;
        }
        .rm-stat {
          flex: 1; display: flex; flex-direction: column; align-items: center;
          gap: .15rem; padding: .875rem .5rem; text-align: center;
        }
        .rm-stat-num { font-size: 1.15rem; font-weight: 800; color: var(--primary); }
        .rm-stat-label { font-size: .72rem; color: var(--text-light); white-space: nowrap; }
        .rm-stat-divider { width: 1px; height: 36px; background: var(--border); flex-shrink: 0; }

        /* Timeline */
        .rm-card { padding: 1.75rem; }
        .timeline { display: flex; flex-direction: column; }
        .tl-row { display: flex; gap: 1rem; }
        .tl-left {
          display: flex; flex-direction: column; align-items: center;
          flex-shrink: 0; width: 36px;
        }
        .tl-icon {
          width: 36px; height: 36px; border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          border: 2px solid var(--border); background: var(--surface);
          color: var(--text-light); flex-shrink: 0; position: relative; z-index: 1;
        }
        .tl-icon-current {
          border-color: var(--secondary); background: var(--secondary-light);
          color: var(--secondary); box-shadow: 0 0 0 4px rgba(14,165,233,.12);
        }
        .tl-icon-next {
          border-color: var(--success); background: var(--success-light);
          color: var(--success);
        }
        .tl-icon-locked { opacity: .4; }
        .tl-line {
          flex: 1; width: 2px; background: var(--border);
          margin: 3px 0; min-height: 24px; border-radius: 2px;
        }
        .tl-line-active { background: linear-gradient(180deg, var(--secondary), var(--primary)); }

        .tl-body {
          flex: 1; padding-bottom: 2rem; display: flex;
          flex-direction: column; gap: .75rem; min-width: 0;
        }
        .tl-row:last-child .tl-body { padding-bottom: 0; }

        .tl-top { display: flex; flex-direction: column; gap: .25rem; }
        .tl-step-row { display: flex; align-items: center; gap: .5rem; }
        .tl-step-label {
          font-size: .67rem; font-weight: 700; letter-spacing: .08em; color: var(--text-light);
        }
        .tl-name { font-size: 1rem; font-weight: 700; color: var(--text); line-height: 1.3; }
        .tl-locked .tl-name { color: var(--text-muted); }
        .tl-desc { font-size: .845rem; color: var(--text-muted); line-height: 1.65; }

        /* Cert rows */
        .tl-certs {
          display: flex; flex-direction: column; gap: .5rem;
          padding: .875rem; background: var(--surface-2);
          border-radius: var(--radius-sm); border: 1px solid var(--border);
        }
        .tl-certs-label {
          font-size: .72rem; font-weight: 700; color: var(--text-light);
          letter-spacing: .05em; margin-bottom: .125rem;
        }
        .tl-cert-list { display: flex; flex-direction: column; gap: .325rem; }
        .tl-cert-row {
          display: flex; align-items: center; gap: .625rem;
          padding: .55rem .75rem;
          border-radius: var(--radius-xs);
          border: 1px solid var(--border); background: var(--surface);
          cursor: pointer; transition: all .18s; text-align: left; width: 100%;
        }
        .tl-cert-row:hover {
          border-color: var(--primary); background: var(--primary-light);
          transform: translateX(3px);
        }
        .tl-cert-badge {
          padding: .15rem .5rem; border-radius: var(--radius-xs);
          font-size: .68rem; font-weight: 700; white-space: nowrap; flex-shrink: 0;
        }
        .tl-cert-name { flex: 1; font-size: .86rem; font-weight: 600; color: var(--text); }
        .tl-cert-meta {
          display: flex; flex-direction: column; align-items: flex-end;
          gap: .1rem; flex-shrink: 0;
        }
        .tl-pass-rate { font-size: .7rem; color: var(--text-light); white-space: nowrap; }
        .tl-bottleneck { color: var(--warning); font-weight: 600; }
        .tl-achievability { font-size: .68rem; font-weight: 600; white-space: nowrap; }
        .tl-empty { font-size: .8rem; color: var(--text-light); font-style: italic; }

        .tl-expand-btn {
          display: inline-flex; align-items: center; gap: .3rem;
          font-size: .78rem; font-weight: 600; color: var(--primary);
          background: none; border: none; cursor: pointer;
          padding: .25rem 0; margin-top: .125rem;
        }

        /* State screens */
        .rm-state {
          display: flex; flex-direction: column; align-items: center;
          justify-content: center; min-height: 360px;
          gap: .875rem; text-align: center; color: var(--text-muted); padding: 2rem;
        }
        .rm-spin { color: var(--primary); animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .rm-state-title { font-size: 1.1rem; font-weight: 700; color: var(--text); }
        .rm-state-sub { font-size: .875rem; }
        .rm-error-wrap { display: flex; flex-direction: column; gap: 1rem; max-width: 480px; }
        .rm-error {
          display: flex; align-items: flex-start; gap: .75rem;
          padding: 1.25rem; flex-wrap: wrap;
        }
        .rm-error-title { font-weight: 700; color: var(--text); font-size: .9rem; }
        .rm-error-sub { font-size: .83rem; color: var(--text-muted); margin-top: .2rem; }
        .rm-error > div { flex: 1; min-width: 180px; }
        .rm-error-actions { display: flex; gap: .75rem; }

        .rm-footer {
          display: flex; gap: .75rem; align-items: center;
          flex-wrap: wrap; padding-top: .5rem; justify-content: space-between;
        }
      `}</style>
    </div>
  );
};

export default Roadmap;
