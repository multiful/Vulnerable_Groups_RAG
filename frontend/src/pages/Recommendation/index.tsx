// Content Hash: SHA256:TBD
import React, { useState, useMemo, useEffect, useCallback, useDeferredValue, memo } from 'react';
import { CertFlowDiagram } from '../../components/charts/CertFlowDiagram';
import { getCertCandidates } from '../../api/client';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Search, Map, FileText, ChevronDown, AlertCircle,
  Loader2, ArrowLeft, ArrowRight, X, BookOpen, ExternalLink,
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
  const passM = cert.text_for_dense.match(/3년 평균 합격률:\s*([\d.]+)%/);
  const sessM = cert.text_for_dense.match(/연간 검정 횟수:\s*(연 \d+회)/);
  const parts: string[] = [];
  if (domain) parts.push(domain + ' 분야');
  if (jobs.length > 0) {
    parts.push(jobs.length > 2
      ? `${jobs.slice(0, 2).join(', ')} 외 ${jobs.length - 2}개 직무`
      : jobs.join(', ') + ' 직무');
  }
  if (sessM) parts.push(sessM[1] + ' 시험');
  if (passM) parts.push(`합격률 ${parseFloat(passM[1]).toFixed(0)}%`);
  return parts.join(' · ');
}

const RISK_LABEL: Record<string, string> = {
  '1': '1단계', '2': '2단계', '3': '3단계', '4': '4단계', '5': '5단계',
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

/* ── Memoized cert card: evidence/dag 상태 변경 시 재렌더 방지 ── */
const CertCard = memo(({
  cert, onEvidence, onDag, onRoadmap,
}: {
  cert: CertCandidate;
  onEvidence: (id: string) => void;
  onDag: (id: string) => void;
  onRoadmap: (id: string) => void;
}) => {
  const summary = buildCertSummary(cert);
  const color   = gradeColor(cert.cert_grade_tier);
  return (
    <div className="card cert-card">
      <div className="cert-top">
        <div className="cert-top-row">
          <span className={`badge ${gradeBadgeClass(cert.cert_grade_tier)}`}>
            {GRADE_LABEL[cert.cert_grade_tier] ?? cert.cert_grade_tier}
          </span>
          <span className="cert-issuer">{cert.issuer}</span>
        </div>
        <h3 className="cert-name">{cert.cert_name}</h3>
        <p className="cert-summary">{summary}</p>
      </div>
      <div className="cert-actions">
        <button className="text-btn evidence-btn"
          onClick={() => { onEvidence(cert.cert_id); onDag(cert.cert_id); }}
          style={{ color }}>
          <FileText size={13} /> 추천 이유
        </button>
        <button className="text-btn roadmap-btn" onClick={() => onRoadmap(cert.cert_id)}>
          <Map size={13} /> 로드맵 <ArrowRight size={12} />
        </button>
      </div>
    </div>
  );
});

const Recommendation: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const stageParam  = searchParams.get('stage') ?? '';
  const domainParam = searchParams.get('domain') ?? '';
  const domainName  = searchParams.get('domainName') ?? '';
  const jobParam    = searchParams.get('job') ?? '';
  const jobName     = searchParams.get('jobName') ?? '';
  const certIdParam = searchParams.get('cert') ?? '';

  const [allCerts, setAllCerts] = useState<CertCandidate[]>([]);
  const [certsLoading, setCertsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGrade, setSelectedGrade] = useState('');
  const deferredQuery = useDeferredValue(searchQuery);

  const [evidence, setEvidence] = useState<EvidenceState>({
    loading: false, rows: [], error: null, fetched: false, certId: '',
  });
  const [showEvidence, setShowEvidence] = useState(false);
  const [dag, setDag] = useState<DagState>({
    loading: false, predecessors: [], successors: [], certId: '', fetched: false,
  });

  useEffect(() => {
    let cancelled = false;
    getCertCandidates()
      .then((data: CertCandidate[]) => { if (!cancelled) { setAllCerts(data); setCertsLoading(false); } })
      .catch((err: Error) => { if (!cancelled) { setFetchError(err.message); setCertsLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  const riskId    = RISK_IDS[stageParam] ?? '';
  const riskLabel = RISK_LABEL[stageParam] ?? '';

  const filtered = useMemo(() => {
    return allCerts.filter(cert => {
      if (riskId      && !cert.recommended_risk_stages.includes(riskId))  return false;
      if (domainParam && !cert.related_domains.includes(domainParam))      return false;
      if (jobParam    && !cert.related_jobs.includes(jobParam))            return false;
      if (selectedGrade && cert.cert_grade_tier !== selectedGrade)         return false;
      const q = deferredQuery;
      if (q && !cert.cert_name.includes(q)) return false;
      return true;
    });
  }, [allCerts, riskId, domainParam, jobParam, selectedGrade, deferredQuery]);

  const featuredCert = useMemo(
    () => allCerts.find(c => c.cert_id === certIdParam) ?? null,
    [allCerts, certIdParam],
  );

  const fetchEvidence = useCallback(async (certId: string) => {
    setEvidence({ loading: true, rows: [], error: null, fetched: false, certId });
    setShowEvidence(true);
    try {
      const res = await fetch('/api/v1/recommendations/evidence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cert_id: certId }),
      });
      const json = await res.json();
      if (json.success) {
        setEvidence({ loading: false, rows: json.data?.evidence ?? [], error: null, fetched: true, certId });
      } else {
        setEvidence({ loading: false, rows: [], error: json.error?.message ?? '오류 발생', fetched: true, certId });
      }
    } catch {
      setEvidence({ loading: false, rows: [], error: '서버에 연결할 수 없습니다.', fetched: true, certId });
    }
  }, []);

  const fetchDag = useCallback(async (certId: string) => {
    setDag({ loading: true, predecessors: [], successors: [], certId, fetched: false });
    try {
      const res = await fetch(`/api/v1/recommendations/related?cert_id=${encodeURIComponent(certId)}`);
      const json = await res.json();
      if (json.success) {
        setDag({
          loading: false,
          predecessors: json.data?.predecessors ?? [],
          successors: json.data?.successors ?? [],
          certId,
          fetched: true,
        });
      } else {
        setDag({ loading: false, predecessors: [], successors: [], certId, fetched: true });
      }
    } catch {
      setDag({ loading: false, predecessors: [], successors: [], certId, fetched: true });
    }
  }, []);

  const goToRoadmap = useCallback((certId: string) => {
    const p = new URLSearchParams();
    if (stageParam)  p.set('stage', stageParam);
    if (domainParam) p.set('domain', domainParam);
    if (domainName)  p.set('domainName', domainName);
    p.set('cert', certId);
    navigate(`/roadmap?${p.toString()}`);
  }, [stageParam, domainParam, domainName, navigate]);

  const evidenceCertName = allCerts.find(c => c.cert_id === evidence.certId)?.cert_name ?? evidence.certId;

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

      {featuredCert && (
        <div className="featured-cert card" style={{ borderLeftColor: gradeColor(featuredCert.cert_grade_tier) }}>
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
            <button className="btn-primary" onClick={() => { fetchEvidence(featuredCert.cert_id); fetchDag(featuredCert.cert_id); }}>
              <FileText size={15} /> 왜 추천됐나요
            </button>
            <button className="btn-ghost" onClick={() => goToRoadmap(featuredCert.cert_id)}>
              <Map size={15} /> 로드맵 보기
            </button>
          </div>
        </div>
      )}

      {showEvidence && (
        <div className="evidence-panel card">
          <div className="ev-header">
            <div className="ev-header-left">
              <BookOpen size={15} style={{ color: 'var(--primary)', flexShrink: 0 }} />
              <span className="ev-title">{evidenceCertName}을 추천하는 이유</span>
            </div>
            <button className="ev-close" onClick={() => setShowEvidence(false)}><X size={15} /></button>
          </div>

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
              <p className="ev-intro">공식 문서에서 가져온 자료입니다. 이 내용을 바탕으로 추천했습니다.</p>
              {evidence.rows.map((row, i) => {
                const pct = row.similarity != null ? Math.round(row.similarity * 100) : null;
                const isLocal = row.source_type === 'candidate' || row.source_type === 'local_candidates';
                return (
                  <div key={row.chunk_id || i} className="ev-row">
                    <div className="ev-row-header">
                      {row.section_path?.length > 0 && (
                        <span className="ev-section-label">{row.section_path.join(' › ')}</span>
                      )}
                      {pct != null && (
                        <div className="ev-score-wrap">
                          <div className="ev-score-track">
                            <div className="ev-score-fill" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="ev-score-pct">관련도 {pct}%</span>
                        </div>
                      )}
                      {isLocal && <span className="ev-src-tag ev-src-local">후보 데이터</span>}
                      {row.source_url && (
                        <a href={row.source_url} target="_blank" rel="noreferrer" className="ev-link">
                          <ExternalLink size={11} /> 원문 보기
                        </a>
                      )}
                    </div>
                    <p className="ev-snippet">{row.snippet}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      <div className="card filter-card">
        <div className="search-wrapper">
          <Search size={16} className="search-icon" />
          <input type="text" className="input search-input" placeholder="자격증명 검색…"
            value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
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
            <p className="result-count">추천 자격증 <span className="count-num">{filtered.length}</span>건</p>
            <div className="cert-grid-scroll">
              <div className="cert-grid">
                {filtered.slice(0, 60).map(cert => (
                  <CertCard
                    key={cert.candidate_id}
                    cert={cert}
                    onEvidence={fetchEvidence}
                    onDag={fetchDag}
                    onRoadmap={goToRoadmap}
                  />
                ))}
                {filtered.length === 0 && (
                  <div className="no-results">
                    {jobParam && domainParam ? (
                      <>
                        <p className="no-results-title">"{domainName}" 분야와 "{jobName}" 직무가 겹치는 자격증이 없습니다.</p>
                        <p className="no-results-sub">
                          선택한 도메인과 직무가 서로 다른 분야에 속해 있을 수 있습니다.<br />
                          직무 선택 없이 도메인만으로 다시 검색해보세요.
                        </p>
                      </>
                    ) : (
                      <>
                        <p className="no-results-title">조건에 맞는 자격증이 없습니다.</p>
                        <p className="no-results-sub">검색어나 등급 필터를 바꿔보세요.</p>
                      </>
                    )}
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
        .evidence-panel{padding:1.25rem;display:flex;flex-direction:column;gap:.875rem;border-left:3px solid var(--primary)}
        .ev-header{display:flex;align-items:center;justify-content:space-between;gap:.75rem}
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
        .ev-score-wrap{display:flex;align-items:center;gap:.3rem;margin-left:auto}
        .ev-score-track{width:44px;height:4px;background:var(--border);border-radius:99px;overflow:hidden}
        .ev-score-fill{height:100%;background:var(--primary);border-radius:99px}
        .ev-score-pct{font-size:.66rem;font-weight:700;color:var(--primary);white-space:nowrap}
        .ev-section-label{font-size:.75rem;font-weight:700;color:var(--primary);padding:.1rem .5rem;background:var(--primary-light);border-radius:var(--radius-xs)}
        .ev-section{font-size:.75rem;color:var(--text-light)}
        .ev-link{display:inline-flex;align-items:center;gap:.25rem;font-size:.75rem;color:var(--secondary);text-decoration:none;margin-left:auto}
        .ev-link:hover{text-decoration:underline}
        .ev-snippet{font-size:.855rem;color:var(--text-muted);line-height:1.7;border-left:3px solid var(--primary-light);padding-left:.75rem}
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
        .result-count{margin-bottom:.875rem;font-size:.9rem;color:var(--text-muted)}
        .count-num{color:var(--primary);font-size:1.2rem;font-weight:800}
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
        .no-results{grid-column:1/-1;text-align:center;padding:2.5rem 1.25rem;line-height:1.8;display:flex;flex-direction:column;gap:.5rem}
        .no-results-title{font-size:.95rem;font-weight:700;color:var(--text)}
        .no-results-sub{font-size:.85rem;color:var(--text-muted);line-height:1.65}
      `}</style>
    </div>
  );
};

export default Recommendation;
