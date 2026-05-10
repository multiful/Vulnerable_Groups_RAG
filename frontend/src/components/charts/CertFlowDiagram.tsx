// Content Hash: SHA256:TBD
// Role: 자격증 선행/현재/후행 관계를 SVG 베지어 화살표 + 위치 지정 노드로 렌더링
import React from 'react';

export interface FlowNode {
  cert_id: string;
  cert_name: string;
  relation_label?: string;
  cert_grade_tier?: string;
  avg_pass_rate?: number | null;
}

interface Props {
  current: { cert_id: string; cert_name: string };
  predecessors: FlowNode[];
  successors: FlowNode[];
  onNodeClick: (id: string, name: string) => void;
}

const NW = 126;   // node width px
const NH = 52;    // node height px
const CG = 50;    // horizontal gap between columns
const RG = 10;    // vertical gap between rows in same column
const PD = 4;     // SVG canvas padding

export const CertFlowDiagram: React.FC<Props> = ({
  current, predecessors, successors, onNodeClick,
}) => {
  const hasPred = predecessors.length > 0;
  const hasSucc = successors.length > 0;

  // Column x positions
  const predX   = PD;
  const centerX = PD + (hasPred ? NW + CG : 0);
  const succX   = centerX + NW + CG;

  // Column heights
  const predH  = predecessors.length * NH + Math.max(0, predecessors.length - 1) * RG;
  const succH  = successors.length   * NH + Math.max(0, successors.length   - 1) * RG;
  const totalH = Math.max(predH, succH, NH) + 2 * PD;

  // Top-y of each column (vertically centered)
  const predTopY   = (totalH - predH)  / 2;
  const succTopY   = (totalH - succH)  / 2;
  const centerTopY = (totalH - NH)     / 2;

  // Total canvas width
  const totalW = centerX + NW + (hasSucc ? CG + NW : 0) + PD;

  const centerMidY = centerTopY + NH / 2;

  function bezier(x1: number, y1: number, x2: number, y2: number) {
    const mx = (x1 + x2) / 2;
    return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
  }

  return (
    <div style={{ position: 'relative', width: totalW, height: totalH, minWidth: totalW }}>
      {/* SVG arrow overlay */}
      <svg
        width={totalW} height={totalH}
        style={{ position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none' }}
      >
        <defs>
          <marker id="cfd-arr-pre" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
            <path d="M0,0 L7,2.5 L0,5 Z" fill="#f97316" />
          </marker>
          <marker id="cfd-arr-nxt" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
            <path d="M0,0 L7,2.5 L0,5 Z" fill="#22c55e" />
          </marker>
        </defs>

        {predecessors.map((_, i) => {
          const midY = predTopY + i * (NH + RG) + NH / 2;
          return (
            <path key={`pa${i}`}
              d={bezier(predX + NW, midY, centerX, centerMidY)}
              stroke="#f97316" strokeWidth="1.5" fill="none"
              strokeDasharray="5,3" markerEnd="url(#cfd-arr-pre)"
            />
          );
        })}

        {successors.map((_, i) => {
          const midY = succTopY + i * (NH + RG) + NH / 2;
          return (
            <path key={`sa${i}`}
              d={bezier(centerX + NW, centerMidY, succX, midY)}
              stroke="#22c55e" strokeWidth="1.5" fill="none"
              markerEnd="url(#cfd-arr-nxt)"
            />
          );
        })}
      </svg>

      {/* Predecessor nodes */}
      {hasPred && predecessors.map((p, i) => (
        <button
          key={p.cert_id} type="button"
          style={{ position: 'absolute', top: predTopY + i * (NH + RG), left: predX, width: NW, height: NH }}
          className="cfd-node cfd-node-pre"
          onClick={() => onNodeClick(p.cert_id, p.cert_name)}
        >
          {p.relation_label && <span className="cfd-rel">{p.relation_label}</span>}
          <span className="cfd-name">{p.cert_name}</span>
        </button>
      ))}

      {/* Current node */}
      <div
        style={{ position: 'absolute', top: centerTopY, left: centerX, width: NW, height: NH }}
        className="cfd-node cfd-node-cur"
      >
        <span className="cfd-rel cfd-cur-lbl">현재 선택</span>
        <span className="cfd-name">{current.cert_name}</span>
      </div>

      {/* Successor nodes */}
      {hasSucc && successors.map((s, i) => (
        <button
          key={s.cert_id} type="button"
          style={{ position: 'absolute', top: succTopY + i * (NH + RG), left: succX, width: NW, height: NH }}
          className="cfd-node cfd-node-nxt"
          onClick={() => onNodeClick(s.cert_id, s.cert_name)}
        >
          {s.relation_label && <span className="cfd-rel">{s.relation_label}</span>}
          <span className="cfd-name">{s.cert_name}</span>
        </button>
      ))}

      <style>{`
        .cfd-node {
          display: flex; flex-direction: column; align-items: flex-start; justify-content: center;
          padding: .3rem .55rem; border-radius: 6px; border: 1.5px solid;
          overflow: hidden; text-align: left;
        }
        .cfd-node-pre {
          background: #fff7ed; border-color: rgba(249,115,22,.45); cursor: pointer;
          transition: background .15s, border-color .15s;
        }
        .cfd-node-pre:hover { background: #ffedd5; border-color: #f97316; }
        .cfd-node-nxt {
          background: #f0fdf4; border-color: rgba(34,197,94,.45); cursor: pointer;
          transition: background .15s, border-color .15s;
        }
        .cfd-node-nxt:hover { background: #dcfce7; border-color: #22c55e; }
        .cfd-node-cur {
          background: var(--primary-light); border-color: var(--primary);
          box-shadow: 0 0 0 3px rgba(99,102,241,.12); cursor: default;
        }
        .cfd-rel {
          font-size: .58rem; font-weight: 700; letter-spacing: .05em;
          line-height: 1; opacity: .8;
        }
        .cfd-node-pre .cfd-rel { color: #c2410c; }
        .cfd-node-nxt .cfd-rel { color: #15803d; }
        .cfd-cur-lbl { color: var(--primary); opacity: .9; }
        .cfd-name {
          font-size: .77rem; font-weight: 600; color: var(--text);
          overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
          width: 100%; margin-top: .2rem; line-height: 1.25;
        }
        .cfd-node-cur .cfd-name { color: var(--primary); font-weight: 700; }
      `}</style>
    </div>
  );
};
