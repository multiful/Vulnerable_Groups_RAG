import React from 'react';
import { ArrowRight, ShieldAlert, Award, Map as MapIcon, CheckCircle2, FileText, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';

const STAGES = [
  { id:'1', label:'1단계', sub:'취업 안정권', color:'#10b981', width:'100%' },
  { id:'2', label:'2단계', sub:'준비 활성',   color:'#0ea5e9', width:'80%'  },
  { id:'3', label:'3단계', sub:'준비 정체',   color:'#6366f1', width:'60%'  },
  { id:'4', label:'4단계', sub:'관계망 약화', color:'#f59e0b', width:'40%'  },
  { id:'5', label:'5단계', sub:'고위험군',    color:'#f43f5e', width:'20%'  },
];

const PROMISES = [
  {
    num:'01', keyword:'PERSONALIZED', title:'내 단계에 맞는 추천',
    desc:'위험군 1~5단계를 1차 키로 사용합니다. 고위험군에는 낮은 등급 자격증을 우선 추천하고, 안정권에는 기사·기술사도 후보에 포함됩니다.',
    icon:<ShieldAlert size={20}/>, color:'promise-primary',
  },
  {
    num:'02', keyword:'STRUCTURED', title:'구조적으로 연결된 추천',
    desc:'자격증·직무·도메인·로드맵 단계가 canonical 데이터로 묶여 있습니다. 한 번의 추천이 4가지 정보를 동시에 설명합니다.',
    icon:<Award size={20}/>, color:'promise-secondary',
  },
  {
    num:'03', keyword:'EVIDENCE-BACKED', title:'근거가 있는 추천',
    desc:'공식 PDF/HTML 문서에서 RAG로 근거 스니펫을 가져옵니다. 근거가 0건이면 환각 대신 "근거 없음" 안내를 표시합니다.',
    icon:<FileText size={20}/>, color:'promise-accent',
  },
];

const FLOW = [
  { num:'1', label:'위험군 진단', sub:'1~5단계 선택',    icon:<ShieldAlert size={17}/>, path:'/risk-assessment', color:'#6366f1' },
  { num:'2', label:'자격증 추천', sub:'후보 목록 확인',   icon:<Award size={17}/>,       path:'/recommendation',  color:'#0ea5e9' },
  { num:'3', label:'로드맵 탐색', sub:'단계별 경로 확인', icon:<MapIcon size={17}/>,     path:'/roadmap',         color:'#10b981' },
];

const STATS = [
  { value:'8.82%', label:'서울시 청년 고립·은둔 비율',    src:'서울시 실태조사 2023' },
  { value:'50.2%', label:'고립군 "지난주 일 안 함"',      src:'비고립군 9.8% (h=+0.937)' },
  { value:'62.6%', label:'고립군 "대면교류 전혀 없음"',   src:'비고립군 8.0% (h=+1.250)' },
];

const Home: React.FC = () => (
  <div className="home-wrap">

    {/* Hero */}
    <section className="hero">
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="hero-inner">
        <div className="hero-text">
          <div className="hero-badge"><Zap size={12}/><span>청년 위험군 맞춤 자격증·로드맵 추천</span></div>
          <h1 className="hero-title">내 상황에 맞는<br/><span className="gradient-text">자격증과 성장 경로</span></h1>
          <p className="hero-sub">위험군 단계·관심 직무·도메인을 1차 키로 삼아 자격증을 추천하고, 단계별 행동 로드맵을 제안합니다.</p>
          <div className="hero-actions">
            <Link to="/risk-assessment" className="btn-primary hero-main-btn">지금 진단 시작하기 <ArrowRight size={17}/></Link>
            <Link to="/recommendation"  className="btn-ghost">자격증 둘러보기</Link>
          </div>
        </div>
        <div className="hero-visual">
          <div className="stage-card">
            <p className="stage-card-title">위험군 단계별 진입</p>
            <div className="stage-list">
              {STAGES.map(s => (
                <Link key={s.id} to={`/recommendation?stage=${s.id}`} className="stage-row">
                  <div className="sr-label">
                    <span className="sr-num">{s.label}</span>
                    <span className="sr-sub">{s.sub}</span>
                  </div>
                  <div className="sr-track">
                    <div className="sr-fill" style={{width:s.width, background:s.color}}/>
                  </div>
                  <ArrowRight size={11} style={{color:s.color, opacity:.5, flexShrink:0}}/>
                </Link>
              ))}
            </div>
            <p className="stage-card-hint">단계 클릭 시 해당 자격증 목록으로 바로 이동합니다</p>
          </div>
        </div>
      </div>
    </section>

    {/* Stats */}
    <section>
      <p className="eyebrow">데이터 배경</p>
      <div className="stats-grid">
        {STATS.map(s => (
          <div key={s.value} className="stat-card card">
            <p className="stat-val gradient-text">{s.value}</p>
            <p className="stat-label">{s.label}</p>
            <p className="stat-src">{s.src}</p>
          </div>
        ))}
      </div>
      <p className="stats-note">서울시 고립·은둔 청년 실태조사(2023) · 고립군 486명 vs 미해당군 5,027명</p>
    </section>

    {/* Flow */}
    <section>
      <p className="eyebrow">이용 흐름</p>
      <h2 className="sec-title">3단계로 완성되는 추천</h2>
      <div className="flow-row">
        {FLOW.map((s, i) => (
          <React.Fragment key={s.num}>
            <Link to={s.path} className="flow-card card">
              <div className="flow-icon" style={{background:s.color+'18', color:s.color}}>{s.icon}</div>
              <div className="flow-num-dot" style={{background:s.color}}>{s.num}</div>
              <div className="flow-info">
                <span className="flow-label">{s.label}</span>
                <span className="flow-sub">{s.sub}</span>
              </div>
              <ArrowRight size={13} style={{color:s.color, opacity:.6, flexShrink:0}}/>
            </Link>
            {i < FLOW.length-1 && <div className="flow-sep"><div className="flow-line"/></div>}
          </React.Fragment>
        ))}
      </div>
    </section>

    {/* Promises */}
    <section>
      <p className="eyebrow">청로드의 3가지 약속</p>
      <h2 className="sec-title">추천을 "행동"으로 바꿉니다</h2>
      <div className="promise-grid">
        {PROMISES.map(p => (
          <div key={p.num} className={`promise-card card ${p.color}`}>
            <div className="promise-bg-num">{p.num}</div>
            <div className="promise-icon">{p.icon}</div>
            <p className="promise-kw">{p.keyword}</p>
            <h3 className="promise-title">{p.title}</h3>
            <p className="promise-desc">{p.desc}</p>
          </div>
        ))}
      </div>
    </section>

    {/* Persona */}
    <section>
      <p className="eyebrow">이런 분께 맞습니다</p>
      <h2 className="sec-title">두 가지 대표 상황</h2>
      <div className="persona-grid">
        <div className="persona-card card">
          <span className="persona-badge badge-red">5단계 · 고위험군</span>
          <p className="persona-name">"방을 거의 나오지 않는 청년"</p>
          <p className="persona-desc">기능사·GTQ 등 집에서 단기 성취 가능한 자격증부터 시작하는 <strong>기능사 → 산업기사 → 기사</strong> 단계형 로드맵을 제안받습니다.</p>
          <Link to="/recommendation?stage=5" className="persona-link">5단계 추천 보기 <ArrowRight size={13}/></Link>
        </div>
        <div className="persona-card card">
          <span className="persona-badge badge-indigo">3단계 · 준비 정체</span>
          <p className="persona-name">"방향을 못 잡은 진로 탐색 청년"</p>
          <p className="persona-desc">컴활 1급·SQLD·정보처리산업기사 등 균형 있는 후보와 함께 <strong>분석 트랙 / 기획 트랙</strong> 두 경로를 비교해 볼 수 있습니다.</p>
          <Link to="/recommendation?stage=3" className="persona-link">3단계 추천 보기 <ArrowRight size={13}/></Link>
        </div>
      </div>
    </section>

    {/* CTA */}
    <section className="cta-section">
      <div className="cta-inner">
        <CheckCircle2 size={32} style={{color:'var(--success)'}}/>
        <h2 className="cta-title">청년의 다음 한 걸음을 데이터로 설명합니다</h2>
        <p className="cta-sub">인기순 추천이 아닌, 내 위험군·직무·도메인 기반의 정확한 추천을 받아보세요.</p>
        <Link to="/risk-assessment" className="btn-primary cta-btn">위험군 진단 시작하기 <ArrowRight size={17}/></Link>
      </div>
    </section>

    <style>{`
      .home-wrap{display:flex;flex-direction:column;gap:3.5rem;padding-bottom:1rem}
      /* Hero */
      .hero{position:relative;overflow:hidden;padding:1.5rem 0 .5rem}
      .orb{position:absolute;border-radius:50%;filter:blur(80px);pointer-events:none;z-index:0;animation:orb-drift 10s ease-in-out infinite}
      .orb-1{width:500px;height:500px;background:radial-gradient(circle,rgba(99,102,241,.10),transparent 70%);top:-180px;left:-130px}
      .orb-2{width:380px;height:380px;background:radial-gradient(circle,rgba(14,165,233,.08),transparent 70%);bottom:-80px;right:-60px;animation-direction:reverse;animation-duration:13s}
      @keyframes orb-drift{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-18px) scale(1.04)}}
      .hero-inner{position:relative;z-index:1;display:grid;grid-template-columns:1fr 1fr;gap:3rem;align-items:center}
      @media(max-width:860px){.hero-inner{grid-template-columns:1fr;gap:2rem}}
      .hero-text{display:flex;flex-direction:column;gap:1.25rem}
      .hero-badge{display:inline-flex;align-items:center;gap:.375rem;padding:.28rem .875rem;background:var(--primary-light);color:var(--primary);border-radius:var(--radius-full);font-size:.78rem;font-weight:700;border:1px solid rgba(99,102,241,.2);box-shadow:0 2px 8px var(--primary-glow);width:fit-content}
      .hero-title{font-size:clamp(1.85rem,4.5vw,2.75rem);font-weight:800;letter-spacing:-.035em;line-height:1.18;color:var(--text)}
      .hero-sub{font-size:.975rem;color:var(--text-muted);line-height:1.75}
      .hero-actions{display:flex;gap:.75rem;flex-wrap:wrap;align-items:center}
      .hero-main-btn{padding:.75rem 1.5rem;font-size:.975rem}
      /* Stage card */
      .hero-visual{display:flex;justify-content:center}
      .stage-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:1.5rem;box-shadow:var(--shadow-md);width:100%;max-width:360px;display:flex;flex-direction:column;gap:.875rem}
      .stage-card-title{font-size:.72rem;font-weight:700;letter-spacing:.07em;color:var(--text-light);text-transform:uppercase}
      .stage-list{display:flex;flex-direction:column;gap:.5rem}
      .stage-row{display:flex;align-items:center;gap:.625rem;padding:.35rem .5rem;border-radius:var(--radius-xs);text-decoration:none;transition:background .15s}
      .stage-row:hover{background:var(--surface-2)}
      .sr-label{display:flex;flex-direction:column;width:72px;flex-shrink:0}
      .sr-num{font-size:.67rem;font-weight:700;color:var(--text-light);line-height:1.2}
      .sr-sub{font-size:.73rem;font-weight:600;color:var(--text);line-height:1.3}
      .sr-track{flex:1;height:6px;background:var(--surface-3);border-radius:3px;overflow:hidden}
      .sr-fill{height:100%;border-radius:3px}
      .stage-card-hint{font-size:.7rem;color:var(--text-light);text-align:center;line-height:1.4}
      /* Stats */
      .eyebrow{font-size:.73rem;font-weight:700;letter-spacing:.1em;color:var(--primary);text-transform:uppercase;margin-bottom:.75rem}
      .stats-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:.5rem}
      @media(max-width:640px){.stats-grid{grid-template-columns:1fr}}
      .stat-card{padding:1.5rem 1.25rem;text-align:center;display:flex;flex-direction:column;gap:.2rem}
      .stat-val{font-size:1.9rem;font-weight:800;letter-spacing:-.04em;line-height:1.1}
      .stat-label{font-size:.84rem;font-weight:600;color:var(--text);line-height:1.4;margin-top:.1rem}
      .stat-src{font-size:.71rem;color:var(--text-light)}
      .stats-note{font-size:.73rem;color:var(--text-light);text-align:center}
      /* Sec headers */
      .sec-title{font-size:1.45rem;font-weight:800;letter-spacing:-.025em;color:var(--text);margin-bottom:1.25rem}
      /* Flow */
      .flow-row{display:flex;align-items:stretch;gap:0}
      @media(max-width:600px){.flow-row{flex-direction:column}}
      .flow-card{flex:1;display:flex;align-items:center;gap:.875rem;padding:1rem 1.125rem;position:relative;text-decoration:none;transition:box-shadow .22s,border-color .22s,transform .22s}
      .flow-card:hover{transform:translateY(-3px)}
      .flow-icon{width:36px;height:36px;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;flex-shrink:0}
      .flow-num-dot{position:absolute;top:-8px;left:1rem;width:20px;height:20px;border-radius:50%;color:#fff;font-size:.67rem;font-weight:800;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,.15)}
      .flow-info{flex:1;display:flex;flex-direction:column;gap:.1rem}
      .flow-label{font-size:.875rem;font-weight:700;color:var(--text)}
      .flow-sub{font-size:.73rem;color:var(--text-light)}
      .flow-sep{width:28px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
      .flow-line{width:20px;height:2px;background:linear-gradient(90deg,var(--primary),var(--secondary));border-radius:2px}
      /* Promises */
      .promise-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1.25rem}
      .promise-card{padding:1.75rem;display:flex;flex-direction:column;gap:.5rem;position:relative;overflow:hidden}
      .promise-bg-num{position:absolute;top:.5rem;right:.875rem;font-size:3rem;font-weight:900;letter-spacing:-.05em;opacity:.05;color:var(--text);pointer-events:none}
      .promise-icon{width:42px;height:42px;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;margin-bottom:.25rem}
      .promise-kw{font-size:.63rem;font-weight:700;letter-spacing:.12em;color:var(--text-light)}
      .promise-title{font-size:1rem;font-weight:700;color:var(--text);line-height:1.3}
      .promise-desc{font-size:.865rem;color:var(--text-muted);line-height:1.65;flex:1}
      .promise-primary .promise-icon{background:var(--primary-light);color:var(--primary)}
      .promise-secondary .promise-icon{background:var(--secondary-light);color:var(--secondary)}
      .promise-accent .promise-icon{background:#fff1f2;color:#f43f5e}
      /* Persona */
      .persona-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:1.25rem}
      .persona-card{padding:1.5rem;display:flex;flex-direction:column;gap:.75rem}
      .persona-badge{display:inline-flex;align-items:center;padding:.2rem .75rem;border-radius:var(--radius-full);font-size:.72rem;font-weight:700;width:fit-content}
      .badge-red{background:#fff1f2;color:#f43f5e;border:1px solid rgba(244,63,94,.2)}
      .badge-indigo{background:var(--primary-light);color:var(--primary);border:1px solid rgba(99,102,241,.2)}
      .persona-name{font-size:1rem;font-weight:700;color:var(--text);line-height:1.3}
      .persona-desc{font-size:.865rem;color:var(--text-muted);line-height:1.65;flex:1}
      .persona-desc strong{color:var(--text)}
      .persona-link{display:inline-flex;align-items:center;gap:.35rem;font-size:.85rem;font-weight:600;color:var(--primary);transition:gap .15s;text-decoration:none;margin-top:.125rem}
      .persona-link:hover{gap:.55rem}
      /* CTA */
      .cta-section{background:linear-gradient(135deg,var(--primary-light) 0%,rgba(14,165,233,.07) 100%);border:1px solid rgba(99,102,241,.14);border-radius:var(--radius-lg);padding:2.75rem 2rem;text-align:center}
      .cta-inner{display:flex;flex-direction:column;align-items:center;gap:.875rem;max-width:520px;margin:0 auto}
      .cta-title{font-size:1.4rem;font-weight:800;letter-spacing:-.025em;color:var(--text);line-height:1.3}
      .cta-sub{font-size:.925rem;color:var(--text-muted);line-height:1.65}
      .cta-btn{padding:.875rem 2rem;font-size:1rem;margin-top:.375rem}
    `}</style>
  </div>
);

export default Home;
