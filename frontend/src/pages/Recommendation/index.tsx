// Content Hash: SHA256:TBD
import React, { useState, useMemo, useEffect, useCallback, useDeferredValue, memo, useTransition, useRef } from 'react';
import { CertFlowDiagram } from '../../components/charts/CertFlowDiagram';
import { getCertCandidates } from '../../api/client';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { loadPipeline } from '../../utils/pipelineState';
import {
  Search, Map, FileText, ChevronDown, AlertCircle,
  Loader2, ArrowLeft, ArrowRight, X, BookOpen, ExternalLink,
  Video, Play, Sparkles,
} from 'lucide-react';
import type { CertCandidate } from '../../types/cert';

const DOMAIN_NAMES: Record<string, string> = {
  domain_0001:'데이터/AI', domain_0002:'소프트웨어개발', domain_0003:'IT인프라/보안',
  domain_0004:'정보통신/무선', domain_0005:'전기/전자', domain_0006:'기계/제조',
  domain_0007:'재료/금속', domain_0008:'화학/바이오', domain_0009:'에너지/원자력',
  domain_0010:'건축/실내건축', domain_0011:'토목/측량/공간정보', domain_0012:'환경/안전',
  domain_0013:'자동차/모빌리티정비', domain_0014:'소방/방재', domain_0015:'비파괴검사/품질검사',
  domain_0016:'금융/회계', domain_0017:'경영/사무', domain_0018:'유통/물류/무역',
  domain_0019:'영업/CS', domain_0020:'부동산/감정/주택관리', domain_0021:'공공/행정',
  domain_0022:'법률', domain_0023:'의료/보건', domain_0024:'사회복지/상담',
  domain_0025:'스포츠/레저/재활', domain_0026:'반려동물/생활케어', domain_0027:'교육',
  domain_0028:'언어/문서/속기', domain_0029:'관광/항공/호텔', domain_0030:'조리/식품',
  domain_0031:'미용/패션', domain_0032:'의류/패션제작', domain_0033:'디자인',
  domain_0034:'콘텐츠/미디어', domain_0035:'공예/목재/주얼리', domain_0036:'음악/공연',
  domain_0037:'문화유산/보존수리', domain_0038:'농림/축산/수산', domain_0039:'광산',
  domain_0040:'철도/교통운송', domain_0041:'선박/해양', domain_0042:'항공/조종',
  domain_0043:'국방/특수',
};

const JOB_NAMES: Record<string, string> = {
  job_0001:'데이터 분석', job_0002:'데이터 엔지니어', job_0003:'데이터 사이언스',
  job_0004:'BI/리포팅 분석', job_0005:'AI 개발', job_0006:'머신러닝 엔지니어',
  job_0007:'MLOps 엔지니어', job_0008:'AI 서비스 기획', job_0009:'백엔드 개발',
  job_0010:'프론트엔드 개발', job_0011:'풀스택 개발', job_0012:'웹 개발',
  job_0013:'모바일 앱 개발', job_0014:'API/서버 개발', job_0015:'게임 개발',
  job_0016:'게임 서버 개발', job_0017:'클라이언트 개발', job_0018:'임베디드 개발',
  job_0019:'테스트/QA 엔지니어', job_0020:'시스템 운영', job_0021:'서버 운영',
  job_0022:'네트워크 운영', job_0023:'클라우드 엔지니어', job_0024:'DevOps 엔지니어',
  job_0025:'정보보안', job_0026:'데이터베이스 운영', job_0027:'정보통신 엔지니어',
  job_0028:'무선통신 운영', job_0029:'디지털포렌식', job_0030:'전기 엔지니어',
  job_0031:'전자 엔지니어', job_0032:'반도체 장비', job_0033:'제어/PLC 엔지니어',
  job_0034:'기계설계', job_0035:'기계정비', job_0036:'생산관리',
  job_0037:'생산기술', job_0038:'공정관리', job_0039:'품질관리',
  job_0040:'비파괴검사', job_0041:'산업안전관리', job_0042:'소방/방재 관리',
  job_0043:'환경관리', job_0044:'에너지 설비 운영', job_0045:'원자력 기술',
  job_0046:'건축 설계', job_0047:'건축 시공', job_0048:'실내건축',
  job_0049:'토목 설계', job_0050:'도시계획', job_0051:'측량/GIS',
  job_0052:'현장관리', job_0053:'건설안전관리', job_0054:'국가유산 보존수리',
  job_0055:'철도 운영/정비', job_0056:'철도 신호', job_0057:'철도 차량 정비',
  job_0058:'자동차 정비', job_0059:'자동차 진단평가', job_0060:'선박 운항',
  job_0061:'선박 기관', job_0062:'선박 정비', job_0063:'항공 운항',
  job_0064:'항공 정비', job_0065:'물류/운송 운영', job_0066:'세무',
  job_0067:'회계', job_0068:'재무', job_0069:'금융사무',
  job_0070:'자산관리', job_0071:'보험보상', job_0072:'리스크 관리',
  job_0073:'경영지원', job_0074:'일반사무', job_0075:'인사',
  job_0076:'총무', job_0077:'마케팅', job_0078:'영업관리',
  job_0079:'무역사무', job_0080:'물류관리', job_0081:'유통관리',
  job_0082:'공공행정', job_0083:'정책기획/평가', job_0084:'법무사무',
  job_0085:'부동산/주택관리', job_0086:'감정평가', job_0087:'간호사',
  job_0088:'보건의료정보', job_0089:'병원행정', job_0090:'의무기록 관리',
  job_0091:'임상지원', job_0092:'의료코디네이터', job_0093:'응급구조',
  job_0094:'사회복지사', job_0095:'상담사', job_0096:'청소년지도',
  job_0097:'직업상담', job_0098:'복지행정', job_0099:'사례관리',
  job_0100:'재활지원', job_0101:'교육', job_0102:'평생교육',
  job_0103:'직업교육', job_0104:'한국어교육', job_0105:'호텔 서비스',
  job_0106:'관광통역', job_0107:'여행기획', job_0108:'조리',
  job_0109:'제과/제빵', job_0110:'바리스타', job_0111:'식품품질관리',
  job_0112:'영양/급식', job_0113:'외식서비스 운영', job_0114:'헤어디자인',
  job_0115:'메이크업', job_0116:'피부관리', job_0117:'반려동물 관리',
  job_0118:'스포츠지도', job_0119:'생활건강관리', job_0120:'시각디자인',
  job_0121:'UI/UX 디자인', job_0122:'편집디자인', job_0123:'산업디자인',
  job_0124:'영상편집', job_0125:'콘텐츠 제작', job_0126:'방송/미디어 제작',
  job_0127:'3D 콘텐츠 제작', job_0128:'문예창작', job_0129:'인쇄/출판 제작',
  job_0130:'공예/주얼리 제작', job_0131:'음악/공연 실무', job_0132:'패션 제작',
  job_0133:'농업기술', job_0134:'스마트팜 운영', job_0135:'산림관리',
  job_0136:'축산관리', job_0137:'수산양식', job_0138:'광업/자원개발',
  job_0139:'국방사업관리', job_0140:'무인기 운용', job_0141:'폭발물 처리',
  job_0142:'특수 안전관리',
};

function buildCertSummary(cert: CertCandidate): string {
  const domain = DOMAIN_NAMES[cert.primary_domain] ?? '';
  const jobs = cert.related_jobs.slice(0, 4).map(j => JOB_NAMES[j]).filter(Boolean);
  // 슬림 JSON: explicit 필드 우선, 구버전 호환을 위해 text_for_dense regex fallback
  const passRate = cert.avg_pass_rate_3yr ?? (() => {
    const m = cert.text_for_dense?.match(/3년 평균 합격률:\s*([\d.]+)%/);
    return m ? parseFloat(m[1]) : null;
  })();
  const sessions = cert.exam_sessions_per_year ?? (() => {
    const m = cert.text_for_dense?.match(/연간 검정 횟수:\s*연 (\d+)회/);
    return m ? parseInt(m[1], 10) : null;
  })();
  const parts: string[] = [];
  if (domain) parts.push(domain + ' 분야');
  if (jobs.length > 0) {
    parts.push(jobs.length > 2
      ? `${jobs.slice(0, 2).join(', ')} 외 ${jobs.length - 2}개 직무`
      : jobs.join(', ') + ' 직무');
  }
  if (sessions !== null) {
    parts.push(sessions === 0 ? '상시 시험' : `연 ${sessions}회 시험`);
  }
  if (passRate !== null) parts.push(`합격률 ${passRate.toFixed(0)}%`);
  return parts.join(' · ');
}

const RISK_LABEL: Record<string, string> = {
  '1': '1단계 (취업 안정권)', '2': '2단계 (준비 활성)', '3': '3단계 (준비 정체)',
  '4': '4단계 (고위험군)', '5': '5단계 (최고위험군)',
};
const RISK_IDS: Record<string, string> = {
  '1': 'risk_0001', '2': 'risk_0002', '3': 'risk_0003',
  '4': 'risk_0004', '5': 'risk_0005',
};
const GRADE_LABEL: Record<string, string> = {
  '5_기능장': '기능장', '4_기술사': '기술사', '3_기사': '기사',
  '2_산업기사': '산업기사', '1_기능사': '기능사',
};
function gradeBadgeClass(tier: string): string {
  if (tier.startsWith('4') || tier.startsWith('5')) return 'badge-primary';
  if (tier.startsWith('3')) return 'badge-secondary';
  if (tier.startsWith('2')) return 'badge-success';
  if (tier.startsWith('1')) return 'badge-warning';
  return 'badge-neutral';
}
function gradeColor(tier: string): string {
  if (tier.startsWith('4') || tier.startsWith('5')) return '#6366f1';
  if (tier.startsWith('3')) return '#0ea5e9';
  if (tier.startsWith('2')) return '#10b981';
  if (tier.startsWith('1')) return '#f59e0b';
  return '#94a3b8';
}

interface EvidenceRow {
  doc_id: string;
  chunk_id: string;
  source_type: string;
  snippet: string;
  section_path: string[];
  source_url: string | null;
  cert_name?: string;
  similarity?: number | null;
}
interface EvidenceState {
  loading: boolean;
  rows: EvidenceRow[];
  error: string | null;
  fetched: boolean;
  certId: string;
}

interface RelatedCert {
  cert_id: string;
  cert_name: string;
  cert_grade_tier: string;
  relation_label: string;
  relation_type: string;
  avg_pass_rate: number | null;
}
interface DagState {
  loading: boolean;
  predecessors: RelatedCert[];
  successors: RelatedCert[];
  certId: string;
  fetched: boolean;
}

interface VideoItem {
  video_id: string;
  title: string;
  channel: string;
  thumbnail_url: string;
  url: string;
}
interface VideosState {
  loading: boolean;
  videos: VideoItem[];
  error: string | null;
  warning: string | null;
  fetched: boolean;
  certId: string;
  certName: string;
  cacheHit: boolean;
}

interface ExamItem {
  impl_seq_name: string | null;
  registration_start: string | null;
  registration_end: string | null;
  exam_start: string | null;
  exam_end: string | null;
  pass_announce_date: string | null;
  d_day_exam: number | null;
  d_day_registration: number | null;
}
interface CertStatsData {
  written_avg_pass_rate: number | null;
  practical_avg_pass_rate: number | null;
  avg_pass_rate_3yr: number | null;
  exam_frequency: string | null;
  exam_difficulty: number | null;
  exam_type_info: string | null;
  exam_subject_info: string | null;
}

interface CertInfoData {
  info: {
    qualification_type?: string;
    level?: string;
    related_occupation?: string;
    acquisition_method?: string;
    exam_fee_written?: string;
    exam_fee_practical?: string;
    eligibility?: string;
    issuer?: string;
    website?: string;
  } | null;
  exam_info: {
    written_subjects?: string;
    practical_subjects?: string;
    written_pass_score?: string;
    practical_pass_score?: string;
    written_exam_time?: string;
    practical_exam_time?: string;
    exam_method?: string;
  } | null;
}
interface JobLearnerItem {
  itemNm?: string;
  corpNm?: string;
  jmNm?: string;
  [key: string]: unknown;
}
interface SessionRateRow {
  year: string; session: string; exam_type: string; grade: string;
  applicants: number; passed: number; pass_rate: number;
}
interface SessionRatesData {
  written: SessionRateRow[];
  practical: SessionRateRow[];
  other: SessionRateRow[];
  total: number;
}
interface ExecState {
  loading: boolean;
  schedule: ExamItem[];
  hiringTotal: number;
  hiringItems: Array<{ title: string; company: string; url: string; close_date: string }>;
  trainingTotal: number;
  trainingItems: Array<{ course_name: string; institution_name: string; employment_rate: string }>;
  certId: string;
  fetched: boolean;
  activeTab: 'schedule' | 'hiring' | 'training' | 'certinfo';
  certInfoData: CertInfoData | null;
  certInfoLoading: boolean;
  certInfoFetched: boolean;
  certStatsData: CertStatsData | null;
  certStatsLoading: boolean;
  certStatsFetched: boolean;
  sessionRatesData: SessionRatesData | null;
  sessionRatesLoading: boolean;
  sessionRatesFetched: boolean;
  jobLearnerItems: JobLearnerItem[];
  jobLearnerLoading: boolean;
  jobLearnerFetched: boolean;
  certJobsList: string[];
  certJobsLoading: boolean;
  certJobsFetched: boolean;
  canonicalRoles: Array<{ job_role_id: string; job_role_name: string; job_top_group_name: string }>;
  relatedMajors: string[];
  selectedJobName: string | null;
  jobDetailData: {
    job_name: string; salary: string; outlook: string; work_content: string;
    pay_score?: number | null; job_security_score?: number | null;
    growth_score?: number | null; work_conditions_score?: number | null;
    professionalism_score?: number | null; equity_score?: number | null;
    similar_jobs?: string | null; salary_summary?: string | null;
  } | null;
  jobDetailLoading: boolean;
  processEvalItems: Array<{ [key: string]: unknown }>;
  processEvalLoading: boolean;
  processEvalFetched: boolean;
}

/* ── Memoized cert card ── */
const CertCard = memo(({
  cert, onEvidence, onDag, onRoadmap, isSelected, matchLabel, isCrossDomain,
}: {
  cert: CertCandidate;
  onEvidence: (id: string) => void;
  onDag: (id: string) => void;
  onRoadmap: (id: string) => void;
  isSelected?: boolean;
  matchLabel?: string | null;
  isCrossDomain?: boolean;
}) => {
  const summary = buildCertSummary(cert);
  const passRate = cert.avg_pass_rate_3yr ?? (() => {
    const m = cert.text_for_dense?.match(/3년 평균 합격률:\s*([\d.]+)%/);
    return m ? parseFloat(m[1]) : null;
  })();
  const pct = passRate !== null ? Math.min(Math.round(passRate), 100) : null;
  // 합격률 구간별 색상: ≤25% 어려움(빨강), 26~50% 보통(주황), 51~70% 양호(파랑), >70% 쉬움(초록)
  const rateColor = pct === null ? '#94a3b8'
    : pct <= 25  ? '#ef4444'
    : pct <= 50  ? '#f59e0b'
    : pct <= 70  ? '#3b82f6'
    : '#10b981';
  const rateLabel = pct === null ? null
    : pct <= 25  ? '높은 난이도'
    : pct <= 50  ? '보통 난이도'
    : pct <= 70  ? '낮은 난이도'
    : '취득 용이';

  return (
    <div
      className={`card cert-card${isSelected ? ' cert-card-selected' : ''}`}
      onClick={() => { onEvidence(cert.cert_id); onDag(cert.cert_id); }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { onEvidence(cert.cert_id); onDag(cert.cert_id); } }}
    >
      <div className="cert-top">
        <div className="cert-top-row">
          <span className={`badge ${gradeBadgeClass(cert.cert_grade_tier)}`}>
            {GRADE_LABEL[cert.cert_grade_tier] ?? cert.cert_grade_tier}
          </span>
          <span className="cert-issuer">{cert.issuer}</span>
          {matchLabel && (
            <span
              className="cert-match-tag"
              data-cross={isCrossDomain ? 'true' : undefined}
              title={isCrossDomain ? '주 분야가 다르지만 관련 분야로 표시됨' : `'${matchLabel}' 조건으로 매칭`}
            >{matchLabel}</span>
          )}
        </div>
        <h3 className="cert-name">{cert.cert_name}</h3>
        <p className="cert-summary">{summary}</p>
      </div>

      {/* ── 합격률 미니 게이지 ── */}
      {pct !== null && (
        <div className="cert-rate-wrap">
          <div className="cert-rate-header">
            <span className="cert-rate-label">3년 평균 합격률</span>
            <span className="cert-rate-pct" style={{ color: rateColor }}>{pct}%</span>
            {rateLabel && <span className="cert-rate-tag" style={{ background: rateColor + '18', color: rateColor }}>{rateLabel}</span>}
          </div>
          <div className="cert-rate-track">
            <div className="cert-rate-fill" style={{ width: `${pct}%`, background: rateColor }} />
          </div>
        </div>
      )}

      <div className="cert-actions">
        <span className="cert-click-hint"><FileText size={11} /> 클릭하여 상세 보기</span>
        <button
          className="text-btn roadmap-btn"
          onClick={(e) => { e.stopPropagation(); onRoadmap(cert.cert_id); }}
        >
          <Map size={13} /> 로드맵 <ArrowRight size={12} />
        </button>
      </div>

      <p className="cert-data-src">한국산업인력공단</p>
    </div>
  );
});

