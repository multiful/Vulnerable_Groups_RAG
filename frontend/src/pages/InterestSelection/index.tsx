// Content Hash: SHA256:TBD
import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, ArrowLeft, ChevronDown, ChevronUp, Briefcase, AlertTriangle } from 'lucide-react';
import { loadPipeline, savePipeline } from '../../utils/pipelineState';

/* ── 도메인 taxonomy (domain_master.csv 기반) ── */
interface DomainItem { id: string; name: string; }
interface DomainGroup { top: string; emoji: string; items: DomainItem[]; }

const DOMAIN_GROUPS: DomainGroup[] = [
  {
    top: 'IT/디지털', emoji: 'IT',
    items: [
      { id: 'domain_0001', name: '데이터/AI' },
      { id: 'domain_0002', name: '소프트웨어개발' },
      { id: 'domain_0003', name: 'IT인프라/보안' },
      { id: 'domain_0004', name: '정보통신/무선' },
    ],
  },
  {
    top: '엔지니어링/산업기술', emoji: '기술',
    items: [
      { id: 'domain_0005', name: '전기/전자' },
      { id: 'domain_0006', name: '기계/제조' },
      { id: 'domain_0007', name: '재료/금속' },
      { id: 'domain_0008', name: '화학/바이오' },
      { id: 'domain_0009', name: '에너지/원자력' },
      { id: 'domain_0010', name: '건축/실내건축' },
      { id: 'domain_0011', name: '토목/측량/공간정보' },
      { id: 'domain_0012', name: '환경/안전' },
      { id: 'domain_0013', name: '자동차/모빌리티정비' },
      { id: 'domain_0014', name: '소방/방재' },
      { id: 'domain_0015', name: '비파괴검사/품질검사' },
    ],
  },
  {
    top: '경영/비즈니스', emoji: '경영',
    items: [
      { id: 'domain_0016', name: '금융/회계' },
      { id: 'domain_0017', name: '경영/사무' },
      { id: 'domain_0018', name: '유통/물류/무역' },
      { id: 'domain_0019', name: '영업/CS' },
      { id: 'domain_0020', name: '부동산/감정/주택관리' },
      { id: 'domain_0021', name: '공공/행정' },
      { id: 'domain_0022', name: '법률' },
    ],
  },
  {
    top: '보건/복지', emoji: '보건',
    items: [
      { id: 'domain_0023', name: '의료/보건' },
      { id: 'domain_0024', name: '사회복지/상담' },
      { id: 'domain_0025', name: '스포츠/레저/재활' },
      { id: 'domain_0026', name: '반려동물/생활케어' },
    ],
  },
  {
    top: '교육/생활서비스', emoji: '교육',
    items: [
      { id: 'domain_0027', name: '교육' },
      { id: 'domain_0028', name: '언어/문서/속기' },
      { id: 'domain_0029', name: '관광/항공/호텔' },
      { id: 'domain_0030', name: '조리/식품' },
      { id: 'domain_0031', name: '미용/패션' },
      { id: 'domain_0032', name: '의류/패션제작' },
    ],
  },
  {
    top: '크리에이티브/미디어', emoji: '미디어',
    items: [
      { id: 'domain_0033', name: '디자인' },
      { id: 'domain_0034', name: '콘텐츠/미디어' },
      { id: 'domain_0035', name: '공예/목재/주얼리' },
      { id: 'domain_0036', name: '음악/공연' },
      { id: 'domain_0037', name: '문화유산/보존수리' },
    ],
  },
  {
    top: '1차산업/자원', emoji: '산업',
    items: [
      { id: 'domain_0038', name: '농림/축산/수산' },
      { id: 'domain_0039', name: '광산' },
    ],
  },
  {
    top: '모빌리티/운송', emoji: '운송',
    items: [
      { id: 'domain_0040', name: '철도/교통운송' },
      { id: 'domain_0041', name: '선박/해양' },
      { id: 'domain_0042', name: '항공/조종' },
    ],
  },
  {
    top: '국방/특수', emoji: '국방',
    items: [
      { id: 'domain_0043', name: '국방/특수' },
    ],
  },
];

/* ── 직무 taxonomy (job_master.csv 기반) ── */
interface JobItem { id: string; name: string; }
interface JobGroup { top: string; items: JobItem[]; }

