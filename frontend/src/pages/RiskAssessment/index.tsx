// Content Hash: SHA256:TBD
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, ArrowLeft, AlertTriangle } from 'lucide-react';
import { clearPipeline, savePipeline } from '../../utils/pipelineState';
import { recordDiagnosisComplete } from '../../utils/userHistory';
import { fetchHydeEvidence } from '../../api/client';
import type { StageEvidenceItem } from '../../api/client';

const SURVEY_KEY = 'didim_survey_v1';
const SURVEY_TTL_MS = 7 * 24 * 60 * 60 * 1000;

function _loadSurvey() {
  try {
    const raw = localStorage.getItem(SURVEY_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (Date.now() - (data.savedAt ?? 0) > SURVEY_TTL_MS) {
      localStorage.removeItem(SURVEY_KEY);
      return null;
    }
    return data;
  } catch { return null; }
}
function _clearSurvey() {
  try { localStorage.removeItem(SURVEY_KEY); } catch {}
}

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

/* ─────────────────────────────────────────────────────────────────────
   2차 정밀 판별 3문항 (SCRIPT.md §4 — 3단계↔4단계 구분)
   AUC 0.74~0.78. 총점 ≥ 50% 케이스에서만 진입.
   근거 실측 h: Q1↔A7(0.617) / Q2↔A13_3(1.026) / Q3↔B12_3(0.615)
───────────────────────────────────────────────────────────────────── */
interface PrecisionQ {
  id: string;
  text: string;
  options: { label: string; value: number }[];
}
const PRECISION_QUESTIONS: PrecisionQ[] = [
  {
    id: 'P_Q1',
    text: '마지막으로 집 밖을 나간 것이 언제입니까?',
    options: [
      { label: '오늘', value: 1 },
      { label: '2~3일 전', value: 2 },
      { label: '1주일 전', value: 3 },
      { label: '2주~1달 전', value: 4 },
      { label: '1달 이상 전', value: 5 },
    ],
  },
  {
    id: 'P_Q2',
    text: '가족 이외에 누군가와 마지막으로 만난 것이 언제입니까?',
    options: [
      { label: '1달 이상 전', value: 1 },
      { label: '2주~1달 전', value: 2 },
      { label: '1주일 전', value: 3 },
      { label: '최근 며칠', value: 4 },
    ],
  },
  {
    id: 'P_Q3',
    text: '최근 잠들기 어렵거나 너무 많이 자는 날이 얼마나 됩니까?',
    options: [
      { label: '없음', value: 1 },
      { label: '1~2일', value: 2 },
      { label: '3~5일', value: 3 },
      { label: '거의 매일 (6~7일)', value: 4 },
    ],
  },
];

const CATEGORY_COLORS: Record<string, string> = {
  '관계망':    '#6366f1',
  '활동':      '#0ea5e9',
  '노동·경제': '#f59e0b',
  '정신건강':  '#f43f5e',
  '자기관리':  '#10b981',
};

// SCRIPT.md §5 판별 규칙
// 1·2단계: 총점 비율로 결정
// 3↔4단계: 2차 3문항 precision answers 기반
//   4단계 = P_Q1=④⑤ AND (P_Q2=① OR P_Q3=③④)
function scoreToStage(score: number, pa: Record<string, number>): string {
  const pct = score / TOTAL_MAX;
  if (pct < 0.25) return '1';
  if (pct < 0.5)  return '2';
  const q1Hi = (pa['P_Q1'] ?? 0) >= 4;
  const q2Hi = (pa['P_Q2'] ?? 0) === 1;
  const q3Hi = (pa['P_Q3'] ?? 0) >= 3;
  if (q1Hi && (q2Hi || q3Hi)) return '4';
  return '3';
}

const STAGE_LABELS: Record<string, { label: string; sub: string; color: string }> = {
  '1': { label: '1단계', sub: '고립위험청년',          color: '#10b981' },
  '2': { label: '2단계', sub: '활동형 고립청년',       color: '#0ea5e9' },
  '3': { label: '3단계', sub: '활동 제한형 고립청년',  color: '#f59e0b' },
  '4': { label: '4단계', sub: '은둔 청년',             color: '#4f46e5' },
};

const STAGE_INTRO: Record<string, { headline: string; sub: string }> = {
  '1': {
    headline: '첫걸음을 내딛기 좋은 자격증들이 있어요',
    sub: '지금 상황에서 도전하기 좋은 자격증들을 추천해드릴게요.',
  },
  '2': {
    headline: '지금 상황에서 시작할 수 있는 자격증들을 찾았어요',
    sub: '관심 있는 분야부터 천천히 살펴볼 수 있어요.',
  },
  '3': {
    headline: '지금 상황에서도 도전할 수 있는 자격증들이 있어요',
    sub: '부담되지 않는 것부터 관심 분야를 살펴볼 수 있어요.',
  },
  '4': {
    headline: '지금 내 상황에서도 시작할 수 있는 자격증들이 있어요',
    sub: '혼자 해내기 어렵지 않은 것부터 천천히 살펴볼 수 있어요.',
  },
};

/* ─────────────────────────────────────────────────────────────────────
   표12 근거 데이터: 보건복지부 고립은둔 청년 지원사업 모형 개발 연구
   김성아 (2022). 정책보고서 2022-35. 요약 표 12.
   지원 대상 유형 및 지원목표에 따른 핵심 서비스
   ───────────────────────────────────────────────────────────────────── */
interface ProgramItem {
  text: string;
  url?: string;
}
interface SupportProgram {
  category: string;
  categoryDesc: string;
  items: ProgramItem[];
}
interface StagePolicy {
  isolationType: string;
  strategy: string;
  characteristic: string;
  programs: SupportProgram[];
}

const STAGE_POLICY: Record<string, StagePolicy> = {
  '1': {
    isolationType: '고립 위험 청년',
    strategy: '예방을 위한 연계 및 추적관리',
    characteristic:
      '관계 형성과 소통에 어려움이 높지 않고, 취·창업 등 사회이행을 위한 노력을 하고 있는 상태입니다.',
    programs: [
      {
        category: '자기이해 및 심리상담',
        categoryDesc: '고립된 삶 단계',
        items: [
          { text: '예방을 위한 심리·상담 연계 및 추적관리', url: 'https://www.bokjiro.go.kr' },
        ],
      },
      {
        category: '일 경험 및 사회활동',
        categoryDesc: '회복 단계',
        items: [
          { text: '청년도전지원사업 연계', url: 'https://www.work24.go.kr' },
          { text: '자기개발 및 진로탐색 프로그램', url: 'https://www.work24.go.kr' },
          { text: '일 경험 프로그램 참여', url: 'https://www.work24.go.kr' },
        ],
      },
      {
        category: '사후관리',
        categoryDesc: '통합된 삶 단계',
        items: [
          { text: '지역 기반 사회적 관계 형성 프로그램 참여 (독서모임, 미술모임, 가드닝모임, 요리모임 등)', url: 'https://www.mogef.go.kr' },
          { text: '자조모임 운영 및 참여' },
        ],
      },
    ],
  },
  '2': {
    isolationType: '활동형 고립 청년',
    strategy: '맞춤형 사례관리',
    characteristic:
      '관계에 어려움이 높지 않으나 문제해결 및 대처능력이 부족하고, 취·창업 등 사회이행 노력을 하고 있지만 사회 안착에서 반복적으로 탈락한 경험이 있는 상태입니다.',
    programs: [
      {
        category: '자기이해 및 심리상담',
        categoryDesc: '고립된 삶 단계',
        items: [
          { text: '자기이해 워크숍 (집단활동 프로그램, 자기 이미지 이해와 관리 등)', url: 'https://www.mogef.go.kr' },
          { text: '마음건강바우처 등 심리·상담 지원 연계 (1:1 심리상담, 집단상담, 방문상담, 온라인상담 등)', url: 'https://www.bokjiro.go.kr' },
        ],
      },
      {
        category: '치유적 관계 형성',
        categoryDesc: '회복 단계',
        items: [
          { text: '치유적 관계 형성 프로그램 (3끼 식사, 신체활동, 예술활동, 놀이활동 등)', url: 'https://www.mogef.go.kr' },
        ],
      },
      {
        category: '일 경험 및 사회활동',
        categoryDesc: '회복 단계',
        items: [
          { text: '고립·은둔청년 활동가 양성 및 활동', url: 'https://www.mogef.go.kr' },
        ],
      },
      {
        category: '사후관리',
        categoryDesc: '통합된 삶 단계',
        items: [
          { text: '지역 기반 사회적 관계 형성 프로그램 참여 (독서모임, 미술모임, 가드닝모임, 요리모임 등)', url: 'https://www.mogef.go.kr' },
          { text: '자조모임 운영 및 참여' },
        ],
      },
    ],
  },
  '3': {
    isolationType: '활동 제한형 고립 청년',
    strategy: '맞춤형 사례관리',
    characteristic:
      '대인관계 및 사회생활에 어려움이 있으며, 기본적인 사회활동과 욕구 관련 활동을 선택적으로 하지만 비자발적인 상태입니다.',
    programs: [
      {
        category: '자기이해 및 심리상담',
        categoryDesc: '고립된 삶 단계',
        items: [
          { text: '자기이해 워크숍 (집단활동 프로그램, 자기 이미지 이해와 관리 등)', url: 'https://www.mogef.go.kr' },
          { text: '마음건강바우처 등 심리·상담 지원 연계 (1:1 심리상담, 집단상담, 방문상담, 온라인상담 등)', url: 'https://www.bokjiro.go.kr' },
          { text: '정신건강의학과 등 심리치료 연계', url: 'https://www.mentalhealth.go.kr' },
        ],
      },
      {
        category: '치유적 관계 형성',
        categoryDesc: '회복 단계',
        items: [
          { text: '치유적 관계 형성 프로그램 (3끼 식사, 신체활동, 예술활동, 놀이활동 등)', url: 'https://www.mogef.go.kr' },
        ],
      },
      {
        category: '경제·생계·주거 지원',
        categoryDesc: '기반 안정',
        items: [
          { text: '긴급복지 및 주거 지원 연계', url: 'https://www.bokjiro.go.kr' },
        ],
      },
    ],
  },
  '4': {
    isolationType: '은둔 청년',
    strategy: '맞춤형 사례관리',
    characteristic:
      '가족 및 타인과의 소통이 어렵고, 외부 접촉을 최소화하며 특정 공간에서만 생활하거나 은둔과 사회활동을 반복하는 상태입니다.',
    programs: [
      {
        category: '자기이해 및 심리상담',
        categoryDesc: '고립된 삶 단계',
        items: [
          { text: '자기이해 워크숍 (집단활동 프로그램, 자기 이미지 이해와 관리 등)', url: 'https://www.mogef.go.kr' },
          { text: '마음건강바우처 등 심리·상담 지원 연계 (1:1 심리상담, 집단상담, 방문상담, 온라인상담 등)', url: 'https://www.bokjiro.go.kr' },
          { text: '정신건강의학과 등 심리치료 연계', url: 'https://www.mentalhealth.go.kr' },
        ],
      },
      {
        category: '치유적 관계 형성',
        categoryDesc: '회복 단계',
        items: [
          { text: '공동생활 참여', url: 'https://www.mogef.go.kr' },
          { text: '시간 및 일상생활 관리 프로그램 (수면 및 위생 관리, 정리정돈)' },
          { text: '사회기술 재학습 프로그램' },
        ],
      },
      {
        category: '경제·생계·주거 지원',
        categoryDesc: '기반 안정',
        items: [
          { text: '생계급여 및 긴급복지 연계 등 생계비 및 주거 지원', url: 'https://www.bokjiro.go.kr' },
        ],
      },
    ],
  },
};

const RiskAssessment: React.FC = () => {
  const navigate = useNavigate();

  const [step, setStep]       = useState<'survey' | 'precision' | 'result'>('survey');
  const [current, setCurrent] = useState(() => (_loadSurvey()?.current ?? 0));
  const [answers, setAnswers] = useState<Record<string, number>>(() => (_loadSurvey()?.answers ?? {}));
  const [safetyFlag, setSafetyFlag] = useState<boolean>(() => (_loadSurvey()?.safetyFlag ?? false));
  const [safetyGatePassed, setSafetyGatePassed] = useState(() => ((_loadSurvey()?.current ?? 0) > 10));
  const [wasRestored, setWasRestored] = useState(() => {
    const s = _loadSurvey();
    return (s?.current ?? 0) > 0;
  });
  const [precisionAnswers, setPrecisionAnswers] = useState<Record<string, number>>({});

  /* ── HyDE 분류 근거 ── */
  const [evidence, setEvidence] = useState<StageEvidenceItem[]>([]);
  const [evidenceSynthesis, setEvidenceSynthesis] = useState<string | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [showEvidenceSources, setShowEvidenceSources] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [showPrograms, setShowPrograms] = useState(false);
  const [showPolicyCard, setShowPolicyCard] = useState(false);

  useEffect(() => {
    if (step !== 'result') return;
    const totalScore = QUESTIONS.reduce((s, q) => s + (answers[q.id] ?? 0), 0);
    const stageId = scoreToStage(totalScore, precisionAnswers);
    recordDiagnosisComplete(stageId, STAGE_LABELS[stageId]?.sub);

    const catAccum = QUESTIONS.reduce<Record<string, { score: number; max: number }>>((acc, q) => {
      const mx = Math.max(...q.options.map(o => o.score));
      if (!acc[q.category]) acc[q.category] = { score: 0, max: 0 };
      acc[q.category].score += answers[q.id] ?? 0;
      acc[q.category].max += mx;
      return acc;
    }, {});
    const dimPct: Record<string, number> = {};
    for (const [cat, { score, max }] of Object.entries(catAccum)) {
      dimPct[cat] = max > 0 ? Math.round((score / max) * 100) : 0;
    }

    setEvidence([]);
    setEvidenceSynthesis(null);
    setShowEvidenceSources(false);
    setEvidenceLoading(true);
    fetchHydeEvidence(stageId, dimPct)
      .then(result => {
        setEvidenceSynthesis(result.synthesis);
        setEvidence(result.evidence.slice(0, 3));
      })
      .catch(() => { setEvidence([]); setEvidenceSynthesis(null); })
      .finally(() => setEvidenceLoading(false));
  }, [step]); // eslint-disable-line react-hooks/exhaustive-deps

  const radioGroupRef = useRef<HTMLDivElement>(null);

  const q = QUESTIONS[current];
  const progress = ((current + 1) / QUESTIONS.length) * 100;
  const answered = answers[q.id] !== undefined;

  function _saveProgress(cur: number, ans: Record<string, number>, sf: boolean) {
    try {
      localStorage.setItem(SURVEY_KEY, JSON.stringify({
        current: cur, answers: ans, safetyFlag: sf, savedAt: Date.now(),
      }));
    } catch {}
  }

  function select(score: number) {
    const newAnswers  = { ...answers, [q.id]: score };
    const newSafety   = safetyFlag || (!!q.safetyKey && score >= 2);
    const nextCurrent = current < QUESTIONS.length - 1 ? current + 1 : current;
    setAnswers(newAnswers);
    if (!safetyFlag && newSafety) setSafetyFlag(true);
    _saveProgress(nextCurrent, newAnswers, newSafety);
    if (current < QUESTIONS.length - 1) {
      setTimeout(() => setCurrent((c: number) => c + 1), 260);
    }
  }

  function finish() {
    _clearSurvey();
    const totalScore = QUESTIONS.reduce((s, q) => s + (answers[q.id] ?? 0), 0);
    const pct = totalScore / TOTAL_MAX;
    if (pct >= 0.5) {
      setStep('precision');
    } else {
      setStep('result');
    }
  }

  function finishPrecision() {
    setStep('result');
  }

  function goNext() {
    if (current < QUESTIONS.length - 1) {
      const next = current + 1;
      setCurrent(next);
      _saveProgress(next, answers, safetyFlag);
    } else finish();
  }

  function goPrev() {
    if (current > 0) {
      const prev = current - 1;
      setCurrent(prev);
      _saveProgress(prev, answers, safetyFlag);
    }
  }

  /* ── 차원 점수 기반 분류 이유 텍스트 생성 ── */
  // 연구 카테고리명 → 사용자 언어 변환
  const CAT_LABEL: Record<string, string> = {
    '관계망': '주변 사람과의 연결',
    '정신건강': '마음 상태',
    '노동·경제': '일과 경제 상황',
    '자기관리': '일상 관리',
    '활동': '외부 활동',
  };

  function buildDimensionReason(
    stage: string,
    catScores: [string, { score: number; max: number }][],
    _pct: number,
  ): string {
    const sm: Record<string, number> = {};
    for (const [cat, { score, max }] of catScores) {
      sm[cat] = max > 0 ? Math.round((score / max) * 100) : 0;
    }
    const sorted = Object.entries(sm).sort(([, a], [, b]) => b - a);
    const toLabel = (k: string) => CAT_LABEL[k] ?? k;

    switch (stage) {
      case '4': {
        const top2 = sorted.slice(0, 2).map(([k]) => toLabel(k));
        return `${top2.join(', ')} 부분에서 많이 힘드신 것 같아요.`;
      }
      case '3': {
        const elevated = sorted.filter(([, v]) => v >= 45).slice(0, 2);
        const display = (elevated.length > 0 ? elevated : sorted.slice(0, 2)).map(([k]) => toLabel(k));
        return `${display.join(', ')} 부분에서 어려움이 있어요.`;
      }
      case '2': {
        const elevated = sorted.filter(([, v]) => v >= 35).slice(0, 2);
        const display = (elevated.length > 0 ? elevated : sorted.slice(0, 2)).map(([k]) => toLabel(k));
        return `${display.join(', ')} 부분에서 일부 어려움이 있어요.`;
      }
      default: {
        const topCat = sorted[0];
        if (topCat && topCat[1] >= 20) {
          return `${toLabel(topCat[0])} 부분에서 살짝 부담이 있지만, 전반적으로 안정적인 상황이에요.`;
        }
        return `전반적으로 안정적인 상황이에요.`;
      }
    }
  }

  /* ── Result ── */
  if (step === 'result') {
    const totalScore = QUESTIONS.reduce((s, q) => s + (answers[q.id] ?? 0), 0);
    const stage = scoreToStage(totalScore, precisionAnswers);
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
    const dimensionReason = buildDimensionReason(stage, categoryScores, pct);

    return (
      <div className="survey-wrap">
        <p aria-live="polite" aria-atomic="true" className="sr-only">
          {evidenceLoading ? '연구 근거를 검색하고 있습니다.' : '진단 결과가 준비되었습니다.'}
        </p>
        <div className="page-header">
          <h1 className="page-title">{STAGE_INTRO[stage]?.headline ?? '자격증 추천을 준비했어요'}</h1>
          <p className="page-desc">{STAGE_INTRO[stage]?.sub ?? '지금 상황에서 도전할 수 있는 자격증들을 찾았습니다.'}</p>
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
            <div>
              <p className="result-stage-name">{dimensionReason}</p>
            </div>
          </div>

          <div className="result-complete-badge">
            <span aria-hidden="true">✓</span> 12/12 문항 완료 · 참고용 결과입니다
          </div>

          {/* ── 상세 보기 토글 ── */}
          <button
            className="result-detail-toggle"
            type="button"
            onClick={() => setShowDetail(v => !v)}
            aria-expanded={showDetail}
          >
            <span aria-hidden="true">{showDetail ? '▲' : '▼'}</span>{' '}
            {showDetail ? '상세 분석 접기' : '상세 분석 보기'}
          </button>

          {showDetail && (<>
          {/* ── 방사형 차트 ── */}
          <div className="result-radar-wrap">
            <svg viewBox="0 0 260 260" className="result-radar-svg" aria-hidden="true">
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
                      style={{ transform: `scaleX(${catPct / 100})`, background: CATEGORY_COLORS[cat] ?? '#6366f1' }}
                    />
                  </div>
                  <span className="result-cat-pct">{catPct}%</span>
                </div>
              );
            })}
          </div>
          </>)}
        </div>

        {/* ── Primary CTA ── */}
        <div className="result-actions">
          <button className="btn-ghost" onClick={() => {
              _clearSurvey();
              setStep('survey'); setCurrent(0); setAnswers({}); setSafetyFlag(false); setPrecisionAnswers({});
            }}>
            <ArrowLeft size={15} /> 다시 진단
          </button>
          <button
            className="btn-primary"
            onClick={() => {
              clearPipeline();
              savePipeline({ stage });
              _clearSurvey();
              navigate(`/interests?stage=${stage}`);
            }}>
            내 상황에 맞는 자격증 보기 <ArrowRight size={15} />
          </button>
        </div>

        {/* ── 내 상황 분석 카드 (접힘) ── */}
        <div style={{ display:'flex', justifyContent:'center', marginTop:'.5rem' }}>
          <button
            className="policy-card-toggle"
            type="button"
            onClick={() => setShowPolicyCard(v => !v)}
            aria-expanded={showPolicyCard}
          >
            <span aria-hidden="true">{showPolicyCard ? '▲' : '▼'}</span>{' '}
            {showPolicyCard ? '내 상황 분석 접기' : '내 상황 분석 · 지원 제도 보기'}
          </button>
        </div>

        {showPolicyCard && (() => {
          const policy = STAGE_POLICY[stage];
          if (!policy) return null;
          return (
            <div className="policy-card">
              {/* 출처 헤더 */}
              <div className="policy-source">
                <span className="policy-source-badge">연구 근거</span>
                <span className="policy-source-text">
                  보건복지부 고립은둔 청년 지원사업 모형 개발 연구 (김성아, 2022) · 정책보고서 2022-35 · 요약 표 12
                </span>
              </div>

              {/* 분류 결과 */}
              <div className="policy-classify">
                <p className="policy-classify-label">지금 내 상황</p>
                <p className="policy-classify-type">아래 설명이 지금 상황과 가깝습니다.</p>
                <p className="policy-classify-char">{policy.characteristic}</p>
                <div className="policy-strategy-row">
                  <span className="policy-strategy-label">지원 전략</span>
                  <span className="policy-strategy-value">{policy.strategy}</span>
                </div>
              </div>

              {/* HyDE 분류 근거 */}
              {(evidenceLoading || evidenceSynthesis || evidence.length > 0) && (
                <div className="policy-evidence-section">
                  <p className="policy-evidence-title">📄 분류 근거</p>
                  {evidenceLoading ? (
                    <p className="policy-evidence-loading">연구 문서 분석 중…</p>
                  ) : evidenceSynthesis ? (
                    <div className="hyde-synthesis-wrap">
                      <div className="hyde-synthesis-card">
                        <span className="hyde-synthesis-badge">AI 분석 근거</span>
                        <p className="hyde-synthesis-text">{evidenceSynthesis.replace(/\[문서\s*\d+\]/g, '').trim()}</p>
                      </div>
                      {evidence.length > 0 && (
                        <div className="hyde-sources">
                          <button
                            className="hyde-sources-toggle"
                            onClick={() => setShowEvidenceSources(v => !v)}
                            type="button"
                          >
                            {showEvidenceSources ? '▲ 원문 출처 접기' : '▼ 원문 출처 보기'}
                          </button>
                          {showEvidenceSources && evidence.map((ev, i) => (
                            <div key={i} className="policy-evidence-item">
                              <p className="policy-evidence-snippet">"{ev.snippet.slice(0, 180).trim()}{ev.snippet.length > 180 ? '…' : ''}"</p>
                              <p className="policy-evidence-source">
                                [{ev.doc_id.replace(/_/g, ' ')}
                                {ev.section_path?.length ? ` · ${ev.section_path[0]}` : ''}]
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    evidence.map((ev, i) => (
                      <div key={i} className="policy-evidence-item">
                        <p className="policy-evidence-snippet">"{ev.snippet.slice(0, 180).trim()}{ev.snippet.length > 180 ? '…' : ''}"</p>
                        <p className="policy-evidence-source">
                          [{ev.doc_id.replace(/_/g, ' ')}
                          {ev.section_path?.length ? ` · ${ev.section_path[0]}` : ''}]
                        </p>
                      </div>
                    ))
                  )}
                </div>
              )}

              <div className="policy-divider" />

              {/* 추천 지원 프로그램 — 접힘 */}
              <button
                className="policy-programs-toggle"
                type="button"
                onClick={() => setShowPrograms(v => !v)}
                aria-expanded={showPrograms}
              >
                <span>추천 지원 제도</span>
                <span className="policy-programs-toggle-arrow" aria-hidden="true">{showPrograms ? '▲' : '▼'}</span>
              </button>

              {showPrograms && (
              <div className="policy-programs">
                {policy.programs.map((prog, pi) => (
                  <div key={pi} className="policy-prog-group">
                    <div className="policy-prog-category">
                      <span className="policy-prog-cat-name">{prog.category}</span>
                      <span className="policy-prog-cat-desc">{prog.categoryDesc}</span>
                    </div>
                    <ul className="policy-prog-items">
                      {prog.items.map((item, ii) => (
                        <li key={ii} className="policy-prog-item">
                          {item.url ? (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="policy-prog-link"
                            >
                              {item.text}
                              <span className="policy-prog-link-arrow">→</span>
                            </a>
                          ) : (
                            item.text
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
              )}

              {/* 위기 단계 추가 안내 */}
              {(stage === '3' || stage === '4') && (
                <div className="policy-crisis-note">
                  <p className="policy-crisis-text">
                    지금 혼자 감당하기 어려우신 상황이라면, 아래 연락처로 연결하실 수 있습니다.
                  </p>
                  <div className="policy-crisis-links">
                    <a href="https://www.suicide.or.kr/m/index.php" target="_blank" rel="noopener noreferrer" className="policy-crisis-link">
                      1393 자살예방상담전화
                    </a>
                  </div>
                </div>
              )}
            </div>
          );
        })()}


        <style>{`
          .result-card { padding:1.75rem; display:flex; flex-direction:column; gap:1.25rem; }
          .result-stage-row { display:flex; align-items:center; gap:1rem; }
          .result-stage-name { font-size:1.05rem; font-weight:600; color:var(--text); line-height:1.6; }
          .result-complete-badge {
            display: inline-flex; align-items: center; gap: .4rem;
            font-size: .78rem; font-weight: 600; color: var(--success);
            background: color-mix(in srgb, var(--success) 10%, transparent);
            border: 1px solid color-mix(in srgb, var(--success) 25%, transparent);
            border-radius: var(--radius-full);
            padding: .25rem .75rem; width: fit-content;
          }
          .result-detail-toggle {
            background: none; border: 1px solid var(--border); border-radius: var(--radius-sm);
            cursor: pointer; font-size: .78rem; font-weight: 600; color: var(--text-light);
            padding: .4rem .875rem; width: 100%; text-align: left;
            transition: color .15s, border-color .15s;
          }
          .result-detail-toggle:hover { color: var(--primary); border-color: var(--primary); }
          .policy-programs-toggle {
            display: flex; justify-content: space-between; align-items: center;
            width: 100%; background: none; border: none; cursor: pointer;
            padding: .875rem 1.125rem;
            font-size: .82rem; font-weight: 700; color: var(--text-muted);
            transition: color .15s; text-align: left;
          }
          .policy-programs-toggle:hover { color: var(--primary); }
          .policy-programs-toggle-arrow { font-size: .65rem; color: var(--text-light); }
          .result-cats { display:flex; flex-direction:column; gap:.625rem; }
          .result-cat-row { display:flex; align-items:center; gap:.75rem; }
          .result-cat-label { font-size:.78rem; font-weight:600; color:var(--text-muted); width:68px; flex-shrink:0; }
          .result-cat-bar-bg { flex:1; height:6px; background:var(--border); border-radius:99px; overflow:hidden; }
          .result-cat-bar-fill { height:100%; width:100%; border-radius:99px; transform-origin:left; transition:transform 0.6s ease; }
          .result-cat-pct { font-size:.75rem; color:var(--text-light); width:32px; text-align:right; flex-shrink:0; }
          .result-radar-wrap {
            display:flex; justify-content:center; padding:.25rem 0;
          }
          .result-radar-svg {
            width:100%; max-width:240px; height:auto; overflow:visible;
          }
          .result-data-note { padding:1rem 1.25rem; background:var(--primary-light); border:1px solid var(--border); border-radius:var(--radius-sm); }
          .rdn-title { font-size:.8rem; font-weight:700; color:var(--primary); margin-bottom:.4rem; }
          .rdn-body { font-size:.82rem; color:var(--text-muted); line-height:1.7; }
          .result-actions { display:flex; gap:.75rem; flex-wrap:wrap; }

          .policy-card-toggle {
            background: none; border: 1px solid var(--border); border-radius: var(--radius-sm);
            cursor: pointer; font-size: .78rem; font-weight: 600; color: var(--text-light);
            padding: .4rem 1rem; transition: color .15s, border-color .15s;
          }
          .policy-card-toggle:hover { color: var(--primary); border-color: var(--primary); }

          /* ── 표12 근거 지원 프로그램 카드 ── */
          .policy-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow-sm);
            display: flex; flex-direction: column; gap: 0;
            overflow: hidden;
          }

          .policy-source {
            display: flex; align-items: center; gap: .625rem; flex-wrap: wrap;
            padding: .625rem 1.125rem;
            background: var(--surface-2);
            border-bottom: 1px solid var(--border);
          }
          .policy-source-badge {
            font-size: .68rem; font-weight: 800; letter-spacing: .05em;
            color: var(--primary); background: var(--primary-light);
            padding: .15rem .55rem; border-radius: 99px;
            white-space: nowrap; flex-shrink: 0;
          }
          .policy-source-text {
            font-size: .72rem; color: var(--text-muted); line-height: 1.5;
          }

          .policy-classify {
            padding: 1rem 1.125rem;
            display: flex; flex-direction: column; gap: .5rem;
          }
          .policy-classify-label {
            font-size: .68rem; font-weight: 800; letter-spacing: .07em;
            color: var(--text-light); text-transform: uppercase; margin: 0;
          }
          .policy-classify-type {
            font-size: .97rem; font-weight: 700; color: var(--text);
            line-height: 1.55; margin: 0;
          }
          .policy-classify-char {
            font-size: .82rem; color: var(--text-muted); line-height: 1.65; margin: 0;
          }
          .policy-strategy-row {
            display: inline-flex; align-items: center; gap: .5rem; margin-top: .15rem;
          }
          .policy-strategy-label {
            font-size: .72rem; font-weight: 700; color: var(--text-muted);
            background: var(--surface-2); padding: .15rem .55rem;
            border-radius: 4px; border: 1px solid var(--border);
          }
          .policy-strategy-value {
            font-size: .82rem; font-weight: 700; color: var(--text);
          }

          .policy-divider { height: 1px; background: var(--border); }

          .policy-programs {
            padding: 1rem 1.125rem;
            display: flex; flex-direction: column; gap: .875rem;
          }
          .policy-programs-title {
            font-size: .72rem; font-weight: 800; letter-spacing: .07em;
            color: var(--text-muted); text-transform: uppercase; margin: 0 0 .125rem;
          }

          .policy-prog-group {
            display: flex; flex-direction: column; gap: .375rem;
          }
          .policy-prog-category {
            display: flex; align-items: center; gap: .5rem;
          }
          .policy-prog-cat-name {
            font-size: .8rem; font-weight: 800; color: var(--text);
          }
          .policy-prog-cat-desc {
            font-size: .68rem; color: var(--text-light);
            background: var(--surface-2); padding: .1rem .45rem;
            border-radius: 4px; border: 1px solid var(--border);
          }

          .policy-prog-items {
            list-style: none; padding: 0; margin: 0;
            display: flex; flex-direction: column; gap: .3rem;
          }
          .policy-prog-item {
            font-size: .83rem; color: var(--text-muted); line-height: 1.6;
            padding-left: 1rem; position: relative;
          }
          .policy-prog-item::before {
            content: ""; position: absolute; left: 0; top: .58em;
            width: 4px; height: 4px; border-radius: 50%;
            background: var(--border-strong);
          }
          .policy-prog-link {
            color: var(--primary); text-decoration: none; font-weight: 600;
            display: inline-flex; align-items: center; gap: .2rem;
          }
          .policy-prog-link:hover { text-decoration: underline; }
          .policy-prog-link-arrow {
            font-size: .75rem; opacity: .7;
          }

          .policy-dim-reason {
            color: var(--primary); font-weight: 700;
          }

          /* ── RAG 연구 근거 ── */
          .policy-evidence-section {
            padding: .875rem 1.125rem;
            border-top: 1px solid var(--border);
            background: var(--surface-2);
            display: flex; flex-direction: column; gap: .5rem;
          }
          .policy-evidence-title {
            font-size: .72rem; font-weight: 800; letter-spacing: .05em;
            color: var(--text-muted); margin: 0;
          }
          .policy-evidence-loading {
            font-size: .8rem; color: var(--text-light); margin: 0;
          }

          .hyde-synthesis-wrap { display: flex; flex-direction: column; gap: .5rem; }
          .hyde-synthesis-card {
            padding: .75rem .875rem;
            background: var(--primary-light); border: 1px solid rgba(99,102,241,.2);
            border-radius: var(--radius-sm);
            display: flex; flex-direction: column; gap: .375rem;
          }
          .hyde-synthesis-badge {
            display: inline-block; padding: .1rem .45rem;
            background: var(--primary); color: #fff;
            border-radius: 3px; font-size: .62rem; font-weight: 700;
            width: fit-content;
          }
          .hyde-synthesis-text {
            font-size: .83rem; color: var(--text); line-height: 1.7; margin: 0;
          }
          .hyde-sources { display: flex; flex-direction: column; gap: .3rem; }
          .hyde-sources-toggle {
            background: none; border: none; cursor: pointer;
            font-size: .72rem; font-weight: 600; color: var(--text-light);
            padding: 0; text-align: left;
            transition: color .15s;
          }
          .hyde-sources-toggle:hover { color: var(--primary); }

          .policy-evidence-item {
            display: flex; flex-direction: column; gap: .2rem;
            padding: .5rem .75rem;
            background: var(--surface); border-radius: var(--radius-sm);
            border: 1px solid var(--border);
          }
          .policy-evidence-snippet {
            font-size: .8rem; color: var(--text); line-height: 1.65; margin: 0;
            font-style: italic;
          }
          .policy-evidence-source {
            font-size: .68rem; color: var(--text-light); margin: 0;
          }

          .policy-crisis-note {
            padding: .75rem 1.125rem;
            background: var(--danger-light);
            border-top: 1px solid rgba(244,63,94,.15);
            display: flex; flex-direction: column; gap: .5rem;
          }
          .policy-crisis-text {
            font-size: .8rem; color: var(--danger-dark); line-height: 1.55; margin: 0;
          }
          .policy-crisis-links {
            display: flex; gap: .625rem; flex-wrap: wrap;
          }
          .policy-crisis-link {
            font-size: .78rem; font-weight: 600; color: var(--danger-text);
            text-decoration: none;
            padding: .25rem .7rem;
            border: 1px solid rgba(244,63,94,.3);
            border-radius: var(--radius-sm);
            background: rgba(255,255,255,.6);
            transition: background .15s;
          }
          .policy-crisis-link:hover { background: rgba(255,255,255,.9); }

          /* ── Mobile ── */
          @media (max-width:640px) {
            .result-card { padding:1.25rem; }
            .result-stage-row { flex-wrap:wrap; gap:.625rem; }
            .result-badge { font-size:.8rem; }
            .result-stage-name { font-size:1.1rem; }
            .result-cat-label { width:56px; font-size:.72rem; }
            .result-actions { flex-direction:column; }
            .result-actions .btn-primary,
            .result-actions .btn-ghost { width:100%; justify-content:center; }
          }
        `}</style>
      </div>
    );
  }

  /* ── Precision (2차 3문항) ── */
  if (step === 'precision') {
    const allAnswered = PRECISION_QUESTIONS.every(pq => precisionAnswers[pq.id] !== undefined);
    return (
      <div className="survey-wrap">
        <div className="page-header">
          <h1 className="page-title">거의 다 됐어요!</h1>
          <p className="page-desc">비슷한 상황이 여럿 있어서, 딱 맞는 추천을 드리려면 3가지만 더 확인할게요. 1분도 안 걸립니다.</p>
        </div>

        <div className="precision-note">
          <span className="precision-note-badge">연구 근거</span>
          <span className="precision-note-text">서울시 고립은둔청년 실태조사(2023, N=5,513) 실측값 기반</span>
        </div>

        {PRECISION_QUESTIONS.map((pq, idx) => (
          <div key={pq.id} className="card precision-q-card">
            <p className="precision-q-num">추가 {idx + 1}/3</p>
            <p className="survey-q-text">{pq.text}</p>
            <div className="survey-options" role="radiogroup" aria-label={pq.text}>
              {pq.options.map(opt => {
                const isSel = precisionAnswers[pq.id] === opt.value;
                return (
                  <button
                    key={opt.value}
                    role="radio"
                    aria-checked={isSel}
                    tabIndex={isSel ? 0 : -1}
                    className={`survey-opt ${isSel ? 'selected' : ''}`}
                    onClick={() => setPrecisionAnswers(prev => ({ ...prev, [pq.id]: opt.value }))}
                    type="button"
                  >
                    <span className="survey-opt-radio" aria-hidden="true">{isSel ? '●' : '○'}</span>
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        <div className="survey-nav">
          <button className="btn-ghost" onClick={() => {
            setPrecisionAnswers({});
            setStep('survey');
            setCurrent(QUESTIONS.length - 1);
            _saveProgress(QUESTIONS.length - 1, answers, safetyFlag);
          }}>
            <ArrowLeft size={15} /> 이전 문항으로
          </button>
          <button className="btn-primary" disabled={!allAnswered} onClick={finishPrecision}>
            결과 보기 <ArrowRight size={15} />
          </button>
        </div>

        <style>{`
          .precision-note {
            display: flex; align-items: center; gap: .5rem; flex-wrap: wrap;
            padding: .5rem .875rem;
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            font-size: .73rem; color: var(--text-muted);
          }
          .precision-note-badge {
            font-size: .65rem; font-weight: 800; letter-spacing: .04em;
            text-transform: uppercase; color: var(--primary);
            background: var(--primary-light); padding: .15rem .5rem;
            border-radius: var(--radius-full);
          }
          .precision-q-card { padding: 1.25rem; display: flex; flex-direction: column; gap: .875rem; }
          .precision-q-num { font-size: .75rem; font-weight: 700; color: var(--text-muted); margin: 0; }
        `}</style>
      </div>
    );
  }

  /* ── Survey ── */
  return (
    <div className="survey-wrap">
      <div className="page-header">
        <h1 className="page-title">나에게 맞는 자격증 찾기</h1>
        <p className="page-desc">12개 질문에 솔직하게 답해주세요. 지금 내 상황에 맞는 자격증 로드맵을 추천해드립니다. 약 3~5분 소요됩니다.</p>
      </div>

      {/* Restore notice */}
      {wasRestored && (
        <div className="survey-restore-bar">
          <span>💾 이전 진행 상태가 복원되었습니다 ({current + 1}번 문항부터)</span>
          <button type="button" className="survey-restore-reset-btn" onClick={() => {
            _clearSurvey();
            setCurrent(0); setAnswers({}); setSafetyFlag(false); setWasRestored(false);
          }}>처음부터</button>
        </div>
      )}

      {/* 안전 인터스티셜 — B12_9(index 10) 직전 1회 */}
      {current === 10 && !safetyGatePassed && (
        <div className="safety-gate-card">
          <div className="safety-gate-icon">🤝</div>
          <p className="safety-gate-title">마지막 두 문항 전에 잠깐요</p>
          <p className="safety-gate-desc">
            다음 문항에서 심리적으로 힘들었던 경험을 여쭤볼 수 있어요.
            편하지 않으시면 <strong>건너뛰어도</strong> 자격증 추천에 전혀 지장이 없습니다.
          </p>
          <div className="safety-gate-actions">
            <button className="btn-primary" onClick={() => setSafetyGatePassed(true)}>
              괜찮아요, 계속할게요
            </button>
            <button className="btn-ghost" onClick={() => {
              // B12_9 건너뜀 — 점수 0 처리 후 다음 문항으로
              const newAnswers = { ...answers, B12_9: 0 };
              setAnswers(newAnswers);
              setSafetyGatePassed(true);
              _saveProgress(11, newAnswers, safetyFlag);
              setCurrent(11);
            }}>
              이 문항은 건너뛸게요
            </button>
          </div>
        </div>
      )}

      {/* Progress */}
      <div className="survey-progress-wrap" style={current === 10 && !safetyGatePassed ? { display: 'none' } : {}}>
        <div className="survey-progress-info">
          <span className="survey-q-num">{current + 1} / {QUESTIONS.length}</span>
          <span className="survey-cat-badge" style={{ background: (CATEGORY_COLORS[q.category] ?? '#6366f1') + '18', color: CATEGORY_COLORS[q.category] ?? '#6366f1' }}>
            {q.category}
          </span>
        </div>
        <div className="survey-prog-bar-bg">
          <div className="survey-prog-bar-fill" style={{ transform: `scaleX(${progress / 100})` }} />
        </div>
      </div>

      {/* Question card — 인터스티셜 중엔 숨김 */}
      {(current !== 10 || safetyGatePassed) && (
        <div className="card survey-card" key={current}>
          {q.safetyKey && (
            <div className="safety-notice">
              <AlertTriangle size={14} />
              <span>이 질문은 정서적 위기와 관련된 항목입니다. 편하게 솔직하게 답해주세요.</span>
            </div>
          )}

          <p className="survey-q-text">{q.text}</p>

          <div
            className="survey-options"
            role="radiogroup"
            aria-label={q.text}
            ref={radioGroupRef}
            onKeyDown={(e) => {
              const opts = q.options;
              const curIdx = opts.findIndex(o => o.score === answers[q.id]);
              const base = curIdx >= 0 ? curIdx : 0;
              let nextIdx = -1;
              if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                e.preventDefault();
                nextIdx = (base + 1) % opts.length;
              } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
                e.preventDefault();
                nextIdx = (base - 1 + opts.length) % opts.length;
              }
              if (nextIdx >= 0) {
                select(opts[nextIdx].score);
                requestAnimationFrame(() => {
                  const btns = radioGroupRef.current?.querySelectorAll<HTMLButtonElement>('[role="radio"]');
                  btns?.[nextIdx]?.focus();
                });
              }
            }}
          >
            {q.options.map((opt, idx) => {
              const isSel = answers[q.id] === opt.score;
              const isFirstUnselected = answers[q.id] === undefined && idx === 0;
              return (
                <button
                  key={opt.score}
                  role="radio"
                  aria-checked={isSel}
                  tabIndex={isSel || isFirstUnselected ? 0 : -1}
                  className={`survey-opt ${isSel ? 'selected' : ''}`}
                  onClick={() => select(opt.score)}
                  type="button"
                >
                  <span className="survey-opt-radio" aria-hidden="true">{isSel ? '●' : '○'}</span>
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Navigation — 인터스티셜 중엔 숨김 */}
      {(current !== 10 || safetyGatePassed) && (
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
      )}

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
          width:100%; transform-origin:left; transition:transform 0.35s ease;
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
          color:var(--warning-text); border:1px solid rgba(245,158,11,.25);
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
          width:100%; min-height:44px;
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
        .safety-title { font-weight:700; font-size:.9rem; color:var(--danger-text); }
        .safety-sub { font-size:.82rem; color:var(--danger-dark); line-height:1.55; }
        .safety-cta {
          display:inline-block; width:fit-content;
          margin-top:.35rem; padding:.45rem .875rem;
          background:var(--danger); color:#fff;
          border-radius:var(--radius-sm); font-size:.82rem; font-weight:700;
          text-decoration:none;
        }
        .safety-gate-card {
          display:flex; flex-direction:column; align-items:center; gap:1rem;
          background:#f0fdf4; border:1px solid #86efac;
          border-radius:var(--radius); padding:2rem 1.5rem;
          text-align:center;
        }
        .safety-gate-icon { font-size:2rem; }
        .safety-gate-title { font-size:1.1rem; font-weight:700; color:var(--text); }
        .safety-gate-desc { font-size:.9rem; color:var(--text-muted); line-height:1.65; max-width:380px; }
        .safety-gate-actions { display:flex; flex-direction:column; gap:.625rem; width:100%; max-width:300px; }
        .safety-gate-actions .btn-primary { width:100%; justify-content:center; }
        .safety-gate-actions .btn-ghost { width:100%; justify-content:center; font-size:.85rem; color:var(--text-muted); }
        .survey-restore-bar {
          display:flex; align-items:center; justify-content:space-between; gap:.75rem;
          padding:.55rem .875rem; background:#fffbeb;
          border:1px solid #fde68a; border-radius:var(--radius-sm);
          font-size:.8rem; color:var(--warning-text);
        }
        .survey-restore-reset-btn {
          font-size:.75rem; font-weight:600; color:#7c3aed;
          background:#ede9fe; border:none; border-radius:20px;
          padding:.2rem .65rem; cursor:pointer; white-space:nowrap;
          display:inline-flex; align-items:center;
        }
        .survey-restore-reset-btn:hover { background:#ddd6fe; }
        @media(pointer:coarse){.survey-restore-reset-btn{min-height:44px;padding:.5rem .875rem}}

        /* ── Mobile ── */
        @media (max-width:640px) {
          .survey-wrap { padding:0 .25rem; }
          .survey-card { padding:1.25rem; }
          .survey-opt { font-size:.875rem; padding:.75rem .875rem; }
          .survey-nav { flex-direction:column-reverse; }
          .survey-nav .btn-primary,
          .survey-nav .btn-ghost { width:100%; justify-content:center; }
        }
      `}</style>
    </div>
  );
};

export default RiskAssessment;
