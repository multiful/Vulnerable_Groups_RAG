// Content Hash: SHA256:TBD
import React, { useState, useCallback, useRef } from 'react';
import { Search, Calendar, Clock, AlertCircle, Loader2, ExternalLink, BookOpen, TrendingUp, ChevronRight } from 'lucide-react';
import { getCertCandidates } from '../../api/client';
import type { CertCandidate } from '../../types/cert';

// ── types ──────────────────────────────────────────────────────────────────
interface ScheduleItem {
  impl_year: string | null;
  impl_seq: string | null;
  impl_seq_name: string | null;
  registration_start: string | null;
  registration_end: string | null;
  exam_start: string | null;
  exam_end: string | null;
  pass_announce_date: string | null;
  d_day_exam: number | null;
  d_day_registration: number | null;
}

interface CertSchedule {
  cert_id: string;
  cert_name: string;
  cert_type: 'tech' | 'private';
  year: string;
  schedules: ScheduleItem[];
  total: number;
  api_status?: 'ok' | 'unavailable' | 'key_missing';
  // enriched cert info from backend
  cert_grade_tier?: string;
  avg_pass_rate_3yr?: number | null;
  primary_domain?: string;
  exam_frequency?: string;
  issuer?: string;
  // Q-Net links
  qnet_search_url?: string;
  qnet_schedule_url?: string;
  qnet_apply_url?: string;
}

// ── helpers ────────────────────────────────────────────────────────────────
const TECH_TIERS = ['기사', '산업기사', '기능사', '기능장', '기술사'];
function getTechType(tier: string): 'tech' | 'private' {
  return TECH_TIERS.some(t => tier.includes(t)) ? 'tech' : 'private';
}

function fmt(s: string | null): string {
  if (!s) return '-';
  const c = s.replace(/-/g, '');
  if (c.length === 8) return `${c.slice(0,4)}.${c.slice(4,6)}.${c.slice(6,8)}`;
  return s;
}

function fmtRange(start: string | null, end: string | null): string {
  if (!start) return '-';
  const s = fmt(start);
  const e = end && end !== start ? ` ~ ${fmt(end)}` : '';
  return `${s}${e}`;
}

function DdayBadge({ dday }: { dday: number | null }) {
  if (dday === null) return null;
  if (dday < 0)   return <span className="sch-badge sch-badge-past">마감</span>;
  if (dday === 0)  return <span className="sch-badge sch-badge-today">D-Day</span>;
  if (dday <= 7)  return <span className="sch-badge sch-badge-urgent">D-{dday}</span>;
  if (dday <= 30) return <span className="sch-badge sch-badge-soon">D-{dday}</span>;
  return <span className="sch-badge sch-badge-future">D-{dday}</span>;
}

function TierBadge({ tier }: { tier: string }) {
  const cls = tier.includes('기술사') ? 'sch-tier-5'
    : tier.includes('기능장') ? 'sch-tier-4'
    : tier.includes('기사') && !tier.includes('산업') ? 'sch-tier-3'
    : tier.includes('산업기사') ? 'sch-tier-2'
    : tier.includes('기능사') ? 'sch-tier-1'
    : 'sch-tier-default';
  return <span className={`sch-tier-badge ${cls}`}>{tier}</span>;
}

// ── Cert Info Card (항상 표시) ──────────────────────────────────────────────
function CertInfoRow({ data, candidate }: { data: CertSchedule; candidate?: CertCandidate }) {
  const grade = data.cert_grade_tier || candidate?.cert_grade_tier || '';
  const passRate = data.avg_pass_rate_3yr ?? candidate?.avg_pass_rate_3yr;
  const domain = data.primary_domain || candidate?.primary_domain || '';
  const freq = data.exam_frequency || candidate?.exam_sessions_per_year?.toString() || '';
  const issuer = data.issuer || candidate?.issuer || '';

  return (
    <div className="sch-cert-info-row">
      <div className="sch-cert-info-left">
        {grade && <TierBadge tier={grade} />}
        {domain && <span className="sch-info-chip">{domain}</span>}
        {issuer && <span className="sch-info-chip sch-info-chip-muted">{issuer}</span>}
      </div>
      <div className="sch-cert-info-right">
        {passRate != null && (
          <span className="sch-pass-rate">
            <TrendingUp size={11} /> 평균 합격률 {passRate.toFixed(1)}%
          </span>
        )}
        {freq && <span className="sch-freq-chip">연 {freq}회</span>}
      </div>
    </div>
  );
}

