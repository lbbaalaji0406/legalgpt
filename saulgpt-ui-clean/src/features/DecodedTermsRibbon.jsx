import React, { useState } from "react";
import { scanForTerms } from "./LegalGlossary";
import "./DecodedTermsRibbon.css";

export default function DecodedTermsRibbon({ content }) {
  const [activeModalTerm, setActiveModalTerm] = useState(null);

  if (!content) return null;

  // Scan content for terms
  const termsFound = scanForTerms(content);
  if (!termsFound || termsFound.length === 0) return null;

  return (
    <div className="decoded-terms-container">
      {/* ── KEY TERMS DECODED RIBBON ── */}
      <div className="terms-ribbon-card">
        <div className="ribbon-header">
          <div className="ribbon-title-box">
            <span className="ribbon-sparkle">📖</span>
            <span className="ribbon-title">
              Legal Glossary & Concept Decoder ({termsFound.length} terms found):
            </span>
          </div>
          <span className="ribbon-hint">Click any term for everyday meaning & simple analogy</span>
        </div>

        <div className="terms-chips-flex">
          {termsFound.slice(0, 8).map((item, idx) => (
            <button
              key={idx}
              className="term-chip"
              onClick={() => setActiveModalTerm(item)}
              title={`Click to decode "${item.term}"`}
            >
              <span className="chip-term-text">{item.term}</span>
              <span className="chip-info-icon">💡</span>
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
              <button className="close-modal-btn" onClick={() => setActiveModalTerm(null)} title="Close">
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
                  <span className="section-label">🎯 REAL-WORLD EVERYDAY ANALOGY:</span>
                  <p className="analogy-text">"{activeModalTerm.analogy}"</p>
                </div>
              )}

              {/* Formal Courtroom Definition — rendered only when distinct to prevent duplicates */}
              {activeModalTerm.def &&
                activeModalTerm.def.trim() !== (activeModalTerm.simple_def || "").trim() && (
                  <div className="modal-section formal-def-box">
                    <span className="section-label">📜 FORMAL COURTROOM DEFINITION:</span>
                    <p>{activeModalTerm.def}</p>
                  </div>
                )}

              {/* Statutory Source */}
              {activeModalTerm.src && (
                <div className="modal-footer-source">
                  <span>Governing Law / Doctrine:</span>
                  <strong>{activeModalTerm.src}</strong>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
