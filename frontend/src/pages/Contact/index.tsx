// Content Hash: SHA256:TBD
import React, { useState } from 'react';
import { Mail, ExternalLink, MessageSquare, Send, CheckCircle2, Code2 } from 'lucide-react';

const FAQ = [
  {
    q: '자격증 추천 결과가 실제 취업을 보장하나요?',
    a: '아닙니다. DIDIM의 추천은 공공 통계(합격률·위험군 단계·NCS 매핑 등) 기반 참고 정보입니다. 실제 취업 여부는 개인 역량, 시장 상황 등 다양한 요인에 따라 다릅니다.',
  },
  {
    q: '위험군 진단 결과는 어디에 저장되나요?',
    a: '진단 결과는 브라우저 세션 스토리지에만 임시 저장되며, 탭을 닫으면 자동으로 삭제됩니다. 서버로 전송되거나 외부에 공유되지 않습니다.',
  },
  {
    q: '채용공고·훈련과정 정보가 최신이 아닌 것 같아요.',
    a: '채용공고(워크넷), 훈련과정(Work24), 시험일정(Q-Net)은 실시간 공공데이터 API를 통해 조회됩니다. API 응답 속도·데이터 업데이트 주기는 각 기관의 정책에 따르며, 최신 정보는 해당 기관 웹사이트에서 직접 확인하시기 바랍니다.',
  },
  {
    q: '특정 자격증이 목록에 없어요.',
    a: '현재 한국산업인력공단 국가기술자격 1,290건을 기반으로 운영합니다. 민간자격 또는 국가전문자격은 일부만 포함되어 있습니다. 추가 요청은 문의하기 이메일로 보내주세요.',
  },
  {
    q: '지도가 표시되지 않아요.',
    a: 'Kakao Maps SDK를 사용합니다. 브라우저에서 위치 권한을 허용하거나, 팝업 차단을 해제해보세요. 계속 문제가 발생하면 아래 이메일로 문의해주세요.',
  },
];

