// Content Hash: SHA256:TBD
// Role: Kakao Maps 기반 인프라 시각화 컴포넌트
// - 일자리카페 (green), 건강증진센터 (purple), 훈련기관 (blue)
// - SDK는 VITE_KAKAO_JAVASCRIPT_KEY로 동적 로드 (autoload=false 패턴)
// - 마커 클릭 시 InfoWindow, 범례 토글로 레이어 제어
import React, { useEffect, useRef, useState } from 'react';

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    kakao: any;
  }
}

export interface MapPoint {
  type: 'job_cafe' | 'health_center' | 'training_institute';
  name: string;
  address: string;
  lat: number;
  lng: number;
  phone?: string | null;
  course_name?: string | null;
}

interface Props {
  points: MapPoint[];
  height?: string;
  /** 지도 중심 (기본: 서울 시청) */
  center?: { lat: number; lng: number };
}

const TYPE_CFG = {
  job_cafe:           { label: '일자리카페',   color: '#10b981', markerBg: '#dcfce7', emoji: '🍵' },
  health_center:      { label: '건강증진센터', color: '#8b5cf6', markerBg: '#ede9fe', emoji: '💜' },
  training_institute: { label: '훈련기관',     color: '#3b82f6', markerBg: '#dbeafe', emoji: '🎓' },
} as const;

const SEOUL = { lat: 37.5665, lng: 126.9780 };

