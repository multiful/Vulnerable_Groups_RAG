// Content Hash: SHA256:TBD
import React from 'react';

const Privacy: React.FC = () => {
  return (
    <div className="policy-wrap">
      <div className="policy-header">
        <h1 className="policy-title">개인정보처리방침</h1>
        <p className="policy-subtitle">시행일: 2026년 5월 14일</p>
      </div>

      <div className="policy-body">
        <section className="policy-section">
          <h2>제1조 (총칙)</h2>
          <p>
            DIDIM (이하 "서비스")은 청년 위험군 단계 맞춤 자격증·로드맵 추천 서비스입니다.
            서비스는 이용자의 개인정보를 중요하게 여기며, 「개인정보 보호법」을 준수합니다.
            본 방침은 서비스가 어떠한 정보를 수집하고, 어떻게 이용하는지를 안내합니다.
          </p>
        </section>

        <section className="policy-section">
          <h2>제2조 (수집하는 개인정보 항목)</h2>
          <p>서비스는 회원가입, 로그인 등의 계정 체계를 운영하지 않으며, 이름·이메일·연락처 등의
          개인식별정보를 수집하지 않습니다.</p>
          <p>서비스 이용 과정에서 아래 정보가 <strong>이용자의 기기(브라우저) 세션 스토리지에만</strong> 임시 저장됩니다.</p>
          <ul>
            <li>위험군 진단 결과 (단계 코드)</li>
            <li>선택한 관심 도메인 및 직무 코드</li>
          </ul>
          <p>이 정보는 브라우저 탭을 닫거나 세션 종료 시 자동으로 삭제되며, 서버로 전송되거나
          영구 저장되지 않습니다.</p>
        </section>

        <section className="policy-section">
          <h2>제3조 (개인정보의 수집 방법)</h2>
          <p>운영팀은 서버 측에서 다음 정보를 자동 수집할 수 있습니다.</p>
          <ul>
            <li>서버 접속 로그 (IP 주소, 접속 시각, 요청 경로)</li>
          </ul>
          <p>이는 서비스 운영 및 장애 대응 목적으로만 사용되며, 개인 식별 목적으로 활용하지 않습니다.</p>
        </section>

        <section className="policy-section">
          <h2>제4조 (개인정보의 이용 목적)</h2>
          <p>수집된 로그 정보는 서비스 품질 유지 및 보안 목적으로만 이용하며,
          제3자에게 제공하지 않습니다.</p>
        </section>

        <section className="policy-section">
          <h2>제5조 (외부 서비스 연동)</h2>
          <p>서비스는 이용자에게 정보를 제공하기 위해 다음 외부 서비스를 연동합니다.
          각 서비스의 이용약관 및 개인정보처리방침이 별도로 적용됩니다.</p>
          <table className="policy-table">
            <thead>
              <tr><th>외부 서비스</th><th>용도</th><th>운영자</th></tr>
            </thead>
            <tbody>
              <tr><td>Kakao Maps JS SDK</td><td>인프라 지도 시각화</td><td>Kakao Corp.</td></tr>
              <tr><td>Kakao REST API (지오코딩)</td><td>주소→좌표 변환</td><td>Kakao Corp.</td></tr>
              <tr><td>YouTube Data API v3</td><td>자격증 관련 강의 영상 검색</td><td>Google LLC</td></tr>
              <tr><td>한국산업인력공단 Q-Net API</td><td>시험일정·자격정보 조회</td><td>한국산업인력공단</td></tr>
              <tr><td>워크넷 채용정보 API</td><td>채용공고 조회</td><td>한국고용정보원</td></tr>
              <tr><td>Work24 훈련과정 API</td><td>훈련과정 조회</td><td>한국고용정보원</td></tr>
              <tr><td>서울시 공공데이터 API</td><td>일자리카페·건강증진센터 조회</td><td>서울특별시</td></tr>
            </tbody>
          </table>
        </section>

        <section className="policy-section">
          <h2>제6조 (개인정보의 보유 및 파기)</h2>
          <p>브라우저 세션 스토리지에 저장된 진단 결과는 세션 종료 즉시 자동 삭제됩니다.
          서버 접속 로그는 최대 30일간 보관 후 자동 삭제됩니다.</p>
        </section>

        <section className="policy-section">
          <h2>제7조 (이용자의 권리)</h2>
          <p>이용자는 언제든지 브라우저의 세션 스토리지를 직접 삭제할 수 있습니다.
          개인정보 관련 문의는 서비스 내 문의하기 페이지를 이용해 주세요.</p>
        </section>

        <section className="policy-section">
          <h2>제8조 (방침 변경)</h2>
          <p>본 방침은 법령·정책 변경에 따라 개정될 수 있으며, 변경 시 서비스 내 공지를 통해 안내합니다.</p>
        </section>

        <div className="policy-contact-box">
          <strong>개인정보 문의</strong>
          <p>서비스 내 <a href="/contact">문의하기 페이지</a>를 이용해 주세요.</p>
        </div>
      </div>

      <style>{`
        .policy-wrap { max-width: 760px; margin: 0 auto; display: flex; flex-direction: column; gap: 2rem; }
        .policy-header { display: flex; flex-direction: column; gap: .5rem; padding-bottom: 1.5rem; border-bottom: 2px solid var(--border-strong); }
        .policy-title { font-size: 1.75rem; font-weight: 900; color: var(--text); margin: 0; }
        .policy-subtitle { font-size: .85rem; color: var(--text-muted); margin: 0; }
        .policy-body { display: flex; flex-direction: column; gap: 2rem; }
        .policy-section { display: flex; flex-direction: column; gap: .75rem; }
        .policy-section h2 { font-size: 1rem; font-weight: 800; color: var(--text); margin: 0; padding-bottom: .375rem; border-bottom: 1px solid var(--border); }
        .policy-section p { font-size: .875rem; color: var(--text-muted); line-height: 1.75; margin: 0; }
        .policy-section ul { margin: 0; padding-left: 1.25rem; display: flex; flex-direction: column; gap: .35rem; }
        .policy-section li { font-size: .875rem; color: var(--text-muted); line-height: 1.65; }
        .policy-table { width: 100%; border-collapse: collapse; font-size: .82rem; }
        .policy-table th, .policy-table td { padding: .5rem .75rem; text-align: left; border: 1px solid var(--border); }
        .policy-table thead { background: var(--surface-2); }
        .policy-table th { font-weight: 700; color: var(--text); }
        .policy-table td { color: var(--text-muted); }
        .policy-section a { color: var(--primary); }
        .policy-contact-box { padding: 1.25rem 1.5rem; background: var(--surface-2); border: 1px solid var(--border); border-left: 4px solid var(--primary); border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: .35rem; }
        .policy-contact-box strong { font-size: .9rem; color: var(--text); }
        .policy-contact-box p { font-size: .82rem; color: var(--text-muted); margin: 0; }
        .policy-contact-box a { color: var(--primary); }
        @media (max-width: 600px) { .policy-table { font-size: .74rem; } .policy-table th, .policy-table td { padding: .35rem .5rem; } }
      `}</style>
    </div>
  );
};

export default Privacy;
