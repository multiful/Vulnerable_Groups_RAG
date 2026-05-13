// Content Hash: SHA256:TBD
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, ArrowLeft, AlertTriangle } from 'lucide-react';
import { clearPipeline, savePipeline } from '../../utils/pipelineState';

/* ─────────────────────────────────────────────
   기획서 F-01 기반 12문항
   관계망 4 · 활동 2 · 노동경제 2 · 정신건강 3 · 자기관리 1
   Safety Override: Q11(B12_9) "거의 매일" → 위기 안내
───────────────────────────────────────────── */

interface Question {
  id: string;
  category: string;
  text: string;
  options: { label: string; score: number }[];
  safetyKey?: boolean;
}

const QUESTIONS: Question[] = [
  /* ── 관계망 4문항 ── */
  {
    id: 'A12_1', category: '관계망',
    text: '중요하거나 어려운 일이 있을 때 조언을 구할 수 있는 사람이 있나요?',
    options: [
      { label: '여러 명 있다',               score: 0 },
      { label: '한두 명 있다',               score: 1 },
      { label: '있긴 하지만 연락하기 부담스럽다', score: 2 },
      { label: '거의 없다',                  score: 3 },
      { label: '전혀 없다',                  score: 4 },
    ],
  },
  {
    id: 'A12_2', category: '관계망',
    text: '급한 일이 생겼을 때 도움을 부탁할 수 있는 사람이 있나요?',
    options: [
      { label: '여러 명 있다',               score: 0 },
      { label: '한두 명 있다',               score: 1 },
      { label: '있긴 하지만 부탁하기 어렵다',  score: 2 },
      { label: '거의 없다',                  score: 3 },
      { label: '전혀 없다',                  score: 4 },
    ],
  },
  {
    id: 'A12_4', category: '관계망',
    text: '낙심하거나 우울할 때 속마음을 털어놓을 수 있는 사람이 있나요?',
    options: [
      { label: '여러 명 있다',               score: 0 },
      { label: '한두 명 있다',               score: 1 },
      { label: '있긴 하지만 말하기 어렵다',    score: 2 },
      { label: '거의 없다',                  score: 3 },
      { label: '전혀 없다',                  score: 4 },
    ],
  },
  {
    id: 'A13_4', category: '관계망',
    text: '지난 2주 동안 지인(가족 제외)과 직접 만난 날이 있었나요?',
    options: [
      { label: '주 3회 이상',   score: 0 },
      { label: '주 1~2회',      score: 1 },
      { label: '2주에 1~2회',   score: 2 },
      { label: '거의 없었다',   score: 3 },
      { label: '전혀 없었다',   score: 4 },
    ],
  },
  /* ── 활동 2문항 ── */
  {
    id: 'A7', category: '활동',
    text: '평소에 집 밖으로 외출하는 빈도는 어느 정도인가요?',
    options: [
      { label: '매일 또는 거의 매일',  score: 0 },
      { label: '주 3~5회',            score: 1 },
      { label: '주 1~2회',            score: 2 },
      { label: '월 1~3회',            score: 3 },
      { label: '거의 나가지 않는다',   score: 4 },
    ],
  },
  {
    id: 'A11', category: '활동',
    text: '지난 2주 동안 다른 사람(온라인 포함)과 대화를 나눈 빈도는?',
    options: [
      { label: '매일 여러 명과 대화',   score: 0 },
      { label: '거의 매일 누군가와 대화', score: 1 },
      { label: '주 2~3회',              score: 2 },
      { label: '주 1회 이하',           score: 3 },
      { label: '거의 대화하지 않았다',   score: 4 },
    ],
  },
  /* ── 노동·경제 2문항 ── */
  {
    id: 'A1', category: '노동·경제',
    text: '지난 한 주 동안 수입을 목적으로 일한 시간이 있었나요?',
    options: [
      { label: '정규직·계약직으로 일했다',         score: 0 },
      { label: '아르바이트·단기 일을 했다',          score: 1 },
      { label: '일은 없었지만 적극적으로 구직 중',   score: 2 },
      { label: '일도 없고 구직도 소극적이다',        score: 3 },
      { label: '일도 없고 지금 일할 생각도 없다',    score: 4 },
    ],
  },
  {
    id: 'A6', category: '노동·경제',
    text: '현재 본인의 경제 상황을 어떻게 느끼나요?',
    options: [
      { label: '여유롭다',                   score: 0 },
      { label: '크게 부족하지 않다',          score: 1 },
      { label: '다소 부족하다',               score: 2 },
      { label: '많이 부족하다',               score: 3 },
      { label: '매우 부족하고 생계가 어렵다',  score: 4 },
    ],
  },
  /* ── 정신건강 3문항 ── */
  {
    id: 'B12_1', category: '정신건강',
    text: '지난 2주 동안 기분이 가라앉거나, 우울하거나, 희망이 없다고 느낀 날이 있었나요?',
    options: [
      { label: '전혀 없었다',    score: 0 },
      { label: '며칠 있었다',    score: 1 },
      { label: '일주일 이상',    score: 2 },
      { label: '거의 매일',      score: 3 },
    ],
  },
  {
    id: 'B12_2', category: '정신건강',
    text: '지난 2주 동안 평소 즐기던 활동에 흥미나 즐거움을 느끼지 못한 날이 있었나요?',
    options: [
      { label: '전혀 없었다',    score: 0 },
      { label: '며칠 있었다',    score: 1 },
      { label: '일주일 이상',    score: 2 },
      { label: '거의 매일',      score: 3 },
    ],
  },
  {
    id: 'B12_9', category: '정신건강',
    safetyKey: true,
    text: '지난 2주 동안 차라리 죽는 게 낫겠다거나 자해하고 싶다는 생각이 든 날이 있었나요?',
    options: [
      { label: '전혀 없었다',    score: 0 },
      { label: '며칠 있었다',    score: 1 },
      { label: '일주일 이상',    score: 2 },
      { label: '거의 매일',      score: 3 },
    ],
  },
  /* ── 자기관리 1문항 ── */
  {
    id: 'B9_4', category: '자기관리',
    text: '식사, 개인위생, 방 정리 등 일상적인 자기 관리가 잘 이루어지고 있나요?',
    options: [
      { label: '매일 규칙적으로 한다',    score: 0 },
      { label: '대체로 하는 편이다',      score: 1 },
      { label: '가끔 빠트리는 편이다',    score: 2 },
      { label: '잘 하지 못하고 있다',     score: 3 },
      { label: '거의 하지 않고 있다',     score: 4 },
    ],
  },
];

