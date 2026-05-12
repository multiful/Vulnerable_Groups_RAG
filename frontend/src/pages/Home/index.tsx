// Content Hash: SHA256:TBD
import React from 'react';
import { ArrowRight, CheckCircle2 } from 'lucide-react';
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
    color:'promise-primary',
  },
  {
    num:'02', keyword:'STRUCTURED', title:'구조적으로 연결된 추천',
    desc:'자격증·직무·도메인·로드맵 단계가 canonical 데이터로 묶여 있습니다. 한 번의 추천이 4가지 정보를 동시에 설명합니다.',
    color:'promise-secondary',
  },
  {
    num:'03', keyword:'EVIDENCE-BACKED', title:'근거가 있는 추천',
    desc:'공식 PDF/HTML 문서에서 RAG로 근거 스니펫을 가져옵니다. 근거가 0건이면 환각 대신 안내를 표시합니다.',
    color:'promise-accent',
  },
];

const FLOW = [
  { num:'1', label:'위험군 진단',  sub:'12문항 설문',      path:'/risk-assessment', color:'#2563eb' },
  { num:'2', label:'관심 선택',    sub:'도메인 직접 선택',  path:'/interests',       color:'#2563eb' },
  { num:'3', label:'로드맵 확인',  sub:'단계별 경로 안내',  path:'/roadmap',         color:'#2563eb' },
  { num:'4', label:'자격증 확인',  sub:'상세 정보·근거',    path:'/recommendation',  color:'#2563eb' },
];