const JOB_GROUPS: JobGroup[] = [
  {
    top: 'IT/데이터',
    items: [
      { id: 'job_0001', name: '데이터 분석' }, { id: 'job_0002', name: '데이터 엔지니어' },
      { id: 'job_0003', name: '데이터 사이언스' }, { id: 'job_0004', name: 'BI/리포팅 분석' },
      { id: 'job_0005', name: 'AI 개발' }, { id: 'job_0006', name: '머신러닝 엔지니어' },
      { id: 'job_0007', name: 'MLOps 엔지니어' }, { id: 'job_0008', name: 'AI 서비스 기획' },
    ],
  },
  {
    top: '소프트웨어/플랫폼',
    items: [
      { id: 'job_0009', name: '백엔드 개발' }, { id: 'job_0010', name: '프론트엔드 개발' },
      { id: 'job_0011', name: '풀스택 개발' }, { id: 'job_0012', name: '웹 개발' },
      { id: 'job_0013', name: '모바일 앱 개발' }, { id: 'job_0014', name: 'API/서버 개발' },
      { id: 'job_0015', name: '게임 개발' }, { id: 'job_0016', name: '게임 서버 개발' },
      { id: 'job_0017', name: '클라이언트 개발' }, { id: 'job_0018', name: '임베디드 개발' },
      { id: 'job_0019', name: '테스트/QA 엔지니어' },
    ],
  },
  {
    top: '인프라/운영/보안',
    items: [
      { id: 'job_0020', name: '시스템 운영' }, { id: 'job_0021', name: '서버 운영' },
      { id: 'job_0022', name: '네트워크 운영' }, { id: 'job_0023', name: '클라우드 엔지니어' },
      { id: 'job_0024', name: 'DevOps 엔지니어' }, { id: 'job_0025', name: '정보보안' },
      { id: 'job_0026', name: '데이터베이스 운영' }, { id: 'job_0027', name: '정보통신 엔지니어' },
      { id: 'job_0028', name: '무선통신 운영' }, { id: 'job_0029', name: '디지털포렌식' },
    ],
  },
  {
    top: '엔지니어링/산업기술',
    items: [
      { id: 'job_0030', name: '전기 엔지니어' }, { id: 'job_0031', name: '전자 엔지니어' },
      { id: 'job_0032', name: '반도체 장비' }, { id: 'job_0033', name: '제어/PLC 엔지니어' },
      { id: 'job_0034', name: '기계설계' }, { id: 'job_0035', name: '기계정비' },
      { id: 'job_0036', name: '생산관리' }, { id: 'job_0037', name: '생산기술' },
      { id: 'job_0038', name: '공정관리' }, { id: 'job_0039', name: '품질관리' },
      { id: 'job_0040', name: '비파괴검사' }, { id: 'job_0041', name: '산업안전관리' },
      { id: 'job_0042', name: '소방/방재 관리' }, { id: 'job_0043', name: '환경관리' },
      { id: 'job_0044', name: '에너지 설비 운영' }, { id: 'job_0045', name: '원자력 기술' },
    ],
  },
  {
    top: '건설/공간/인프라',
    items: [
      { id: 'job_0046', name: '건축 설계' }, { id: 'job_0047', name: '건축 시공' },
      { id: 'job_0048', name: '실내건축' }, { id: 'job_0049', name: '토목 설계' },
      { id: 'job_0050', name: '도시계획' }, { id: 'job_0051', name: '측량/GIS' },
      { id: 'job_0052', name: '현장관리' }, { id: 'job_0053', name: '건설안전관리' },
      { id: 'job_0054', name: '국가유산 보존수리' },
    ],
  },
  {
    top: '모빌리티/운송',
    items: [
      { id: 'job_0055', name: '철도 운영/정비' }, { id: 'job_0056', name: '철도 신호' },
      { id: 'job_0057', name: '철도 차량 정비' }, { id: 'job_0058', name: '자동차 정비' },
      { id: 'job_0059', name: '자동차 진단평가' }, { id: 'job_0060', name: '선박 운항' },
      { id: 'job_0061', name: '선박 기관' }, { id: 'job_0062', name: '선박 정비' },
      { id: 'job_0063', name: '항공 운항' }, { id: 'job_0064', name: '항공 정비' },
      { id: 'job_0065', name: '물류/운송 운영' },
    ],
  },
  {
    top: '경영/회계/금융',
    items: [
      { id: 'job_0066', name: '세무' }, { id: 'job_0067', name: '회계' },
      { id: 'job_0068', name: '재무' }, { id: 'job_0069', name: '금융사무' },
      { id: 'job_0070', name: '자산관리' }, { id: 'job_0071', name: '보험보상' },
      { id: 'job_0072', name: '리스크 관리' }, { id: 'job_0073', name: '경영지원' },
      { id: 'job_0074', name: '일반사무' }, { id: 'job_0075', name: '인사' },
      { id: 'job_0076', name: '총무' }, { id: 'job_0077', name: '마케팅' },
      { id: 'job_0078', name: '영업관리' }, { id: 'job_0079', name: '무역사무' },
      { id: 'job_0080', name: '물류관리' }, { id: 'job_0081', name: '유통관리' },
      { id: 'job_0082', name: '공공행정' }, { id: 'job_0083', name: '정책기획/평가' },
      { id: 'job_0084', name: '법무사무' }, { id: 'job_0085', name: '부동산/주택관리' },
      { id: 'job_0086', name: '감정평가' },
    ],
  },
  {
    top: '보건/복지',
    items: [
      { id: 'job_0087', name: '간호사' }, { id: 'job_0088', name: '보건의료정보' },
      { id: 'job_0089', name: '병원행정' }, { id: 'job_0090', name: '의무기록 관리' },
      { id: 'job_0091', name: '임상지원' }, { id: 'job_0092', name: '의료코디네이터' },
      { id: 'job_0093', name: '응급구조' }, { id: 'job_0094', name: '사회복지사' },
      { id: 'job_0095', name: '상담사' }, { id: 'job_0096', name: '청소년지도' },
      { id: 'job_0097', name: '직업상담' }, { id: 'job_0098', name: '복지행정' },
      { id: 'job_0099', name: '사례관리' }, { id: 'job_0100', name: '재활지원' },
    ],
  },
  {
    top: '교육/생활서비스',
    items: [
      { id: 'job_0101', name: '교육' }, { id: 'job_0102', name: '평생교육' },
      { id: 'job_0103', name: '직업교육' }, { id: 'job_0104', name: '한국어교육' },
      { id: 'job_0105', name: '호텔 서비스' }, { id: 'job_0106', name: '관광통역' },
      { id: 'job_0107', name: '여행기획' }, { id: 'job_0108', name: '조리' },
      { id: 'job_0109', name: '제과/제빵' }, { id: 'job_0110', name: '바리스타' },
      { id: 'job_0111', name: '식품품질관리' }, { id: 'job_0112', name: '영양/급식' },
      { id: 'job_0113', name: '외식서비스 운영' }, { id: 'job_0114', name: '헤어디자인' },
      { id: 'job_0115', name: '메이크업' }, { id: 'job_0116', name: '피부관리' },
      { id: 'job_0117', name: '반려동물 관리' }, { id: 'job_0118', name: '스포츠지도' },
      { id: 'job_0119', name: '생활건강관리' },
    ],
  },
  {
    top: '콘텐츠/디자인/예술',
    items: [
      { id: 'job_0120', name: '시각디자인' }, { id: 'job_0121', name: 'UI/UX 디자인' },
      { id: 'job_0122', name: '편집디자인' }, { id: 'job_0123', name: '산업디자인' },
      { id: 'job_0124', name: '영상편집' }, { id: 'job_0125', name: '콘텐츠 제작' },
      { id: 'job_0126', name: '방송/미디어 제작' }, { id: 'job_0127', name: '3D 콘텐츠 제작' },
      { id: 'job_0128', name: '문예창작' }, { id: 'job_0129', name: '인쇄/출판 제작' },
      { id: 'job_0130', name: '공예/주얼리 제작' }, { id: 'job_0131', name: '음악/공연 실무' },
      { id: 'job_0132', name: '패션 제작' },
    ],
  },
  {
    top: '1차산업/자원',
    items: [
      { id: 'job_0133', name: '농업기술' }, { id: 'job_0134', name: '스마트팜 운영' },
      { id: 'job_0135', name: '산림관리' }, { id: 'job_0136', name: '축산관리' },
      { id: 'job_0137', name: '수산양식' }, { id: 'job_0138', name: '광업/자원개발' },
    ],
  },
  {
    top: '국방/특수',
    items: [
      { id: 'job_0139', name: '국방사업관리' }, { id: 'job_0140', name: '무인기 운용' },
      { id: 'job_0141', name: '폭발물 처리' }, { id: 'job_0142', name: '특수 안전관리' },
    ],
  },
];

