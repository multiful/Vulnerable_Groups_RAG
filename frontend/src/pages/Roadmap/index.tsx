// Content Hash: SHA256:TBD
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { CertFlowDiagram } from '../../components/charts/CertFlowDiagram';
import { getCertCandidates } from '../../api/client';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, Loader2, AlertTriangle,
  CheckCircle2, Clock, Lock, ChevronDown, ChevronUp,
  Info, FileText, X,
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
  llm_reason?: string;
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
  llm_generated?: boolean;
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
  '1': '1단계 (취업 안정권)', '2': '2단계 (준비 활성)',
  '3': '3단계 (준비 정체)',   '4': '4단계 (관계망 약화)',
  '5': '5단계 (고위험군)',
};
const RISK_IDS: Record<string, string> = {
  '1': 'risk_0001', '2': 'risk_0002', '3': 'risk_0003',
  '4': 'risk_0004', '5': 'risk_0005',
};

/* ── Local fallback helpers ── */
const LOCAL_STAGES: StageInfo[] = [
  { id: 'roadmap_stage_0001', name: '상태 인식',   order: 1, description: '현재 생활 상태와 진로 및 취업 준비 수준을 점검하는 초기 단계입니다.' },
  { id: 'roadmap_stage_0002', name: '탐색 시작',   order: 2, description: '관심 분야, 전공 연계성, 가능한 직무와 자격증을 탐색하는 단계입니다.' },
  { id: 'roadmap_stage_0003', name: '역량 준비',   order: 3, description: '기초 학습, 자격증 준비, 교육훈련 참여 등으로 역량을 쌓는 단계입니다.' },
  { id: 'roadmap_stage_0004', name: '실행 확대',   order: 4, description: '지원 활동, 대외활동, 실전 경험을 늘리며 진로 실행을 확장하는 단계입니다.' },
  { id: 'roadmap_stage_0005', name: '유지 및 정착', order: 5, description: '형성된 진로 경로와 생활 리듬을 유지하며 장기 계획으로 정착하는 단계입니다.' },
];

/* roadmap_stage_master.csv 기준: risk_0001→0003, risk_0002/0003→0002, risk_0004/0005→0001 */
const STARTING_STAGE_MAP: Record<number, string> = {
  1: 'roadmap_stage_0003',
  2: 'roadmap_stage_0002',
  3: 'roadmap_stage_0002',
  4: 'roadmap_stage_0001',
  5: 'roadmap_stage_0001',
};

function extractPassRate(text: string): number | null {
  const m = text.match(/(?:3년 평균 합격률|합격률):\s*([\d.]+)/);
  return m ? Math.round(parseFloat(m[1])) : null;
}