const Home: React.FC = () => (
  <div className="home-wrap">

    <section className="hero">
      <div className="hero-inner">
        <div className="hero-text">
          <div className="hero-badge">청년 위험군 맞춤 자격증 추천</div>
          <h1 className="hero-title">내 상황에 맞는<br/><span className="gradient-text">자격증과 성장 경로</span></h1>
          <p className="hero-sub">위험군 진단 후 관심 도메인을 선택하면 맞춤 로드맵과 자격증을 추천합니다.</p>
          <div className="hero-actions">
            <Link to="/risk-assessment" className="btn-primary hero-main-btn">진단 시작하기 <ArrowRight size={17}/></Link>
            <Link to="/certs" className="btn-ghost">자격증 둘러보기</Link>
          </div>
        </div>
        <div className="hero-visual">
          <div className="mascot-figure">
            <img src="/didimi.png" alt="디딤이" className="mascot-img" />
          </div>
        </div>
      </div>
    </section>

    <section>
      <p className="eyebrow">이용 흐름</p>
      <h2 className="sec-title">4단계로 완성되는 맞춤 추천</h2>
      <div className="flow-row">
        {FLOW.map((s, i) => (
          <React.Fragment key={s.num}>
            <Link to={s.path} className="flow-card card">
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

    <section>
      <p className="eyebrow">디딤의 3가지 약속</p>
      <h2 className="sec-title">추천을 행동으로 바꿉니다</h2>
      <div className="promise-grid">
        {PROMISES.map(p => (
          <div key={p.num} className={`promise-card card ${p.color}`}>
            <div className="promise-bg-num">{p.num}</div>
            <p className="promise-kw">{p.keyword}</p>
            <h3 className="promise-title">{p.title}</h3>
            <p className="promise-desc">{p.desc}</p>
          </div>
        ))}
      </div>
    </section>

    <section className="cta-section">
      <div className="cta-inner">
        <CheckCircle2 size={32} style={{color:'var(--success)'}}/>
        <h2 className="cta-title">청년의 다음 한 걸음을 데이터로 설명합니다</h2>
        <p className="cta-sub">인기순이 아닌, 위험군·도메인 기반의 정확한 추천을 받아보세요.</p>
        <Link to="/risk-assessment" className="btn-primary cta-btn">위험군 진단 시작하기 <ArrowRight size={17}/></Link>
      </div>
    </section>

    <style>{`
      .home-wrap{display:flex;flex-direction:column;gap:3.5rem;padding-bottom:1rem}
      .hero{padding:1.5rem 0 .5rem}
      .hero-inner{display:grid;grid-template-columns:1fr 1fr;gap:3rem;align-items:center}
      @media(max-width:860px){.hero-inner{grid-template-columns:1fr;gap:2rem}}
      .hero-text{display:flex;flex-direction:column;gap:1.25rem}
      .hero-badge{display:inline-flex;align-items:center;gap:.375rem;padding:.28rem .875rem;background:var(--primary-light);color:var(--primary);border-radius:var(--radius-full);font-size:.78rem;font-weight:700;border:1px solid rgba(37,99,235,.2);width:fit-content}
      .hero-title{font-size:clamp(1.85rem,4.5vw,2.75rem);font-weight:800;letter-spacing:-.035em;line-height:1.18;color:var(--text)}
      .hero-sub{font-size:.975rem;color:var(--text-muted);line-height:1.75}
      .hero-actions{display:flex;gap:.75rem;flex-wrap:wrap;align-items:center}
      .hero-main-btn{padding:.75rem 1.5rem;font-size:.975rem}
      .hero-visual{display:flex;justify-content:center}
      .mascot-figure{display:flex;justify-content:center;align-items:center;width:100%}
      .mascot-img{width:260px;height:260px;object-fit:contain;filter:drop-shadow(0 12px 32px rgba(99,102,241,.25));animation:mascot-float 3s ease-in-out infinite}
      @keyframes mascot-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
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
      .sec-title{font-size:1.45rem;font-weight:800;letter-spacing:-.025em;color:var(--text);margin-bottom:1.25rem}
      .flow-row{display:flex;align-items:stretch;gap:0;flex-wrap:wrap}
      @media(max-width:700px){.flow-row{flex-direction:column}}
      .flow-card{flex:1;min-width:130px;display:flex;align-items:center;gap:.75rem;padding:.875rem 1rem;position:relative;text-decoration:none;transition:box-shadow .22s,border-color .22s,transform .22s}
      .flow-card:hover{transform:translateY(-3px)}
      .flow-num-dot{position:absolute;top:-8px;left:.875rem;width:18px;height:18px;border-radius:50%;color:#fff;font-size:.63rem;font-weight:800;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,.15)}
      .flow-info{flex:1;display:flex;flex-direction:column;gap:.08rem;min-width:0}
      .flow-label{font-size:.82rem;font-weight:700;color:var(--text)}
      .flow-sub{font-size:.7rem;color:var(--text-light)}
      .flow-sep{width:24px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
      .flow-line{width:16px;height:2px;background:var(--primary);border-radius:2px;opacity:.4}
      .promise-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1.25rem}
      .promise-card{padding:1.75rem;display:flex;flex-direction:column;gap:.5rem;position:relative;overflow:hidden}
      .promise-bg-num{position:absolute;top:.5rem;right:.875rem;font-size:3rem;font-weight:900;letter-spacing:-.05em;opacity:.05;color:var(--text);pointer-events:none}
      .promise-kw{font-size:.63rem;font-weight:700;letter-spacing:.12em;color:var(--text-light)}
      .promise-title{font-size:1rem;font-weight:700;color:var(--text);line-height:1.3}
      .promise-desc{font-size:.865rem;color:var(--text-muted);line-height:1.65;flex:1}
      .cta-section{background:var(--primary-light);border:1px solid rgba(37,99,235,.14);border-radius:var(--radius-lg);padding:2.75rem 2rem;text-align:center}
      .cta-inner{display:flex;flex-direction:column;align-items:center;gap:.875rem;max-width:520px;margin:0 auto}
      .cta-title{font-size:1.4rem;font-weight:800;letter-spacing:-.025em;color:var(--text);line-height:1.3}
      .cta-sub{font-size:.925rem;color:var(--text-muted);line-height:1.65}
      .cta-btn{padding:.875rem 2rem;font-size:1rem;margin-top:.375rem}
    `}</style>
  </div>
);

export default Home;