const Recommendation: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // URL 파라미터가 없을 때 세션에서 복원 (헤더 내비게이션 등으로 컨텍스트 손실 시)
  const [pSession] = useState(() => loadPipeline());
  const stageParam  = searchParams.get('stage')      || pSession.stage     || '';
  const domainParam = searchParams.get('domain')     || pSession.domain    || '';
  const domainName  = searchParams.get('domainName') || pSession.domainName || domainParam;
  const jobParam    = searchParams.get('job')        || pSession.job       || '';
  const jobName     = searchParams.get('jobName')    || pSession.jobName   || '';
  const certIdParam = searchParams.get('cert') ?? '';

  const [allCerts, setAllCerts] = useState<CertCandidate[]>([]);
  const [certsLoading, setCertsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGrade, setSelectedGrade] = useState('');
  const [sortBy, setSortBy] = useState<'default' | 'passrate_desc' | 'grade_desc' | 'name_asc'>('default');
  const [expandedJobsCerts, setExpandedJobsCerts] = useState<Set<string>>(new Set());
  const deferredQuery = useDeferredValue(searchQuery);

  const [evidence, setEvidence] = useState<EvidenceState>({
    loading: false, rows: [], error: null, fetched: false, certId: '',
  });
  const [showEvidence, setShowEvidence] = useState(false);
  const [dag, setDag] = useState<DagState>({
    loading: false, predecessors: [], successors: [], certId: '', fetched: false,
  });
  const [videos, setVideos] = useState<VideosState>({
    loading: false, videos: [], error: null, warning: null, fetched: false,
    certId: '', certName: '', cacheHit: false,
  });
  const [certExplain, setCertExplain] = useState<{
    loading: boolean; text: string | null; certId: string; error: string | null;
  }>({ loading: false, text: null, certId: '', error: null });

  const [exec, setExec] = useState<ExecState>({
    loading: false, schedule: [], hiringTotal: 0, hiringItems: [],
    trainingTotal: 0, trainingItems: [], certId: '', fetched: false, activeTab: 'schedule',
    certInfoData: null, certInfoLoading: false, certInfoFetched: false,
    certStatsData: null, certStatsLoading: false, certStatsFetched: false,
    sessionRatesData: null, sessionRatesLoading: false, sessionRatesFetched: false,
    jobLearnerItems: [], jobLearnerLoading: false, jobLearnerFetched: false,
    certJobsList: [], certJobsLoading: false, certJobsFetched: false,
    canonicalRoles: [], relatedMajors: [],
    selectedJobName: null, jobDetailData: null, jobDetailLoading: false,
    processEvalItems: [], processEvalLoading: false, processEvalFetched: false,
  });

  // ── In-memory caches: avoid redundant API calls when re-clicking same cert ──
  const [, startTransition] = useTransition();
  const evidenceCacheRef = useRef<Record<string, EvidenceRow[]>>({});
  const dagCacheRef = useRef<Record<string, { predecessors: RelatedCert[]; successors: RelatedCert[] }>>({});
  const execCacheRef = useRef<Record<string, Pick<ExecState, 'schedule' | 'hiringTotal' | 'hiringItems' | 'trainingTotal' | 'trainingItems'>>>({});
  const certInfoCacheRef = useRef<Record<string, CertInfoData | null>>({});
  const certStatsCacheRef = useRef<Record<string, CertStatsData | null>>({});
  const certExplainCacheRef = useRef<Record<string, string | null>>({});
  const jobLearnerCacheRef = useRef<Record<string, JobLearnerItem[]>>({});
  const certJobsCacheRef = useRef<Record<string, { jobs: string[]; canonicalRoles: ExecState['canonicalRoles']; relatedMajors: string[] }>>({});
  const processEvalCacheRef = useRef<Record<string, Array<{ [key: string]: unknown }>>>({});

  useEffect(() => {
    let cancelled = false;
    getCertCandidates()
      .then((data: CertCandidate[]) => { if (!cancelled) { setAllCerts(data); setCertsLoading(false); } })
      .catch((err: Error) => { if (!cancelled) { setFetchError(err.message); setCertsLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  // 모달 열림 동안 body 스크롤 잠금 + ESC 키로 닫기
  useEffect(() => {
    if (!showEvidence) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setShowEvidence(false); };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [showEvidence]);

  const riskId    = RISK_IDS[stageParam] ?? '';
  const riskLabel = RISK_LABEL[stageParam] ?? '';

  const filtered = useMemo(() => {
    const base = allCerts.filter(cert => {
      // 위험군은 항상 AND
      if (riskId && !cert.recommended_risk_stages.includes(riskId)) return false;
      // 도메인+직무 둘 다 지정되면 OR (로드맵과 동일 로직). 한쪽만이면 해당 조건만 AND.
      const domainOk = !domainParam || cert.related_domains.includes(domainParam) || cert.primary_domain === domainParam;
      const jobOk    = !jobParam    || cert.related_jobs.includes(jobParam);
      if (domainParam && jobParam) {
        if (!domainOk && !jobOk) return false;
      } else {
        if (!domainOk || !jobOk) return false;
      }
      if (selectedGrade && cert.cert_grade_tier !== selectedGrade) return false;
      const q = deferredQuery;
      if (q) {
        const ql = q.toLowerCase();
        const hit =
          cert.cert_name.toLowerCase().includes(ql) ||
          (cert.issuer ?? '').toLowerCase().includes(ql) ||
          (DOMAIN_NAMES[cert.primary_domain] ?? '').toLowerCase().includes(ql) ||
          cert.related_domains.some(d => (DOMAIN_NAMES[d] ?? '').toLowerCase().includes(ql)) ||
          cert.related_jobs.some(j => (JOB_NAMES[j] ?? '').toLowerCase().includes(ql));
        if (!hit) return false;
      }
      return true;
    });
    // 기본 정렬: domain+job 동시 지정 시 both > domain > job 매칭 우선 노출
    const matchRank = (cert: CertCandidate): number => {
      if (!domainParam || !jobParam) return 0;
      const dOk = cert.related_domains.includes(domainParam) || cert.primary_domain === domainParam;
      const jOk = cert.related_jobs.includes(jobParam);
      if (dOk && jOk) return 0;
      if (dOk) return 1;
      if (jOk) return 2;
      return 3;
    };
    if (sortBy === 'default' && domainParam && jobParam) {
      return [...base].sort((a, b) => matchRank(a) - matchRank(b));
    }
    // 도메인만 선택 시 주 도메인 자격증 우선, 관련 도메인 자격증 후순위
    if (sortBy === 'default' && domainParam && !jobParam) {
      return [...base].sort((a, b) => {
        const aPrimary = a.primary_domain === domainParam ? 0 : 1;
        const bPrimary = b.primary_domain === domainParam ? 0 : 1;
        return aPrimary - bPrimary;
      });
    }
    if (sortBy === 'default') return base;
    return [...base].sort((a, b) => {
      if (sortBy === 'passrate_desc') {
        const ar = a.avg_pass_rate_3yr ?? -1;
        const br = b.avg_pass_rate_3yr ?? -1;
        return br - ar;
      }
      if (sortBy === 'grade_desc') {
        const g = (t: string) => parseInt(t.charAt(0), 10) || 0;
        return g(b.cert_grade_tier) - g(a.cert_grade_tier);
      }
      if (sortBy === 'name_asc') {
        return a.cert_name.localeCompare(b.cert_name, 'ko');
      }
      return 0;
    });
  }, [allCerts, riskId, domainParam, jobParam, selectedGrade, deferredQuery, sortBy]);

  const featuredCert = useMemo(
    () => allCerts.find(c => c.cert_id === certIdParam) ?? null,
    [allCerts, certIdParam],
  );

  const fetchEvidence = useCallback(async (certId: string) => {
    // Check cache — instant response for repeat clicks
    const cachedEvidence = evidenceCacheRef.current[certId];
    const hasExplainCache = certId in certExplainCacheRef.current;
    const cachedExplain   = certExplainCacheRef.current[certId];

    startTransition(() => {
      if (cachedEvidence) {
        setEvidence({ loading: false, rows: cachedEvidence, error: null, fetched: true, certId });
      } else {
        setEvidence({ loading: true, rows: [], error: null, fetched: false, certId });
      }
      setShowEvidence(true);
      if (hasExplainCache) {
        setCertExplain({ loading: false, text: cachedExplain ?? null, certId, error: null });
      } else {
        setCertExplain({ loading: true, text: null, certId, error: null });
      }
    });

    fetchExecData(certId);

    // Auto-fetch all certinfo sections so user doesn't need to click tabs
    fetchCertInfo(certId);
    fetchCertStats(certId);
    fetchSessionRates(certId);
    // certJobs / fallback training needs cert name — look up from candidates
    const certName_ = allCerts.find(c => c.cert_id === certId)?.cert_name ?? '';
    if (certName_) {
      fetchCertJobs(certId, certName_);
      fetchJobLearner(certId, certName_);
      fetchProcessEval(certId, certName_);
    }

    // Fire AI explanation in parallel only if not cached
    if (!hasExplainCache) {
      fetch('/api/v1/recommendations/cert_explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cert_id: certId,
          domain_id: domainParam || '',
          risk_stage_id: RISK_IDS[stageParam] || '',
        }),
      }).then(r => r.json()).then(json => {
        const explanation = json.success ? (json.data?.explanation ?? null) : null;
        certExplainCacheRef.current[certId] = explanation;
        setCertExplain({ loading: false, text: explanation, certId, error: null });
      }).catch(() => {
        certExplainCacheRef.current[certId] = null;
        setCertExplain({ loading: false, text: null, certId, error: null });
      });
    }

    if (cachedEvidence) return; // already shown from cache

    try {
      const res = await fetch('/api/v1/recommendations/evidence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cert_id: certId }),
      });
      const json = await res.json();
      if (json.success) {
        const rows: EvidenceRow[] = json.data?.evidence ?? [];
        evidenceCacheRef.current[certId] = rows;
        setEvidence({ loading: false, rows, error: null, fetched: true, certId });
      } else {
        setEvidence({ loading: false, rows: [], error: json.error?.message ?? '오류 발생', fetched: true, certId });
      }
    } catch {
      setEvidence({ loading: false, rows: [], error: '서버에 연결할 수 없습니다.', fetched: true, certId });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageParam, domainParam, allCerts]);

  const fetchDag = useCallback(async (certId: string) => {
    const cached = dagCacheRef.current[certId];
    if (cached) {
      setDag({ loading: false, predecessors: cached.predecessors, successors: cached.successors, certId, fetched: true });
      return;
    }
    setDag({ loading: true, predecessors: [], successors: [], certId, fetched: false });
    try {
      const res = await fetch(`/api/v1/recommendations/related?cert_id=${encodeURIComponent(certId)}`);
      const json = await res.json();
      if (json.success) {
        const predecessors: RelatedCert[] = json.data?.predecessors ?? [];
        const successors: RelatedCert[]   = json.data?.successors ?? [];
        dagCacheRef.current[certId] = { predecessors, successors };
        setDag({ loading: false, predecessors, successors, certId, fetched: true });
      } else {
        dagCacheRef.current[certId] = { predecessors: [], successors: [] };
        setDag({ loading: false, predecessors: [], successors: [], certId, fetched: true });
      }
    } catch {
      setDag({ loading: false, predecessors: [], successors: [], certId, fetched: true });
    }
  }, []);

  const fetchVideos = useCallback(async (certId: string, certName: string) => {
    setVideos({
      loading: true, videos: [], error: null, warning: null, fetched: false,
      certId, certName, cacheHit: false,
    });
    try {
      const res = await fetch(`/api/v1/certs/${encodeURIComponent(certId)}/videos`);
      const json = await res.json();
      if (json.success) {
        setVideos({
          loading: false,
          videos: json.data?.videos ?? [],
          error: null,
          warning: json.data?.warning ?? null,
          fetched: true,
          certId,
          certName: json.data?.cert_name ?? certName,
          cacheHit: !!json.data?.cache_hit,
        });
      } else {
        setVideos({
          loading: false, videos: [],
          error: json.error?.message ?? '동영상을 불러올 수 없습니다.',
          warning: null, fetched: true, certId, certName, cacheHit: false,
        });
      }
    } catch {
      setVideos({
        loading: false, videos: [],
        error: '서버에 연결할 수 없습니다.',
        warning: null, fetched: true, certId, certName, cacheHit: false,
      });
    }
  }, []);

  const fetchExecData = useCallback(async (certId: string) => {
    const cached = execCacheRef.current[certId];
    if (cached) {
      setExec(prev => ({ ...prev, ...cached, loading: false, certId, fetched: true, activeTab: 'schedule' }));
      return;
    }
    setExec(prev => ({
      ...prev, loading: true, certId, fetched: false, activeTab: 'schedule',
      jobLearnerFetched: false, jobLearnerLoading: false, jobLearnerItems: [],
      certJobsFetched: false, certJobsLoading: false, certJobsList: [],
      canonicalRoles: [], relatedMajors: [],
      selectedJobName: null, jobDetailData: null, jobDetailLoading: false,
      processEvalFetched: false, processEvalLoading: false, processEvalItems: [],
      certInfoData: null, certInfoLoading: false, certInfoFetched: false,
      certStatsData: null, certStatsLoading: false, certStatsFetched: false,
      sessionRatesData: null, sessionRatesLoading: false, sessionRatesFetched: false,
    }));
    const [schedRes, jobsRes, trainRes] = await Promise.allSettled([
      fetch(`/api/v1/schedules/exams/${encodeURIComponent(certId)}`).then(r => r.json()),
      fetch(`/api/v1/jobs/hiring/by-cert/${encodeURIComponent(certId)}?display=5`).then(r => r.json()),
      fetch(`/api/v1/training/courses/by-cert/${encodeURIComponent(certId)}?page_size=5`).then(r => r.json()),
    ]);
    const schedData = schedRes.status === 'fulfilled' && schedRes.value.success ? schedRes.value.data : null;
    const jobsData  = jobsRes.status === 'fulfilled'  && jobsRes.value.success  ? jobsRes.value.data  : null;
    const trainData = trainRes.status === 'fulfilled' && trainRes.value.success ? trainRes.value.data : null;
    const execResult = {
      schedule:      (schedData?.schedules ?? []).slice(0, 4),
      hiringTotal:   jobsData?.total  ?? 0,
      hiringItems:   (jobsData?.jobs ?? []).slice(0, 5),
      trainingTotal: trainData?.total ?? 0,
      trainingItems: (trainData?.courses ?? []).slice(0, 5),
    };
    execCacheRef.current[certId] = execResult;
    setExec(prev => ({ ...prev, ...execResult, loading: false, certId, fetched: true }));
  }, []);

  const fetchCertInfo = useCallback(async (certId: string) => {
    const hasCached = certId in certInfoCacheRef.current;
    if (hasCached) {
      setExec(prev => ({ ...prev, certInfoData: certInfoCacheRef.current[certId] ?? null, certInfoLoading: false, certInfoFetched: true }));
      return;
    }
    setExec(prev => ({ ...prev, certInfoLoading: true, certInfoFetched: false }));
    try {
      const res = await fetch(`/api/v1/certs/${encodeURIComponent(certId)}/full-info`);
      const json = await res.json();
      const data: CertInfoData | null = json.success
        ? { info: json.data?.info ?? null, exam_info: json.data?.exam_info ?? null }
        : null;
      certInfoCacheRef.current[certId] = data;
      setExec(prev => ({ ...prev, certInfoData: data, certInfoLoading: false, certInfoFetched: true }));
    } catch {
      certInfoCacheRef.current[certId] = null;
      setExec(prev => ({ ...prev, certInfoData: null, certInfoLoading: false, certInfoFetched: true }));
    }
  }, []);

  const fetchCertStats = useCallback(async (certId: string) => {
    if (certId in certStatsCacheRef.current) {
      setExec(prev => ({ ...prev, certStatsData: certStatsCacheRef.current[certId] ?? null, certStatsLoading: false, certStatsFetched: true }));
      return;
    }
    setExec(prev => ({ ...prev, certStatsLoading: true, certStatsFetched: false }));
    try {
      const res = await fetch(`/api/v1/certs/${encodeURIComponent(certId)}/stats`);
      const json = await res.json();
      const data: CertStatsData | null = json.success ? {
        written_avg_pass_rate: json.data?.written_avg_pass_rate ?? null,
        practical_avg_pass_rate: json.data?.practical_avg_pass_rate ?? null,
        avg_pass_rate_3yr: json.data?.avg_pass_rate_3yr ?? null,
        exam_frequency: json.data?.exam_frequency ?? null,
        exam_difficulty: json.data?.exam_difficulty ?? null,
        exam_type_info: json.data?.exam_type_info ?? null,
        exam_subject_info: json.data?.exam_subject_info ?? null,
      } : null;
      certStatsCacheRef.current[certId] = data;
      setExec(prev => ({ ...prev, certStatsData: data, certStatsLoading: false, certStatsFetched: true }));
    } catch {
      certStatsCacheRef.current[certId] = null;
      setExec(prev => ({ ...prev, certStatsData: null, certStatsLoading: false, certStatsFetched: true }));
    }
  }, []);

  const sessionRatesCacheRef = useRef<Record<string, SessionRatesData | null>>({});
  const fetchSessionRates = useCallback(async (certId: string) => {
    if (certId in sessionRatesCacheRef.current) {
      setExec(prev => ({ ...prev, sessionRatesData: sessionRatesCacheRef.current[certId] ?? null, sessionRatesLoading: false, sessionRatesFetched: true }));
      return;
    }
    setExec(prev => ({ ...prev, sessionRatesLoading: true, sessionRatesFetched: false }));
    try {
      const res = await fetch(`/api/v1/certs/${encodeURIComponent(certId)}/session-rates`);
      const json = await res.json();
      const data: SessionRatesData | null = json.success ? {
        written: json.data?.written ?? [],
        practical: json.data?.practical ?? [],
        other: json.data?.other ?? [],
        total: json.data?.total ?? 0,
      } : null;
      sessionRatesCacheRef.current[certId] = data;
      setExec(prev => ({ ...prev, sessionRatesData: data, sessionRatesLoading: false, sessionRatesFetched: true }));
    } catch {
      sessionRatesCacheRef.current[certId] = null;
      setExec(prev => ({ ...prev, sessionRatesData: null, sessionRatesLoading: false, sessionRatesFetched: true }));
    }
  }, []);

  const fetchJobDetail = useCallback(async (jobName: string) => {
    setExec(prev => ({
      ...prev,
      selectedJobName: prev.selectedJobName === jobName ? null : jobName,
      jobDetailData: null,
      jobDetailLoading: prev.selectedJobName !== jobName,
    }));
    if (exec.selectedJobName === jobName) return; // toggle off
    try {
      const res = await fetch(`/api/v1/jobs/info/${encodeURIComponent(jobName)}`);
      const json = await res.json();
      if (json.success && json.data?.job) {
        setExec(prev => ({ ...prev, jobDetailData: json.data.job, jobDetailLoading: false }));
      } else {
        setExec(prev => ({ ...prev, jobDetailLoading: false }));
      }
    } catch {
      setExec(prev => ({ ...prev, jobDetailLoading: false }));
    }
  }, [exec.selectedJobName]);

  const fetchJobLearner = useCallback(async (certId: string, certName: string) => {
    const cached = jobLearnerCacheRef.current[certId];
    if (cached) {
      setExec(prev => ({ ...prev, jobLearnerItems: cached, jobLearnerLoading: false, jobLearnerFetched: true }));
      return;
    }
    setExec(prev => ({ ...prev, jobLearnerLoading: true, jobLearnerFetched: false }));
    try {
      const res = await fetch(`/api/v1/training/job-learner?keyword=${encodeURIComponent(certName)}&page_size=5`);
      const json = await res.json();
      const items: JobLearnerItem[] = json.success ? (json.data?.items ?? []).slice(0, 5) : [];
      jobLearnerCacheRef.current[certId] = items;
      setExec(prev => ({ ...prev, jobLearnerItems: items, jobLearnerLoading: false, jobLearnerFetched: true }));
    } catch {
      jobLearnerCacheRef.current[certId] = [];
      setExec(prev => ({ ...prev, jobLearnerItems: [], jobLearnerLoading: false, jobLearnerFetched: true }));
    }
  }, []);

  const fetchProcessEval = useCallback(async (certId: string, certName: string) => {
    const cached = processEvalCacheRef.current[certId];
    if (cached) {
      setExec(prev => ({ ...prev, processEvalItems: cached, processEvalLoading: false, processEvalFetched: true }));
      return;
    }
    setExec(prev => ({ ...prev, processEvalLoading: true, processEvalFetched: false }));
    try {
      const res = await fetch(`/api/v1/training/process-eval?keyword=${encodeURIComponent(certName)}&page_size=5`);
      const json = await res.json();
      const items = json.success ? (json.data?.courses ?? json.data?.items ?? []).slice(0, 5) : [];
      processEvalCacheRef.current[certId] = items;
      setExec(prev => ({ ...prev, processEvalItems: items, processEvalLoading: false, processEvalFetched: true }));
    } catch {
      processEvalCacheRef.current[certId] = [];
      setExec(prev => ({ ...prev, processEvalItems: [], processEvalLoading: false, processEvalFetched: true }));
    }
  }, []);

  const fetchCertJobs = useCallback(async (certId: string, certName: string) => {
    const cached = certJobsCacheRef.current[certId];
    if (cached) {
      setExec(prev => ({
        ...prev,
        certJobsList: cached.jobs,
        canonicalRoles: cached.canonicalRoles,
        relatedMajors: cached.relatedMajors,
        certJobsLoading: false,
        certJobsFetched: true,
      }));
      return;
    }
    setExec(prev => ({ ...prev, certJobsLoading: true, certJobsFetched: false }));
    try {
      const res = await fetch(`/api/v1/jobs/cert-jobs/${encodeURIComponent(certName)}`);
      const json = await res.json();
      const jobs: string[] = json.success ? (json.data?.jobs ?? []) : [];
      const canonicalRoles: ExecState['canonicalRoles'] = json.success ? (json.data?.canonical_roles ?? []) : [];
      const relatedMajors: string[] = json.success ? (json.data?.related_majors ?? []) : [];
      certJobsCacheRef.current[certId] = { jobs, canonicalRoles, relatedMajors };
      setExec(prev => ({ ...prev, certJobsList: jobs, canonicalRoles, relatedMajors, certJobsLoading: false, certJobsFetched: true }));
    } catch {
      certJobsCacheRef.current[certId] = { jobs: [], canonicalRoles: [], relatedMajors: [] };
      setExec(prev => ({ ...prev, certJobsList: [], canonicalRoles: [], relatedMajors: [], certJobsLoading: false, certJobsFetched: true }));
    }
  }, []);

  const fromParam = searchParams.get('from') || '';
  const goToRoadmap = useCallback((certId: string) => {
    const p = new URLSearchParams();
    if (fromParam)   p.set('from', fromParam);
    if (stageParam)  p.set('stage', stageParam);
    if (domainParam) p.set('domain', domainParam);
    if (domainName)  p.set('domainName', domainName);
    p.set('cert', certId);
    navigate(`/roadmap?${p.toString()}`);
  }, [fromParam, stageParam, domainParam, domainName, navigate]);

  const evidenceCertName = allCerts.find(c => c.cert_id === evidence.certId)?.cert_name ?? evidence.certId;

  const isSurveyIncomplete = !stageParam && !domainParam;

  return (
    <div className="rec-wrap">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} /> 뒤로
        </button>
        <h1 className="page-title">자격증 확인</h1>
        <p className="page-desc">
          {domainName && riskLabel
            ? <><strong>{domainName}</strong>{jobName ? <> + <strong>{jobName}</strong></> : ''} 분야에서 <strong>{riskLabel}</strong>에 맞는 자격증을 골랐습니다.</>
            : domainName
              ? <><strong>{domainName}</strong>{jobName ? <> + <strong>{jobName}</strong></> : ''} 분야 추천 자격증입니다.</>
              : '추천 자격증을 확인하세요.'}
        </p>
      </div>

      {isSurveyIncomplete && (
        <div className="survey-required-banner">
          <AlertCircle size={20} className="survey-required-icon" />
          <div className="survey-required-body">
            <p className="survey-required-title">AI 추천을 받을 수 없습니다</p>
            <p className="survey-required-sub">위험군 진단과 관심 분야를 먼저 설정해야 맞춤 자격증 추천을 받을 수 있습니다.</p>
          </div>
          <button className="btn-primary survey-required-btn" onClick={() => navigate('/risk-assessment')}>
            진단 시작하기
          </button>
        </div>
      )}

      {featuredCert && (
        <div
          className={`featured-cert card${evidence.certId === featuredCert.cert_id && showEvidence ? ' featured-cert-active' : ''}`}
          style={{ borderLeftColor: gradeColor(featuredCert.cert_grade_tier), cursor: 'pointer' }}
          onClick={() => { fetchEvidence(featuredCert.cert_id); fetchDag(featuredCert.cert_id); }}
          role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') { fetchEvidence(featuredCert.cert_id); fetchDag(featuredCert.cert_id); } }}
        >
          <div className="featured-tag-row"><span className="featured-tag">로드맵에서 선택</span></div>
          <div className="featured-body">
            <span className={`badge ${gradeBadgeClass(featuredCert.cert_grade_tier)}`}>
              {GRADE_LABEL[featuredCert.cert_grade_tier] ?? featuredCert.cert_grade_tier}
            </span>
            <h2 className="featured-name">{featuredCert.cert_name}</h2>
            <p className="featured-issuer">{featuredCert.issuer}</p>
            <p className="featured-summary">{buildCertSummary(featuredCert)}</p>
          </div>
          <div className="featured-actions">
            <button className="btn-primary" onClick={(e) => { e.stopPropagation(); fetchEvidence(featuredCert.cert_id); fetchDag(featuredCert.cert_id); }}>
              <FileText size={15} /> 왜 추천됐나요
            </button>
            <button className="btn-ghost" onClick={(e) => { e.stopPropagation(); goToRoadmap(featuredCert.cert_id); }}>
              <Map size={15} /> 로드맵 보기
            </button>
          </div>
        </div>
      )}

      {showEvidence && (
        <div className="modal-backdrop" onClick={() => setShowEvidence(false)} role="presentation">
        <div className="evidence-modal modal-card card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
          <div className="ev-header">
            <div className="ev-header-left">
              <BookOpen size={15} style={{ color: 'var(--primary)', flexShrink: 0 }} />
              <span className="ev-title">{evidenceCertName}을 추천하는 이유</span>
            </div>
            <button className="ev-close" onClick={() => setShowEvidence(false)} aria-label="닫기"><X size={15} /></button>
          </div>
          <div className="evidence-panel">

          {/* AI 추천 이유 — 패널 최상단의 핵심 결론 */}
          {certExplain.certId === evidence.certId && (certExplain.loading || certExplain.text) && (
            <div className="ai-reasoning-card">
              <div className="ai-reasoning-header">
                <Sparkles size={18} className="ai-reasoning-icon" />
                <span className="ai-reasoning-label">AI가 분석한 추천 이유</span>
                <span className="ai-reasoning-badge">핵심 분석</span>
              </div>
              {certExplain.loading ? (
                <div className="ai-reasoning-loading">
                  <Loader2 size={15} className="ev-spin" />
                  <span>{evidenceCertName}을 분석 중…</span>
                </div>
              ) : (
                <p className="ai-reasoning-text">{certExplain.text}</p>
              )}
            </div>
          )}

          {/* DAG 경로 */}
          {dag.fetched && (dag.predecessors.length > 0 || dag.successors.length > 0) && (
            <div className="dag-panel">
              <p className="dag-panel-title">이 자격증과 연결된 경로</p>
              <div className="dag-flow-scroll">
                <CertFlowDiagram
                  current={{ cert_id: dag.certId, cert_name: evidenceCertName }}
                  predecessors={dag.predecessors}
                  successors={dag.successors}
                  onNodeClick={(id) => { fetchEvidence(id); fetchDag(id); }}
                />
              </div>
            </div>
          )}

          {/* Evidence 섹션 */}
          {evidence.loading && (
            <div className="ev-loading"><Loader2 size={18} className="ev-spin" /><span>관련 자료를 찾는 중…</span></div>
          )}
          {!evidence.loading && evidence.error && (
            <div className="ev-empty"><AlertCircle size={16} style={{ flexShrink: 0 }} /><span>{evidence.error}</span></div>
          )}
          {!evidence.loading && evidence.fetched && evidence.rows.length === 0 && !evidence.error && (
            <div className="ev-empty">
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>아직 연결된 공식 자료가 없습니다.</span>
            </div>
          )}
          {!evidence.loading && evidence.rows.length > 0 && (
            <div className="ev-list">
              <div className="ev-supporting-header">
                <FileText size={14} />
                <span className="ev-supporting-title">참고 자료</span>
                <span className="ev-supporting-sub">공식 문서에서 가져온 보조 근거입니다</span>
              </div>
              {[...evidence.rows].sort((a, b) => {
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
              }).map((row, i) => {
                const sec = row.section_path?.[0] ?? '';
                const isGasanjeom = row.source_type === 'gasanjeom' || row.source_type === 'gasanjeom_inferred';
                const isNational = row.source_type === 'national_cert_catalog';
                const isPrivate  = row.source_type === 'private_cert_catalog';
                const isCatalog  = isNational || isPrivate;
                const isCareer   = sec === '진로(자격활용)' || sec === '자격 활용 현황';
                const isIntro    = sec === '도입목적';
                const isExamInfo = sec === '시험 정보' || sec.includes('합격률') || sec.includes('난이도');
                const snippetLines = (isPrivate && row.snippet.includes('\n'))
                  ? row.snippet.split('\n').filter(Boolean)
                  : null;
                // 공무원 가산점
                if (isGasanjeom || sec === '가산점') {
                  const isInferred = row.source_type === 'gasanjeom_inferred';
                  return (
                    <div key={row.chunk_id || i} className="ev-gasanjeom">
                      <span className="ev-gasanjeom-label">{isInferred ? '가산점 참고' : '공무원 가산점'}</span>
                      <p className="ev-gasanjeom-text">{row.snippet}</p>
                    </div>
                  );
                }
                // 자격증 소개 — 도입목적 → 전용 intro 박스
                if (isIntro) {
                  return (
                    <div key={row.chunk_id || i} className="ev-intro-box">
                      <span className="ev-intro-label">자격증 소개</span>
                      <p className="ev-intro-text">{row.snippet}</p>
                    </div>
                  );
                }
                // 자격 활용 — 진로(자격활용) / 자격 활용 현황
                if (isCareer) {
                  const careerText = row.snippet.replace(/^진로\(자격활용\):\s*/, '');
                  return (
                    <div key={row.chunk_id || i} className="ev-career-box">
                      <span className="ev-career-label">자격 활용</span>
                      {snippetLines && snippetLines.length > 1 ? (
                        <ul className="ev-catalog-list">
                          {snippetLines.map((line, li) => (
                            <li key={li}>{line.replace(/^\+\s*/, '')}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="ev-career-text">{careerText}</p>
                      )}
                    </div>
                  );
                }
                // 시험 정보 — pill 배지 방식
                if (isExamInfo) {
                  // 정규화된 형식("A · B · C") vs 구형식("시험 난이도: 3.0. ...")
                  let pills: string[];
                  if (row.snippet.includes(' · ')) {
                    pills = row.snippet.split(' · ').filter(Boolean);
                  } else {
                    // 구형 Supabase 데이터: 필드별 파싱
                    const rawPills: string[] = [];
                    const diffLabels: Record<string, string> = {
                      '1':'하 (쉬움)','1.0':'하 (쉬움)','1.5':'중하','2':'중하','2.0':'중하',
                      '2.5':'중','3':'중 (보통)','3.0':'중 (보통)','3.5':'중상',
                      '4':'중상','4.0':'중상','4.5':'상','5':'상 (어려움)','5.0':'상 (어려움)',
                    };
                    const dm2 = row.snippet.match(/시험 난이도:\s*(\d+(?:\.\d+)?)/);
                    if (dm2) rawPills.push(`난이도: ${diffLabels[dm2[1]] ?? dm2[1]}`);
                    const pm2 = row.snippet.match(/3년 평균 합격률:\s*([\d.]+)/);
                    if (pm2) rawPills.push(`합격률: ${Math.round(parseFloat(pm2[1]))}%`);
                    const fm2 = row.snippet.match(/연간 검정 횟수:\s*([^.\n]+)/);
                    if (fm2) rawPills.push(`연간 시험: ${fm2[1].trim()}`);
                    pills = rawPills.length ? rawPills : [row.snippet];
                  }
                  return (
                    <div key={row.chunk_id || i} className="ev-exam-section">
                      <span className="ev-exam-section-label">시험 정보</span>
                      <div className="ev-exam-row">
                        {pills.map((p, pi) => (
                          <span key={pi} className="ev-exam-pill">{p}</span>
                        ))}
                      </div>
                    </div>
                  );
                }
                // 검정 현황 — PDF 표 raw 데이터 → 파싱 후 테이블 카드 렌더링
                if (sec === '검정 현황' || sec.includes('검정 현황')) {
                  // ── Step 1: 연도 붙여쓰기 복원 ──
                  const cleaned = row.snippet
                    .replace(/(\d)\s(\d)\s(\d)\s(\d)/g, '$1$2$3$4')
                    .replace(/(\d)\s(\d)\s(\d)\s(\d)/g, '$1$2$3$4');

                  // ── Step 2: 연도 추출 ──
                  const yearMatches = [...cleaned.matchAll(/20[2-9]\d/g)].map(m => m[0]);
                  const years = [...new Set(yearMatches)].sort();

                  // ── Step 3: 급수/레벨 라벨 추출 ──
                  const LEVEL_RE = /(기술사|기능장|기사|산업기사|기능사|전문가|개발자|준전문가|특급|고급|중급|초급|1급|2급|3급|A급|B급|C급|필기|실기)/g;
                  const allLvl = [...cleaned.matchAll(LEVEL_RE)].map(m => m[0]);
                  const seenL = new Set<string>();
                  const levels: string[] = [];
                  for (const l of allLvl) { if (!seenL.has(l)) { seenL.add(l); levels.push(l); } }

                  // ── Step 4: 합격률 소수 추출 (≤100만 유효) ──
                  const rates: string[] = [...cleaned.matchAll(/\b(\d{1,2}\.\d+)\b/g)]
                    .map(m => m[1]).filter(n => parseFloat(n) <= 100);

                  // ── Step 5: "응시자" 이후 텍스트에서만 정수 추출 (설명문 오염 방지) ──
                  // 설명문에 "75점", "40%" 같은 숫자가 섞여 allCounts가 오염되는 버그 수정
                  const tblMarkers = ['응시자 합격자', '응시자', '합격자'];
                  let tblSection = cleaned;
                  for (const mk of tblMarkers) {
                    const idx = cleaned.indexOf(mk);
                    if (idx >= 0) { tblSection = cleaned.slice(idx + mk.length); break; }
                  }
                  const tblCounts: string[] = [];
                  const tcRe = /\b([\d,]+)\b/g;
                  let tc: RegExpExecArray | null;
                  while ((tc = tcRe.exec(tblSection)) !== null) {
                    const raw = tc[1].replace(/,/g, '');
                    const n = parseInt(raw, 10);
                    if (!isNaN(n) && raw.length >= 2 && !(raw.length === 4 && n >= 2020 && n <= 2030)) {
                      tblCounts.push(tc[1]);
                    }
                  }

                  // ── 헬퍼: sanity check (합격자 ≤ 응시자, 합격률 ≤ 100) ──
                  type ExamRow = { year: string; level: string; applicants: string; passed: string; rate: string };
                  type StatRow = { label: string; applicants: string; passed: string; rate: string };
                  const isValidRow = (app: string, pass: string, rate: string) => {
                    const a = parseInt(app.replace(/,/g, ''), 10);
                    const p = parseInt(pass.replace(/,/g, ''), 10);
                    const r = parseFloat(rate);
                    if (!isNaN(a) && !isNaN(p) && p > a) return false;
                    if (!isNaN(r) && r > 100) return false;
                    return true;
                  };

                  // ── Step 6: 열 방향(column-major) 파싱 — 최우선 시도 ──
                  // 구조: (응시자×nC) → (합격자×nC) → (합격률×nC)  (nC = nYears × nLevels)
                  let colMajorRows: ExamRow[] = [];
                  if (years.length > 0 && levels.length > 0 && rates.length > 0) {
                    const nC = rates.length;                          // 연도×급수 조합 수
                    const nLevels = nC / years.length;                // 급수 수 추론
                    if (Number.isInteger(nLevels) && nLevels <= levels.length
                        && tblCounts.length === nC * 2) {
                      const usedLevels = levels.slice(0, nLevels);
                      const candidate: ExamRow[] = [];
                      for (let ci = 0; ci < nC; ci++) {
                        candidate.push({
                          year:       years[Math.floor(ci / nLevels)],
                          level:      usedLevels[ci % nLevels],
                          applicants: tblCounts[ci]        ?? '-',
                          passed:     tblCounts[nC + ci]   ?? '-',
                          rate:       parseFloat(rates[ci]).toFixed(1),
                        });
                      }
                      // 전체 행 sanity check 통과 시만 채택
                      if (candidate.every(r => isValidRow(r.applicants, r.passed, r.rate))) {
                        colMajorRows = candidate;
                      }
                    }
                  }

                  // ── Step 7: 연도별 1행 형식 (단일 급수, 연도=행 라벨) ──
                  let yearRows: StatRow[] = [];
                  if (colMajorRows.length === 0 && years.length > 0
                      && rates.length === years.length
                      && tblCounts.length === years.length * 2) {
                    const candidate = years.map((yr, yi) => ({
                      label:      `${yr}년`,
                      applicants: tblCounts[yi]               ?? '-',
                      passed:     tblCounts[years.length + yi] ?? '-',
                      rate:       parseFloat(rates[yi]).toFixed(1),
                    }));
                    if (candidate.every(r => isValidRow(r.applicants, r.passed, r.rate))) {
                      yearRows = candidate;
                    }
                  }

                  // ── Step 7.5: Transposed format — years as column headers ──
                  // Handles: "연도 2022 2023 2024  응시자 A B C  합격자 D E F  합격률(%) R1 R2 R3"
                  let transposedRows: StatRow[] = [];
                  if (colMajorRows.length === 0 && yearRows.length === 0 && years.length >= 2) {
                    const appM = cleaned.match(/응시자\s+((?:[\d,]+\s+){1,6})/);
                    const passM = cleaned.match(/합격자\s+((?:[\d,]+\s+){1,6})/);
                    const rateM = cleaned.match(/합격률[^0-9]+((?:[\d.]+\s*){1,6})/);
                    if (appM && passM) {
                      const appNums = (appM[1].match(/[\d,]+/g) ?? []).slice(0, years.length);
                      const passNums = (passM[1].match(/[\d,]+/g) ?? []).slice(0, years.length);
                      const rateNums = rateM ? (rateM[1].match(/[\d.]+/g) ?? []).slice(0, years.length) : [];
                      if (appNums.length === years.length && passNums.length === years.length) {
                        const candidate = years.map((yr, yi) => ({
                          label: `${yr}년`, applicants: appNums[yi], passed: passNums[yi],
                          rate: rateNums[yi] ? parseFloat(rateNums[yi]).toFixed(1) : '-',
                        }));
                        if (candidate.every(r => isValidRow(r.applicants, r.passed, r.rate))) {
                          transposedRows = candidate;
                        }
                      }
                    }
                  }

                  // ── Step 8: 행 방향(row-major) 파싱 — sanity check 포함 ──
                  let rowMajorRows: StatRow[] = [];
                  if (colMajorRows.length === 0 && yearRows.length === 0 && transposedRows.length === 0) {
                    const rowPat = /(기술사|기능장|기사|산업기사|기능사|전문가|개발자|준전문가|특급|고급|중급|초급|1급|2급|3급|A급|B급|C급|필기|실기|[가-힣\d]+차시?)\s+([\d,]+)\s+([\d,]+|-)\s*([\d.]+)?/g;
                    let rm: RegExpExecArray | null;
                    while ((rm = rowPat.exec(cleaned)) !== null) {
                      const rateStr = rm[4] ?? '-';
                      if (!isValidRow(rm[2], rm[3], rateStr === '-' ? '0' : rateStr)) continue;
                      rowMajorRows.push({ label: rm[1], applicants: rm[2], passed: rm[3], rate: rateStr });
                    }
                  }

                  // ── 공통 헤더 렌더 ──
                  const statsHeader = (
                    <div className="ev-row-header">
                      <span className="ev-section-label">{sec}</span>
                      {isCatalog && (
                        <span className={`ev-src-tag ${isNational ? 'ev-src-national' : 'ev-src-catalog'}`}>
                          {isNational ? '국가자격' : '공인민간자격'}
                        </span>
                      )}
                      {row.source_url && (
                        <a href={row.source_url} target="_blank" rel="noreferrer" className="ev-link">
                          <ExternalLink size={11} /> 원문 보기
                        </a>
                      )}
                    </div>
                  );

                  return (
                    <div key={row.chunk_id || i} className="ev-row ev-row-stats">
                      {statsHeader}

                      {/* 열 방향 (year × level 조합) */}
                      {colMajorRows.length > 0 && (
                        <div className="ev-stats-table-wrap">
                          {years.map(yr => {
                            const yRows = colMajorRows.filter(r => r.year === yr);
                            return (
                              <div key={yr} className="ev-stats-year-block">
                                <div className="ev-stats-year-head">{yr}년</div>
                                <table className="ev-stats-table">
                                  <thead><tr><th>급수</th><th>응시자</th><th>합격자</th><th>합격률(%)</th></tr></thead>
                                  <tbody>
                                    {yRows.map((r, ri) => (
                                      <tr key={ri}>
                                        <td className="ev-td-label">{r.level}</td>
                                        <td>{r.applicants}</td>
                                        <td>{r.passed}</td>
                                        <td className="ev-td-rate">{r.rate}%</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* 연도별 1행 형식 */}
                      {colMajorRows.length === 0 && yearRows.length > 0 && (
                        <div className="ev-stats-table-wrap">
                          <table className="ev-stats-table">
                            <thead><tr><th>연도</th><th>응시자</th><th>합격자</th><th>합격률(%)</th></tr></thead>
                            <tbody>
                              {yearRows.map((r, ri) => (
                                <tr key={ri}>
                                  <td className="ev-td-label">{r.label}</td>
                                  <td>{r.applicants}</td>
                                  <td>{r.passed}</td>
                                  <td className="ev-td-rate">{r.rate}%</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Transposed (연도=열) 형식 */}
                      {colMajorRows.length === 0 && yearRows.length === 0 && transposedRows.length > 0 && (
                        <div className="ev-stats-table-wrap">
                          <table className="ev-stats-table">
                            <thead>
                              <tr>
                                <th>구분</th>
                                {transposedRows.map(r => <th key={r.label}>{r.label}</th>)}
                              </tr>
                            </thead>
                            <tbody>
                              <tr><td className="ev-td-label">응시자</td>{transposedRows.map(r => <td key={r.label}>{r.applicants}</td>)}</tr>
                              <tr><td className="ev-td-label">합격자</td>{transposedRows.map(r => <td key={r.label}>{r.passed}</td>)}</tr>
                              <tr>
                                <td className="ev-td-label">합격률(%)</td>
                                {transposedRows.map(r => (
                                  <td key={r.label} className="ev-td-rate">{r.rate !== '-' ? `${r.rate}%` : '-'}</td>
                                ))}
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* 행 방향 (급수 라벨 inline) */}
                      {colMajorRows.length === 0 && yearRows.length === 0 && transposedRows.length === 0 && rowMajorRows.length > 0 && (
                        <div className="ev-stats-table-wrap">
                          {years.length > 0 && (
                            <div className="ev-stats-years">
                              {years.map(y => <span key={y} className="ev-stats-year-chip">{y}년</span>)}
                            </div>
                          )}
                          <table className="ev-stats-table">
                            <thead><tr><th>급수/차시</th><th>응시자</th><th>합격자</th><th>합격률(%)</th></tr></thead>
                            <tbody>
                              {rowMajorRows.map((r, ri) => (
                                <tr key={ri}>
                                  <td className="ev-td-label">{r.label}</td>
                                  <td>{r.applicants}</td>
                                  <td>{r.passed}</td>
                                  <td className="ev-td-rate">{r.rate !== '-' ? `${r.rate}%` : '-'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* 파싱 실패 fallback — 정제된 텍스트 */}
                      {colMajorRows.length === 0 && yearRows.length === 0 && transposedRows.length === 0 && rowMajorRows.length === 0 && (
                        <div className="ev-stats-fallback">
                          {years.length > 0 && (
                            <div className="ev-stats-years">
                              {years.map(y => <span key={y} className="ev-stats-year-chip">{y}년</span>)}
                              <span className="ev-stats-year-label">검정 현황 데이터</span>
                            </div>
                          )}
                          <p className="ev-stats-raw-text">{cleaned}</p>
                        </div>
                      )}

                      <p className="ev-stats-disclaimer">* PDF에서 자동 추출된 데이터입니다. 정확한 수치는 원문을 확인해 주세요.</p>
                    </div>
                  );
                }
                // 나머지 섹션 (직무·역할, 시험 과목, 응시료 등)
                return (
                  <div key={row.chunk_id || i} className={`ev-row${isCatalog ? ' ev-row-catalog' : ''}`}>
                    <div className="ev-row-header">
                      {sec && (
                        <span className="ev-section-label">{sec}</span>
                      )}
                      {isCatalog && (
                        <span className={`ev-src-tag ${isNational ? 'ev-src-national' : 'ev-src-catalog'}`}>
                          {isNational ? '국가자격' : '공인민간자격'}
                        </span>
                      )}
                      {row.source_url && (
                        <a href={row.source_url} target="_blank" rel="noreferrer" className="ev-link">
                          <ExternalLink size={11} /> 원문 보기
                        </a>
                      )}
                    </div>
                    {snippetLines && snippetLines.length > 1 ? (
                      <ul className="ev-catalog-list">
                        {snippetLines.map((line, li) => (
                          <li key={li}>{line.replace(/^\+\s*/, '')}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="ev-snippet">{row.snippet}</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* ── Execution Panel: 시험일정 / 채용정보 / 훈련과정 / 자격정보 (stacked) ── */}
          {exec.certId === evidence.certId && (
            <div className="exec-panel">
              {/* dummy tabs removed — sections always visible */}
              <div style={{display:'none'}}>
              </div>

              {exec.loading && (
                <div className="exec-loading"><Loader2 size={14} className="ev-spin" /> 실시간 정보 조회 중…</div>
              )}

              {/* ── 시험 일정 ── */}
              <div className="exec-section">
                <p className="exec-section-title">시험 일정</p>
                {!exec.loading && exec.fetched && (
                  exec.schedule.length === 0
                    ? <p className="exec-empty">현재 예정된 시험 일정이 없습니다.</p>
                    : <div className="exec-list">
                        {exec.schedule.map((s, i) => (
                          <div key={i} className="exec-sched-row">
                            <div className="exec-sched-left">
                              <span className="exec-sched-round">{s.impl_seq_name ?? '-'}</span>
                              <span className="exec-sched-period">
                                {s.registration_start ? `접수 ${s.registration_start}` : ''}
                                {s.registration_end ? `~${s.registration_end}` : ''}
                              </span>
                              {s.exam_start && (
                                <span className="exec-sched-exam">시험 {s.exam_start}{s.exam_end && s.exam_end !== s.exam_start ? `~${s.exam_end}` : ''}</span>
                              )}
                            </div>
                            <div className="exec-sched-right">
                              {s.d_day_registration !== null && s.d_day_registration <= 0 && (s.d_day_exam ?? 1) > 0 && (
                                <span className="exec-sched-reg-open">접수 중</span>
                              )}
                              {s.d_day_exam !== null && (
                                <span className={`exec-dday${s.d_day_exam <= 0 ? ' exec-dday-open' : s.d_day_exam <= 7 ? ' exec-dday-soon' : ''}`}>
                                  {s.d_day_exam === 0 ? 'D-Day' : s.d_day_exam < 0 ? '마감' : `D-${s.d_day_exam}`}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                )}
                {exec.fetched && evidenceCertName && (() => {
                  const qnetUrl = `https://www.q-net.or.kr/crf005.do?id=crf00501&gSite=Q&jmNm=${encodeURIComponent(evidenceCertName)}`;
                  return (
                    <a href={qnetUrl} target="_blank" rel="noreferrer" className="exec-qnet-btn">
                      <ExternalLink size={12} /> Q-Net 원서접수
                    </a>
                  );
                })()}
              </div>

              {/* ── 채용공고 ── */}
              <div className="exec-section">
                <p className="exec-section-title">채용공고</p>
                {!exec.loading && exec.fetched && (
                  exec.hiringItems.length === 0
                    ? <p className="exec-empty">현재 관련 채용공고를 찾지 못했습니다.</p>
                    : <div className="exec-list">
                        {exec.hiringItems.map((j, i) => (
                          <a key={i} href={j.url || '#'} target="_blank" rel="noreferrer" className="exec-job-row">
                            <div className="exec-job-main">
                              <span className="exec-job-title">{j.title}</span>
                              <span className="exec-job-company">{j.company}</span>
                            </div>
                            {j.close_date && <span className="exec-job-close">~{j.close_date}</span>}
                            <ExternalLink size={11} className="exec-job-icon" />
                          </a>
                        ))}
                      </div>
                )}
              </div>

              {/* ── 훈련과정 ── */}
              <div className="exec-section">
                <p className="exec-section-title">훈련과정</p>
                {!exec.loading && exec.fetched && (
                  exec.trainingItems.length > 0
                    ? <div className="exec-list">
                        {exec.trainingItems.map((t, i) => (
                          <div key={i} className="exec-train-row">
                            <div className="exec-train-main">
                              <span className="exec-train-name">{t.course_name}</span>
                              <span className="exec-train-org">{t.institution_name}</span>
                            </div>
                            {t.employment_rate && (
                              <span className="exec-train-rate">취업률 {t.employment_rate}%</span>
                            )}
                          </div>
                        ))}
                      </div>
                    : <div>
                        <p className="exec-empty">Work24 훈련과정을 찾지 못했습니다.</p>
                        {exec.jobLearnerLoading && (
                          <div className="exec-loading"><Loader2 size={14} className="ev-spin" /> 일학습병행 과정 조회 중…</div>
                        )}
                        {exec.jobLearnerFetched && exec.jobLearnerItems.length > 0 && (
                          <div className="exec-list">
                            <p className="exec-section-label">일학습병행 과정 (Q-Net)</p>
                            {exec.jobLearnerItems.map((item, i) => (
                              <div key={i} className="exec-train-row">
                                <div className="exec-train-main">
                                  <span className="exec-train-name">{String(item.itemNm ?? item.jmNm ?? '-')}</span>
                                  <span className="exec-train-org">{String(item.corpNm ?? '-')}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                        {exec.jobLearnerFetched && exec.jobLearnerItems.length === 0 && (
                          <p className="exec-empty">일학습병행 과정도 찾지 못했습니다.</p>
                        )}
                        {exec.processEvalLoading && (
                          <div className="exec-loading"><Loader2 size={14} className="ev-spin" /> 과정평가형 자격 조회 중…</div>
                        )}
                        {exec.processEvalFetched && exec.processEvalItems.length > 0 && (
                          <div className="exec-list">
                            <p className="exec-section-label">과정평가형 자격 (Work24)</p>
                            {exec.processEvalItems.map((item, i) => {
                              const name = String(item.jmNm ?? item.course_name ?? item.itemNm ?? '-');
                              const org = String(item.insttNm ?? item.institution_name ?? item.corpNm ?? '');
                              return (
                                <div key={i} className="exec-train-row">
                                  <div className="exec-train-main">
                                    <span className="exec-train-name">{name}</span>
                                    {org && <span className="exec-train-org">{org}</span>}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                )}
              </div>

              {/* ── 자격 정보 ── */}
              <div className="exec-section">
                <p className="exec-section-title">자격 정보</p>
                {exec.certInfoLoading
                  ? <div className="exec-loading"><Loader2 size={14} className="ev-spin" /> 자격정보 조회 중…</div>
                  : !exec.certInfoFetched
                    ? <p className="exec-empty">자격 정보를 불러오는 중입니다…</p>
                    : (!exec.certInfoData?.info && !exec.certInfoData?.exam_info && !exec.certStatsData)
                      ? <p className="exec-empty">이 자격증의 상세 정보를 찾지 못했습니다.</p>
                      : (
                        <div className="certinfo-wrap">
                          {exec.certInfoData?.info && (
                            <div className="certinfo-block">
                              <p className="certinfo-block-title">자격 기본 정보</p>
                              <div className="certinfo-grid">
                                {exec.certInfoData.info.qualification_type && (
                                  <div className="certinfo-row"><span className="certinfo-key">자격 구분</span><span className="certinfo-val">{exec.certInfoData.info.qualification_type}</span></div>
                                )}
                                {exec.certInfoData.info.eligibility && (
                                  <div className="certinfo-row"><span className="certinfo-key">응시자격</span><span className="certinfo-val">{exec.certInfoData.info.eligibility}</span></div>
                                )}
                                {exec.certInfoData.info.exam_fee_written && (
                                  <div className="certinfo-row"><span className="certinfo-key">필기 수수료</span><span className="certinfo-val">{exec.certInfoData.info.exam_fee_written}원</span></div>
                                )}
                                {exec.certInfoData.info.exam_fee_practical && (
                                  <div className="certinfo-row"><span className="certinfo-key">실기 수수료</span><span className="certinfo-val">{exec.certInfoData.info.exam_fee_practical}원</span></div>
                                )}
                                {exec.certInfoData.info.related_occupation && (
                                  <div className="certinfo-row"><span className="certinfo-key">관련 직업</span><span className="certinfo-val">{exec.certInfoData.info.related_occupation}</span></div>
                                )}
                                {exec.certInfoData.info.website && (
                                  <div className="certinfo-row"><span className="certinfo-key">공식 사이트</span>
                                    <a href={exec.certInfoData.info.website} target="_blank" rel="noreferrer" className="certinfo-link">{exec.certInfoData.info.website} <ExternalLink size={11} /></a>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                          {exec.certInfoData?.exam_info && (
                            <div className="certinfo-block">
                              <p className="certinfo-block-title">시험 정보</p>
                              <div className="certinfo-grid">
                                {exec.certInfoData.exam_info.written_subjects && (
                                  <div className="certinfo-row"><span className="certinfo-key">필기 과목</span><span className="certinfo-val">{exec.certInfoData.exam_info.written_subjects}</span></div>
                                )}
                                {exec.certInfoData.exam_info.practical_subjects && (
                                  <div className="certinfo-row"><span className="certinfo-key">실기 과목</span><span className="certinfo-val">{exec.certInfoData.exam_info.practical_subjects}</span></div>
                                )}
                                {exec.certInfoData.exam_info.written_pass_score && (
                                  <div className="certinfo-row"><span className="certinfo-key">필기 합격기준</span><span className="certinfo-val">{exec.certInfoData.exam_info.written_pass_score}</span></div>
                                )}
                                {exec.certInfoData.exam_info.practical_pass_score && (
                                  <div className="certinfo-row"><span className="certinfo-key">실기 합격기준</span><span className="certinfo-val">{exec.certInfoData.exam_info.practical_pass_score}</span></div>
                                )}
                                {exec.certInfoData.exam_info.written_exam_time && (
                                  <div className="certinfo-row"><span className="certinfo-key">필기 시험시간</span><span className="certinfo-val">{exec.certInfoData.exam_info.written_exam_time}</span></div>
                                )}
                                {exec.certInfoData.exam_info.exam_method && (
                                  <div className="certinfo-row"><span className="certinfo-key">시험방법</span><span className="certinfo-val">{exec.certInfoData.exam_info.exam_method}</span></div>
                                )}
                              </div>
                            </div>
                          )}
                          <p className="certinfo-src">한국산업인력공단</p>

                          {/* 합격률 통계 — session-rates (회별 실데이터) + cert_master 평균 */}
                          {exec.sessionRatesLoading && (
                            <div className="exec-loading"><Loader2 size={14} className="ev-spin" /> 합격률 데이터 조회 중…</div>
                          )}
                          {exec.sessionRatesFetched && (() => {
                            const sr = exec.sessionRatesData;
                            const cs = exec.certStatsData;
                            const hasSession = sr && sr.total > 0;
                            const hasSummary = cs && (cs.written_avg_pass_rate != null || cs.practical_avg_pass_rate != null || cs.avg_pass_rate_3yr != null || cs.exam_frequency);
                            if (!hasSession && !hasSummary) return null;

                            // build year-aggregated series for chart
                            type ChartPoint = { year: string; written: number | null; practical: number | null };
                            const yearMap: Record<string, { wSum: number; wCnt: number; pSum: number; pCnt: number }> = {};
                            if (sr) {
                              for (const r of sr.written) {
                                const y = r.year;
                                if (!yearMap[y]) yearMap[y] = { wSum: 0, wCnt: 0, pSum: 0, pCnt: 0 };
                                yearMap[y].wSum += r.pass_rate; yearMap[y].wCnt++;
                              }
                              for (const r of sr.practical) {
                                const y = r.year;
                                if (!yearMap[y]) yearMap[y] = { wSum: 0, wCnt: 0, pSum: 0, pCnt: 0 };
                                yearMap[y].pSum += r.pass_rate; yearMap[y].pCnt++;
                              }
                            }
                            const chartData: ChartPoint[] = Object.keys(yearMap).sort().map(y => ({
                              year: y,
                              written: yearMap[y].wCnt > 0 ? yearMap[y].wSum / yearMap[y].wCnt : null,
                              practical: yearMap[y].pCnt > 0 ? yearMap[y].pSum / yearMap[y].pCnt : null,
                            }));

                            // SVG mini line chart
                            const SvgChart = ({ data, color, key2 }: { data: ChartPoint[]; color: string; key2: 'written' | 'practical' }) => {
                              const pts = data.filter(d => d[key2] != null);
                              if (pts.length < 2) return null;
                              const W = 260, H = 72, PAD = 28;
                              const vals = pts.map(p => p[key2] as number);
                              const minV = Math.max(0, Math.min(...vals) - 5);
                              const maxV = Math.min(100, Math.max(...vals) + 5);
                              const range = maxV - minV || 1;
                              const toX = (i: number) => PAD + (i / (pts.length - 1)) * (W - PAD * 2);
                              const toY = (v: number) => H - 14 - ((v - minV) / range) * (H - 28);
                              const polyline = pts.map((p, i) => `${toX(i)},${toY(p[key2] as number)}`).join(' ');
                              return (
                                <svg width={W} height={H} style={{ overflow: 'visible', display: 'block' }}>
                                  <polyline points={polyline} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
                                  {pts.map((p, i) => (
                                    <g key={i}>
                                      <circle cx={toX(i)} cy={toY(p[key2] as number)} r="3.5" fill={color} />
                                      <text x={toX(i)} y={toY(p[key2] as number) - 7} textAnchor="middle" fontSize="10" fill={color} fontWeight="600">
                                        {(p[key2] as number).toFixed(1)}%
                                      </text>
                                      <text x={toX(i)} y={H - 2} textAnchor="middle" fontSize="9" fill="#94a3b8">{p.year}</text>
                                    </g>
                                  ))}
                                </svg>
                              );
                            };

                            // Render session table for one group
                            const SessionTable = ({ rows, label, color }: { rows: SessionRateRow[]; label: string; color: string }) => {
                              if (rows.length === 0) return null;
                              const years = [...new Set(rows.map(r => r.year))].sort();
                              const sessions = [...new Set(rows.map(r => r.session))].sort();
                              return (
                                <div className="sr-table-wrap">
                                  <div className="sr-table-head" style={{ color }}>{label}</div>
                                  <div className="sr-chart-row">
                                    <SvgChart data={chartData} color={color} key2={label === '필기' ? 'written' : 'practical'} />
                                  </div>
                                  <div style={{ overflowX: 'auto' }}>
                                    <table className="ev-stats-table">
                                      <thead>
                                        <tr>
                                          <th>연도</th>
                                          {sessions.map(s => (
                                            <React.Fragment key={s}>
                                              <th>{s} 응시</th>
                                              <th>{s} 합격</th>
                                              <th>{s} 합격률</th>
                                            </React.Fragment>
                                          ))}
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {years.map(yr => {
                                          const rowsByYear = rows.filter(r => r.year === yr);
                                          return (
                                            <tr key={yr}>
                                              <td className="ev-td-label">{yr}년</td>
                                              {sessions.map(s => {
                                                const r = rowsByYear.find(x => x.session === s);
                                                return (
                                                  <React.Fragment key={s}>
                                                    <td>{r ? r.applicants.toLocaleString() : '-'}</td>
                                                    <td>{r ? r.passed.toLocaleString() : '-'}</td>
                                                    <td className="ev-td-rate">{r ? `${r.pass_rate.toFixed(1)}%` : '-'}</td>
                                                  </React.Fragment>
                                                );
                                              })}
                                            </tr>
                                          );
                                        })}
                                      </tbody>
                                    </table>
                                  </div>
                                </div>
                              );
                            };

                            return (
                              <div className="certinfo-block">
                                <p className="certinfo-block-title">합격률 통계</p>
                                {/* summary chips from cert_master */}
                                {hasSummary && (
                                  <div className="certinfo-stat-row">
                                    {cs!.written_avg_pass_rate != null && (
                                      <div className="certinfo-stat-chip certinfo-stat-written">
                                        <span className="certinfo-stat-label">필기 평균</span>
                                        <span className="certinfo-stat-val">{cs!.written_avg_pass_rate.toFixed(1)}%</span>
                                      </div>
                                    )}
                                    {cs!.practical_avg_pass_rate != null && (
                                      <div className="certinfo-stat-chip certinfo-stat-practical">
                                        <span className="certinfo-stat-label">실기 평균</span>
                                        <span className="certinfo-stat-val">{cs!.practical_avg_pass_rate.toFixed(1)}%</span>
                                      </div>
                                    )}
                                    {cs!.avg_pass_rate_3yr != null && (
                                      <div className="certinfo-stat-chip certinfo-stat-avg">
                                        <span className="certinfo-stat-label">3년 평균</span>
                                        <span className="certinfo-stat-val">{cs!.avg_pass_rate_3yr.toFixed(1)}%</span>
                                      </div>
                                    )}
                                    {cs!.exam_frequency && (
                                      <div className="certinfo-stat-chip certinfo-stat-freq">
                                        <span className="certinfo-stat-label">시험 횟수</span>
                                        <span className="certinfo-stat-val">{cs!.exam_frequency}</span>
                                      </div>
                                    )}
                                    {cs!.exam_difficulty != null && (
                                      <div className="certinfo-stat-chip certinfo-stat-diff">
                                        <span className="certinfo-stat-label">난이도</span>
                                        <span className="certinfo-stat-val">{cs!.exam_difficulty.toFixed(1)}</span>
                                      </div>
                                    )}
                                    {(cs!.exam_type_info || cs!.exam_subject_info) && (
                                      <div className="certinfo-stat-chip certinfo-stat-type">
                                        <span className="certinfo-stat-label">시험 구성</span>
                                        <span className="certinfo-stat-val">{cs!.exam_type_info || cs!.exam_subject_info}</span>
                                      </div>
                                    )}
                                  </div>
                                )}
                                {/* Session-rate tables with charts */}
                                {hasSession && (
                                  <div className="sr-tables">
                                    <SessionTable rows={sr!.written} label="필기" color="#3b82f6" />
                                    <SessionTable rows={sr!.practical} label="실기" color="#10b981" />
                                    {sr!.other.length > 0 && <SessionTable rows={sr!.other} label="기타" color="#f59e0b" />}
                                  </div>
                                )}
                                <p className="certinfo-src">한국산업인력공단 국가기술자격 취득현황</p>
                              </div>
                            );
                          })()}

                          {/* GOMS 연관 직업 */}
                          {exec.certJobsLoading && (
                            <div className="exec-loading"><Loader2 size={14} className="ev-spin" /> 연관 직업 조회 중…</div>
                          )}

                          {/* 캐노니컬 직무 역할 (cert_job_mapping 기반) */}
                          {exec.certJobsFetched && exec.canonicalRoles.length > 0 && (() => {
                            const groups = exec.canonicalRoles.reduce<Record<string, string[]>>((acc, r) => {
                              (acc[r.job_top_group_name] ??= []).push(r.job_role_name);
                              return acc;
                            }, {});
                            return (
                              <div className="certinfo-block">
                                <p className="certinfo-block-title">직무 유형 ({exec.canonicalRoles.length}개)</p>
                                {Object.entries(groups).map(([group, roles]) => (
                                  <div key={group} className="certinfo-role-group">
                                    <span className="certinfo-role-group-label">{group}</span>
                                    <div className="certinfo-job-tags" style={{ marginTop: 4 }}>
                                      {roles.map((r, i) => (
                                        <span key={i} className="certinfo-job-tag">{r}</span>
                                      ))}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            );
                          })()}

                          {exec.certJobsFetched && exec.certJobsList.length > 0 && (
                            <div className="certinfo-block">
                              <p className="certinfo-block-title">연관 직업 ({exec.certJobsList.length}개) <span className="certinfo-job-hint">직업 클릭 → 상세 보기</span></p>
                              <div className="certinfo-job-tags">
                                {exec.certJobsList.slice(0, expandedJobsCerts.has(exec.certId) ? undefined : 18).map((job, i) => (
                                  <button
                                    key={i}
                                    className={`certinfo-job-tag certinfo-job-btn${exec.selectedJobName === job ? ' certinfo-job-selected' : ''}`}
                                    onClick={() => fetchJobDetail(job)}
                                  >{job}</button>
                                ))}
                                {!expandedJobsCerts.has(exec.certId) && exec.certJobsList.length > 18 && (
                                  <button
                                    className="certinfo-job-more-btn"
                                    onClick={() => setExpandedJobsCerts(prev => new Set([...prev, exec.certId]))}
                                  >+{exec.certJobsList.length - 18}개 더 보기</button>
                                )}
                              </div>
                              {exec.jobDetailLoading && (
                                <div className="exec-loading"><Loader2 size={13} className="ev-spin" /> 직업 정보 조회 중…</div>
                              )}
                              {exec.jobDetailData && exec.selectedJobName && (
                                <div className="job-detail-card">
                                  <p className="job-detail-name">{exec.jobDetailData.job_name || exec.selectedJobName}</p>
                                  {/* 워크넷 6개 직업 지수 */}
                                  {(exec.jobDetailData.pay_score != null || exec.jobDetailData.job_security_score != null) && (
                                    <div className="jd-scores">
                                      {[
                                        { label: '보상', val: exec.jobDetailData.pay_score },
                                        { label: '고용안정', val: exec.jobDetailData.job_security_score },
                                        { label: '성장', val: exec.jobDetailData.growth_score },
                                        { label: '근무여건', val: exec.jobDetailData.work_conditions_score },
                                        { label: '전문성', val: exec.jobDetailData.professionalism_score },
                                        { label: '고용평등', val: exec.jobDetailData.equity_score },
                                      ].filter(s => s.val != null).map(({ label, val }) => {
                                        const v = val!;
                                        const c = v >= 67 ? '#16a34a' : v >= 34 ? '#d97706' : '#dc2626';
                                        return (
                                          <div key={label} className="jd-score-item">
                                            <span className="jd-score-label">{label}</span>
                                            <div className="jd-score-bar"><div className="jd-score-fill" style={{ width: `${v}%`, background: c }} /></div>
                                            <span className="jd-score-num" style={{ color: c }}>{Math.round(v)}</span>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  )}
                                  {(exec.jobDetailData.salary_summary || exec.jobDetailData.salary) && (() => {
                                    const raw = exec.jobDetailData.salary_summary || exec.jobDetailData.salary || '';
                                    // "임금 하위(25%) 5725만원, 평균(50%) 6500만원, 상위(25%) 8000만원"
                                    const nums = [...raw.matchAll(/(\d[\d,]+)만원/g)].map(m => parseInt(m[1].replace(/,/g, ''), 10));
                                    const [low, mid, high] = nums.length >= 3 ? [nums[0], nums[1], nums[2]] : [null, null, null];
                                    return (
                                      <div className="job-salary-viz">
                                        <span className="job-detail-key">임금 수준</span>
                                        {low && mid && high ? (
                                          <div className="salary-range-wrap">
                                            <div className="salary-range-bar">
                                              <div className="salary-range-fill" style={{ left: '0%', right: '0%' }} />
                                              {[
                                                { label: '하위25%', val: low, pct: 0 },
                                                { label: '평균', val: mid, pct: Math.round((mid - low) / (high - low) * 100) },
                                                { label: '상위25%', val: high, pct: 100 },
                                              ].map(({ label, val, pct }) => (
                                                <div key={label} className="salary-dot-wrap" style={{ left: `${pct}%` }}>
                                                  <div className="salary-dot" />
                                                  <span className="salary-dot-val">{val.toLocaleString()}</span>
                                                  <span className="salary-dot-label">{label}</span>
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        ) : (
                                          <span className="job-detail-val">{raw}</span>
                                        )}
                                      </div>
                                    );
                                  })()}
                                  {exec.jobDetailData.outlook && (() => {
                                    const raw = exec.jobDetailData.outlook;
                                    // "증가(23%) 현상유지(42%) 감소(34%)"
                                    const parts = [...raw.matchAll(/([가-힣·]+)\((\d+)%\)/g)].map(m => ({ label: m[1], pct: parseInt(m[2], 10) }));
                                    const colors: Record<string, string> = { '증가': '#16a34a', '현상유지': '#d97706', '감소': '#dc2626' };
                                    return (
                                      <div className="job-outlook-viz">
                                        <span className="job-detail-key">일자리 전망</span>
                                        {parts.length >= 2 ? (
                                          <div className="outlook-stack-wrap">
                                            <div className="outlook-stack-bar">
                                              {parts.map(({ label, pct }) => (
                                                <div
                                                  key={label}
                                                  className="outlook-stack-seg"
                                                  style={{ width: `${pct}%`, background: colors[label] ?? '#94a3b8' }}
                                                  title={`${label} ${pct}%`}
                                                />
                                              ))}
                                            </div>
                                            <div className="outlook-legend">
                                              {parts.map(({ label, pct }) => (
                                                <span key={label} className="outlook-legend-item">
                                                  <span className="outlook-dot" style={{ background: colors[label] ?? '#94a3b8' }} />
                                                  {label} {pct}%
                                                </span>
                                              ))}
                                            </div>
                                          </div>
                                        ) : (
                                          <span className="job-detail-val">{raw}</span>
                                        )}
                                      </div>
                                    );
                                  })()}
                                  {exec.jobDetailData.similar_jobs && (
                                    <div className="job-detail-row">
                                      <span className="job-detail-key">유사 직업</span>
                                      <span className="job-detail-val">{exec.jobDetailData.similar_jobs}</span>
                                    </div>
                                  )}
                                  {exec.jobDetailData.work_content && (
                                    <div className="job-detail-row job-detail-row-block">
                                      <span className="job-detail-key">하는 일</span>
                                      <span className="job-detail-val job-detail-content">{exec.jobDetailData.work_content.slice(0, 200)}{exec.jobDetailData.work_content.length > 200 ? '…' : ''}</span>
                                    </div>
                                  )}
                                  <p className="certinfo-src">고용24 · 워크넷 직업사전</p>
                                </div>
                              )}
                              <p className="certinfo-src">고용24 · NCS</p>
                            </div>
                          )}

                          {/* 연관 전공 */}
                          {exec.certJobsFetched && exec.relatedMajors.length > 0 && (
                            <div className="certinfo-block">
                              <p className="certinfo-block-title">연관 전공 ({exec.relatedMajors.length}개)</p>
                              <div className="certinfo-job-tags">
                                {exec.relatedMajors.slice(0, 16).map((m, i) => (
                                  <span key={i} className="certinfo-job-tag">{m}</span>
                                ))}
                                {exec.relatedMajors.length > 16 && (
                                  <span className="certinfo-job-tag certinfo-job-more">+{exec.relatedMajors.length - 16}개</span>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                  }
              </div>
            </div>
          )}

          {/* 관련 동영상 섹션 — 모달 하단, 버튼 클릭 시 영상 inline 펼침 */}
          <div className="modal-videos-section">
            {videos.certId !== evidence.certId || (!videos.fetched && !videos.loading) ? (
              <button
                type="button"
                className="btn-videos-cta"
                onClick={() => fetchVideos(evidence.certId, evidenceCertName)}
              >
                <Video size={15} /> 관련 동영상 보기
                <span className="btn-videos-hint">YouTube 강의 5개</span>
              </button>
            ) : (
              <>
                <div className="modal-videos-header">
                  <Video size={15} style={{ color: 'var(--primary)' }} />
                  <span className="modal-videos-title">{evidenceCertName} 관련 강의 동영상</span>
                  {videos.cacheHit && <span className="cache-badge" title="캐시된 결과">캐시</span>}
                </div>

                {videos.loading && (
                  <div className="ev-loading"><Loader2 size={18} className="ev-spin" /><span>YouTube에서 강의 영상을 찾는 중…</span></div>
                )}

                {!videos.loading && videos.error && (
                  <div className="ev-empty">
                    <AlertCircle size={16} style={{ flexShrink: 0 }} />
                    <span>{videos.error}</span>
                  </div>
                )}

                {!videos.loading && videos.warning && videos.videos.length > 0 && (
                  <div className="ev-empty" style={{ color: '#b45309', background: '#fef3c7', padding: '.5rem .75rem', borderRadius: '6px' }}>
                    <AlertCircle size={14} style={{ flexShrink: 0 }} />
                    <span>
                      {videos.warning === 'quota_exceeded_using_stale_cache'
                        ? '일일 검색 한도 초과 — 이전 결과를 보여드립니다.'
                        : '최신 결과를 불러오지 못해 이전 결과를 보여드립니다.'}
                    </span>
                  </div>
                )}

                {!videos.loading && videos.fetched && videos.videos.length === 0 && !videos.error && (
                  <div className="ev-empty">
                    <AlertCircle size={16} style={{ flexShrink: 0 }} />
                    <span>관련 동영상을 찾지 못했습니다.</span>
                  </div>
                )}

                {!videos.loading && videos.videos.length > 0 && (
                  <div className="videos-grid">
                    {videos.videos.map(v => (
                      <a key={v.video_id} href={v.url} target="_blank" rel="noreferrer" className="video-card">
                        <div className="video-thumb">
                          {v.thumbnail_url
                            ? <img src={v.thumbnail_url} alt={v.title} loading="lazy" />
                            : <div className="video-thumb-fallback"><Play size={32} /></div>
                          }
                          <div className="video-play-overlay"><Play size={28} /></div>
                        </div>
                        <div className="video-meta">
                          <p className="video-title">{v.title}</p>
                          <p className="video-channel">{v.channel}</p>
                        </div>
                      </a>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
          </div>
        </div>
        </div>
      )}

      <div className="card filter-card">
        <div className="search-wrapper">
          <Search size={16} className="search-icon" />
          <input type="text" className="input search-input" placeholder="자격증명, 발급기관, 분야 검색…"
            value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
          {searchQuery && (
            <button className="search-clear" onClick={() => setSearchQuery('')} aria-label="검색어 지우기">
              <X size={14} />
            </button>
          )}
        </div>
        <div className="filter-row">
          <div className="filter-group">
            <label className="filter-label">등급 필터</label>
            <div className="select-wrap">
              <select className="select" value={selectedGrade} onChange={e => setSelectedGrade(e.target.value)}>
                <option value="">전체 등급</option>
                <option value="1_기능사">기능사</option>
                <option value="2_산업기사">산업기사</option>
                <option value="3_기사">기사</option>
                <option value="4_기술사">기술사</option>
                <option value="5_기능장">기능장</option>
              </select>
              <ChevronDown size={14} className="select-arrow" />
            </div>
          </div>
          <div className="filter-group">
            <label className="filter-label">정렬</label>
            <div className="select-wrap">
              <select className="select" value={sortBy} onChange={e => setSortBy(e.target.value as typeof sortBy)}>
                <option value="default">기본순</option>
                <option value="passrate_desc">합격률 높은 순</option>
                <option value="grade_desc">등급 높은 순</option>
                <option value="name_asc">이름순</option>
              </select>
              <ChevronDown size={14} className="select-arrow" />
            </div>
          </div>
          <div className="active-filters">
            {domainName && <span className="filter-chip">{domainName}</span>}
            {riskLabel  && <span className="filter-chip">{riskLabel}</span>}
            {jobName    && <span className="filter-chip filter-chip-job">{jobName}</span>}
          </div>
        </div>
      </div>

      <section>
        {certsLoading ? (
          <div className="rec-loading"><Loader2 size={24} className="rec-spin" /><p>자격증 데이터를 불러오는 중…</p></div>
        ) : fetchError ? (
          <div className="rec-error card">
            <AlertCircle size={18} /><p>데이터 로드 실패: {fetchError}</p>
            <button className="btn-ghost" onClick={() => window.location.reload()}>다시 시도</button>
          </div>
        ) : (
          <>
            <div className="result-count-row">
              <p className="result-count">추천 자격증 <span className="count-num">{filtered.length}</span>건</p>
              {domainParam && jobParam && (
                <span className="result-cap-hint" style={{ background: '#f0fdf4', borderColor: 'rgba(16,185,129,.25)', color: '#065f46' }}>
                  분야 OR 직무 합산 결과
                </span>
              )}
              {filtered.length > 60 && (
                <span className="result-cap-hint">상위 60건 표시 · 검색어나 등급 필터로 좁히세요</span>
              )}
            </div>
            <div className="cert-grid-scroll">
              <div className="cert-grid">
                {filtered.slice(0, 60).map(cert => {
                  // domain+job 둘 다 선택 시 어느 조건으로 매칭됐는지 뱃지
                  let matchLabel: string | null = null;
                  const isPrimaryDomainMatch = cert.primary_domain === domainParam;
                  const isRelatedDomainMatch = !isPrimaryDomainMatch && cert.related_domains.includes(domainParam ?? '');
                  if (domainParam && jobParam) {
                    const dOk = isPrimaryDomainMatch || isRelatedDomainMatch;
                    const jOk = cert.related_jobs.includes(jobParam);
                    if (!dOk && jOk) matchLabel = jobName || jobParam;
                    else if (dOk && !jOk) matchLabel = domainName || domainParam;
                    // dOk && jOk → both match, no label needed
                  } else if (domainParam && isRelatedDomainMatch) {
                    // 교차 도메인 확장으로 표시된 자격증
                    matchLabel = '관련 분야';
                  }
                  return (
                    <CertCard
                      key={cert.candidate_id}
                      cert={cert}
                      onEvidence={fetchEvidence}
                      onDag={fetchDag}
                      onRoadmap={goToRoadmap}
                      isSelected={evidence.certId === cert.cert_id && showEvidence}
                      matchLabel={matchLabel}
                      isCrossDomain={isRelatedDomainMatch}
                    />
                  );
                })}
                {filtered.length === 0 && (
                  <div className="no-results">
                    <>
                      <p className="no-results-title">조건에 맞는 자격증이 없습니다.</p>
                      <p className="no-results-sub">검색어나 등급 필터를 바꿔보세요.</p>
                    </>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </section>


      <style>{`
        .rec-wrap{display:flex;flex-direction:column;gap:1.5rem}
        .back-btn{display:inline-flex;align-items:center;gap:.35rem;font-size:.85rem;font-weight:500;color:var(--text-muted);margin-bottom:.25rem;background:none;border:none;cursor:pointer;padding:0;transition:color .15s;width:fit-content}
        .back-btn:hover{color:var(--primary)}
        .featured-cert{border-left-width:4px;padding:1.5rem;display:flex;flex-direction:column;gap:.75rem}
        .featured-tag-row{display:flex}
        .featured-tag{font-size:.68rem;font-weight:700;letter-spacing:.07em;padding:.2rem .625rem;background:var(--primary-light);color:var(--primary);border-radius:var(--radius-full);border:1px solid rgba(99,102,241,.2)}
        .featured-body{display:flex;flex-direction:column;gap:.3rem}
        .featured-name{font-size:1.3rem;font-weight:800;color:var(--text);margin-top:.2rem}
        .featured-issuer{font-size:.78rem;color:var(--text-light)}
        .featured-summary{font-size:.875rem;color:var(--text-muted);line-height:1.65;margin-top:.2rem}
        .featured-actions{display:flex;gap:.75rem;flex-wrap:wrap;padding-top:.25rem}
        /* 모달 backdrop & 카드 */
        .modal-backdrop{
          position:fixed;inset:0;z-index:1000;
          background:rgba(15,23,42,.55);
          backdrop-filter:blur(2px);
          -webkit-backdrop-filter:blur(2px);
          display:flex;align-items:center;justify-content:center;
          padding:2vh 1rem;
          overflow:hidden;
          animation:modal-fade-in .18s ease-out;
        }
        @keyframes modal-fade-in{from{opacity:0}to{opacity:1}}
        .modal-card{
          width:100%;max-width:720px;
          animation:modal-pop .22s ease-out;
        }
        @keyframes modal-pop{
          from{opacity:0;transform:translateY(12px) scale(.98)}
          to{opacity:1;transform:translateY(0) scale(1)}
        }
        .evidence-modal{
          max-height:90vh;display:flex;flex-direction:column;overflow:hidden;
          border-left:3px solid var(--primary);
        }
        .ev-header{
          display:flex;align-items:center;justify-content:space-between;gap:.75rem;
          flex-shrink:0;padding:.875rem 1.25rem;
          border-bottom:1px solid var(--border);
          background:var(--surface);
          border-radius:var(--radius-md) var(--radius-md) 0 0;
        }
        .evidence-panel{
          flex:1;overflow-y:auto;padding:1.25rem;
          display:flex;flex-direction:column;gap:.875rem;
          scrollbar-width:thin;scrollbar-color:var(--border-strong) transparent;
        }
        .evidence-panel::-webkit-scrollbar{width:5px}
        .evidence-panel::-webkit-scrollbar-thumb{background:var(--border-strong);border-radius:99px}

        /* 모달 안 영상 섹션 */
        .modal-videos-section{margin-top:.25rem;padding-top:1rem;border-top:1px dashed var(--border);display:flex;flex-direction:column;gap:.75rem}
        .btn-videos-cta{
          display:inline-flex;align-items:center;gap:.5rem;
          padding:.7rem 1.1rem;
          background:var(--primary-light);
          color:var(--primary);
          border:1.5px dashed var(--primary);
          border-radius:var(--radius-sm);
          font-size:.9rem;font-weight:700;
          width:fit-content;cursor:pointer;transition:all .15s;
        }
        .btn-videos-cta:hover{background:var(--primary);color:#fff}
        .btn-videos-hint{font-size:.7rem;font-weight:500;opacity:.7;margin-left:.25rem}
        .btn-videos-cta:hover .btn-videos-hint{opacity:1}
        .modal-videos-header{display:flex;align-items:center;gap:.45rem}
        .modal-videos-title{font-size:.85rem;font-weight:700;color:var(--text)}
        .ev-header-left{display:flex;align-items:center;gap:.5rem;flex:1;min-width:0}
        .ev-title{font-size:.875rem;font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .ev-close{background:none;border:none;cursor:pointer;color:var(--text-light);padding:.2rem;flex-shrink:0;transition:color .15s}
        .ev-close:hover{color:var(--danger)}
        .ev-loading{display:flex;align-items:center;gap:.5rem;font-size:.875rem;color:var(--text-muted)}
        .ev-spin{animation:spin 1s linear infinite;color:var(--primary)}
        @keyframes spin{to{transform:rotate(360deg)}}
        .ev-empty{display:flex;align-items:flex-start;gap:.5rem;font-size:.84rem;color:var(--text-muted);line-height:1.6}
        .ev-intro{font-size:.8rem;color:var(--text-muted);line-height:1.65;padding-bottom:.25rem}
        .ev-list{display:flex;flex-direction:column;gap:.75rem}
        .dag-panel{display:flex;flex-direction:column;gap:.625rem;padding:.875rem;background:var(--surface-2);border-radius:var(--radius-sm);border:1px solid var(--border)}
        .dag-panel-title{font-size:.7rem;font-weight:700;color:var(--text-light);letter-spacing:.05em;text-transform:uppercase}
        .dag-flow-scroll{overflow-x:auto;padding-bottom:.25rem}
        .ev-row{padding:.875rem;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-sm);display:flex;flex-direction:column;gap:.5rem}
        .ev-row-header{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}
        .ev-source-badge{padding:.15rem .5rem;background:var(--primary-light);color:var(--primary);border-radius:var(--radius-xs);font-size:.64rem;font-weight:700;letter-spacing:.06em}
        .ev-src-tag{padding:.1rem .4rem;border-radius:3px;font-size:.62rem;font-weight:700;letter-spacing:.05em;flex-shrink:0}
        .ev-src-db{background:#ede9fe;color:#6d28d9}
        .ev-src-local{background:#f1f5f9;color:#64748b}
        .ev-src-catalog{background:#fef3c7;color:#92400e}
        .ev-src-national{background:#dbeafe;color:#1e40af}
        .ev-row-catalog{border-color:rgba(245,158,11,.3);background:#fffbeb}
        .ev-catalog-list{margin:0;padding-left:1.1rem;display:flex;flex-direction:column;gap:.3rem}
        .ev-catalog-list li{font-size:.84rem;color:var(--text-muted);line-height:1.65}
        .ev-score-wrap{display:flex;align-items:center;gap:.3rem;margin-left:auto}
        .ev-score-track{width:44px;height:4px;background:var(--border);border-radius:99px;overflow:hidden}
        .ev-score-fill{height:100%;background:var(--primary);border-radius:99px}
        .ev-score-pct{font-size:.66rem;font-weight:700;color:var(--primary);white-space:nowrap}
        .ev-section-label{font-size:.75rem;font-weight:700;color:var(--primary);padding:.1rem .5rem;background:var(--primary-light);border-radius:var(--radius-xs)}
        .ev-section{font-size:.75rem;color:var(--text-light)}
        .ev-link{display:inline-flex;align-items:center;gap:.25rem;font-size:.75rem;color:var(--secondary);text-decoration:none;margin-left:auto}
        .ev-link:hover{text-decoration:underline}
        .ev-snippet{font-size:.855rem;color:var(--text-muted);line-height:1.7;border-left:3px solid var(--primary-light);padding-left:.75rem}
        .cert-match-tag{margin-left:auto;padding:.1rem .45rem;background:#f0fdf4;border:1px solid rgba(16,185,129,.3);border-radius:var(--radius-xs);font-size:.62rem;font-weight:700;color:#065f46;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:80px}
        .cert-match-tag[data-cross="true"]{background:#eff6ff;border-color:rgba(37,99,235,.25);color:var(--primary)}
        .search-clear{position:absolute;right:.5rem;background:none;border:none;cursor:pointer;color:var(--text-light);display:flex;align-items:center;padding:.25rem;transition:color .15s;border-radius:var(--radius-xs)}
        .search-clear:hover{color:var(--danger)}
        .filter-card{padding:1.25rem;display:flex;flex-direction:column;gap:.875rem}
        .filter-row{display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end}
        .filter-group{display:flex;flex-direction:column;gap:.375rem}
        .filter-label{font-size:.78rem;font-weight:600;color:var(--text-muted)}
        .select-wrap{position:relative;display:flex;align-items:center}
        .select-arrow{position:absolute;right:.75rem;color:var(--text-light);pointer-events:none}
        .active-filters{display:flex;gap:.375rem;flex-wrap:wrap;align-items:center;margin-left:auto}
        .filter-chip{padding:.25rem .75rem;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-full);font-size:.75rem;color:var(--text-muted)}
        .filter-chip-job{background:#f0fdf4;border-color:rgba(16,185,129,.25);color:#065f46}
        .rec-loading{display:flex;flex-direction:column;align-items:center;gap:.75rem;padding:3rem 1rem;color:var(--text-muted);font-size:.9rem}
        .rec-spin{animation:spin 1s linear infinite;color:var(--primary)}
        .rec-error{display:flex;align-items:center;gap:.75rem;padding:1.25rem;color:var(--danger);flex-wrap:wrap}
        .result-count-row{display:flex;align-items:baseline;gap:.75rem;margin-bottom:.875rem;flex-wrap:wrap}
        .result-count{font-size:.9rem;color:var(--text-muted);margin:0}
        .count-num{color:var(--primary);font-size:1.2rem;font-weight:800}
        .result-cap-hint{font-size:.75rem;color:var(--text-light);padding:.15rem .6rem;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-full)}
        .cert-grid-scroll{max-height:72vh;overflow-y:auto;padding-right:4px;scrollbar-width:thin;scrollbar-color:var(--border-strong) transparent}
        .cert-grid-scroll::-webkit-scrollbar{width:5px}
        .cert-grid-scroll::-webkit-scrollbar-thumb{background:var(--border-strong);border-radius:99px}
        .cert-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:.875rem}
        .cert-card{padding:1.125rem;display:flex;flex-direction:column;gap:.625rem;transition:box-shadow .2s,border-color .2s,transform .2s}
        .cert-card:hover{box-shadow:0 6px 24px rgba(99,102,241,.12),var(--shadow-md);border-color:rgba(99,102,241,.2);transform:translateY(-3px)}
        .cert-top{display:flex;flex-direction:column;gap:.25rem}
        .cert-top-row{display:flex;align-items:center;gap:.5rem;justify-content:space-between}
        .cert-name{font-size:.975rem;font-weight:700;color:var(--text)}
        .cert-issuer{font-size:.72rem;color:var(--text-light)}
        .cert-summary{font-size:.79rem;color:var(--text-muted);line-height:1.55;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
        .cert-actions{display:flex;gap:.75rem;padding-top:.625rem;border-top:1px solid var(--border);margin-top:auto;align-items:center}
        .text-btn{display:inline-flex;align-items:center;gap:.35rem;font-size:.82rem;font-weight:600;background:none;border:none;cursor:pointer;padding:0;transition:opacity .15s}
        .text-btn:hover{opacity:.75}
        .evidence-btn{color:var(--primary)}
        .roadmap-btn{color:var(--secondary);margin-left:auto}
        .cert-actions{flex-wrap:wrap;row-gap:.4rem}
        .no-results{grid-column:1/-1;text-align:center;padding:2.5rem 1.25rem;line-height:1.8;display:flex;flex-direction:column;gap:.5rem}
        .no-results-title{font-size:.95rem;font-weight:700;color:var(--text)}
        .no-results-sub{font-size:.85rem;color:var(--text-muted);line-height:1.65}
        .cert-card-selected{border-color:var(--primary)!important;box-shadow:0 0 0 2px rgba(99,102,241,.18),var(--shadow-md)!important;background:#f5f3ff}
        .cert-click-hint{display:inline-flex;align-items:center;gap:.25rem;font-size:.72rem;color:var(--text-light)}
        /* 합격률 게이지 */
        .cert-rate-wrap{display:flex;flex-direction:column;gap:.35rem;padding:.5rem .625rem;background:var(--surface-2);border-radius:var(--radius-xs);border:1px solid var(--border)}
        .cert-rate-header{display:flex;align-items:center;gap:.4rem}
        .cert-rate-label{font-size:.67rem;font-weight:600;color:var(--text-light);flex:1}
        .cert-rate-pct{font-size:.8rem;font-weight:800;letter-spacing:-.01em}
        .cert-rate-tag{font-size:.6rem;font-weight:700;letter-spacing:.04em;padding:.1rem .45rem;border-radius:99px}
        .cert-rate-track{height:5px;background:var(--surface-3,#e2e8f0);border-radius:99px;overflow:hidden}
        .cert-rate-fill{height:100%;border-radius:99px;transition:width .4s ease}
        /* 데이터 출처 */
        .cert-data-src{font-size:.62rem;color:var(--text-light);line-height:1.4;margin-top:auto;padding-top:.375rem;border-top:1px solid var(--border)}
        /* 페이지 하단 데이터 출처 푸터 */
        .data-src-footer{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;padding:.625rem .875rem;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-sm)}
        .data-src-footer-label{font-size:.68rem;font-weight:700;color:var(--text-muted);letter-spacing:.04em;white-space:nowrap}
        .data-src-sep{color:var(--border-strong);font-size:.75rem}
        .data-src-link{font-size:.68rem;color:var(--text-light);text-decoration:none;transition:color .15s}
        .data-src-link:hover{color:var(--primary);text-decoration:underline}
        .featured-cert-active{border-left-color:var(--primary)!important;background:#f5f3ff}
        .ev-intro-box{padding:.875rem 1rem;background:#eff6ff;border:1px solid #bfdbfe;border-radius:var(--radius-sm);display:flex;flex-direction:column;gap:.4rem}
        .ev-intro-label{font-size:.68rem;font-weight:800;letter-spacing:.07em;color:#1d4ed8;text-transform:uppercase}
        .ev-intro-text{font-size:.875rem;color:#1e3a5f;line-height:1.7;margin:0}
        .ev-career-box{padding:.875rem 1rem;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:var(--radius-sm);display:flex;flex-direction:column;gap:.4rem}
        .ev-career-label{font-size:.68rem;font-weight:800;letter-spacing:.07em;color:#15803d;text-transform:uppercase}
        .ev-career-text{font-size:.855rem;color:#14532d;line-height:1.7;margin:0}
        .ev-exam-section{padding:.875rem 1rem;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-sm);display:flex;flex-direction:column;gap:.5rem}
        .ev-exam-section-label{font-size:.68rem;font-weight:800;letter-spacing:.07em;color:var(--primary);text-transform:uppercase}
        .ev-exam-row{display:flex;flex-wrap:wrap;gap:.5rem}
        .ev-exam-pill{display:inline-flex;align-items:center;padding:.25rem .75rem;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-full);font-size:.8rem;font-weight:600;color:var(--text);white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)}
        .ev-gasanjeom{padding:.875rem 1rem;background:#fefce8;border:1px solid #fde68a;border-radius:var(--radius-sm);display:flex;flex-direction:column;gap:.35rem}
        .ev-gasanjeom-label{font-size:.68rem;font-weight:800;letter-spacing:.07em;color:#92400e;text-transform:uppercase}
        .ev-gasanjeom-text{font-size:.855rem;color:#78350f;line-height:1.65;margin:0}
        .videos-panel{padding:1.25rem;display:flex;flex-direction:column;gap:.875rem;border-left:3px solid #ef4444}
        .cache-badge{padding:.1rem .4rem;background:#f1f5f9;color:#64748b;border-radius:3px;font-size:.62rem;font-weight:700;letter-spacing:.05em;flex-shrink:0}
        .videos-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:.875rem}
        .video-card{display:flex;flex-direction:column;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-sm);overflow:hidden;text-decoration:none;color:inherit;transition:transform .2s,box-shadow .2s,border-color .2s}
        .video-card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.08);border-color:rgba(239,68,68,.3)}
        .video-thumb{position:relative;aspect-ratio:16/9;background:#0f172a;display:flex;align-items:center;justify-content:center;overflow:hidden}
        .video-thumb img{width:100%;height:100%;object-fit:cover;display:block}
        .video-thumb-fallback{color:#475569}
        .video-play-overlay{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.25);color:#fff;opacity:0;transition:opacity .2s}
        .video-card:hover .video-play-overlay{opacity:1}
        .video-meta{padding:.625rem .75rem;display:flex;flex-direction:column;gap:.25rem}
        .video-title{font-size:.82rem;font-weight:600;color:var(--text);line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
        .video-channel{font-size:.72rem;color:var(--text-light)}
        /* AI 추천 이유 (5번 — 패널 최상단 핵심 결론으로 격상) */
        .ai-reasoning-card{
          padding:1.125rem 1.25rem;
          background:#eff6ff;
          border:1.5px solid rgba(37,99,235,.35);
          border-radius:10px;
          display:flex;flex-direction:column;gap:.6rem;
          box-shadow:0 4px 14px rgba(37,99,235,.10);
          position:relative;
        }
        .ai-reasoning-card::before{
          content:'';position:absolute;left:0;top:0;bottom:0;width:4px;
          background:#2563eb;
          border-radius:10px 0 0 10px;
        }
        .ai-reasoning-header{display:flex;align-items:center;gap:.5rem}
        .ai-reasoning-icon{color:#2563eb;flex-shrink:0;animation:ai-pulse 2.4s ease-in-out infinite}
        @keyframes ai-pulse{0%,100%{opacity:.85;transform:scale(1)}50%{opacity:1;transform:scale(1.08)}}
        .ai-reasoning-label{font-size:.85rem;font-weight:800;color:#1d4ed8;letter-spacing:-.01em}
        .ai-reasoning-badge{
          margin-left:auto;font-size:.62rem;font-weight:700;letter-spacing:.05em;
          padding:.15rem .5rem;background:#2563eb;color:#fff;
          border-radius:99px;text-transform:uppercase;
        }
        .ai-reasoning-loading{display:flex;align-items:center;gap:.5rem;font-size:.85rem;color:#2563eb;padding-top:.2rem}
        .ai-reasoning-text{font-size:.95rem;color:#1e3a8a;line-height:1.75;margin:0;font-weight:500}

        /* 보조 근거 헤더 */
        .ev-supporting-header{
          display:flex;align-items:center;gap:.4rem;
          padding:.5rem .25rem .25rem;
          margin-top:.25rem;
          border-bottom:1px solid var(--border);
          color:var(--text-light);
        }
        .ev-supporting-title{font-size:.78rem;font-weight:700;color:var(--text-muted)}
        .ev-supporting-sub{font-size:.72rem;color:var(--text-light);margin-left:.3rem}

        /* 검정 현황 — 표 렌더링 */
        .ev-row-stats{background:#f8fafc;border-color:#e2e8f0}
        .ev-stats-years{display:flex;align-items:center;gap:.35rem;flex-wrap:wrap;margin-bottom:.1rem}
        .ev-stats-year-chip{
          padding:.15rem .55rem;background:#dbeafe;color:#1e40af;
          border-radius:99px;font-size:.68rem;font-weight:700;
        }
        .ev-stats-year-label{font-size:.68rem;color:#64748b;margin-left:.2rem}
        .ev-stats-table-wrap{overflow-x:auto;border-radius:6px;border:1px solid #e2e8f0}
        .ev-stats-table{
          width:100%;border-collapse:collapse;font-size:.8rem;
        }
        .ev-stats-table thead tr{background:#f1f5f9}
        .ev-stats-table th{
          padding:.45rem .75rem;text-align:right;font-size:.72rem;font-weight:700;
          color:#475569;border-bottom:1px solid #e2e8f0;white-space:nowrap;
        }
        .ev-stats-table th:first-child{text-align:left}
        .ev-stats-table td{
          padding:.4rem .75rem;text-align:right;color:#334155;
          border-bottom:1px solid #f1f5f9;font-variant-numeric:tabular-nums;
        }
        .ev-stats-table td:first-child{text-align:left;font-weight:600;color:#1e293b}
        .ev-stats-table tbody tr:last-child td{border-bottom:none}
        .ev-stats-table tbody tr:hover td{background:#f8fafc}
        .ev-stats-disclaimer{
          font-size:.68rem;color:#94a3b8;margin:0;line-height:1.5;
          border-top:1px solid #f1f5f9;padding-top:.4rem;
        }
        .ev-stats-pre{
          font-size:.72rem;
          font-family:'Menlo','Consolas','D2Coding',monospace;
          color:#334155;line-height:1.75;white-space:pre-wrap;word-break:break-all;
          background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;
          padding:.625rem .875rem;margin:0;max-height:160px;overflow-y:auto;
          scrollbar-width:thin;scrollbar-color:var(--border-strong) transparent;
        }
        /* 연도별 블록 (column-major) */
        .ev-stats-year-block { margin-bottom: .75rem; }
        .ev-stats-year-block:last-child { margin-bottom: 0; }
        .ev-stats-year-head {
          font-size:.75rem;font-weight:800;color:#1e40af;
          background:#eff6ff;padding:.3rem .75rem;border-radius:4px 4px 0 0;
          border:1px solid #bfdbfe;border-bottom:none;
        }
        .ev-stats-year-block .ev-stats-table { border-top:none; border-radius:0 0 6px 6px; }
        .ev-td-label { font-weight:700 !important; color:#0f172a !important; }
        .ev-td-rate { color:#0369a1 !important; font-weight:600 !important; }
        /* fallback: 파싱 실패 시 정제된 텍스트 */
        .ev-stats-fallback { display:flex; flex-direction:column; gap:.5rem; }
        .ev-stats-raw-text {
          font-size:.78rem;color:#475569;line-height:1.8;
          white-space:normal;word-break:keep-all;
          background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;
          padding:.625rem .875rem;margin:0;
        }

        /* ── Execution Panel ── */
        .exec-panel{padding:0;background:transparent;border:none;display:flex;flex-direction:column;gap:0}
        .exec-section{padding:.875rem 1rem;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-sm);display:flex;flex-direction:column;gap:.5rem;margin-bottom:.5rem}
        .exec-section:last-child{margin-bottom:0}
        .exec-section-title{font-size:.68rem;font-weight:800;letter-spacing:.07em;color:var(--primary);text-transform:uppercase;margin:0}
        .exec-loading{font-size:.8rem;color:var(--text-light);display:flex;align-items:center;gap:.4rem;padding:.375rem 0}
        .exec-empty{font-size:.82rem;color:var(--text-light);padding:.375rem 0;margin:0}
        .exec-list{display:flex;flex-direction:column;gap:.375rem}
        /* 시험 일정 */
        .exec-sched-row{display:flex;align-items:center;justify-content:space-between;padding:.5rem .75rem;background:#fff;border:1px solid #e2e8f0;border-radius:6px;gap:.5rem}
        .exec-sched-right{display:flex;flex-direction:column;align-items:flex-end;gap:.25rem;flex-shrink:0}
        .exec-sched-reg-open{font-size:.68rem;font-weight:700;padding:.15rem .45rem;border-radius:var(--radius-xs);background:#dcfce7;color:#15803d}
        .exec-qnet-btn{display:inline-flex;align-items:center;gap:.35rem;font-size:.75rem;font-weight:600;color:var(--primary);text-decoration:none;padding:.3rem .6rem;border:1px solid var(--primary);border-radius:var(--radius-xs);width:fit-content;margin-top:.25rem;transition:background .15s}
        .exec-qnet-btn:hover{background:var(--primary-light)}
        .exec-sched-left{display:flex;flex-direction:column;gap:.1rem}
        .exec-sched-round{font-size:.82rem;font-weight:700;color:#1e293b}
        .exec-sched-period{font-size:.72rem;color:#64748b}
        .exec-sched-exam{font-size:.72rem;color:#0ea5e9;margin-top:.1rem;display:block}
        .exec-dday{font-size:.78rem;font-weight:800;padding:.2rem .625rem;border-radius:99px;background:#f1f5f9;color:#475569;white-space:nowrap}
        .exec-dday-open{background:#dcfce7;color:#166534}
        .exec-dday-soon{background:#fef3c7;color:#92400e}
        /* 채용공고 */
        .exec-job-row{display:flex;align-items:center;gap:.5rem;padding:.5rem .75rem;background:#fff;border:1px solid #e2e8f0;border-radius:6px;text-decoration:none;color:inherit;transition:border-color .15s}
        .exec-job-row:hover{border-color:#6366f1}
        .exec-job-main{display:flex;flex-direction:column;gap:.1rem;flex:1;min-width:0}
        .exec-job-title{font-size:.82rem;font-weight:600;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .exec-job-company{font-size:.72rem;color:#64748b}
        .exec-job-close{font-size:.7rem;color:#94a3b8;white-space:nowrap}
        .exec-job-icon{color:#94a3b8;flex-shrink:0}
        /* 훈련과정 */
        .exec-train-row{display:flex;align-items:center;gap:.5rem;padding:.5rem .75rem;background:#fff;border:1px solid #e2e8f0;border-radius:6px}
        .exec-train-main{display:flex;flex-direction:column;gap:.1rem;flex:1;min-width:0}
        .exec-train-name{font-size:.82rem;font-weight:600;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .exec-train-org{font-size:.72rem;color:#64748b}
        .exec-train-rate{font-size:.75rem;font-weight:700;color:#0369a1;white-space:nowrap;flex-shrink:0}

        /* 자격정보 탭 */
        .certinfo-wrap{display:flex;flex-direction:column;gap:.75rem}
        .certinfo-block{display:flex;flex-direction:column;gap:.5rem}
        .certinfo-block-title{font-size:.72rem;font-weight:800;letter-spacing:.06em;color:var(--primary);text-transform:uppercase;margin:0}
        .certinfo-grid{display:flex;flex-direction:column;gap:.3rem}
        .certinfo-row{display:flex;gap:.5rem;align-items:flex-start;padding:.35rem .5rem;background:#fff;border-radius:4px;border:1px solid #f1f5f9}
        .certinfo-key{font-size:.74rem;font-weight:700;color:#475569;width:90px;flex-shrink:0}
        .certinfo-val{font-size:.8rem;color:#1e293b;line-height:1.5;flex:1}
        .certinfo-link{font-size:.8rem;color:var(--primary);text-decoration:none;display:inline-flex;align-items:center;gap:.2rem}
        .certinfo-link:hover{text-decoration:underline}
        .certinfo-src{font-size:.65rem;color:#94a3b8;margin:0;border-top:1px solid #f1f5f9;padding-top:.375rem}
        .certinfo-stat-row{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:.5rem}
        .certinfo-stat-chip{display:flex;flex-direction:column;align-items:center;padding:.35rem .7rem;border-radius:8px;min-width:64px;gap:.1rem}
        .certinfo-stat-label{font-size:.62rem;font-weight:600;opacity:.75}
        .certinfo-stat-val{font-size:.9rem;font-weight:800}
        .certinfo-stat-written{background:#eef2ff;color:#4f46e5}
        .certinfo-stat-practical{background:#ecfeff;color:#0891b2}
        .certinfo-stat-avg{background:#f0fdf4;color:#16a34a}
        .certinfo-stat-freq{background:#fef9c3;color:#92400e}
        .certinfo-stat-diff{background:#fdf4ff;color:#7c3aed}
        .certinfo-stat-type{background:#f0fdf4;color:#15803d}
        .certinfo-job-tags{display:flex;flex-wrap:wrap;gap:.35rem}
        .certinfo-job-tag{padding:.2rem .6rem;background:#f0f9ff;border:1px solid #bae6fd;border-radius:99px;font-size:.75rem;color:#0369a1;font-weight:500}
        .certinfo-job-btn{cursor:pointer;transition:all .15s;border:1px solid #bae6fd}
        .certinfo-job-btn:hover{background:#0369a1;color:#fff;border-color:#0369a1}
        .certinfo-job-selected{background:#0369a1!important;color:#fff!important;border-color:#0369a1!important}
        .certinfo-job-more{background:#f8fafc;border-color:#e2e8f0;color:#64748b}
        .certinfo-job-more-btn{padding:.2rem .75rem;background:#f8fafc;border:1.5px dashed #94a3b8;border-radius:99px;font-size:.75rem;color:#64748b;cursor:pointer;transition:all .15s;font-weight:600}
        .certinfo-job-more-btn:hover{background:var(--primary-light);border-color:var(--primary);color:var(--primary)}
        .certinfo-job-hint{font-size:.62rem;font-weight:500;color:#94a3b8;text-transform:none;letter-spacing:0}
        .jd-scores{display:flex;flex-direction:column;gap:.25rem;background:#e0f2fe;border-radius:6px;padding:.5rem .625rem;margin-bottom:.25rem}
        .jd-score-item{display:grid;grid-template-columns:60px 1fr 24px;align-items:center;gap:.35rem}
        .jd-score-label{font-size:.65rem;font-weight:600;color:#0369a1}
        .jd-score-bar{height:5px;background:#bae6fd;border-radius:99px;overflow:hidden}
        .jd-score-fill{height:100%;border-radius:99px;transition:width .4s}
        .jd-score-num{font-size:.67rem;font-weight:800;text-align:right}
        .job-detail-card{margin-top:.5rem;padding:.75rem .875rem;background:#f0f9ff;border:1px solid #bae6fd;border-radius:var(--radius-sm);display:flex;flex-direction:column;gap:.35rem;animation:fade-in .15s ease}
        @keyframes fade-in{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
        .job-detail-name{font-size:.85rem;font-weight:800;color:#0c4a6e;margin:0 0 .2rem}
        .job-detail-row{display:flex;gap:.5rem;align-items:flex-start}
        .job-detail-row-block{flex-direction:column}
        .job-detail-key{font-size:.7rem;font-weight:700;color:#0369a1;white-space:nowrap;min-width:70px}
        .job-detail-val{font-size:.8rem;color:#0c4a6e;line-height:1.55}
        .job-detail-content{white-space:pre-wrap;word-break:keep-all}
        /* 임금 시각화 */
        .job-salary-viz{display:flex;flex-direction:column;gap:.35rem}
        .salary-range-wrap{padding:.6rem 0 1.2rem;position:relative}
        .salary-range-bar{position:relative;height:6px;background:#bae6fd;border-radius:99px;margin:0 8px}
        .salary-range-fill{position:absolute;inset:0;background:linear-gradient(90deg,#7dd3fc,#0ea5e9);border-radius:99px}
        .salary-dot-wrap{position:absolute;top:-3px;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:2px}
        .salary-dot{width:12px;height:12px;border-radius:50%;background:#0ea5e9;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.2)}
        .salary-dot-val{font-size:.68rem;font-weight:800;color:#0c4a6e;white-space:nowrap;margin-top:6px}
        .salary-dot-label{font-size:.6rem;color:#64748b;white-space:nowrap}
        /* 일자리 전망 시각화 */
        .job-outlook-viz{display:flex;flex-direction:column;gap:.35rem}
        .outlook-stack-wrap{display:flex;flex-direction:column;gap:.35rem}
        .outlook-stack-bar{display:flex;height:12px;border-radius:6px;overflow:hidden;gap:2px}
        .outlook-stack-seg{flex-shrink:0;border-radius:3px;transition:width .3s}
        .outlook-legend{display:flex;gap:.6rem;flex-wrap:wrap}
        .outlook-legend-item{display:flex;align-items:center;gap:.25rem;font-size:.7rem;color:#0c4a6e;font-weight:600}
        .outlook-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
        .exec-section-label{font-size:.68rem;font-weight:800;letter-spacing:.06em;color:#6366f1;text-transform:uppercase;margin:.375rem 0 .25rem;display:block}

        /* session-rates table+chart */
        .sr-tables{display:flex;flex-direction:column;gap:.875rem;margin-top:.5rem}
        .sr-table-wrap{display:flex;flex-direction:column;gap:.3rem}
        .sr-table-head{font-size:.72rem;font-weight:800;letter-spacing:.05em;text-transform:uppercase;padding:.2rem 0}
        .sr-chart-row{padding:.25rem 0 .5rem}

        /* 설문 미완료 배너 */
        .survey-required-banner{
          display:flex;align-items:center;gap:1rem;flex-wrap:wrap;
          padding:1.125rem 1.375rem;
          background:#fff7ed;
          border:1.5px solid #fed7aa;
          border-left:4px solid #f97316;
          border-radius:var(--radius-sm);
        }
        .survey-required-icon{color:#f97316;flex-shrink:0}
        .survey-required-body{flex:1;min-width:0;display:flex;flex-direction:column;gap:.2rem}
        .survey-required-title{font-size:.95rem;font-weight:800;color:#9a3412;margin:0}
        .survey-required-sub{font-size:.82rem;color:#c2410c;margin:0;line-height:1.55}
        .survey-required-btn{white-space:nowrap;flex-shrink:0}
      `}</style>
    </div>
  );
};

export default Recommendation;
