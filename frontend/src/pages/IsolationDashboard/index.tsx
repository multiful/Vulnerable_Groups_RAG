// Content Hash: SHA256:TBD
// 고립군 청년 진단 결과 → 맞춤 서비스 대시보드
// 두 API를 병렬 호출: /isolation/dashboard (DIDIM 서비스) + /isolation/policy (복지 정책)
import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, ExternalLink, ChevronDown, ChevronUp, Zap, MapPin, Heart, BookOpen, Briefcase, Users, Home, Star } from 'lucide-react';
import { getApiBase } from '../../api/client';

/* ─── 타입 ─────────────────────────────────────────────── */
interface ServiceItem {
  id: string;
  name: string;
  desc?: string;
  category: string;
  frontend_path?: string;
  api_prefix?: string;
  explanation: string;
  reason?: string;
}

interface TodayAction {
  action_type: string;
  title: string;
  description: string;
  cta: string;
  cta_path: string;
  effort_minutes: number;
}

interface DashboardData {
  cluster_id: string;
  cluster_meta: { label: string; description: string; direction: string };
  region: string | null;
  active_services: ServiceItem[];
  inactive_services: ServiceItem[];
  today_action: { cluster_id: string; action: TodayAction; motivation: string };
  active_count: number;
  inactive_count: number;
}

interface PolicyItem {
  name?: string;
  title?: string;
  description?: string;
  region?: string;
  url?: string;
  link?: string;
  [key: string]: unknown;
}

interface PolicyBundle {
  category: string;
  label: string;
  icon: string;
  desc: string;
  count: number;
  items: PolicyItem[];
  error?: string;
}

interface PolicyData {
  cluster_id: string;
  cluster_meta: { label: string; direction: string };
  active_categories: string[];
  bundles: PolicyBundle[];
  total_items: number;
}

/* ─── 상수 ─────────────────────────────────────────────── */
const CLUSTER_COLORS: Record<string, string> = {
  '1': '#10b981',
  '2': '#0ea5e9',
  '3': '#f59e0b',
  '4': '#f43f5e',
};

const CLUSTER_GRADIENT: Record<string, string> = {
  '1': 'linear-gradient(135deg,#ecfdf5,#d1fae5)',
  '2': 'linear-gradient(135deg,#eff6ff,#dbeafe)',
  '3': 'linear-gradient(135deg,#fffbeb,#fef3c7)',
  '4': 'linear-gradient(135deg,#fff1f2,#ffe4e6)',
};

const CLUSTER_BG_SOFT: Record<string, string> = {
  '1': '#f0fdf4',
  '2': '#eff6ff',
  '3': '#fffbeb',
  '4': '#fff1f2',
};

// 서비스 ID → 실제 라우트 매핑 (없으면 정책 섹션으로 스크롤)
const SERVICE_ROUTE: Record<string, string | null> = {
  certification_roadmap: '/recommendation',
  exam_schedule:         '/schedule',
  youtube_lectures:      '/certs',
  training_courses:      '/training',
  job_listings:          '/jobs',
  govt_job_programs:     null,  // 정책 섹션
  job_cafes:             null,  // API 중단 — 제거 대상
  health_centers:        null,
  welfare_central:       null,
  welfare_local:         null,
  family_centers:        null,
  gender_facilities:     null,
  today_action:          null,
};

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  '취업준비': <BookOpen size={15} />,
  '취업':     <Briefcase size={15} />,
  '사회참여': <Users size={15} />,
  '공간지원': <MapPin size={15} />,
  '복지지원': <Heart size={15} />,
  '가족지원': <Home size={15} />,
  '상담지원': <Heart size={15} />,
  '실천':     <Star size={15} />,
};

const ACTION_TYPE_LABEL: Record<string, string> = {
  connect: '관계 연결',
  apply:   '신청',
  space:   '공간 방문',
  welfare: '복지 신청',
  micro:   '작은 시작',
  wellness:'건강 관리',
  family:  '가족 지원',
  study:   '학습',
  training:'훈련',
};

