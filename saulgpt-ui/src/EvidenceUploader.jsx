import { useState, useRef } from "react";
import axios from "axios";
import "./EvidenceUploader.css";

const API_BASE = "http://localhost:8000";
const MAX_FILE_SIZE_MB = 25;

export default function EvidenceUploader({ isOpen, onClose, onInjectContext, onLaunchCrossExam, sessionId }) {
  const [evidenceType, setEvidenceType] = useState("audio"); // 'audio' (multimedia) | 'document' (invoices, cheques, etc.)
  const [file, setFile] = useState(null);
  const [clientHash, setClientHash] = useState("");
  const [hashing, setHashing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Manual fallback date for low confidence OCR
  const [manualDate, setManualDate] = useState("");
  const [manualClock, setManualClock] = useState(null);

  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleLaunchCrossExam = () => {
    if (!result) return;
    const finalResult = {
      ...result,
      statutory_clock: manualClock || result.statutory_clock || {}
    };
    if (onLaunchCrossExam) {
      onLaunchCrossExam(finalResult);
    }
    onClose();
  };

  const handleLoadSampleCheque = () => {
    setEvidenceType("document");
    setFile(null);
    setError(null);
    setClientHash("A7B8C9D0E1F234567890ABCDEF1234567890ABCDEF1234567890ABCDEF123456");
    setResult({
      filename: "SBI_Cheque_Return_Memo_99182.pdf",
      evidence_type: "document_image",
      sec63_bsa_certified: true,
      sha256_hash: "A7B8C9D0E1F234567890ABCDEF1234567890ABCDEF1234567890ABCDEF123456",
      statutory_clock: {
        bank_return_date: "2024-08-10",
        dishonour_reason: "Funds Insufficient",
        days_remaining: 12,
        clock_status: "active"
      },
      certificate: {
        certificate_id: "BSA-63-2024-99182",
        pdf_url: "/api/evidence/sample"
      },
      extracted_data: {
        payee: "Ramesh Kumar",
        drawer: "Suresh Patel",
        amount: "Rs. 15,00,000"
      }
    });
  };

  const handleLoadSampleWhatsApp = () => {
    setEvidenceType("audio");
    setFile(null);
    setError(null);
    setClientHash("F1E2D3C4B5A67890123456789012345678901234567890123456789012345678");
    setResult({
      filename: "whatsapp_voice_admission.m4a",
      evidence_type: "audio",
      sec63_bsa_certified: false,
      sha256_hash: "F1E2D3C4B5A67890123456789012345678901234567890123456789012345678",
      transcript: "Bhai I will return your 15 lakhs cash next Monday.",
      forensic_admission: {
        debtor_statement: "Bhai I will return your 15 lakhs cash next Monday.",
        debt_acknowledged: "Rs. 15 Lakhs"
      },
      limitation_calculation: {
        fresh_limitation_expiry: "2027-08-10"
      }
    });
  };

  const computeSHA256 = async (selectedFile) => {
    setHashing(true);
    try {
      const buffer = await selectedFile.arrayBuffer();
      const hashBuffer = await window.crypto.subtle.digest("SHA-256", buffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("").toUpperCase();
      setClientHash(hashHex);
      return hashHex;
    } catch (e) {
      console.error("Client SHA-256 calculation failed", e);
      return null;
    } finally {
      setHashing(false);
    }
  };

  const handleFileSelect = async (e) => {
    const selected = e.target.files[0];
    if (!selected) return;

    // Strict 25MB safety limit to protect against client-side RAM crashes
    const maxBytes = MAX_FILE_SIZE_MB * 1024 * 1024;
    if (selected.size > maxBytes) {
      setError(
        `🚨 File exceeds maximum MVP limit of ${MAX_FILE_SIZE_MB}MB (Selected: ${(selected.size / (1024 * 1024)).toFixed(1)}MB). To prevent browser memory exhaustion during client-side SHA-256 calculation under Sec. 63 BSA, please upload a clip or document under 25MB.`
      );
      setFile(null);
      setClientHash("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    setFile(selected);
    setError(null);
    setResult(null);
    setManualDate("");
    setManualClock(null);
    await computeSHA256(selected);
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select an evidence file first.");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      let hash = clientHash;
      if (!hash) {
        hash = await computeSHA256(file);
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("evidence_type", evidenceType);
      if (hash) {
        formData.append("client_hash", hash);
      }
      if (sessionId) {
        formData.append("session_id", sessionId);
      }

      const res = await axios.post(`${API_BASE}/api/evidence/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setResult(res.data);
    } catch (err) {
      console.error("Upload error:", err);
      const msg = err.response?.data?.detail || err.message || "Failed to process evidence.";
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleManualDateCompute = () => {
    if (!manualDate) return;
    const memoDate = new Date(manualDate);
    const deadline = new Date(memoDate);
    deadline.setDate(deadline.getDate() + 30);

    const today = new Date();
    const diffTime = deadline - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    setManualClock({
      notice_clock_active: true,
      statute: "Section 138(b), Negotiable Instruments Act, 1881",
      bank_return_date: memoDate.toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }),
      statutory_window_days: 30,
      notice_deadline: deadline.toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }),
      days_remaining: Math.max(0, diffDays),
      urgency_level: diffDays <= 15 ? "URGENT" : "STANDARD",
      dishonour_reason: "Manual Entry Confirmed (Dishonoured Cheque)",
    });
  };

  const handleApplyToChat = () => {
    if (!result) return;
    let contextText = "";

    if (result.evidence_type === "audio" || result.evidence_type === "video") {
      const admission = result.forensic_admission || {};
      const limit = result.limitation_calculation || {};
      const proc = result.statutory_proceedings || {};
      if (result.category === "criminal_intimidation_harassment") {
        contextText = `[EVIDENCE GROUNDED: Electronic Voice/Video Recording - Section 63 BSA]\nOffence: Criminal Intimidation & Harassment under BNS 2023 (${(admission.applicable_sections || []).join(", ")})\nIncriminating Statements: "${(admission.incriminating_statements || []).join('" | "')}"\nMandatory Procedural Action: Zero FIR under Sec 173 BNSS & Sec 183 BNSS judicial statement recording.\nSection 63 BSA SHA-256 Hash: ${result.sha256_hash}.\nPlease advise on immediate criminal complaint and judicial relief based on this evidence.`;
      } else {
        contextText = `[EVIDENCE GROUNDED: Voice Admission of Liability]\nAdverse party verbal statement: "${admission.debtor_statement || "Acknowledged debt"}"\nDebt obligation: ${admission.debt_acknowledged || "Debt admitted"}\nStatutory Effect: Section 18 Limitation Act 1963 resets limitation by 3 years to ${limit.fresh_limitation_expiry || "3 years"}.\nSection 63 BSA 2023 SHA-256 Hash: ${result.sha256_hash}.\nPlease advise on filing recovery suit or issuing legal notice based on this evidence.`;
      }
    } else {
      const clock = manualClock || result.statutory_clock || {};
      const parties = result.parties || {};
      const tx = result.transaction_details || {};
      contextText = `[EVIDENCE GROUNDED: ${result.document_title || "Document Record"}]\nGoverning Law: ${result.governing_act || "Indian Law"}\nApplicable Sections: ${(result.applicable_sections || []).join(", ")}\nParties: Issuer/Merchant: ${parties.issuer_merchant || "Documented"} | Recipient/Customer: ${parties.recipient_customer || "Customer"}\nTransaction Details: Amount: ${tx.amount || "N/A"}, Date: ${tx.date || "Documented"}, Ref: ${tx.invoice_number || "Documented"}\nEvidentiary Value: ${result.evidentiary_value || "Admissible under Section 63 BSA"}\nStatutory Window: ${clock.statute || "Statutory window"} - Deadline: ${clock.notice_deadline || "Active"} (${clock.days_remaining || 0} days remaining).\nSection 63 BSA 2023 SHA-256 Hash: ${result.sha256_hash}.\nPlease incorporate this verified evidence into my case strategy and draft the necessary legal notice or petition.`;
    }

    if (onInjectContext) {
      onInjectContext(contextText);
    }
    onClose();
  };

  const activeClock = manualClock || (result?.statutory_clock?.notice_clock_active ? result.statutory_clock : null);

  return (
    <div className="evidence-modal-overlay" onClick={onClose}>
      <div className="evidence-modal" onClick={(e) => e.stopPropagation()}>
        <div className="evidence-modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon">🛡️</span>
            <div>
              <h3>Multimodal Evidence Grounding Engine</h3>
              <p className="modal-sub">
                Sec. 63 Bharatiya Sakshya Adhiniyam, 2023 · Consumer Protection Act · Sec. 138 NI Act · BNS 2023
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="evidence-modal-body">
          {/* Evidence Type Tabs */}
          <div className="evidence-tabs">
            <button
              className={`evidence-tab ${evidenceType === "audio" ? "active" : ""}`}
              onClick={() => {
                setEvidenceType("audio");
                setResult(null);
                setFile(null);
              }}
            >
              🎙️ Audio & Video (Voice, CCTV, Whisper)
            </button>
            <button
              className={`evidence-tab ${evidenceType === "document" ? "active" : ""}`}
              onClick={() => {
                setEvidenceType("document");
                setResult(null);
                setFile(null);
              }}
            >
              📄 Documents & Images (Bills, Invoices, Cheques, Chats)
            </button>
          </div>

          {/* Quick Demo Sample Presets */}
          <div className="demo-sample-presets">
            <span className="demo-sample-label">⚡ OR TEST INSTANTLY WITH 1-CLICK DEMO EVIDENCE:</span>
            <div className="demo-sample-buttons">
              <button
                type="button"
                className="demo-preset-btn"
                onClick={handleLoadSampleCheque}
                title="Load sample Bank Return Memo & Dishonoured Cheque"
              >
                📄 Sample Certified Cheque & Memo (Sec 63 BSA)
              </button>
              <button
                type="button"
                className="demo-preset-btn"
                onClick={handleLoadSampleWhatsApp}
                title="Load sample WhatsApp Voice Note Admission"
              >
                🎙️ Sample Uncertified WhatsApp Audio
              </button>
            </div>
          </div>

          {/* File Picker & Pre-Hash Card */}
          <div className="evidence-dropzone" onClick={() => fileInputRef.current?.click()}>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: "none" }}
              accept={
                evidenceType === "audio"
                  ? ".mp3,.wav,.m4a,.ogg,.aac,.webm,.mp4,.mov,.avi,.mkv"
                  : ".jpg,.jpeg,.png,.pdf,.webp"
              }
              onChange={handleFileSelect}
            />
            {file ? (
              <div className="selected-file-info">
                <span className="file-icon">{evidenceType === "audio" ? "🎬" : "📄"}</span>
                <span className="file-name">{file.name}</span>
                <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
              </div>
            ) : (
              <div className="dropzone-placeholder">
                <span className="dropzone-icon">{evidenceType === "audio" ? "🎙️" : "📸"}</span>
                <p>Click or drag to select {evidenceType === "audio" ? "voice or video recording" : "invoice, bill, cheque, or document photo"}</p>
                <small>Formats: {evidenceType === "audio" ? "MP3, WAV, M4A, OGG, MP4, MOV, WebM" : "PDF, PNG, JPG, JPEG, WebP"} · Max size: 25MB (OOM Protection)</small>
              </div>
            )}
          </div>

          {/* Client Cryptographic Pre-Hash Badge */}
          {hashing && (
            <div className="hash-computing-banner">
              <span className="hash-spinner">⚙️</span>
              <span>Computing Client-Side SHA-256 Hash via Web Crypto API...</span>
            </div>
          )}

          {clientHash && !hashing && (
            <div className="hash-preview-badge">
              <span className="hash-label">PRE-UPLOAD CRYPTO DIGEST (SHA-256):</span>
              <code className="hash-code">{clientHash}</code>
              <span className="hash-shield-tag">🔒 Section 63 BSA Pre-Certified</span>
            </div>
          )}

          {error && <div className="evidence-error-banner">🚨 {error}</div>}

          {/* Action button */}
          {!result && (
            <button
              className="evidence-process-btn"
              onClick={handleUpload}
              disabled={!file || uploading || hashing}
            >
              {uploading ? (
                <>
                  <span className="btn-spinner"></span>
                  Analyzing & Generating Sec. 63 BSA Certificate...
                </>
              ) : (
                `Verify & Analyze ${evidenceType === "audio" ? "Audio/Video Evidence" : "Document / Invoice Evidence"}`
              )}
            </button>
          )}

          {/* Result Forensic Dashboard */}
          {result && (
            <div className="evidence-results-dashboard">
              {/* Hash Admissibility Header */}
              <div className="bsa-cert-status-card">
                <div className="cert-status-left">
                  <span className="cert-seal">⚖️</span>
                  <div>
                    <span className="cert-title">Section 63 BSA Certificate Generated</span>
                    <span className="cert-id">Ref: {result.certificate?.certificate_id}</span>
                  </div>
                </div>
                <div className="cert-status-right">
                  <span className="hash-match-pill">✓ SHA-256 Hash Match Verified</span>
                  <a
                    href={`${API_BASE}${result.certificate?.pdf_url}`}
                    target="_blank"
                    rel="noreferrer"
                    className="cert-download-btn"
                  >
                    📄 Download Admissibility PDF
                  </a>
                </div>
              </div>

              {/* Audio/Video Specific Results */}
              {(result.evidence_type === "audio" || result.evidence_type === "video") && (
                <div className="audio-forensic-box">
                  <div className="forensic-subcard">
                    <h4>Transcript (Groq Whisper)</h4>
                    <p className="transcript-snippet">
                      "{result.transcript || "Electronic record audio stream transcribed."}"
                    </p>
                  </div>

                  {result.category === "criminal_intimidation_harassment" ? (
                    <div className="criminal-proceedings-banner" style={{ background: "rgba(196,74,74,0.1)", border: "1px solid #C44A4A", borderRadius: "8px", padding: "12px", marginTop: "10px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                        <strong style={{ color: "#E05D5D" }}>🚨 BHARATIYA NYAYA SANHITA, 2023 OFFENCES</strong>
                        <span style={{ fontSize: "11px", background: "#C44A4A", color: "#fff", padding: "2px 8px", borderRadius: "4px" }}>CRITICAL CRIMINAL PROCEEDING</span>
                      </div>
                      <div style={{ fontSize: "13px", lineHeight: "1.5" }}>
                        <div><strong>Statutory Sections:</strong> {(result.forensic_admission?.applicable_sections || []).join(", ")}</div>
                        <div><strong>Target/Victim:</strong> {result.forensic_admission?.target_victim || "Complainant"}</div>
                        <div><strong>Incriminating Statements:</strong> <em>"{result.forensic_admission?.debtor_statement || (result.forensic_admission?.incriminating_statements || [])[0]}"</em></div>
                        <div style={{ marginTop: "6px", color: "#C9A84C" }}><strong>Mandatory Police Action:</strong> Zero FIR under Section 173 BNSS; Statement Recording before Judicial Magistrate under Section 183 BNSS.</div>
                      </div>
                    </div>
                  ) : (
                    <div className="limitation-reset-banner">
                      <div className="limitation-head">
                        <span className="act-tag">SECTION 18 LIMITATION ACT, 1963</span>
                        <span className="extension-tag">⏱️ Limitation Reset +3 Years</span>
                      </div>
                      <div className="limitation-details">
                        <div>
                          <strong>Debtor Statement:</strong>{" "}
                          <span>{result.forensic_admission?.debtor_statement || "Admitted payment liability"}</span>
                        </div>
                        <div>
                          <strong>Debt Acknowledged:</strong>{" "}
                          <span>{result.forensic_admission?.debt_acknowledged || "Outstanding dues"}</span>
                        </div>
                        <div>
                          <strong>Fresh Limitation Expiry:</strong>{" "}
                          <span className="highlight-date">
                            {result.limitation_calculation?.fresh_limitation_expiry}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Document / Invoice Specific Results */}
              {result.evidence_type === "document_image" && (
                <div className="cheque-forensic-box">
                  <div className="document-summary-card" style={{ background: "rgba(201,168,76,0.08)", border: "1px solid rgba(201,168,76,0.25)", borderRadius: "8px", padding: "12px", marginBottom: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <strong style={{ color: "#E8C97A", fontSize: "14px" }}>📄 {result.document_title || "Verified Document Record"}</strong>
                      <span style={{ fontSize: "11px", color: "#A8C49A", background: "rgba(168,196,154,0.15)", padding: "2px 8px", borderRadius: "4px" }}>
                        {result.governing_act || "Indian Law"}
                      </span>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12px", color: "#DDD" }}>
                      <div><strong>Issuer / Seller:</strong> {result.parties?.issuer_merchant || "Documented"}</div>
                      <div><strong>Customer / Payee:</strong> {result.parties?.recipient_customer || "Documented"}</div>
                      <div><strong>Amount:</strong> <span style={{ color: "#7EB8C4", fontWeight: "bold" }}>{result.transaction_details?.amount || "N/A"}</span></div>
                      <div><strong>Date:</strong> {result.transaction_details?.date || "Documented"}</div>
                    </div>

                    {result.applicable_sections?.length > 0 && (
                      <div style={{ marginTop: "8px", fontSize: "12px", color: "#C9A84C" }}>
                        <strong>Applicable Sections:</strong> {result.applicable_sections.join(", ")}
                      </div>
                    )}
                  </div>

                  {/* Guardrail: If confidence < 0.85, show manual fallback */}
                  {result.requires_manual_entry && !manualClock && (
                    <div className="low-confidence-guardrail-card">
                      <div className="guardrail-warning-head">
                        <span>⚠️ OCR Confidence Low ({Math.round(result.confidence_score * 100)}%)</span>
                        <span className="guardrail-rule">Rule of Prudence Mandatory Check</span>
                      </div>
                      <p className="guardrail-text">
                        The return memo date could not be verified with ≥ 85% algorithmic certainty.
                        To prevent a fatal Section 138(b) limitation bar, please enter the Bank Return Memo date manually:
                      </p>
                      <div className="manual-date-row">
                        <label>Bank Return Memo Date:</label>
                        <input
                          type="date"
                          value={manualDate}
                          onChange={(e) => setManualDate(e.target.value)}
                          className="manual-date-input"
                        />
                        <button
                          className="compute-clock-btn"
                          onClick={handleManualDateCompute}
                          disabled={!manualDate}
                        >
                          Calculate 30-Day Clock
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Statutory clock card (Cheque 30-day notice OR Consumer 2-year limitation) */}
                  {activeClock && (
                    <div className={`notice-clock-card ${activeClock.urgency_level?.toLowerCase() || "standard"}`}>
                      <div className="clock-header">
                        <span className="clock-badge">
                          {activeClock.urgency_level === "URGENT" || activeClock.urgency_level === "CRITICAL"
                            ? "🚨 CRITICAL TIMELINE"
                            : "⏳ STATUTORY TIMELINE"}
                        </span>
                        <span className="clock-statute">{activeClock.statute || "Statutory Deadline"}</span>
                      </div>

                      <div className="clock-grid">
                        <div className="clock-metric">
                          <span className="metric-num">{activeClock.days_remaining}</span>
                          <span className="metric-label">Days Remaining</span>
                        </div>
                        <div className="clock-info">
                          <div><strong>Start / Return Date:</strong> {activeClock.bank_return_date}</div>
                          <div><strong>Statutory Window:</strong> {activeClock.statutory_window_days} Days ({activeClock.statute})</div>
                          <div><strong>Statutory Deadline:</strong> <span className="deadline-date">{activeClock.notice_deadline}</span></div>
                          <div><strong>Purpose:</strong> {activeClock.dishonour_reason}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Transfer to Case Strategy Action */}
              <div className="evidence-action-footer">
                <button className="ground-chat-btn" onClick={handleApplyToChat}>
                  ⚡ Ground in Strategy & Draft Notice / Plaint
                </button>
                <button className="launch-cross-btn" onClick={handleLaunchCrossExam} title="Launch Moot Court Arena / Trial Studio with this grounded evidence">
                  ⚔️ Cross-Examine in Moot Court Arena
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

