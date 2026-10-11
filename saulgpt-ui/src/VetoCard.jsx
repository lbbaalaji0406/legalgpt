import { useState, useEffect } from "react";
import "./VetoCard.css";

export default function VetoCard({ scrutiny, deliberation, onAcknowledge, onAction, logEvent }) {
  const [acknowledged, setAcknowledged] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [activeRubric, setActiveRubric] = useState("ALL");

  const hasScrutiny = Boolean(scrutiny && (scrutiny.veto_message || scrutiny.warnings?.length > 0));
  const hasDeliberation = Boolean(deliberation && Array.isArray(deliberation.audit_trail) && deliberation.audit_trail.length > 0);

  // Telemetry Mount
  useEffect(() => {
    if (logEvent) {
      if (hasScrutiny) {
        logEvent("veto_card_shown", { severity: scrutiny.severity, warnings: scrutiny.warnings?.length });
      }
      if (hasDeliberation) {
        logEvent("deliberation_inspector_shown", { score: deliberation.process_reward_score });
      }
    }
  }, [hasScrutiny, hasDeliberation, scrutiny, deliberation, logEvent]);

  if (!hasScrutiny && !hasDeliberation) return null;

  const severity = scrutiny?.severity || (deliberation && !deliberation.pass_verdict ? "warning" : "info");
  const canProceed = scrutiny?.can_proceed !== false;
  
  const warnings = Array.isArray(scrutiny?.warnings) ? scrutiny.warnings : [];
  const remappedLaws = scrutiny?.remapped_laws && typeof scrutiny.remapped_laws === 'object' ? scrutiny.remapped_laws : {};

  const cfg = {
    serious: { icon: "🚨", title: "SERIOUS LEGAL CONCERNS", cls: "veto-serious", accentColor: "var(--accent-red, #C44A4A)" },
    warning: { icon: "⚠️", title: "LEGAL SCRUTINY & REVISION", cls: "veto-warning", accentColor: "var(--gold, #C9A84C)" },
    info: { icon: "⚖️", title: "ADVERSARIAL DELIBERATION INSPECTOR", cls: "veto-info", accentColor: "var(--accent-teal, #7EB8C4)" },
  }[severity] || { icon: "⚖️", title: "ADVERSARIAL DELIBERATION INSPECTOR", cls: "veto-info", accentColor: "var(--accent-teal, #7EB8C4)" };

  const limitationWarning = warnings.find(w => w && w.toUpperCase().includes("LIMITATION"));
  const remedyWarning = warnings.find(w => w && w.toUpperCase().includes("REMEDY"));
  const lawWarning = warnings.find(w => w && (w.toUpperCase().includes("LAW UPDATE") || w.toUpperCase().includes("BNS")));
  const otherWarnings = warnings.filter(w => w !== limitationWarning && w !== remedyWarning && w !== lawWarning);

  // Safe string parser for bold and line breaks
  function renderSafeWarning(text) {
    if (!text) return null;
    const parts = text.split(/\*\*(.*?)\*\*/g);
    
    return (
      <p className="veto-text">
        {parts.map((part, index) => {
          if (index % 2 === 1) return <strong key={index}>{part}</strong>;
          return (
            <span key={index}>
              {part.split('\n').map((line, i, arr) => (
                <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
              ))}
            </span>
          );
        })}
      </p>
    );
  }

  const handleCheckbox = (e) => {
    const isChecked = e.target.checked;
    setAcknowledged(isChecked);
    if (onAcknowledge) onAcknowledge(isChecked);
  };

  const concordancePct = deliberation?.concordance_percentage ?? 95;
  const auditTrail = deliberation?.audit_trail || [];
  const filteredAudit = activeRubric === "ALL" 
    ? auditTrail 
    : auditTrail.filter(a => a.rubric_dimension === activeRubric);

  return (
    <div className={`veto-card ${cfg.cls} deliberation-card`}>
      {/* Header with Title and Concordance Badge */}
      <button 
        className="veto-header" 
        onClick={() => setCollapsed(c => !c)}
        aria-expanded={!collapsed}
        tabIndex={0}
      >
        <div className="veto-header-left">
          <span className={`veto-icon ${severity === "serious" ? "veto-pulse" : ""}`}>{cfg.icon}</span>
          <span className="veto-title" style={{ color: cfg.accentColor }}>{cfg.title}</span>
        </div>

        <div className="veto-header-right">
          {hasDeliberation && (
            <span className={`concordance-badge ${concordancePct >= 85 ? "concordance-high" : concordancePct >= 70 ? "concordance-mid" : "concordance-low"}`}>
              {concordancePct}% Bare Act Concordance
            </span>
          )}
          <span className="veto-collapse">{collapsed ? "▼" : "▲"}</span>
        </div>
      </button>

      {!collapsed && (
        <div className="veto-body">
          {/* Pre-Draft Scrutiny Warnings (if any) */}
          {limitationWarning && (
            <div className="veto-section">
              <span className="veto-subtitle">📅 Limitation Act 1963</span>
              {renderSafeWarning(limitationWarning)}
            </div>
          )}
          {remedyWarning && (
            <div className="veto-section">
              <span className="veto-subtitle">⚖️ Remedy Not Recognized</span>
              {renderSafeWarning(remedyWarning)}
            </div>
          )}
          {lawWarning && (
            <div className="veto-section">
              <span className="veto-subtitle">📜 Law Updated — BNS/BNSS 2023</span>
              {renderSafeWarning(lawWarning)}
            </div>
          )}
          {otherWarnings.map((w, i) => (
            <div key={i} className="veto-section">{renderSafeWarning(w)}</div>
          ))}
          {!warnings.length && scrutiny?.veto_message && (
            <div className="veto-section">{renderSafeWarning(scrutiny.veto_message)}</div>
          )}

          {/* Bare Act Remapped Laws */}
          {Object.keys(remappedLaws).length > 0 && (
            <div className="veto-remapped">
              <span className="veto-remap-title">⚖️ AUTO-CORRECTIONS APPLIED:</span>
              <div className="veto-remap-list">
                {Object.entries(remappedLaws).map(([old, nw], i) => (
                  <span key={i} className="veto-remap-pill"><s>{old}</s> → <strong>{nw}</strong></span>
                ))}
              </div>
            </div>
          )}

          {/* Actor-Critic PRM Deliberation Section */}
          {hasDeliberation && (
            <div className="deliberation-container">
              {/* Reflexive Self-Correction / Rescue Banner */}
              {(deliberation.corrections_made > 0 || auditTrail.some(a => a.is_rescued)) && (
                <div className="self-healing-banner">
                  <span className="self-healing-icon">⚡</span>
                  <span className="self-healing-text">
                    <strong>Autonomous Reflexive Repair:</strong> Adversarial Critic intercepted and verified claims directly against Bare Acts in ChromaDB.
                  </span>
                </div>
              )}

              {/* Rubric Filter Tabs */}
              <div className="rubric-filter-tabs">
                {["ALL", "CANONICAL_CONCORDANCE", "DEONTIC_MODALITY", "PROCEDURAL_DEADLINES", "CONDITIONAL_PROVISOS"].map(rubric => (
                  <button
                    key={rubric}
                    className={`rubric-chip ${activeRubric === rubric ? "active" : ""}`}
                    onClick={() => setActiveRubric(rubric)}
                  >
                    {rubric === "ALL" ? "All Rubrics" : rubric.replace(/_/g, " ").toLowerCase()}
                  </button>
                ))}
              </div>

              {/* Audited Claims List */}
              <div className="audit-claims-list">
                {filteredAudit.map((item, idx) => (
                  <div key={idx} className={`audit-claim-item ${item.pass_verdict ? "claim-valid" : "claim-invalid"}`}>
                    <div className="claim-item-header">
                      <span className="rubric-tag">{item.rubric_dimension?.replace(/_/g, " ")}</span>
                      <span className={`verdict-pill ${item.is_rescued ? "pill-rescued" : item.pass_verdict ? "pill-pass" : "pill-flagged"}`}>
                        {item.is_rescued ? "⚡ Rescued via ChromaDB" : item.pass_verdict ? "✓ Verified" : "⚠️ Vetoed / Contradicted"}
                      </span>
                    </div>

                    <div className="claim-span-text">
                      <em>"{item.substantive_claim_span}"</em>
                    </div>

                    {item.extracted_ground_truth && (
                      <div className="claim-grounding">
                        <span className="grounding-label">Statutory Grounding:</span> {item.extracted_ground_truth}
                      </div>
                    )}

                    {item.adversarial_reasoning && (
                      <div className="claim-reasoning">
                        <span className="reasoning-label">Judicial Review:</span> {item.adversarial_reasoning}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Actionable Callbacks */}
      {!collapsed && canProceed && hasScrutiny && (
        <div className="veto-footer">
          <label className="veto-checkbox">
            <input type="checkbox" checked={acknowledged} onChange={handleCheckbox} />
            <span>I understand these concerns and wish to proceed anyway</span>
          </label>
          {acknowledged && <span className="veto-ack">✓ Acknowledged — document drafted at your own risk</span>}
        </div>
      )}

      {!collapsed && !canProceed && severity === "serious" && (
        <div className="veto-footer veto-blocked">
          <span className="veto-blocked-msg">⛔ This matter requires resolution before a legal notice can be drafted.</span>
          <div className="veto-action-buttons">
            <button className="veto-btn primary" onClick={() => onAction && onAction('consult_human')}>Consult a Human Lawyer</button>
            <button className="veto-btn secondary" onClick={() => onAction && onAction('draft_general')}>Draft General Demand Letter</button>
          </div>
        </div>
      )}
    </div>
  );
}