/* ── 도메인 그룹 → 호환 직무 그룹 매핑 (불일치 경고용) ── */
const DOMAIN_JOB_COMPAT: Record<string, string[]> = {
  'IT/디지털':        ['IT/데이터', '소프트웨어/플랫폼', '인프라/운영/보안'],
  '엔지니어링/산업기술': ['엔지니어링/산업기술', '건설/공간/인프라'],
  '경영/비즈니스':    ['경영/회계/금융'],
  '보건/복지':        ['보건/복지'],
  '교육/생활서비스':  ['교육/생활서비스'],
  '크리에이티브/미디어': ['콘텐츠/디자인/예술'],
  '1차산업/자원':     ['1차산업/자원'],
  '모빌리티/운송':    ['모빌리티/운송'],
  '국방/특수':        ['국방/특수'],
};

function getDomainGroup(domainId: string | null): string | null {
  if (!domainId) return null;
  return DOMAIN_GROUPS.find(g => g.items.some(i => i.id === domainId))?.top ?? null;
}

function getJobGroup(jobId: string | null): string | null {
  if (!jobId) return null;
  return JOB_GROUPS.find(g => g.items.some(i => i.id === jobId))?.top ?? null;
}

function isMismatch(domainId: string | null, jobId: string | null): boolean {
  if (!domainId || !jobId) return false;
  const dg = getDomainGroup(domainId);
  const jg = getJobGroup(jobId);
  if (!dg || !jg) return false;
  const compatible = DOMAIN_JOB_COMPAT[dg];
  if (!compatible) return false;
  return !compatible.includes(jg);
}

