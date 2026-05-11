// Content Hash: SHA256:TBD
import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, ArrowLeft, ChevronDown, ChevronUp } from 'lucide-react';

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

const RISK_STAGE_LABELS: Record<string, string> = {
  '1': '1단계 (취업 안정권)',
  '2': '2단계 (준비 활성)',
  '3': '3단계 (준비 정체)',
  '4': '4단계 (관계망 약화)',
  '5': '5단계 (고위험군)',
};

const InterestSelection: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const stage = searchParams.get('stage') ?? '';

  const [selectedDomain, setSelectedDomain] = useState<DomainItem | null>(null);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    'IT/디지털': true,
  });

  function toggleGroup(top: string) {
    setOpenGroups(prev => ({ ...prev, [top]: !prev[top] }));
  }

  function selectDomain(item: DomainItem) {
    setSelectedDomain(prev => (prev?.id === item.id ? null : item));
  }

  function handleNext() {
    if (!selectedDomain) return;
    const params = new URLSearchParams();
    if (stage) params.set('stage', stage);
    params.set('domain', selectedDomain.id);
    params.set('domainName', selectedDomain.name);
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

      {/* Selected badge */}
      {selectedDomain && (
        <div className="selected-banner">
          <span className="selected-label">선택됨:</span>
          <span className="selected-name">{selectedDomain.name}</span>
          <button className="selected-clear" onClick={() => setSelectedDomain(null)}>×</button>
        </div>
      )}

      {/* Domain groups */}
      <div className="groups-list">
        {DOMAIN_GROUPS.map(group => {
          const isOpen = !!openGroups[group.top];
          const hasSelected = group.items.some(i => i.id === selectedDomain?.id);
          return (
            <div key={group.top} className={`group-card card ${hasSelected ? 'group-card-active' : ''}`}>
              <button
                className="group-header"
                onClick={() => toggleGroup(group.top)}
                type="button"
              >
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
                        key={item.id}
                        type="button"
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
            ? <><strong>{selectedDomain.name}</strong> 로드맵 보기 <ArrowRight size={15} /></>
            : '분야를 선택해주세요'}
        </button>
      </div>

      <style>{`
        .interest-wrap {
          max-width: 680px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }
        .back-btn {
          display: inline-flex; align-items: center; gap: .35rem;
          font-size: .85rem; font-weight: 500; color: var(--text-muted);
          margin-bottom: .25rem; background: none; border: none;
          cursor: pointer; padding: 0; transition: color .15s; width: fit-content;
        }
        .back-btn:hover { color: var(--primary); }

        .selected-banner {
          display: flex; align-items: center; gap: .625rem;
          padding: .625rem 1rem;
          background: var(--primary-light); border: 1px solid rgba(99,102,241,.25);
          border-radius: var(--radius-sm);
          animation: fade-in .2s ease;
        }
        @keyframes fade-in { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
        .selected-label { font-size: .78rem; color: var(--text-light); font-weight: 600; }
        .selected-name { font-size: .9rem; font-weight: 700; color: var(--primary); flex: 1; }
        .selected-clear {
          background: none; border: none; cursor: pointer;
          font-size: 1.1rem; color: var(--text-light); padding: 0 .25rem;
          line-height: 1; transition: color .15s;
        }
        .selected-clear:hover { color: var(--danger); }

        .groups-list { display: flex; flex-direction: column; gap: .625rem; }

        .group-card { padding: 0; overflow: hidden; }
        .group-card-active { border-color: rgba(99,102,241,.3); box-shadow: 0 0 0 3px var(--primary-glow); }

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
        .group-top {
          flex: 1; font-size: .9rem; font-weight: 700; color: var(--text);
        }
        .group-sel-badge {
          padding: .15rem .5rem; background: var(--primary);
          color: #fff; border-radius: var(--radius-full);
          font-size: .65rem; font-weight: 700;
        }
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
          border: 1.5px solid var(--border);
          background: var(--surface);
          border-radius: var(--radius-full);
          font-size: .83rem; font-weight: 500; color: var(--text-muted);
          cursor: pointer; transition: all .18s; white-space: nowrap;
        }
        .domain-chip:hover {
          border-color: var(--primary); color: var(--primary);
          background: var(--primary-light);
        }
        .domain-chip-selected {
          border-color: var(--primary); background: var(--primary);
          color: #fff; font-weight: 700;
          box-shadow: 0 2px 8px var(--primary-glow);
        }
        .chip-check { font-size: .8rem; }

        .interest-footer {
          display: flex; gap: .75rem; align-items: center;
          justify-content: space-between;
          padding-top: .5rem;
          position: sticky; bottom: 0;
          background: var(--bg);
          padding-bottom: 1rem;
        }
        .interest-next-btn {
          padding: .75rem 1.5rem; font-size: .95rem;
          transition: all .2s;
        }
        .interest-next-btn:disabled {
          opacity: .45; cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};

export default InterestSelection;
