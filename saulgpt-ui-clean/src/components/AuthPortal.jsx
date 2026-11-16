import { useState } from "react";
import axios from "axios";
import { Mail, Lock, User, KeyRound, ExternalLink, Loader2, MessagesSquare, FileText, Gavel, ShieldCheck } from "lucide-react";
import BrandMark from "./BrandMark";

/**
 * Sign in / Sign up. Same API contract as the classic AuthPage:
 * POST /api/auth/{login|signup}, Groq key required and stored locally.
 */
export default function AuthPortal({ onAuth, migrating }) {
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
      setError("A Groq API key is required. Paste your free key (starts with gsk_) from console.groq.com/keys.");
      return;
    }
    if (!trimmedKey.startsWith("gsk_")) {
      setError("Invalid API key format. Groq API keys begin with 'gsk_'.");
      return;
    }

    setLoading(true);
    try {
      localStorage.setItem("saulgpt_user_groq_key", trimmedKey);
      const payload = mode === "signup" ? { email, password, username } : { email, password };
      const { data } = await axios.post(`/api/auth/${mode}`, payload);
      const user = { id: data.user_id, email: data.email, username: data.username };
      localStorage.setItem("saulgpt_token", data.token);
      localStorage.setItem("saulgpt_user", JSON.stringify(user));
      onAuth(data.token, user);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const inputCls =
    "w-full pl-10 pr-4 py-3 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl " +
    "focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 text-sm text-zinc-800 dark:text-zinc-100 " +
    "placeholder-zinc-400 dark:placeholder-zinc-600 outline-none transition-all";

  return (
    <div className="min-h-full flex items-center justify-center bg-zinc-100 dark:bg-zinc-950 p-4 sm:p-6">
      <div className="w-full max-w-5xl grid md:grid-cols-2 rounded-3xl overflow-hidden shadow-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        {/* ── Left: what SaulGPT does ── */}
        <div className="hidden md:flex flex-col justify-between p-10 bg-gradient-to-br from-indigo-600 via-brand-600 to-violet-700 text-white">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/20 text-xs font-semibold tracking-wide">
              <BrandMark size={20} className="!bg-white/20 !shadow-none" /> SAULGPT
            </div>
            <h1 className="mt-8 text-3xl font-bold leading-tight tracking-tight">
              Indian legal help,<br />in plain language.
            </h1>
            <p className="mt-4 text-sm text-white/80 leading-relaxed max-w-sm">
              Describe your problem the way you'd tell a friend. SaulGPT finds the relevant
              Indian laws (BNS, BNSS, BSA, Constitution and more) and tells you your options.
            </p>
          </div>

          <ul className="mt-10 space-y-3">
            {[
              { icon: MessagesSquare, title: "Ask anything", text: "Rights, procedures, sections — in English or Hindi." },
              { icon: FileText, title: "Draft documents", text: "Legal notices, FIR complaints, rental agreements (.docx)." },
              { icon: ShieldCheck, title: "Review contracts", text: "Upload a PDF/DOCX and get the risky clauses flagged." },
              { icon: Gavel, title: "Practise for court", text: "Trial Studio cross-examines your case before the judge does." },
            ].map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-3 p-3 rounded-2xl bg-white/10 border border-white/15">
                <Icon className="w-4 h-4 mt-0.5 shrink-0" />
                <div>
                  <div className="text-sm font-semibold">{title}</div>
                  <div className="text-xs text-white/75">{text}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* ── Right: form ── */}
        <div className="p-6 sm:p-10 flex flex-col justify-center">
          {migrating ? (
            <div className="text-center py-16">
              <Loader2 className="w-8 h-8 mx-auto animate-spin text-brand-500" />
              <h2 className="mt-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">Saving your session</h2>
              <p className="mt-1 text-sm text-zinc-500">Moving your chat history into your account…</p>
            </div>
          ) : (
            <>
              <div className="text-center mb-6">
                <BrandMark size={44} className="mx-auto" />
                <h2 className="mt-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
                  {mode === "login" ? "Welcome back" : "Create your account"}
                </h2>
                <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                  {mode === "login" ? "Sign in to continue to SaulGPT." : "It takes less than a minute."}
                </p>
              </div>

              <div className="grid grid-cols-2 p-1 mb-5 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-sm font-medium">
                {["login", "signup"].map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => { setMode(m); setError(""); }}
                    className={`py-2 rounded-lg transition-all ${mode === m
                      ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-sm"
                      : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"}`}
                  >
                    {m === "login" ? "Sign in" : "Sign up"}
                  </button>
                ))}
              </div>

              <form onSubmit={handleSubmit} className="space-y-3">
                <Field label="Email address" icon={Mail}>
                  <input className={inputCls} type="email" placeholder="name@domain.com" autoComplete="email"
                    value={email} onChange={(e) => setEmail(e.target.value)} required />
                </Field>
                {mode === "signup" && (
                  <Field label="Name (optional)" icon={User}>
                    <input className={inputCls} type="text" placeholder="How should we greet you?"
                      value={username} onChange={(e) => setUsername(e.target.value)} />
                  </Field>
                )}
                <Field label="Password" icon={Lock}>
                  <input className={inputCls} type="password" placeholder="At least 4 characters"
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                    value={password} onChange={(e) => setPassword(e.target.value)} required minLength={4} />
                </Field>

                <div className="pt-1">
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                      Groq API key <span className="text-red-500">*</span>
                    </label>
                    <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-brand-600 dark:text-brand-400 hover:underline">
                      Get a free key <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                  <div className="relative">
                    <KeyRound className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" />
                    <input className={`${inputCls} font-mono`} type="password" placeholder="gsk_…"
                      value={groqKey} onChange={(e) => setGroqKey(e.target.value)} required />
                  </div>
                  <p className="mt-1.5 text-[11px] text-zinc-500 dark:text-zinc-500">
                    Free, takes 30 seconds. Stored only in this browser.
                  </p>
                </div>

                {error && (
                  <p className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-xl px-3 py-2">
                    {error}
                  </p>
                )}

                <button
                  disabled={loading}
                  className="w-full mt-2 py-3 bg-brand-500 hover:bg-brand-600 disabled:opacity-60 text-white text-sm font-semibold rounded-xl shadow-lg shadow-brand-500/20 transition-all flex items-center justify-center gap-2"
                >
                  {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                  {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
                </button>
              </form>

              <p className="mt-6 text-center text-[11px] text-zinc-400 dark:text-zinc-500">
                Procedural guidance only · Not legal advice · Consult a qualified advocate
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, icon: Icon, children }) {
  return (
    <div>
      <label className="block text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1.5">{label}</label>
      <div className="relative">
        <Icon className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
        {children}
      </div>
    </div>
  );
}
