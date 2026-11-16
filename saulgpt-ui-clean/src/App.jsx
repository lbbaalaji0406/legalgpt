import { useState, useRef, useEffect } from "react";
import axios from "axios";
import {
  Menu, Sun, Moon, LogOut, PanelRightOpen, PanelRightClose, Paperclip, ShieldCheck, ArrowUp,
  Loader2, MessagesSquare, FileSearch, PenLine, Gavel, X, KeyRound, ChevronRight,
} from "lucide-react";
import { API_BASE } from "./apiConfig";
import AuthPortal from "./components/AuthPortal";
import Sidebar from "./components/Sidebar";
import Message, { parseMeta } from "./components/Message";
import InspectorPanel from "./components/InspectorPanel";
import ApiKeyModal from "./components/ApiKeyModal";
import BrandMark from "./components/BrandMark";
import EvidenceUploader from "./features/EvidenceUploader";
import VirtualBench from "./features/VirtualBench";
import TrialStudio from "./features/TrialStudio";

/* ─────────────────────────────────────────────────────────────────
   SaulGPT — Clean UI
   Behaviour is intentionally identical to the classic UI (saulgpt-ui):
   same endpoints, same localStorage keys, same session/conversation
   handling. Only the layout and styling differ.
   ───────────────────────────────────────────────────────────────── */

function generateSessionId(convId = null) {
  if (convId) return `session_conv_${convId}`;
  const stored = localStorage.getItem("saulgpt_session_id");
  if (stored) return stored;
  const newId = `session_${Math.random().toString(36).slice(2, 9)}_${Date.now().toString(36)}`;
  localStorage.setItem("saulgpt_session_id", newId);
  return newId;
}

const SUGGESTED_QUERIES = [
  "My employer hasn't paid salary for 3 months",
  "A cheque I received was returned by the bank",
  "I need to draft a legal notice for unpaid dues",
  "What is the procedure to file an FIR?",
  "What are my rights if police arrest me?",
];

const hasValidKey = (k) => !!k && k.trim().startsWith("gsk_");

function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("saulgpt_clean_theme", dark ? "dark" : "light"); } catch {}
  }, [dark]);
  return [dark, setDark];
}

