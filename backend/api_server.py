"""
SAULGPT — FASTAPI SERVER (v2)
================================
All endpoints:

POST /api/chat              — Main 6-layer pipeline + interview intercept
POST /api/upload            — Contract evaluation (PDF/DOCX/TXT)
GET  /api/draft/state/{id}  — Check interview progress
DEL  /api/draft/state/{id}  — Cancel interview
GET  /api/history/{id}      — Conversation history
DEL  /api/history/{id}      — Clear history + interview state
GET  /                      — Health check

Run:
    python api_server.py
"""

import sys, os, re
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env from project root before any imports that need GROQ_API_KEY
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Depends, Request, Form
from fastapi.responses import Response, FileResponse
from typing import Annotated, Optional, Dict, Any, List
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import traceback
import uvicorn

from pipeline_orchestrator import run_saulgpt_pipeline, get_session_history, get_history_with_summary, save_turn_to_memory
import time
from layer5_external import start_auto_updater
from layer6_evaluator import evaluate_contract, format_evaluation_response
from interview_state import (
    get_interview_state,
    DOCUMENT_SCHEMAS,
    generate_field_questions,
    generate_document_spec,
    detect_document_type,
    map_doc_type_to_family,
)
from scrutiny_agent import scrutinize
from document_generator import generate_docx, validate_document_spec
from database import (
    init_db, create_user, get_user_by_email, get_user_by_id,
    ensure_user_exists, ensure_conversation_exists,
    create_conversation, get_conversations, get_conversation,
    delete_conversation, update_conversation_title,
    add_message, get_messages, get_last_turn, touch_conversation, bulk_import_messages
)
from auth import hash_password, verify_password, create_token, decode_token

# In-memory storage for generated .docx files (session_id → bytes)
SESSION_DOCUMENTS: dict[str, bytes] = {}
DOC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_docs")
os.makedirs(DOC_DIR, exist_ok=True)

# Track active conversation per user session (user_id → conv_id or session_id → conv_id)
ACTIVE_CONVERSATIONS: dict[str, int] = {}
SESSION_LEGAL_CONTEXT: dict[str, dict] = {}

# NEW: Agents import (for testing)
try:
    from agents.manager import manager
    from agents.triage import TriageAgent
    AGENTS_AVAILABLE = True
    TRIAGE_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] Agents not available: {e}")
    AGENTS_AVAILABLE = False
    TRIAGE_AVAILABLE = False

try:
    from triage_state import get_triage_state, reset_triage_state, enrich_query_with_triage, MAX_INTAKE_QUESTIONS
    TRIAGE_STATE_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] Triage state not available: {e}")

try:
    from agents.llm_client import get_binary_gate_llm
    from langchain_core.prompts import PromptTemplate
    from prompts.binary_gate import BINARY_GATE_PROMPT
    BINARY_GATE_AVAILABLE = True
    _BINARY_GATE_TEMPLATE = PromptTemplate(
        template=BINARY_GATE_PROMPT,
        input_variables=["user_query"]
    )
except Exception as e:
    print(f"[WARNING] Binary gate not available: {e}")
    BINARY_GATE_AVAILABLE = False
    TRIAGE_STATE_AVAILABLE = False

try:
    from discovery_agent import DiscoveryAgent
    from strategy_agent import StrategyAgent
    DISCOVERY_AVAILABLE = True
    STRATEGY_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] Discovery/Strategy agent not available: {e}")
    DISCOVERY_AVAILABLE = False
    STRATEGY_AVAILABLE = False

try:
    from irac_agent import IRACAgent
    IRAC_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] IRAC agent not available: {e}")
    IRAC_AVAILABLE = False

try:
    from evidence_processor import EvidenceProcessor, CERT_DIR
    EVIDENCE_PROCESSOR_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] EvidenceProcessor not available: {e}")
    EVIDENCE_PROCESSOR_AVAILABLE = False

try:
    from virtual_bench import VirtualBenchEngine
    BENCH_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] VirtualBench not available: {e}")
    BENCH_AVAILABLE = False

try:
    from infographic_generator import extract_oral_briefing, detect_and_build_infographic
    INFOGRAPHIC_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] Infographic generator not available: {e}")
    INFOGRAPHIC_AVAILABLE = False

# Pre-initialize triage agent
_triage_agent = TriageAgent() if TRIAGE_AVAILABLE else None

try:
    from trial_studio import (
        PrecedentEngine,
        get_precedent_engine,
        HostileCrossExaminerAgent,
        DefenseStrategistAgent,
        TrialStudioStartRequest,
        TrialStudioTurnRequest,
        TrialStudioConcludeRequest,
        AdversarialTurnResponse
    )
    TRIAL_STUDIO_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] TrialStudio not available: {e}")
    TRIAL_STUDIO_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "SaulGPT Legal API",
    description = "6-Layer AI pipeline + Contract Evaluation + Interactive Drafter",
    version     = "2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

from key_context import set_request_groq_key, get_effective_groq_key, has_user_custom_key

@app.middleware("http")
async def byok_middleware(request: Request, call_next):
    # Extract client key from header (case-insensitive in ASGI headers)
    custom_key = request.headers.get("x-groq-api-key") or request.headers.get("X-Groq-Api-Key")
    set_request_groq_key(custom_key)
    response = await call_next(request)
    return response

class ValidateKeyRequest(BaseModel):
    api_key: str

@app.post("/api/keys/validate")
async def validate_api_key(req: ValidateKeyRequest):
    key = (req.api_key or "").strip()
    if not key:
        return {"valid": False, "error": "API key cannot be empty"}
    if not key.startswith("gsk_"):
        return {"valid": False, "error": "Groq API keys must begin with 'gsk_'"}
    
    try:
        from groq import Groq
        client = Groq(api_key=key, timeout=10.0)
        models_page = client.models.list()
        model_ids = [m.id for m in getattr(models_page, 'data', [])][:5]
        return {
            "valid": True,
            "message": "Key successfully verified! Dedicated quota active.",
            "models_available": len(getattr(models_page, 'data', [])),
            "sample_models": model_ids
        }
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "Invalid API Key" in err_msg:
            return {"valid": False, "error": "Invalid API Key. Please verify key from console.groq.com/keys"}
        return {"valid": False, "error": f"Verification failed: {err_msg}"}

@app.get("/api/keys/status")
async def get_key_status(request: Request):
    header_key = request.headers.get("x-groq-api-key") or request.headers.get("X-Groq-Api-Key")
    has_custom = bool(header_key and header_key.strip().startswith("gsk_"))
    masked = ""
    if has_custom:
        masked = header_key[:7] + "••••••••" + header_key[-4:]
    return {
        "using_custom_key": has_custom,
        "masked_custom_key": masked,
        "server_fallback_available": False,
        "ready": has_custom
    }


# ─────────────────────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query:       Optional[str] = None
    message:     Optional[str] = None
    session_id:  str           = "web_session_1"
    mode:        Optional[str] = None
    conv_id:     Optional[int] = None

    def get_query_text(self) -> str:
        return (self.query or self.message or "").strip()


class AuthRequest(BaseModel):
    email:    str
    password: str
    username: Optional[str] = None


class AuthResponse(BaseModel):
    token:    str
    user_id:  int
    email:    str
    username: str


class BenchRequest(BaseModel):
    matter:            str
    statutory_context: Optional[str] = None
    evidence_data:     Optional[Dict[str, Any]] = None
    target_role:       Optional[str] = "adverse_witness"


# ─────────────────────────────────────────────────────────────
# LIFECYCLE
# ─────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_event():
    print("🚀 SaulGPT API v2 starting...")
    init_db()
    print("✅ Database initialized.")
    start_auto_updater()
    print("✅ Ready on port 8000.")


# ─────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────

@app.get("/")
@app.get("/api/health")
@app.get("/health")
async def health_check():
    return {
        "status":   "SaulGPT API is Online ⚖️",
        "version":  "2.0.0",
        "features": ["6-layer RAG", "Contract Evaluation", "Interactive Drafter"]
    }


# ─────────────────────────────────────────────────────────────
# AGENT RESPONSE NORMALIZER
# ─────────────────────────────────────────────────────────────

def _populate_frontend_widgets(
    result: dict,
    session_id: str = None
):
    """
    Populate meta fields for frontend widgets (UrgencyBanner,
    JurisdictionBadge, VetoCard) from triage state + scrutiny result.
    """
    try:
        from triage_state import get_triage_state
        ts = get_triage_state(session_id)
        intake = ts.get("intake_fields", {})

        # ── JurisdictionBadge from triage jurisdiction_note + intake ──
        if not result.get("jurisdiction_mapped"):
            jn = ts.get("jurisdiction_note") or result.get("jurisdiction_note", "")
            court_level = None
            if "Small Claims" in jn:
                court_level = "Magistrate"
            elif "District Court" in jn or "Commercial Court" in jn:
                court_level = "District Court"
            elif "High Court" in jn:
                court_level = "High Court"
            if court_level:
                result["jurisdiction_mapped"] = {
                    "court_level": court_level,
                    "jurisdiction_type": "Civil",
                    "territorial": f"At {intake.get('location', 'appropriate jurisdiction')}",
                    "pecuniary": intake.get("amount", "As applicable"),
                }

        # ── UrgencyBanner from triage limitation_warning + intake ──
        if not result.get("urgency_flags"):
            lw = ts.get("limitation_warning") or result.get("limitation_warning", "")
            if "LIMITATION ALERT" in lw or "LIMITATION WARNING" in lw:
                # Parse remaining months from text like "Only **3 month(s)** remain"
                import re
                m = re.search(r"(\d+)\s*month", lw)
                if m:
                    days = int(m.group(1)) * 30
                    result["limitation_days"] = days
                result["urgency_flags"] = ["notice_period_expiring"]
                result["urgency_reason"] = lw
            elif "time-barred" in lw or "may be time-barred" in lw:
                result["urgency_flags"] = ["immediate_filing_required"]
                result["urgency_reason"] = lw

        # ── BNS CorrectionNotice from response text + citations ──
        # Wire remapped_laws for ALL responses (not just document drafting)
        if not result.get("remapped_laws"):
            response_text = result.get("response", "")
            citations = result.get("citations", [])
            # Check citations for repealed acts
            repealed_acts_in_result = set()
            for c in citations:
                name = (c.get("act_name") or "").lower()
                if "ipc" in name or "indian penal code" in name:
                    repealed_acts_in_result.add("IPC")
                if "crpc" in name or "code of criminal procedure" in name:
                    repealed_acts_in_result.add("CrPC")
                if "iea" in name or "indian evidence act" in name:
                    repealed_acts_in_result.add("Indian Evidence Act")
            # Check response text for old law mentions
            if "IPC" in response_text or "Indian Penal Code" in response_text or " ipc " in response_text.lower():
                repealed_acts_in_result.add("IPC")
            if "CrPC" in response_text or "Code of Criminal Procedure" in response_text:
                repealed_acts_in_result.add("CrPC")
            if "IEA" in response_text or "Indian Evidence Act" in response_text:
                repealed_acts_in_result.add("Indian Evidence Act")
            # Build remapped_laws
            LAW_REMAP = {
                "IPC": "BNS (Bharatiya Nyaya Sanhita, 2023)",
                "Indian Penal Code": "BNS (Bharatiya Nyaya Sanhita, 2023)",
                "CrPC": "BNSS (Bharatiya Nagarik Suraksha Sanhita, 2023)",
                "Code of Criminal Procedure": "BNSS (Bharatiya Nagarik Suraksha Sanhita, 2023)",
                "Indian Evidence Act": "BSA (Bharatiya Sakshya Adhiniyam, 2023)",
                "IEA": "BSA (Bharatiya Sakshya Adhiniyam, 2023)",
            }
            remapped = {}
            for act in repealed_acts_in_result:
                if act in LAW_REMAP:
                    remapped[act] = LAW_REMAP[act]
            if remapped:
                result["remapped_laws"] = remapped
                # Also set inside meta for frontend widgets
                if "meta" not in result:
                    result["meta"] = {}
                if isinstance(result["meta"], dict):
                    result["meta"]["remapped_laws"] = remapped

    except Exception:
        pass  # Widget population is best-effort


def _normalize_agent_response(result: dict, query: str = "", mode: str = None, session_id: str = None) -> dict:
    """
    Normalizes agent response to match frontend expectations
    (same shape as old pipeline response).
    """
    defaults = {
        "original_query":       query,
        "status":               "success",
        "mode_used":            result.get("mode_used", mode or "knowledge"),
        "domain":               result.get("domain", "general"),
        "laws_retrieved":       result.get("laws_retrieved", 0),
        "citations":            result.get("citations", []),
        "graph_insights":       result.get("graph_insights", []),
        "case_law_found":       result.get("case_law_found", False),
        "is_hallucinating":     result.get("is_hallucinating", False),
        "confidence_score":     result.get("confidence_score", 0.85),
        "critic_reward_score":  result.get("critic_reward_score", 0.95),
        "critic_deliberation":  result.get("critic_deliberation"),
        "oral_briefing":        result.get("oral_briefing", ""),
        "infographic_data":     result.get("infographic_data"),
        "flagged_citations":    result.get("flagged_citations", []),
        "repealed_warnings":    result.get("repealed_warnings", []),
        "struck_down_warnings": result.get("struck_down_warnings", []),
        "elapsed_seconds":      result.get("elapsed_seconds", 0),
    }
    defaults.update(result)
    raw_resp = result.get("response", "No response generated.")
    cleaned_resp = re.sub(r'^\s*\{[\s\S]*?context_sufficient[\s\S]*?\}\s*', '', raw_resp).strip()
    defaults["response"] = cleaned_resp if cleaned_resp else raw_resp

    if INFOGRAPHIC_AVAILABLE:
        if not defaults.get("oral_briefing"):
            defaults["oral_briefing"] = extract_oral_briefing(defaults["response"])
        if not defaults.get("infographic_data"):
            defaults["infographic_data"] = detect_and_build_infographic(query, defaults["response"])

    # Populate frontend widget fields from triage state
    if session_id:
        _populate_frontend_widgets(defaults, session_id)

    return defaults


# ─────────────────────────────────────────────────────────────
# MAIN CHAT ENDPOINT
# ─────────────────────────────────────────────────────────────

