// Content Hash: SHA256:TBD
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { CertFlowDiagram } from '../../components/charts/CertFlowDiagram';
import { getCertCandidates } from '../../api/client';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { loadPipeline, savePipeline } from '../../utils/pipelineState';
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
  written_avg_pass_rate?: number | null;
  practical_avg_pass_rate?: number | null;
  exam_frequency?: string | null;
  exam_difficulty?: number | null;
  exam_fee_info?: string | null;
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

interface TodayActionData {
  risk_stage_id: string | null;
  cert_name: string;
  region: string;
  action: {
    action_type: string;
    title: string;
    description: string;
    cta: string;
    cta_path: string;
    effort_minutes: number;
  };
  motivation: string;
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
  '3': '3단계 (준비 정체)',   '4': '4단계 (고위험군)',
  '5': '5단계 (최고위험군)',
};
const RISK_IDS: Record<string, string> = {
  '1': 'risk_0001', '2': 'risk_0002', '3': 'risk_0003',
  '4': 'risk_0004', '5': 'risk_0005',
};

const ACTION_TYPE_EMOJI: Record<string, string> = {
  apply:        '💼',
  study:        '📖',
  training:     '🎓',
  space:        '📍',
  process_eval: '✅',
  reservation:  '📅',
  micro:        '⚡',
  wellness:     '💚',
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
  4: 'roadmap_stage_0002',
  5: 'roadmap_stage_0002',
};

