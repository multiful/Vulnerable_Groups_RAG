// Content Hash: SHA256:TBD
// Role: 자격증 추천 카드 — 스켈레톤 로딩 + 실제 데이터 (채용공고 매칭 포함)
import React from 'react';
import { ExternalLink, TrendingUp, Briefcase, Award } from 'lucide-react';

export interface JobPosting {
  company: string;
  title: string;
  url: string;
  department?: string;
  location?: string;
  match_score?: number;
  is_active?: boolean;
}

export interface CertJobCardData {
  cert_name: string;
  job_domain: string;
  risk_stage: number;
  difficulty_score: number;
  difficulty_threshold: number;
  meets_threshold: boolean;
  pass_rate: number | null;
  domain_relevance_delta: number;
  relevance_summary: string;
  job_demand_level: '상' | '중' | '하';
  job_postings: JobPosting[];
  posting_count: number;
}

interface CertJobCardProps {
  data?: CertJobCardData;
  isLoading?: boolean;
  /** 자격증 로드맵 보기 버튼 클릭 콜백 */
  onViewRoadmap?: (certName: string) => void;
}

/* ──────────────────────────────────────────────────────────
   스켈레톤 — 실제 카드 구조와 동일한 레이아웃
────────────────────────────────────────────────────────── */
function CertJobCardSkeleton() {
  return (
    <div className="cjc-card">
      {/* 헤더 */}
      <div className="cjc-header">
        <div className="skeleton cjc-skel-title" />
        <div className="cjc-meta-row">
          <div className="skeleton cjc-skel-badge" />
          <div className="skeleton cjc-skel-badge" />
          <div className="skeleton cjc-skel-badge-sm" />
        </div>
      </div>

      {/* 이유 섹션 */}
      <div className="cjc-section">
        <div className="skeleton cjc-skel-label" />
        <div className="cjc-reason-lines">
          <div className="skeleton cjc-skel-line-full" />
          <div className="skeleton cjc-skel-line-3q" />
          <div className="skeleton cjc-skel-line-half" />
        </div>
      </div>

      {/* 채용공고 섹션 */}
      <div className="cjc-section">
        <div className="skeleton cjc-skel-label" />
        {[1, 2, 3].map(i => (
          <div key={i} className="cjc-job-skeleton-row">
            <div className="skeleton cjc-skel-company" />
            <div className="skeleton cjc-skel-jobtitle" />
            <div className="skeleton cjc-skel-arrow" />
          </div>
        ))}
      </div>

      {/* 버튼 */}
      <div className="skeleton cjc-skel-btn" />

      <style>{skeletonCss}</style>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────
   실제 카드
────────────────────────────────────────────────────────── */
function CertJobCardContent({ data, onViewRoadmap }: { data: CertJobCardData; onViewRoadmap?: (c: string) => void }) {
  const demandColor: Record<string, string> = {
    '상': 'var(--success)',
    '중': 'var(--warning)',
    '하': 'var(--text-muted)',
  };
  const stageName = (s: number) => {
    const map: Record<number, string> = {
      1: '고립위험청년', 2: '활동형 고립청년', 3: '활동제한형 고립청년', 4: '은둔청년',
    };
    return map[s] ?? `${s}단계`;
  };

  return (
    <div className="cjc-card">
      {/* ── 헤더 ── */}
      <div className="cjc-header">
        <div className="cjc-title-row">
          <Award size={18} className="cjc-icon-award" />
          <h3 className="cjc-title">{data.cert_name}</h3>
        </div>
        <div className="cjc-meta-row">
          <span className="cjc-badge cjc-badge-blue">
            난이도 {data.difficulty_score}%
          </span>
          {data.pass_rate !== null && (
            <span className="cjc-badge cjc-badge-green">
              합격률 {data.pass_rate}%
            </span>
          )}
          <span
            className="cjc-badge"
            style={{ background: `color-mix(in srgb, ${demandColor[data.job_demand_level] ?? 'var(--text-muted)'} 10%, transparent)`, color: demandColor[data.job_demand_level] ?? 'var(--text-muted)', border: `1px solid color-mix(in srgb, ${demandColor[data.job_demand_level] ?? 'var(--text-muted)'} 25%, transparent)` }}
          >
            수요 {data.job_demand_level}
          </span>
          <span className="cjc-stage-chip">{stageName(data.risk_stage)} 추천</span>
        </div>
      </div>

      <div className="cjc-divider" />

      {/* ── 추천 이유 ── */}
      <div className="cjc-section">
        <div className="cjc-section-label">
          <TrendingUp size={13} />
          이 자격증을 추천한 이유
        </div>
        <ul className="cjc-reason-list">
          <li>
            희망 분야({data.job_domain || '해당 직무'}) 연관성이 평균 대비{' '}
            <strong>{data.domain_relevance_delta > 0 ? `${data.domain_relevance_delta}% 높습니다` : `${Math.abs(data.domain_relevance_delta)}% 낮습니다`}</strong>
          </li>
          <li>{data.relevance_summary}</li>
          {data.posting_count > 0 && (
            <li>
              현재 분석된 채용공고{' '}
              <strong>{data.posting_count}건</strong>에서 이 자격증 관련 직무가 확인됩니다
            </li>
          )}
        </ul>
      </div>

      {/* ── 채용공고 매칭 ── */}
      {data.job_postings.length > 0 && (
        <>
          <div className="cjc-divider" />
          <div className="cjc-section">
            <div className="cjc-section-label">
              <Briefcase size={13} />
              현재 채용 중인 매칭 공고
            </div>
            <ul className="cjc-job-list">
              {data.job_postings.map((job, idx) => (
                <li key={idx} className="cjc-job-item">
                  <div className="cjc-job-left">
                    <span className="cjc-company">{job.company}</span>
                    <span className="cjc-job-title">{job.title}</span>
                    {job.location && <span className="cjc-location">{job.location}</span>}
                  </div>
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="cjc-job-link"
                  >
                    공고 보기 <ExternalLink size={11} />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {/* ── CTA ── */}
      <div className="cjc-footer">
        <button
          className="btn-primary cjc-roadmap-btn"
          onClick={() => onViewRoadmap?.(data.cert_name)}
        >
          {data.cert_name} 로드맵 보기
        </button>
      </div>

      <style>{cardCss}</style>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────
   메인 export
────────────────────────────────────────────────────────── */
const CertJobCard: React.FC<CertJobCardProps> = ({ data, isLoading = false, onViewRoadmap }) => {
  if (isLoading || !data) return <CertJobCardSkeleton />;
  return <CertJobCardContent data={data} onViewRoadmap={onViewRoadmap} />;
};

export default CertJobCard;

/* ──────────────────────────────────────────────────────────
   CSS — 스켈레톤
────────────────────────────────────────────────────────── */
const skeletonCss = `
  .cjc-skel-title  { height: 22px; width: 55%; }
  .cjc-skel-badge  { height: 22px; width: 80px; border-radius: 99px; }
  .cjc-skel-badge-sm { height: 22px; width: 60px; border-radius: 99px; }
  .cjc-skel-label  { height: 14px; width: 140px; margin-bottom: .625rem; }
  .cjc-reason-lines { display: flex; flex-direction: column; gap: .45rem; }
  .cjc-skel-line-full { height: 13px; }
  .cjc-skel-line-3q   { height: 13px; width: 75%; }
  .cjc-skel-line-half { height: 13px; width: 50%; }
  .cjc-job-skeleton-row {
    display: flex; align-items: center; gap: .625rem;
    padding: .625rem 0; border-bottom: 1px solid var(--border);
  }
  .cjc-job-skeleton-row:last-child { border-bottom: none; }
  .cjc-skel-company  { height: 14px; width: 64px; border-radius: 4px; flex-shrink: 0; }
  .cjc-skel-jobtitle { height: 14px; flex: 1; }
  .cjc-skel-arrow    { height: 14px; width: 56px; border-radius: 4px; flex-shrink: 0; }
  .cjc-skel-btn      { height: 40px; width: 100%; border-radius: var(--radius-sm); margin-top: .5rem; }
`;

/* ──────────────────────────────────────────────────────────
   CSS — 실제 카드
────────────────────────────────────────────────────────── */
const cardCss = `
  .cjc-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
    padding: 1.375rem;
    display: flex; flex-direction: column; gap: 1rem;
  }

  .cjc-header { display: flex; flex-direction: column; gap: .5rem; }
  .cjc-title-row { display: flex; align-items: center; gap: .5rem; }
  .cjc-icon-award { color: var(--primary); flex-shrink: 0; }
  .cjc-title { font-size: 1.1rem; font-weight: 800; color: var(--text); }

  .cjc-meta-row { display: flex; align-items: center; gap: .4rem; flex-wrap: wrap; }
  .cjc-badge {
    padding: .2rem .6rem;
    border-radius: 99px;
    font-size: .72rem; font-weight: 700;
  }
  .cjc-badge-blue  { background: var(--primary-light); color: var(--primary); }
  .cjc-badge-green { background: var(--success-light); color: var(--success); }
  .cjc-stage-chip {
    font-size: .7rem; font-weight: 600; color: var(--text-muted);
    padding: .15rem .5rem; border-radius: 99px;
    background: var(--surface-2); border: 1px solid var(--border);
  }

  .cjc-divider { height: 1px; background: var(--border); }

  .cjc-section { display: flex; flex-direction: column; gap: .5rem; }
  .cjc-section-label {
    display: flex; align-items: center; gap: .35rem;
    font-size: .75rem; font-weight: 700; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: .04em;
  }

  .cjc-reason-list {
    list-style: none; padding: 0; margin: 0;
    display: flex; flex-direction: column; gap: .4rem;
  }
  .cjc-reason-list li {
    font-size: .85rem; color: var(--text-muted); line-height: 1.6;
    padding-left: .875rem; position: relative;
  }
  .cjc-reason-list li::before {
    content: ""; position: absolute; left: 0; top: .55em;
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--primary); opacity: .6;
  }
  .cjc-reason-list li strong { color: var(--text); font-weight: 700; }

  .cjc-job-list { list-style: none; padding: 0; margin: 0; }
  .cjc-job-item {
    display: flex; align-items: center; justify-content: space-between;
    gap: .75rem; padding: .625rem 0;
    border-bottom: 1px solid var(--border);
  }
  .cjc-job-item:last-child { border-bottom: none; }

  .cjc-job-left { display: flex; align-items: center; gap: .5rem; flex: 1; min-width: 0; }
  .cjc-company {
    font-size: .72rem; font-weight: 700; color: var(--primary);
    background: var(--primary-light);
    padding: .15rem .5rem; border-radius: 4px;
    white-space: nowrap; flex-shrink: 0;
  }
  .cjc-job-title {
    font-size: .85rem; font-weight: 600; color: var(--text);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .cjc-location {
    font-size: .72rem; color: var(--text-light);
    white-space: nowrap; flex-shrink: 0;
  }

  .cjc-job-link {
    display: inline-flex; align-items: center; gap: .25rem;
    font-size: .75rem; font-weight: 600; color: var(--primary);
    white-space: nowrap; flex-shrink: 0;
    padding: .25rem .6rem;
    border: 1px solid var(--primary);
    border-radius: var(--radius-xs);
    text-decoration: none;
    transition: var(--transition);
  }
  .cjc-job-link:hover {
    background: var(--primary-light);
  }

  .cjc-footer { margin-top: .25rem; }
  .cjc-roadmap-btn { width: 100%; justify-content: center; }
`;
