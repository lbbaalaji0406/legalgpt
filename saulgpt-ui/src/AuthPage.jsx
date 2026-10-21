import { useState } from "react";
import axios from "axios";

export default function AuthPage({ onAuth, migrating }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [groqKey, setGroqKey] = useState(() => localStorage.getItem("saulgpt_user_groq_key") || "");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    const trimmedKey = groqKey.trim();
    if (!trimmedKey) {
      setError("Groq API Key is compulsory. Please paste your free Groq key (starts with gsk_) from console.groq.com/keys to proceed.");
      return;
    }
    if (!trimmedKey.startsWith("gsk_")) {
      setError("Invalid API key format. Groq API keys must begin with 'gsk_'.");
      return;
    }

    setLoading(true);
    try {
      localStorage.setItem("saulgpt_user_groq_key", trimmedKey);
      const payload = mode === "signup" ? { email, password, username } : { email, password };
      const { data } = await axios.post(`/api/auth/${mode}`, payload);
      localStorage.setItem("saulgpt_token", data.token);
      localStorage.setItem("saulgpt_user", JSON.stringify({ id: data.user_id, email: data.email, username: data.username }));
      onAuth(data.token, { id: data.user_id, email: data.email, username: data.username });
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  if (migrating) {
    return (
      <div className="auth-page">
        <div className="auth-card" style={{ textAlign: "center" }}>
          <div className="auth-seal">⚖</div>
          <h2 style={{ color: "var(--gold)", fontFamily: "Cinzel,serif", margin: "16px 0 8px" }}>Saving Your Session</h2>
          <p style={{ color: "var(--ink-faint)" }}>Migrating your chat history to your account...</p>
          <div className="spinner" style={{ margin: "20px auto", width: 32, height: 32, border: "3px solid var(--border)", borderTopColor: "var(--gold)", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-seal">⚖</div>
        <h1 className="auth-title">SaulGPT</h1>
        <p className="auth-sub">Indian Legal Intelligence Workstation</p>

        <div className="auth-tabs">
          <button className={`auth-tab ${mode === "login" ? "active" : ""}`} onClick={() => setMode("login")}>Sign In</button>
          <button className={`auth-tab ${mode === "signup" ? "active" : ""}`} onClick={() => setMode("signup")}>Sign Up</button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <input className="auth-input" type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required />
          {mode === "signup" && (
            <input className="auth-input" type="text" placeholder="Username (optional)" value={username} onChange={e => setUsername(e.target.value)} />
          )}
          <input className="auth-input" type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required minLength={4} />

          {/* BYOK Section — Compulsory */}
          <div className="auth-byok-box" style={{ borderColor: "var(--gold)", background: "rgba(201,168,76,0.06)" }}>
            <div className="auth-byok-header">
              <span style={{ fontWeight: 600, color: "var(--gold-light)" }}>🔑 Groq API Key (Compulsory)</span>
              <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer" className="auth-byok-link">
                Get Free Key (Instant) ↗
              </a>
            </div>
            <input
              className="auth-input"
              style={{ fontSize: "14px", padding: "8px 10px", borderColor: groqKey ? "var(--border)" : "var(--gold-dim)" }}
              type="password"
              placeholder="gsk_... (Required to run AI queries)"
              value={groqKey}
              onChange={e => setGroqKey(e.target.value)}
              required
            />
            <p className="auth-byok-hint" style={{ color: "var(--parchment-dk)" }}>
              ⚡ 100% Free · Dedicated quota · Get yours in 30 seconds at console.groq.com/keys
            </p>
          </div>

          {error && <p className="auth-error">{error}</p>}
          <button className="auth-submit" disabled={loading}>{loading ? "Please wait..." : mode === "login" ? "Sign In & Launch" : "Create Account & Launch"}</button>
        </form>
      </div>
    </div>
  );
}