// ── Schedule timeline (일정이 있을 때) ────────────────────────────────────
function ScheduleTimeline({ schedules }: { schedules: ScheduleItem[] }) {
  const upcoming = schedules.filter(s => (s.d_day_exam ?? -1) >= 0);
  const past     = schedules.filter(s => (s.d_day_exam ?? 0)  <  0);

  return (
    <div className="sch-timeline">
      {upcoming.length > 0 && (
        <div className="sch-timeline-section">
          <p className="sch-timeline-label">예정된 시험</p>
          {upcoming.map((s, i) => {
            return (
            <div key={i} className="sch-timeline-item sch-timeline-upcoming">
              <div className="sch-timeline-dot" />
              <div className="sch-timeline-body">
                <div className="sch-timeline-header">
                  <span className="sch-timeline-seq">{s.impl_seq_name ?? `${s.impl_seq}회`}</span>
                  <DdayBadge dday={s.d_day_exam} />
                  {s.d_day_registration !== null && s.d_day_registration !== undefined && s.d_day_registration >= 0 && (
                    <span className="sch-badge sch-badge-reg">접수 D-{s.d_day_registration}</span>
                  )}
                </div>
                <div className="sch-timeline-dates">
                  {s.registration_start && (
                    <span className="sch-td-date">
                      <span className="sch-td-key">접수</span>
                      {fmtRange(s.registration_start, s.registration_end)}
                    </span>
                  )}
                  {s.exam_start && (
                    <span className="sch-td-date">
                      <span className="sch-td-key">시험</span>
                      {fmtRange(s.exam_start, s.exam_end)}
                    </span>
                  )}
                  {s.pass_announce_date && (
                    <span className="sch-td-date">
                      <span className="sch-td-key">발표</span>
                      {fmt(s.pass_announce_date)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );})}
        </div>
      )}
      {past.length > 0 && (
        <details className="sch-past-details">
          <summary className="sch-past-summary">지난 일정 {past.length}건</summary>
          <div className="sch-timeline-section sch-past-section">
            {past.map((s, i) => (
              <div key={i} className="sch-timeline-item sch-timeline-past">
                <div className="sch-timeline-dot sch-dot-past" />
                <div className="sch-timeline-body">
                  <div className="sch-timeline-header">
                    <span className="sch-timeline-seq">{s.impl_seq_name ?? `${s.impl_seq}회`}</span>
                    <DdayBadge dday={s.d_day_exam} />
                  </div>
                  <div className="sch-timeline-dates">
                    {s.exam_start && (
                      <span className="sch-td-date">
                        <span className="sch-td-key">시험</span>
                        {fmtRange(s.exam_start, s.exam_end)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

// ── API 불가 시 fallback 패널 ──────────────────────────────────────────────
function ScheduleFallback({ certName, qnetSearchUrl, qnetScheduleUrl }: {
  certName: string;
  qnetSearchUrl: string;
  qnetScheduleUrl: string;
}) {
  return (
    <div className="sch-fallback">
      <div className="sch-fallback-notice">
        <AlertCircle size={13} />
        <span>Q-Net API 점검 중 — 공식 사이트에서 최신 일정을 확인하세요</span>
      </div>
      <div className="sch-fallback-actions">
        <a href={qnetSearchUrl} target="_blank" rel="noopener noreferrer" className="sch-fallback-btn sch-fallback-primary">
          <Calendar size={14} /> Q-Net에서 "{certName}" 시험일정 보기
          <ChevronRight size={13} />
        </a>
        <a href={qnetScheduleUrl} target="_blank" rel="noopener noreferrer" className="sch-fallback-btn sch-fallback-secondary">
          <ExternalLink size={13} /> 연도별 시험 일정 전체 보기
        </a>
        <a
          href={`https://www.google.com/search?q=${encodeURIComponent(`${certName} 시험 일정 2026`)}`}
          target="_blank" rel="noopener noreferrer"
          className="sch-fallback-btn sch-fallback-secondary"
        >
          <Search size={13} /> Google에서 검색
        </a>
      </div>
    </div>
  );
}

// ── Main cert card ─────────────────────────────────────────────────────────
function CertCard({ data, candidate }: { data: CertSchedule; candidate?: CertCandidate }) {
  const typeLabel = data.cert_type === 'tech' ? '국가기술' : '국가자격';
  const typeCls   = data.cert_type === 'tech' ? 'sch-type-tech' : 'sch-type-private';
  const hasSchedule = data.schedules.length > 0;
  const apiDown = !hasSchedule && data.api_status !== 'ok';

  const qnetSearch = data.qnet_search_url
    || `https://www.q-net.or.kr/crf005.do?id=crf00501&gSite=Q&jmNm=${encodeURIComponent(data.cert_name)}`;
  const qnetSchedule = data.qnet_schedule_url || 'https://www.q-net.or.kr/crf021.do?id=crf02101&scheType=03';

  const upcoming = data.schedules.filter(s => (s.d_day_exam ?? -1) >= 0);
  const nearest  = upcoming[0] ?? data.schedules[0] ?? null;

  return (
    <div className="sch-card">
      {/* 헤더 */}
      <div className="sch-card-header-info">
        <div className="sch-card-title-row">
          <span className="sch-cert-name">{data.cert_name}</span>
          <span className={`sch-type-badge ${typeCls}`}>{typeLabel}</span>
          {nearest && <DdayBadge dday={nearest.d_day_exam} />}
          {apiDown && <span className="sch-badge sch-badge-api-down">일정 조회 불가</span>}
        </div>
        {data.year && (
          <div className="sch-card-meta">
            <span className="sch-year">{data.year}년</span>
            {hasSchedule && <span className="sch-count">총 {data.total}회차</span>}
            {nearest?.exam_start && (
              <span className="sch-nearest"><Clock size={11} /> 최근 시험: {fmt(nearest.exam_start)}</span>
            )}
          </div>
        )}
      </div>

      {/* cert 기본 정보 */}
      <CertInfoRow data={data} candidate={candidate} />

      {/* 일정 또는 fallback */}
      {hasSchedule
        ? <ScheduleTimeline schedules={data.schedules} />
        : <ScheduleFallback certName={data.cert_name} qnetSearchUrl={qnetSearch} qnetScheduleUrl={qnetSchedule} />
      }

      {/* 항상 표시되는 Q-Net 링크 */}
      {hasSchedule && (
        <div className="sch-card-footer">
          <a href={qnetSearch} target="_blank" rel="noopener noreferrer" className="sch-qnet-link">
            <ExternalLink size={12} /> Q-Net 원서접수
          </a>
          <p className="sch-source">한국산업인력공단 Q-Net</p>
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────
const Schedule: React.FC = () => {
  const [query, setQuery]       = useState('');
  const [results, setResults]   = useState<{ data: CertSchedule; candidate: CertCandidate }[]>([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const schedCacheRef = useRef<Record<string, CertSchedule>>({});

  const fetchSchedule = useCallback(async (certId: string): Promise<CertSchedule | null> => {
    if (schedCacheRef.current[certId]) return schedCacheRef.current[certId];
    try {
      const r    = await fetch(`/api/v1/schedules/exams/${encodeURIComponent(certId)}`);
      const json = await r.json();
      if (json.success && json.data) {
        const sched: CertSchedule = {
          cert_id:   certId,
          cert_name: json.data.cert_name ?? '',
          cert_type: getTechType(json.data.cert_grade_tier ?? ''),
          year:      json.data.year ?? '',
          schedules: json.data.schedules ?? [],
          total:     json.data.total ?? 0,
          api_status:       json.data.api_status,
          cert_grade_tier:  json.data.cert_grade_tier,
          avg_pass_rate_3yr: json.data.avg_pass_rate_3yr,
          primary_domain:   json.data.primary_domain,
          exam_frequency:   json.data.exam_frequency,
          issuer:           json.data.issuer,
          qnet_search_url:   json.data.qnet_search_url,
          qnet_schedule_url: json.data.qnet_schedule_url,
          qnet_apply_url:    json.data.qnet_apply_url,
        };
        schedCacheRef.current[certId] = sched;
        return sched;
      }
    } catch { /* silent */ }
    return null;
  }, []);

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;

    setLoading(true);
    setError(null);
    setSearched(true);
    setResults([]);

    try {
      const allCerts = await getCertCandidates();
      const matched = allCerts
        .filter(c =>
          c.cert_name.includes(q) ||
          (c.aliases ?? []).some((a: string) => a.includes(q))
        )
        .slice(0, 10);

      if (matched.length === 0) {
        setLoading(false);
        return;
      }

      const settled = await Promise.allSettled(
        matched.map(c => fetchSchedule(c.cert_id))
      );

      const unified: { data: CertSchedule; candidate: CertCandidate }[] = [];
      for (let i = 0; i < matched.length; i++) {
        const candidate = matched[i];
        const r = settled[i];
        if (r.status === 'fulfilled' && r.value) {
          unified.push({ data: r.value, candidate });
        } else {
          // API 실패 시에도 candidate 데이터로 카드 구성
          unified.push({
            candidate,
            data: {
              cert_id:   candidate.cert_id,
              cert_name: candidate.cert_name,
              cert_type: getTechType(candidate.cert_grade_tier ?? ''),
              year:      new Date().getFullYear().toString(),
              schedules: [],
              total:     0,
              api_status:       'unavailable',
              cert_grade_tier:  candidate.cert_grade_tier,
              avg_pass_rate_3yr: candidate.avg_pass_rate_3yr,
              primary_domain:   candidate.primary_domain,
              issuer:           candidate.issuer,
            },
          });
        }
      }
      setResults(unified);
    } catch {
      setError('자격증 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
    setLoading(false);
  }, [query, fetchSchedule]);

  const exampleCerts = ['정보처리기사', '직업상담사', '산업안전기사', '전기기사', '사회복지사'];

  return (
    <div className="sch-wrap">
      <div className="sch-header">
        <h1 className="sch-title">시험 일정</h1>
        <p className="sch-sub">국가기술·전문자격 시험 일정 및 Q-Net 바로가기</p>
      </div>

      <form className="sch-search-form" onSubmit={handleSearch}>
        <div className="sch-search-inner">
          <Search size={16} className="sch-search-icon" />
          <input
            className="sch-search-input"
            type="text"
            placeholder="자격증명 검색 (예: 정보처리기사, 직업상담사)"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
          <button type="submit" className="btn-primary sch-search-btn" disabled={loading}>
            {loading ? <Loader2 size={15} className="spin" /> : '검색'}
          </button>
        </div>
        <div className="sch-quick-searches">
          {exampleCerts.map(c => (
            <button
              key={c} type="button" className="sch-quick-btn"
              onClick={() => { setQuery(c); }}
            >{c}</button>
          ))}
        </div>
      </form>

      {error && (
        <div className="sch-error"><AlertCircle size={16} /><span>{error}</span></div>
      )}
      {loading && (
        <div className="sch-loading">
          <Loader2 size={20} className="spin" />
          <span>자격증 정보를 조회하는 중…</span>
        </div>
      )}

      {!loading && searched && results.length === 0 && !error && (
        <div className="sch-empty">
          <BookOpen size={22} className="sch-empty-icon" />
          <div>
            <p className="sch-empty-title">"{query}"와 일치하는 자격증이 없습니다</p>
            <p className="sch-empty-hint">자격증 전체 이름으로 검색해보세요.</p>
            <a
              href={`https://www.q-net.or.kr/crf005.do?id=crf00501&gSite=Q&jmNm=${encodeURIComponent(query)}`}
              target="_blank" rel="noopener noreferrer"
              className="sch-empty-link"
            >
              <ExternalLink size={13} /> Q-Net에서 직접 검색 →
            </a>
          </div>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="sch-results">
          <p className="sch-result-count">
            {results.length}개 자격증 —{' '}
            {results.some(r => r.data.schedules.length > 0)
              ? '일정 데이터 포함'
              : 'Q-Net 바로가기 제공'}
          </p>
          {results.map(r => (
            <CertCard key={r.data.cert_id} data={r.data} candidate={r.candidate} />
          ))}
        </div>
      )}

      {!searched && !loading && (
        <div className="sch-guide-wrap">
          <div className="sch-guide-header">
            <h2 className="sch-guide-title">이용 안내</h2>
          </div>
          <div className="sch-guide">
            <div className="sch-guide-card">
              <div className="sch-guide-icon-wrap"><Calendar size={22} /></div>
              <h3>시험 일정 조회</h3>
              <p>자격증명 검색 시 Q-Net에 등록된 연도별 시험 일정·접수 기간·합격 발표일을 제공합니다.</p>
            </div>
            <div className="sch-guide-card">
              <div className="sch-guide-icon-wrap"><Clock size={22} /></div>
              <h3>D-Day 표시</h3>
              <p>시험까지 남은 일수(D-Day)와 접수 마감 D-Day를 한눈에 확인할 수 있습니다.</p>
            </div>
            <div className="sch-guide-card">
              <div className="sch-guide-icon-wrap"><ExternalLink size={22} /></div>
              <h3>Q-Net 바로가기</h3>
              <p>API 점검 중인 경우에도 Q-Net 공식 일정 페이지 바로가기 링크를 제공합니다.</p>
            </div>
          </div>
          <div className="sch-api-notice">
            <AlertCircle size={14} />
            <span>현재 Q-Net 시험일정 API 점검 중으로 일정 데이터가 제한될 수 있습니다. 검색 시 Q-Net 직접 링크를 제공합니다.</span>
          </div>
        </div>
      )}

      <style>{`
        .sch-wrap { display:flex; flex-direction:column; gap:1.5rem; max-width:860px; margin:0 auto; }
        .sch-header { display:flex; flex-direction:column; gap:.3rem; }
        .sch-title { font-size:1.75rem; font-weight:900; color:var(--text); margin:0; }
        .sch-sub { font-size:.875rem; color:var(--text-muted); margin:0; }

        /* 검색 */
        .sch-search-form { display:flex; flex-direction:column; gap:.625rem; }
        .sch-search-inner {
          display:flex; align-items:center; gap:.625rem;
          background:var(--surface-2); border:1.5px solid var(--border);
          border-radius:var(--radius-sm); padding:.55rem .875rem;
          transition:border-color .15s, box-shadow .15s;
        }
        .sch-search-inner:focus-within {
          border-color:var(--primary);
          box-shadow:0 0 0 3px rgba(37,99,235,.1);
        }
        .sch-search-icon { color:var(--text-light); flex-shrink:0; }
        .sch-search-input { flex:1; border:none; background:transparent; font-size:.95rem; color:var(--text); outline:none; }
        .sch-search-input::placeholder { color:var(--text-light); }
        .sch-search-btn { padding:.45rem 1.1rem; font-size:.875rem; }
        .sch-quick-searches { display:flex; gap:.375rem; flex-wrap:wrap; }
        .sch-quick-btn {
          padding:.3rem .65rem; font-size:.75rem; font-weight:600;
          background:var(--surface-2); border:1px solid var(--border);
          border-radius:20px; cursor:pointer; color:var(--text-muted);
          transition:all .15s;
        }
        .sch-quick-btn:hover { border-color:var(--primary); color:var(--primary); background:var(--primary-light); }

        /* 결과 */
        .sch-results { display:flex; flex-direction:column; gap:.875rem; }
        .sch-result-count { font-size:.78rem; color:var(--text-muted); margin:0; font-weight:600; }

        /* 카드 */
        .sch-card {
          border:1px solid var(--border); border-radius:10px;
          background:var(--surface-2); overflow:hidden;
          display:flex; flex-direction:column; gap:0;
        }
        .sch-card-header-info {
          display:flex; flex-direction:column; gap:.3rem;
          padding:1rem 1.125rem .625rem;
        }
        .sch-card-title-row { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; }
        .sch-cert-name { font-size:1.05rem; font-weight:800; color:var(--text); }
        .sch-card-meta { display:flex; align-items:center; gap:.625rem; flex-wrap:wrap; }
        .sch-year { font-size:.72rem; color:var(--text-light); }
        .sch-count { font-size:.72rem; color:var(--text-light); }
        .sch-nearest { font-size:.72rem; color:var(--text-muted); display:flex; align-items:center; gap:.25rem; }

        /* cert info row */
        .sch-cert-info-row {
          display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:.5rem;
          padding:.5rem 1.125rem .75rem;
          border-bottom:1px solid var(--border);
          background:var(--surface-3,#f8fafc);
        }
        .sch-cert-info-left { display:flex; gap:.375rem; flex-wrap:wrap; align-items:center; }
        .sch-cert-info-right { display:flex; gap:.375rem; align-items:center; }
        .sch-info-chip {
          font-size:.7rem; font-weight:600;
          background:var(--primary-light); color:var(--primary);
          padding:.15rem .5rem; border-radius:20px;
        }
        .sch-info-chip-muted {
          background:var(--surface-2); color:var(--text-muted);
          border:1px solid var(--border);
        }
        .sch-pass-rate { font-size:.72rem; color:#059669; display:flex; align-items:center; gap:.25rem; font-weight:700; }
        .sch-freq-chip {
          font-size:.7rem; background:#ede9fe; color:#6d28d9;
          padding:.15rem .5rem; border-radius:20px; font-weight:600;
        }

        /* tier badges */
        .sch-tier-badge {
          font-size:.66rem; font-weight:800; letter-spacing:.02em;
          padding:.15rem .5rem; border-radius:20px;
        }
        .sch-tier-1 { background:#f0fdf4; color:#16a34a; }
        .sch-tier-2 { background:#fef9c3; color:#ca8a04; }
        .sch-tier-3 { background:#dbeafe; color:#1e40af; }
        .sch-tier-4 { background:#fce7f3; color:#9d174d; }
        .sch-tier-5 { background:#ede9fe; color:#5b21b6; }
        .sch-tier-default { background:var(--border); color:var(--text-muted); }

        .sch-type-badge {
          display:inline-flex; align-items:center; padding:.15rem .5rem;
          border-radius:20px; font-size:.66rem; font-weight:700; letter-spacing:.04em;
        }
        .sch-type-tech    { background:#dbeafe; color:#1e40af; }
        .sch-type-private { background:#fef3c7; color:#92400e; }

        .sch-badge { display:inline-flex; align-items:center; padding:.15rem .5rem; border-radius:20px; font-size:.7rem; font-weight:700; }
        .sch-badge-past    { background:#f1f5f9; color:#94a3b8; }
        .sch-badge-today   { background:#fee2e2; color:#ef4444; }
        .sch-badge-urgent  { background:#fee2e2; color:#ef4444; animation:pulse .9s ease infinite; }
        .sch-badge-soon    { background:#fef3c7; color:#d97706; }
        .sch-badge-future  { background:#e0f2fe; color:#0284c7; }
        .sch-badge-reg     { background:#f0fdf4; color:#16a34a; }
        .sch-badge-api-down { background:#f1f5f9; color:#64748b; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.6} }

        /* Timeline */
        .sch-timeline { padding:.875rem 1.125rem; display:flex; flex-direction:column; gap:.75rem; }
        .sch-timeline-section { display:flex; flex-direction:column; gap:.5rem; }
        .sch-timeline-label { font-size:.68rem; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:.05em; margin:0 0 .25rem; }
        .sch-timeline-item { display:flex; gap:.75rem; align-items:flex-start; }
        .sch-timeline-dot {
          width:10px; height:10px; border-radius:50%;
          background:var(--primary); flex-shrink:0; margin-top:.35rem;
          box-shadow:0 0 0 3px rgba(37,99,235,.15);
        }
        .sch-dot-past { background:#cbd5e1; box-shadow:none; }
        .sch-timeline-body { display:flex; flex-direction:column; gap:.3rem; flex:1; }
        .sch-timeline-header { display:flex; align-items:center; gap:.375rem; flex-wrap:wrap; }
        .sch-timeline-seq { font-size:.85rem; font-weight:700; color:var(--text); }
        .sch-timeline-dates { display:flex; flex-wrap:wrap; gap:.5rem; }
        .sch-td-date { font-size:.78rem; color:var(--text-muted); display:flex; align-items:center; gap:.3rem; }
        .sch-td-key { font-size:.68rem; font-weight:700; color:var(--text-light); min-width:28px; }
        .sch-timeline-past { opacity:.5; }

        /* Past details */
        .sch-past-details { border-top:1px solid var(--border); margin:0 -1.125rem; padding:.5rem 1.125rem; background:var(--surface-3,#f8fafc); }
        .sch-past-summary { font-size:.75rem; color:var(--text-light); cursor:pointer; list-style:none; font-weight:600; }
        .sch-past-summary::-webkit-details-marker { display:none; }
        .sch-past-section { margin-top:.5rem; }

        /* Fallback */
        .sch-fallback { padding:.875rem 1.125rem; display:flex; flex-direction:column; gap:.75rem; }
        .sch-fallback-notice {
          display:flex; align-items:center; gap:.5rem;
          font-size:.75rem; color:#d97706; background:#fffbeb;
          border:1px solid #fde68a; border-radius:6px;
          padding:.5rem .75rem;
        }
        .sch-fallback-actions { display:flex; flex-direction:column; gap:.5rem; }
        .sch-fallback-btn {
          display:flex; align-items:center; gap:.5rem;
          padding:.6rem .875rem; border-radius:var(--radius-sm);
          font-size:.82rem; font-weight:600; text-decoration:none;
          transition:all .15s; border:none; cursor:pointer;
        }
        .sch-fallback-primary {
          background:var(--primary); color:#fff;
          justify-content:space-between;
        }
        .sch-fallback-primary:hover { background:#1d4ed8; }
        .sch-fallback-secondary {
          background:var(--surface); color:var(--text-muted);
          border:1px solid var(--border);
        }
        .sch-fallback-secondary:hover { border-color:var(--primary); color:var(--primary); }

        /* Card footer */
        .sch-card-footer {
          display:flex; align-items:center; justify-content:space-between;
          padding:.625rem 1.125rem;
          border-top:1px solid var(--border);
          background:var(--surface-3,#f8fafc);
        }
        .sch-qnet-link {
          display:inline-flex; align-items:center; gap:.35rem;
          font-size:.78rem; color:var(--primary); text-decoration:none;
          padding:.3rem .65rem; border:1px solid var(--primary);
          border-radius:var(--radius-sm); transition:background .15s;
        }
        .sch-qnet-link:hover { background:var(--primary-light); }
        .sch-source { font-size:.65rem; color:#94a3b8; margin:0; }

        /* 상태 */
        .sch-loading { display:flex; align-items:center; gap:.75rem; padding:2.5rem; justify-content:center; color:var(--text-muted); font-size:.9rem; }
        .sch-error { display:flex; align-items:center; gap:.625rem; padding:1rem 1.25rem; background:#fef2f2; border:1px solid #fecaca; border-radius:var(--radius-sm); color:#dc2626; font-size:.875rem; }
        .sch-empty {
          display:flex; align-items:flex-start; gap:.875rem;
          padding:2rem; background:var(--surface-2);
          border:1px dashed var(--border); border-radius:var(--radius-sm);
        }
        .sch-empty-icon { color:var(--border-strong); margin-top:.15rem; flex-shrink:0; }
        .sch-empty-title { font-size:.9rem; font-weight:700; color:var(--text); margin:0 0 .3rem; }
        .sch-empty-hint { font-size:.8rem; color:var(--text-muted); margin:0 0 .625rem; }
        .sch-empty-link {
          display:inline-flex; align-items:center; gap:.3rem;
          font-size:.8rem; color:var(--primary); text-decoration:none;
          font-weight:600;
        }
        .sch-empty-link:hover { text-decoration:underline; }

        /* Guide */
        .sch-guide-wrap { display:flex; flex-direction:column; gap:1rem; }
        .sch-guide-header { display:flex; align-items:center; gap:.5rem; }
        .sch-guide-title { font-size:1rem; font-weight:800; color:var(--text); margin:0; }
        .sch-guide { display:grid; grid-template-columns:repeat(3,1fr); gap:.75rem; }
        @media (max-width:640px) { .sch-guide { grid-template-columns:1fr; } }
        .sch-guide-card {
          display:flex; flex-direction:column; gap:.5rem;
          padding:1rem; background:var(--surface-2);
          border:1px solid var(--border); border-radius:10px;
          transition:border-color .15s, box-shadow .15s;
        }
        .sch-guide-card:hover { border-color:var(--primary); box-shadow:0 2px 8px rgba(37,99,235,.08); }
        .sch-guide-icon-wrap {
          width:38px; height:38px; border-radius:10px;
          background:var(--primary-light); color:var(--primary);
          display:flex; align-items:center; justify-content:center;
        }
        .sch-guide-card h3 { font-size:.875rem; font-weight:700; color:var(--text); margin:0; }
        .sch-guide-card p { font-size:.78rem; color:var(--text-muted); margin:0; line-height:1.65; }
        .sch-api-notice {
          display:flex; align-items:flex-start; gap:.5rem;
          padding:.625rem .875rem; font-size:.75rem; color:#d97706;
          background:#fffbeb; border:1px solid #fde68a; border-radius:var(--radius-sm);
        }

        .spin { animation:spin 1s linear infinite; }
        @keyframes spin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default Schedule;