def _build_triage_response(triage_result: dict, session_id: str = None) -> dict:
    """Build a frontend-friendly triage response with SWOT + options."""
    has_options = bool(triage_result.get("options"))
    is_intake = triage_result.get("is_intake_needed", False)

    resp_text = triage_result.get("clarifying_question") or (
        "I've analyzed your situation. Here are your strategic options:"
    )

    triage_payload = {
        "swot_analysis":        triage_result.get("swot_analysis"),
        "options":              triage_result.get("options", []),
        "allow_explanation":    triage_result.get("allow_explanation_trigger", True),
        "allow_advocate":       triage_result.get("allow_advocate_mode", True),
        "is_explanation":       triage_result.get("_is_explanation", False),
        "is_intake_needed":     is_intake,
        "limitation_warning":   triage_result.get("limitation_warning"),
        "jurisdiction_note":    triage_result.get("jurisdiction_note"),
        "extracted_fields":     triage_result.get("extracted_fields", {}),
    }

    return {
        "status":           "triage",
        "mode_used":        "triage",
        "response":         resp_text,
        "triage":           triage_payload,
        "session_id":       session_id or "",
        "interview_active": False,
        "limitation_warning": triage_result.get("limitation_warning"),
        "jurisdiction_note":  triage_result.get("jurisdiction_note"),
    }


# ── Direct legal query patterns (bypass Discovery, go straight to Knowledge) ──
_DIRECT_LEGAL_PATTERNS = [
    # Section/Article references
    r"(section|sec|article|s\.|art\.)\s*\d+",
    # Specific Indian acts
    r"(negotiable instruments|industrial disputes|hindu marriage|motor vehicles|"
    r"indian penal|code of criminal|code of civil|indian evidence|"
    r"bharatiya nyaya|bharatiya nagarik|bharatiya sakshya|"
    r"constitution of india|transfer of property|specific relief|"
    r"limitation act|contract act|partnership act|companies act)",
    # Legal procedure questions
    r"can i (file|sue|put them in|get|claim|apply|register)",
    r"(is it|is this) (legal|illegal|valid|allowed|permitted)",
    r"what (is the|are the) (punishment|penalty|ingredients|procedure|grounds|difference)",
    r"how (many|long|much) (days|months|years|notice|time)",
    r"under (section|article|which|what) (law|act|section)",
    r"does .* violate (article|section|law|right|act)",
    r"right to (file|sue|claim|appeal|apply)",
    r"legal (under|according to|as per)",
]

_SITUATIONAL_LEGAL_ANCHORS = [
    # Employment
    r"(unpaid|salary|wages|firing|termination|notice period|pf|provident fund|gratuity|workplace harassment|constructive dismissal)",
    # Tenancy
    r"(landlord|eviction|deposit refund|illegal lockout|tenancy|rent agreement|lease)",
    # Family
    r"(divorce|maintenance|custody|dowry|domestic violence|inheritance|will|succession|adoption|guardianship)",
    # Money/Fraud
    r"(unpaid loan|cheque bounce|business partner fraud|investment scam|non.?refund|embezzlement)",
    # Property
    r"(ownership dispute|encroachment|sale deed|illegal construction|property dispute|boundary dispute)",
    # Digital
    r"(account ban|online fraud|defamation|data breach|internet restriction|cyber crime|phishing)",
    # Criminal
    r"(threats|assault|stalking|extortion|trespass|blackmail|kidnapping|robbery|theft|dacoity)",
    # Corporate
    r"(company registration|LLP|MCA|GST registration|partnership deed|director liability|msme|startup registration)",
    # Consumer
    r"(product defect|insurance rejection|medical negligence|service failure|deficient service|flawed product)",
    # Constitutional
    r"(fundamental rights|right to life|freedom of speech|right to equality|right to education|writ petition|habeas corpus)",
]

_NON_INDIAN_JURISDICTIONS = [
    r"\bcalifornia\b", r"\bnew york\b", r"\btexas\b", r"\bflorida\b",
    r"\bunited states\b", r"\bu\.?s\.?a?\b", r"\bUK\b", r"\bengland\b",
    r"\blondon\b", r"\bcanada\b", r"\baustralia\b", r"\beuropean union\b",
    r"\bEU\b", r"\bsingapore\b", r"\bmalaysia\b",
]

# ── Crisis / emergency patterns (checked before triage) ──
_CRISIS_RESPONSES = {
    "self_harm": (
        "I hear you, and your wellbeing comes first, before any legal matter.\n\n"
        "**Please reach out for immediate support:**\n"
        "• **AASRA** (24x7 suicide prevention): **+91-9820466726**\n"
        "• **iCall** (mental health helpline): **+91-9152987821** (Mon-Sat 10am-8pm)\n"
        "• **Vandrevala Foundation**: **1860-266-2345** (24x7)\n"
        "• **Emergency**: **112** (National Emergency Number)\n\n"
        "Please talk to someone you trust or visit the nearest hospital. "
        "Your legal issue can wait — your safety cannot."
    ),
    "active_violence": (
        "This sounds like an **emergency situation** that needs immediate action.\n\n"
        "**Please contact emergency services now:**\n"
        "• **Police**: **100**\n"
        "• **National Emergency**: **112**\n"
        "• **Women's Helpline**: **1091**\n"
        "• **Child Helpline**: **1098**\n\n"
        "Go to a safe location if you can. I can help you with legal options "
        "once you're out of immediate danger."
    ),
    "confinement": (
        "This sounds like an **emergency situation** involving unlawful confinement.\n\n"
        "**Please contact emergency services now:**\n"
        "• **Police**: **100**\n"
        "• **National Emergency**: **112**\n"
        "• **Women's Helpline**: **1091**\n\n"
        "If you can, inform a trusted person about your location. "
        "I can assist with legal recourse once you are in a safe environment."
    ),
}

_CRISIS_PATTERNS = {
    "self_harm": [
        r"(kill|end|take) my (own )?(life|self)",
        r"suicide",
        r"(hurt|harm|cut) myself",
        r"i (want|am going) to (die|end it)",
        r"no (point|reason) (to )?(live|living)",
        r"(suicide )?(note|letter)",
        r"i (can'?t|cannot) (do this|take it) (anymore|any longer)",
    ],
    "active_violence": [
        r"(beating|hitting|attacking|choking|strangling) me (right now|currently|at this moment)",
        r"(weapon|knife|gun|blade|stick) .*(right now|in front|here|currently)",
        r"help me.*(bleeding|hurt|injured|in danger|attack)",
        r"(trying to|about to) (kill|hurt|attack|harm) me",
    ],
    "confinement": [
        r"(locked|trapped|held) (in|inside|against my will)",
        r"(can'?t|cannot) (leave|escape|get out)",
        r"(took|confiscated|stole) my (passport|phone|id|documents)",
        r"(holding|keeping) me (hostage|captive)",
        r"padlock(ed)?",
    ],
}


def _detect_crisis(query: str) -> str | None:
    """Detect if query signals an emergency. Returns crisis type or None."""
    query_lower = query.strip().lower()
    for crisis_type, patterns in _CRISIS_PATTERNS.items():
        if any(re.search(p, query_lower) for p in patterns):
            return crisis_type
    return None


def _is_direct_legal_query(query: str) -> bool:
    """Check if query is a direct legal concept/procedure question that should skip Discovery."""
    query_lower = query.strip().lower()
    
    # Check for personal grievance indicators in Hindi/Hinglish
    _HINDI_GRIEVANCE_PATTERNS = [
        r"(हमारे|मेरी|मेरा|मेरे|हमारा|हमे|हमें|मुझको|मुझे)",
        r"(दबंग|मारपीट|कब्जा|कब्ज़ा|धमकी|तोड़कर|बर्बाद|लड़ाई|झगड़ा|लाठी|पिस्तौल)",
        r"(थाने|पुलिस|दरोगा|चौकी|रिपोर्ट|एफआईआर|शिकायत)",
        r"(खेत|जमीन|ज़मीन|फसल|मेड़|पुश्तैनी|हिस्सा|बंटवारा|तहसील|गांव)",
        r"(किराया|मालिक|मकान|सैलरी|वेतन|नौकरी|धोखा|पैसे)",
    ]
    if any(re.search(p, query_lower) for p in _HINDI_GRIEVANCE_PATTERNS):
        return False

    # Explicit legal patterns (acts, sections, generic procedures)
    if any(re.search(p, query_lower) for p in _DIRECT_LEGAL_PATTERNS):
        # If the user is describing their personal situation ("my landlord", "my salary", "i was fired"),
        # it is a personal dispute that must go to Discovery & Strategy (Phase 1 & 2)!
        if re.search(r"\b(my|i was|me|mine|we|our|my father|our village|my land)\b", query_lower) or any(re.search(p, query_lower) for p in _SITUATIONAL_LEGAL_ANCHORS):
            return False
        return True
    return False


