import { useState } from "react";
import { Library, BookOpen, HelpCircle, X, AlertTriangle, CircleCheck, Quote, Lightbulb } from "lucide-react";
import { scanForTerms, getCategories, GLOSSARY } from "../features/LegalGlossary";
import { MODES } from "./Message";

/**
 * Right panel — the "inspector". Three tabs:
 *  • Sources  — citations / validation / confidence for the selected answer
 *               (the classic UI's collapsible PipelineMeta)
 *  • Glossary — legal terms found in the latest answer + browse all
 *               (the classic UI's glossary sidebar)
 *  • Guide    — how to use SaulGPT, in four steps
 */
export default function InspectorPanel({ tab, onTab, sourceMeta, lastBotText, onClose, onSuggest }) {
  const tabs = [
    { id: "sources", label: "Sources", icon: Library },
    { id: "glossary", label: "Glossary", icon: BookOpen },
    { id: "guide", label: "Guide", icon: HelpCircle },
  ];

  return (
    <aside className="w-full h-full flex flex-col bg-zinc-50 dark:bg-zinc-900/60 border-l border-zinc-200 dark:border-zinc-800">
      <div className="flex items-center gap-1 p-2 border-b border-zinc-200 dark:border-zinc-800">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onTab(id)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-lg text-xs font-medium transition-colors ${tab === id
              ? "bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-sm border border-zinc-200 dark:border-zinc-700"
              : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200 border border-transparent"}`}
          >
            <Icon className="w-3.5 h-3.5" /> {label}
          </button>
        ))}
        <button onClick={onClose} className="p-2 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-200/50 dark:hover:bg-zinc-800" title="Close panel" aria-label="Close side panel">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {tab === "sources" && <SourcesTab meta={sourceMeta} />}
        {tab === "glossary" && <GlossaryTab lastBotText={lastBotText} />}
        {tab === "guide" && <GuideTab onSuggest={onSuggest} />}
      </div>
    </aside>
  );
}

function Empty({ icon: Icon, title, text }) {
  return (
    <div className="h-full min-h-[240px] flex flex-col items-center justify-center text-center px-4">
      <Icon className="w-10 h-10 text-zinc-300 dark:text-zinc-700" strokeWidth={1.5} />
      <p className="mt-3 text-sm font-medium text-zinc-600 dark:text-zinc-300">{title}</p>
      <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-500 leading-relaxed">{text}</p>
    </div>
  );
}

function Section({ title, children, tone }) {
  return (
    <section className={`mb-4 p-3 rounded-xl border ${tone === "warn"
      ? "border-amber-200 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-500/5"
      : "border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900"}`}>
      <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">{title}</h4>
      {children}
    </section>
  );
}

