import React, { useState, useEffect } from "react";
import axios from "axios";
import "./ApiKeyModal.css";

export default function ApiKeyModal({ isOpen, onClose, rateLimitAlert = false, onKeyUpdated }) {
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [activeStoredKey, setActiveStoredKey] = useState("");

  useEffect(() => {
    if (isOpen) {
      const stored = localStorage.getItem("saulgpt_user_groq_key") || "";
      setActiveStoredKey(stored);
      setApiKey(stored);
      setTestResult(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestKey = async () => {
    const trimmed = apiKey.trim();
    if (!trimmed) {
      setTestResult({ success: false, message: "Please enter a valid Groq API key (starts with gsk_)" });
      return;
    }
    setLoading(true);
    setTestResult(null);
    try {
      const res = await axios.post("/api/keys/validate", { api_key: trimmed });
      if (res.data?.valid) {
        setTestResult({
          success: true,
          message: `Verified! Access granted with ${res.data.models_available || 10}+ models available.`
        });
      } else {
        setTestResult({
          success: false,
          message: res.data?.error || "Invalid Groq API key. Check console.groq.com/keys"
        });
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: err.response?.data?.error || "Verification request failed. Check server connection."
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = () => {
    const trimmed = apiKey.trim();
    if (!trimmed) {
      handleRemoveKey();
      return;
    }
    localStorage.setItem("saulgpt_user_groq_key", trimmed);
    setActiveStoredKey(trimmed);
    if (onKeyUpdated) onKeyUpdated(trimmed);
    onClose();
  };

  const handleRemoveKey = () => {
    localStorage.removeItem("saulgpt_user_groq_key");
    setActiveStoredKey("");
    setApiKey("");
    setTestResult({ success: true, message: "Reverted to shared server default key." });
    if (onKeyUpdated) onKeyUpdated("");
    setTimeout(() => onClose(), 600);
  };

  const getMasked = (key) => {
    if (!key || key.length < 12) return "";
    return `${key.slice(0, 7)}••••••••${key.slice(-4)}`;
  };

  return (
    <div className="api-key-modal-overlay" onClick={onClose}>
      <div className="api-key-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="api-key-modal-header">
          <div className="header-title-box">
            <span className="key-shield-icon">🔑</span>
            <div>
              <h3>Bring Your Own Key (BYOK)</h3>
              <p className="modal-subtitle">Dedicated Groq inference · Zero rate limits · 100% Client-Side Privacy</p>
            </div>
          </div>
          <button className="close-btn" onClick={onClose} title="Close">✕</button>
        </div>

        {rateLimitAlert && (
          <div className="rate-limit-banner">
            <span className="alert-icon">⚠️</span>
            <div className="alert-text">
              <strong>Shared Server Key Quota Exceeded (429 Rate Limit)</strong>
              <p>Groq's shared free tier has temporarily hit token limits. Add your own free key below to resume immediately with dedicated quota!</p>
            </div>
          </div>
        )}

        <div className="api-key-modal-body">
          <div className="key-status-indicator">
            <span className="status-label">Current Engine Status:</span>
            {activeStoredKey ? (
              <span className="status-pill dedicated">
                🟢 Personal Key Active ({getMasked(activeStoredKey)})
              </span>
            ) : (
              <span className="status-pill shared">
                🟡 Shared Server Key (Free Tier Fallback)
              </span>
            )}
          </div>

          <div className="key-input-group">
            <label htmlFor="groq-key-input">Groq API Key (starts with <code>gsk_</code>):</label>
            <div className="input-with-toggle">
              <input
                id="groq-key-input"
                type={showKey ? "text" : "password"}
                placeholder="gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                autoComplete="off"
                spellCheck="false"
              />
              <button
                type="button"
                className="toggle-visibility-btn"
                onClick={() => setShowKey(!showKey)}
                title={showKey ? "Hide key" : "Show key"}
              >
                {showKey ? "👁️" : "🔒"}
              </button>
            </div>
          </div>

          {testResult && (
            <div className={`test-feedback-box ${testResult.success ? "success" : "error"}`}>
              <span>{testResult.success ? "✓" : "✕"}</span>
              <p>{testResult.message}</p>
            </div>
          )}

          <div className="key-guide-box">
            <div className="guide-header">
              <span>💡 Need a free Groq API key?</span>
              <a
                href="https://console.groq.com/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="guide-link"
              >
                Get Free Key on Groq Console ↗
              </a>
            </div>
            <p className="guide-note">
              1. Sign in to <strong>console.groq.com</strong> with Google/GitHub.<br />
              2. Click <strong>"Create API Key"</strong> and paste it above.<br />
              3. It is stored <em>only</em> in your browser's local memory and never saved to our database.
            </p>
          </div>
        </div>

        <div className="api-key-modal-footer">
          {activeStoredKey && (
            <button className="remove-key-btn" onClick={handleRemoveKey}>
              🗑️ Revert to Server Key
            </button>
          )}
          <div className="footer-right-actions">
            <button
              className="test-key-btn"
              onClick={handleTestKey}
              disabled={loading || !apiKey.trim()}
            >
              {loading ? "Testing..." : "⚡ Test Connection"}
            </button>
            <button className="save-key-btn" onClick={handleSave}>
              Save & Apply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