/** Kakao Maps SDK 동적 로드 (중복 로드 방지) */
function loadSdk(appKey: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.kakao?.maps?.Map) { resolve(); return; }
    const existing = document.getElementById('kakao-maps-sdk');
    if (existing) {
      // 이미 로드 시작됨 — 완료 대기
      existing.addEventListener('load', () => window.kakao.maps.load(resolve));
      existing.addEventListener('error', reject);
      return;
    }
    const script = document.createElement('script');
    script.id = 'kakao-maps-sdk';
    script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${appKey}&libraries=clusterer&autoload=false`;
    script.onload = () => window.kakao.maps.load(resolve);
    script.onerror = () => reject(new Error('Kakao Maps SDK load failed'));
    document.head.appendChild(script);
  });
}

const KakaoMap: React.FC<Props> = ({ points, height = '360px', center = SEOUL }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const markersRef = useRef<{ marker: any; type: string }[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const infoWindowRef = useRef<any>(null);

  const [sdkReady, setSdkReady] = useState(false);
  const [sdkError, setSdkError] = useState(false);
  const [activeTypes, setActiveTypes] = useState<Record<string, boolean>>({
    job_cafe: true,
    health_center: true,
    training_institute: true,
  });

  const APP_KEY = import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY as string | undefined;

  // ── 1. SDK 로드 ────────────────────────────────────────────────────
  useEffect(() => {
    if (!APP_KEY) { setSdkError(true); return; }
    loadSdk(APP_KEY).then(() => setSdkReady(true)).catch(() => setSdkError(true));
  }, [APP_KEY]);

  // ── 2. 지도 초기화 ──────────────────────────────────────────────────
  useEffect(() => {
    if (!sdkReady || !containerRef.current) return;
    if (!mapRef.current) {
      mapRef.current = new window.kakao.maps.Map(containerRef.current, {
        center: new window.kakao.maps.LatLng(center.lat, center.lng),
        level: 9,
      });
      infoWindowRef.current = new window.kakao.maps.InfoWindow({ zIndex: 10 });
    }
  }, [sdkReady, center.lat, center.lng]);

  // ── 3. 마커 그리기 ──────────────────────────────────────────────────
  useEffect(() => {
    if (!sdkReady || !mapRef.current) return;

    // 기존 마커 제거
    markersRef.current.forEach(({ marker }) => marker.setMap(null));
    markersRef.current = [];

    const bounds = new window.kakao.maps.LatLngBounds();
    let hasVisible = false;

    points.forEach(p => {
      if (!activeTypes[p.type]) return;
      const cfg = TYPE_CFG[p.type];
      const pos = new window.kakao.maps.LatLng(p.lat, p.lng);
      bounds.extend(pos);
      hasVisible = true;

      // 커스텀 오버레이로 이모지 마커 구현
      const overlay = new window.kakao.maps.CustomOverlay({
        position: pos,
        content: `<div style="
          background:${cfg.markerBg};border:1.5px solid ${cfg.color};
          border-radius:50%;width:28px;height:28px;
          display:flex;align-items:center;justify-content:center;
          font-size:14px;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.18);
          transition:transform .15s;
        " title="${p.name}">${cfg.emoji}</div>`,
        zIndex: 3,
      });
      overlay.setMap(mapRef.current);

      // 클릭 → InfoWindow
      const content = document.createElement('div');
      content.innerHTML = `
        <div style="padding:8px 10px;max-width:240px;font-family:inherit">
          <div style="display:flex;align-items:center;gap:5px;margin-bottom:4px">
            <span style="
              padding:1px 6px;border-radius:99px;font-size:10px;font-weight:700;
              background:${cfg.markerBg};color:${cfg.color};border:1px solid ${cfg.color}40
            ">${cfg.label}</span>
          </div>
          <div style="font-weight:700;font-size:12px;color:#1e293b;line-height:1.4">${p.name}</div>
          <div style="font-size:11px;color:#64748b;margin-top:2px;line-height:1.4">${p.address}</div>
          ${p.phone ? `<div style="font-size:11px;color:#64748b;margin-top:2px">📞 ${p.phone}</div>` : ''}
          ${p.course_name ? `<div style="font-size:11px;color:#64748b;margin-top:2px;font-style:italic">📖 ${p.course_name}</div>` : ''}
        </div>
      `;

      window.kakao.maps.event.addListener(overlay, 'click', () => {
        infoWindowRef.current.setContent(content);
        // CustomOverlay의 getPosition()은 LatLng를 반환하므로 Marker 대신 직접 열기
        infoWindowRef.current.open(mapRef.current, {
          getPosition: () => pos,
          getMap: () => mapRef.current,
        });
      });

      markersRef.current.push({ marker: overlay, type: p.type });
    });

    if (hasVisible && points.length > 1) {
      mapRef.current.setBounds(bounds);
    }
  }, [sdkReady, points, activeTypes]);

  if (!APP_KEY || sdkError) {
    return (
      <div className="kmap-error">
        🗺️ 지도를 불러올 수 없습니다.<br />
        <span style={{ fontSize: '.75rem', opacity: .7 }}>Kakao Maps API 키를 확인하세요.</span>
      </div>
    );
  }

  const toggleType = (type: string) =>
    setActiveTypes(prev => ({ ...prev, [type]: !prev[type] }));

  return (
    <div className="kmap-wrap">
      {/* 범례 */}
      <div className="kmap-legend">
        {(Object.entries(TYPE_CFG) as [keyof typeof TYPE_CFG, typeof TYPE_CFG[keyof typeof TYPE_CFG]][]).map(
          ([type, cfg]) => {
            const count = points.filter(p => p.type === type).length;
            const active = activeTypes[type];
            return (
              <button
                key={type}
                className={`kmap-legend-btn${active ? ' active' : ''}`}
                style={{ '--lc': cfg.color } as React.CSSProperties}
                onClick={() => toggleType(type)}
                type="button"
              >
                <span className="kmap-legend-dot" />
                {cfg.label}
                {count > 0 && <span className="kmap-legend-cnt">{count}</span>}
              </button>
            );
          }
        )}
      </div>

      {/* 지도 컨테이너 */}
      <div style={{ position: 'relative' }}>
        <div ref={containerRef} style={{ width: '100%', height }} />
        {!sdkReady && (
          <div className="kmap-loading">지도 로딩 중…</div>
        )}
      </div>

      <style>{`
        .kmap-wrap { display: flex; flex-direction: column; gap: .5rem; }
        .kmap-legend { display: flex; gap: .35rem; flex-wrap: wrap; }
        .kmap-legend-btn {
          display: inline-flex; align-items: center; gap: .3rem;
          padding: .2rem .65rem; border-radius: 99px;
          border: 1.5px solid var(--lc, #94a3b8);
          background: none; cursor: pointer; font-size: .72rem; font-weight: 600;
          color: #64748b; opacity: .45; transition: all .15s;
        }
        .kmap-legend-btn.active { opacity: 1; color: var(--lc); background: color-mix(in srgb, var(--lc) 10%, white); }
        .kmap-legend-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--lc); flex-shrink: 0; }
        .kmap-legend-cnt { font-weight: 800; font-size: .7rem; }
        .kmap-loading {
          position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
          background: rgba(248,250,252,.85); font-size: .8rem; color: #94a3b8;
        }
        .kmap-error {
          padding: 1rem; background: #fef2f2; border: 1px solid #fecaca;
          border-radius: 8px; font-size: .82rem; color: #ef4444; text-align: center;
          line-height: 1.6;
        }
      `}</style>
    </div>
  );
};

export default KakaoMap;