export default function App() {
  const [dark, setDark] = useTheme();
  const [token, setToken] = useState(() => localStorage.getItem("saulgpt_token"));
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("saulgpt_user");
    if (saved) { try { return JSON.parse(saved); } catch {} }
    return null;
  });
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem("saulgpt_guest_messages");
    if (saved) { try { return JSON.parse(saved); } catch {} }
    return [];
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState("");
  const [interviewActive, setInterviewActive] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(() => !localStorage.getItem("saulgpt_guest_messages"));
  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [showBenchModal, setShowBenchModal] = useState(false);
  const [benchMatter, setBenchMatter] = useState("");
  const [activeEvidence, setActiveEvidence] = useState(null);
  const [convId, setConvId] = useState(() => {
    const saved = localStorage.getItem("saulgpt_conv_id");
    if (!saved) return null;
    const n = Number(saved);
    return !isNaN(n) && n > 0 ? n : null;
  });
  const [sessionId, setSessionId] = useState(() => {
    const saved = localStorage.getItem("saulgpt_conv_id");
    const n = saved ? Number(saved) : null;
    return generateSessionId(n && !isNaN(n) ? n : null);
  });
  const [authLoading] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [currentView, setCurrentView] = useState("chat"); // 'chat' | 'trial_studio'
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [rateLimitAlert, setRateLimitAlert] = useState(false);
  const [userGroqKey, setUserGroqKey] = useState(() => localStorage.getItem("saulgpt_user_groq_key") || "");

  // Layout state (new UI only)
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(() => window.innerWidth >= 1280);
  const [inspectorTab, setInspectorTab] = useState("guide");
  const [sourceIdx, setSourceIdx] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const fileRef = useRef(null);
  const convRef = useRef(convId);

  useEffect(() => {
    const handleRateLimit = () => { setRateLimitAlert(true); setShowApiKeyModal(true); };
    window.addEventListener("saulgpt-rate-limit-hit", handleRateLimit);
    return () => window.removeEventListener("saulgpt-rate-limit-hit", handleRateLimit);
  }, []);

  // Cross-tab logout sync (same key as classic UI)
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === "saulgpt_token" && !e.newValue) { setToken(null); setUser(null); }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => { convRef.current = convId; }, [convId]);

  useEffect(() => {
    if (convId) localStorage.setItem("saulgpt_conv_id", String(convId));
    else localStorage.removeItem("saulgpt_conv_id");
  }, [convId]);

  useEffect(() => {
    const saved = localStorage.getItem("saulgpt_conv_id");
    const savedToken = localStorage.getItem("saulgpt_token");
    if (saved && savedToken) {
      const n = Number(saved);
      if (!isNaN(n) && n > 0) loadConversation(n);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!token && messages.length > 0) {
      try { localStorage.setItem("saulgpt_guest_messages", JSON.stringify(messages)); } catch {}
    } else if (!token && messages.length === 0) {
      localStorage.removeItem("saulgpt_guest_messages");
    }
  }, [messages, token]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!loading && !interviewActive) inputRef.current?.focus();
  }, [loading, interviewActive]);

  useEffect(() => {
    if (token && !hasValidKey(localStorage.getItem("saulgpt_user_groq_key"))) setShowApiKeyModal(true);
  }, [token]);

  // Auto-grow the composer
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }, [input]);

  function api() {
    const headers = {};
    const currentToken = token || localStorage.getItem("saulgpt_token");
    if (currentToken) {
      headers.Authorization = `Bearer ${currentToken}`;
      headers["X-SaulGPT-Token"] = currentToken;
    }
    const key = localStorage.getItem("saulgpt_user_groq_key");
    if (key && key.trim()) headers["X-Groq-Api-Key"] = key.trim();
    const instance = axios.create({ headers, baseURL: API_BASE || undefined });
    instance.interceptors.response.use(
      (res) => res,
      (err) => {
        if (err.response?.status === 401 && (token || localStorage.getItem("saulgpt_token"))) logout();
        const status = err.response?.status;
        const detail = err.response?.data?.detail || err.response?.data?.error || "";
        const ours = typeof detail === "string" && detail.startsWith("Too many requests");
        if (!ours && (status === 429 || (typeof detail === "string" && detail.toLowerCase().includes("rate limit")))) {
          window.dispatchEvent(new CustomEvent("saulgpt-rate-limit-hit", { detail: { error: detail } }));
        }
        return Promise.reject(err);
      }
    );
    return instance;
  }

  function handleAuth(newToken, newUser) {
    setToken(newToken);
    setUser(newUser);
    setUserGroqKey(localStorage.getItem("saulgpt_user_groq_key") || "");
    localStorage.setItem("saulgpt_token", newToken);
    localStorage.setItem("saulgpt_user", JSON.stringify(newUser));
  }

  function logout() {
    localStorage.removeItem("saulgpt_token");
    localStorage.removeItem("saulgpt_user");
    localStorage.removeItem("saulgpt_conv_id");
    localStorage.removeItem("saulgpt_session_id");
    setToken(null);
    setUser(null);
    setMessages([]);
    setConvId(null);
    setSessionId(generateSessionId());
  }

  async function loadConversation(id) {
    if (!id) return;
    try {
      if (sessionId) api().delete(`/api/draft/state/${sessionId}`).catch(() => {});
      setMessages([]);
      setShowSuggestions(false);
      setInterviewActive(false);
      setSourceIdx(null);
      setLoading(true);
      setConvId(id);
      convRef.current = id;
      const nextSid = generateSessionId(id);
      setSessionId(nextSid);
      localStorage.setItem("saulgpt_session_id", nextSid);
      localStorage.setItem("saulgpt_conv_id", String(id));

      const { data } = await api().get(`/api/conversations/${id}`);
      const loadedMsgs = (data.messages || []).map((m) => {
        let parsedMeta;
        if (m.meta) {
          try { parsedMeta = typeof m.meta === "string" ? JSON.parse(m.meta) : m.meta; } catch { parsedMeta = undefined; }
        }
        const pPct = parsedMeta?.progress_pct !== undefined ? parsedMeta.progress_pct : parsedMeta?.meta?.progress_pct;
        return {
          role: m.role,
          content: m.content || "",
          meta: parsedMeta,
          triage: parsedMeta?.triage || parsedMeta?.meta?.triage,
          interviewProgress: pPct,
        };
      });
      setMessages(loadedMsgs);
      setRefreshTrigger((p) => p + 1);
    } catch (e) {
      console.warn("Could not load conversation (may be fresh or reset):", e);
      localStorage.removeItem("saulgpt_conv_id");
      setConvId(null);
      setMessages([]);
      setShowSuggestions(true);
    } finally {
      setLoading(false);
    }
  }

  async function newConversation() {
    try {
      if (sessionId) {
        api().delete(`/api/draft/state/${sessionId}`).catch(() => {});
        api().delete(`/api/history/${sessionId}`).catch(() => {});
      }
      setMessages([]);
      setConvId(null);
      setInterviewActive(false);
      setShowSuggestions(true);
      setSourceIdx(null);
      setCurrentView("chat");
      setLoading(true);

      const { data } = await api().post("/api/conversations");
      if (data.conv_id) {
        setConvId(data.conv_id);
        const nextSid = generateSessionId(data.conv_id);
        setSessionId(nextSid);
        localStorage.setItem("saulgpt_session_id", nextSid);
        setRefreshTrigger((p) => p + 1);
      }
    } catch (e) {
      console.error("Failed to create conversation:", e);
      const freshSid = generateSessionId();
      setSessionId(freshSid);
      localStorage.setItem("saulgpt_session_id", freshSid);
      setConvId(null);
      setShowSuggestions(true);
    } finally {
      setLoading(false);
    }
  }

  function deleteConversation(id) {
    api().delete(`/api/conversations/${id}`).then(() => {
      if (convId === id) newConversation();
      else setRefreshTrigger((p) => p + 1);
    }).catch(() => {});
  }

  function requireKey(text) {
    if (hasValidKey(localStorage.getItem("saulgpt_user_groq_key"))) return true;
    setShowApiKeyModal(true);
    setMessages((prev) => [...prev, { role: "assistant", content: text }]);
    return false;
  }

  async function sendMessage(query) {
    const text = (query || input).trim();
    if (!text || loading) return;

    if (!requireKey("🔑 **Groq API Key Required**: SaulGPT requires every user to provide their own free Groq API Key (starts with `gsk_`). Please enter your key in the settings modal or generate one for free in 30 seconds at [console.groq.com/keys](https://console.groq.com/keys).")) return;

    setCurrentView("chat");
    setInput("");
    setShowSuggestions(false);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setLoadingLabel(interviewActive ? "Recording your answer…" : "Consulting the law…");

    try {
      const payload = { query: text, session_id: sessionId };
      if (convId) payload.conv_id = convId;

      const { data } = await api().post("/api/chat", payload);
      if (data.conv_id) {
        if (data.conv_id !== convId) setRefreshTrigger((p) => p + 1);
        setConvId(data.conv_id);
      }

      const isInterview = data.status === "interviewing";
      const isTriage = data.status === "triage";
      setInterviewActive(isInterview && !data.interview_complete);
      if (isTriage) setInterviewActive(false);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response || "No response generated.",
          meta: isInterview && !data.interview_complete ? null : (isTriage ? null : data),
          triage: isTriage ? data.triage : undefined,
          interviewProgress: isInterview ? data.progress_pct : undefined,
        },
      ]);
      setSourceIdx(null); // follow the newest answer
    } catch (err) {
      if (err.response?.status === 401) return; // interceptor handles logout
      let detail = "";
      if (err.response?.data?.detail) {
        const d = err.response.data.detail;
        detail = Array.isArray(d) ? d.map((x) => x.msg).join("; ") : (typeof d === "string" ? d : "");
      }
      if (err.response?.status === 404 || (detail && (detail.includes("FOREIGN KEY") || detail.includes("locked") || detail.includes("not found")))) {
        localStorage.removeItem("saulgpt_conv_id");
        setConvId(null);
      }
      if (err.response?.status === 400 && (detail.toLowerCase().includes("groq") || detail.toLowerCase().includes("api key") || detail.includes("gsk_"))) {
        setShowApiKeyModal(true);
      }
      const msg = err.response
        ? `Server error ${err.response.status}${detail ? `: ${detail}` : ""}`
        : "Cannot connect to SaulGPT API. Is api_server.py running?";
      setMessages((prev) => [...prev, { role: "assistant", content: `🚨 ${msg}` }]);
      setInterviewActive(false);
    } finally {
      setLoading(false);
      setLoadingLabel("");
      inputRef.current?.focus();
    }
  }

  async function handleFile(file) {
    if (!file || loading) return;
    if (!requireKey("🔑 **Groq API Key Required**: Please provide your free Groq API key (starts with `gsk_`) to evaluate contracts.")) return;

    setCurrentView("chat");
    setShowSuggestions(false);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: `📎 **${file.name}** (${(file.size / 1024).toFixed(0)}KB)\nEvaluating for legal flaws…` },
    ]);
    setLoading(true);
    setLoadingLabel("Parsing document…");

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoadingLabel("Running Red Pen evaluation…");
      const { data } = await api().post("/api/upload", formData, { headers: { "Content-Type": "multipart/form-data" } });
      setMessages((prev) => [...prev, { role: "assistant", content: data.response || data.error || "Evaluation complete.", meta: data.meta }]);
      setSourceIdx(null);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "🚨 File evaluation failed. Check backend." }]);
    } finally {
      setLoading(false);
      setLoadingLabel("");
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function cancelInterview() {
    if (sessionId) api().delete(`/api/draft/state/${sessionId}`).catch(() => {});
    setInterviewActive(false);
    setMessages((prev) => [...prev, { role: "assistant", content: "Draft cancelled. How else can I assist?" }]);
  }

  function handleInjectEvidence(contextText) {
    setCurrentView("chat");
    setInput(contextText);
    inputRef.current?.focus();
  }

  function handleLaunchCrossExamFromEvidence(evidenceData) {
    setActiveEvidence(evidenceData);
    let matterText = input;
    if (!matterText.trim()) {
      if (evidenceData.evidence_type === "audio") {
        const statement = evidenceData.forensic_admission?.debtor_statement || "Debt acknowledged";
        matterText = `Debtor voice admission in audio recording: "${statement}". Extended limitation under Section 18 Limitation Act. Opposing party challenges voice authenticity, tampering, and Sec 63 BSA compliance.`;
      } else {
        const clock = evidenceData.statutory_clock || {};
        matterText = `Dishonoured cheque of Rs. 15 Lakhs with bank return memo dated ${clock.bank_return_date || "recently"} for "${clock.dishonour_reason || "Funds Insufficient"}". Accused claims cheque was handed over as unfulfilled security.`;
      }
    }
    setBenchMatter(matterText);
    setShowEvidenceModal(false);
    setShowBenchModal(false);
    setCurrentView("trial_studio");
  }

  function handleOpenBench(matterText) {
    setBenchMatter(matterText || input || "Cheque bounce under Sec 138 NI Act");
    setShowEvidenceModal(false);
    setShowBenchModal(false);
    setCurrentView("trial_studio");
  }

  function openInspector(tab) {
    setInspectorTab(tab);
    setInspectorOpen(true);
  }

  function handleShowSources(idx) {
    setSourceIdx(idx);
    openInspector("sources");
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function closeDrawerThen(fn) {
    return (...args) => { setDrawerOpen(false); return fn(...args); };
  }

  if (!token) {
    return <AuthPortal onAuth={handleAuth} migrating={authLoading} />;
  }

  // Derived values
  const lastBotMsg = messages.filter((m) => m.role === "assistant" && !String(m.content).startsWith("🚨")).slice(-1)[0];
  const latestMetaIdx = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && parseMeta(messages[i]).effectiveMeta) return i;
    }
    return null;
  })();
  const activeSourceIdx = sourceIdx ?? latestMetaIdx;
  const sourceMeta = activeSourceIdx != null && messages[activeSourceIdx] ? parseMeta(messages[activeSourceIdx]).effectiveMeta : null;
  const firstUser = messages.find((m) => m.role === "user");
  const chatTitle = firstUser ? String(firstUser.content).replace(/[*📎]/g, "").split("\n")[0].trim() : "New Matter";
  const keyOk = hasValidKey(userGroqKey);

  const status = loading
    ? { label: "Thinking", cls: "bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-400 border-brand-500/20" }
    : interviewActive
      ? { label: "Drafting", cls: "bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20" }
      : { label: "Ready", cls: "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700" };

  const sidebarProps = {
    token, activeConvId: convId, refreshTrigger, currentView, hasKey: keyOk,
    onSelect: closeDrawerThen(async (id) => { setCurrentView("chat"); await loadConversation(id); }),
    onNew: closeDrawerThen(newConversation),
    onDelete: deleteConversation,
    onNavigate: closeDrawerThen((v) => setCurrentView(v)),
    onOpenEvidence: closeDrawerThen(() => setShowEvidenceModal(true)),
    onReviewContract: closeDrawerThen(() => fileRef.current?.click()),
    onOpenGlossary: closeDrawerThen(() => openInspector("glossary")),
    onOpenKey: closeDrawerThen(() => { setShowApiKeyModal(true); setRateLimitAlert(false); }),
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-zinc-950 text-zinc-700 dark:text-zinc-300">
      <input type="file" ref={fileRef} accept=".pdf,.docx,.txt" className="hidden" onChange={(e) => handleFile(e.target.files[0])} />

      {/* ═══ Top bar ═══ */}
      <header className="h-14 shrink-0 flex items-center gap-3 px-3 sm:px-5 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
        <button onClick={() => setDrawerOpen(true)} className="lg:hidden p-2 -ml-1 rounded-lg text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800" title="Menu">
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-3 min-w-0">
          <BrandMark size={32} />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-[15px] font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">Saul<span className="text-brand-500">GPT</span></span>
            </div>
            <div className="hidden sm:block text-[9px] font-medium tracking-[0.18em] uppercase text-zinc-400 dark:text-zinc-500">Indian Legal Intelligence</div>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-2">
          {keyOk ? (
            <span className="hidden md:inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Connected
            </span>
          ) : (
            <button onClick={() => setShowApiKeyModal(true)} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-500/20">
              <KeyRound className="w-3.5 h-3.5" /> Add API key
            </button>
          )}

          <div className="hidden sm:flex items-center p-0.5 rounded-full border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs font-medium">
            <button onClick={() => setDark(false)} className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${!dark ? "bg-white shadow-sm text-zinc-900" : "text-zinc-500 hover:text-zinc-300"}`}>
              <Sun className="w-3.5 h-3.5" /> Light
            </button>
            <button onClick={() => setDark(true)} className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${dark ? "bg-zinc-800 shadow-sm text-zinc-100" : "text-zinc-500 hover:text-zinc-800"}`}>
              <Moon className="w-3.5 h-3.5" /> Dark
            </button>
          </div>
          <button onClick={() => setDark(!dark)} className="sm:hidden p-2 rounded-lg text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800" title="Toggle theme">
            {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <span className="hidden lg:block max-w-[160px] truncate text-xs text-zinc-500 dark:text-zinc-400" title={user?.email}>
            {user?.username || user?.email || "User"}
          </span>
          <button onClick={logout} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-500/30 hover:bg-red-50 dark:hover:bg-red-500/10" title="Sign out">
            <LogOut className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Log Out</span>
          </button>
        </div>
      </header>

      <div className="flex-1 flex min-h-0 relative">
        {/* ═══ Left sidebar ═══ */}
        <div className="hidden lg:block h-full">
          <Sidebar {...sidebarProps} />
        </div>
        {drawerOpen && (
          <div className="lg:hidden fixed inset-0 z-40 flex">
            <div className="absolute inset-0 bg-black/40" onClick={() => setDrawerOpen(false)} />
            <div className="relative h-full sg-fade-in">
              <Sidebar {...sidebarProps} isDrawer onClose={() => setDrawerOpen(false)} />
            </div>
          </div>
        )}

        {/* ═══ Center ═══ */}
        <main className="flex-1 min-w-0 flex flex-col">
          {currentView === "trial_studio" ? (
            <div className="flex-1 min-h-0 overflow-auto">
              <TrialStudio
                sessionId={sessionId}
                token={token}
                groundedEvidence={activeEvidence}
                initialMatter={benchMatter}
                onBack={() => setCurrentView("chat")}
                onAttachEvidence={() => setShowEvidenceModal(true)}
              />
            </div>
          ) : (
            <>
              <div className="h-12 shrink-0 flex items-center gap-3 px-4 sm:px-6 border-b border-zinc-200 dark:border-zinc-800">
                <h1 className="flex-1 min-w-0 truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100" title={chatTitle}>{chatTitle}</h1>
                <span className={`px-2.5 py-0.5 rounded-full border text-[10px] font-mono font-medium uppercase tracking-wider ${status.cls}`}>{status.label}</span>
                <button
                  onClick={() => setInspectorOpen(!inspectorOpen)}
                  className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                  title={inspectorOpen ? "Hide side panel" : "Show sources, glossary & guide"}
                >
                  {inspectorOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
                </button>
              </div>

              <div
                className="flex-1 min-h-0 overflow-y-auto"
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
              >
                <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-6">
                  {messages.length === 0 && !loading && (
                    <Welcome
                      showSuggestions={showSuggestions}
                      onAsk={() => inputRef.current?.focus()}
                      onContract={() => fileRef.current?.click()}
                      onDraft={() => sendMessage("I need to draft a legal notice")}
                      onTrial={() => setCurrentView("trial_studio")}
                      onSuggest={sendMessage}
                    />
                  )}

                  {messages.map((msg, i) => {
                    const hasPriorBNS = messages.slice(0, i).some((m) => {
                      const mMeta = m.meta?.meta || m.meta;
                      return m.role === "assistant" && mMeta?.remapped_laws && Object.keys(mMeta.remapped_laws).length > 0;
                    });
                    return (
                      <Message
                        key={i}
                        index={i}
                        msg={msg}
                        busy={loading}
                        isCompactBNS={hasPriorBNS}
                        onTriageChoice={sendMessage}
                        onOpenBench={handleOpenBench}
                        onShowSources={handleShowSources}
                      />
                    );
                  })}

                  {loading && (
                    <div className="flex items-center gap-3 sg-fade-in">
                      <BrandMark size={28} />
                      <div className="flex items-center gap-3 px-4 py-2.5 rounded-2xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                        <div className="flex gap-1"><span className="sg-dot" /><span className="sg-dot" /><span className="sg-dot" /></div>
                        {loadingLabel && <span className="text-xs text-zinc-500 dark:text-zinc-400">{loadingLabel}</span>}
                      </div>
                    </div>
                  )}
                  <div ref={bottomRef} />
                </div>
              </div>

              {/* ═══ Composer ═══ */}
              <div className="shrink-0 px-4 sm:px-6 pb-4 pt-2">
                <div className="max-w-3xl mx-auto">
                  {interviewActive && (
                    <div className="mb-2 flex items-center gap-2 px-3 py-2 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 text-xs text-amber-800 dark:text-amber-300">
                      <PenLine className="w-3.5 h-3.5 shrink-0" />
                      <span className="flex-1">Drafting mode — answer the question above, then press Enter.</span>
                      <button onClick={cancelInterview} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-medium hover:bg-amber-100 dark:hover:bg-amber-500/20">
                        <X className="w-3 h-3" /> Cancel draft
                      </button>
                    </div>
                  )}

                  <div className={`rounded-2xl border bg-white dark:bg-zinc-900 shadow-sm transition-colors ${dragOver
                    ? "border-brand-500 ring-4 ring-brand-500/10"
                    : "border-zinc-200 dark:border-zinc-800 focus-within:border-brand-500/60 focus-within:ring-4 focus-within:ring-brand-500/10"}`}>
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKey}
                      rows={1}
                      disabled={loading}
                      placeholder={interviewActive ? "Type your answer…" : "Describe your legal problem or ask a question… (English or Hindi)"}
                      className="block w-full resize-none bg-transparent px-4 pt-3.5 pb-2 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 outline-none disabled:opacity-60"
                      style={{ minHeight: 52 }}
                    />
                    <div className="flex items-center gap-1 px-2.5 pb-2.5">
                      {!interviewActive && (
                        <>
                          <ComposerBtn onClick={() => fileRef.current?.click()} disabled={loading} title="Review a contract (PDF · DOCX · TXT, max 50MB)">
                            <Paperclip className="w-4 h-4" /> <span className="hidden sm:inline">Contract</span>
                          </ComposerBtn>
                          <ComposerBtn onClick={() => setShowEvidenceModal(true)} disabled={loading} title="Attach evidence — voice notes, cheques (Sec 63 BSA)">
                            <ShieldCheck className="w-4 h-4" /> <span className="hidden sm:inline">Evidence</span>
                          </ComposerBtn>
                        </>
                      )}
                      <span className="ml-auto hidden sm:block text-[10px] text-zinc-400 dark:text-zinc-500 mr-2">Enter to send · Shift+Enter for new line</span>
                      <button
                        onClick={() => sendMessage()}
                        disabled={loading || !input.trim()}
                        className="ml-auto sm:ml-0 w-9 h-9 rounded-full flex items-center justify-center bg-brand-500 hover:bg-brand-600 disabled:bg-zinc-200 dark:disabled:bg-zinc-800 disabled:text-zinc-400 text-white shadow-sm transition-colors"
                        title="Send"
                      >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowUp className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                  <p className="mt-2 text-center text-[10px] text-zinc-400 dark:text-zinc-500">
                    Procedural guidance only · Not legal advice · Consult a qualified advocate
                  </p>
                </div>
              </div>
            </>
          )}
        </main>

        {/* ═══ Right inspector ═══ */}
        {inspectorOpen && currentView === "chat" && (
          <>
            <div className="xl:hidden fixed inset-0 z-30 bg-black/30" onClick={() => setInspectorOpen(false)} />
            <div className="fixed xl:static right-0 top-14 bottom-0 z-30 w-[88vw] max-w-sm xl:w-80 xl:max-w-none shrink-0 sg-fade-in">
              <InspectorPanel
                tab={inspectorTab}
                onTab={setInspectorTab}
                sourceMeta={sourceMeta}
                lastBotText={lastBotMsg?.content}
                onClose={() => setInspectorOpen(false)}
                onSuggest={(q) => { if (window.innerWidth < 1280) setInspectorOpen(false); sendMessage(q); }}
              />
            </div>
          </>
        )}
      </div>

      {/* ═══ Modals (shared feature components) ═══ */}
      <EvidenceUploader
        isOpen={showEvidenceModal}
        onClose={() => setShowEvidenceModal(false)}
        onInjectContext={handleInjectEvidence}
        onLaunchCrossExam={handleLaunchCrossExamFromEvidence}
        sessionId={sessionId}
      />
      <VirtualBench
        isOpen={showBenchModal}
        onClose={() => setShowBenchModal(false)}
        initialMatter={benchMatter}
        connectedEvidence={activeEvidence}
        onOpenEvidenceUploader={() => { setShowBenchModal(false); setShowEvidenceModal(true); }}
      />
      <ApiKeyModal
        isOpen={showApiKeyModal}
        onClose={() => { setShowApiKeyModal(false); setRateLimitAlert(false); }}
        rateLimitAlert={rateLimitAlert}
        onKeyUpdated={(k) => setUserGroqKey(k)}
      />
    </div>
  );
}