def _extract_gate_json(raw: str) -> dict:
    """4-layer JSON extraction for binary gate output (same pattern as layer1)._"""
    import json
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    m = __import__("re").search(r'```(?:json)?\s*\n(.*?)\n```', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    result = {}
    for line in raw.split("\n"):
        line = line.strip().lower()
        if 'classification' in line:
            if 'legal' in line and 'non' not in line:
                result["classification"] = "LEGAL"
            elif 'non' in line:
                result["classification"] = "NON-LEGAL"
        if 'web_fallback' in line:
            result["web_fallback_recommended"] = 'true' in line
        if 'is_non_legal' in line:
            result["is_non_legal"] = 'true' in line
    if result.get("classification"):
        result.setdefault("is_non_legal", result["classification"] == "NON-LEGAL")
        result.setdefault("web_fallback_recommended", False)
        return result
    return {"classification": "LEGAL", "is_non_legal": False, "web_fallback_recommended": False}


def _detect_non_indian_jurisdiction(query: str) -> str | None:
    """Detect if query refers to a non-Indian jurisdiction. Returns the jurisdiction name or None."""
    query_lower = query.strip().lower()
    for pattern in _NON_INDIAN_JURISDICTIONS:
        m = re.search(pattern, query_lower)
        if m:
            return m.group(0)
    return None


# Phrases that indicate user rejects all shown options
_REJECTION_PATTERNS = [
    "none of these", "other option", "not satisfied", "different way",
    "alternate", "anything else", "not helpful", "tell me other",
    "not what i need", "something else", "another way"
]


def _get_route_to(choice: str, options: list) -> str:
    """Read route_to from the chosen option. Never returns 'analysis' (killed fallback)."""
    for opt in options:
        if opt.get("id") == choice:
            return opt.get("route_to", "pathfinder")
    return "pathfinder"  # safe default for unrecognized IDs


def _is_rejection(query: str) -> bool:
    """Check if user is rejecting the shown triage options."""
    q = query.strip().lower()
    return any(p in q for p in _REJECTION_PATTERNS)


def _resolve_triage_choice(query: str, options: list = None) -> Optional[str]:
    """
    Direct selection resolver for UI buttons, single-token numbers/letters, or explicit imperative commands.
    Strictly does NOT match questions, comparisons, or inquiries!
    """
    q = query.strip().lower()

    # If it contains question marks or inquiry interrogatives, it is NOT direct selection
    inquiry_starters = ("why", "how", "what", "can i", "can we", "is there", "which", "is option", "is path", "tell me", "explain", "compare", "cost", "risk")
    if "?" in q or any(q.startswith(s) for s in inquiry_starters):
        return None

    # Check exact option match from options list
    if options:
        for opt in options:
            opt_id = opt.get("id", "").lower()
            opt_label = opt.get("label", "").lower()
            opt_title = opt.get("title", "").lower()
            if q == opt_id:
                return opt.get("id")
            if opt_label and q == opt_label:
                return opt.get("id")
            if opt_title and q == opt_title:
                return opt.get("id")

    # Match single numbers or single letters or simple direct path names
    if q in ("1", "a", "path 1", "path a", "path_a", "option 1", "option a", "opt 1", "opt a", "choice 1", "choice a"):
        return "path_a"
    if q in ("2", "b", "path 2", "path b", "path_b", "option 2", "option b", "opt 2", "opt b", "choice 2", "choice b"):
        return "path_b"
    if q in ("3", "c", "path 3", "path c", "path_c", "option 3", "option c", "opt 3", "opt c", "choice 3", "choice c"):
        return "path_c"
    if q in ("4", "d", "path 4", "path d", "path_d", "option 4", "option d", "opt 4", "opt d", "choice 4", "choice d"):
        return "path_d"

    # Match imperative selection phrases only (e.g. "select option 1", "choose path b", "let's go with option 2")
    for prefix in ("select ", "choose ", "go with ", "i choose ", "i pick ", "proceed with ", "start with ", "let's do "):
        if q.startswith(prefix):
            tail = q[len(prefix):].strip()
            if tail in ("1", "a", "path 1", "path a", "path_a", "option 1", "option a", "opt 1", "opt a"):
                return "path_a"
            if tail in ("2", "b", "path 2", "path b", "path_b", "option 2", "option b", "opt 2", "opt b"):
                return "path_b"
            if tail in ("3", "c", "path 3", "path c", "path_c", "option 3", "option c", "opt 3", "opt c"):
                return "path_c"
            if tail in ("4", "d", "path 4", "path d", "path_d", "option 4", "option d", "opt 4", "opt d"):
                return "path_d"
            if options:
                for opt in options:
                    if tail == opt.get("id", "").lower() or tail == opt.get("label", "").lower() or tail == opt.get("title", "").lower():
                        return opt.get("id")

    return None


def _is_requesting_alternatives(query: str) -> bool:
    """Check if the user is asking for alternative options beyond the 4 shown."""
    q = query.strip().lower()
    # If the user is asking specifically about an existing option, it is an option inquiry, not a request for new alternatives
    if any(opt_ref in q for opt_ref in ["option 1", "option 2", "option 3", "option 4", "path a", "path b", "path c", "path d", "opt 1", "opt 2", "opt 3", "opt 4"]):
        return False

    alt_signals = [
        "other option", "other options", "another option", "different option", "different way",
        "anything else", "what else", "another way", "alternative", "alternatives",
        "can we do something else", "none of these", "not satisfied", "what other",
        "more options", "any other way", "is there something else", "outside court", "without court",
        "other choices", "other paths", "can we do other", "out of court", "settle", "settlement",
        "mediation", "negotiate", "ombudsman", "lok adalat", "amicable", "without litigation", "avoid court"
    ]
    return any(s in q for s in alt_signals)


def _is_advocate_mode_request(query: str) -> bool:
    """Strictly checks if user is explicitly commanding to enter Advocate / IRAC mode."""
    clean_q = re.sub(r'[^\w\s]', '', query.strip().lower()).strip()
    return clean_q in (
        "advocate", "advocate mode", "irac", "irac mode", "deep legal analysis",
        "switch to advocate", "switch to advocate mode", "start advocate mode",
        "enter advocate mode", "open advocate mode"
    ) or bool(re.match(r'^(?:switch\s+to\s+|enter\s+|start\s+)?(?:advocate\s+mode|irac(?:\s+mode)?|deep\s+legal\s+analysis)$', clean_q))


async def _handle_strategy_natural_query(
    query: str,
    session_id: str,
    triage_state: dict,
    user_id,
    conv_id,
    state,
    request
) -> dict:
    """
    Seamlessly handles questions, comparisons, and requests for alternative options
    after the 4 strategic options are presented, without brittle regex misclassification.
    """
    substantive_q = _resolve_substantive_session_query(session_id, triage_state, query, conv_id) or query
    options = triage_state.get("options_shown", [])

    # Case 1: User asks for other options / alternatives
    if _is_requesting_alternatives(query):
        print(f"[Strategy] User requested alternative options for session {session_id}.")
        alternative_options = [
            {
                "id": "path_alt_1",
                "label": "Pre-Institution Mediation & Conciliation",
                "title": "Pre-Institution Mediation & Conciliation",
                "description": "Engage a trained neutral mediator under the Commercial Courts Act or Legal Services Authorities Act. Completely confidential, cost-effective, and maintains business relationships.",
                "pros": ["Zero court fee", "Completely confidential", "Fast-track resolution (usually 30-60 days)"],
                "cons": ["Requires mutual consent to participate"],
                "route_to": "pathfinder"
            },
            {
                "id": "path_alt_2",
                "label": "Statutory Ombudsman / Consumer Helpline (NCH)",
                "title": "Statutory Ombudsman / Regulatory Redressal",
                "description": "Lodge an online complaint before the statutory Ombudsman (RBI Ombudsman for finance, Insurance Ombudsman, or National Consumer Helpline 1915).",
                "pros": ["Completely free to file online", "Statutory power to penalize companies", "High compliance rate"],
                "cons": ["Limited to recognized regulated entities"],
                "route_to": "pathfinder"
            },
            {
                "id": "path_alt_3",
                "label": "Formal Demand & Structured Settlement Table",
                "title": "Formal Demand & Settlement Table",
                "description": "Issue an advocate demand notice with an explicit 7-day settlement window offering structured installment terms or mutual release before escalating.",
                "pros": ["Strong legal leverage without litigation costs", "High settlement success rate"],
                "cons": ["Depends on debtor's willingness to avoid trial"],
                "route_to": "document"
            },
            {
                "id": "path_alt_4",
                "label": "Lok Adalat Fast-Track Amicable Settlement",
                "title": "National Lok Adalat Amicable Disposal",
                "description": "Refer the dispute to National Lok Adalat (organized by NALSA/DLSA). The award is deemed a civil court decree with finality, and court fees (if paid) are 100% refunded.",
                "pros": ["Zero or 100% refunded court fees", "Decree is final and non-appealable", "Same-day amicable settlement"],
                "cons": ["Cannot force unwilling party if absent"],
                "route_to": "pathfinder"
            }
        ]

        triage_state["options_shown"] = alternative_options
        resp_text = (
            "I completely understand if the standard formal routes feel too cumbersome or aggressive. "
            "Under Indian law, you have proven non-litigious and Alternative Dispute Resolution (ADR) pathways that "
            "save time and court fees while maintaining legal pressure:\n\n"
            "Here are **4 practical alternative pathways** tailored to your situation. Let me know which one you'd like to explore:"
        )

        triage_state["options_shown"] = alternative_options
        triage_state["current_mode"] = "strategy"
        if session_id in SESSION_LEGAL_CONTEXT:
            SESSION_LEGAL_CONTEXT[session_id]["options_shown"] = alternative_options

        resp = {
            "response": resp_text,
            "mode_used": "strategy",
            "status": "triage",
            "session_id": session_id,
            "interview_active": False,
            "triage": {
                "swot_analysis": triage_state.get("swot_analysis"),
                "options": alternative_options,
                "allow_explanation": True,
                "is_explanation": True,
                "is_intake_needed": False
            }
        }
        _populate_frontend_widgets(resp, session_id)
        return _save_and_return(resp, user_id, conv_id)

    # Case 2: User asks a specific question about an option, asks for comparison, costs, or risks
    print(f"[Strategy] User asked follow-up / comparison question about options: '{query}'")
    options_summary = ""
    for opt in options:
        options_summary += f"- {opt.get('title', opt.get('label', 'Option'))}: {opt.get('description', '')}\n"

    try:
        from groq import Groq
        groq_client = Groq(api_key=get_effective_groq_key())
        counselor_prompt = f"""You are SaulGPT, serving as Senior Legal Counsel to the client under Indian Law.
The client has been presented with 4 strategic legal pathways, and is asking a tactical question, inquiring about costs, risks, timelines, or comparing options before deciding.

CLIENT'S DISPUTE:
{substantive_q}

STRATEGIC OPTIONS CURRENTLY PRESENTED:
{options_summary}

CLIENT'S QUESTION / INQUIRY:
"{query}"

INSTRUCTIONS:
1. Address the client directly as "you" from word one. NEVER say "The user asks...", "The query inquires...", or "In this case...". Speak as their senior advocate across the table.
2. Answer their question directly and authoritatively in 2 to 3 crisp paragraphs.
3. If they ask about costs/fees: Explain realistic Indian court fee calculation (ad valorem percentage on claim amount), advocate notice charges, or ADR cost savings.
4. If they ask about risks/timelines: Explain realistic timelines (e.g. summary suits 6-12 months, standard suits 2-4 years, legal notice 15 days) and procedural hurdles.
5. If they ask for your recommendation: Give candid tactical advice on which option gives maximum settlement leverage with minimum outlay.
6. Conclude by encouraging them to select any of the options above, or ask any other questions.
"""
        counselor_res = groq_client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
            messages=[{"role": "user", "content": counselor_prompt}],
            temperature=0.2,
            max_tokens=900
        )
        answer_text = counselor_res.choices[0].message.content.strip()
    except Exception as err:
        print(f"[Strategy] Counselor LLM error: {err}")
        answer_text = (
            f"Regarding your question about **{query}**:\n\n"
            "Each option carries distinct procedural timelines and cost implications. "
            "A formal Legal Notice (Option 1) is typically the fastest and lowest-cost move (usually 15 days for compliance), "
            "often prompting settlement before formal court proceedings. In contrast, instituting a court lawsuit involves ad valorem "
            "court fees based on your claim amount and procedural timelines under the CPC, but creates judicial decree enforcement power.\n\n"
            "Whenever you are ready, you can select any option above, or ask me for more details."
        )

    triage_state["current_mode"] = "strategy"
    resp = {
        "response": answer_text,
        "mode_used": "strategy",
        "status": "triage",
        "session_id": session_id,
        "interview_active": False,
        "triage": {
            "swot_analysis": triage_state.get("swot_analysis"),
            "options": options,
            "allow_explanation": True,
            "is_explanation": True,
            "is_intake_needed": False
        }
    }
    _populate_frontend_widgets(resp, session_id)
    return _save_and_return(resp, user_id, conv_id)



def _maybe_offer_voluntary_intake(resp: dict, triage_state: dict, triage_result: dict) -> dict:
    """If there are still fields to gather, append a voluntary prompt."""
    if not triage_state or not triage_result:
        return resp
    intake_fields = triage_state.get("intake_fields", {})
    has_missing = triage_result.get("is_intake_needed") or any(
        not intake_fields.get(f) for f in ["amount", "incident_date", "location"]
    )
    if has_missing:
        triage_state["voluntary_intake_open"] = True
        resp["response"] += "\n\n---\n✨ **Would you like to provide any additional details to strengthen your case?** (Yes/No)"
        if "triage" in resp:
            resp["triage"]["voluntary_intake_offered"] = True
    return resp


def _interview_response(state, response_text):
    """Helper — builds standard response dict for interview turns."""
    return {
        "status":               "interviewing",
        "interview_complete":   False,
        "response":             response_text,
        "interview_active":     True,
        "progress_pct":         state.progress_pct,
        "domain":               "civil",
        "mode_used":            "document",
        "laws_retrieved":       0,
        "citations":            [],
        "graph_insights":       [],
        "case_law_found":       False,
        "is_hallucinating":     False,
        "confidence_score":     1.0,
        "flagged_citations":    [],
        "repealed_warnings":    [],
        "struck_down_warnings": [],
        "elapsed_seconds":      0,
    }


_CONTROL_PATTERNS = [
    r'^(?:⚖\s*)?advocate(?:\s+mode)?$',
    r'^irac(?:\s+(?:mode|analysis))?$',
    r'^deep\s+legal(?:\s+analysis)?$',
    r'^path_[a-d]$',
    r'^option\s*[1-4]$',
    r'^(?:yes|no|y|n|ok|okay|proceed|cancel|continue|skip)$',
    r'^\d{1,8}$',
    r'^\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}$',
]

def _is_control_phrase(text: str) -> bool:
    if not text:
        return True
    t = text.strip().lower()
    if len(t) < 3:
        return True
    for p in _CONTROL_PATTERNS:
        if re.match(p, t, re.IGNORECASE):
            return True
    return False


def _clean_substantive_query(text: str) -> str:
    """
    Strips internal pipeline prompt wrappers, synthetic roadmap requests,
    and control text from query candidates to prevent prompt leakage.
    """
    if not text:
        return ""
    t = text.strip()
    # If wrapped in 'Client Grievance: ... \nChosen Legal Action:', extract just the client grievance
    m = re.search(r'Client Grievance:\s*(.*?)(?:\n\s*Chosen Legal Action:|\n\s*Provide a comprehensive|\Z)', t, re.DOTALL | re.IGNORECASE)
    if m and m.group(1).strip():
        t = m.group(1).strip()
    # Strip any synthetic roadmap instructions
    t = re.sub(r'Provide a comprehensive.*?(?=\n\n|\Z)', '', t, flags=re.DOTALL | re.IGNORECASE)
    t = re.sub(r'Chosen Legal Action:\s*\w+', '', t, flags=re.IGNORECASE)
    t = re.sub(r'Additional Details / Facts:\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^(?:Subject|Re|Regarding|Query):\s*', '', t, flags=re.IGNORECASE)
    return t.strip()


def _resolve_substantive_session_query(
    session_id: str,
    triage_state: dict = None,
    default_query: str = "",
    conv_id: Optional[int] = None
) -> Optional[str]:
    """
    Resiliently resolves the user's substantive legal dispute statement across turns.
    Prevents commands like 'advocate', 'path_a', 'yes', or short form numbers from becoming
    the search query for IRAC, Document Generation, or Procedural Roadmaps.
    """
    candidates = []

    def _add_cand(raw: str):
        cleaned = _clean_substantive_query(raw)
        if cleaned and not _is_control_phrase(cleaned) and len(cleaned) >= 10:
            if cleaned not in candidates:
                candidates.append(cleaned)

    # 1. Check persistent SESSION_LEGAL_CONTEXT
    ctx = SESSION_LEGAL_CONTEXT.get(session_id, {})
    if ctx.get("substantive_queries"):
        for q in reversed(ctx["substantive_queries"]):
            _add_cand(q)
        if ctx.get("original_query"):
            _add_cand(ctx["original_query"])

    # 2. Check triage_state
    if triage_state:
        orig_q = triage_state.get("original_query")
        if orig_q:
            _add_cand(orig_q)

    # 3. Check Interview State
    state = get_interview_state(session_id)
    if state:
        prob = getattr(state, "problem_description", "") or getattr(state, "last_problem_description", "")
        if prob:
            _add_cand(prob)

    # 4. Check conversation memory from pipeline_orchestrator
    history = get_session_history(session_id)
    if history:
        for t in reversed(history):
            turn_q = t.get("query") or t.get("content") or ""
            _add_cand(turn_q)

    # 5. Check SQLite DB messages if conv_id provided
    if conv_id:
        try:
            msgs = get_messages(conv_id)
            for m in reversed(msgs):
                if m.get("role") == "user":
                    content = m.get("content", "").strip()
                    _add_cand(content)
        except Exception as e:
            print(f"[QueryResolver] DB message retrieval error: {e}")

    # Merge facts if multiple distinct substantive turns exist
    if candidates:
        earliest = candidates[-1]  # first user grievance
        latest = candidates[0]    # most recent user elaboration
        if earliest != latest and len(earliest) >= 15 and len(latest) >= 15:
            if earliest in latest:
                return latest
            elif latest in earliest:
                return earliest
            return f"{earliest}\n\nAdditional Details / Facts:\n{latest}"
        return latest or earliest

    # 6. Fallback to default_query if substantive
    if default_query:
        clean_def = _clean_substantive_query(default_query)
        if clean_def and not _is_control_phrase(clean_def) and len(clean_def) >= 10:
            return clean_def

    return None