/* ─── 유틸 ─────────────────────────────────────────────── */
async function fetchJson(url: string): Promise<unknown> {
  const base = getApiBase();
  const full = base ? `${base}${url}` : url;
  const res = await fetch(full);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function getPolicyItemName(item: PolicyItem): string {
  return String(item.name || item.title || '서비스명 미제공');
}
function getPolicyItemDesc(item: PolicyItem): string {
  return String(item.description || item.desc || '');
}
function getPolicyItemUrl(item: PolicyItem): string {
  return String(item.url || item.link || '');
}

/* ─── 컴포넌트 ─────────────────────────────────────────── */
const IsolationDashboard: React.FC = () => {
  const [params] = useSearchParams();
  const navigate  = useNavigate();

  const clusterId = params.get('cluster_id') || '1';
  const region    = params.get('region') || undefined;

  const [dashboard, setDashboard]         = useState<DashboardData | null>(null);
  const [policy, setPolicy]               = useState<PolicyData | null>(null);
  const [loading, setLoading]             = useState(true);
  const [policyLoading, setPolicyLoading] = useState(true);
  const [error, setError]                 = useState<string | null>(null);
  const [showInactive, setShowInactive]   = useState(false);

  const color    = CLUSTER_COLORS[clusterId]   ?? '#6366f1';
  const gradient = CLUSTER_GRADIENT[clusterId] ?? 'linear-gradient(135deg,#f8fafc,#f1f5f9)';
  const softBg   = CLUSTER_BG_SOFT[clusterId]  ?? '#f8fafc';

  useEffect(() => {
    if (!['1','2','3','4'].includes(clusterId)) {
      setError('유효하지 않은 군집 ID입니다. 다시 진단해 주세요.');
      setLoading(false);
      return;
    }

    // 두 API 병렬 호출
    const regionParam = region ? `&region=${encodeURIComponent(region)}` : '';

    const p1 = fetchJson(`/api/v1/isolation/dashboard?cluster_id=${clusterId}${regionParam}&with_llm=false`)
      .then(r => {
        const d = (r as { success: boolean; data: DashboardData });
        if (d.success) setDashboard(d.data);
      })
      .catch(() => setError('서비스 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'))
      .finally(() => setLoading(false));

    const p2 = fetchJson(`/api/v1/isolation/policy?cluster_id=${clusterId}${regionParam}&items_per_category=3`)
      .then(r => {
        const d = (r as { success: boolean; data: PolicyData });
        if (d.success) setPolicy(d.data);
      })
      .catch(() => {/* 정책 로딩 실패는 조용히 처리 */})
      .finally(() => setPolicyLoading(false));

    Promise.all([p1, p2]);
  }, [clusterId, region]);

  /* ── 에러 ── */
  if (error) return (
    <div className="iso-wrap">
      <div className="iso-error-card">
        <p>{error}</p>
        <div style={{ display:'flex', gap:'.75rem', flexWrap:'wrap', justifyContent:'center', marginTop:'.25rem' }}>
          <button className="btn-ghost" onClick={() => navigate('/risk-assessment')}>
            진단 다시 하기
          </button>
          <button className="btn-primary" onClick={() => navigate(`/interests?stage=${clusterId}`)}>
            자격증 추천 바로 보기
          </button>
        </div>
      </div>
    </div>
  );

  /* ── 로딩 ── */
  if (loading) return (
    <div className="iso-wrap">
      <div className="iso-loading">
        <div className="iso-spinner" style={{ borderTopColor: color }} />
        <p>맞춤 서비스를 준비하고 있어요…</p>
      </div>
    </div>
  );

  if (!dashboard) return null;

  const { cluster_meta, active_services, inactive_services, today_action } = dashboard;
  const todayAct = today_action?.action;

  // 카테고리 그룹핑 (active services)
  const categoryGroups = active_services.reduce<Record<string, ServiceItem[]>>((acc, s) => {
    (acc[s.category] = acc[s.category] || []).push(s);
    return acc;
  }, {});

  const CATEGORY_ORDER = ['취업준비','취업','사회참여','공간지원','복지지원','가족지원','상담지원','실천'];
  const sortedCategories = CATEGORY_ORDER.filter(c => categoryGroups[c]);

  return (
    <div className="iso-wrap">

      {/* ── 헤더 뒤로가기 ── */}
      <button className="iso-back-btn" onClick={() => navigate(-1)}>
        <ArrowLeft size={15} /> 진단 결과로
      </button>

      {/* ══ 군집 히어로 ══ */}
      <div className="iso-hero" style={{ background: gradient, borderColor: color + '30' }}>
        <div className="iso-hero-badge" style={{ background: color + '18', color, borderColor: color + '40' }}>
          {clusterId}단계
        </div>
        <h1 className="iso-hero-title">{cluster_meta.label}</h1>
        <p className="iso-hero-desc">{cluster_meta.description}</p>
        <div className="iso-hero-direction" style={{ background: color + '12', borderColor: color + '30', color }}>
          <Zap size={13} />
          <span>{cluster_meta.direction}</span>
        </div>
      </div>

      {/* ══ 오늘의 행동 ══ */}
      {todayAct && (
        <div className="iso-action-card" style={{ background: softBg }}>
          <div className="iso-action-top">
            <span className="iso-action-badge" style={{ background: color, color: '#fff' }}>
              {ACTION_TYPE_LABEL[todayAct.action_type] ?? '오늘의 행동'} · {todayAct.effort_minutes}분
            </span>
            <span className="iso-action-chip">지금 바로 시작</span>
          </div>
          <p className="iso-action-title">{todayAct.title}</p>
          <p className="iso-action-desc">{todayAct.description}</p>
          <div className="iso-action-motivation">{today_action.motivation}</div>
          {todayAct.cta_path && (
            <Link to={todayAct.cta_path} className="iso-action-cta" style={{ background: color }}>
              {todayAct.cta} <ArrowRight size={14} />
            </Link>
          )}
        </div>
      )}

      {/* ══ DIDIM 서비스 그리드 ══ */}
      <section className="iso-section">
        <div className="iso-section-header">
          <h2 className="iso-section-title">지금 이용할 수 있는 서비스</h2>
          <span className="iso-section-count" style={{ background: color + '18', color }}>
            {active_services.length}개
          </span>
        </div>
        <p className="iso-section-sub">현재 단계에 맞는 서비스만 골라드렸어요</p>

        {sortedCategories.map(cat => (
          <div key={cat} className="iso-cat-group">
            <div className="iso-cat-header">
              <span className="iso-cat-icon">{CATEGORY_ICON[cat]}</span>
              <span className="iso-cat-name">{cat}</span>
            </div>
            <div className="iso-service-grid">
              {categoryGroups[cat].filter(svc => svc.id !== 'job_cafes').map(svc => {
                const route = SERVICE_ROUTE[svc.id];
                const isInternal = !!route;
                return (
                  <div key={svc.id} className="iso-service-card">
                    <p className="iso-svc-name">{svc.name}</p>
                    <p className="iso-svc-exp">{svc.explanation}</p>
                    {isInternal ? (
                      <Link to={route!} className="iso-svc-cta" style={{ color }}>
                        바로 가기 <ArrowRight size={12} />
                      </Link>
                    ) : (
                      <button
                        className="iso-svc-cta"
                        style={{ color }}
                        onClick={() => {
                          const el = document.getElementById('iso-policy');
                          el?.scrollIntoView({ behavior: 'smooth' });
                        }}
                      >
                        정책 보기 <ArrowRight size={12} />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </section>

      {/* ══ 복지 정책 번들 ══ */}
      <section className="iso-section" id="iso-policy">
        <div className="iso-section-header">
          <h2 className="iso-section-title">맞춤 정책 · 지원 프로그램</h2>
        </div>
        <p className="iso-section-sub">지금 신청하거나 문의할 수 있는 실제 서비스예요</p>

        {policyLoading ? (
          <div className="iso-policy-loading">
            <div className="iso-spinner-sm" style={{ borderTopColor: color }} />
            <span>정책 정보 불러오는 중…</span>
          </div>
        ) : policy?.bundles?.length ? (
          policy.bundles.map(bundle => (
            <div key={bundle.category} className="iso-policy-bundle">
              <div className="iso-bundle-header">
                <span className="iso-bundle-icon">{bundle.icon}</span>
                <div>
                  <span className="iso-bundle-label">{bundle.label}</span>
                  <p className="iso-bundle-desc">{bundle.desc}</p>
                </div>
                <span className="iso-bundle-count">{bundle.count}건</span>
              </div>

              {bundle.error && (
                <p className="iso-bundle-error">일시적으로 불러오지 못했습니다</p>
              )}

              {bundle.items.length > 0 ? (
                <div className="iso-policy-items">
                  {bundle.items.map((item, idx) => {
                    const name = getPolicyItemName(item);
                    const desc = getPolicyItemDesc(item);
                    const url  = getPolicyItemUrl(item);
                    return (
                      <div key={idx} className="iso-policy-item">
                        <div className="iso-policy-item-body">
                          <p className="iso-policy-item-name">{name}</p>
                          {desc && <p className="iso-policy-item-desc">{desc}</p>}
                        </div>
                        {url ? (
                          <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="iso-policy-item-link"
                            style={{ color }}
                          >
                            <ExternalLink size={13} />
                          </a>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              ) : !bundle.error ? (
                <p className="iso-bundle-empty">현재 지역에서 조회된 서비스가 없습니다</p>
              ) : null}
            </div>
          ))
        ) : (
          <div className="iso-policy-empty">
            <p>정책 정보를 불러오지 못했습니다.</p>
            <p className="iso-policy-empty-sub">복지로(bokjiro.go.kr) 또는 온통청년(youth.go.kr)에서 직접 확인해 보세요.</p>
            <a href="https://www.bokjiro.go.kr" target="_blank" rel="noopener noreferrer" className="iso-ext-link" style={{ color }}>
              복지로 바로가기 <ExternalLink size={12} />
            </a>
          </div>
        )}
      </section>

      {/* ══ 외부 자원 퀵링크 ══ */}
      <section className="iso-section">
        <h2 className="iso-section-title">외부 지원 채널</h2>
        <div className="iso-quicklinks">
          {[
            { label: '복지로', sub: '중앙부처 복지서비스 검색', href: 'https://www.bokjiro.go.kr', color: '#6366f1' },
            { label: '온통청년', sub: '청년 정책 통합 안내', href: 'https://www.youthcenter.go.kr', color: '#0ea5e9' },
            { label: '청년도전지원', sub: '고용노동부 일경험 프로그램', href: 'https://www.moel.go.kr', color: '#10b981' },
            { label: '마음이음', sub: '정신건강 상담 1577-0199', href: 'tel:15770199', color: '#f59e0b' },
          ].map(ql => (
            <a key={ql.label} href={ql.href} target={ql.href.startsWith('tel') ? undefined : '_blank'}
               rel="noopener noreferrer" className="iso-quicklink-card">
              <span className="iso-ql-dot" style={{ background: ql.color }} />
              <div>
                <p className="iso-ql-label">{ql.label}</p>
                <p className="iso-ql-sub">{ql.sub}</p>
              </div>
              <ExternalLink size={12} className="iso-ql-icon" />
            </a>
          ))}
        </div>
      </section>

      {/* ══ 지금은 아직인 서비스 (접이식) ══ */}
      {inactive_services.length > 0 && (
        <section className="iso-section iso-inactive-section">
          <button
            className="iso-inactive-toggle"
            onClick={() => setShowInactive(v => !v)}
          >
            <span>지금은 아직인 서비스 ({inactive_services.length}개)</span>
            {showInactive ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>

          {showInactive && (
            <div className="iso-inactive-body">
              <p className="iso-inactive-intro">
                아래 서비스는 지금 단계보다 조금 더 회복된 후에 시작하면 더 효과적이에요.
                지금 바로 하지 않아도 괜찮습니다.
              </p>
              {inactive_services.map(svc => (
                <div key={svc.id} className="iso-inactive-item">
                  <div>
                    <p className="iso-inactive-name">{svc.name}</p>
                    <span className="iso-inactive-cat">{svc.category}</span>
                  </div>
                  {svc.reason && (
                    <p className="iso-inactive-reason">{svc.reason}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ══ 다음 단계 CTA ══ */}
      <div className="iso-next-steps">
        <button className="btn-ghost" onClick={() => navigate('/risk-assessment')}>
          <ArrowLeft size={15} /> 진단 다시 하기
        </button>
        {['1','2','3'].includes(clusterId) && (
          <Link to={`/recommendation?stage=${clusterId}`} className="btn-primary">
            자격증 추천 보기 <ArrowRight size={15} />
          </Link>
        )}
      </div>

      <style>{`
        .iso-wrap {
          max-width: 680px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          padding-bottom: 3rem;
        }

        /* ── 뒤로가기 ── */
        .iso-back-btn {
          display: inline-flex; align-items: center; gap: .375rem;
          font-size: .82rem; font-weight: 600; color: var(--text-muted);
          background: none; border: none; cursor: pointer; padding: 0;
          width: fit-content;
        }
        .iso-back-btn:hover { color: var(--text); }

        /* ── 히어로 ── */
        .iso-hero {
          padding: 1.5rem 1.75rem;
          border-radius: var(--radius);
          border: 1.5px solid;
          display: flex; flex-direction: column; gap: .625rem;
        }
        .iso-hero-badge {
          display: inline-flex; width: fit-content;
          padding: .3rem .85rem;
          border-radius: var(--radius-full);
          font-size: .78rem; font-weight: 800;
          border: 1.5px solid;
        }
        .iso-hero-title {
          font-size: 1.45rem; font-weight: 900;
          color: var(--text); margin: 0;
          line-height: 1.3;
        }
        .iso-hero-desc {
          font-size: .9rem; color: var(--text-muted);
          margin: 0; line-height: 1.6;
        }
        .iso-hero-direction {
          display: flex; align-items: center; gap: .4rem;
          padding: .5rem .875rem;
          border-radius: var(--radius-sm);
          border: 1px solid;
          font-size: .82rem; font-weight: 600;
          margin-top: .25rem;
          width: fit-content;
        }

        /* ── 오늘의 행동 ── */
        .iso-action-card {
          padding: 1.25rem 1.5rem;
          border-radius: var(--radius);
          border: 1.5px solid var(--border);
          display: flex; flex-direction: column; gap: .75rem;
        }
        .iso-action-top {
          display: flex; align-items: center; gap: .625rem; flex-wrap: wrap;
        }
        .iso-action-badge {
          padding: .25rem .7rem;
          border-radius: var(--radius-full);
          font-size: .72rem; font-weight: 700;
        }
        .iso-action-chip {
          font-size: .72rem; font-weight: 600;
          color: var(--text-muted);
          background: var(--surface-2);
          padding: .2rem .55rem;
          border-radius: var(--radius-full);
        }
        .iso-action-title {
          font-size: 1.1rem; font-weight: 800; color: var(--text);
          margin: 0;
        }
        .iso-action-desc {
          font-size: .88rem; color: var(--text-muted);
          margin: 0; line-height: 1.65;
        }
        .iso-action-motivation {
          font-size: .8rem; color: var(--text-light);
          font-style: italic;
          padding: .5rem .75rem;
          background: var(--surface-2);
          border-radius: var(--radius-sm);
        }
        .iso-action-cta {
          display: inline-flex; align-items: center; gap: .4rem;
          padding: .65rem 1.25rem;
          border-radius: var(--radius-sm);
          color: #fff; font-size: .88rem; font-weight: 700;
          text-decoration: none;
          width: fit-content;
          transition: opacity .15s;
        }
        .iso-action-cta:hover { opacity: .88; }

        /* ── 섹션 공통 ── */
        .iso-section {
          display: flex; flex-direction: column; gap: 1rem;
        }
        .iso-section-header {
          display: flex; align-items: center; gap: .625rem;
        }
        .iso-section-title {
          font-size: 1.05rem; font-weight: 800; color: var(--text);
          margin: 0;
        }
        .iso-section-count {
          padding: .2rem .6rem;
          border-radius: var(--radius-full);
          font-size: .72rem; font-weight: 700;
        }
        .iso-section-sub {
          font-size: .82rem; color: var(--text-muted);
          margin: -.5rem 0 0;
        }

        /* ── 카테고리 그룹 ── */
        .iso-cat-group { display: flex; flex-direction: column; gap: .625rem; }
        .iso-cat-header {
          display: flex; align-items: center; gap: .4rem;
          padding: 0 .25rem;
        }
        .iso-cat-icon { color: var(--text-muted); display: flex; }
        .iso-cat-name {
          font-size: .78rem; font-weight: 700;
          color: var(--text-muted); text-transform: uppercase;
          letter-spacing: .05em;
        }

        /* ── 서비스 카드 그리드 ── */
        .iso-service-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
          gap: .75rem;
        }
        .iso-service-card {
          padding: 1rem 1.125rem;
          border: 1.5px solid var(--border);
          border-radius: var(--radius-sm);
          background: var(--surface);
          display: flex; flex-direction: column; gap: .5rem;
          transition: border-color .15s, box-shadow .15s;
        }
        .iso-service-card:hover {
          border-color: var(--border-strong);
          box-shadow: 0 2px 12px rgba(0,0,0,.06);
        }
        .iso-svc-name {
          font-size: .9rem; font-weight: 700; color: var(--text);
          margin: 0;
        }
        .iso-svc-exp {
          font-size: .8rem; color: var(--text-muted);
          margin: 0; line-height: 1.6; flex: 1;
        }
        .iso-svc-cta {
          display: inline-flex; align-items: center; gap: .3rem;
          font-size: .78rem; font-weight: 700;
          background: none; border: none; cursor: pointer;
          padding: 0; text-decoration: none;
          margin-top: .25rem;
          transition: opacity .15s;
        }
        .iso-svc-cta:hover { opacity: .7; }

        /* ── 정책 번들 ── */
        .iso-policy-loading {
          display: flex; align-items: center; gap: .625rem;
          padding: 1rem 0;
          font-size: .85rem; color: var(--text-muted);
        }
        .iso-spinner-sm {
          width: 18px; height: 18px;
          border: 2px solid var(--border);
          border-top-color: var(--primary);
          border-radius: 50%;
          animation: iso-spin .7s linear infinite;
        }
        .iso-policy-bundle {
          border: 1.5px solid var(--border);
          border-radius: var(--radius-sm);
          overflow: hidden;
        }
        .iso-bundle-header {
          display: flex; align-items: flex-start; gap: .75rem;
          padding: .875rem 1rem;
          background: var(--surface-2);
          border-bottom: 1px solid var(--border);
        }
        .iso-bundle-icon { font-size: 1.25rem; flex-shrink: 0; line-height: 1; }
        .iso-bundle-label {
          font-size: .9rem; font-weight: 700; color: var(--text);
          display: block; margin-bottom: .15rem;
        }
        .iso-bundle-desc {
          font-size: .75rem; color: var(--text-muted);
          margin: 0; line-height: 1.5;
        }
        .iso-bundle-count {
          margin-left: auto; flex-shrink: 0;
          font-size: .75rem; font-weight: 700;
          color: var(--text-muted);
          background: var(--border);
          padding: .2rem .55rem;
          border-radius: var(--radius-full);
        }
        .iso-bundle-error {
          font-size: .8rem; color: var(--danger);
          padding: .625rem 1rem; margin: 0;
        }
        .iso-policy-items {
          display: flex; flex-direction: column;
        }
        .iso-policy-item {
          display: flex; align-items: flex-start; gap: .75rem;
          padding: .75rem 1rem;
          border-bottom: 1px solid var(--border);
        }
        .iso-policy-item:last-child { border-bottom: none; }
        .iso-policy-item-body { flex: 1; }
        .iso-policy-item-name {
          font-size: .85rem; font-weight: 600; color: var(--text);
          margin: 0 0 .2rem;
        }
        .iso-policy-item-desc {
          font-size: .78rem; color: var(--text-muted);
          margin: 0; line-height: 1.55;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        .iso-policy-item-link {
          flex-shrink: 0; display: flex; align-items: center;
          padding: .4rem;
          border: 1px solid var(--border);
          border-radius: var(--radius-xs);
          transition: background .1s;
        }
        .iso-policy-item-link:hover { background: var(--surface-2); }
        .iso-bundle-empty {
          font-size: .82rem; color: var(--text-muted);
          padding: .875rem 1rem; margin: 0;
        }
        .iso-policy-empty {
          padding: 1.25rem;
          border: 1.5px dashed var(--border);
          border-radius: var(--radius-sm);
          display: flex; flex-direction: column; gap: .5rem;
        }
        .iso-policy-empty p { font-size: .85rem; color: var(--text-muted); margin: 0; }
        .iso-policy-empty-sub { font-size: .78rem !important; }
        .iso-ext-link {
          display: inline-flex; align-items: center; gap: .3rem;
          font-size: .8rem; font-weight: 600;
          text-decoration: none;
          width: fit-content;
        }

        /* ── 외부 퀵링크 ── */
        .iso-quicklinks {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: .625rem;
        }
        .iso-quicklink-card {
          display: flex; align-items: center; gap: .625rem;
          padding: .875rem 1rem;
          border: 1.5px solid var(--border);
          border-radius: var(--radius-sm);
          background: var(--surface);
          text-decoration: none;
          transition: border-color .15s, box-shadow .15s;
        }
        .iso-quicklink-card:hover {
          border-color: var(--border-strong);
          box-shadow: 0 2px 8px rgba(0,0,0,.06);
        }
        .iso-ql-dot {
          width: 8px; height: 8px;
          border-radius: 50%; flex-shrink: 0;
        }
        .iso-ql-label {
          font-size: .85rem; font-weight: 700; color: var(--text);
          margin: 0 0 .1rem;
        }
        .iso-ql-sub {
          font-size: .73rem; color: var(--text-muted);
          margin: 0;
        }
        .iso-ql-icon {
          margin-left: auto; flex-shrink: 0;
          color: var(--text-light);
        }

        /* ── 비활성 서비스 ── */
        .iso-inactive-section { gap: 0; }
        .iso-inactive-toggle {
          display: flex; align-items: center; justify-content: space-between;
          width: 100%; padding: .875rem 1rem;
          background: var(--surface-2);
          border: 1.5px solid var(--border);
          border-radius: var(--radius-sm);
          font-size: .85rem; font-weight: 600; color: var(--text-muted);
          cursor: pointer; text-align: left;
          transition: background .15s;
        }
        .iso-inactive-toggle:hover { background: var(--border); }
        .iso-inactive-body {
          border: 1.5px solid var(--border);
          border-top: none;
          border-radius: 0 0 var(--radius-sm) var(--radius-sm);
          padding: .875rem 1rem;
          display: flex; flex-direction: column; gap: .75rem;
        }
        .iso-inactive-intro {
          font-size: .8rem; color: var(--text-muted);
          line-height: 1.65; margin: 0;
          padding-bottom: .625rem;
          border-bottom: 1px solid var(--border);
        }
        .iso-inactive-item {
          display: flex; flex-direction: column; gap: .25rem;
        }
        .iso-inactive-name {
          font-size: .85rem; font-weight: 600; color: var(--text-muted);
          margin: 0;
        }
        .iso-inactive-cat {
          font-size: .72rem; color: var(--text-light);
          background: var(--surface-2);
          padding: .1rem .45rem;
          border-radius: var(--radius-full);
        }
        .iso-inactive-reason {
          font-size: .78rem; color: var(--text-light);
          margin: .1rem 0 0;
          line-height: 1.55;
        }

        /* ── 다음 단계 ── */
        .iso-next-steps {
          display: flex; gap: .75rem; flex-wrap: wrap;
          padding-top: .5rem;
        }

        /* ── 로딩 / 에러 ── */
        .iso-loading {
          display: flex; flex-direction: column; align-items: center;
          gap: 1rem; padding: 3rem 0;
          color: var(--text-muted); font-size: .88rem;
        }
        .iso-spinner {
          width: 32px; height: 32px;
          border: 3px solid var(--border);
          border-radius: 50%;
          animation: iso-spin .7s linear infinite;
        }
        @keyframes iso-spin {
          to { transform: rotate(360deg); }
        }
        .iso-error-card {
          padding: 2rem; text-align: center;
          display: flex; flex-direction: column; gap: 1rem; align-items: center;
          color: var(--text-muted);
        }

        /* ── 모바일 ── */
        @media (max-width: 480px) {
          .iso-service-grid { grid-template-columns: 1fr; }
          .iso-quicklinks { grid-template-columns: 1fr 1fr; }
          .iso-hero { padding: 1.25rem; }
          .iso-action-card { padding: 1rem 1.125rem; }
        }
      `}</style>
    </div>
  );
};

export default IsolationDashboard;