function extractPassRate(text: string): number | null {
  // legacy fallback (구버전 text_for_dense 호환). 슬림 빌드에서는 cert.avg_pass_rate_3yr 직접 사용.
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
  avg_pass_rate_3yr?: number | null;  // 슬림 빌드 explicit 필드
  text_for_dense?: string;             // legacy fallback
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
      avg_pass_rate: c.avg_pass_rate_3yr ?? extractPassRate(c.text_for_dense ?? ''),
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
  const majorParam  = searchParams.get('major') ?? '';

  const [data, setData]       = useState<RoadmapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const [todayAction, setTodayAction]           = useState<TodayActionData | null>(null);
  const [todayActionLoading, setTodayActionLoading] = useState(false);

  // 탭: 'base' | 'ai'
  const [activeTab, setActiveTab] = useState<'base' | 'ai'>('base');
  const [llmData, setLlmData]     = useState<RoadmapData | null>(null);
  const [llmLoading, setLlmLoading] = useState(false);
  const [llmFetched, setLlmFetched] = useState(false);
  const [llmLoadStep, setLlmLoadStep] = useState(0);

  const LLM_LOAD_MESSAGES = [
    '위험군 단계와 관심 분야를 파악하는 중…',
    '조건에 맞는 자격증 후보를 추리는 중…',
    '학습 난이도와 선수 관계를 정리하는 중…',
    '단계별 로드맵 경로를 조합하는 중…',
    '마지막으로 검토하는 중…',
  ];

  useEffect(() => {
    if (!llmLoading) { setLlmLoadStep(0); return; }
    // 1.8s 간격으로 단계 진행 — 마지막 단계에서는 API 완료까지 대기
    const iv = setInterval(() => {
      setLlmLoadStep(s => Math.min(s + 1, LLM_LOAD_MESSAGES.length - 1));
    }, 1800);
    return () => clearInterval(iv);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [llmLoading]);

  // 인라인 evidence/DAG 드로어
  const [activeCert, setActiveCert] = useState<{ id: string; name: string } | null>(null);
  const [evRows, setEvRows] = useState<{ section_path: string[]; snippet: string; chunk_id: string; source_type?: string; similarity?: number | null; source_url?: string | null }[]>([]);
  const [dagData, setDagData] = useState<{ predecessors: { cert_id: string; cert_name: string; relation_label: string; cert_grade_tier?: string; avg_pass_rate?: number | null }[]; successors: { cert_id: string; cert_name: string; relation_label: string; cert_grade_tier?: string; avg_pass_rate?: number | null }[] } | null>(null);
  const [evLoading, setEvLoading] = useState(false);
  const [srData, setSrData] = useState<{ written: {year:string;session:string;pass_rate:number}[]; practical: {year:string;session:string;pass_rate:number}[]; total: number } | null>(null);
  const srCacheRef = useRef<Record<string, typeof srData>>({});
  const drawerAbortRef  = useRef<AbortController | null>(null);
  const roadmapAbortRef = useRef<AbortController | null>(null);
  const llmAbortRef     = useRef<AbortController | null>(null);
  const llmFetchingRef  = useRef(false);

  const riskId    = RISK_IDS[stageParam] ?? '';
  const riskNum   = parseInt(stageParam) || 0;
  const riskLabel = RISK_LABELS[stageParam] ?? '';

  // ── 파이프라인 guard & 세션 저장/복원 ──────────────────────────────
  useEffect(() => {
    if (stageParam && domainParam) {
      // URL에 파라미터가 있으면 세션에 저장
      savePipeline({
        stage: stageParam,
        domain: domainParam,
        domainName: domainName || undefined,
        job: jobParam || undefined,
        jobName: jobName || undefined,
        major: majorParam || undefined,
      });
      return;
    }
    // URL에 파라미터가 없으면 세션에서 복원 또는 이전 단계로 리디렉션
    const s = loadPipeline();
    if (s.stage && s.domain) {
      const p = new URLSearchParams({ stage: s.stage, domain: s.domain });
      if (s.domainName) p.set('domainName', s.domainName);
      if (s.job)        p.set('job', s.job);
      if (s.jobName)    p.set('jobName', s.jobName);
      if (s.major)      p.set('major', s.major);
      navigate(`/roadmap?${p.toString()}`, { replace: true });
      return;
    }
    // stage만 있으면 관심 선택으로
    if (s.stage) {
      navigate(`/interests?stage=${s.stage}`, { replace: true });
      return;
    }
    // 아무것도 없으면 위험군 진단으로
    navigate('/risk-assessment', { replace: true });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchRoadmap = useCallback(async () => {
    // guard: 파이프라인 복원 전에는 fetch 건너뜀
    if (!riskId || !domainParam) return;
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
      if (majorParam)  body.major_name    = majorParam;
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
  }, [riskId, domainParam, riskNum, jobParam, majorParam]);

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

  const fetchTodayAction = useCallback(async (certIds: string[]) => {
    if (!riskId) return;
    setTodayActionLoading(true);
    try {
      const params = new URLSearchParams({ risk_stage_id: riskId });
      if (certIds.length > 0) params.set('cert_ids', certIds.slice(0, 3).join(','));
      const res = await fetch(`/api/v1/actions/today?${params.toString()}`);
      const json = await res.json();
      if (json.success && json.data) setTodayAction(json.data);
    } catch { /* silent */ } finally {
      setTodayActionLoading(false);
    }
  }, [riskId]);

  useEffect(() => {
    fetchRoadmap();
    return () => { roadmapAbortRef.current?.abort(); };
  }, [fetchRoadmap]);

  useEffect(() => {
    if (!data || !riskId) return;
    const certIds = (data.roadmap_sequence ?? []).slice(0, 3).map(c => c.cert_id);
    fetchTodayAction(certIds);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, riskId]);

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
    setSrData(null);
    setEvLoading(true);
    try {
      const srCached = srCacheRef.current[certId];
      const srPromise = srCached !== undefined
        ? Promise.resolve(srCached)
        : fetch(`/api/v1/certs/${encodeURIComponent(certId)}/session-rates`, { signal: ctrl.signal })
            .then(r => r.json())
            .then(json => {
              const d = json.success && json.data?.total > 0
                ? { written: json.data.written ?? [], practical: json.data.practical ?? [], total: json.data.total ?? 0 }
                : null;
              srCacheRef.current[certId] = d;
              return d;
            })
            .catch(() => null);

      const [evRes, dagRes, srResult] = await Promise.all([
        fetch('/api/v1/recommendations/evidence', {
          method: 'POST', signal: ctrl.signal,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cert_id: certId }),
        }),
        fetch(`/api/v1/recommendations/related?cert_id=${encodeURIComponent(certId)}`, { signal: ctrl.signal }),
        srPromise,
      ]);
      if (ctrl.signal.aborted) return;
      const evJson = await evRes.json();
      const dagJson = await dagRes.json();
      if (evJson.success) setEvRows(evJson.data?.evidence ?? []);
      if (dagJson.success) setDagData(dagJson.data);
      setSrData(srResult ?? null);
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

      {/* 오늘의 한 행동 */}
      {(todayActionLoading || todayAction) && (
        <div className="rm-today-wrap">
          {todayActionLoading ? (
            <div className="rm-today-skeleton">
              <Loader2 size={14} className="rm-spin" />
              <span>오늘의 행동을 추천하는 중…</span>
            </div>
          ) : todayAction && (
            <div className="rm-today-card">
              <div className="rm-today-header">
                <span className="rm-today-label">오늘의 한 가지 행동</span>
                <span className="rm-today-effort">{todayAction.action.effort_minutes}분</span>
              </div>
              <p className="rm-today-title">
                {ACTION_TYPE_EMOJI[todayAction.action.action_type] ?? '⚡'} {todayAction.action.title}
              </p>
              <p className="rm-today-desc">{todayAction.action.description}</p>
              <p className="rm-today-motivation">{todayAction.motivation}</p>
              <div className="rm-today-footer">
                <button
                  className="rm-today-cta"
                  onClick={() => fetchTodayAction((data?.roadmap_sequence ?? []).slice(0, 3).map(c => c.cert_id))}
                  type="button"
                  title="다른 행동 추천받기"
                >
                  다른 행동 보기
                </button>
              </div>
            </div>
          )}
        </div>
      )}

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
          <p className="rm-state-sub">{LLM_LOAD_MESSAGES[llmLoadStep]}</p>
          <div className="rm-ai-steps">
            {LLM_LOAD_MESSAGES.map((msg, i) => (
              <div key={i} className={`rm-ai-step ${i < llmLoadStep ? 'done' : i === llmLoadStep ? 'active' : 'pending'}`}>
                <span className="rm-ai-step-dot" />
                <span className="rm-ai-step-label">
                  {i < llmLoadStep
                    ? msg.replace(/…$/, '').replace(/중$/, '완료').trim() + ' ✓'
                    : msg.replace(/…$/, '').trim()}
                </span>
              </div>
            ))}
          </div>
          <p className="rm-state-sub rm-ai-time-note">20~30초 소요됩니다</p>
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
                                      {cert.written_avg_pass_rate !== null && cert.written_avg_pass_rate !== undefined && (
                                        <span className="tl-pass-split">필기 {Math.round(cert.written_avg_pass_rate)}%</span>
                                      )}
                                      {cert.practical_avg_pass_rate !== null && cert.practical_avg_pass_rate !== undefined && (
                                        <span className="tl-pass-split tl-pass-practical">실기 {Math.round(cert.practical_avg_pass_rate)}%</span>
                                      )}
                                      {cert.exam_frequency && (
                                        <span className="tl-exam-freq">{cert.exam_frequency}</span>
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
                                            const isGasanjeom = ev.source_type === 'gasanjeom' || ev.source_type === 'gasanjeom_inferred';
                                            const isNational = ev.source_type === 'national_cert_catalog';
                                            const isPrivate  = ev.source_type === 'private_cert_catalog';
                                            const isCatalog  = isNational || isPrivate;

                                            if (isGasanjeom || sec === '가산점') {
                                              const isInferred = ev.source_type === 'gasanjeom_inferred';
                                              return (
                                                <div key={ev.chunk_id ?? i} className="rm-ev-gasanjeom">
                                                  <span className="rm-ev-gasanjeom-label">{isInferred ? '가산점 참고' : '공무원 가산점'}</span>
                                                  <p className="rm-ev-gasanjeom-text">{ev.snippet}</p>
                                                </div>
                                              );
                                            }
                                            const isIntro       = sec === '도입목적';
                                            const isCareer      = sec === '진로(자격활용)' || sec === '자격 활용 현황';
                                            const isExamInfo    = sec === '시험 정보' || sec.includes('합격률') || sec.includes('난이도');
                                            const isExamHistory = sec === '검정 현황';
                                            const snippetLines  = (isPrivate && ev.snippet.includes('\n'))
                                              ? ev.snippet.split('\n').filter(Boolean)
                                              : null;

                                            if (isExamHistory) {
                                              // 공백 구분 평문 테이블을 파싱
                                              const tks = ev.snippet.trim().split(/\s+/);
                                              const FIXED = ['연도','차시','응시자','합격자','합격률(%)'];
                                              let ti = 0;
                                              // 헤더 건너뜀
                                              for (const h of FIXED) { if (tks[ti] === h) ti++; }
                                              const years: string[] = [];
                                              while (ti < tks.length && /^20\d{2}$/.test(tks[ti])) years.push(tks[ti++]);
                                              const sessions: string[] = [];
                                              while (ti < tks.length && /^\d+차$/.test(tks[ti])) sessions.push(tks[ti++]);
                                              const nC = sessions.length;
                                              const rem = tks.slice(ti);
                                              const app = rem.slice(0, nC);
                                              const pas = rem.slice(nC, nC * 2);
                                              const rat = rem.slice(nC * 2, nC * 3);
                                              const spY = years.length > 0 ? Math.ceil(nC / years.length) : 1;
                                              type HRow = {year:string;session:string;app:string;pas:string;rat:string};
                                              const tableRows: HRow[] = sessions.map((s, idx) => ({
                                                year: idx % spY === 0 ? (years[Math.floor(idx / spY)] ?? '') : '',
                                                session: s,
                                                app: app[idx] ?? '-',
                                                pas: pas[idx] ?? '-',
                                                rat: rat[idx] && rat[idx] !== '.' ? rat[idx] + '%' : '-',
                                              }));
                                              const parsed = tableRows.length > 0 && nC > 0;
                                              return (
                                                <div key={ev.chunk_id ?? i} className="rm-ev-hist-wrap">
                                                  <span className="rm-ev-src rm-ev-src-catalog">공인민간자격</span>
                                                  <span className="rm-ev-hist-title">검정 현황</span>
                                                  {parsed ? (
                                                    <div style={{ overflowX: 'auto' }}>
                                                      <table className="rm-ev-hist-table">
                                                        <thead>
                                                          <tr>
                                                            <th>연도</th>
                                                            <th>차시</th>
                                                            <th>응시자</th>
                                                            <th>합격자</th>
                                                            <th>합격률</th>
                                                          </tr>
                                                        </thead>
                                                        <tbody>
                                                          {tableRows.map((r, ri) => (
                                                            <tr key={ri}>
                                                              <td className="rm-ev-hist-year">{r.year}</td>
                                                              <td className="rm-ev-hist-sess">{r.session}</td>
                                                              <td>{r.app}</td>
                                                              <td>{r.pas}</td>
                                                              <td className={`rm-ev-hist-rate${parseFloat(r.rat) >= 70 ? ' hi' : parseFloat(r.rat) >= 50 ? ' mid' : ''}`}>{r.rat}</td>
                                                            </tr>
                                                          ))}
                                                        </tbody>
                                                      </table>
                                                    </div>
                                                  ) : (
                                                    <p className="rm-ev-snippet">{ev.snippet}</p>
                                                  )}
                                                </div>
                                              );
                                            }

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
                                      {srData && srData.total > 0 && (() => {
                                        type ChartPt = { year: string; w: number | null; p: number | null };
                                        const yearMap: Record<string, { wS: number; wC: number; pS: number; pC: number }> = {};
                                        for (const r of srData.written) {
                                          if (!yearMap[r.year]) yearMap[r.year] = { wS: 0, wC: 0, pS: 0, pC: 0 };
                                          yearMap[r.year].wS += r.pass_rate; yearMap[r.year].wC++;
                                        }
                                        for (const r of srData.practical) {
                                          if (!yearMap[r.year]) yearMap[r.year] = { wS: 0, wC: 0, pS: 0, pC: 0 };
                                          yearMap[r.year].pS += r.pass_rate; yearMap[r.year].pC++;
                                        }
                                        const pts: ChartPt[] = Object.keys(yearMap).sort().map(y => ({
                                          year: y,
                                          w: yearMap[y].wC > 0 ? yearMap[y].wS / yearMap[y].wC : null,
                                          p: yearMap[y].pC > 0 ? yearMap[y].pS / yearMap[y].pC : null,
                                        }));
                                        const hasW = pts.some(p => p.w !== null);
                                        const hasP = pts.some(p => p.p !== null);
                                        if (!hasW && !hasP) return null;
                                        const W = 280, H = 80, PAD = 26;
                                        const allVals = pts.flatMap(p => [p.w, p.p]).filter(v => v != null) as number[];
                                        const minV = Math.max(0, Math.min(...allVals) - 5);
                                        const maxV = Math.min(100, Math.max(...allVals) + 5);
                                        const range = maxV - minV || 1;
                                        const toX = (i: number, total: number) => PAD + (i / Math.max(total - 1, 1)) * (W - PAD * 2);
                                        const toY = (v: number) => H - 14 - ((v - minV) / range) * (H - 28);
                                        const wPts = pts.map((p, i) => p.w !== null ? { x: toX(i, pts.length), y: toY(p.w), v: p.w, yr: p.year } : null).filter(Boolean) as {x:number;y:number;v:number;yr:string}[];
                                        const pPts = pts.map((p, i) => p.p !== null ? { x: toX(i, pts.length), y: toY(p.p), v: p.p, yr: p.year } : null).filter(Boolean) as {x:number;y:number;v:number;yr:string}[];
                                        return (
                                          <div className="rm-sr-section">
                                            <p className="rm-dag-title">합격률 추이</p>
                                            <div className="rm-sr-chart-wrap">
                                              <svg width={W} height={H} style={{ overflow: 'visible', display: 'block' }}>
                                                {hasW && wPts.length >= 2 && (
                                                  <polyline points={wPts.map(p => `${p.x},${p.y}`).join(' ')} fill="none" stroke="#2563eb" strokeWidth="2" strokeLinejoin="round" />
                                                )}
                                                {hasP && pPts.length >= 2 && (
                                                  <polyline points={pPts.map(p => `${p.x},${p.y}`).join(' ')} fill="none" stroke="#10b981" strokeWidth="2" strokeLinejoin="round" strokeDasharray="4 2" />
                                                )}
                                                {hasW && wPts.map((p, i) => (
                                                  <g key={`w${i}`}>
                                                    <circle cx={p.x} cy={p.y} r="3" fill="#2563eb" />
                                                    <text x={p.x} y={p.y - 6} textAnchor="middle" fontSize="9" fill="#2563eb" fontWeight="700">{p.v.toFixed(1)}%</text>
                                                    <text x={p.x} y={H - 2} textAnchor="middle" fontSize="8" fill="#94a3b8">{p.yr}</text>
                                                  </g>
                                                ))}
                                                {hasP && pPts.map((p, i) => (
                                                  <g key={`p${i}`}>
                                                    <circle cx={p.x} cy={p.y} r="3" fill="#10b981" />
                                                    <text x={p.x} y={p.y - 6} textAnchor="middle" fontSize="9" fill="#10b981" fontWeight="700">{p.v.toFixed(1)}%</text>
                                                  </g>
                                                ))}
                                              </svg>
                                              <div className="rm-sr-legend">
                                                {hasW && <span className="rm-sr-leg rm-sr-leg-w">필기</span>}
                                                {hasP && <span className="rm-sr-leg rm-sr-leg-p">실기</span>}
                                              </div>
                                            </div>
                                          </div>
                                        );
                                      })()}
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
          justify-content: center; min-height: 300px; gap: .875rem;
          text-align: center; color: var(--text-muted);
          background: var(--surface); border: 1px solid var(--border);
          border-radius: var(--radius-sm); padding: 2rem;
        }
        .rm-ai-steps {
          display: flex; flex-direction: column; gap: .45rem;
          margin-top: .25rem; width: 100%; max-width: 320px; text-align: left;
        }
        .rm-ai-step { display: flex; align-items: center; gap: .6rem; }
        .rm-ai-step-dot {
          width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
          background: var(--border); transition: background .3s;
        }
        .rm-ai-step.done .rm-ai-step-dot { background: var(--success); }
        .rm-ai-step.active .rm-ai-step-dot { background: var(--primary); box-shadow: 0 0 0 3px var(--primary-glow); }
        .rm-ai-step-label {
          font-size: .78rem; color: var(--text-light); transition: color .3s;
        }
        .rm-ai-step.done .rm-ai-step-label { color: var(--success); }
        .rm-ai-step.active .rm-ai-step-label { color: var(--primary); font-weight: 600; }
        .rm-ai-time-note { font-size: .73rem; margin-top: .25rem; opacity: .7; }

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
        .tl-line-active { background: var(--primary); }

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
        .rm-sr-section { display: flex; flex-direction: column; gap: .35rem; }
        .rm-sr-chart-wrap { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius-xs); padding: .625rem .75rem .375rem; display: flex; flex-direction: column; gap: .35rem; }
        .rm-sr-legend { display: flex; gap: .625rem; }
        .rm-sr-leg { font-size: .7rem; font-weight: 600; display: flex; align-items: center; gap: .3rem; }
        .rm-sr-leg::before { content: ''; display: inline-block; width: 14px; height: 2px; border-radius: 1px; }
        .rm-sr-leg-w { color: #2563eb; }
        .rm-sr-leg-w::before { background: #2563eb; }
        .rm-sr-leg-p { color: #10b981; }
        .rm-sr-leg-p::before { background: #10b981; }
        .rm-ev-hist-wrap { display: flex; flex-direction: column; gap: .35rem; }
        .rm-ev-hist-title { font-size: .72rem; font-weight: 700; color: var(--text-muted); }
        .rm-ev-hist-table { border-collapse: collapse; width: 100%; font-size: .78rem; min-width: 280px; }
        .rm-ev-hist-table th { background: var(--surface-3, #f1f5f9); color: var(--text-muted); font-weight: 700; padding: .3rem .5rem; text-align: center; border: 1px solid var(--border); white-space: nowrap; }
        .rm-ev-hist-table td { padding: .28rem .5rem; border: 1px solid var(--border); text-align: center; color: var(--text-muted); }
        .rm-ev-hist-year { font-weight: 700; color: var(--text); white-space: nowrap; }
        .rm-ev-hist-sess { color: var(--text-light); }
        .rm-ev-hist-rate { font-weight: 700; }
        .rm-ev-hist-rate.hi { color: #16a34a; }
        .rm-ev-hist-rate.mid { color: #d97706; }
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
        .rm-ev-gasanjeom { padding: .5rem .75rem; background: #fefce8; border: 1px solid #fde68a; border-radius: var(--radius-xs); display: flex; flex-direction: column; gap: .25rem; }
        .rm-ev-gasanjeom-label { font-size: .62rem; font-weight: 800; letter-spacing: .07em; color: #92400e; text-transform: uppercase; }
        .rm-ev-gasanjeom-text { font-size: .8rem; color: #78350f; line-height: 1.6; margin: 0; }
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
        .tl-pass-split { font-size: .68rem; color: #6366f1; white-space: nowrap; padding: .1rem .35rem; background: #eef2ff; border-radius: 4px; }
        .tl-pass-practical { color: #0891b2; background: #ecfeff; }
        .tl-exam-freq { font-size: .68rem; color: #059669; background: #ecfdf5; padding: .1rem .35rem; border-radius: 4px; white-space: nowrap; }
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

        /* Today's one action */
        .rm-today-wrap { width: 100%; }
        .rm-today-skeleton {
          display: flex; align-items: center; gap: .5rem;
          padding: .75rem 1rem; font-size: .8rem; color: var(--text-muted);
          background: var(--surface); border: 1px solid var(--border);
          border-radius: var(--radius-sm);
        }
        .rm-today-card {
          background: linear-gradient(135deg, #f0fdf4 0%, #eff6ff 100%);
          border: 1px solid rgba(16,185,129,.25);
          border-radius: var(--radius-sm); padding: 1rem 1.25rem;
          display: flex; flex-direction: column; gap: .5rem;
        }
        .rm-today-header {
          display: flex; align-items: center; justify-content: space-between;
        }
        .rm-today-label {
          font-size: .67rem; font-weight: 800; letter-spacing: .08em;
          color: #15803d; text-transform: uppercase;
        }
        .rm-today-effort {
          font-size: .72rem; font-weight: 700; color: #15803d;
          background: rgba(16,185,129,.12); padding: .1rem .5rem;
          border-radius: var(--radius-full);
        }
        .rm-today-title {
          font-size: .95rem; font-weight: 700; color: var(--text); margin: 0;
        }
        .rm-today-desc {
          font-size: .83rem; color: var(--text-muted); line-height: 1.6; margin: 0;
        }
        .rm-today-motivation {
          font-size: .77rem; color: #15803d; font-style: italic;
          border-left: 2px solid rgba(16,185,129,.35); padding-left: .6rem; margin: 0;
        }
        .rm-today-footer { display: flex; justify-content: flex-end; margin-top: .25rem; }
        .rm-today-cta {
          font-size: .75rem; font-weight: 600; color: var(--primary);
          background: none; border: 1px solid rgba(99,102,241,.3);
          border-radius: var(--radius-xs); padding: .2rem .7rem;
          cursor: pointer; transition: all .15s;
        }
        .rm-today-cta:hover { background: var(--primary-light); border-color: var(--primary); }
      `}</style>
    </div>
  );
};

export default Roadmap;
