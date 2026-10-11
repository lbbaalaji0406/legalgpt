import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./TrialStudio.css";

const API_BASE = "http://localhost:8000";

const CORE_ACTS = [
  { id: "all", label: "All 8 Acts Matrix", icon: "🏛️" },
  { id: "ni_act", label: "NI Act (Sec 138/139)", icon: "🖋️", actName: "Negotiable Instruments Act, 1881" },
  { id: "bns", label: "BNS / BNSS / BSA 2023", icon: "⚖️", actName: "Bharatiya Nyaya Sanhita, 2023" },
  { id: "cpa", label: "Consumer Protection (CPA 2019)", icon: "🛒", actName: "Consumer Protection Act, 2019" },
  { id: "contract", label: "Indian Contract Act", icon: "📜", actName: "Indian Contract Act, 1872" },
  { id: "limitation", label: "Limitation Act (Sec 18 Reset)", icon: "⏳", actName: "Limitation Act, 1963" },
  { id: "arbitration", label: "Arbitration Act (Sec 12/34)", icon: "🤝", actName: "Arbitration and Conciliation Act, 1996" }
];

export default function TrialStudio({
  sessionId,
  token,
  groundedEvidence,
  initialMatter,
  onBack,
  onAttachEvidence
}) {
  const [mode, setMode] = useState("moot_court"); // 'moot_court' | 'cross_examiner' | 'defense_fortifier'
  const [witnessRole, setWitnessRole] = useState("accused"); // 'accused' (Defense/Respondent) | 'complainant' (Prosecution/Plaintiff)
  const [copiedKey, setCopiedKey] = useState(null);
  const [selectedAct, setSelectedAct] = useState("all");
  const [scenario, setScenario] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);

  // Interrogation dialogue history (ONLY courtroom dialogue: interrogator & witness)
  const [turns, setTurns] = useState([]);
  const [witnessInput, setWitnessInput] = useState("");
  const [vulnerabilityScore, setVulnerabilityScore] = useState(35);
  const [vulnerabilityDelta, setVulnerabilityDelta] = useState(0);
  const [fatalFlaw, setFatalFlaw] = useState(null);
  const [controllingPrecedent, setControllingPrecedent] = useState(null);
  const [suggestedMotions, setSuggestedMotions] = useState([]);
  const [latestCoachAdvice, setLatestCoachAdvice] = useState(null);
  const [concludeData, setConcludeData] = useState(null);

  const interrogationEndRef = useRef(null);

  const handleCopy = (text, key) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // Dynamic persona titles and descriptions adapted for all legal domains
  const getPersonaDetails = () => {
    switch (selectedAct) {
      case "bns":
        return {
          role1: {
            title: "Accused (Facing Charges)",
            tag: "Defense Stand",
            tagClass: "tag-defense",
            icon: "🎯",
            desc: "You are the Accused facing criminal prosecution. Opposing counsel is the Public Prosecutor. Your Coach protects you against self-incrimination (Art 20(3)) and raises reasonable doubt (Sharad Birdhichand Sarda)."
          },
          role2: {
            title: "Prosecution / Complainant Witness",
            tag: "Proving Offence",
            tagClass: "tag-claimant",
            icon: "⚔️",
            desc: "You are the Complainant or Prosecution Witness proving the crime. Opposing counsel is the Defense Advocate attacking delay in FIR, police statement contradictions, and Sec 63 BSA compliance."
          }
        };
      case "cpa":
        return {
          role1: {
            title: "Opposite Party / Manufacturer",
            tag: "Defending Product/Service",
            tagClass: "tag-defense",
            icon: "🎯",
            desc: "You are the Company / Service Provider / Hospital. Opposing counsel represents the Consumer. Your Coach challenges the absence of mandatory Sec 38(2)(c) CPA laboratory testing reports."
          },
          role2: {
            title: "Complainant / Consumer",
            tag: "Asserting Defect/Deficiency",
            tagClass: "tag-claimant",
            icon: "⚔️",
            desc: "You are the aggrieved Consumer. Opposing counsel represents the Manufacturer. Your Coach fortifies repeated service job-cards, dealer admissions, and Sec 2(11) CPA deficiency of service."
          }
        };
      case "contract":
      case "limitation":
        return {
          role1: {
            title: "Defendant / Borrower",
            tag: "Defending Recovery/Damages",
            tagClass: "tag-defense",
            icon: "🎯",
            desc: "You are defending against a money suit or damages claim. Opposing counsel is the Plaintiff. Your Coach invokes Sec 25 Contract Act (void for want of consideration), lack of actual loss (Kailash Nath), or limitation bars."
          },
          role2: {
            title: "Plaintiff / Creditor",
            tag: "Asserting Breach/Claim",
            tagClass: "tag-claimant",
            icon: "⚔️",
            desc: "You are the Plaintiff seeking recovery or damages. Opposing counsel is the Defendant. Your Coach relies on signed written agreements, Sec 70/73 Contract Act, and certified bank ledgers."
          }
        };
      case "arbitration":
        return {
          role1: {
            title: "Respondent",
            tag: "Challenging Award/Claim",
            tagClass: "tag-defense",
            icon: "🎯",
            desc: "You are the Respondent in arbitral proceedings. Opposing counsel represents the Claimant. Your Coach challenges unilateral arbitrator appointments under Sec 12(5) (Perkins Eastman) and patent illegality under Sec 34."
          },
          role2: {
            title: "Claimant",
            tag: "Enforcing Contract/Award",
            tagClass: "tag-claimant",
            icon: "⚔️",
            desc: "You are the Claimant asserting liquidated damages and contract milestones. Opposing counsel represents the Respondent. Your Coach produces express written arbitral consent and project logs."
          }
        };
      case "ni_act":
      default:
        return {
          role1: {
            title: "Accused / Drawer",
            tag: "Defending Claim",
            tagClass: "tag-defense",
            icon: "🎯",
            desc: "You are defending against an alleged cheque bounce or debt. Opposing counsel represents the Complainant. Your Corner Coach provides Rangappa & Basalingappa rebuttals targeting lack of financial capacity."
          },
          role2: {
            title: "Complainant / Payee",
            tag: "Proving Debt",
            tagClass: "tag-claimant",
            icon: "⚔️",
            desc: "You are prosecuting/recovering money. Opposing counsel represents the Accused. Your Corner Coach arms you with Bir Singh statutory presumptions under Sec 139 NI Act."
          }
        };
    }
  };

  const personas = getPersonaDetails();

  // Auto-scroll courtroom chamber
  useEffect(() => {
    interrogationEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  // Seed default scenario if grounded evidence or initialMatter exists
  useEffect(() => {
    if (groundedEvidence) {
      const fn = groundedEvidence.filename || "Uploaded Evidence";
      const typ = groundedEvidence.evidence_type || groundedEvidence.file_type || "Commercial record";
      let desc = "";
      if (groundedEvidence.evidence_type === "audio") {
        const stmt = groundedEvidence.forensic_admission?.debtor_statement || "Debt acknowledged";
        desc = `Debtor voice admission in audio recording: "${stmt}". Extended limitation under Section 18 Limitation Act. Opposing party challenges voice authenticity, tampering, and Sec 63 BSA compliance.`;
        setSelectedAct("limitation");
      } else {
        const clock = groundedEvidence.statutory_clock || {};
        desc = `Dishonoured cheque of Rs. 15 Lakhs with bank return memo dated ${clock.bank_return_date || "recently"} for "${clock.dishonour_reason || "Funds Insufficient"}". Accused claims cheque was handed over as unfulfilled security.`;
        setSelectedAct("ni_act");
      }
      setScenario(desc);
      setSessionActive(false);
      setTurns([]);
      setFatalFlaw(null);
      setControllingPrecedent(null);
      setConcludeData(null);
      setLatestCoachAdvice(null);
    } else if (initialMatter) {
      setScenario(initialMatter);
    } else if (!scenario) {
      setScenario(
        "Cheque bounce matter for Rs. 15 Lakhs cash loan. Accused admits signature on cheque but disputes receipt of cash, alleging lack of Income Tax Returns and missing bank withdrawal slips."
      );
    }
  }, [groundedEvidence, initialMatter]);

  const handleStartSession = async () => {
    if (!scenario.trim()) return;
    setLoading(true);
    try {
      const actObj = CORE_ACTS.find((a) => a.id === selectedAct);
      const payload = {
        session_id: sessionId,
        scenario: scenario.trim(),
        act_hint: actObj?.actName || undefined,
        mode: mode,
        witness_role: witnessRole,
        grounded_evidence: groundedEvidence || undefined
      };

      const res = await axios.post(`${API_BASE}/api/trial/start`, payload);
      const data = res.data;

      setVulnerabilityScore(data.vulnerability_score);
      setVulnerabilityDelta(0);
      setFatalFlaw(data.fatal_flaw_detected);
      setControllingPrecedent(data.precedent_backing);
      setSuggestedMotions(data.suggested_statutory_motions || []);

      if (data.coach_advice) {
        setLatestCoachAdvice(data.coach_advice);
      }

      setTurns([
        {
          role: mode === "defense_fortifier" ? "fortifier" : "interrogator",
          content: data.interrogation_content,
          turn_index: 1,
          score: data.vulnerability_score
        }
      ]);
      setConcludeData(null);
      setSessionActive(true);
    } catch (err) {
      console.error("Failed to start trial session:", err);
      alert("Failed to connect to Precedent Engine. Ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const handleConcludeInterrogation = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/api/trial/conclude`, { session_id: sessionId });
      setConcludeData(res.data);
      setSessionActive(false);
    } catch (err) {
      console.error("Failed to conclude trial session:", err);
      setConcludeData({
        final_score: vulnerabilityScore,
        status_label: vulnerabilityScore >= 75 ? "FATAL EXPOSURE / STATUTORY CHECKMATE" : vulnerabilityScore >= 40 ? "CONTESTED TRIAL / BALANCED BURDEN" : "POSITION FORTIFIED / PRESUMPTION REBUTTED",
        status_color: getScoreColor(vulnerabilityScore),
        judicial_outlook: "Examination formally closed on the record. Proceed to file written submissions under Order 20 Rule 1 CPC / Section 353 BNSS.",
        admissions_on_record: [fatalFlaw].filter(Boolean),
        statutory_motions: suggestedMotions
      });
      setSessionActive(false);
    } finally {
      setLoading(false);
    }
  };

  const handleSendWitnessTurn = async () => {
    if (!witnessInput.trim() || loading) return;
    const answer = witnessInput.trim();
    setWitnessInput("");

    // Append witness turn locally in the courtroom chamber
    setTurns((prev) => [
      ...prev,
      { role: "witness", content: answer, turn_index: prev.length + 1 }
    ]);
    setLoading(true);

    try {
      const payload = {
        session_id: sessionId,
        witness_answer: answer,
        turn_index: turns.length + 1,
        witness_role: witnessRole,
        grounded_evidence: groundedEvidence || undefined
      };

      const res = await axios.post(`${API_BASE}/api/trial/turn`, payload);
      const data = res.data;

      setVulnerabilityScore(data.vulnerability_score);
      setVulnerabilityDelta(data.vulnerability_delta || 0);
      if (data.precedent_backing) setControllingPrecedent(data.precedent_backing);
      if (data.coach_advice) {
        setLatestCoachAdvice(data.coach_advice);
      }

      setTurns((prev) => [
        ...prev,
        {
          role: mode === "defense_fortifier" ? "fortifier" : "interrogator",
          content: data.interrogation_content,
          turn_index: prev.length + 1,
          score: data.vulnerability_score,
          delta: data.vulnerability_delta
        }
      ]);
    } catch (err) {
      console.error("Failed to process witness turn:", err);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 65) return "#ff4d4f"; // High danger (crimson)
    if (score >= 35) return "#faad14"; // Moderate warning (amber)
    return "#52c41a"; // Fortified (emerald)
  };

  return (
    <div className="trial-studio-container">
      {/* ── TOP CROWN JEWEL NAVIGATION ── */}
      <header className="trial-studio-header">
        <div className="header-left">
          <button className="back-btn" onClick={onBack}>
            ← Back to SaulGPT Chat
          </button>
          <div className="studio-brand">
            <span className="crown-jewel-badge">👑 DIAMOND PRE-TRIAL STUDIO</span>
            <h1>Adversarial Precedent Intelligence</h1>
          </div>
        </div>

        <div className="header-right">
          <div className="corpus-pill">
            <span className="live-dot" />
            <span>50,000+ Judgments & Trial Dossiers across 8 Acts</span>
          </div>
        </div>
      </header>

      {/* ── SHARED EVIDENCE RIBBON ── */}
      <div className="shared-evidence-ribbon">
        <div className="ribbon-info">
          <span className="ribbon-icon">🛡️</span>
          {groundedEvidence ? (
            <div className="ribbon-details">
              <strong>Active Grounded Evidence:</strong>{" "}
              <span className="evidence-fn">{groundedEvidence.filename || "Evidence Record"}</span>
              <span className="bsa-cert-tag">
                {groundedEvidence.sec63_bsa_certified ? "✓ Sec 63 BSA Certified" : "Hash Verified"}
              </span>
              {groundedEvidence.sha256_hash && (
                <span className="hash-chip">
                  SHA-256: {groundedEvidence.sha256_hash.slice(0, 12)}...
                </span>
              )}
              {groundedEvidence.statutory_clock?.days_remaining != null && (
                <span className="clock-chip">
                  ⏳ {groundedEvidence.statutory_clock.days_remaining} Days Remaining
                </span>
              )}
            </div>
          ) : (
            <div className="ribbon-details">
              <span>No evidence attached to active session. You can attach invoices, audio, or PDFs for full grounding.</span>
            </div>
          )}
        </div>
        <button className="attach-evidence-btn" onClick={onAttachEvidence}>
          + Attach / Scan Evidence
        </button>
      </div>

      {/* ── WORKSPACE SPLIT (Left: Courtroom Chamber | Right: Corner Coach & Precedents) ── */}
      <div className="trial-workspace">
        {/* ── LEFT COLUMN: COURTROOM & INTERROGATION CHAMBER ── */}
        <div className="trial-main-console">
          {/* Scenario Configuration Box */}
          <div className="scenario-card">
            <div className="card-top-row">
              <span className="section-title">1. Trial Setup & Persona Selection</span>
              <div className="mode-toggle-group">
                <button
                  className={`mode-toggle-btn moot-court ${mode === "moot_court" ? "active" : ""}`}
                  onClick={() => { setMode("moot_court"); setSessionActive(false); }}
                >
                  🥊 Dual Moot Court (With Coach)
                </button>
                <button
                  className={`mode-toggle-btn cross-exam ${mode === "cross_examiner" ? "active" : ""}`}
                  onClick={() => { setMode("cross_examiner"); setSessionActive(false); }}
                >
                  ⚔️ Solo Cross-Examiner
                </button>
                <button
                  className={`mode-toggle-btn defense ${mode === "defense_fortifier" ? "active" : ""}`}
                  onClick={() => { setMode("defense_fortifier"); setSessionActive(false); }}
                >
                  🛡️ Solo Defense Chambers
                </button>
              </div>
            </div>

            {/* Act Chips */}
            <div className="act-chips-row">
              {CORE_ACTS.map((act) => (
                <button
                  key={act.id}
                  className={`act-chip ${selectedAct === act.id ? "selected" : ""}`}
                  onClick={() => setSelectedAct(act.id)}
                >
                  <span className="chip-icon">{act.icon}</span>
                  <span>{act.label}</span>
                </button>
              ))}
            </div>

            {/* Dynamic Persona Selector Grid */}
            <div className="persona-selection-section">
              <span className="sub-label">SELECT YOUR ROLE ON THE WITNESS STAND:</span>
              <div className="persona-grid">
                <div
                  className={`persona-card ${witnessRole === "accused" ? "active" : ""}`}
                  onClick={() => { setWitnessRole("accused"); setSessionActive(false); }}
                >
                  <div className="persona-card-header">
                    <span className="persona-icon">{personas.role1.icon}</span>
                    <span className="persona-title">{personas.role1.title}</span>
                    <span className={`persona-tag ${personas.role1.tagClass}`}>{personas.role1.tag}</span>
                  </div>
                  <p className="persona-desc">{personas.role1.desc}</p>
                </div>

                <div
                  className={`persona-card ${witnessRole === "complainant" ? "active" : ""}`}
                  onClick={() => { setWitnessRole("complainant"); setSessionActive(false); }}
                >
                  <div className="persona-card-header">
                    <span className="persona-icon">{personas.role2.icon}</span>
                    <span className="persona-title">{personas.role2.title}</span>
                    <span className={`persona-tag ${personas.role2.tagClass}`}>{personas.role2.tag}</span>
                  </div>
                  <p className="persona-desc">{personas.role2.desc}</p>
                </div>
              </div>
            </div>

            <textarea
              className="scenario-input"
              rows={3}
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              placeholder="State the facts of the case, amount, evidence produced, and what the opponent claims..."
            />

            <div className="scenario-action-row">
              <span className="hint-text">
                {mode === "moot_court"
                  ? "🥊 Opposing counsel will cross-examine you on the stand while your Corner Coach on the right audits every answer and supplies real-time objections."
                  : mode === "cross_examiner"
                  ? "⚔️ Face continuous hostile leading interrogation under Section 146 BSA with zero assistance."
                  : "🛡️ Access pre-trial witness coaching brief, evidentiary checklist, and vulnerability audit."}
              </span>
              <button
                className="launch-adversarial-btn"
                onClick={handleStartSession}
                disabled={loading || !scenario.trim()}
              >
                {loading
                  ? "Analyzing 50k Precedents..."
                  : mode === "moot_court"
                  ? "⚡ Enter Moot Court Arena"
                  : mode === "cross_examiner"
                  ? "⚡ Launch Solo Cross-Examination"
                  : "⚡ Convene Defense Chambers"}
              </button>
            </div>
          </div>

          {/* Courtroom Interrogation Chamber */}
          <div className="courtroom-chamber">
            <div className="chamber-header">
              <div className="chamber-header-title-wrap">
                <span className="chamber-title">
                  {mode === "moot_court"
                    ? "🥊 Courtroom Interrogation Chamber"
                    : mode === "cross_examiner"
                    ? "⚔️ Witness Stand & Hostile Interrogation"
                    : "🛡️ Defense Fortification Chambers"}
                </span>
                <span className="role-stand-pill">
                  {witnessRole === "accused" ? `🎯 Stand: ${personas.role1.title}` : `⚔️ Stand: ${personas.role2.title}`}
                </span>
              </div>
              <div className="chamber-header-actions">
                {sessionActive && (
                  <>
                    <span className="turn-count-badge">Turn {turns.length}</span>
                    <button
                      className="rest-header-btn"
                      onClick={handleConcludeInterrogation}
                      disabled={loading}
                      title="Conclude Examination and Enter Final Record of Proceedings"
                    >
                      ⏹️ Rest Case / Conclude
                    </button>
                  </>
                )}
                {concludeData && (
                  <span className="concluded-badge">⚖️ Record Closed</span>
                )}
              </div>
            </div>

            <div className="chamber-messages">
              {turns.length === 0 ? (
                <div className="chamber-empty-state">
                  <div className="empty-icon">{mode === "moot_court" ? "🥊" : mode === "cross_examiner" ? "⚔️" : "🛡️"}</div>
                  <h3>{mode === "moot_court" ? "Ready for Moot Court Interrogation" : mode === "cross_examiner" ? "Ready for Hostile Cross-Examination" : "Ready for Defense Preparation"}</h3>
                  <p>
                    {mode === "moot_court"
                      ? "Set your scenario above and enter the arena. Opposing counsel will cross-examine you while your Corner Coach on the right provides confidential analysis in real time."
                      : "Set your scenario above and click Launch to initiate turn-by-turn simulation powered by 50,000+ Indian precedents."}
                  </p>
                </div>
              ) : (
                turns.map((t, idx) => {
                  if (t.role === "witness") {
                    return (
                      <div key={idx} className="chamber-turn witness">
                        <div className="turn-avatar witness-avatar">👤</div>
                        <div className="turn-bubble witness-bubble">
                          <div className="turn-meta">
                            <span className="speaker-name">
                              {witnessRole === "accused" ? `${personas.role1.title} (Testimony Under Oath)` : `${personas.role2.title} (Testimony Under Oath)`}
                            </span>
                          </div>
                          <div className="turn-content witness-content">
                            <p>"{t.content}"</p>
                          </div>
                        </div>
                      </div>
                    );
                  }

                  // Interrogator or Fortifier turn
                  const isInterrogator = t.role === "interrogator";
                  return (
                    <div key={idx} className={`chamber-turn ${t.role}`}>
                      <div className="turn-avatar">
                        {isInterrogator ? "⚔️" : "🛡️"}
                      </div>
                      <div className="turn-bubble">
                        <div className="turn-meta">
                          <span className="speaker-name">
                            {isInterrogator
                              ? (witnessRole === "accused" 
                                  ? `Adverse Counsel (Sec 146 BSA)` 
                                  : `Defense Trial Advocate (Sec 146 BSA)`)
                              : "Senior Trial Defense Strategist"}
                          </span>
                          <div className="meta-right">
                            {t.score != null && (
                              <span
                                className="turn-score-tag"
                                style={{ color: getScoreColor(t.score) }}
                              >
                                Exposure: {t.score}%
                              </span>
                            )}
                            <button
                              className="copy-mini-btn"
                              onClick={() => handleCopy(t.content, `turn_${idx}`)}
                            >
                              {copiedKey === `turn_${idx}` ? "✓ Copied" : "📋 Copy"}
                            </button>
                          </div>
                        </div>
                        <div className="turn-content">
                          {t.content.split("\n").map((line, lIdx) => (
                            <p key={lIdx}>{line}</p>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              {loading && (
                <div className="chamber-loading">
                  <span className="spinner" />
                  <span>Analyzing witness testimony against Supreme Court and High Court precedents...</span>
                </div>
              )}

              {/* Final Trial Record of Proceedings Card */}
              {concludeData && (
                <div className="trial-concluded-card">
                  <div className="concluded-header-row">
                    <span className="concluded-seal">⚖️</span>
                    <div className="concluded-headings">
                      <span className="concluded-sub">RECORD OF PROCEEDINGS · SECTION 146 BSA</span>
                      <h3>EXAMINATION FORMALLY CONCLUDED</h3>
                    </div>
                  </div>

                  <div
                    className="concluded-status-pill"
                    style={{ borderColor: concludeData.status_color, color: concludeData.status_color }}
                  >
                    {concludeData.status_label} ({concludeData.final_score}% Exposure)
                  </div>

                  <div className="concluded-assessment-box">
                    <span className="box-mini-label">BENCH VERDICT & JUDICIAL IMPACT:</span>
                    <p>{concludeData.judicial_outlook}</p>
                  </div>

                  {concludeData.admissions_on_record?.length > 0 && (
                    <div className="concluded-admissions-box">
                      <span className="box-mini-label">MATERIAL ADMISSIONS ON RECORD:</span>
                      <ul>
                        {concludeData.admissions_on_record.map((adm, aIdx) => (
                          <li key={aIdx}>{adm}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {concludeData.statutory_motions?.length > 0 && (
                    <div className="concluded-motions-box">
                      <span className="box-mini-label">RECOMMENDED STATUTORY MOTIONS:</span>
                      <ul>
                        {concludeData.statutory_motions.map((mot, mIdx) => (
                          <li key={mIdx}>{mot}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <button
                    className="restart-trial-btn"
                    onClick={() => {
                      setTurns([]);
                      setConcludeData(null);
                      setSessionActive(false);
                      setLatestCoachAdvice(null);
                    }}
                  >
                    ⟳ Reset & Spar on New Scenario
                  </button>
                </div>
              )}

              <div ref={interrogationEndRef} />
            </div>

            {/* Witness Response Input Box */}
            {sessionActive && !concludeData && (
              <div className="witness-reply-box">
                <input
                  type="text"
                  className="witness-input"
                  placeholder="Enter witness response on the stand... Corner Coach will audit admissions in real time."
                  value={witnessInput}
                  onChange={(e) => setWitnessInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSendWitnessTurn();
                  }}
                  disabled={loading}
                />
                <button
                  className="send-turn-btn"
                  onClick={handleSendWitnessTurn}
                  disabled={loading || !witnessInput.trim()}
                >
                  {mode === "moot_court" ? "Testify on Stand ↵" : mode === "cross_examiner" ? "Testify ↵" : "Consult Coach ↵"}
                </button>
                <button
                  className="rest-turn-btn"
                  onClick={handleConcludeInterrogation}
                  disabled={loading}
                  title="Conclude Examination and Generate Final Verdict"
                >
                  ⏹️ Rest Case
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT COLUMN: CORNER COACH DESK & PRECEDENT INTELLIGENCE ── */}
        <div className="precedent-drawer">
          {/* Live Vulnerability Radar */}
          <div className="drawer-card vulnerability-card">
            <div className="gauge-header">
              <span className="card-label">TRIAL EXPOSURE RADAR</span>
              <span
                className="score-val"
                style={{ color: getScoreColor(vulnerabilityScore) }}
              >
                {vulnerabilityScore}%
              </span>
            </div>

            <div className="gauge-bar-track">
              <div
                className="gauge-bar-fill"
                style={{
                  width: `${vulnerabilityScore}%`,
                  background: getScoreColor(vulnerabilityScore)
                }}
              />
            </div>

            <div className="gauge-status-text">
              {vulnerabilityScore >= 65 ? (
                <span className="status-danger">🔴 Critical Evidentiary Exposure</span>
              ) : vulnerabilityScore >= 35 ? (
                <span className="status-warning">🟡 Active Rebuttal Required</span>
              ) : (
                <span className="status-safe">🟢 Fortified Position</span>
              )}
            </div>

            {fatalFlaw && (
              <div className="fatal-flaw-box">
                <strong>Primary Vulnerability:</strong>
                <p>{fatalFlaw}</p>
              </div>
            )}
          </div>

          {/* DEDICATED CORNER COACH STRATEGY DESK */}
          {mode === "moot_court" && (
            <div className="drawer-card corner-coach-desk">
              <div className="coach-desk-header">
                <div className="coach-desk-title-wrap">
                  <span className="coach-badge">🛡️ CORNER COACH REAL-TIME DESK</span>
                  <span className="coach-sub">Confidential Tactical Analysis & Sec 146 BSA Objections</span>
                </div>
                {vulnerabilityDelta !== 0 && (
                  <span
                    className={`coach-delta-badge ${vulnerabilityDelta > 0 ? "danger" : "safe"}`}
                  >
                    {vulnerabilityDelta > 0 ? `⚠️ +${vulnerabilityDelta}% Exposure` : `✓ ${vulnerabilityDelta}% Lowered`}
                  </span>
                )}
              </div>

              {latestCoachAdvice ? (
                <div className="coach-desk-body">
                  {latestCoachAdvice.audit_critique && (
                    <div className="coach-critique-box">
                      <span className="coach-section-label">🚨 TESTIMONY AUDIT & ADMISSION RISK:</span>
                      <p>{latestCoachAdvice.audit_critique}</p>
                    </div>
                  )}

                  {latestCoachAdvice.counsel_objection && (
                    <div className="coach-objection-box">
                      <div className="coach-box-header">
                        <span className="coach-section-label">⚖️ COUNSEL'S FORMAL OBJECTION (SEC. 146 BSA):</span>
                        <button
                          className="copy-mini-btn"
                          onClick={() => handleCopy(latestCoachAdvice.counsel_objection, "side_obj")}
                        >
                          {copiedKey === "side_obj" ? "✓ Copied" : "📋 Copy Objection"}
                        </button>
                      </div>
                      <p className="objection-text">"{latestCoachAdvice.counsel_objection}"</p>
                    </div>
                  )}

                  {latestCoachAdvice.optimized_rejoinder && (
                    <div className="coach-rejoinder-box">
                      <div className="coach-box-header">
                        <span className="coach-section-label">💬 SAFE VERBATIM WITNESS REJOINDER:</span>
                        <div className="coach-btn-group">
                          <button
                            className="adopt-script-btn"
                            onClick={() => setWitnessInput(latestCoachAdvice.optimized_rejoinder)}
                            title="Populate witness dock with this safe answer"
                          >
                            ↵ Adopt Script
                          </button>
                          <button
                            className="copy-mini-btn"
                            onClick={() => handleCopy(latestCoachAdvice.optimized_rejoinder, "side_rej")}
                          >
                            {copiedKey === "side_rej" ? "✓ Copied" : "📋 Copy Script"}
                          </button>
                        </div>
                      </div>
                      <p className="rejoinder-text">"{latestCoachAdvice.optimized_rejoinder}"</p>
                    </div>
                  )}

                  {latestCoachAdvice.evidentiary_plug && (
                    <div className="coach-plug-box">
                      <span className="coach-section-label">📁 EVIDENTIARY PLUG TO TENDER:</span>
                      <p>• {latestCoachAdvice.evidentiary_plug}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="coach-desk-empty">
                  <span className="coach-empty-icon">🛡️</span>
                  <p>Your Corner Coach will monitor opposing counsel's questions and your answers, providing real-time objections and bulletproof rejoinders right here.</p>
                </div>
              )}
            </div>
          )}

          {/* Controlling Precedent Card */}
          {controllingPrecedent ? (
            <div className="drawer-card precedent-card">
              <div className="card-top-tag">
                <span className="tag-icon">🏛️</span>
                <span>CONTROLLING JUDICIAL PRECEDENT</span>
              </div>
              <h4 className="precedent-title">{controllingPrecedent.title}</h4>
              <div className="precedent-citation-row">
                <span className="citation-badge">{controllingPrecedent.citation}</span>
                <span className="court-badge">{controllingPrecedent.court}</span>
                <span className="year-badge">{controllingPrecedent.year}</span>
              </div>

              <div className="precedent-ratio-box">
                <span className="box-label">BINDING RATIO DECIDENDI:</span>
                <p className="ratio-text">{controllingPrecedent.ratio_decidendi}</p>
              </div>

              {controllingPrecedent.turning_point && (
                <div className="turning-point-box">
                  <span className="box-label">HISTORICAL TURNING POINT:</span>
                  <p className="tp-q">
                    <strong>Q:</strong> {controllingPrecedent.turning_point.cross_question}
                  </p>
                  <p className="tp-holding">
                    <strong>Rule:</strong> {controllingPrecedent.turning_point.judicial_holding}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="drawer-card empty-precedent">
              <span className="empty-icon">📖</span>
              <p>Controlling case precedents, ratio decidendi, and turning points will populate here when you launch questioning.</p>
            </div>
          )}

          {/* Statutory Motions & Actions */}
          {suggestedMotions.length > 0 && (
            <div className="drawer-card motions-card">
              <span className="card-label">RECOMMENDED STATUTORY ACTIONS</span>
              <ul className="motions-list">
                {suggestedMotions.map((motion, mIdx) => (
                  <li key={mIdx}>
                    <span className="motion-bullet">⚡</span>
                    <span>{motion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
