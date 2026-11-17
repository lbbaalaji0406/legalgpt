import { useState, useEffect } from "react";
import axios from "axios";
import { KeyRound, X, Eye, EyeOff, AlertTriangle, CircleCheck, CircleAlert, ExternalLink, Zap } from "lucide-react";

/**
 * Bring-Your-Own-Key modal.
 * Same behaviour and props as the classic UI's ApiKeyModal
 * (also used by Trial Studio): validates via POST /api/keys/validate and
 * stores the key only in localStorage ("saulgpt_user_groq_key").
 */
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
        setTestResult({ success: true, message: `Verified! Access granted with ${res.data.models_available || 10}+ models available.` });
      } else {
        setTestResult({ success: false, message: res.data?.error || "Invalid Groq API key. Check console.groq.com/keys" });
      }
    } catch (err) {
      setTestResult({ success: false, message: err.response?.data?.error || "Verification request failed. Check server connection." });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = () => {
    const trimmed = apiKey.trim();
    if (!trimmed) {
      setTestResult({ success: false, message: "Groq API key is required. Please paste your key (starts with gsk_)." });
      return;
    }
    if (!trimmed.startsWith("gsk_")) {
      setTestResult({ success: false, message: "Invalid key format. Groq API keys must begin with 'gsk_'." });
      return;
    }
    localStorage.setItem("saulgpt_user_groq_key", trimmed);
    setActiveStoredKey(trimmed);
    if (onKeyUpdated) onKeyUpdated(trimmed);
    onClose();
  };

  const masked = activeStoredKey && activeStoredKey.length >= 12
    ? `${activeStoredKey.slice(0, 7)}••••••••${activeStoredKey.slice(-4)}`
    : "";

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" onClick={onClose}>
      <div
        className="w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl sg-fade-in"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="api-key-title"
      >
        <div className="flex items-start justify-between p-5 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand-50 dark:bg-brand-500/10 text-brand-600 dark:text-brand-400 flex items-center justify-center">
              <KeyRound className="w-4 h-4" />
            </div>
            <div>
              <h3 id="api-key-title" className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Your Groq API key</h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Free · stays in this browser only</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 dark:hover:text-zinc-200" title="Close" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {rateLimitAlert && (
            <div className="flex gap-3 p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 text-amber-800 dark:text-amber-300">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="text-xs leading-relaxed">
                <strong className="font-semibold">Rate limit reached (429).</strong> The shared free quota is used up for now.
                Add your own free key below to continue immediately.
              </div>
            </div>
          )}

          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-500 dark:text-zinc-400">Status</span>
            {activeStoredKey ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Key active <span className="font-mono">{masked}</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-500/20 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500" /> Key required to chat
              </span>
            )}
          </div>

          <div>
            <label htmlFor="groq-key-input" className="block text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1.5">
              Groq API key
            </label>
            <div className="relative">
              <input
                id="groq-key-input"
                type={showKey ? "text" : "password"}
                placeholder="gsk_xxxxxxxxxxxxxxxxxxxxxxxx"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                autoComplete="off"
                spellCheck="false"
                className="w-full pl-3 pr-10 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-sm font-mono text-zinc-800 dark:text-zinc-100 placeholder-zinc-400 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
                title={showKey ? "Hide key" : "Show key"}
                aria-label={showKey ? "Hide key" : "Show key"}
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {testResult && (
            <div className={`flex gap-2 p-3 rounded-xl text-xs border ${testResult.success
              ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400"
              : "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/20 text-red-600 dark:text-red-400"}`}>
              {testResult.success ? <CircleCheck className="w-4 h-4 shrink-0" /> : <CircleAlert className="w-4 h-4 shrink-0" />}
              <p>{testResult.message}</p>
            </div>
          )}

          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">Don't have a key?</span>
              <a href="https://console.groq.com/keys" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-brand-600 dark:text-brand-400 font-medium hover:underline">
                Get one free <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            1. Sign in at <strong>console.groq.com</strong> with Google or GitHub.<br />
            2. Click <strong>Create API Key</strong> and paste it above.<br />
            3. It's stored only in your browser — never in our database.
          </div>
        </div>

        <div className="flex justify-end gap-2 p-4 border-t border-zinc-200 dark:border-zinc-800">
          <button
            onClick={handleTestKey}
            disabled={loading || !apiKey.trim()}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-50"
          >
            <Zap className="w-3.5 h-3.5" /> {loading ? "Testing…" : "Test connection"}
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-brand-500 hover:bg-brand-600 text-white shadow-lg shadow-brand-500/20"
          >
            Save key
          </button>
        </div>
      </div>
    </div>
  );
}
