import { useState } from "react";
import "./ToulminMatrix.css";

export default function ToulminMatrix({ matrix }) {
  const [activeNode, setActiveNode] = useState("all");

  if (!matrix || (!matrix.claim && !matrix.warrant)) return null;

  const nodes = [
    { id: "claim", title: "1. Judicial Claim", icon: "🎯", desc: "Substantive Relief Sought", content: matrix.claim },
    { id: "grounds", title: "2. Evidentiary Grounds", icon: "📑", desc: "Factual Foundations", content: matrix.grounds },
    { id: "warrant", title: "3. Statutory Warrant", icon: "📜", desc: "Legislative Bridge", content: matrix.warrant },
    { id: "backing", title: "4. Judicial Backing", icon: "🏛️", desc: "Precedent Authority", isBacking: true },
    { id: "rebuttal", title: "5. Adversarial Rebuttal", icon: "🛡️", desc: "Counter-Arguments and Rejoinder", content: matrix.rebuttal }
  ];

  const backingList = Array.isArray(matrix.backing) ? matrix.backing : [];

  return (
    <div className="toulmin-matrix-card">
      <div className="toulmin-header">
        <div className="toulmin-title-group">
          <span className="toulmin-icon">⚖️</span>
          <div>
            <h3 className="toulmin-title">TOULMIN COMPUTATIONAL ARGUMENTATION MATRIX</h3>
            <p className="toulmin-subtitle">Formal 5-Node Jurisprudential Proof Graph (Stephen Toulmin Model)</p>
          </div>
        </div>
      </div>

      {/* 5-Node Interactive Navigation Bar */}
      <div className="toulmin-node-nav">
        {nodes.map(n => (
          <button
            key={n.id}
            className={`toulmin-node-btn ${activeNode === n.id ? "active" : ""}`}
            onClick={() => setActiveNode(activeNode === n.id ? "all" : n.id)}
          >
            <span className="node-btn-icon">{n.icon}</span>
            <span className="node-btn-label">{n.title.split(". ")[1]}</span>
          </button>
        ))}
      </div>

      {/* Grid of Nodes */}
      <div className="toulmin-grid">
        {/* Node 1: Claim */}
        {(activeNode === "all" || activeNode === "claim") && (
          <div className="toulmin-node node-claim">
            <div className="node-header">
              <span className="node-icon">🎯</span>
              <span className="node-name">CLAIM / RELIEF SOUGHT</span>
            </div>
            <div className="node-body">{matrix.claim}</div>
          </div>
        )}

        {/* Node 2: Grounds */}
        {(activeNode === "all" || activeNode === "grounds") && (
          <div className="toulmin-node node-grounds">
            <div className="node-header">
              <span className="node-icon">📑</span>
              <span className="node-name">FACTUAL GROUNDS & DATA</span>
            </div>
            <div className="node-body">{matrix.grounds}</div>
          </div>
        )}

        {/* Node 3: Statutory Warrant */}
        {(activeNode === "all" || activeNode === "warrant") && (
          <div className="toulmin-node node-warrant">
            <div className="node-header">
              <span className="node-icon">📜</span>
              <span className="node-name">STATUTORY WARRANT</span>
            </div>
            <div className="node-body">{matrix.warrant}</div>
          </div>
        )}

        {/* Node 4: Judicial Backing (Precedents with DB Verification Check) */}
        {(activeNode === "all" || activeNode === "backing") && (
          <div className="toulmin-node node-backing">
            <div className="node-header">
              <span className="node-icon">🏛️</span>
              <span className="node-name">JUDICIAL BACKING (PRECEDENTS)</span>
            </div>
            <div className="node-body">
              {backingList.length > 0 ? (
                <div className="backing-list">
                  {backingList.map((b, i) => (
                    <div
                      key={i}
                      className={`backing-item ${b.is_verified_in_db ? "backing-verified" : "backing-unverified"}`}
                    >
                      <div className="backing-item-header">
                        <span className="backing-case-name"><strong>{b.case_name}</strong></span>
                        <span className={`backing-verification-badge ${b.is_verified_in_db ? "badge-verified" : "badge-unverified"}`}>
                          {b.is_verified_in_db ? "✓ Verified Precedent" : "⚠️ Theoretical Ratio - Unverified"}
                        </span>
                      </div>
                      {b.citation && <div className="backing-citation"><em>Citation: {b.citation}</em></div>}
                      {b.ratio && <div className="backing-ratio"><span className="ratio-label">Ratio:</span> {b.ratio}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="backing-empty">Direct statutory application. No extrinsic case law cited.</div>
              )}
            </div>
          </div>
        )}

        {/* Node 5: Adversarial Rebuttal */}
        {(activeNode === "all" || activeNode === "rebuttal") && (
          <div className="toulmin-node node-rebuttal">
            <div className="node-header">
              <span className="node-icon">🛡️</span>
              <span className="node-name">ADVERSARIAL REBUTTAL & REJOINDER</span>
            </div>
            <div className="node-body">{matrix.rebuttal}</div>
          </div>
        )}
      </div>
    </div>
  );
}
