import React, { useState } from "react";
import { scanForTerms } from "./LegalGlossary";
import "./DecodedTermsRibbon.css";

export default function DecodedTermsRibbon({ content, onToggleCitizenView, isCitizenView }) {
  const [activeModalTerm, setActiveModalTerm] = useState(null);

  if (!content) return null;

  // Scan content for terms
  const termsFound = scanForTerms(content);
  if (!termsFound || termsFound.length === 0) return null;

  return (
    <div className="decoded-terms-container">
      {/* ── TOP VIEW TOGGLE (ADVOCATE VS CITIZEN) ── */}
      <div className="view-mode-bar">
        <div className="bar-label">
          <span className="sparkle-icon">✦</span>
          <span>Legal Intelligence Dual-View:</span>
        </div>
        <div className="toggle-pill-group">
          <button
            className={`view-toggle-pill ${!isCitizenView ? "active-advocate" : ""}`}
            onClick={() => onToggleCitizenView(false)}
            title="Full Supreme Court citations, exact statutory clauses, and procedural trial mechanics"
          >
            ⚖️ Advocate View
          </button>
          <button
            className={`view-toggle-pill ${isCitizenView ? "active-citizen" : ""}`}
            onClick={() => onToggleCitizenView(true)}
            title="Plain everyday English with real-world analogies and simple action items"
          >
            🧑‍💼 Citizen View
          </button>
        </div>
      </div>

      {/* ── KEY TERMS DECODED RIBBON ── */}
      <div className="terms-ribbon-card">
        <div className="ribbon-header">
          <span className="ribbon-title">
            📖 Decoded in this response ({termsFound.length} legal terms):
          </span>
          <span className="ribbon-hint">Click any term for simple meaning & analogy</span>
        </div>

        <div className="terms-chips-flex">
          {termsFound.slice(0, 6).map((item, idx) => (
            <button
              key={idx}
              className="term-chip"
              onClick={() => setActiveModalTerm(item)}
            >
              <span className="chip-term-text">{item.term}</span>
              <span className="chip-info-icon">ℹ️</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── POPUP MODAL FOR DECODED TERM ── */}
      {activeModalTerm && (
        <div className="term-modal-backdrop" onClick={() => setActiveModalTerm(null)}>
          <div className="term-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="term-modal-header">
              <div className="modal-title-box">
                <span className="modal-category-badge">{activeModalTerm.category}</span>
                <h3>{activeModalTerm.term.toUpperCase()}</h3>
              </div>
              <button className="close-modal-btn" onClick={() => setActiveModalTerm(null)}>
                ✕
              </button>
            </div>

            <div className="term-modal-body">
              {/* Plain English Meaning */}
              <div className="modal-section simple-meaning-box">
                <span className="section-label">💡 PLAIN-ENGLISH MEANING:</span>
                <p>{activeModalTerm.simple_def || activeModalTerm.def}</p>
              </div>

              {/* Real World Analogy */}
              {activeModalTerm.analogy && (
                <div className="modal-section analogy-box">
                  <span className="section-label">🎯 REAL-WORLD ANALOGY:</span>
                  <p className="analogy-text">"{activeModalTerm.analogy}"</p>
                </div>
              )}

              {/* Formal Courtroom Definition */}
              <div className="modal-section formal-def-box">
                <span className="section-label">📜 FORMAL COURTROOM DEFINITION:</span>
                <p>{activeModalTerm.def}</p>
              </div>

              {/* Statutory Source */}
              <div className="modal-footer-source">
                <span>Governing Law / Doctrine:</span>
                <strong>{activeModalTerm.src}</strong>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
