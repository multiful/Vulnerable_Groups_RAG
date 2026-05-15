// Content Hash: SHA256:TBD
import React, { useState, useCallback } from 'react';
import { ArrowRight, Calendar, Briefcase, BookOpen, Map, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';


const SERVICES = [
  {
    icon: Calendar,
    title: '시험 일정',
    desc: 'Q-Net 실시간 D-Day',
    path: '/schedule',
    color: '#6366f1',
    bg: '#eef2ff',
  },
  {
    icon: Briefcase,
    title: '채용 정보',
    desc: 'WorkNet 실시간 공고',
    path: '/jobs',
    color: '#0ea5e9',
    bg: '#e0f2fe',
  },
  {
    icon: BookOpen,
    title: '직업·학과 탐색',
    desc: '커리어넷 직업·학과 정보',
    path: '/explore',
    color: '#10b981',
    bg: '#ecfdf5',
  },
  {
    icon: Map,
    title: '주변 인프라',
    desc: '일자리카페·훈련기관',
    path: '/recommendation',
    color: '#f59e0b',
    bg: '#fef3c7',
  },
];

const PROMISES = [
  {
    num:'01', keyword:'PERSONALIZED', title:'내 단계에 맞는 추천',
    desc:'위험군 단계에 따라 지금 도전 가능한 자격증부터 추천합니다. 단계가 높을수록 더 작은 첫 걸음을 제안합니다.',
    color:'promise-primary',
  },
  {
    num:'02', keyword:'STRUCTURED', title:'자격증부터 취업까지 연결',
    desc:'자격증 하나를 선택하면 관련 직무, 훈련 과정, 채용 공고까지 한 화면에서 확인할 수 있습니다.',
    color:'promise-secondary',
  },
  {
    num:'03', keyword:'EVIDENCE-BACKED', title:'이유가 있는 추천',
    desc:'공식 문서와 국가 통계를 근거로 추천 이유를 설명합니다. 추측이 아닌 실제 데이터에서 가져온 정보입니다.',
    color:'promise-accent',
  },
];

const FLOW = [
  { num:'1', label:'위험군 진단',  sub:'12문항 설문',      path:'/risk-assessment', color:'#2563eb' },
  { num:'2', label:'관심 선택',    sub:'도메인 직접 선택',  path:'/interests',       color:'#2563eb' },
  { num:'3', label:'로드맵 확인',  sub:'단계별 경로 안내',  path:'/roadmap',         color:'#2563eb' },
  { num:'4', label:'자격증 확인',  sub:'상세 정보·근거',    path:'/recommendation',  color:'#2563eb' },
];

const Home: React.FC = () => {
  const [happy, setHappy] = useState(false);

  const handleMascotClick = useCallback(() => {
    if (happy) return;
    setHappy(true);
    setTimeout(() => setHappy(false), 2000);
  }, [happy]);

  return (
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
            <div className="mascot-wrap" onClick={handleMascotClick}>
              <img
                src={happy ? '/didimi_smile.png' : '/didimi.png'}
                alt="디딤이"
                className={`mascot-img${happy ? ' mascot-happy' : ''}`}
              />
              {happy && <span className="mascot-heart">🩷</span>}
            </div>
          </div>
        </div>
      </div>
    </section>

    {/* 서비스 빠른 접근 */}
    <section>
      <p className="eyebrow">공공데이터 실시간 연동</p>
      <h2 className="sec-title">자격증 추천 이후도 함께합니다</h2>
      <div className="service-grid">
        {SERVICES.map(s => (
          <Link key={s.path} to={s.path} className="service-card card" style={{'--sc': s.color, '--sc-bg': s.bg} as React.CSSProperties}>
            <div className="service-icon-wrap" style={{background: s.bg}}>
              <s.icon size={20} style={{color: s.color}} />
            </div>
            <div className="service-info">
              <span className="service-title">{s.title}</span>
              <span className="service-desc">{s.desc}</span>
            </div>
            <ArrowRight size={14} className="service-arrow" />
          </Link>
        ))}
      </div>
    </section>

    <section>
      <p className="eyebrow">이용 흐름</p>
      <h2 className="sec-title">4단계로 완성되는 맞춤 추천</h2>
      <div className="flow-row">
        {FLOW.map((s, i) => (
          <React.Fragment key={s.num}>
            <div className="flow-card card">
              <div className="flow-num-dot" style={{background:s.color}}>{s.num}</div>
              <div className="flow-info">
                <span className="flow-label">{s.label}</span>
                <span className="flow-sub">{s.sub}</span>
              </div>
            </div>
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

    <section className="data-source-section">
      <div className="data-stats-row">
        <div className="ds-stat">
          <span className="ds-stat-num">5,513명</span>
          <span className="ds-stat-desc">서울 청년 조사 샘플</span>
        </div>
        <div className="ds-stat">
          <span className="ds-stat-num">9.4%</span>
          <span className="ds-stat-desc">고립·은둔 경험 청년 비율</span>
        </div>
        <div className="ds-stat">
          <span className="ds-stat-num">12문항</span>
          <span className="ds-stat-desc">선별된 진단 문항</span>
        </div>
        <div className="ds-stat">
          <span className="ds-stat-num">RAG</span>
          <span className="ds-stat-desc">자격증 근거 검색 기술</span>
        </div>
      </div>
    </section>

    {/* 오늘의 행동 티저 */}
    <section className="today-section">
      <div className="today-inner">
        <div className="today-left">
          <div className="today-badge"><Zap size={12}/> 오늘의 한 가지 행동</div>
          <h3 className="today-title">작은 행동 하나가 경로를 바꿉니다</h3>
          <p className="today-desc">
            진단 후 맞춤 로드맵에서 위험군 단계와 관심 자격증에 맞는 오늘의 구체적인 행동 하나를 추천받아보세요.
            시험 접수, 강의 1강, 훈련기관 방문 예약 등 작은 것부터 시작합니다.
          </p>
          <Link to="/risk-assessment" className="btn-primary today-btn">진단하고 행동 추천 받기 <ArrowRight size={16}/></Link>
        </div>
        <div className="today-right">
          <div className="today-example-card">
            <span className="today-ex-label">예시</span>
            <p className="today-ex-action">📚 오늘 30분 공부</p>
            <p className="today-ex-desc">정보처리기사 관련 무료 강의 1강을 들어 보세요.</p>
            <div className="today-ex-effort"><span className="today-ex-min">30분</span> 소요 예상</div>
          </div>
        </div>
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
      .mascot-figure{display:flex;justify-content:center;align-items:center;width:100%;position:relative}
      .mascot-wrap{position:relative;width:260px;height:260px;flex-shrink:0;cursor:pointer}
      .mascot-img{width:260px;height:260px;object-fit:contain;filter:drop-shadow(0 12px 32px rgba(99,102,241,.25));animation:mascot-float 3s ease-in-out infinite}
      .mascot-img.mascot-happy{animation:mascot-bounce .4s ease forwards, mascot-float 3s ease-in-out 0.4s infinite}
.mascot-heart{position:absolute;top:5px;left:50%;transform:translateX(-50%);font-size:1.6rem;animation:heart-pop .6s ease forwards;pointer-events:none}
      @keyframes mascot-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
      @keyframes mascot-bounce{0%{transform:scale(1)}25%{transform:scale(1.13) translateY(-12px)}55%{transform:scale(.97) translateY(0)}75%{transform:scale(1.05) translateY(-5px)}100%{transform:scale(1) translateY(0)}}
@keyframes heart-pop{0%{opacity:0;transform:scale(0) translateY(0)}40%{opacity:1;transform:scale(1.3) translateY(-8px)}70%{opacity:1;transform:scale(1) translateY(-14px)}100%{opacity:0;transform:scale(.8) translateY(-22px)}}
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
      .flow-card{flex:1;min-width:130px;display:flex;align-items:center;gap:.75rem;padding:.875rem 1rem;position:relative;cursor:default}
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
      .eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.1em;color:var(--primary);text-transform:uppercase;margin-bottom:.375rem}
      .data-source-section{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:.875rem}
      .data-source-inner{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}
      .ds-icon{color:var(--text-light);flex-shrink:0}
      .ds-label{font-size:.72rem;font-weight:700;letter-spacing:.08em;color:var(--text-light);text-transform:uppercase;flex-shrink:0}
      .ds-divider{color:var(--border);font-size:.85rem;flex-shrink:0}
      .ds-item{font-size:.78rem;color:var(--text-muted)}
      .ds-dot{color:var(--text-light);font-size:.85rem}
      .data-stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem}
      @media(max-width:600px){.data-stats-row{grid-template-columns:repeat(2,1fr)}}
      .ds-stat{display:flex;flex-direction:column;gap:.18rem;padding:.75rem;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);text-align:center}
      .ds-stat-num{font-size:1.1rem;font-weight:800;color:var(--primary);letter-spacing:-.02em}
      .ds-stat-desc{font-size:.7rem;color:var(--text-light);line-height:1.4}
      /* 서비스 그리드 */
      .service-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:.875rem}
      .service-card{
        display:flex;align-items:center;gap:.75rem;
        padding:.875rem 1rem;text-decoration:none;
        transition:all .15s;
      }
      .service-card:hover{border-color:var(--sc,var(--primary));transform:translateY(-1px);box-shadow:0 4px 14px rgba(0,0,0,.07)}
      .service-icon-wrap{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
      .service-info{flex:1;display:flex;flex-direction:column;gap:.08rem}
      .service-title{font-size:.875rem;font-weight:700;color:var(--text)}
      .service-desc{font-size:.72rem;color:var(--text-muted)}
      .service-arrow{color:var(--text-light);flex-shrink:0;transition:transform .15s}
      .service-card:hover .service-arrow{transform:translateX(2px);color:var(--sc,var(--primary))}

      /* 오늘의 행동 티저 */
      .today-section{
        background:linear-gradient(135deg,#1d4ed8 0%,#2563eb 55%,#3b82f6 100%);
        border-radius:var(--radius-lg);
        padding:2rem 2.25rem;
        color:#fff;
      }
      .today-inner{display:grid;grid-template-columns:1fr auto;gap:2rem;align-items:center}
      @media(max-width:600px){.today-inner{grid-template-columns:1fr}}
      .today-left{display:flex;flex-direction:column;gap:.75rem}
      .today-badge{
        display:inline-flex;align-items:center;gap:.3rem;
        padding:.2rem .625rem;background:rgba(255,255,255,.15);
        border-radius:20px;font-size:.72rem;font-weight:700;
        color:rgba(255,255,255,.9);width:fit-content;
      }
      .today-title{font-size:1.25rem;font-weight:800;line-height:1.3;letter-spacing:-.02em}
      .today-desc{font-size:.85rem;color:rgba(255,255,255,.75);line-height:1.7}
      .today-btn{background:#fff;color:#1d4ed8;padding:.65rem 1.25rem;font-size:.875rem;width:fit-content}
      .today-btn:hover{background:rgba(255,255,255,.9)}
      .today-right{}
      .today-example-card{
        background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);
        border-radius:12px;padding:1rem 1.1rem;
        display:flex;flex-direction:column;gap:.4rem;min-width:200px;
      }
      .today-ex-label{font-size:.65rem;font-weight:700;color:rgba(255,255,255,.5);letter-spacing:.08em;text-transform:uppercase}
      .today-ex-action{font-size:.95rem;font-weight:700;margin:0}
      .today-ex-desc{font-size:.78rem;color:rgba(255,255,255,.7);margin:0;line-height:1.5}
      .today-ex-effort{display:flex;align-items:center;gap:.35rem;font-size:.72rem;color:rgba(255,255,255,.55)}
      .today-ex-min{font-weight:700;color:rgba(255,255,255,.8)}

      .cta-section{background:var(--primary-light);border:1px solid rgba(37,99,235,.14);border-radius:var(--radius-lg);padding:2.75rem 2rem;text-align:center}
      .cta-inner{display:flex;flex-direction:column;align-items:center;gap:.875rem;max-width:520px;margin:0 auto}
      .cta-title{font-size:1.4rem;font-weight:800;letter-spacing:-.025em;color:var(--text);line-height:1.3}
      .cta-sub{font-size:.925rem;color:var(--text-muted);line-height:1.65}
      .cta-btn{padding:.875rem 2rem;font-size:1rem;margin-top:.375rem}
    `}</style>
  </div>
  );
};

export default Home;
