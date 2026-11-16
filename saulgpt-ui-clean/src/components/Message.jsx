import { useState } from "react";
import axios from "axios";
import { Copy, Check, Gavel, FileDown, Download, Library, AlertTriangle, CircleCheck } from "lucide-react";
import { API_BASE } from "../apiConfig";
import { downloadAsPDF, copyToClipboard } from "../features/usePDF";
import UrgencyBanner from "../features/UrgencyBanner";
import VetoCard from "../features/VetoCard";
import JurisdictionBadge from "../features/JurisdictionBadge";
import BNSCorrectionNotice from "../features/BNSCorrectionNotice";
import ToulminMatrix from "../features/ToulminMatrix";
import DecodedTermsRibbon from "../features/DecodedTermsRibbon";
import LegalInfographic from "../features/LegalInfographic";
import AudioPillPlayer from "../features/AudioPillPlayer";
import StrategyCards from "./StrategyCards";
import BrandMark from "./BrandMark";

export const MODES = {
  analysis:     { label: "Case Analysis" },
  knowledge:    { label: "Legal Knowledge" },
  document:     { label: "Document Draft" },
  pathfinder:   { label: "Step-by-step Path" },
  evaluate:     { label: "Contract Review" },
  interviewing: { label: "Drafting" },
};

const EXPORTABLE_MODES = ["document", "evaluate", "pathfinder", "analysis", "knowledge"];

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function resolveUrl(url) {
  if (url.includes("localhost:8000") || url.includes("127.0.0.1:8000")) {
    return url.replace(/https?:\/\/(localhost|127\.0\.0\.1):8000/, API_BASE);
  }
  if (url.startsWith("/api/")) return `${API_BASE}${url}`;
  return url;
}