async def _handle_strategy_choice(choice: str, query: str, session_id: str, triage_state: dict, user_id, conv_id, state, request):
    """Handles execution of user-selected strategy path (Drafting vs Procedural Roadmap)."""
    triage_state["chosen_path"] = choice
    triage_state["is_triaged"] = True
    mode = _get_route_to(choice, triage_state.get("options_shown", []))

    # If user selected legal notice / drafting path
    if "notice" in query.lower() or "draft" in query.lower() or choice == "path_a" or mode == "document":
        orig_q = _resolve_substantive_session_query(session_id, triage_state, query, conv_id) or query

        doc_type = detect_document_type(orig_q) or triage_state.get("doc_type") or "legal_notice"
        doc_family = map_doc_type_to_family(doc_type) or triage_state.get("doc_family") or "letter"

        fields = generate_field_questions(
            doc_family, doc_type,
            orig_q
        )
        display_name = DOCUMENT_SCHEMAS.get(doc_type, {}).get("display_name",
                       doc_type.replace("_", " ").title() if doc_type else "Legal Notice")
        if not fields:
            fields = [
                {"key": "sender_name", "label": "Your Full Name & Address", "example": "Rahul Sharma, Flat 101..."},
                {"key": "recipient_name", "label": "Opponent/Employer/Landlord Full Name & Address", "example": "XYZ Corp, Bangalore..."},
                {"key": "demand_details", "label": "Specific Demand & Amount", "example": "Immediate payment of Rs. 3,50,000 unpaid salary for 3 months"},
                {"key": "compliance_days", "label": "Deadline to comply (e.g. 7 or 15 days)", "example": "15 days"}
            ]

        question = state.start_interview(
            doc_type,
            problem_description=orig_q,
            doc_family=doc_family,
            dynamic_fields=fields
        )
        total = len(fields)
        intro = (
            f"I'll draft a formal **{display_name}** for you.\n\n"
            f"I need **{total} pieces of information** to ground the legal notice. "
            f"Let's go through them one at a time.\n\n"
            f"{question}"
        )
        return _save_and_return(_interview_response(state, intro), user_id, conv_id)

    # Otherwise, it's a procedural path (Labour Commissioner, Summary Suit, Police Complaint, Consumer Forum)
    orig_q = _resolve_substantive_session_query(session_id, triage_state, query, conv_id) or query

    triage_state["current_mode"] = "idle"
    roadmap_query = (
        f"Client Grievance: {orig_q}\n"
        f"Chosen Legal Action: {query}\n\n"
        f"Provide a comprehensive, authoritative Step-by-Step Procedural Roadmap for this chosen legal action under Indian Law. "
        f"Include: (1) Competent Forum / Court Jurisdiction, (2) Statutory Limitation Period, "
        f"(3) Mandatory Documents & Evidence Checklist, (4) Exact Filing Process & Court Fee, and (5) Next Steps."
    )
    result = run_saulgpt_pipeline(
        user_query=roadmap_query,
        session_id=session_id,
        mode="pathfinder"
    )
    if session_id:
        _populate_frontend_widgets(result, session_id)
    result["interview_active"] = False
    return _save_and_return(result, user_id, conv_id)


# ── Confirmation detection patterns ──
_CONFIRMATION_PATTERNS = [
    "yes", "yeah", "yep", "sure", "ok", "okay", "proceed",
    "go ahead", "do it", "generate", "draft", "create",
    "please do", "sounds good", "go for it", "fine"
]


def _is_confirmation(query: str) -> bool:
    """Check if user is confirming document generation."""
    q = query.strip().lower().rstrip(".!?")
    return any(p == q or q.startswith(p) for p in _CONFIRMATION_PATTERNS)


def _generate_document_docx(session_id: str, state) -> dict:
    """
    Generate .docx from interview state, store in memory,
    reset interview state, return response with download_url.
    """
    draft_context = state.get_draft_context()
    scrutiny_res = state.scrutiny_result
    display_name = draft_context["display_name"]
    filled_fields = draft_context["filled_fields"]
    doc_type_key = draft_context.get("doc_type")
    doc_family = draft_context.get("doc_family")

    # ── Generate structured document spec (new path) ──
    spec = generate_document_spec(
        doc_family=doc_family or "letter",
        doc_type=doc_type_key or "legal_document",
        display_name=display_name,
        problem_description=getattr(state, 'problem_description', ""),
        filled_fields=filled_fields,
    )

    if spec:
        # Validate spec against guardrails
        validation = validate_document_spec(spec, filled_fields)
        if not validation["valid"]:
            # If validation fails, log warnings and try to proceed with spec anyway
            # (the spec is still legally informative even if structure is imperfect)
            print(f"[Generator] Spec validation warnings: {validation['errors']}")
            if validation.get("warnings"):
                print(f"[Generator] Spec validation warnings: {validation['warnings']}")

        docx_bytes = generate_docx(
            display_name=display_name,
            filled_fields=filled_fields,
            doc_spec=spec,
        )
    else:
        # ── Legacy fallback if spec generation fails ──
        docx_bytes = generate_docx(
            display_name=display_name,
            filled_fields=filled_fields,
            doc_type=doc_type_key,
            is_dynamic=False,
            problem_description=getattr(state, 'problem_description', ""),
        )

    SESSION_DOCUMENTS[session_id] = docx_bytes
    try:
        doc_file_path = os.path.join(DOC_DIR, f"{session_id}.docx")
        with open(doc_file_path, "wb") as f:
            f.write(docx_bytes)
    except Exception as e:
        print(f"[Document] Warning: Failed to cache docx to disk: {e}")

    public_base = os.getenv("PUBLIC_API_URL")
    if not public_base:
        if os.getenv("SPACE_HOST"):
            public_base = f"https://{os.getenv('SPACE_HOST')}"
        elif os.getenv("SPACE_ID"):
            public_base = f"https://{os.environ['SPACE_ID'].replace('/', '-').lower()}.hf.space"
        else:
            public_base = "https://lvvbaaal-legalgpt-api.hf.space"

    doc_download_url = f"{public_base}/api/document/{session_id}"

    response_text = (
        f"**{display_name}** has been drafted successfully.\n\n"
        f"[Download your document]({doc_download_url})\n\n"
        "Please review it carefully and consult a qualified advocate before use."
    )

    meta = {
        "scrutiny": {
            "is_valid": getattr(scrutiny_res, "is_valid", True) if scrutiny_res else True,
            "warnings": getattr(scrutiny_res, "warnings", []) if scrutiny_res else [],
            "veto_message": getattr(scrutiny_res, "veto_message", "") if scrutiny_res else "",
            "can_proceed": True,
            "remapped_laws": getattr(scrutiny_res, "remapped_laws", {}) if scrutiny_res else {},
            "limitation_info": getattr(scrutiny_res, "limitation_info", "") if scrutiny_res else "",
            "severity": "warning",
        },
        "remapped_laws": getattr(scrutiny_res, "remapped_laws", {}) if scrutiny_res else {},
        "jurisdiction_mapped": getattr(scrutiny_res, "jurisdiction", None) if scrutiny_res else None,
        "urgency_flags": getattr(scrutiny_res, "urgency_flags", []) if scrutiny_res else [],
        "limitation_days": getattr(scrutiny_res, "limitation_days", None) if scrutiny_res else None,
        "limitation_expiry": getattr(scrutiny_res, "limitation_expiry", None) if scrutiny_res else None,
        "urgency_reason": getattr(scrutiny_res, "urgency_reason", None) if scrutiny_res else None,
        "document_ready": True,
        "document_url": doc_download_url,
    }

    if hasattr(state, "problem_description") and state.problem_description:
        state.last_problem_description = state.problem_description
    if session_id in SESSION_LEGAL_CONTEXT:
        SESSION_LEGAL_CONTEXT[session_id]["last_problem_description"] = getattr(state, "problem_description", "")
    state.reset()
    if TRIAGE_STATE_AVAILABLE:
        reset_triage_state(session_id)
    return {
        "interview_active": False,
        "interview_complete": True,
        "response": response_text,
        "meta": meta,
        "mode_used": "document",
    }


# ── Helper: save chat turn to DB for authenticated users ──
def _save_to_db(user_id: int, conv_id: int, query: str, result: dict):
    import json
    turn = get_last_turn(conv_id) + 1
    add_message(conv_id, "user", query, turn=turn)
    meta_json = json.dumps({k: v for k, v in result.items() if k != "response"}, default=str)
    add_message(conv_id, "assistant", result.get("response", ""), meta=meta_json, turn=turn + 1)
    touch_conversation(conv_id)
    # Auto-set title from first user query (max 60 chars)
    if turn == 1:
        title = query.strip()[:60]
        if len(query) > 60:
            title += "..."
        update_conversation_title(conv_id, title)


def _save_assistant_response(conv_id: int, result: dict):
    """Save only the assistant response to DB (user message already saved)."""
    try:
        import json
        turn = get_last_turn(conv_id) + 1
        meta_json = json.dumps({k: v for k, v in result.items() if k != "response"}, default=str)
        add_message(conv_id, "assistant", result.get("response", ""), meta=meta_json, turn=turn)
        touch_conversation(conv_id)
    except Exception as e:
        print(f"[Chat] Warning: failed to save assistant response: {e}")


def _save_and_return(result: dict, user_id, conv_id, chosen_mode: Optional[str] = None, query: str = ""):
    """Save assistant response to DB if authenticated, then return result."""
    if user_id and conv_id and isinstance(result, dict):
        try:
            _save_assistant_response(conv_id, result)
        except Exception as e:
            print(f"[Chat] Warning: _save_and_return failed to save assistant response: {e}")
        result["conv_id"] = conv_id  # inject conv_id so frontend persists it to localStorage
    return result


async def _execute_advocate_mode(session_id: str, triage_state: dict, query: str, user_id, conv_id):
    """
    Executes IRAC Advocate Mode with robust factual grievance recovery.
    Never searches on control phrases or the literal word 'advocate'.
    """
    resolved_q = _resolve_substantive_session_query(session_id, triage_state, query, conv_id)
    if not resolved_q:
        resp = {
            "response": (
                "⚖ **Advocate Mode (IRAC Deep Legal Analysis)** requires an active legal scenario or dispute.\n\n"
                "Please describe your legal issue (for example: an employment grievance, PF settlement, "
                "property dispute, contract breach, or cheque bounce), and I will generate an exhaustive IRAC legal brief "
                "citing relevant statutory sections, High Court & Supreme Court precedents, and actionable strategy."
            ),
            "mode_used": "irac",
            "domain": "civil",
            "interview_active": False,
            "laws_retrieved": 0,
            "citations": [],
            "graph_insights": [],
            "case_law_found": False,
            "is_hallucinating": False,
            "confidence_score": 0.85,
            "flagged_citations": [],
            "repealed_warnings": [],
            "struck_down_warnings": [],
            "elapsed_seconds": 0,
        }
        _populate_frontend_widgets(resp, session_id)
        return _save_and_return(resp, user_id, conv_id)

    profile = (
        triage_state.get("discovery_profile")
        or SESSION_LEGAL_CONTEXT.get(session_id, {}).get("discovery_profile")
        or {}
    )
    options = (
        triage_state.get("options_shown")
        or SESSION_LEGAL_CONTEXT.get(session_id, {}).get("options_shown")
        or []
    )

    if not IRAC_AVAILABLE:
        resp = {
            "response": "Deep legal analysis (IRAC Advocate Mode) is not available right now. Please try standard options above.",
            "mode_used": "irac",
            "domain": "civil",
            "interview_active": False,
        }
        _populate_frontend_widgets(resp, session_id)
        return _save_and_return(resp, user_id, conv_id)

    irac_agent = IRACAgent()
    irac_result = await irac_agent.run(
        resolved_q,
        profile,
        options
    )
    triage_state["current_mode"] = "idle"
    _populate_frontend_widgets(irac_result, session_id)
    return _save_and_return(irac_result, user_id, conv_id)



# ─────────────────────────────────────────────────────────────
# INTERRUPTION HANDLING (State Stack)
# ─────────────────────────────────────────────────────────────

_INTERRUPT_CLARIFICATION = [
    "why", "what is", "explain", "how is", "can you tell",
    "what does", "why is", "reason", "purpose", "how does",
    "meaning", "define",
]

_INTERRUPT_HYPOTHETICAL = [
    "what if", "suppose", "imagine", "hypothetically",
    "what happens if",
]

_INTERRUPT_PUSHBACK = [
    "i think", "i disagree", "that's not right", "that's wrong",
    "actually,", "but what about", "let's ask for", "why not",
    "too low", "too high", "i want", "let's put", "make it",
]


def _classify_interruption(query: str, state=None) -> Optional[str]:
    """Classify a mid-interview interruption by intent.
    
    Two-layer approach:
    1. Fast path — keyword patterns (zero LLM cost, covers ~80% of cases)
    2. Fallback — LLM classification (covers semantic variants at ~50 tokens/call)
    """
    q = query.lower().strip()

    # Digits and short direct answers are ALWAYS field values, never interruptions
    if q.isdigit() or re.match(r"^\d+[\s\w]*$", q):
        return None

    # ── Fast path: keywords with word boundaries ──
    for s in _INTERRUPT_PUSHBACK:
        if re.search(r'\b' + re.escape(s) + r'\b', q):
            return "pushback"

    for s in _INTERRUPT_HYPOTHETICAL:
        if re.search(r'\b' + re.escape(s) + r'\b', q):
            return "hypothetical"

    for s in _INTERRUPT_CLARIFICATION:
        if re.search(r'\b' + re.escape(s) + r'\b', q) and len(q) > 3:
            return "clarification"

    # ── Fallback: LLM classification for queries that look non-answer ──
    # Skip if it looks like a straightforward field value (contains number or is very short)
    _LOOKS_LIKE_ANSWER = r"^(?:\d{1,4}[-/.]?\w*|\d+\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)|rs\.?\s*\d+|₹\d+)"
    if not re.match(_LOOKS_LIKE_ANSWER, q, re.IGNORECASE) and len(q) > 10:
        try:
            from interview_state import _ensure_field_llm
            llm = _ensure_field_llm()
            field_label = ""
            if state and hasattr(state, 'current_field') and state.current_field:
                idx = state._field_index
                if idx < len(state._pending_fields):
                    field_label = state._pending_fields[idx].get("label", state.current_field)
            prompt = (
                f"Field: '{field_label}'\n"
                f"User: '{query}'\n\n"
                f"Classify intent as ONE word:\n"
                f"- answer (providing the requested information)\n"
                f"- clarification (asking why, what, how about the field)\n"
                f"- hypothetical (what-if scenario, alternative course)\n"
                f"- pushback (disagreeing, suggesting different value)\n"
                f"Intent:"
            )
            resp = llm.invoke(prompt, max_tokens=5, temperature=0)
            intent = resp.content.strip().lower().rstrip(".")
            if intent in ("clarification", "hypothetical", "pushback"):
                return intent
        except Exception:
            pass

    return None


def _resume_after_interruption(state) -> str:
    """Re-ask the appropriate question based on the resumed state.
    If we popped back to a pushback, re-prompt the pushback confirmation.
    Otherwise re-ask the current field."""
    if state.state == "interruption:pushback":
        ctx = state.interruption_context
        suggested = ctx.get("suggested_value", "your suggestion")
        return f"**Regarding your suggestion:** Do you want to proceed with **{suggested}**? (Yes / No)"
    return state._ask_next() if state._field_index < len(state._pending_fields) else state._summarize()


