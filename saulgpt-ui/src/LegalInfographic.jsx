import { useState } from "react";
import "./LegalInfographic.css";

export default function LegalInfographic({ data }) {
  const [expanded, setExpanded] = useState(true);

  if (!data) return null;

  const isDecisionTree = data.type === "decision_tree";

  return (
    <div className="legal-infographic-card">
      <div className="infographic-header" onClick={() => setExpanded(!expanded)}>
        <div className="infographic-title-wrap">
          <span className="infographic-glyph">📊</span>
          <div>
            <h4 className="infographic-title">{data.title}</h4>
            <span className="infographic-statute">{data.statute}</span>
          </div>
        </div>
        <button className="infographic-collapse-btn">
          {expanded ? "▲" : "▼"}
        </button>
      </div>

      {expanded && (
        <div className="infographic-body">
          {/* Root Trigger Node */}
          {data.root && (
            <div className="infographic-root-node">
              <span className="root-badge">{data.root.badge}</span>
              <div className="root-title">{data.root.title}</div>
              <div className="root-desc">{data.root.desc}</div>
              <div className="root-connector-line">
                <span className="down-arrow">▼</span>
              </div>
            </div>
          )}

          {/* Decision Tree Branch Cards */}
          {isDecisionTree && (
            <div className="decision-tree-grid">
              {data.nodes.map((node, i) => (
                <div key={i} className="decision-branch-card" style={{ borderTopColor: node.color || "#C9A84C" }}>
                  <div className="branch-head">
                    <span className="branch-badge" style={{ color: node.color, borderColor: `${node.color}55` }}>
                      {node.status_badge}
                    </span>
                    <h5 className="branch-title">{node.title}</h5>
                  </div>

                  <div className="branch-specs">
                    <div className="spec-item">
                      <span className="spec-label">Qualifying Asset:</span>
                      <span className="spec-val">{node.target_asset}</span>
                    </div>
                    <div className="spec-item">
                      <span className="spec-label">Reinvestment Window:</span>
                      <span className="spec-val highlight">{node.time_limit}</span>
                    </div>
                    <div className="spec-item">
                      <span className="spec-label">Statutory Ceiling:</span>
                      <span className="spec-val cap">{node.statutory_cap}</span>
                    </div>
                    <div className="spec-item">
                      <span className="spec-label">Permitted Investment:</span>
                      <span className="spec-val">{node.eligible_investment}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Statutory Transition Matrix (IPC -> BNS) */}
          {!isDecisionTree && (
            <div className="transition-matrix-grid">
              {data.nodes.map((node, i) => (
                <div key={i} className="transition-row-card">
                  <div className="transition-offence-head">
                    <h5>{node.title}</h5>
                  </div>
                  <div className="transition-law-compare">
                    <div className="law-box legacy">
                      <span className="law-type">REPEALED CODE</span>
                      <span className="law-sec">{node.legacy_law}</span>
                    </div>
                    <span className="transition-arrow">➔</span>
                    <div className="law-box enacted">
                      <span className="law-type">ENACTED SANHITA</span>
                      <span className="law-sec">{node.enacted_law}</span>
                    </div>
                  </div>
                  <div className="transition-specs">
                    <div><strong>Punishment:</strong> {node.punishment}</div>
                    <div><strong>Statutory Reform:</strong> {node.key_change}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Provisos & Statutory Safeguards */}
          {data.provisos?.length > 0 && (
            <div className="infographic-provisos-box">
              <span className="proviso-header">⚖️ STATUTORY CONDITIONS & PROVISOS:</span>
              <ul>
                {data.provisos.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