const RISK_STAGE_LABELS: Record<string, string> = {
  '1': '1단계 (취업 안정권)',
  '2': '2단계 (준비 활성)',
  '3': '3단계 (준비 정체)',
  '4': '4단계 (고위험군)',
  '5': '5단계 (최고위험군)',
};

const InterestSelection: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // URL에 stage가 없으면 세션에서 복원 (헤더 내비게이션 등으로 파라미터 손실 시)
  const [pSession] = useState(() => loadPipeline());
  const stage = searchParams.get('stage') || pSession.stage || '';

  const [selectedDomain, setSelectedDomain] = useState<DomainItem | null>(null);
  const [selectedJob, setSelectedJob] = useState<JobItem | null>(null);
  const [majorInput, setMajorInput] = useState(pSession.major ?? '');
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({ 'IT/디지털': true });
  const [openJobGroups, setOpenJobGroups] = useState<Record<string, boolean>>({});
  const [jobSectionOpen, setJobSectionOpen] = useState(false);

  function toggleGroup(top: string) {
    setOpenGroups(prev => ({ ...prev, [top]: !prev[top] }));
  }
  function toggleJobGroup(top: string) {
    setOpenJobGroups(prev => ({ ...prev, [top]: !prev[top] }));
  }

  function selectDomain(item: DomainItem) {
    setSelectedDomain(prev => (prev?.id === item.id ? null : item));
  }
  function selectJob(item: JobItem) {
    setSelectedJob(prev => (prev?.id === item.id ? null : item));
  }

  function handleNext() {
    if (!selectedDomain) return;
    const params = new URLSearchParams();
    if (stage) params.set('stage', stage);
    params.set('domain', selectedDomain.id);
    params.set('domainName', selectedDomain.name);
    if (selectedJob) {
      params.set('job', selectedJob.id);
      params.set('jobName', selectedJob.name);
    }
    const trimmedMajor = majorInput.trim();
    if (trimmedMajor) params.set('major', trimmedMajor);
    savePipeline({
      stage: stage || undefined,
      domain: selectedDomain.id,
      domainName: selectedDomain.name,
      job: selectedJob?.id,
      jobName: selectedJob?.name,
      major: trimmedMajor || undefined,
    });
    navigate(`/roadmap?${params.toString()}`);
  }

  const stageLabel = stage ? RISK_STAGE_LABELS[stage] : '';

  return (
    <div className="interest-wrap">

      {/* Header */}
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} /> 뒤로
        </button>
        <h1 className="page-title">관심 분야 선택</h1>
        <p className="page-desc">
          {stageLabel
            ? <><strong style={{ color: 'var(--primary)' }}>{stageLabel}</strong> 기준으로 어떤 분야에 관심이 있나요?</>
            : '어떤 분야에 관심이 있나요?'}
        </p>
      </div>

      {/* Selected summary banner */}
      {(selectedDomain || selectedJob) && (
        <div className="selected-banner">
          {selectedDomain && (
            <span className="sel-item">
              <span className="sel-tag domain-tag">분야</span>
              <span className="selected-name">{selectedDomain.name}</span>
              <button className="selected-clear" onClick={() => setSelectedDomain(null)}>×</button>
            </span>
          )}
          {selectedJob && (
            <span className="sel-item">
              <span className="sel-tag job-tag">직무</span>
              <span className="selected-name selected-name-job">{selectedJob.name}</span>
              <button className="selected-clear" onClick={() => setSelectedJob(null)}>×</button>
            </span>
          )}
        </div>
      )}

      {/* Section 1: 관심 분야 */}
      <div className="section-header-row">
        <span className="section-num">1</span>
        <span className="section-label">관심 분야를 하나 선택하세요</span>
        <span className="section-required">필수</span>
      </div>
      <div className="groups-list">
        {DOMAIN_GROUPS.map(group => {
          const isOpen = !!openGroups[group.top];
          const hasSelected = group.items.some(i => i.id === selectedDomain?.id);
          return (
            <div key={group.top} className={`group-card card ${hasSelected ? 'group-card-active' : ''}`}>
              <button className="group-header" onClick={() => toggleGroup(group.top)} type="button">
                <span className="group-emoji">{group.emoji}</span>
                <span className="group-top">{group.top}</span>
                {hasSelected && <span className="group-sel-badge">선택됨</span>}
                <span className="group-chevron">
                  {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </span>
              </button>
              {isOpen && (
                <div className="group-chips">
                  {group.items.map(item => {
                    const isSel = selectedDomain?.id === item.id;
                    return (
                      <button
                        key={item.id} type="button"
                        className={`domain-chip ${isSel ? 'domain-chip-selected' : ''}`}
                        onClick={() => selectDomain(item)}
                      >
                        {item.name}
                        {isSel && <span className="chip-check">✓</span>}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Section 2: 희망 직무 (optional) */}
      <div className="section-header-row" style={{ marginTop: '.5rem' }}>
        <span className="section-num">2</span>
        <span className="section-label">희망 직무를 선택하세요</span>
        <span className="section-optional">선택 사항</span>
        <button
          className="job-toggle-btn"
          onClick={() => setJobSectionOpen(p => !p)}
          type="button"
        >
          <Briefcase size={13} />
          {jobSectionOpen ? '접기' : (selectedJob ? selectedJob.name : '직무 선택하기')}
          {jobSectionOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>
      </div>

      {jobSectionOpen && (
        <div className="groups-list job-groups-list">
          {JOB_GROUPS.map(group => {
            const isOpen = !!openJobGroups[group.top];
            const hasSelected = group.items.some(i => i.id === selectedJob?.id);
            return (
              <div key={group.top} className={`group-card card ${hasSelected ? 'group-card-job-active' : ''}`}>
                <button className="group-header" onClick={() => toggleJobGroup(group.top)} type="button">
                  <span className="group-top">{group.top}</span>
                  {hasSelected && <span className="group-sel-badge job-sel-badge">선택됨</span>}
                  <span className="group-chevron">
                    {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </span>
                </button>
                {isOpen && (
                  <div className="group-chips">
                    {group.items.map(item => {
                      const isSel = selectedJob?.id === item.id;
                      return (
                        <button
                          key={item.id} type="button"
                          className={`domain-chip job-chip ${isSel ? 'job-chip-selected' : ''}`}
                          onClick={() => selectJob(item)}
                        >
                          {item.name}
                          {isSel && <span className="chip-check">✓</span>}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 도메인·직무 불일치 경고 */}
      {isMismatch(selectedDomain?.id ?? null, selectedJob?.id ?? null) && (
        <div className="mismatch-warn">
          <AlertTriangle size={15} className="mismatch-icon" />
          <div className="mismatch-body">
            <strong>선택한 분야와 직무가 잘 맞지 않을 수 있어요.</strong>
            <span className="mismatch-desc">
              &nbsp;예를 들어 <em>{getDomainGroup(selectedDomain?.id ?? null)}</em> 분야에서는
              주로 <em>{DOMAIN_JOB_COMPAT[getDomainGroup(selectedDomain?.id ?? null) ?? '']?.join(' · ')}</em> 직무 계열이 추천됩니다.
              그래도 현재 선택을 유지하고 계속 진행하셔도 됩니다.
            </span>
          </div>
        </div>
      )}

      {/* 전공 입력 (선택) */}
      <div className="major-input-section">
        <div className="section-header-row">
          <span className="section-num">3</span>
          <span className="section-label">전공 입력 <span className="section-optional">선택</span></span>
        </div>
        <p className="major-input-desc">전공을 입력하면 해당 전공 취득자 사례 기반 자격증을 우선 추천합니다.</p>
        <input
          className="major-text-input"
          type="text"
          placeholder="예: 컴퓨터공학, 전기공학, 경영학, 사회복지학…"
          value={majorInput}
          onChange={e => setMajorInput(e.target.value)}
          maxLength={40}
        />
      </div>

      {/* Footer CTA */}
      <div className="interest-footer">
        <button className="btn-ghost" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} /> 이전
        </button>
        <button
          className="btn-primary interest-next-btn"
          disabled={!selectedDomain}
          onClick={handleNext}
        >
          {selectedDomain
            ? selectedJob
              ? <><strong>{selectedDomain.name}</strong>  <strong>{selectedJob.name}</strong> 로드맵 보기 <ArrowRight size={15} /></>
              : <><strong>{selectedDomain.name}</strong> 로드맵 보기 <ArrowRight size={15} /></>
            : '분야를 선택해주세요'}
        </button>
      </div>

      <style>{`
        .interest-wrap {
          max-width: 680px; margin: 0 auto;
          display: flex; flex-direction: column; gap: 1.25rem;
        }
        .back-btn {
          display: inline-flex; align-items: center; gap: .35rem;
          font-size: .85rem; font-weight: 500; color: var(--text-muted);
          margin-bottom: .25rem; background: none; border: none;
          cursor: pointer; padding: 0; transition: color .15s; width: fit-content;
        }
        .back-btn:hover { color: var(--primary); }

        .section-header-row {
          display: flex; align-items: center; gap: .5rem; flex-wrap: wrap;
        }
        .section-num {
          width: 20px; height: 20px; border-radius: 50%;
          background: var(--primary); color: #fff;
          font-size: .68rem; font-weight: 800;
          display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        }
        .section-label { font-size: .9rem; font-weight: 700; color: var(--text); flex: 1; }
        .section-required {
          padding: .15rem .5rem; background: var(--primary-light); color: var(--primary);
          border-radius: var(--radius-full); font-size: .65rem; font-weight: 700;
          border: 1px solid rgba(99,102,241,.2);
        }
        .section-optional {
          padding: .15rem .5rem; background: var(--surface-2); color: var(--text-light);
          border-radius: var(--radius-full); font-size: .65rem; font-weight: 700;
          border: 1px solid var(--border);
        }

        .job-toggle-btn {
          display: inline-flex; align-items: center; gap: .35rem;
          padding: .3rem .75rem; border: 1.5px solid var(--secondary);
          border-radius: var(--radius-full); background: var(--secondary-light);
          color: var(--secondary); font-size: .78rem; font-weight: 700;
          cursor: pointer; transition: all .18s; white-space: nowrap; margin-left: auto;
        }
        .job-toggle-btn:hover { background: var(--secondary); color: #fff; }

        .selected-banner {
          display: flex; align-items: center; gap: .75rem; flex-wrap: wrap;
          padding: .625rem 1rem;
          background: var(--surface-2); border: 1px solid var(--border);
          border-radius: var(--radius-sm); animation: fade-in .2s ease;
        }
        @keyframes fade-in { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
        .sel-item { display: flex; align-items: center; gap: .375rem; }
        .sel-tag {
          padding: .1rem .4rem; border-radius: 3px;
          font-size: .62rem; font-weight: 700; flex-shrink: 0;
        }
        .domain-tag { background: var(--primary-light); color: var(--primary); }
        .job-tag { background: var(--secondary-light); color: var(--secondary); }
        .selected-name { font-size: .9rem; font-weight: 700; color: var(--primary); }
        .selected-name-job { color: var(--secondary); }
        .selected-clear {
          background: none; border: none; cursor: pointer;
          font-size: 1.1rem; color: var(--text-light); padding: 0 .25rem;
          line-height: 1; transition: color .15s;
        }
        .selected-clear:hover { color: var(--danger); }

        .groups-list { display: flex; flex-direction: column; gap: .625rem; }
        .job-groups-list { animation: fade-in .15s ease; }

        .group-card { padding: 0; overflow: hidden; }
        .group-card-active { border-color: rgba(99,102,241,.3); box-shadow: 0 0 0 3px var(--primary-glow); }
        .group-card-job-active { border-color: rgba(14,165,233,.3); box-shadow: 0 0 0 3px rgba(14,165,233,.1); }

        .group-header {
          display: flex; align-items: center; gap: .75rem;
          padding: .875rem 1.125rem; width: 100%;
          background: none; border: none; cursor: pointer;
          text-align: left; transition: background .15s;
        }
        .group-header:hover { background: var(--surface-2); }
        .group-emoji {
          font-size: .65rem; font-weight: 700; flex-shrink: 0;
          padding: .18rem .5rem; border-radius: 4px;
          background: var(--surface-3); color: var(--text-light);
          letter-spacing: .02em; white-space: nowrap;
        }
        .group-top { flex: 1; font-size: .9rem; font-weight: 700; color: var(--text); }
        .group-sel-badge {
          padding: .15rem .5rem; background: var(--primary);
          color: #fff; border-radius: var(--radius-full);
          font-size: .65rem; font-weight: 700;
        }
        .job-sel-badge { background: var(--secondary); }
        .group-chevron { color: var(--text-light); flex-shrink: 0; }

        .group-chips {
          display: flex; flex-wrap: wrap; gap: .5rem;
          padding: .25rem 1.125rem 1rem;
          border-top: 1px solid var(--border);
          animation: fade-in .15s ease;
        }

        .domain-chip {
          display: inline-flex; align-items: center; gap: .375rem;
          padding: .45rem .875rem;
          border: 1.5px solid var(--border); background: var(--surface);
          border-radius: var(--radius-full);
          font-size: .83rem; font-weight: 500; color: var(--text-muted);
          cursor: pointer; transition: all .18s; white-space: nowrap;
        }
        .domain-chip:hover { border-color: var(--primary); color: var(--primary); background: var(--primary-light); }
        .domain-chip-selected {
          border-color: var(--primary); background: var(--primary); color: #fff; font-weight: 700;
          box-shadow: 0 2px 8px var(--primary-glow);
        }
        .job-chip:hover { border-color: var(--secondary); color: var(--secondary); background: var(--secondary-light); }
        .job-chip-selected {
          border-color: var(--secondary); background: var(--secondary); color: #fff; font-weight: 700;
          box-shadow: 0 2px 8px rgba(14,165,233,.25);
        }
        .chip-check { font-size: .8rem; }

        .mismatch-warn {
          display: flex; align-items: flex-start; gap: .625rem;
          padding: .875rem 1rem;
          background: #fefce8; border: 1px solid #fde68a; border-radius: var(--radius-sm);
          animation: fade-in .2s ease;
        }
        .mismatch-icon { color: #d97706; flex-shrink: 0; margin-top: .15rem; }
        .mismatch-body { font-size: .82rem; color: #78350f; line-height: 1.6; }
        .mismatch-desc { color: #92400e; }
        .mismatch-body em { font-style: normal; font-weight: 700; }

        .major-input-section { display: flex; flex-direction: column; gap: .5rem; padding: .875rem 1rem; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius-sm); }
        .major-input-desc { font-size: .8rem; color: var(--text-muted); margin: 0; line-height: 1.55; }
        .major-text-input {
          width: 100%; padding: .6rem .875rem; font-size: .88rem; color: var(--text);
          background: var(--surface); border: 1.5px solid var(--border); border-radius: var(--radius-sm);
          outline: none; transition: border-color .15s; box-sizing: border-box;
        }
        .major-text-input:focus { border-color: var(--primary); }
        .major-text-input::placeholder { color: var(--text-light); }

        .interest-footer {
          display: flex; gap: .75rem; align-items: center; justify-content: space-between;
          padding-top: .5rem; position: sticky; bottom: 0;
          background: var(--bg); padding-bottom: 1rem;
        }
        .interest-next-btn { padding: .75rem 1.5rem; font-size: .95rem; transition: all .2s; }
        .interest-next-btn:disabled { opacity: .45; cursor: not-allowed; }
      `}</style>
    </div>
  );
};

export default InterestSelection;