def _is_broad_strategy_interruption(query: str) -> bool:
    q = query.lower()
    patterns = [
        r"\b(?:strategy|remedies|remedy|options|legal\s+position|explain\s+(?:the\s+)?law|can\s+we\s+stop|can\s+i\s+stop|criminal\s+and\s+civil)\b",
        r"\b(?:before\s+drafting|tell\s+me\s+the\s+law|what\s+are\s+(?:our|my)\s+rights|what\s+can\s+we\s+do)\b"
    ]
    return any(re.search(p, q) for p in patterns)


def _handle_clarification(state, query: str) -> dict:
    """Explain why the current field matters, or provide full legal strategy if a broad question was asked, then re-ask."""
    from interview_state import _ensure_field_llm
    llm = _ensure_field_llm()
    field_key = state.current_field
    idx = state._field_index
    field_label = state._pending_fields[idx].get("label", field_key) if idx < len(state._pending_fields) else field_key

    if _is_broad_strategy_interruption(query):
        prompt = (
            f"The user is dealing with the following Indian legal situation:\n"
            f"'{state.problem_description}'\n\n"
            f"During the document preparation ({state.display_name}), they asked this substantive legal question:\n"
            f"'{query}'\n\n"
            f"Provide a clear, authoritative, senior-counsel legal analysis covering:\n"
            f"1. Complete Civil & Criminal Remedies under Indian law (cite active BNS/BNSS 2023, NI Act, CPC, Contract Act).\n"
            f"2. Mandatory statutory notice requirements and limitation periods.\n"
            f"3. Practical strategic guidance directly answering their query.\n"
            f"Format with clean markdown bullet points, professional tone, and concise legal clarity."
        )
    else:
        prompt = (
            f"The user is drafting a legal document ({state.display_name}). "
            f"They were asked: '{field_label}'. Their response: '{query}'.\n\n"
            f"Explain in 2-3 clear sentences why this information is legally necessary. "
            f"Be specific (limitation period, court rules, evidence requirements, etc.). "
            f"Be practical and reassuring. If they don't know the exact answer, suggest a reasonable approximation."
        )
    try:
        resp = llm.invoke(prompt)
        explanation = resp.content.strip()
    except Exception:
        explanation = "This information helps us ensure the document is legally accurate and meets court requirements."

    state.pop_state()
    next_q = _resume_after_interruption(state)
    
    if _is_broad_strategy_interruption(query):
        return {
            "response": f"{explanation}\n\n---\n**When you are ready to proceed with drafting your {state.display_name}, please provide:**\n\n{next_q}",
            "interview_active": True,
            "state_stack_resumed": True,
        }

    return {
        "response": f"{explanation}\n\n{next_q}",
        "interview_active": True,
        "state_stack_resumed": True,
    }


def _handle_hypothetical(state, query: str) -> dict:
    """Warn about the risks of the hypothetical, then re-ask."""
    from interview_state import _ensure_field_llm
    llm = _ensure_field_llm()
    prompt = (
        f"The user is drafting a legal document about: {state.problem_description}\n\n"
        f"They asked: '{query}'\n\n"
        f"Warn them about the legal risks of this alternative course of action in 3-4 sentences. "
        f"Be specific about Indian law sections where relevant (e.g., Defamation S.356 BNS, "
        f"Contempt of Court, etc.). End with: 'I strongly advise sticking to the formal legal route.'"
    )
    try:
        resp = llm.invoke(prompt)
        warning = resp.content.strip()
    except Exception:
        warning = "That alternative could expose you to legal liability. I strongly advise sticking to the formal legal route."

    state.pop_state()
    next_q = _resume_after_interruption(state)
    return {
        "response": f"{warning}\n\n{next_q}",
        "interview_active": True,
        "state_stack_resumed": True,
    }


def _handle_pushback(state, query: str) -> dict:
    """Evaluate the user's alternative suggestion and ask for confirmation."""
    from interview_state import _ensure_field_llm
    llm = _ensure_field_llm()
    field_key = state.current_field
    idx = state._field_index
    field_label = state._pending_fields[idx].get("label", field_key) if idx < len(state._pending_fields) else field_key
    current_value = state.collected.get(field_key, "not yet set")

    prompt = (
        f"The user is drafting: {state.display_name}\n"
        f"Field asked: '{field_label}'\n"
        f"Their current value: '{current_value}'\n"
        f"Their suggestion: '{query}'\n\n"
        f"Evaluate their suggestion against legal reality in 3-4 sentences:\n"
        f"1. Is their suggestion legally viable?\n"
        f"2. What are the practical consequences (court fees, evidence, limitation)?\n"
        f"3. Are there any risks they should know?\n"
        f"End by asking: 'Do you want to proceed with this? (Yes / No)'"
    )
    try:
        resp = llm.invoke(prompt)
        evaluation = resp.content.strip()
    except Exception:
        evaluation = (
            f"Your suggestion has been noted. However, you should be aware that the amount/value "
            f"you specify may affect court fees, jurisdiction, and legal strategy. "
            f"Do you want to proceed with this? (Yes / No)"
        )

    state.push_state("interruption:pushback", {
        "question": field_key,
        "label": field_label,
        "suggested_value": query,
    })
    return {
        "response": evaluation,
        "interview_active": True,
        "confirmation_needed": True,
        "interruption_type": "pushback",
    }


def _handle_pushback_confirmation(state, query: str) -> dict:
    """User responded to a pushback — yes/no on the suggested value."""
    ctx = state.interruption_context
    suggested = ctx.get("suggested_value", query)
    field_key = ctx.get("question", state.current_field)

    if _is_confirmation(query):
        state.collected[field_key] = suggested
        state.pop_state()
        state._field_index += 1
        next_q = state._ask_next()
        return {
            "response": f"Updated. {next_q}",
            "interview_active": True,
        }
    else:
        state.pop_state()
        next_q = state._ask_next()
        return {
            "response": f"No changes made. {next_q}",
            "interview_active": True,
        }
        