/** Same lightweight markdown rendering as the classic UI (with HTML escaped first). */
export function formatMessageContent(rawText) {
  if (!rawText) return "";
  return escapeHtml(rawText)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`\n]+)`/g, "<code>$1</code>")
    .replace(/### (.*?)(\n|$)/g, "<h3>$1</h3>")
    .replace(/## (.*?)(\n|$)/g, "<h2>$1</h2>")
    .replace(/^- (.*)/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>")
    .replace(/\[(.*?)\]\((.*?)\)/g, (m, text, url) => {
      if (!/^(https?:\/\/|\/api\/)/.test(url)) return m;
      return `<a href="${resolveUrl(url)}" target="_blank" rel="noopener noreferrer">${text}</a>`;
    })
    .replace(/\n/g, "<br/>");
}

export function parseMeta(msg) {
  let meta = msg.meta;
  if (meta && typeof meta === "string") {
    try { meta = JSON.parse(meta); } catch { meta = null; }
  }
  return { meta, effectiveMeta: meta?.meta || meta };
}

export default function Message({ msg, index, onTriageChoice, onOpenBench, onShowSources, isCompactBNS = false, busy }) {
  const isUser = msg.role === "user";
  const [copied, setCopied] = useState(false);

  const content = typeof msg.content === "string" ? msg.content : (msg.content != null ? String(msg.content) : "");
  const { meta, effectiveMeta } = parseMeta(msg);

  const triage = msg.triage || meta?.triage || effectiveMeta?.triage;
  const scrutiny = meta?.scrutiny || effectiveMeta?.scrutiny;
  const deliberation = msg.critic_deliberation || meta?.critic_deliberation || effectiveMeta?.critic_deliberation;
  const toulminMatrix = msg.toulmin_matrix || meta?.toulmin_matrix || effectiveMeta?.toulmin_matrix;
  const progressPct = msg.interviewProgress !== undefined ? msg.interviewProgress
    : (meta?.progress_pct !== undefined ? meta.progress_pct : effectiveMeta?.progress_pct);
  const docReady = meta?.document_ready || effectiveMeta?.document_ready;
  const docUrl = meta?.document_url || effectiveMeta?.document_url;

  const showExport = !isUser && content && content.length > 100;
  const isError = content.startsWith("🚨");
  const isClarify = content.includes("Could you please clarify");
  const showPDF = showExport && !isError && !isClarify && (
    EXPORTABLE_MODES.includes(meta?.mode_used) ||
    EXPORTABLE_MODES.includes(effectiveMeta?.mode_used) ||
    meta?.interview_complete || effectiveMeta?.interview_complete ||
    content.length > 300
  );

  const docHref = docUrl
    ? (docUrl.startsWith("http") && !docUrl.includes("localhost:8000")
        ? docUrl
        : `${API_BASE}${docUrl.replace(/https?:\/\/(localhost|127\.0\.0\.1):8000/, "")}`)
    : null;

  async function handleCopy() {
    await copyToClipboard(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleDocxDownload(e) {
    e.preventDefault();
    try {
      const res = await axios.get(docHref, { responseType: "blob" });
      const blob = new Blob([res.data], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.setAttribute("download", `legal_document_${msg.session_id || "draft"}.docx`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.warn("Direct blob download failed, opening URL in new window:", err);
      window.open(docHref, "_blank");
    }
  }

  if (isUser) {
    return (
      <div className="flex justify-end sg-fade-in">
        <div
          className="max-w-[85%] sm:max-w-[75%] px-4 py-2.5 rounded-2xl rounded-br-md bg-brand-500 text-white text-sm leading-relaxed whitespace-pre-wrap break-words [&_strong]:font-semibold"
          dangerouslySetInnerHTML={{ __html: formatMessageContent(content) }}
        />
      </div>
    );
  }

  const mode = MODES[effectiveMeta?.mode_used];
  const citations = effectiveMeta?.citations || [];

  return (
    <div className="flex gap-3 sg-fade-in">
      <BrandMark size={28} className="mt-0.5" />
      <div className="flex-1 min-w-0 text-sm">
        {progressPct !== undefined && <InterviewProgress pct={progressPct} />}

        {effectiveMeta && (
          <>
            {toulminMatrix && <ToulminMatrix matrix={toulminMatrix} />}
            <BNSCorrectionNotice meta={effectiveMeta} compact={isCompactBNS} />
            <UrgencyBanner meta={effectiveMeta} />
            <JurisdictionBadge meta={effectiveMeta} />
            {effectiveMeta.oral_briefing && <AudioPillPlayer text={effectiveMeta.oral_briefing} />}
          </>
        )}

        <div
          className={`prose-legal ${isError ? "text-red-600 dark:text-red-400" : ""}`}
          dangerouslySetInnerHTML={{ __html: formatMessageContent(content) }}
        />

        {effectiveMeta?.infographic_data && <LegalInfographic data={effectiveMeta.infographic_data} />}

        {triage && <StrategyCards triage={triage} onChoose={onTriageChoice} disabled={busy} />}

        {content && <DecodedTermsRibbon content={content} />}

        {effectiveMeta && <VetoCard scrutiny={scrutiny} deliberation={deliberation} />}

        {/* Compact pipeline summary — full details open in the right panel */}
        {effectiveMeta && (mode || citations.length > 0 || effectiveMeta.domain) && (
          <button
            onClick={() => onShowSources(index)}
            className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200"
            title="Show sources & validation"
          >
            {mode && <Pill accent>{mode.label}</Pill>}
            {effectiveMeta.domain && <Pill>{effectiveMeta.domain}</Pill>}
            {effectiveMeta.laws_retrieved > 0 && <Pill>{effectiveMeta.laws_retrieved} laws</Pill>}
            {effectiveMeta.case_law_found && <Pill>case law</Pill>}
            {effectiveMeta.elapsed_seconds > 0 && <Pill>{effectiveMeta.elapsed_seconds}s</Pill>}
            {effectiveMeta.is_hallucinating
              ? <Pill warn><AlertTriangle className="w-3 h-3" /> verify</Pill>
              : <Pill ok><CircleCheck className="w-3 h-3" /> validated</Pill>}
          </button>
        )}

        {showExport && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            <ActionBtn onClick={handleCopy} title="Copy plain text">
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? "Copied" : "Copy"}
            </ActionBtn>
            {effectiveMeta && (
              <ActionBtn onClick={() => onShowSources(index)} title="Citations, validation and confidence">
                <Library className="w-3.5 h-3.5" /> Sources
              </ActionBtn>
            )}
            <ActionBtn onClick={() => onOpenBench && onOpenBench(content)} title="Practise this matter in Trial Studio">
              <Gavel className="w-3.5 h-3.5" /> Trial Studio
            </ActionBtn>
            {showPDF && (
              <ActionBtn onClick={() => downloadAsPDF(content, effectiveMeta || meta || {})} title="Download as formatted PDF">
                <FileDown className="w-3.5 h-3.5" /> PDF
              </ActionBtn>
            )}
            {docReady && docHref && (
              <a
                href={docHref}
                onClick={handleDocxDownload}
                download
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-brand-500 hover:bg-brand-600 text-white shadow-sm"
                title="Download editable Word document"
              >
                <Download className="w-3.5 h-3.5" /> Download .docx
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function InterviewProgress({ pct }) {
  return (
    <div className="mb-3 flex items-center gap-3">
      <div className="flex-1 h-1.5 rounded-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
        <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400 whitespace-nowrap">
        {pct < 100 ? `${pct}% of details collected` : "All details collected"}
      </span>
    </div>
  );
}

function Pill({ children, accent, warn, ok }) {
  const cls = accent
    ? "bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-400 border-brand-500/20"
    : warn
      ? "bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20"
      : ok
        ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
        : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700";
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border font-medium ${cls}`}>{children}</span>;
}

function ActionBtn({ children, onClick, title }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
    >
      {children}
    </button>
  );
}