function ComposerBtn({ children, onClick, disabled, title }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-800 dark:hover:text-zinc-200 disabled:opacity-50 transition-colors"
    >
      {children}
    </button>
  );
}

function Welcome({ showSuggestions, onAsk, onContract, onDraft, onTrial, onSuggest }) {
  const cards = [
    { icon: MessagesSquare, title: "Ask a legal question", text: "Rights, sections, procedures", onClick: onAsk },
    { icon: PenLine, title: "Draft a document", text: "Legal notice, FIR, rent deed", onClick: onDraft },
    { icon: FileSearch, title: "Review a contract", text: "Upload PDF · DOCX · TXT", onClick: onContract },
    { icon: Gavel, title: "Practise in Trial Studio", text: "Face a mock cross-examination", onClick: onTrial },
  ];
  return (
    <div className="pt-6 sm:pt-10 text-center sg-fade-in">
      <div className="mx-auto w-14 h-14 rounded-full flex items-center justify-center bg-brand-50 dark:bg-brand-500/10 border border-brand-100 dark:border-brand-500/20">
        <BrandMark size={34} />
      </div>
      <h2 className="mt-5 text-xl font-semibold text-zinc-900 dark:text-zinc-100">Welcome to SaulGPT</h2>
      <p className="mt-2 max-w-md mx-auto text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">
        Tell me what happened in your own words. I'll find the Indian laws that apply and show you clear options.
      </p>

      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
        {cards.map(({ icon: Icon, title, text, onClick }) => (
          <button
            key={title}
            onClick={onClick}
            className="group flex items-center gap-3 p-4 text-left rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-brand-500/50 hover:shadow-sm transition-all"
          >
            <span className="w-9 h-9 shrink-0 rounded-xl bg-zinc-100 dark:bg-zinc-800 group-hover:bg-brand-50 dark:group-hover:bg-brand-500/10 text-zinc-500 group-hover:text-brand-600 dark:group-hover:text-brand-400 flex items-center justify-center transition-colors">
              <Icon className="w-4 h-4" />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-medium text-zinc-900 dark:text-zinc-100">{title}</span>
              <span className="block text-xs text-zinc-500 dark:text-zinc-400">{text}</span>
            </span>
          </button>
        ))}
      </div>

      {showSuggestions && (
        <div className="mt-8 text-left">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">Or start with a common matter</p>
          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 divide-y divide-zinc-200 dark:divide-zinc-800 overflow-hidden bg-white dark:bg-zinc-900">
            {SUGGESTED_QUERIES.map((q) => (
              <button
                key={q}
                onClick={() => onSuggest(q)}
                className="group w-full flex items-center gap-3 px-4 py-3 text-left text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800/60"
              >
                <span className="flex-1">{q}</span>
                <ChevronRight className="w-4 h-4 text-zinc-300 dark:text-zinc-600 group-hover:text-brand-500" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