function SourcesTab({ meta }) {
  if (!meta) {
    return <Empty icon={Library} title="No answer selected" text="Ask a question, then click “Sources” under an answer to see which laws it relied on and how it was validated." />;
  }
  const mode = MODES[meta.mode_used];
  const conf = meta.confidence_score > 0 ? Math.round(meta.confidence_score * 100) : null;

  return (
    <div>
      <Section title="Overview">
        <dl className="grid grid-cols-2 gap-y-2 text-xs">
          {mode && (<><dt className="text-zinc-500">Mode</dt><dd className="text-zinc-900 dark:text-zinc-100 font-medium text-right">{mode.label}</dd></>)}
          {meta.domain && (<><dt className="text-zinc-500">Area of law</dt><dd className="text-zinc-900 dark:text-zinc-100 font-medium text-right capitalize">{meta.domain}</dd></>)}
          {meta.laws_retrieved > 0 && (<><dt className="text-zinc-500">Laws retrieved</dt><dd className="text-zinc-900 dark:text-zinc-100 font-medium text-right">{meta.laws_retrieved}</dd></>)}
          {meta.graph_insights?.length > 0 && (<><dt className="text-zinc-500">Graph insights</dt><dd className="text-zinc-900 dark:text-zinc-100 font-medium text-right">{meta.graph_insights.length}</dd></>)}
          {meta.case_law_found && (<><dt className="text-zinc-500">Case law</dt><dd className="text-zinc-900 dark:text-zinc-100 font-medium text-right">Found</dd></>)}
          {meta.elapsed_seconds > 0 && (<><dt className="text-zinc-500">Time</dt><dd className="text-zinc-900 dark:text-zinc-100 font-medium text-right">{meta.elapsed_seconds}s</dd></>)}
        </dl>
      </Section>

      <Section title="Validation">
        <div className={`flex items-center gap-2 text-xs font-medium ${meta.is_hallucinating ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400"}`}>
          {meta.is_hallucinating ? <AlertTriangle className="w-4 h-4" /> : <CircleCheck className="w-4 h-4" />}
          {meta.is_hallucinating ? "Possible unsupported claims — verify" : "Passed fact-check against sources"}
        </div>
        {conf !== null && (
          <div className="mt-3">
            <div className="flex justify-between text-[11px] text-zinc-500 mb-1"><span>Confidence</span><span className="font-mono">{conf}%</span></div>
            <div className="h-1.5 rounded-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
              <div className={`h-full rounded-full ${conf >= 70 ? "bg-emerald-500" : conf >= 40 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${conf}%` }} />
            </div>
          </div>
        )}
      </Section>

      {meta.citations?.length > 0 && (
        <Section title={`Citations (${meta.citations.length})`}>
          <ul className="space-y-1.5">
            {meta.citations.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <Quote className="w-3 h-3 mt-0.5 shrink-0 text-zinc-400" />
                <span className={c.is_repealed ? "text-amber-700 dark:text-amber-400" : "text-zinc-700 dark:text-zinc-300"}>
                  {c.act_name?.replace("_from_db", "")}
                  {c.section_number && <span className="font-mono"> § {c.section_number}</span>}
                  {c.is_repealed && " (repealed)"}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {meta.repealed_warnings?.length > 0 && (
        <Section title="Repealed laws" tone="warn">
          {meta.repealed_warnings.map((w, i) => <p key={i} className="text-xs text-amber-800 dark:text-amber-300 mb-1">{w}</p>)}
        </Section>
      )}
      {meta.struck_down_warnings?.length > 0 && (
        <Section title="Struck down" tone="warn">
          {meta.struck_down_warnings.map((w, i) => <p key={i} className="text-xs text-amber-800 dark:text-amber-300 mb-1">{w}</p>)}
        </Section>
      )}
    </div>
  );
}

function TermCard({ name, term }) {
  return (
    <div className="p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
      <div className="flex items-center justify-between gap-2 mb-1">
        <strong className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 capitalize">{name}</strong>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500">{term.category}</span>
      </div>
      <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">{term.simple_def || term.def}</p>
      {term.analogy && (
        <p className="mt-2 flex gap-1.5 text-xs text-brand-700 dark:text-brand-400 bg-brand-50 dark:bg-brand-500/10 rounded-lg p-2">
          <Lightbulb className="w-3.5 h-3.5 shrink-0 mt-0.5" /> <em>{term.analogy}</em>
        </p>
      )}
      {term.src && <p className="mt-1.5 text-[10px] text-zinc-400">Source: {term.src}</p>}
    </div>
  );
}

function GlossaryTab({ lastBotText }) {
  const [category, setCategory] = useState("All");
  const [query, setQuery] = useState("");
  const found = lastBotText ? scanForTerms(lastBotText) : [];
  const categories = ["All", ...getCategories()];

  const q = query.trim().toLowerCase();
  const allKeys = Object.keys(GLOSSARY).filter((k) =>
    (category === "All" || GLOSSARY[k].category === category) && (!q || k.toLowerCase().includes(q))
  );

  return (
    <div className="space-y-4">
      <div>
        <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">In the latest answer</h4>
        {found.length === 0 ? (
          <p className="text-xs text-zinc-500">No legal terms detected yet. Ask a question to see terms explained here.</p>
        ) : (
          <div className="space-y-2">
            {found.map((t, i) => <TermCard key={i} name={t.term} term={t} />)}
          </div>
        )}
      </div>

      <div>
        <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">Browse all terms</h4>
        <div className="flex gap-2 mb-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search a term…"
            className="flex-1 min-w-0 px-3 py-2 rounded-lg text-xs bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-100 placeholder-zinc-400 outline-none focus:border-brand-500"
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="max-w-[45%] px-2 py-2 rounded-lg text-xs bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-200 outline-none"
          >
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="space-y-2">
          {allKeys.slice(0, 30).map((k) => <TermCard key={k} name={k} term={GLOSSARY[k]} />)}
          {allKeys.length === 0 && <p className="text-xs text-zinc-500">No matching terms.</p>}
          {allKeys.length > 30 && <p className="text-[11px] text-zinc-400 text-center">Showing 30 of {allKeys.length} — search to narrow down.</p>}
        </div>
      </div>
    </div>
  );
}

function GuideTab({ onSuggest }) {
  const steps = [
    { t: "Describe your problem", d: "Write it the way you'd tell a friend — what happened, when, and what you want. English or Hindi." },
    { t: "Answer a few questions", d: "For personal matters SaulGPT asks up to 3 short questions to understand your situation." },
    { t: "Pick an option", d: "You'll get 4 options (A–D). Choose one to get a step-by-step path or to draft a document." },
    { t: "Download & act", d: "Drafts download as editable .docx. Answers can be saved as PDF. Use Trial Studio to rehearse." },
  ];
  return (
    <div>
      <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">How SaulGPT works</h3>
      <ol className="mt-3 space-y-3">
        {steps.map((s, i) => (
          <li key={i} className="flex gap-3">
            <span className="w-6 h-6 shrink-0 rounded-full bg-brand-500 text-white text-xs font-semibold flex items-center justify-center">{i + 1}</span>
            <div>
              <div className="text-sm font-medium text-zinc-800 dark:text-zinc-200">{s.t}</div>
              <div className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">{s.d}</div>
            </div>
          </li>
        ))}
      </ol>

      <div className="mt-5 p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs text-zinc-600 dark:text-zinc-400 space-y-1.5">
        <p><strong className="text-zinc-800 dark:text-zinc-200">Paperclip</strong> in the message box → review a contract.</p>
        <p><strong className="text-zinc-800 dark:text-zinc-200">Shield</strong> → attach evidence (voice notes, cheques) with a Sec 63 BSA certificate.</p>
        <p><strong className="text-zinc-800 dark:text-zinc-200">Advocate Mode</strong> on the options card → deep IRAC analysis arguing both sides.</p>
      </div>

      <button
        onClick={() => onSuggest("What is the procedure to file an FIR?")}
        className="mt-4 w-full py-2 rounded-xl text-xs font-semibold border border-brand-500/30 text-brand-700 dark:text-brand-400 bg-brand-50 dark:bg-brand-500/10 hover:bg-brand-100 dark:hover:bg-brand-500/20"
      >
        Try an example question
      </button>

      <p className="mt-4 text-[11px] text-zinc-400 leading-relaxed">
        SaulGPT gives procedural guidance, not legal advice. For your specific case, consult a qualified advocate.
      </p>
    </div>
  );
}
