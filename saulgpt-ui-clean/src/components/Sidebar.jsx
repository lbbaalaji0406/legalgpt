import { useState, useEffect } from "react";
import axios from "axios";
import { Plus, MessageSquare, Gavel, ShieldCheck, FileSearch, BookOpen, KeyRound, Trash2, X, Loader2 } from "lucide-react";

/**
 * Left sidebar: primary actions, tools, and conversation history.
 * History uses the same endpoints as the classic ConversationsSidebar:
 *   GET /api/conversations?limit=&offset=
 */
export default function Sidebar({
  token, activeConvId, refreshTrigger, currentView, hasKey,
  onSelect, onNew, onDelete, onNavigate, onOpenEvidence, onReviewContract,
  onOpenGlossary, onOpenKey, onClose, isDrawer,
}) {
  const [convs, setConvs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const limit = 25;

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    setLoading(true);
    axios.get(`/api/conversations?limit=${limit}&offset=0`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(({ data }) => {
        setConvs(data.conversations || []);
        setTotal(data.total || 0);
      })
      .catch((e) => { if (!axios.isCancel(e)) setConvs([]); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [token, refreshTrigger]);

  function loadMore() {
    const offset = convs.length;
    if (offset >= total) return;
    setLoading(true);
    axios.get(`/api/conversations?limit=${limit}&offset=${offset}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => setConvs((prev) => [...prev, ...(data.conversations || [])]))
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  const tools = [
    { id: "chat", label: "Legal Chat", hint: "Ask or describe your problem", icon: MessageSquare, onClick: () => onNavigate("chat"), active: currentView === "chat" },
    { id: "trial", label: "Trial Studio", hint: "Practise cross-examination", icon: Gavel, onClick: () => onNavigate("trial_studio"), active: currentView === "trial_studio" },
    { id: "evidence", label: "Evidence Locker", hint: "Audio, cheques, Sec 63 BSA", icon: ShieldCheck, onClick: onOpenEvidence },
    { id: "contract", label: "Review a Contract", hint: "Upload PDF · DOCX · TXT", icon: FileSearch, onClick: onReviewContract },
    { id: "glossary", label: "Legal Glossary", hint: "Legal words, explained", icon: BookOpen, onClick: onOpenGlossary },
  ];

  return (
    <aside className="w-72 lg:w-64 h-full shrink-0 flex flex-col bg-zinc-50 dark:bg-zinc-900/60 border-r border-zinc-200 dark:border-zinc-800">
      <div className="p-4 pb-3 flex items-center gap-2">
        <button
          onClick={onNew}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-sm font-medium text-zinc-800 dark:text-zinc-100 shadow-sm hover:border-brand-500/40 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
        >
          <Plus className="w-4 h-4" /> New Conversation
        </button>
        {isDrawer && (
          <button onClick={onClose} className="p-2.5 rounded-xl text-zinc-500 hover:bg-zinc-200/60 dark:hover:bg-zinc-800" title="Close menu">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <nav className="px-3">
        <SectionLabel>Tools</SectionLabel>
        <ul className="space-y-0.5">
          {tools.map(({ id, label, hint, icon: Icon, onClick, active }) => (
            <li key={id}>
              <button
                onClick={onClick}
                title={hint}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm transition-colors ${active
                  ? "bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-400 font-medium"
                  : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/70 hover:text-zinc-900 dark:hover:text-zinc-100"}`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="truncate">{label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="mt-4 px-3 flex-1 min-h-0 flex flex-col">
        <SectionLabel>
          Conversation History {total > 0 && <span className="text-zinc-400 dark:text-zinc-600 normal-case tracking-normal font-normal">({total})</span>}
        </SectionLabel>
        <div className="flex-1 overflow-y-auto -mx-1 px-1 pb-2">
          {loading && convs.length === 0 && (
            <div className="flex items-center gap-2 px-3 py-2 text-xs text-zinc-400"><Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading…</div>
          )}
          {!loading && convs.length === 0 && (
            <p className="px-3 py-2 text-xs italic text-zinc-400 dark:text-zinc-500">No conversations yet.</p>
          )}
          <ul className="space-y-0.5">
            {convs.map((c) => {
              const active = c.id === activeConvId;
              return (
                <li key={c.id}>
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => onSelect(c.id)}
                    onKeyDown={(e) => { if (e.key === "Enter") onSelect(c.id); }}
                    className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${active
                      ? "bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-sm border border-zinc-200 dark:border-zinc-700"
                      : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/70 border border-transparent"}`}
                  >
                    <span className="flex-1 truncate">{displayTitle(c)}</span>
                    <span className="text-[10px] text-zinc-400 dark:text-zinc-500 group-hover:hidden">{relativeTime(c.updated_at)}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}
                      className="hidden group-hover:block p-0.5 text-zinc-400 hover:text-red-500"
                      title="Delete conversation"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
          {convs.length < total && (
            <button onClick={loadMore} className="w-full mt-2 py-1.5 text-xs text-brand-600 dark:text-brand-400 hover:underline">
              Load more ({total - convs.length} remaining)
            </button>
          )}
        </div>
      </div>

      <div className="p-3 border-t border-zinc-200 dark:border-zinc-800">
        <button
          onClick={onOpenKey}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/70 hover:text-zinc-900 dark:hover:text-zinc-100"
        >
          <KeyRound className="w-4 h-4" />
          <span className="flex-1 text-left">API Key</span>
          <span className={`w-2 h-2 rounded-full ${hasKey ? "bg-emerald-500" : "bg-red-500"}`} title={hasKey ? "Key active" : "Key missing"} />
        </button>
      </div>
    </aside>
  );
}

function SectionLabel({ children }) {
  return <div className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">{children}</div>;
}

function displayTitle(c) {
  const t = c.title || "";
  if (!t || t === "New Chat") return "New Chat";
  return t;
}

function relativeTime(dateStr) {
  if (!dateStr) return "";
  const diff = Math.floor((new Date() - new Date(dateStr)) / 1000);
  if (diff < 60) return "now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}