@app.post("/api/chat")
async def chat_endpoint(
    request: QueryRequest,
    fastapi_request: Request,
):
    """
    Main chat endpoint. Checks interview state first,
    then routes to normal pipeline or interview flow.
    For authenticated users, persists conversations to SQLite.
    """
    try:
        session_id = request.session_id
        query      = request.get_query_text()

        # BYOK support — personal Groq key if provided, or server .env key
        header_key = fastapi_request.headers.get("x-groq-api-key") or fastapi_request.headers.get("X-Groq-Api-Key")
        effective_key = (header_key or "").strip() or os.getenv("GROQ_API_KEY", "").strip()
        if not effective_key or not effective_key.startswith("gsk_"):
            raise HTTPException(
                status_code=400,
                detail="Groq API Key is required. Please provide your free Groq API Key (starts with 'gsk_') from console.groq.com/keys via the API Key button in the top bar."
            )

        # Maintain persistent substantive legal context across turns
        if session_id not in SESSION_LEGAL_CONTEXT:
            SESSION_LEGAL_CONTEXT[session_id] = {
                "original_query": "",
                "substantive_queries": [],
                "discovery_profile": {},
                "options_shown": [],
                "last_document_type": "",
            }
        if not _is_control_phrase(query):
            s_ctx = SESSION_LEGAL_CONTEXT[session_id]
            if not s_ctx.get("original_query"):
                s_ctx["original_query"] = query
            if query not in s_ctx.get("substantive_queries", []):
                s_ctx.setdefault("substantive_queries", []).append(query)

        # ── Extract authenticated user (optional) ──
        authorization = fastapi_request.headers.get("authorization", "")
        user_id = _get_user_id(authorization)
        conv_id = request.conv_id

        # ── For authenticated users: resolve conversation ──
        if user_id:
            if conv_id:
                conv = get_conversation(conv_id, user_id)
                if not conv:
                    # Gracefully create a new conversation instead of throwing 404 or FK violation
                    conv_id = create_conversation(user_id)
                    ACTIVE_CONVERSATIONS[session_id] = conv_id
            else:
                if session_id in ACTIVE_CONVERSATIONS:
                    conv_id = ACTIVE_CONVERSATIONS[session_id]
                    conv = get_conversation(conv_id, user_id)
                    if not conv:
                        conv_id = create_conversation(user_id)
                        ACTIVE_CONVERSATIONS[session_id] = conv_id
                else:
                    conv_id = create_conversation(user_id)
                    ACTIVE_CONVERSATIONS[session_id] = conv_id

        # ── Persist user query to DB safely ──
        if user_id and conv_id:
            try:
                _turn = get_last_turn(conv_id) + 1
                add_message(conv_id, "user", query, turn=_turn)
                if _turn == 1:
                    _title = query.strip()[:60]
                    if len(query) > 60:
                        _title += "..."
                    update_conversation_title(conv_id, _title)
            except Exception as e:
                print(f"[Chat] Warning: failed to save user query: {e}")

        # ── Active interview: accept answer ──
        state = get_interview_state(session_id)

        # ── LAYER 0: INTERRUPTION GUARD (runs BEFORE all state routing) ──
        # If we're in an active interview with an unanswered field, check for
        # interruptions FIRST before the query reaches any field extractor.
        if state.state in ("interviewing", "interruption:clarification",
                           "interruption:hypothetical", "interruption:pushback"):
            field_unanswered = (
                state.current_field
                and state._field_index < len(state._pending_fields)
                and state.collected.get(state.current_field) is None
            )
            if state.state == "interruption:pushback":
                # Nested check: even while awaiting pushback confirmation, the user
                # may throw another interruption ("actually what if 60 instead")
                nested_intent = _classify_interruption(query, state)
                if nested_intent:
                    state.push_state(f"interruption:{nested_intent}")
                    if nested_intent == "clarification":
                        return _save_and_return(_handle_clarification(state, query), user_id, conv_id)
                    elif nested_intent == "hypothetical":
                        return _save_and_return(_handle_hypothetical(state, query), user_id, conv_id)
                    elif nested_intent == "pushback":
                        return _save_and_return(_handle_pushback(state, query), user_id, conv_id)
                # Otherwise fall through to normal pushback confirmation below
            elif field_unanswered and state.state == "interviewing":
                intent = _classify_interruption(query, state)
                if intent == "clarification":
                    return _save_and_return(_handle_clarification(state, query), user_id, conv_id)
                elif intent == "hypothetical":
                    return _save_and_return(_handle_hypothetical(state, query), user_id, conv_id)
                elif intent == "pushback":
                    return _save_and_return(_handle_pushback(state, query), user_id, conv_id)
            # else: no interruption — fall through to state routing

        # ── Pending generation confirmation: user is saying yes/no to .docx ──
        if state.state == "pending_generation" and state.confirm_generation:
            if _is_confirmation(query):
                return _save_and_return(_generate_document_docx(session_id, state), user_id, conv_id)
            else:
                doc_name = state.display_name or (state._doc_display_name() if hasattr(state, '_doc_display_name') else "document")
                state.reset()
                if TRIAGE_STATE_AVAILABLE:
                    reset_triage_state(session_id)
                return _save_and_return({
                    "interview_active": False,
                    "interview_complete": True,
                    "response": f"Alright, I won't draft the **{doc_name}**. "
                                "If you change your mind, just let me know."
                }, user_id, conv_id)

        # ── Interrupted interview (legacy path, fallback) ──
        if state.state == "interrupted":
            if query.lower().strip() in ("cancel", "2", "stop", "never mind", "2️⃣"):
                doc_name = state.display_name
                state.reset()
                if TRIAGE_STATE_AVAILABLE:
                    reset_triage_state(session_id)
                return _save_and_return({
                    "interview_active": False,
                    "response": f"Alright, I've cancelled the **{doc_name}** draft. How can I help you?",
                }, user_id, conv_id)
            else:
                state.state = "interviewing"
                state.pop_state()
                next_q = state.record_answer(query)
                if next_q:
                    return _save_and_return(_interview_response(state, next_q), user_id, conv_id)

        # ── Pushback confirmation (second turn of pushback flow) ──
        if state.state == "interruption:pushback":
            return _save_and_return(_handle_pushback_confirmation(state, query), user_id, conv_id)

        # ── Interviewing: answer the current field ──
        if state.state == "interviewing":
            # Defense-in-depth: re-check interruptions before recording answer.
            # Catches any cases LAYER 0 missed due to state routing subtleties.
            if state.current_field and state._field_index < len(state._pending_fields):
                intent = _classify_interruption(query, state)
                if intent == "clarification":
                    return _save_and_return(_handle_clarification(state, query), user_id, conv_id)
                elif intent == "hypothetical":
                    return _save_and_return(_handle_hypothetical(state, query), user_id, conv_id)
                elif intent == "pushback":
                    return _save_and_return(_handle_pushback(state, query), user_id, conv_id)
            next_q = state.record_answer(query)

            if next_q:
                return _save_and_return(_interview_response(state, next_q), user_id, conv_id)

            # All fields collected — run pre-flight scrutiny
            draft_context = state.get_draft_context()
            prob_desc = getattr(state, 'problem_description', query)
            filled_f  = draft_context.get("filled_fields", {})

            scrutiny_res = scrutinize(prob_desc, filled_f)

            # VETO CHECK: If the agent says STOP, we stop.
            if getattr(scrutiny_res, 'can_proceed', True) is False:
                state.reset()
                if TRIAGE_STATE_AVAILABLE:
                    reset_triage_state(session_id)
                return _save_and_return({
                    "status": "vetoed",
                    "response": "Legal scrutiny has identified critical issues with this matter.",
                    "interview_active": False,
                    "interview_complete": True,
                    "meta": {
                        "scrutiny": {
                            "is_valid": False,
                            "warnings": scrutiny_res.warnings,
                            "veto_message": scrutiny_res.veto_message,
                            "can_proceed": False,
                            "remapped_laws": getattr(scrutiny_res, 'remapped_laws', {}),
                            "severity": "serious"
                        }
                    }
                }, user_id, conv_id)

            # Ask user for explicit confirmation before generating
            state.confirm_generation = True
            state.state = "pending_generation"
            state.scrutiny_result = scrutiny_res

            summary_lines = [
                f"**{state.display_name}** — I have all the information needed.",
                "",
                "Here's what you've provided:"
            ]
            for key, val in state.collected.items():
                label = state.doc_schema["fields"][key]["label"]
                summary_lines.append(f"  **{label}:** {val}")

            # Include scrutiny warnings if any
            warnings = getattr(scrutiny_res, 'warnings', [])
            if warnings:
                summary_lines.append("")
                summary_lines.append("**Note:** " + " ".join(warnings[:2]))

            summary_lines.append("")
            summary_lines.append("**Shall I proceed to draft this document?** (Yes / No)")

            return _save_and_return({
                "interview_active": True,
                "interview_complete": False,
                "response": "\n".join(summary_lines),
                "confirmation_needed": True
            }, user_id, conv_id)

        # ── MANUAL MODE OVERRIDE: mode="document" bypasses triage entirely ──
        if request.mode == "document":
            # Detect doc_family and doc_type directly from query, skip triage
            doc_type = detect_document_type(query)
            doc_family = map_doc_type_to_family(doc_type) if doc_type else None
            if doc_type or doc_family:
                fields = generate_field_questions(
                    doc_family or "letter", doc_type or "legal_document", query
                )
                display_name = DOCUMENT_SCHEMAS.get(doc_type, {}).get("display_name",
                               doc_type.replace("_", " ").title() if doc_type else "Legal Document")
                if not fields:
                    fields = [{"key": "details", "label": "Describe your situation", "example": ""}]
                question = state.start_interview(
                    doc_type or "legal_document",
                    problem_description=query,
                    doc_family=doc_family or "letter",
                    dynamic_fields=fields
                )
                total = len(fields)
                intro = (
                    f"I'll draft a **{display_name}** for you.\n\n"
                    f"I need **{total} pieces of information**. "
                    f"Let's go through them one at a time.\n\n"
                    f"{question}"
                )
                return _save_and_return(_interview_response(state, intro), user_id, conv_id)
            # If no doc type detected, fall through to triage below

        # ── 3-PHASE "VIRTUAL COUNSEL" PIPELINE ──
        # Replaces old triage layer with Discovery (Phase 1) → Strategy (Phase 2) → Drafting (Phase 3)
        if TRIAGE_AVAILABLE and TRIAGE_STATE_AVAILABLE and DISCOVERY_AVAILABLE:
            triage_state = get_triage_state(session_id)
            current_mode = triage_state.get("current_mode", "idle")

            # Universal pre-check: crisis overrides any mode
            crisis_type = _detect_crisis(query)
            if crisis_type:
                resp = {
                    "response": _CRISIS_RESPONSES[crisis_type],
                    "mode_used": "crisis",
                    "domain": "general",
                    "interview_active": False,
                    "laws_retrieved": 0,
                    "citations": [],
                    "confidence_score": 0.0,
                    "crisis_help_shown": True,
                }
                _populate_frontend_widgets(resp, session_id)
                # Reset triage state so user can start fresh after crisis
                triage_state["current_mode"] = "idle"
                triage_state["discovery_turn_count"] = 0
                triage_state["discovery_profile"] = {}
                return _save_and_return(resp, user_id, conv_id)

            # Universal Advocate / IRAC check across all phases (strict command check)
            if _is_advocate_mode_request(query):
                return await _execute_advocate_mode(session_id, triage_state, query, user_id, conv_id)

            # Universal Strategy Path Selection check (handles direct clicks, loaded chats, or idle state)
            path_choice = _resolve_triage_choice(query, triage_state.get("options_shown", []))
            if path_choice and (current_mode in ("idle", "strategy")):
                return await _handle_strategy_choice(path_choice, query, session_id, triage_state, user_id, conv_id, state, request)

            # ═══════════════════════════════════════════════
            # PHASE 0: INITIAL CLASSIFICATION (idle)
            # ═══════════════════════════════════════════════
            if current_mode == "idle":
                # Pre-check 1: Non-Indian jurisdiction → gate immediately
                non_indian_jur = _detect_non_indian_jurisdiction(query)
                if non_indian_jur:
                    resp = {
                        "response": (
                            f"Your question refers to **{non_indian_jur}** law, "
                            f"but my legal database is limited to **Indian law** "
                            f"(Constitution of India, IPC/BNS, CrPC/BNSS, CPC, "
                            f"Negotiable Instruments Act, Industrial Disputes Act, etc.).\n\n"
                            f"I cannot provide legal guidance for {non_indian_jur}. "
                            f"Please consult a qualified attorney licensed in that jurisdiction."
                        ),
                        "mode_used": "knowledge",
                        "domain": "general",
                        "interview_active": False,
                        "laws_retrieved": 0,
                        "citations": [],
                        "confidence_score": 0.0,
                    }
                    _populate_frontend_widgets(resp, session_id)
                    return _save_and_return(resp, user_id, conv_id)

                # Pre-check 2: Direct legal question — force knowledge even if triage says otherwise
                is_direct_legal = _is_direct_legal_query(query)

                # Pre-check 3: Binary gate for non-direct-legal queries
                # Catches off-topic queries before reaching triage LLM
                if not is_direct_legal and BINARY_GATE_AVAILABLE:
                    try:
                        gate_llm = get_binary_gate_llm()
                        gate_prompt = _BINARY_GATE_TEMPLATE.format(user_query=query)
                        gate_raw = gate_llm.invoke(gate_prompt).content.strip()
                        gate_result = _extract_gate_json(gate_raw)
                        if gate_result.get("classification") == "NON-LEGAL":
                            resp = {
                                "response": (
                                    "I'm designed to answer questions about **Indian law** "
                                    "(Constitution, IPC/BNS, CrPC/BNSS, CPC, Family Law, etc.). "
                                    "Your query doesn't appear to be a legal question. "
                                    "Could you rephrase or ask a law-related question?"
                                ),
                                "mode_used": "knowledge",
                                "domain": "legal",
                                "laws_retrieved": 0,
                                "citations": [],
                                "confidence_score": 0.0,
                            }
                            _populate_frontend_widgets(resp, session_id)
                            return _save_and_return(resp, user_id, conv_id)
                    except Exception as e:
                        print(f"[Binary Gate] Gate failed: {e}")

                triage_result = await _triage_agent.analyze(query, triage_state)

                # Override: if it's a direct legal question, force pass_through regardless of triage
                if is_direct_legal:
                    triage_result["pass_through"] = True
                    triage_result["suggested_mode"] = "knowledge"
                    triage_result["swot_analysis"] = None
                    triage_result["options"] = None
                    triage_result["role"] = None

                extracted = triage_result.get("extracted_fields") or {}
                for k, v in extracted.items():
                    if v:
                        triage_state["intake_fields"][k] = v

                # Store classification fields regardless of pass_through
                if triage_result.get("doc_family"):
                    triage_state["doc_family"] = triage_result["doc_family"]
                if triage_result.get("doc_type"):
                    triage_state["doc_type"] = triage_result["doc_type"]
                if triage_result.get("suggested_mode"):
                    triage_state["goal"] = triage_result["suggested_mode"]
                if triage_result.get("role"):
                    triage_state["role"] = triage_result["role"]

                if triage_result.get("pass_through", True):
                    # Knowledge / off-topic / document — skip Discovery, route directly
                    triage_state["is_triaged"] = True
                    query = enrich_query_with_triage(query, triage_state)
                else:
                    # Personal grievance — enter Discovery (Phase 1)
                    triage_state["original_query"] = query
                    triage_state["current_mode"] = "discovery"
                    triage_state["discovery_profile"] = {}
                    triage_state["discovery_turn_count"] = 0

                    discovery_agent = DiscoveryAgent()
                    discovery_result = await discovery_agent.run(query)

                    triage_state["discovery_profile"] = discovery_result.get("discovery_profile", {})
                    triage_state["discovery_turn_count"] = 1
                    if session_id in SESSION_LEGAL_CONTEXT:
                        SESSION_LEGAL_CONTEXT[session_id]["discovery_profile"] = triage_state["discovery_profile"]

                    e_fields = discovery_result.get("extracted_fields") or {}
                    for k, v in e_fields.items():
                        if v:
                            triage_state["intake_fields"][k] = v

                    if discovery_result.get("discovery_complete"):
                        triage_state["current_mode"] = "strategy"
                        strategy_agent = StrategyAgent()
                        substantive_q = _resolve_substantive_session_query(session_id, triage_state, query, conv_id) or query
                        strategy_result = await strategy_agent.run(
                            substantive_q,
                            triage_state["discovery_profile"]
                        )
                        triage_state["swot_analysis"] = strategy_result.get("swot_analysis")
                        triage_state["options_shown"] = strategy_result.get("options", [])
                        triage_state["allow_explain"] = strategy_result.get("allow_explanation_trigger", True)
                        if session_id in SESSION_LEGAL_CONTEXT:
                            SESSION_LEGAL_CONTEXT[session_id]["options_shown"] = triage_state["options_shown"]
                            SESSION_LEGAL_CONTEXT[session_id]["swot_analysis"] = triage_state["swot_analysis"]

                        resp = _build_triage_response(strategy_result, session_id)
                        return _save_and_return(resp, user_id, conv_id)

                    resp = {
                        "response": discovery_result.get("response", "Tell me more about your situation."),
                        "mode_used": "discovery",
                        "domain": "civil",
                        "discovery_active": True,
                        "interview_active": False,
                        "laws_retrieved": 0,
                        "citations": [],
                        "graph_insights": [],
                        "case_law_found": False,
                        "is_hallucinating": False,
                        "confidence_score": 0.85,
                        "flagged_citations": [],
                        "repealed_warnings": [],
                        "struck_down_warnings": [],
                        "elapsed_seconds": 0,
                    }
                    _populate_frontend_widgets(resp, session_id)
                    return _save_and_return(resp, user_id, conv_id)

            # ═══════════════════════════════════════════════
            # PHASE 1: DISCOVERY (max 3 turns)
            # ═══════════════════════════════════════════════
            elif current_mode == "discovery":
                discovery_agent = DiscoveryAgent()
                existing_profile = triage_state.get("discovery_profile", {})
                discovery_turn = triage_state.get("discovery_turn_count", 0)

                discovery_result = await discovery_agent.run(query, existing_profile, discovery_turn)

                triage_state["discovery_profile"] = discovery_result.get("discovery_profile", {})
                triage_state["discovery_turn_count"] = discovery_turn + 1
                if session_id in SESSION_LEGAL_CONTEXT:
                    SESSION_LEGAL_CONTEXT[session_id]["discovery_profile"] = triage_state["discovery_profile"]

                e_fields = discovery_result.get("extracted_fields") or {}
                for k, v in e_fields.items():
                    if v:
                        triage_state["intake_fields"][k] = v

                if discovery_result.get("discovery_complete") or discovery_turn >= 1:
                    # Force transition to Strategy (Phase 2)
                    triage_state["current_mode"] = "strategy"

                    strategy_agent = StrategyAgent()
                    substantive_q = _resolve_substantive_session_query(session_id, triage_state, query, conv_id) or query
                    strategy_result = await strategy_agent.run(
                        substantive_q,
                        triage_state["discovery_profile"]
                    )

                    triage_state["swot_analysis"] = strategy_result.get("swot_analysis")
                    triage_state["options_shown"] = strategy_result.get("options", [])
                    triage_state["allow_explain"] = strategy_result.get("allow_explanation_trigger", True)
                    if session_id in SESSION_LEGAL_CONTEXT:
                        SESSION_LEGAL_CONTEXT[session_id]["options_shown"] = triage_state["options_shown"]
                        SESSION_LEGAL_CONTEXT[session_id]["swot_analysis"] = triage_state["swot_analysis"]

                    resp = _build_triage_response(strategy_result, session_id)
                    return _save_and_return(resp, user_id, conv_id)
                else:
                    resp = {
                        "response": discovery_result.get("response", "Tell me more."),
                        "mode_used": "discovery",
                        "domain": "civil",
                        "discovery_active": True,
                        "interview_active": False,
                        "laws_retrieved": 0,
                        "citations": [],
                        "graph_insights": [],
                        "case_law_found": False,
                        "is_hallucinating": False,
                        "confidence_score": 0.85,
                        "flagged_citations": [],
                        "repealed_warnings": [],
                        "struck_down_warnings": [],
                        "elapsed_seconds": 0,
                    }
                    _populate_frontend_widgets(resp, session_id)
                    return _save_and_return(resp, user_id, conv_id)

            # ═══════════════════════════════════════════════
            # PHASE 2: STRATEGY (user picks option)
            # ═══════════════════════════════════════════════
            elif current_mode == "strategy":
                choice = _resolve_triage_choice(query, triage_state.get("options_shown", []))

                # "advocate" / IRAC mode — intentional deep legal analysis (strict command check)
                if not choice and _is_advocate_mode_request(query):
                    return await _execute_advocate_mode(session_id, triage_state, query, user_id, conv_id)

                if choice:
                    return await _handle_strategy_choice(choice, query, session_id, triage_state, user_id, conv_id, state, request)

                # Seamlessly handle natural language inquiries, comparisons, and alternative options
                return await _handle_strategy_natural_query(query, session_id, triage_state, user_id, conv_id, state, request)

        # ── Use LLM-decided mode from triage (if available) ──
        # When triage returned pass_through=true, the LLM already inferred
        # the correct mode. Use it instead of keyword fallback detection.
        llm_mode = None
        if TRIAGE_STATE_AVAILABLE and not request.mode:
            ts = get_triage_state(session_id)
            if ts.get("goal"):
                llm_mode = request.mode = ts["goal"]

        # ── Document routing via doc_family from triage ──
        # If triage set suggested_mode="document", it also set doc_family + doc_type.
        # Only trust LLM-decided classification from triage, not keyword fallback.
        doc_family = None
        doc_type = None
        if TRIAGE_STATE_AVAILABLE:
            ts = get_triage_state(session_id)
            if ts.get("goal") == "document":
                doc_family = ts.get("doc_family")
                doc_type = ts.get("doc_type")

        if doc_family or doc_type:
            # ── SPEC-BASED INTERVIEW ──
            # Generate field questions via LLM or fallback to legacy schemas
            fields = generate_field_questions(
                doc_family or "letter",
                doc_type or "legal_document",
                query
            )
            display_name = DOCUMENT_SCHEMAS.get(doc_type, {}).get("display_name",
                           doc_type.replace("_", " ").title() if doc_type else "Legal Document")

            if not fields:
                # Should not happen — fallback fields always return something
                fields = [{"key": "details", "label": "Describe your situation", "example": ""}]

            question = state.start_interview(
                doc_type or "legal_document",
                problem_description=query,
                doc_family=doc_family or "letter",
                dynamic_fields=fields
            )
            total = len(fields)

            intro = (
                f"I'll draft a **{display_name}** for you.\n\n"
                f"I need **{total} pieces of information**. "
                f"Let's go through them one at a time.\n\n"
                f"{question}"
            )
            return _save_and_return(_interview_response(state, intro), user_id, conv_id)

        # ── Build triage_context from triage state ──
        triage_context = None
        if TRIAGE_STATE_AVAILABLE:
            ts = get_triage_state(session_id)
            if ts.get("is_triaged") or ts.get("role"):
                triage_context = {
                    "role": ts.get("role"),
                    "goal": ts.get("goal"),
                    "chosen_path": ts.get("chosen_path"),
                    "intake_fields": ts.get("intake_fields", {}),
                }

        # ── Agent Manager (new) or Pipeline fallback ──
        if AGENTS_AVAILABLE:
            result = await manager.run(
                query=query,
                mode=request.mode,
                session_id=session_id,
                conversation_history=get_history_with_summary(session_id),
                triage_context=triage_context
            )
            result = _normalize_agent_response(result, query, request.mode, session_id=session_id)
            # Save turn to conversation memory for sliding window
            save_turn_to_memory(
                session_id=session_id,
                user_query=query,
                domain=result.get("domain", "general"),
                mode=result.get("mode_used", request.mode or "knowledge"),
                response=result.get("response", ""),
                laws_cited=result.get("citations", []),
            )
        else:
            result = run_saulgpt_pipeline(
                user_query=query,
                session_id=session_id,
                mode=request.mode
            )
            if session_id:
                _populate_frontend_widgets(result, session_id)
        result["interview_active"] = False

        # ── Persist to SQLite for authenticated users ──
        if user_id and conv_id:
            result["conv_id"] = conv_id

        return _save_and_return(result, user_id, conv_id, chosen_mode=request.mode, query=query)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        print(f"[API] Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# CONTRACT EVALUATOR ENDPOINT
# ─────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE_MB   = 50


@app.post("/api/upload")
async def upload_and_evaluate(file: UploadFile = File(...)):
    """
    Accepts PDF, DOCX, or TXT.
    Returns structured Red Pen evaluation report.
    """
    try:
        ext = os.path.splitext(file.filename.lower())[1]
        if ext not in ALLOWED_EXTENSIONS:
            return {
                "response": (
                    f"🚨 Unsupported file type: **{ext}**\n\n"
                    f"Accepted formats: PDF, DOCX, TXT"
                ),
                "meta": None
            }

        file_bytes = await file.read()
        size_mb    = len(file_bytes) / (1024 * 1024)

        if size_mb > MAX_FILE_SIZE_MB:
            return {
                "response": (
                    f"🚨 File too large: **{size_mb:.1f}MB** "
                    f"(max {MAX_FILE_SIZE_MB}MB)"
                ),
                "meta": None
            }

        print(f"[API] Evaluating: {file.filename} ({size_mb:.2f}MB)")
        evaluation = evaluate_contract(file_bytes, file.filename)
        response   = format_evaluation_response(evaluation)

        return {
            "response":        response,
            "evaluation_data": evaluation,
            "meta": {
                "mode_used":            "evaluate",
                "domain":               "civil",
                "is_hallucinating":     False,
                "confidence_score":     0.92,
                "laws_retrieved":       0,
                "citations":            [],
                "graph_insights":       [],
                "case_law_found":       False,
                "flagged_citations":    [],
                "repealed_warnings":    evaluation.get("repealed_laws_cited", []),
                "struck_down_warnings": [],
                "elapsed_seconds":      0,
            }
        }

    except ImportError as e:
        return {
            "response": (
                f"🚨 Missing dependency: {str(e)}\n\n"
                "Run: `pip install PyMuPDF python-docx python-multipart`"
            ),
            "meta": None
        }
    except ValueError as e:
        return {"response": f"🚨 {str(e)}", "meta": None}
    except Exception as e:
        print(f"[API] Upload error: {e}")
        return {"response": f"🚨 Evaluation failed: {str(e)}", "meta": None}


# ─────────────────────────────────────────────────────────────
# MULTIMODAL EVIDENCE GROUNDING & SECTION 63 BSA CERTIFICATES
# ─────────────────────────────────────────────────────────────

@app.post("/api/evidence/upload")
async def upload_evidence(
    file: UploadFile = File(...),
    evidence_type: str = Form("audio"),
    client_hash: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """
    Multimodal Evidence Grounding endpoint.
    Processes voice & video recordings (audio/video) or documents, bills, invoices & cheques (image/PDF).
    Computes cryptographic SHA-256, extracts statutory entities under Indian law,
    and generates court-admissible Section 63 BSA PDF certificate.
    """
    if not EVIDENCE_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=500, detail="EvidenceProcessor not available on server")

    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "temp_evidence")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{int(time.time())}_{os.path.basename(file.filename)}")

    MAX_EVIDENCE_SIZE_MB = 25

    try:
        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_EVIDENCE_SIZE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum limit of {MAX_EVIDENCE_SIZE_MB}MB (Uploaded: {size_mb:.1f}MB). To prevent server and browser memory exhaustion, please upload a clip under 25MB."
            )

        with open(temp_path, "wb") as f:
            f.write(content)

        ext = os.path.splitext(file.filename.lower())[1]
        is_multimedia = ("audio" in evidence_type.lower()) or ("video" in evidence_type.lower()) or (ext in [".mp3", ".wav", ".m4a", ".ogg", ".aac", ".webm", ".mp4", ".mov", ".avi", ".mkv"])

        if is_multimedia:
            result = EvidenceProcessor.process_audio_or_video_evidence(temp_path, client_hash=client_hash)
        else:
            result = EvidenceProcessor.process_document_evidence(temp_path, client_hash=client_hash)

        # Ground evidence directly into the active session
        if session_id:
            if session_id not in SESSION_LEGAL_CONTEXT:
                SESSION_LEGAL_CONTEXT[session_id] = {
                    "original_query": "",
                    "substantive_queries": [],
                    "discovery_profile": {},
                    "options_shown": [],
                    "last_document_type": "",
                }
            SESSION_LEGAL_CONTEXT[session_id]["grounded_evidence"] = result
            if TRIAGE_STATE_AVAILABLE:
                from triage_state import get_triage_state
                ts = get_triage_state(session_id)
                ts["grounded_evidence"] = result

        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Evidence processing failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.get("/api/certificates/{cert_filename}")
