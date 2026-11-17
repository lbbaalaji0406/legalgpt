import { useState } from "react";
import { ArrowRight, AlertTriangle, Info, ChevronDown, HelpCircle, Scale, Compass } from "lucide-react";

/**
 * Strategy options returned by the triage/strategy phase.
 * Same behaviour as the classic TriageCards: clicking an option sends its id
 * (path_a…path_d), plus "explain" and "advocate" actions.
 */
const SWOT = {
  strengths:     { label: "Strengths",     cls: "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10" },
  weaknesses:    { label: "Weaknesses",    cls: "border-red-500 bg-red-50 dark:bg-red-500/10" },
  opportunities: { label: "Opportunities", cls: "border-brand-500 bg-brand-50 dark:bg-brand-500/10" },
  threats:       { label: "Threats",       cls: "border-amber-500 bg-amber-50 dark:bg-amber-500/10" },
};

export default function StrategyCards({ triage, onChoose, disabled }) {
  const [showSwot, setShowSwot] = useState(false);
  const swot = triage?.swot_analysis;
  const options = triage?.options || [];
  const allowAdvocate = triage?.allow_advocate !== false;

  if (triage?.is_explanation || triage?.is_intake_needed) return null;
  if (!options.length) return null;

  return (
    <div className="mt-3 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <Compass className="w-4 h-4 text-brand-500" />
        <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Your options</span>
        <span className="text-xs text-zinc-500 dark:text-zinc-400">— pick one to continue</span>
      </div>

      <div className="p-3 space-y-2">
        {triage.limitation_warning && <Banner type="warning" text={triage.limitation_warning} />}
        {triage.jurisdiction_note && <Banner type="note" text={triage.jurisdiction_note} />}

        <div className="grid sm:grid-cols-2 gap-2">
          {options.map((opt, i) => (
            <button
              key={opt.id}
              disabled={disabled}
              onClick={() => onChoose(opt.id)}
              className="group text-left p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 hover:border-brand-500/60 hover:bg-brand-50/50 dark:hover:bg-brand-500/5 transition-colors disabled:opacity-60"
            >
              <div className="flex items-start gap-2">
                <span className="mt-0.5 w-5 h-5 shrink-0 rounded-md bg-zinc-100 dark:bg-zinc-800 text-[10px] font-semibold text-zinc-500 flex items-center justify-center">
                  {String.fromCharCode(65 + i)}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{opt.label}</div>
                  {opt.description && <div className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">{opt.description}</div>}
                </div>
                <ArrowRight className="w-4 h-4 mt-0.5 shrink-0 text-zinc-300 group-hover:text-brand-500 transition-colors" />
              </div>
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2 pt-1">
          {swot && (
            <Action onClick={() => setShowSwot(!showSwot)}>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showSwot ? "rotate-180" : ""}`} />
              {showSwot ? "Hide analysis" : "Show strengths & risks"}
            </Action>
          )}
          {triage.allow_explanation && (
            <Action onClick={() => onChoose("explain")} disabled={disabled}>
              <HelpCircle className="w-3.5 h-3.5" /> Explain these options
            </Action>
          )}
          {allowAdvocate && (
            <Action onClick={() => onChoose("advocate")} disabled={disabled} primary>
              <Scale className="w-3.5 h-3.5" /> Advocate Mode (deep analysis)
            </Action>
          )}
        </div>

        {showSwot && swot && (
          <div className="grid sm:grid-cols-2 gap-2 pt-1">
            {Object.keys(SWOT).map((k) =>
              swot[k]?.length ? (
                <div key={k} className={`p-3 rounded-xl border-l-4 ${SWOT[k].cls}`}>
                  <div className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 mb-1">{SWOT[k].label}</div>
                  <ul className="swot-list text-xs text-zinc-600 dark:text-zinc-400 space-y-0.5">
                    {swot[k].map((it, i) => <li key={i}>{it}</li>)}
                  </ul>
                </div>
              ) : null
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Banner({ type, text }) {
  const warn = type === "warning";
  const Icon = warn ? AlertTriangle : Info;
  return (
    <div className={`flex gap-2 p-3 rounded-xl text-xs leading-relaxed border ${warn
      ? "bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20 text-amber-800 dark:text-amber-300"
      : "bg-sky-50 dark:bg-sky-500/10 border-sky-200 dark:border-sky-500/20 text-sky-800 dark:text-sky-300"}`}>
      <Icon className="w-4 h-4 shrink-0" /> <span>{text}</span>
    </div>
  );
}

function Action({ children, onClick, disabled, primary }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors disabled:opacity-60 ${primary
        ? "border-brand-500/30 bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-500/20"
        : "border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800"}`}
    >
      {children}
    </button>
  );
}