const TOTAL_MAX = QUESTIONS.reduce((s, q) => s + Math.max(...q.options.map(o => o.score)), 0);

const CATEGORY_COLORS: Record<string, string> = {
  '관계망':    '#6366f1',
  '활동':      '#0ea5e9',
  '노동·경제': '#f59e0b',
  '정신건강':  '#f43f5e',
  '자기관리':  '#10b981',
};

function scoreToStage(score: number, safetyTriggered: boolean): string {
  const pct = score / TOTAL_MAX;
  if (safetyTriggered && pct < 0.8) {
    /* Safety override: 위기 응답 시 최소 4단계 이상 */
    return pct < 0.6 ? '4' : '5';
  }
  if (pct < 0.2)  return '1';
  if (pct < 0.38) return '2';
  if (pct < 0.56) return '3';
  if (pct < 0.74) return '4';
  return '5';
}

const STAGE_LABELS: Record<string, { label: string; sub: string; color: string }> = {
  '1': { label: '1단계', sub: '취업 안정권', color: '#10b981' },
  '2': { label: '2단계', sub: '준비 활성',   color: '#0ea5e9' },
  '3': { label: '3단계', sub: '준비 정체',   color: '#6366f1' },
  '4': { label: '4단계', sub: '고위험군',    color: '#f59e0b' },
  '5': { label: '5단계', sub: '최고위험군',  color: '#f43f5e' },
};