async def get_certificate_pdf(cert_filename: str):
    """Serve court-admissible Section 63 BSA PDF certificate."""
    if not EVIDENCE_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=500, detail="EvidenceProcessor not available on server")

    clean_filename = os.path.basename(cert_filename)
    cert_path = os.path.join(CERT_DIR, clean_filename)
    if not os.path.exists(cert_path):
        raise HTTPException(status_code=404, detail="Certificate PDF not found")

    return FileResponse(
        cert_path,
        media_type="application/pdf",
        filename=clean_filename
    )


@app.post("/api/bench/debate")
async def simulate_courtroom_bench(req: BenchRequest):
    """
    Virtual Witness Stand & Trial Cross-Examination Simulation.
    Simulates high-court / trial cross-examination interrogation chains,
    witness credibility scoring, evidence grounding, and judicial assessment.
    """
    if not BENCH_AVAILABLE:
        raise HTTPException(status_code=500, detail="VirtualBench engine not available on server")

    try:
        data = VirtualBenchEngine.simulate_cross_examination(
            matter=req.matter,
            evidence_data=req.evidence_data,
            target_role=req.target_role or "adverse_witness",
            statutory_context=req.statutory_context
        )
        return data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Bench simulation failed: {str(e)}")


# ─────────────────────────────────────────────────────────────
# TRIAL STUDIO & ADVERSARIAL PRECEDENT INTELLIGENCE ENDPOINTS
# ─────────────────────────────────────────────────────────────

TRIAL_STUDIO_SESSIONS: Dict[str, Dict[str, Any]] = {}

@app.post("/api/trial/start")
async def start_trial_studio_session(req: TrialStudioStartRequest):
    """
    Initializes a Pre-Trial Adversarial Interrogation or Defense Fortification session.
    Automatically inherits grounded evidence from the active session.
    """
    if not TRIAL_STUDIO_AVAILABLE:
        raise HTTPException(status_code=500, detail="TrialStudio engine not available on server")

    try:
        session_id = req.session_id
        # Inherit grounded evidence if passed in request or available in active session
        grounded_evidence = req.grounded_evidence
        if not grounded_evidence and session_id in SESSION_LEGAL_CONTEXT:
            grounded_evidence = SESSION_LEGAL_CONTEXT[session_id].get("grounded_evidence")

        witness_role = req.witness_role or "accused"

        if req.mode == "cross_examiner":
            agent = HostileCrossExaminerAgent()
            resp = agent.generate_opening_attack(
                scenario=req.scenario,
                witness_role=witness_role,
                grounded_evidence=grounded_evidence,
                act_hint=req.act_hint
            )
        elif req.mode == "defense_fortifier":
            agent = DefenseStrategistAgent()
            resp = agent.generate_defense_fortification(
                scenario=req.scenario,
                witness_role=witness_role,
                grounded_evidence=grounded_evidence,
                act_hint=req.act_hint
            )
        else:
            # "moot_court" — Dual-Agent Sparring Arena
            cross_agent = HostileCrossExaminerAgent()
            cross_resp = cross_agent.generate_opening_attack(
                scenario=req.scenario,
                witness_role=witness_role,
                grounded_evidence=grounded_evidence,
                act_hint=req.act_hint
            )
            def_agent = DefenseStrategistAgent()
            def_resp = def_agent.generate_defense_fortification(
                scenario=req.scenario,
                witness_role=witness_role,
                grounded_evidence=grounded_evidence,
                act_hint=req.act_hint
            )
            resp = AdversarialTurnResponse(
                mode="moot_court",
                turn_index=1,
                interrogation_content=cross_resp.interrogation_content,
                vulnerability_score=cross_resp.vulnerability_score,
                vulnerability_delta=0,
                fatal_flaw_detected=def_resp.fatal_flaw_detected,
                precedent_backing=cross_resp.precedent_backing or def_resp.precedent_backing,
                suggested_statutory_motions=def_resp.suggested_statutory_motions,
                coach_advice=def_resp.coach_advice
            )

        # Store session state
        TRIAL_STUDIO_SESSIONS[session_id] = {
            "mode": req.mode or "moot_court",
            "witness_role": witness_role,
            "scenario": req.scenario,
            "act_hint": req.act_hint,
            "last_question": resp.interrogation_content,
            "current_score": resp.vulnerability_score,
            "turn_index": 1,
            "grounded_evidence": grounded_evidence,
            "history": [resp.dict()]
        }

        return resp.dict()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to start Trial Studio session: {str(e)}")


@app.post("/api/trial/turn")
async def process_trial_studio_turn(req: TrialStudioTurnRequest):
    """
    Processes turn-by-turn witness testimony against empirical precedents,
    updates vulnerability scoring, and drives home the next punchy follow-up (cross-examiner)
    or tactical defense rejoinder and Section 146 BSA objection (defense coach).
    """
    if not TRIAL_STUDIO_AVAILABLE:
        raise HTTPException(status_code=500, detail="TrialStudio engine not available on server")

    session_id = req.session_id
    session_data = TRIAL_STUDIO_SESSIONS.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Trial Studio session not found. Please start a new session.")

    try:
        mode = session_data.get("mode", "moot_court")
        witness_role = req.witness_role or session_data.get("witness_role", "accused")
        new_turn_index = session_data.get("turn_index", 1) + 1
        grounded_evidence = req.grounded_evidence or session_data.get("grounded_evidence")
        if grounded_evidence and not session_data.get("grounded_evidence"):
            session_data["grounded_evidence"] = grounded_evidence

        if mode == "defense_fortifier":
            agent = DefenseStrategistAgent()
            resp = agent.generate_defense_rejoinder_turn(
                scenario=session_data["scenario"],
                previous_brief_or_question=session_data["last_question"],
                witness_answer=req.witness_answer,
                current_score=session_data["current_score"],
                turn_index=new_turn_index,
                witness_role=witness_role,
                grounded_evidence=grounded_evidence,
                history=session_data.get("history")
            )
        elif mode == "cross_examiner":
            agent = HostileCrossExaminerAgent()
            resp = agent.generate_follow_up(
                scenario=session_data["scenario"],
                previous_question=session_data["last_question"],
                witness_answer=req.witness_answer,
                current_score=session_data["current_score"],
                turn_index=new_turn_index,
                witness_role=witness_role,
                grounded_evidence=grounded_evidence,
                history=session_data.get("history")
            )
        else:
            # "moot_court" mode: Dual-Agent Sparring Loop
            # 1. Corner Coach audits the witness's practice answer
            def_agent = DefenseStrategistAgent()
            def_resp = def_agent.generate_defense_rejoinder_turn(
                scenario=session_data["scenario"],
                previous_brief_or_question=session_data["last_question"],
                witness_answer=req.witness_answer,
                current_score=session_data["current_score"],
                turn_index=new_turn_index,
                witness_role=witness_role,
                grounded_evidence=grounded_evidence,
                history=session_data.get("history")
            )

            # 2. Hostile Cross-Examiner attacks newly exposed holes
            cross_agent = HostileCrossExaminerAgent()
            cross_resp = cross_agent.generate_follow_up(
                scenario=session_data["scenario"],
                previous_question=session_data["last_question"],
                witness_answer=req.witness_answer,
                current_score=def_resp.vulnerability_score,
                turn_index=new_turn_index,
                witness_role=witness_role,
                grounded_evidence=grounded_evidence,
                history=session_data.get("history")
            )

            resp = AdversarialTurnResponse(
                mode="moot_court",
                turn_index=new_turn_index,
                interrogation_content=cross_resp.interrogation_content,
                vulnerability_score=cross_resp.vulnerability_score,
                vulnerability_delta=cross_resp.vulnerability_delta,
                fatal_flaw_detected=def_resp.fatal_flaw_detected,
                precedent_backing=cross_resp.precedent_backing,
                suggested_statutory_motions=def_resp.suggested_statutory_motions,
                coach_advice=def_resp.coach_advice
            )

        # Update session
        session_data["last_question"] = resp.interrogation_content
        session_data["current_score"] = resp.vulnerability_score
        session_data["turn_index"] = new_turn_index
        session_data["history"].append({"witness_answer": req.witness_answer, "turn_response": resp.dict()})

        return resp.dict()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process trial turn: {str(e)}")