const Contact: React.FC = () => {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  const [sent, setSent] = useState(false);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    const subject = encodeURIComponent(`[DIDIM 문의] ${data.get('subject') ?? ''}`);
    const body = encodeURIComponent(
      `이름: ${data.get('name') ?? ''}\n\n내용:\n${data.get('message') ?? ''}`
    );
    window.location.href = `mailto:rlaehdrb2485@naver.com?subject=${subject}&body=${body}`;
    setSent(true);
  };

  return (
    <div className="contact-wrap">
      <div className="contact-header">
        <h1 className="contact-title">문의하기</h1>
        <p className="contact-sub">DIDIM 서비스 관련 의견이나 버그 제보를 남겨주세요.</p>
      </div>

      <div className="contact-grid">
        {/* 연락 채널 */}
        <div className="contact-channels">
          <h2 className="contact-sec-title">연락 채널</h2>
          <div className="channel-list">
            <a href="mailto:rlaehdrb2485@naver.com" className="channel-card">
              <Mail size={22} className="channel-icon" />
              <div>
                <p className="channel-name">이메일 문의</p>
                <p className="channel-desc">rlaehdrb2485@naver.com</p>
                <p className="channel-hint">일반 문의, 개인정보 관련 요청</p>
              </div>
            </a>
            <a href="https://www.didim.life" target="_blank" rel="noopener noreferrer" className="channel-card">
              <ExternalLink size={22} className="channel-icon" />
              <div>
                <p className="channel-name">서비스 바로가기</p>
                <p className="channel-desc">www.didim.life</p>
                <p className="channel-hint">운영 중인 서비스 확인</p>
              </div>
            </a>
          </div>

          {/* 빠른 문의 폼 */}
          <div className="quick-form-wrap">
            <div className="quick-form-header">
              <MessageSquare size={16} />
              <h3>빠른 문의</h3>
            </div>
            {sent ? (
              <div className="form-sent">
                <CheckCircle2 size={24} style={{ color: 'var(--success)' }} />
                <p>이메일 앱이 열렸습니다.<br />직접 전송 후 제출해주세요.</p>
                <button className="btn-ghost" onClick={() => setSent(false)}>다시 작성</button>
              </div>
            ) : (
              <form className="quick-form" onSubmit={handleSubmit}>
                <div className="form-group">
                  <label className="form-label">이름 / 닉네임</label>
                  <input name="name" type="text" className="input" placeholder="익명 가능" />
                </div>
                <div className="form-group">
                  <label className="form-label">문의 유형</label>
                  <div className="select-wrap" style={{ position: 'relative' }}>
                    <select name="subject" className="select" required>
                      <option value="">선택하세요</option>
                      <option value="버그 제보">버그 제보</option>
                      <option value="기능 제안">기능 제안</option>
                      <option value="데이터 오류">데이터 오류</option>
                      <option value="개인정보 문의">개인정보 문의</option>
                      <option value="기타">기타</option>
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">내용 <span style={{ color: 'var(--danger)' }}>*</span></label>
                  <textarea name="message" className="input form-textarea" placeholder="문의 내용을 자유롭게 작성해주세요." required />
                </div>
                <button type="submit" className="btn-primary form-submit">
                  <Send size={15} /> 이메일로 보내기
                </button>
                <p className="form-hint">제출 시 기본 이메일 앱이 열립니다.</p>
              </form>
            )}
          </div>
        </div>

        {/* FAQ */}
        <div className="faq-wrap">
          <h2 className="contact-sec-title">자주 묻는 질문</h2>
          <div className="faq-list">
            {FAQ.map((item, i) => (
              <div key={i} className={`faq-item${openIdx === i ? ' faq-open' : ''}`}>
                <button
                  className="faq-q"
                  onClick={() => setOpenIdx(openIdx === i ? null : i)}
                >
                  <span>{item.q}</span>
                  <span className="faq-arrow">{openIdx === i ? '▲' : '▼'}</span>
                </button>
                {openIdx === i && (
                  <div className="faq-a">{item.a}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <style>{`
        .contact-wrap { display: flex; flex-direction: column; gap: 2rem; max-width: 1000px; margin: 0 auto; }
        .contact-header { display: flex; flex-direction: column; gap: .5rem; }
        .contact-title { font-size: 1.75rem; font-weight: 900; color: var(--text); margin: 0; }
        .contact-sub { font-size: .9rem; color: var(--text-muted); margin: 0; }
        .contact-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; align-items: start; }
        @media (max-width: 768px) { .contact-grid { grid-template-columns: 1fr; } }
        .contact-sec-title { font-size: 1rem; font-weight: 800; color: var(--text); margin: 0 0 1rem; }
        .contact-channels { display: flex; flex-direction: column; gap: 1.25rem; }
        .channel-list { display: flex; flex-direction: column; gap: .625rem; }
        .channel-card {
          display: flex; align-items: flex-start; gap: .875rem;
          padding: 1rem 1.125rem;
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          text-decoration: none; color: inherit;
          transition: border-color .15s, box-shadow .15s;
          position: relative;
        }
        .channel-card:hover { border-color: var(--primary); box-shadow: 0 2px 12px rgba(99,102,241,.1); }
        .channel-icon { color: var(--primary); flex-shrink: 0; margin-top: .1rem; }
        .channel-ext { position: absolute; top: .875rem; right: .875rem; color: var(--text-light); }
        .channel-name { font-size: .875rem; font-weight: 700; color: var(--text); margin: 0; }
        .channel-desc { font-size: .8rem; color: var(--primary); margin: .15rem 0; }
        .channel-hint { font-size: .74rem; color: var(--text-light); margin: 0; }
        /* Quick form */
        .quick-form-wrap { padding: 1.25rem; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: 1rem; }
        .quick-form-header { display: flex; align-items: center; gap: .5rem; color: var(--primary); }
        .quick-form-header h3 { font-size: .9rem; font-weight: 800; color: var(--text); margin: 0; }
        .quick-form { display: flex; flex-direction: column; gap: .875rem; }
        .form-group { display: flex; flex-direction: column; gap: .35rem; }
        .form-label { font-size: .78rem; font-weight: 600; color: var(--text-muted); }
        .form-textarea { min-height: 120px; resize: vertical; }
        .form-submit { width: 100%; justify-content: center; gap: .5rem; }
        .form-hint { font-size: .72rem; color: var(--text-light); margin: 0; text-align: center; }
        .form-sent { display: flex; flex-direction: column; align-items: center; gap: .75rem; padding: 1.5rem 1rem; text-align: center; }
        .form-sent p { font-size: .875rem; color: var(--text-muted); margin: 0; line-height: 1.6; }
        /* FAQ */
        .faq-wrap { display: flex; flex-direction: column; gap: .5rem; }
        .faq-list { display: flex; flex-direction: column; gap: .5rem; }
        .faq-item { border: 1px solid var(--border); border-radius: var(--radius-sm); overflow: hidden; }
        .faq-item.faq-open { border-color: var(--primary); }
        .faq-q {
          width: 100%; display: flex; justify-content: space-between; align-items: center; gap: .75rem;
          padding: .875rem 1rem;
          background: var(--surface-2);
          border: none; cursor: pointer;
          font-size: .875rem; font-weight: 600; color: var(--text);
          text-align: left; transition: background .15s;
        }
        .faq-q:hover { background: var(--surface-3, #e2e8f0); }
        .faq-open .faq-q { background: var(--primary-light); color: var(--primary); }
        .faq-arrow { font-size: .65rem; flex-shrink: 0; color: var(--text-light); }
        .faq-open .faq-arrow { color: var(--primary); }
        .faq-a { padding: .875rem 1rem; font-size: .855rem; color: var(--text-muted); line-height: 1.75; border-top: 1px solid var(--border); }
      `}</style>
    </div>
  );
};

export default Contact;