const RiskAssessment: React.FC = () => {
  const navigate = useNavigate();

  const [step, setStep]       = useState<'survey' | 'result'>('survey');
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [safetyFlag, setSafetyFlag] = useState(false);

  const q = QUESTIONS[current];
  const progress = ((current) / QUESTIONS.length) * 100;
  const answered = answers[q.id] !== undefined;

  function select(score: number) {
    const newAnswers = { ...answers, [q.id]: score };
    setAnswers(newAnswers);
    if (q.safetyKey && score >= 2) setSafetyFlag(true);
    if (current < QUESTIONS.length - 1) {
      setTimeout(() => setCurrent(c => c + 1), 260);
    }
  }

  function finish() {
    setStep('result');
  }

  function goNext() {
    if (current < QUESTIONS.length - 1) setCurrent(c => c + 1);
    else finish();
  }

  function goPrev() {
    if (current > 0) setCurrent(c => c - 1);
  }

  /* ── Result ── */
  if (step === 'result') {
    const totalScore = QUESTIONS.reduce((s, q) => s + (answers[q.id] ?? 0), 0);
    const stage = scoreToStage(totalScore, safetyFlag);
    const pct = Math.round((totalScore / TOTAL_MAX) * 100);
    const info = STAGE_LABELS[stage];

    const categoryScores = Object.entries(
      QUESTIONS.reduce<Record<string, { score: number; max: number }>>((acc, q) => {
        const max = Math.max(...q.options.map(o => o.score));
        acc[q.category] = acc[q.category] || { score: 0, max: 0 };
        acc[q.category].score += answers[q.id] ?? 0;
        acc[q.category].max   += max;
        return acc;
      }, {})
    );

    return (
      <div className="survey-wrap">
        <div className="page-header">
          <h1 className="page-title">진단 결과</h1>
          <p className="page-desc">12문항 응답 기반으로 산출된 위험군 단계입니다.</p>
        </div>

        {safetyFlag && (
          <div className="safety-banner">
            <div className="safety-banner-icon"><AlertTriangle size={17} /></div>
            <div className="safety-banner-body">
              <p className="safety-title">정서적으로 힘드신 것 같아요</p>
              <p className="safety-sub">지금 많이 힘드시다면 전문 상담을 받아보시는 게 도움이 될 수 있습니다.</p>
              <a href="tel:1393" className="safety-cta">1393 자살예방상담전화에 전화하기</a>
            </div>
          </div>
        )}

        <div className="card result-card">
          <div className="result-stage-row">
            <div className="result-badge" style={{ background: info.color + '18', color: info.color, borderColor: info.color + '40' }}>
              {info.label}
            </div>
            <div>
              <p className="result-stage-name">{info.sub}</p>
              <p className="result-score-sub">위험도 점수 {pct}점 / 100점</p>
            </div>
          </div>

          <div className="result-bar-bg">
            <div className="result-bar-fill" style={{ width: `${pct}%`, background: info.color }} />
          </div>

          {/* ── 방사형 차트 ── */}
          <div className="result-radar-wrap">
            <svg viewBox="0 0 260 260" className="result-radar-svg">
              {/* 격자 링 25/50/75/100% */}
              {[0.25, 0.5, 0.75, 1].map(frac => (
                <polygon
                  key={frac}
                  points={categoryScores.map((_entry, i) => {
                    const a = -Math.PI / 2 + (2 * Math.PI / 5) * i;
                    const r = frac * 90;
                    return `${130 + r * Math.cos(a)},${130 + r * Math.sin(a)}`;
                  }).join(' ')}
                  fill="none"
                  stroke="var(--border)"
                  strokeWidth={frac === 1 ? 1.5 : 0.8}
                />
              ))}
              {/* 축 선 */}
              {categoryScores.map(([cat], i) => {
                const a = -Math.PI / 2 + (2 * Math.PI / 5) * i;
                return (
                  <line key={cat}
                    x1="130" y1="130"
                    x2={130 + 90 * Math.cos(a)} y2={130 + 90 * Math.sin(a)}
                    stroke="var(--border)" strokeWidth="1"
                  />
                );
              })}
              {/* 데이터 다각형 */}
              <polygon
                points={categoryScores.map(([, { score, max }], i) => {
                  const a = -Math.PI / 2 + (2 * Math.PI / 5) * i;
                  const r = (score / max) * 90;
                  return `${130 + r * Math.cos(a)},${130 + r * Math.sin(a)}`;
                }).join(' ')}
                fill={info.color}
                fillOpacity="0.18"
                stroke={info.color}
                strokeWidth="2.5"
                strokeLinejoin="round"
              />
              {/* 꼭짓점 점 */}
              {categoryScores.map(([cat, { score, max }], i) => {
                const a = -Math.PI / 2 + (2 * Math.PI / 5) * i;
                const r = (score / max) * 90;
                return (
                  <circle key={cat}
                    cx={130 + r * Math.cos(a)} cy={130 + r * Math.sin(a)}
                    r="4.5" fill={CATEGORY_COLORS[cat] ?? info.color}
                    stroke="#fff" strokeWidth="1.5"
                  />
                );
              })}
              {/* 라벨 */}
              {categoryScores.map(([cat], i) => {
                const a = -Math.PI / 2 + (2 * Math.PI / 5) * i;
                const r = 108;
                const x = 130 + r * Math.cos(a);
                const y = 130 + r * Math.sin(a);
                const anchor =
                  Math.abs(Math.cos(a)) < 0.15 ? 'middle'
                  : Math.cos(a) > 0 ? 'start' : 'end';
                return (
                  <text key={cat} x={x} y={y}
                    textAnchor={anchor} dominantBaseline="middle"
                    fontSize="10.5" fontWeight="700"
                    fill={CATEGORY_COLORS[cat] ?? '#888'}
                  >
                    {cat}
                  </text>
                );
              })}
            </svg>
          </div>

          <div className="result-cats">
            {categoryScores.map(([cat, { score, max }]) => {
              const catPct = Math.round((score / max) * 100);
              return (
                <div key={cat} className="result-cat-row">
                  <span className="result-cat-label">{cat}</span>
                  <div className="result-cat-bar-bg">
                    <div
                      className="result-cat-bar-fill"
                      style={{ width: `${catPct}%`, background: CATEGORY_COLORS[cat] ?? '#6366f1' }}
                    />
                  </div>
                  <span className="result-cat-pct">{catPct}%</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="result-actions">
          <button className="btn-ghost" onClick={() => { setStep('survey'); setCurrent(0); setAnswers({}); setSafetyFlag(false); }}>
            <ArrowLeft size={15} /> 다시 진단
          </button>
          <button className="btn-primary" onClick={() => {
              clearPipeline();
              savePipeline({ stage });
              navigate(`/interests?stage=${stage}`);
            }}>
            관심 분야 선택하기 <ArrowRight size={15} />
          </button>
        </div>

        <style>{`
          .result-card { padding:1.75rem; display:flex; flex-direction:column; gap:1.25rem; }
          .result-stage-row { display:flex; align-items:center; gap:1rem; }
          .result-badge {
            padding:.4rem 1rem; border-radius:var(--radius-sm);
            font-size:.9rem; font-weight:800; border:1.5px solid;
            white-space:nowrap;
          }
          .result-stage-name { font-size:1.3rem; font-weight:800; color:var(--text); }
          .result-score-sub { font-size:.85rem; color:var(--text-muted); margin-top:.2rem; }
          .result-bar-bg { height:10px; background:var(--border); border-radius:99px; overflow:hidden; }
          .result-bar-fill { height:100%; border-radius:99px; transition:width 0.8s ease; }
          .result-cats { display:flex; flex-direction:column; gap:.625rem; }
          .result-cat-row { display:flex; align-items:center; gap:.75rem; }
          .result-cat-label { font-size:.78rem; font-weight:600; color:var(--text-muted); width:68px; flex-shrink:0; }
          .result-cat-bar-bg { flex:1; height:6px; background:var(--border); border-radius:99px; overflow:hidden; }
          .result-cat-bar-fill { height:100%; border-radius:99px; transition:width 0.6s ease; }
          .result-cat-pct { font-size:.75rem; color:var(--text-light); width:32px; text-align:right; flex-shrink:0; }
          .result-radar-wrap {
            display:flex; justify-content:center; padding:.25rem 0;
          }
          .result-radar-svg {
            width:100%; max-width:240px; height:auto; overflow:visible;
          }
          .result-actions { display:flex; gap:.75rem; flex-wrap:wrap; }
        `}</style>
      </div>
    );
  }

  /* ── Survey ── */
  return (
    <div className="survey-wrap">
      <div className="page-header">
        <h1 className="page-title">위험군 진단</h1>
        <p className="page-desc">12개 질문에 솔직하게 답해주세요. 결과를 바탕으로 맞춤 자격증을 추천해드립니다.</p>
      </div>

      {/* Progress */}
      <div className="survey-progress-wrap">
        <div className="survey-progress-info">
          <span className="survey-q-num">{current + 1} / {QUESTIONS.length}</span>
          <span className="survey-cat-badge" style={{ background: (CATEGORY_COLORS[q.category] ?? '#6366f1') + '18', color: CATEGORY_COLORS[q.category] ?? '#6366f1' }}>
            {q.category}
          </span>
        </div>
        <div className="survey-prog-bar-bg">
          <div className="survey-prog-bar-fill" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {/* Question card */}
      <div className="card survey-card" key={current}>
        {q.safetyKey && (
          <div className="safety-notice">
            <AlertTriangle size={14} />
            <span>이 질문은 정서적 위기와 관련된 항목입니다. 편하게 솔직하게 답해주세요.</span>
          </div>
        )}

        <p className="survey-q-text">{q.text}</p>

        <div className="survey-options">
          {q.options.map(opt => {
            const isSel = answers[q.id] === opt.score;
            return (
              <button
                key={opt.score}
                className={`survey-opt ${isSel ? 'selected' : ''}`}
                onClick={() => select(opt.score)}
                type="button"
              >
                <span className="survey-opt-radio">{isSel ? '●' : '○'}</span>
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Navigation */}
      <div className="survey-nav">
        <button className="btn-ghost" onClick={goPrev} disabled={current === 0}>
          <ArrowLeft size={15} /> 이전
        </button>
        {current === QUESTIONS.length - 1 ? (
          <button className="btn-primary" disabled={!answered} onClick={finish}>
            결과 보기 <ArrowRight size={15} />
          </button>
        ) : (
          <button className="btn-primary" disabled={!answered} onClick={goNext}>
            다음 <ArrowRight size={15} />
          </button>
        )}
      </div>

      <style>{`
        .survey-wrap { max-width:640px; display:flex; flex-direction:column; gap:1.5rem; margin:0 auto; }
        .survey-progress-wrap { display:flex; flex-direction:column; gap:.5rem; }
        .survey-progress-info { display:flex; align-items:center; gap:.75rem; }
        .survey-q-num { font-size:.85rem; font-weight:700; color:var(--text-muted); }
        .survey-cat-badge {
          padding:.2rem .65rem; border-radius:var(--radius-full);
          font-size:.72rem; font-weight:700;
        }
        .survey-prog-bar-bg { height:5px; background:var(--border); border-radius:99px; overflow:hidden; }
        .survey-prog-bar-fill {
          height:100%; border-radius:99px;
          background:var(--gradient-primary);
          transition:width 0.35s ease;
        }
        .survey-card {
          padding:1.75rem; display:flex; flex-direction:column; gap:1.25rem;
          animation:survey-in .18s ease;
        }
        @keyframes survey-in {
          from { opacity:0; transform:translateX(10px); }
          to   { opacity:1; transform:none; }
        }
        .safety-notice {
          display:flex; align-items:center; gap:.5rem;
          padding:.6rem .875rem; background:var(--warning-light);
          border-radius:var(--radius-xs); font-size:.8rem;
          color:#92400e; border:1px solid rgba(245,158,11,.25);
        }
        .survey-q-text {
          font-size:1.05rem; font-weight:700; color:var(--text);
          line-height:1.55;
        }
        .survey-options { display:flex; flex-direction:column; gap:.5rem; }
        .survey-opt {
          display:flex; align-items:center; gap:.75rem;
          padding:.875rem 1rem; border-radius:var(--radius-sm);
          border:1.5px solid var(--border); background:var(--surface);
          text-align:left; font-size:.9rem; color:var(--text-muted);
          font-weight:500; transition:var(--transition); cursor:pointer;
          width:100%;
        }
        .survey-opt:hover { border-color:var(--border-strong); background:var(--surface-2); color:var(--text); }
        .survey-opt.selected {
          border-color:var(--primary); background:var(--primary-light);
          color:var(--primary); font-weight:700;
          box-shadow:0 2px 12px var(--primary-glow);
        }
        .survey-opt-radio { font-size:.9rem; flex-shrink:0; }
        .survey-nav {
          display:flex; gap:.75rem; align-items:center; justify-content:space-between;
        }
        .safety-banner {
          display:flex; gap:.75rem; align-items:flex-start;
          padding:1rem 1.25rem; background:var(--danger-light);
          border:1px solid rgba(244,63,94,.25);
          border-radius:var(--radius-sm);
        }
        .safety-banner-icon { flex-shrink:0; color:var(--danger); padding-top:.1rem; }
        .safety-banner-body { display:flex; flex-direction:column; gap:.3rem; flex:1; }
        .safety-title { font-weight:700; font-size:.9rem; color:#9f1239; }
        .safety-sub { font-size:.82rem; color:#be123c; line-height:1.55; }
        .safety-cta {
          display:inline-block; width:fit-content;
          margin-top:.35rem; padding:.45rem .875rem;
          background:var(--danger); color:#fff;
          border-radius:var(--radius-sm); font-size:.82rem; font-weight:700;
          text-decoration:none;
        }
      `}</style>
    </div>
  );
};

export default RiskAssessment;