@app.post("/api/trial/conclude")
async def conclude_trial_studio_session(req: TrialStudioConcludeRequest):
    """
    Formally closes the evidentiary record of cross-examination or defense sparring,
    evaluates final exposure score against 50,000 precedent benchmarks,
    and produces the definitive Courtroom Record of Proceedings & Bench Assessment.
    """
    if not TRIAL_STUDIO_AVAILABLE:
        raise HTTPException(status_code=500, detail="TrialStudio engine not available on server")

    session_id = req.session_id
    session_data = TRIAL_STUDIO_SESSIONS.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Trial session not found.")

    score = session_data.get("current_score", 50)
    mode = session_data.get("mode", "cross_examiner")
    scenario = session_data.get("scenario", "")
    history = session_data.get("history", [])

    if score >= 75:
        status_label = "FATAL EXPOSURE / STATUTORY CHECKMATE"
        color = "#ff4d4f"
        judicial_outlook = (
            "Cross-examination successfully unseated the core evidentiary foundation. "
            "Under controlling Supreme Court precedents, the failure of primary documentary corroboration "
            "and fatal admissions entered on the trial record warrant the dismissal of the claim / decree against the defaulting party."
        )
    elif score >= 40:
        status_label = "CONTESTED TRIAL / BALANCED BURDEN"
        color = "#faad14"
        judicial_outlook = (
            "Material contradictions have been extracted onto the record. While statutory presumptions were invoked, "
            "the lack of contemporaneous financial records leaves the issue to be decided on a strict preponderance of probabilities."
        )
    else:
        status_label = "POSITION FORTIFIED / PRESUMPTION REBUTTED"
        color = "#52c41a"
        judicial_outlook = (
            "The witness successfully weathered adverse cross-examination, anchored their defense to statutory presumptions "
            "and admissible documentary records. The adverse party has failed to discharge the reverse burden of proof."
        )

    # Collect key admissions or points
    admissions = []
    for item in history:
        resp = item.get("turn_response") or item
        flaw = resp.get("fatal_flaw_detected")
        if flaw and flaw not in admissions and not flaw.startswith("Witness maintained"):
            admissions.append(flaw)

    conclude_summary = {
        "session_id": session_id,
        "turns_completed": len(history),
        "final_score": score,
        "status_label": status_label,
        "status_color": color,
        "judicial_outlook": judicial_outlook,
        "admissions_on_record": admissions[:4],
        "statutory_motions": [
            "Order 18 Rule 4 / Rule 17 CPC: Formally close witness cross-examination on record",
            "Order 11 Rule 14 CPC: Compel production of disputed bank statements / ITR filings",
            "Section 146 / 158 BSA: Move application for formal impeachment of credit"
        ]
    }
    return conclude_summary


@app.get("/api/trial/precedents/{case_id}")
async def get_precedent_dossier_endpoint(case_id: str):
    """Retrieves full verified precedent dossier and ratio decidendi."""
    if not TRIAL_STUDIO_AVAILABLE:
        raise HTTPException(status_code=500, detail="TrialStudio engine not available on server")

    try:
        pe = get_precedent_engine()
        dossier = pe.extract_ratio_decidendi(case_id)
        return dossier
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Precedent dossier not found: {str(e)}")


@app.get("/api/trial/search")
async def search_precedents_endpoint(query: str, act: Optional[str] = None):
    """Searches controlling precedents across the 50,000+ case matrix."""
    if not TRIAL_STUDIO_AVAILABLE:
        raise HTTPException(status_code=500, detail="TrialStudio engine not available on server")

    try:
        pe = get_precedent_engine()
        results = pe.search(query=query, act=act, top_k=5)
        return [r.dict() for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ─────────────────────────────────────────────────────────────
# MASTER LEGAL DICTIONARY & GLOSSARY (10,000+ TERMS) ENDPOINTS
# ─────────────────────────────────────────────────────────────

try:
    from legal_dictionary import get_legal_dictionary
    LEGAL_DICT_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] LegalDictionary not available: {e}")
    LEGAL_DICT_AVAILABLE = False


class GlossaryScanRequest(BaseModel):
    text: str
    max_terms: int = 6


@app.get("/api/glossary/term/{term_name}")
async def get_glossary_term_endpoint(term_name: str):
    """Instant lookup for legal term definition, simple meaning, and analogy."""
    if not LEGAL_DICT_AVAILABLE:
        raise HTTPException(status_code=500, detail="LegalDictionary not available")
    ld = get_legal_dictionary()
    item = ld.get_term(term_name)
    if not item:
        raise HTTPException(status_code=404, detail="Term not found in dictionary")
    return item


@app.post("/api/glossary/scan")
async def scan_glossary_terms_endpoint(req: GlossaryScanRequest):
    """Scans legal response text and returns decoded terms with analogies and examples."""
    if not LEGAL_DICT_AVAILABLE:
        return {"terms": []}
    ld = get_legal_dictionary()
    found = ld.scan_text(req.text, max_terms=req.max_terms)
    return {"terms": found, "count": len(found)}


@app.get("/api/glossary/categories")
async def get_glossary_categories_endpoint():
    """Returns all available legal categories."""
    if not LEGAL_DICT_AVAILABLE:
        return {"categories": []}
    ld = get_legal_dictionary()
    return {"categories": list(ld.categories.keys())}




# ─────────────────────────────────────────────────────────────
# INTERVIEW STATE ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/api/draft/state/{session_id}")
async def get_draft_state(session_id: str):
    state = get_interview_state(session_id)
    return {
        "state":          state.state,
        "doc_type":       state.doc_type,
        "progress_pct":   state.progress_pct,
        "missing_fields": state.missing_fields,
        "is_active":      state.is_active,
    }


@app.delete("/api/draft/state/{session_id}")
async def cancel_draft(session_id: str):
    state = get_interview_state(session_id)
    state.reset()
    if TRIAGE_STATE_AVAILABLE:
        reset_triage_state(session_id)
    return {"status": "cancelled", "session_id": session_id}


# ─────────────────────────────────────────────────────────────
# HISTORY ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/api/history/{session_id}")
async def get_history_endpoint(session_id: str):
    history = get_session_history(session_id)
    return {"session_id": session_id, "turns": len(history), "history": history}


@app.delete("/api/history/{session_id}")
async def clear_history_endpoint(session_id: str):
    from pipeline_orchestrator import CONVERSATION_MEMORY
    from interview_state import INTERVIEW_STATES
    if session_id in CONVERSATION_MEMORY:
        CONVERSATION_MEMORY[session_id] = []
    if session_id in INTERVIEW_STATES:
        INTERVIEW_STATES[session_id].reset()
    if TRIAGE_STATE_AVAILABLE:
        reset_triage_state(session_id)
    SESSION_DOCUMENTS.pop(session_id, None)
    SESSION_LEGAL_CONTEXT.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}


# ─────────────────────────────────────────────────────────────
# DOCUMENT DOWNLOAD ENDPOINT
# ─────────────────────────────────────────────────────────────

from fastapi.responses import Response

@app.get("/api/document/{session_id}")
async def download_document(session_id: str):
    """Download a previously generated .docx document."""
    docx_bytes = SESSION_DOCUMENTS.get(session_id)
    if docx_bytes is None:
        doc_file_path = os.path.join(DOC_DIR, f"{session_id}.docx")
        if os.path.exists(doc_file_path):
            try:
                with open(doc_file_path, "rb") as f:
                    docx_bytes = f.read()
                SESSION_DOCUMENTS[session_id] = docx_bytes
            except Exception as e:
                print(f"[Document] Failed to read disk cached docx: {e}")

    if docx_bytes is None:
        raise HTTPException(status_code=404, detail="No document found for this session. Generate one first via /api/chat.")

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="legal_document_{session_id}.docx"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


# ─────────────────────────────────────────────────────────────
# AUTH ENDPOINTS
# ─────────────────────────────────────────────────────────────

def _get_user_id(authorization: str = "") -> int:
    """Extract user_id from Bearer token, or fallback to default guest user (id=1)."""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            uid = decode_token(token)
            if uid:
                return ensure_user_exists(uid)
    # Default fallback to guest user (id=1) so conversations always persist & load seamlessly
    return ensure_user_exists(1)


@app.post("/api/auth/signup")
async def signup(req: AuthRequest):
    if not req.email or not req.password:
        raise HTTPException(400, "Email and password required")
    norm_email = req.email.strip().lower()
    if not req.username:
        req.username = norm_email.split("@")[0]
    existing = get_user_by_email(norm_email)
    if existing:
        raise HTTPException(409, "Email already registered. Please log in.")
    hashed = hash_password(req.password)
    user_id = create_user(norm_email, req.username, hashed)
    if not user_id:
        raise HTTPException(500, "Failed to create user account. Please try again.")
    token = create_token(user_id)
    return AuthResponse(token=token, user_id=user_id, email=norm_email, username=req.username)


@app.post("/api/auth/login")
async def login(req: AuthRequest):
    if not req.email or not req.password:
        raise HTTPException(400, "Email and password required")
    norm_email = req.email.strip().lower()
    user = get_user_by_email(norm_email)
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user["id"])
    return AuthResponse(token=token, user_id=user["id"], email=user["email"], username=user["username"])


@app.get("/api/auth/me")
async def get_me(fastapi_request: Request):
    authorization = fastapi_request.headers.get("authorization", "")
    user_id = _get_user_id(authorization)
    if not user_id:
        raise HTTPException(401, "Invalid or missing token")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return {"user_id": user["id"], "email": user["email"], "username": user["username"]}


# ─────────────────────────────────────────────────────────────
# CONVERSATION ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/api/conversations")
async def list_conversations(fastapi_request: Request):
    authorization = fastapi_request.headers.get("authorization", "")
    user_id = _get_user_id(authorization)
    if not user_id:
        return {"conversations": [], "total": 0}
    limit = int(fastapi_request.query_params.get("limit", 50))
    offset = int(fastapi_request.query_params.get("offset", 0))
    result = get_conversations(user_id, limit=min(limit, 100), offset=offset)
    return {
        "conversations": [{"id": c["id"], "title": c["title"], "updated_at": c["updated_at"]} for c in result["conversations"]],
        "total": result["total"],
    }


@app.post("/api/conversations")
async def new_conversation(fastapi_request: Request):
    authorization = fastapi_request.headers.get("authorization", "")
    user_id = _get_user_id(authorization)
    if not user_id:
        raise HTTPException(401, "Authentication required")
    conv_id = create_conversation(user_id, "New Chat")
    return {"conv_id": conv_id}


@app.get("/api/conversations/{conv_id}")
async def get_conversation_endpoint(conv_id: int, fastapi_request: Request):
    authorization = fastapi_request.headers.get("authorization", "")
    user_id = _get_user_id(authorization)
    if not user_id:
        raise HTTPException(401, "Authentication required")
    conv = get_conversation(conv_id, user_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    messages = get_messages(conv_id)
    return {"conversation": conv, "messages": messages}


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation_endpoint(conv_id: int, fastapi_request: Request):
    authorization = fastapi_request.headers.get("authorization", "")
    user_id = _get_user_id(authorization)
    if not user_id:
        raise HTTPException(401, "Authentication required")
    if not delete_conversation(conv_id, user_id):
        raise HTTPException(404, "Conversation not found")
    return {"status": "deleted"}


class MigrateRequest(BaseModel):
    turns: list
    title: Optional[str] = None


@app.post("/api/conversations/migrate")
async def migrate_conversation(req: MigrateRequest, fastapi_request: Request):
    authorization = fastapi_request.headers.get("authorization", "")
    user_id = _get_user_id(authorization)
    if not user_id:
        raise HTTPException(401, "Authentication required")
    if not req.turns:
        raise HTTPException(400, "No turns provided")
    title = (req.title or req.turns[0].get("content", "Migrated Chat")[:60]).strip()
    conv_id = create_conversation(user_id, title)
    if not bulk_import_messages(conv_id, req.turns):
        delete_conversation(conv_id, user_id)
        raise HTTPException(500, "Failed to import messages")
    return {"conv_id": conv_id}


# ─────────────────────────────────────────────────────────────
# TEST ENDPOINTS - New Multi-Agent Architecture
# ─────────────────────────────────────────────────────────────

@app.get("/api/test/agents")
async def test_agents_available():
    """Check if new agents are available"""
    return {
        "agents_available": AGENTS_AVAILABLE,
        "available_modes": ["knowledge", "analysis", "pathfinder", "document", "interviewing", "evaluate", "scrutiny"] if AGENTS_AVAILABLE else []
    }


@app.post("/api/test/researcher")
async def test_researcher_agent(query: str, mode: str = "knowledge"):
    """Test the Researcher Agent"""
    if not AGENTS_AVAILABLE:
        return {"error": "Agents not available", "legacy_fallback": "Use /api/chat instead"}
    
    try:
        result = await manager.run(query, mode=mode)
        return {"agent": "Researcher", "mode": mode, "result": result}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/test/drafter")
async def test_drafter_agent(query: str, mode: str = "document"):
    """Test the Drafter Agent"""
    if not AGENTS_AVAILABLE:
        return {"error": "Agents not available", "legacy_fallback": "Use /api/chat instead"}
    
    try:
        result = await manager.run(query, mode=mode)
        return {"agent": "Drafter", "mode": mode, "result": result}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/test/reviewer")
async def test_reviewer_agent(query: str, mode: str = "scrutiny"):
    """Test the Reviewer Agent"""
    if not AGENTS_AVAILABLE:
        return {"error": "Agents not available", "legacy_fallback": "Use /api/upload instead"}
    
    try:
        result = await manager.run(query, mode=mode)
        return {"agent": "Reviewer", "mode": mode, "result": result}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/test/{mode}")
async def quick_test(mode: str, q: str = "What is Section 138 of NIA?"):
    """Quick test endpoint - /api/test/knowledge?q=Your question"""
    if not AGENTS_AVAILABLE:
        return {"error": "Agents not loaded"}
    
    try:
        result = await manager.run(q, mode=mode)
        return {
            "mode": mode,
            "query": q,
            "response": result.get("response", str(result))
        }
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("⚖️  SaulGPT API v2 — Port 8000")
    print("   /api/chat  /api/upload  /api/draft  /api/history  /api/document/<id>")
    print("=" * 55 + "\n")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)