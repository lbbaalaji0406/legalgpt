import { useState, useEffect } from "react";
import axios from "axios";
import "./VirtualBench.css";

const API_BASE = "http://localhost:8000";

export default function VirtualBench({
  isOpen,
  onClose,
  initialMatter,
  connectedEvidence,
  onOpenEvidenceUploader
}) {
  const [matter, setMatter] = useState(initialMatter || "");
  const [targetRole, setTargetRole] = useState("adverse_witness"); // 'adverse_witness' | 'accused' | 'deposition_defense'
  const [activeEvidence, setActiveEvidence] = useState(connectedEvidence || null);
  const [loading, setLoading] = useState(false);
  const [trialData, setTrialData] = useState(null);
  const [error, setError] = useState(null);
  const [activeChainIndex, setActiveChainIndex] = useState(0);
  const [copiedStepKey, setCopiedStepKey] = useState(null);
  const [copiedShieldIndex, setCopiedShieldIndex] = useState(null);

  useEffect(() => {
    if (initialMatter) {
      setMatter(initialMatter);
    }
  }, [initialMatter]);

  useEffect(() => {
    if (connectedEvidence) {
      setActiveEvidence(connectedEvidence);
    }
  }, [connectedEvidence]);

  if (!isOpen) return null;

  const handleSimulate = async (roleOverride = null) => {
    const roleToUse = roleOverride || targetRole;
    if (!matter.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = await axios.post(`${API_BASE}/api/bench/debate`, {
        matter: matter,
        evidence_data: activeEvidence,
        target_role: roleToUse,
      });
      setTrialData(res.data);
      setActiveChainIndex(0);
    } catch (err) {
      console.error("Trial Stand error:", err);
      setError(err.response?.data?.detail || "Failed to convene trial stand cross-examination.");
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = (newRole) => {
    setTargetRole(newRole);
    if (matter.trim() && trialData) {
      handleSimulate(newRole);
    }
  };

  const copyToClipboard = (text, key, isShield = false) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    if (isShield) {
      setCopiedShieldIndex(key);
      setTimeout(() => setCopiedShieldIndex(null), 2000);
    } else {
      setCopiedStepKey(key);
      setTimeout(() => setCopiedStepKey(null), 2000);
    }
  };

  const handleClearEvidence = () => {
    setActiveEvidence(null);
  };

  const chains = trialData?.question_chains || [];
  const activeChain = chains[activeChainIndex] || chains[0];
  const witness = trialData?.witness_profile;
  const grounding = trialData?.evidence_grounding;
  const shield = trialData?.protective_shield;
  const judicial = trialData?.judicial_assessment;

  return (
    <div className="bench-modal-overlay" onClick={onClose}>
      <div className="bench-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="bench-modal-header">
          <div className="bench-title-wrap">
            <span className="bench-gavel-icon">🏛️</span>
            <div>
              <h3>Virtual Witness Stand & Trial Cross-Examiner</h3>
              <p className="bench-sub">
                Bharatiya Sakshya Adhiniyam, 2023 (Sec. 141-157) · Presumption Rebuttal (Sec. 139 NI Act)
              </p>
            </div>
          </div>
          <button className="bench-close-btn" onClick={onClose} title="Close Trial Stand">✕</button>
        </div>

        <div className="bench-modal-body">
          {/* Strategy Mode Selector */}
          <div className="trial-mode-selector">
            <button
              className={`trial-mode-btn ${targetRole === "adverse_witness" ? "active" : ""}`}
              onClick={() => handleRoleChange("adverse_witness")}
            >
              ⚔️ Cross-Examine Complainant / Adverse Witness
            </button>
            <button
              className={`trial-mode-btn ${targetRole === "accused" ? "active" : ""}`}
              onClick={() => handleRoleChange("accused")}
            >
              🎯 Cross-Examine Accused / Drawer
            </button>
            <button
              className={`trial-mode-btn ${targetRole === "deposition_defense" ? "active" : ""}`}
              onClick={() => handleRoleChange("deposition_defense")}
            >
              🛡️ Evidence Affidavit Insulation
            </button>
          </div>

          {/* Evidence Foundation Connection Card */}
          <div className="evidence-foundation-banner">
            <div className="foundation-left">
              <span className="foundation-icon">🛡️</span>
              <div className="foundation-details">
                <span className="foundation-label">CONNECTED EVIDENTIARY RECORD:</span>
                {activeEvidence ? (
                  <div className="active-evidence-pill-row">
                    <span className="evidence-type-badge">
                      {activeEvidence.evidence_type === "audio" ? "🎙️ Voice Recording / Admission" : "🧾 Cheque Leaf / Return Memo"}
                    </span>
                    {activeEvidence.sha256_hash && (
                      <span className="evidence-hash-tag" title={activeEvidence.sha256_hash}>
                        SHA-256: {activeEvidence.sha256_hash.slice(0, 10)}...{activeEvidence.sha256_hash.slice(-6)}
                      </span>
                    )}
                    {activeEvidence.statutory_clock?.dishonour_reason && (
                      <span className="evidence-stat-tag">
                        {activeEvidence.statutory_clock.dishonour_reason}
                      </span>
                    )}
                    {activeEvidence.forensic_admission?.debtor_statement && (
                      <span className="evidence-stat-tag" title={activeEvidence.forensic_admission.debtor_statement}>
                        Voice: "{activeEvidence.forensic_admission.debtor_statement.slice(0, 30)}..."
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="no-evidence-text">
                    No physical evidence connected yet. Operating in theoretical cross-examination mode.
                  </span>
                )}
              </div>
            </div>

            <div className="foundation-right">
              {activeEvidence ? (
                <button className="evidence-ctrl-btn detach" onClick={handleClearEvidence} title="Detach Evidence">
                  ✕ Detach
                </button>
              ) : (
                onOpenEvidenceUploader && (
                  <button className="evidence-ctrl-btn attach" onClick={onOpenEvidenceUploader}>
                    + Attach Uploaded Evidence
                  </button>
                )
              )}
            </div>
          </div>

          {/* Controversy Input Bar */}
          <div className="bench-input-section">
            <label className="bench-input-label">Case Controversy & Factual Matrix:</label>
            <div className="bench-input-row">
              <input
                type="text"
                className="bench-matter-input"
                value={matter}
                onChange={(e) => setMatter(e.target.value)}
                placeholder="e.g. Dishonoured cheque of Rs 10 Lakhs with memo 'Funds Insufficient'. Accused claims blank security cheque given in 2022..."
              />
              <button
                className="bench-simulate-btn"
                onClick={() => handleSimulate()}
                disabled={loading || !matter.trim()}
              >
                {loading ? "Constructing Interrogation Chains..." : "Convene Trial Stand ⚖️"}
              </button>
            </div>
          </div>

          {error && <div className="bench-error-banner">🚨 {error}</div>}

          {/* Trial Examination Workspace */}
          {trialData && (
            <div className="trial-workspace">
              {/* Case Metadata Banner */}
              <div className="courtroom-meta-banner">
                <div className="courtroom-case-title">
                  <span className="courtroom-seal">⚖️</span>
                  <div>
                    <h4>{trialData.case_title}</h4>
                    <span className="court-forum-tag">{trialData.court_type || "Competent Trial Court"}</span>
                  </div>
                </div>
                <div className="courtroom-controls">
                  <span className="statute-badge">{trialData.statute_focus}</span>
                </div>
              </div>

              {/* Witness Credibility & Contradiction Scorecard */}
              {witness && (
                <div className="witness-scorecard-card">
                  <div className="scorecard-header">
                    <div className="witness-info">
                      <span className="witness-avatar">👤</span>
                      <div>
                        <span className="witness-title">WITNESS UNDER CROSS-EXAMINATION</span>
                        <h4 className="witness-name">{witness.name}</h4>
                        <span className="witness-role">{witness.role}</span>
                      </div>
                    </div>

                    <div className="vulnerability-metric-box">
                      <div className="metric-score-wrap">
                        <span className="metric-score">{witness.credibility_score}%</span>
                        <span className="metric-label">Credibility Baseline</span>
                      </div>
                      <span className="vulnerability-badge high">
                        {witness.risk_level || "Critical Vulnerability"}
                      </span>
                    </div>
                  </div>

                  {witness.statutory_bars?.length > 0 && (
                    <div className="statutory-bars-tray">
                      <span className="bars-title">⚠️ FATAL STATUTORY VULNERABILITIES IDENTIFIED:</span>
                      <div className="bars-list">
                        {witness.statutory_bars.map((bar, idx) => (
                          <div key={idx} className="statutory-bar-item">
                            <span className="bar-icon">⚡</span>
                            <span>{bar}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Sequential Interrogation Chains */}
              {chains.length > 0 && (
                <div className="interrogation-chains-section">
                  <div className="chains-tab-bar">
                    <span className="chains-label">INTERROGATION LINES:</span>
                    {chains.map((c, idx) => (
                      <button
                        key={idx}
                        className={`chain-tab-btn ${activeChainIndex === idx ? "active" : ""}`}
                        onClick={() => setActiveChainIndex(idx)}
                      >
                        Line {idx + 1}: {c.theme?.split(":")[1]?.trim() || c.theme || `Strategy ${idx + 1}`}
                      </button>
                    ))}
                  </div>

                  {activeChain && (
                    <div className="active-chain-container">
                      <div className="chain-strategy-header">
                        <div className="chain-theme-title">
                          <span className="chain-tag">THEME</span>
                          <h3>{activeChain.theme}</h3>
                        </div>
                        <p className="chain-summary-text">{activeChain.strategy_summary}</p>
                      </div>

                      {/* 4 Progressive Steps */}
                      <div className="chain-steps-stack">
                        {activeChain.steps?.map((step, sIdx) => {
                          const stepKey = `${activeChainIndex}-${sIdx}`;
                          const isCopied = copiedStepKey === stepKey;

                          return (
                            <div key={sIdx} className={`interrogation-step-card stage-${step.step_number || sIdx + 1}`}>
                              <div className="step-card-header">
                                <div className="step-badge-wrap">
                                  <span className="step-number-pill">STEP {step.step_number || sIdx + 1}</span>
                                  <span className="step-stage-name">{step.stage_type}</span>
                                </div>
                                <button
                                  className="copy-step-btn"
                                  onClick={() => copyToClipboard(step.question, stepKey)}
                                  title="Copy leading question for courtroom use"
                                >
                                  {isCopied ? "✓ Question Copied" : "📋 Copy Question"}
                                </button>
                              </div>

                              {/* Leading Question */}
                              <div className="leading-question-box">
                                <span className="question-quote-icon">“</span>
                                <p className="leading-question-text">{step.question}</p>
                              </div>

                              {/* Strategic Breakdown Grid */}
                              <div className="step-meta-grid">
                                <div className="meta-block grounding">
                                  <span className="block-title">📚 PRIOR KNOWLEDGE GROUNDED:</span>
                                  <p>{step.prior_knowledge_grounding}</p>
                                </div>

                                <div className="meta-block expected">
                                  <span className="block-title">🎯 ANTICIPATED WITNESS REACTION:</span>
                                  <p>{step.expected_answer}</p>
                                </div>
                              </div>

                              <div className="step-tactics-row">
                                <div className="tactic-item notes">
                                  <strong>⚖️ Advocate Strategy:</strong> {step.advocate_notes}
                                </div>
                                {step.pivot_if_hedged && (
                                  <div className="tactic-item pivot">
                                    <strong>⚡ Pivot if Witness Evades:</strong> {step.pivot_if_hedged}
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Protective Examination-in-Chief Shield */}
              {shield && shield.clauses?.length > 0 && (
                <div className="protective-shield-section">
                  <div className="shield-section-header">
                    <span className="shield-icon">🛡️</span>
                    <div>
                      <h3>{shield.title || "Examination-in-Chief Insulation (Proof Affidavit)"}</h3>
                      <p>{shield.guidance}</p>
                    </div>
                  </div>

                  <div className="shield-clauses-grid">
                    {shield.clauses.map((c, cIdx) => (
                      <div key={cIdx} className="shield-clause-card">
                        <div className="shield-card-head">
                          <span className="risk-target-pill">Target Risk: {c.target_risk}</span>
                          <button
                            className="copy-clause-btn"
                            onClick={() => copyToClipboard(c.shield_clause, cIdx, true)}
                          >
                            {copiedShieldIndex === cIdx ? "✓ Copied" : "📋 Copy Clause"}
                          </button>
                        </div>
                        <p className="clause-text">"{c.shield_clause}"</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Judicial Ruling & Landmark Precedents */}
              {judicial && (
                <div className="judicial-assessment-card">
                  <div className="judicial-header">
                    <span className="judge-icon">🏛️</span>
                    <div>
                      <span className="judicial-subtitle">{judicial.presiding_judge || "Hon'ble Presiding Magistrate"}</span>
                      <h4>Probative Impact & Trial Assessment</h4>
                    </div>
                  </div>

                  <p className="judicial-ruling-text">{judicial.ruling_impact}</p>

                  {judicial.key_precedents?.length > 0 && (
                    <div className="precedents-box">
                      <span className="precedents-label">BINDING SUPREME COURT PRECEDENTS:</span>
                      <ul className="precedents-list">
                        {judicial.key_precedents.map((p, pIdx) => (
                          <li key={pIdx}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