function calcAchievability(tier: string, riskNum: number): string {
  const t = parseInt(tier.charAt(0)) || 3;
  // 기능사(1): 위험군 무관 항상 바로 도전 가능
  if (t <= 1) return 'immediate';
  // 산업기사(2): 위험군 4~5단계는 단기 목표, 1~3단계는 바로 도전
  if (t <= 2) return riskNum >= 4 ? 'near_term' : 'immediate';
  // 기사(3): 위험군 1~2단계만 바로 도전, 나머지는 단기 목표
  if (t <= 3) return riskNum <= 2 ? 'immediate' : 'near_term';
  // 기술사/기능장(4~5): 위험군 1~2단계는 단기, 나머지는 장기
  return riskNum <= 2 ? 'near_term' : 'long_term';
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

async function buildLocalRoadmap(riskId: string, domainId: string, riskNum: number, jobId?: string): Promise<RoadmapData> {
  const all = await getCertCandidates() as unknown as RawCert[];

  const filtered = all.filter(c => {
    const domainOk = !domainId || (c.related_domains ?? []).includes(domainId) || c.primary_domain === domainId;
    const riskOk   = !riskId   || (c.recommended_risk_stages ?? []).includes(riskId);
    const jobOk    = !jobId    || (c.related_jobs ?? []).includes(jobId);
    return domainOk && riskOk && jobOk;
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
  const jobParam    = searchParams.get('job') ?? '';
  const jobName     = searchParams.get('jobName') ?? '';

  const [data, setData]       = useState<RoadmapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  // 탭: 'base' | 'ai'
  const [activeTab, setActiveTab] = useState<'base' | 'ai'>('base');
  const [llmData, setLlmData]     = useState<RoadmapData | null>(null);
  const [llmLoading, setLlmLoading] = useState(false);
  const [llmFetched, setLlmFetched] = useState(false);

  // 인라인 evidence/DAG 드로어
  const [activeCert, setActiveCert] = useState<{ id: string; name: string } | null>(null);
  const [evRows, setEvRows] = useState<{ section_path: string[]; snippet: string; chunk_id: string; source_type?: string; similarity?: number | null; source_url?: string | null }[]>([]);
  const [dagData, setDagData] = useState<{ predecessors: { cert_id: string; cert_name: string; relation_label: string; cert_grade_tier?: string; avg_pass_rate?: number | null }[]; successors: { cert_id: string; cert_name: string; relation_label: string; cert_grade_tier?: string; avg_pass_rate?: number | null }[] } | null>(null);
  const [evLoading, setEvLoading] = useState(false);
  const drawerAbortRef  = useRef<AbortController | null>(null);
  const roadmapAbortRef = useRef<AbortController | null>(null);
  const llmAbortRef     = useRef<AbortController | null>(null);
  const llmFetchingRef  = useRef(false);

  const riskId    = RISK_IDS[stageParam] ?? '';
  const riskNum   = parseInt(stageParam) || 0;
  const riskLabel = RISK_LABELS[stageParam] ?? '';

  const fetchRoadmap = useCallback(async () => {
    /* Cancel any in-flight call (fixes React StrictMode double-invocation) */
    roadmapAbortRef.current?.abort();
    const compCtrl = new AbortController();
    roadmapAbortRef.current = compCtrl;

    setLoading(true);
    setError(null);

    /* ── 1. DB 우선 렌더 (5초 backend-only timeout) ── */
    let showed = false;
    try {
      const backendCtrl = new AbortController();
      const tid = setTimeout(() => backendCtrl.abort(), 5000);
      const body: Record<string, unknown> = { top_n_per_stage: 6 };
      if (riskId)      body.risk_stage_id = riskId;
      if (domainParam) body.domain_ids    = [domainParam];
      if (jobParam)    body.job_ids       = [jobParam];
      const res = await fetch('/api/v1/recommendations', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: backendCtrl.signal,
      });
      clearTimeout(tid);
      if (compCtrl.signal.aborted) return;
      const json: ApiResponse = await res.json();
      if (json.success && json.data) {
        setData(json.data);
        setLoading(false);
        showed = true;
      }
    } catch {
      if (compCtrl.signal.aborted) return;
    }

    /* ── 2. 로컬 fallback (DB 실패 시) ── */
    if (!showed) {
      try {
        const local = await buildLocalRoadmap(riskId, domainParam, riskNum, jobParam || undefined);
        if (compCtrl.signal.aborted) return;
        setData(local);
      } catch {
        if (compCtrl.signal.aborted) return;
        setError('데이터를 불러오지 못했습니다. 새로고침 해주세요.');
      } finally {
        if (!compCtrl.signal.aborted) setLoading(false);
      }
    }
  }, [riskId, domainParam, riskNum, jobParam]);

  // AI 탭 클릭 시 호출 (실패 후 재시도 가능)
  const fetchLlm = useCallback(async () => {
    if (llmFetchingRef.current) return;
    if (!riskId || !domainParam) return;
    /* Cancel any previous llm fetch */
    llmAbortRef.current?.abort();
    const ctrl = new AbortController();
    llmAbortRef.current = ctrl;
    llmFetchingRef.current = true;
    setLlmLoading(true);
    setLlmFetched(false);
    try {
      const tid = setTimeout(() => ctrl.abort(), 30000);
      const res = await fetch('/api/v1/recommendations/llm', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ risk_stage_id: riskId, domain_ids: [domainParam], domain_name: domainName, job_ids: jobParam ? [jobParam] : undefined }),
        signal: ctrl.signal,
      });
      clearTimeout(tid);
      if (llmAbortRef.current !== ctrl) return;
      const json: ApiResponse = await res.json();
      if (json.success && json.data) setLlmData(json.data);
    } catch { /* timeout → fallback notice shown; external abort → ref check guards */ } finally {
      llmFetchingRef.current = false;
      if (llmAbortRef.current === ctrl) {
        setLlmLoading(false);
        setLlmFetched(true);
      }
    }
  }, [riskId, domainParam, domainName]);

  useEffect(() => {
    fetchRoadmap();
    return () => { roadmapAbortRef.current?.abort(); };
  }, [fetchRoadmap]);

  const openCertDrawer = useCallback(async (certId: string, certName: string) => {
    if (activeCert?.id === certId) {
      setActiveCert(null);
      drawerAbortRef.current?.abort();
      return;
    }
    drawerAbortRef.current?.abort();
    const ctrl = new AbortController();
    drawerAbortRef.current = ctrl;

    setActiveCert({ id: certId, name: certName });
    setEvRows([]);
    setDagData(null);
    setEvLoading(true);
    try {
      const [evRes, dagRes] = await Promise.all([
        fetch('/api/v1/recommendations/evidence', {
          method: 'POST', signal: ctrl.signal,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cert_id: certId }),
        }),
        fetch(`/api/v1/recommendations/related?cert_id=${encodeURIComponent(certId)}`, { signal: ctrl.signal }),
      ]);
      if (ctrl.signal.aborted) return;
      const evJson = await evRes.json();
      const dagJson = await dagRes.json();
      if (evJson.success) setEvRows(evJson.data?.evidence ?? []);
      if (dagJson.success) setDagData(dagJson.data);
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
    } finally {
      if (!ctrl.signal.aborted) setEvLoading(false);
    }
  }, [activeCert]);

  function toggleExpand(id: string) {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  }

  function goToCert(certId: string, certName: string) {
    const p = new URLSearchParams();
    if (stageParam)  p.set('stage', stageParam);
    if (domainParam) p.set('domain', domainParam);
    if (domainName)  p.set('domainName', domainName);
    if (jobParam)    p.set('job', jobParam);
    if (jobName)     p.set('jobName', jobName);
    p.set('cert', certId);
    p.set('certName', certName);
    navigate(`/recommendation?${p.toString()}`);
  }

  function goToAll() {
    const p = new URLSearchParams();
    if (stageParam)  p.set('stage', stageParam);
    if (domainParam) p.set('domain', domainParam);
    if (domainName)  p.set('domainName', domainName);
    if (jobParam)    p.set('job', jobParam);
    if (jobName)     p.set('jobName', jobName);
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

  const displayData = (activeTab === 'ai' && llmData) ? llmData : data;
  const stages      = displayData.roadmap_by_stage ?? [];
  const startingIdx = stages.findIndex(s => s.is_starting_point);

  function handleTabAi() {
    setActiveTab('ai');
    if (!llmData && !llmLoading) fetchLlm();
  }

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
            {jobName && <span className="rm-chip rm-chip-job">{jobName}</span>}
          </div>
        </div>
        <p className="page-desc">
          {domainName
            ? <><strong>{domainName}</strong> 분야의 단계별 자격증 학습 경로입니다.</>
            : '단계별 자격증 학습 경로를 확인하세요.'}
        </p>
      </div>

      {/* 탭 */}
      {(domainParam && data) && (
        <div className="rm-tabs">
          <button
            className={`rm-tab${activeTab === 'base' ? ' rm-tab-active' : ''}`}
            onClick={() => setActiveTab('base')}
            type="button"
          >
            전체 추천
          </button>
          <button
            className={`rm-tab${activeTab === 'ai' ? ' rm-tab-active' : ''}`}
            onClick={handleTabAi}
            type="button"
          >
            {llmLoading
              ? <><Loader2 size={12} className="rm-spin rm-spin-sm" /> AI 분석 중…</>
              : <>✦ AI 맞춤 추천</>}
          </button>
        </div>
      )}

      {/* AI 탭 로딩 */}
      {activeTab === 'ai' && llmLoading && (
        <div className="rm-ai-loading">
          <Loader2 size={22} className="rm-spin" />
          <p className="rm-state-title">AI가 맞춤 로드맵을 구성하는 중…</p>
          <p className="rm-state-sub">위험군과 도메인을 분석해 최적 경로를 선별합니다 (20~30초 소요)</p>
        </div>
      )}

      {/* AI 탭 실패 → 기본 추천으로 대체 (소프트 안내) */}
      {activeTab === 'ai' && llmFetched && !llmData && !llmLoading && (
        <div className="fallback-notice rm-ai-fallback" style={{ margin: 0 }}>
          <Info size={13} />
          <span>AI 분석 결과를 가져오지 못했습니다. 아래에 기본 추천을 표시합니다.</span>
          <button className="rm-retry-btn" onClick={fetchLlm} type="button">다시 시도</button>
        </div>
      )}

      {/* fallback 노트 (전체 탭) */}
      {activeTab === 'base' && data.fallback_note && (
        <div className="fallback-notice">
          <Info size={13} />
          <span>{data.fallback_note}</span>
        </div>
      )}

      {/* AI 탭 안내 */}
      {activeTab === 'ai' && llmData && llmData.llm_generated && (
        <div className="fallback-notice llm-notice">
          <Info size={13} />
          <span>✦ AI 맞춤 분석이 완료되었습니다. 각 자격증 카드에서 추천 이유를 확인하세요.</span>
        </div>
      )}

      {/* 추천 결과 0건 안내 */}
      {!(activeTab === 'ai' && llmLoading) &&
        displayData.total_certs_in_roadmap === 0 && (
        <div className="fallback-notice rm-empty-notice">
          <Info size={14} style={{ flexShrink: 0, marginTop: '.1rem' }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.35rem', flex: 1 }}>
            {jobName && domainName ? (
              <>
                <span style={{ fontWeight: 600 }}>
                  "{domainName}" 분야와 "{jobName}" 직무를 동시에 만족하는 자격증이 없습니다.
                </span>
                <span style={{ fontSize: '.82rem', color: 'var(--text-light)', lineHeight: 1.55 }}>
                  선택한 도메인과 직무가 서로 다른 분야에 속해 있을 수 있습니다.
                  직무 선택을 해제하거나 다른 도메인으로 변경해 보세요.
                </span>
              </>
            ) : (
              <span>
                선택한 조건에 맞는 자격증이 없습니다. 도메인이나 위험군을 변경해보세요.
              </span>
            )}
          </div>
          <button className="rm-retry-btn" onClick={() => navigate(-1)} type="button">조건 변경</button>
        </div>
      )}

      {/* Stats bar */}
      {!(activeTab === 'ai' && llmLoading) && (
        <div className="rm-stats">
          <div className="rm-stat">
            <span className="rm-stat-num">{displayData.total_certs_in_roadmap}</span>
            <span className="rm-stat-label">추천 자격증</span>
          </div>
          <div className="rm-stat-divider" />
          <div className="rm-stat">
            <span className="rm-stat-num">{stages.filter(s => s.recommended_certs.length > 0).length}</span>
            <span className="rm-stat-label">활성 단계</span>
          </div>
          <div className="rm-stat-divider" />
          <div className="rm-stat">
            <span className="rm-stat-num">{displayData.starting_roadmap_stage?.name ?? '-'}</span>
            <span className="rm-stat-label">시작점</span>
          </div>
        </div>
      )}

      {/* Timeline */}
      {!(activeTab === 'ai' && llmLoading) && (
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
                          const color    = gradeColor(cert.cert_grade_tier);
                          const aColor   = achievabilityColor(cert.achievability);
                          const isActive = activeCert?.id === cert.cert_id;
                          return (
                            <React.Fragment key={cert.cert_id}>
                              <div className={`tl-cert-row${isActive ? ' tl-cert-row-active' : ''}`}>
                                <button
                                  className="tl-cert-main"
                                  onClick={() => goToCert(cert.cert_id, cert.cert_name)}
                                  type="button"
                                  title="자격증 상세 확인 페이지로 이동"
                                >
                                  <div className="tl-cert-top-row">
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
                                          합격률 {Math.round(cert.avg_pass_rate)}%
                                          {cert.is_bottleneck && ' ⚠'}
                                        </span>
                                      )}
                                      <span className="tl-achievability" style={{ color: aColor }}>
                                        {achievabilityLabel(cert.achievability)}
                                      </span>
                                    </div>
                                    <ArrowRight size={13} style={{ color: 'var(--text-light)', flexShrink: 0 }} />
                                  </div>
                                  {cert.llm_reason && (
                                    <p className="tl-cert-reason">{cert.llm_reason}</p>
                                  )}
                                </button>
                                <button
                                  className={`tl-drawer-btn${isActive ? ' tl-drawer-btn-active' : ''}`}
                                  onClick={() => openCertDrawer(cert.cert_id, cert.cert_name)}
                                  type="button"
                                  title={isActive ? '닫기' : '자격증 소개 · 자격활용 보기'}
                                >
                                  {isActive ? <X size={13} /> : <FileText size={13} />}
                                </button>
                              </div>

                              {isActive && (
                                <div className="rm-drawer">
                                  {evLoading ? (
                                    <div className="rm-drawer-loading">
                                      <Loader2 size={14} className="rm-spin" />
                                      <span>자료를 불러오는 중…</span>
                                    </div>
                                  ) : (
                                    <>
                                      {dagData && (dagData.predecessors.length > 0 || dagData.successors.length > 0) && (
                                        <div className="rm-dag-section">
                                          <p className="rm-dag-title">자격증 경로</p>
                                          <div className="rm-flow-scroll">
                                            <CertFlowDiagram
                                              current={{ cert_id: activeCert?.id ?? '', cert_name: activeCert?.name ?? '' }}
                                              predecessors={dagData.predecessors}
                                              successors={dagData.successors}
                                              onNodeClick={(id, name) => openCertDrawer(id, name)}
                                            />
                                          </div>
                                        </div>
                                      )}
                                      {evRows.length > 0 && (
                                        <div className="rm-ev-section">
                                          <p className="rm-dag-title">왜 이 자격증인가요</p>
                                          {[...evRows].sort((a, b) => {
                                            const pri = (s: string) => {
                                              if (s === '도입목적') return 0;
                                              if (s === '직무 · 역할') return 1;
                                              if (s === '시험 정보' || s.includes('합격률') || s.includes('난이도')) return 2;
                                              if (s === '진로(자격활용)' || s === '자격 활용 현황') return 3;
                                              if (s === '응시료') return 4;
                                              if (s === '시험 과목') return 5;
                                              return 6;
                                            };
                                            return pri(a.section_path?.[0] ?? '') - pri(b.section_path?.[0] ?? '');
                                          }).map((ev, i) => {
                                            const sec = ev.section_path?.[0] ?? '';
                                            const isNational = ev.source_type === 'national_cert_catalog';
                                            const isPrivate  = ev.source_type === 'private_cert_catalog';
                                            const isCatalog  = isNational || isPrivate;
                                            const isIntro    = sec === '도입목적';
                                            const isCareer   = sec === '진로(자격활용)' || sec === '자격 활용 현황';
                                            const isExamInfo = sec === '시험 정보' || sec.includes('합격률') || sec.includes('난이도');
                                            const snippetLines = (isPrivate && ev.snippet.includes('\n'))
                                              ? ev.snippet.split('\n').filter(Boolean)
                                              : null;
                                            if (isIntro) {
                                              return (
                                                <div key={ev.chunk_id ?? i} className="rm-ev-intro-box">
                                                  <span className="rm-ev-intro-label">자격증 소개</span>
                                                  <p className="rm-ev-intro-text">{ev.snippet}</p>
                                                </div>
                                              );
                                            }
                                            if (isCareer) {
                                              const careerText = ev.snippet.replace(/^진로\(자격활용\):\s*/, '');
                                              return (
                                                <div key={ev.chunk_id ?? i} className="rm-ev-career-box">
                                                  <span className="rm-ev-career-label">자격 활용</span>
                                                  {snippetLines && snippetLines.length > 1 ? (
                                                    <ul className="rm-ev-catalog-list">
                                                      {snippetLines.map((line, li) => (
                                                        <li key={li}>{line.replace(/^\+\s*/, '')}</li>
                                                      ))}
                                                    </ul>
                                                  ) : (
                                                    <p className="rm-ev-career-text">{careerText}</p>
                                                  )}
                                                </div>
                                              );
                                            }
                                            if (isExamInfo) {
                                              let pills: string[];
                                              if (ev.snippet.includes(' · ')) {
                                                pills = ev.snippet.split(' · ').filter(Boolean);
                                              } else {
                                                const rawPills: string[] = [];
                                                const diffLabels: Record<string, string> = {
                                                  '1':'하 (쉬움)','1.0':'하 (쉬움)','1.5':'중하','2':'중하','2.0':'중하',
                                                  '2.5':'중','3':'중 (보통)','3.0':'중 (보통)','3.5':'중상',
                                                  '4':'중상','4.0':'중상','4.5':'상','5':'상 (어려움)','5.0':'상 (어려움)',
                                                };
                                                const dm2 = ev.snippet.match(/시험 난이도:\s*(\d+(?:\.\d+)?)/);
                                                if (dm2) rawPills.push(`난이도: ${diffLabels[dm2[1]] ?? dm2[1]}`);
                                                const pm2 = ev.snippet.match(/3년 평균 합격률:\s*([\d.]+)/);
                                                if (pm2) rawPills.push(`합격률: ${Math.round(parseFloat(pm2[1]))}%`);
                                                const fm2 = ev.snippet.match(/연간 검정 횟수:\s*([^.\n]+)/);
                                                if (fm2) rawPills.push(`연간 시험: ${fm2[1].trim()}`);
                                                pills = rawPills.length ? rawPills : [ev.snippet];
                                              }
                                              return (
                                                <div key={ev.chunk_id ?? i} className="rm-ev-exam-section">
                                                  <span className="rm-ev-exam-label">시험 정보</span>
                                                  <div className="rm-ev-exam-row">
                                                    {pills.map((p, pi) => (
                                                      <span key={pi} className="rm-ev-exam-pill">{p}</span>
                                                    ))}
                                                  </div>
                                                </div>
                                              );
                                            }
                                            return (
                                              <div key={ev.chunk_id ?? i} className={`rm-ev-card${isCatalog ? ' rm-ev-card-catalog' : ''}`}>
                                                <div className="rm-ev-card-hdr">
                                                  {isCatalog ? (
                                                    <span className={`rm-ev-src ${isNational ? 'rm-ev-src-national' : 'rm-ev-src-catalog'}`}>
                                                      {isNational ? '국가자격' : '공인민간자격'}
                                                    </span>
                                                  ) : null}
                                                  {sec && <span className="rm-ev-sec-path">{sec}</span>}
                                                </div>
                                                {snippetLines && snippetLines.length > 1 ? (
                                                  <ul className="rm-ev-catalog-list">
                                                    {snippetLines.map((line, li) => (
                                                      <li key={li}>{line.replace(/^\+\s*/, '')}</li>
                                                    ))}
                                                  </ul>
                                                ) : (
                                                  <p className="rm-ev-snippet">{ev.snippet}</p>
                                                )}
                                              </div>
                                            );
                                          })}
                                        </div>
                                      )}
                                      {!evLoading && !dagData && evRows.length === 0 && (
                                        <p className="rm-drawer-empty">근거 데이터가 없습니다.</p>
                                      )}
                                    </>
                                  )}
                                </div>
                              )}
                            </React.Fragment>
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
      )}

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

        /* Tabs */
        .rm-tabs {
          display: flex; gap: 0;
          border-bottom: 2px solid var(--border);
        }
        .rm-tab {
          padding: .55rem 1.25rem; font-size: .875rem; font-weight: 600;
          background: none; border: none; cursor: pointer; color: var(--text-muted);
          border-bottom: 2px solid transparent; margin-bottom: -2px;
          transition: all .15s; display: inline-flex; align-items: center; gap: .35rem;
        }
        .rm-tab:hover { color: var(--primary); }
        .rm-tab-active { color: var(--primary); border-bottom-color: var(--primary); }
        .rm-spin-sm { animation: spin 1s linear infinite; }

        /* AI loading */
        .rm-ai-loading {
          display: flex; flex-direction: column; align-items: center;
          justify-content: center; min-height: 260px; gap: .875rem;
          text-align: center; color: var(--text-muted);
          background: var(--surface); border: 1px solid var(--border);
          border-radius: var(--radius-sm); padding: 2rem;
        }

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
        .rm-chip-job {
          background: #f0fdf4; color: #065f46;
          border-color: rgba(16,185,129,.25);
        }

        .fallback-notice {
          display: flex; align-items: flex-start; gap: .5rem;
          padding: .625rem .875rem;
          background: #fffbeb; border: 1px solid rgba(245,158,11,.25);
          border-radius: var(--radius-xs);
          font-size: .8rem; color: #92400e; line-height: 1.5;
        }
        .fallback-notice svg { flex-shrink: 0; margin-top: 1px; color: #f59e0b; }
        .llm-notice {
          background: #f0fdf4; border-color: rgba(16,185,129,.25);
          color: #065f46;
        }
        .llm-notice svg { color: #10b981; }
        .rm-ai-fallback { background: #f8fafc; border-color: var(--border); color: var(--text-muted); }
        .rm-ai-fallback svg { color: var(--text-light); }
        .rm-empty-notice { background: #f8fafc; border-color: var(--border); color: var(--text-muted); }
        .rm-retry-btn {
          margin-left: auto; flex-shrink: 0; padding: .2rem .7rem;
          background: none; border: 1px solid currentColor; border-radius: var(--radius-xs);
          font-size: .75rem; font-weight: 600; cursor: pointer; color: inherit;
          transition: background .15s;
        }
        .rm-retry-btn:hover { background: rgba(0,0,0,.06); }

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
          display: flex; align-items: stretch;
          border-radius: var(--radius-xs);
          border: 1px solid var(--border); background: var(--surface);
          transition: all .18s; width: 100%; overflow: hidden;
        }
        .tl-cert-row:hover { border-color: rgba(99,102,241,.35); transform: translateX(2px); box-shadow: 2px 0 0 0 var(--primary); }
        .tl-cert-row-active { border-color: var(--primary); box-shadow: 2px 0 0 0 var(--primary); background: #f5f3ff; }
        .tl-cert-main {
          flex: 1; display: flex; flex-direction: column; gap: .3rem; min-width: 0;
          padding: .55rem .75rem; text-align: left; background: none; border: none;
          cursor: pointer;
        }
        .tl-cert-row:hover .tl-cert-main { background: var(--primary-light); }
        .tl-cert-row-active .tl-cert-main { background: transparent; }
        .tl-locked .tl-cert-row { opacity: .6; }
        .tl-drawer-btn {
          flex-shrink: 0; width: 36px; display: flex; align-items: center; justify-content: center;
          background: none; border: none; border-left: 1px solid var(--border);
          color: var(--text-light); cursor: pointer; transition: all .15s;
          font-size: .64rem; font-weight: 700; flex-direction: column; gap: .1rem;
        }
        .tl-drawer-btn:hover { background: rgba(99,102,241,.08); color: var(--primary); }
        .tl-drawer-btn-active { color: var(--primary); background: rgba(99,102,241,.12); border-left-color: var(--primary); }
        .tl-cert-top-row { display: flex; align-items: center; gap: .625rem; width: 100%; }

        /* Inline evidence/DAG drawer */
        .rm-drawer {
          margin: .1rem 0 .375rem;
          border: 1px solid rgba(99,102,241,.3); border-radius: var(--radius-xs);
          background: #f8f9ff; padding: .875rem 1rem;
          display: flex; flex-direction: column; gap: .75rem;
        }
        .rm-drawer-loading {
          display: flex; align-items: center; gap: .5rem;
          color: var(--text-muted); font-size: .8rem;
        }
        .rm-dag-section, .rm-ev-section { display: flex; flex-direction: column; gap: .35rem; }
        .rm-dag-title {
          font-size: .69rem; font-weight: 700; color: var(--text-light);
          letter-spacing: .04em; text-transform: uppercase; margin-bottom: .15rem;
        }
        .rm-flow-scroll { overflow-x: auto; padding-bottom: .25rem; }
        .rm-ev-card {
          display: flex; flex-direction: column; gap: .3rem;
          padding: .5rem .625rem; background: var(--surface);
          border-radius: var(--radius-xs); border: 1px solid var(--border);
          border-left: 3px solid var(--primary-light);
        }
        .rm-ev-card-hdr { display: flex; align-items: center; gap: .35rem; flex-wrap: wrap; }
        .rm-ev-src {
          padding: .1rem .35rem; border-radius: 3px;
          font-size: .6rem; font-weight: 700; letter-spacing: .05em; flex-shrink: 0;
        }
        .rm-ev-src-db { background: #ede9fe; color: #6d28d9; }
        .rm-ev-src-local { background: #f1f5f9; color: #64748b; }
        .rm-ev-src-catalog { background: #fef3c7; color: #92400e; }
        .rm-ev-src-national { background: #dbeafe; color: #1e40af; }
        .rm-ev-card-catalog { border-color: rgba(245,158,11,.35); border-left-color: #f59e0b; background: #fffbeb; }
        .rm-ev-catalog-list { margin: 0; padding-left: 1.1rem; display: flex; flex-direction: column; gap: .3rem; }
        .rm-ev-catalog-list li { font-size: .78rem; color: var(--text-muted); line-height: 1.6; }
        .rm-ev-sec-path { font-size: .7rem; font-weight: 600; color: var(--primary); }
        .rm-ev-score { display: flex; align-items: center; gap: .3rem; margin-left: auto; }
        .rm-ev-score-track { width: 42px; height: 4px; background: var(--border); border-radius: 99px; overflow: hidden; }
        .rm-ev-score-fill { height: 100%; background: var(--primary); border-radius: 99px; }
        .rm-ev-score-pct { font-size: .65rem; font-weight: 700; color: var(--primary); white-space: nowrap; }
        .rm-ev-snippet { font-size: .79rem; color: var(--text-muted); line-height: 1.55; margin: 0; }
        .rm-drawer-empty { font-size: .8rem; color: var(--text-light); font-style: italic; margin: 0; }
        .rm-ev-intro-box { padding: .625rem .75rem; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: var(--radius-xs); display: flex; flex-direction: column; gap: .3rem; }
        .rm-ev-intro-label { font-size: .62rem; font-weight: 800; letter-spacing: .07em; color: #1d4ed8; text-transform: uppercase; }
        .rm-ev-intro-text { font-size: .8rem; color: #1e3a5f; line-height: 1.65; margin: 0; }
        .rm-ev-career-box { padding: .625rem .75rem; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: var(--radius-xs); display: flex; flex-direction: column; gap: .3rem; }
        .rm-ev-career-label { font-size: .62rem; font-weight: 800; letter-spacing: .07em; color: #15803d; text-transform: uppercase; }
        .rm-ev-career-text { font-size: .79rem; color: #14532d; line-height: 1.65; margin: 0; }
        .rm-ev-exam-section { padding: .625rem .75rem; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius-xs); display: flex; flex-direction: column; gap: .4rem; }
        .rm-ev-exam-label { font-size: .62rem; font-weight: 800; letter-spacing: .07em; color: var(--primary); text-transform: uppercase; }
        .rm-ev-exam-row { display: flex; flex-wrap: wrap; gap: .35rem; }
        .rm-ev-exam-pill { display: inline-flex; align-items: center; padding: .2rem .6rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-full); font-size: .74rem; font-weight: 600; color: var(--text); white-space: nowrap; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
        .tl-cert-reason {
          font-size: .76rem; color: var(--text-muted); line-height: 1.55;
          font-style: italic; padding-left: .25rem;
          border-left: 2px solid var(--success-light);
          padding-left: .5rem; margin: 0;
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
