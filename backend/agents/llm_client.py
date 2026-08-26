"""
LLM Client - Single source for all Language Models
===============================================
All agents import from here. No more repeated LLM initialization.
"""

from langchain_groq import ChatGroq
import os

# Load .env from project root (two levels up from agents/)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set. Create a .env file in the project root with GROQ_API_KEY=your_key")

# ============================================================
# AVAILABLE MODELS (Active on Groq)
# ============================================================

# Primary reasoning and Q&A model (27B)
RESEARCHER_MODEL = os.environ.get("RESEARCHER_MODEL", "qwen/qwen3.8-27b")

# Document creation model (27B)
DRAFTER_MODEL = os.environ.get("DRAFTER_MODEL", "qwen/qwen3.8-27b")

# Review and contract scrutiny model (120B)
REVIEWER_MODEL = os.environ.get("REVIEWER_MODEL", "openai/gpt-oss-120b")

# Deep IRAC Advocate analysis model (120B)
ADVOCATE_MODEL = os.environ.get("ADVOCATE_MODEL", "openai/gpt-oss-120b")

# Triage, discovery, and strategy model (27B)
TRIAGE_MODEL = os.environ.get("TRIAGE_MODEL", "qwen/qwen3.8-27b")

# ============================================================
# LLM INSTANCES
# ============================================================

def _build_llm(primary_model: str, fallback_model: str, temperature: float, max_tokens: int):
    primary = ChatGroq(
        model=primary_model,
        api_key=GROQ_API_KEY,
        temperature=temperature,
        max_completion_tokens=max_tokens
    )
    if primary_model != fallback_model:
        fallback = ChatGroq(
            model=fallback_model,
            api_key=GROQ_API_KEY,
            temperature=temperature,
            max_completion_tokens=max_tokens
        )
        return primary.with_fallbacks([fallback])
    return primary

def get_researcher_llm():
    """Researcher Agent - Legal Q&A, case analysis, procedures"""
    return _build_llm(RESEARCHER_MODEL, "openai/gpt-oss-20b", 0.3, 4096)

def get_drafter_llm():
    """Drafter Agent - Legal documents, notices, FIRs"""
    return _build_llm(DRAFTER_MODEL, "openai/gpt-oss-20b", 0.2, 8192)

def get_reviewer_llm():
    """Reviewer Agent - Contract review, validation, scrutiny (120B with 27B fallback)"""
    return _build_llm(REVIEWER_MODEL, "qwen/qwen3.8-27b", 0.1, 4096)

def get_advocate_llm():
    """Advocate Agent - IRAC deep legal analysis (120B with 27B fallback)"""
    return _build_llm(ADVOCATE_MODEL, "qwen/qwen3.8-27b", 0.1, 4096)

def get_triage_llm():
    """Triage Agent - Strategic query analysis, SWOT generation"""
    return _build_llm(TRIAGE_MODEL, "openai/gpt-oss-20b", 0.2, 2048)

def get_binary_gate_llm():
    """Binary Gatekeeper - LEGAL/NON-LEGAL classification only"""
    primary = ChatGroq(
        model=TRIAGE_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.0,
        top_p=0.1,
        max_completion_tokens=512
    )
    fallback = ChatGroq(
        model="openai/gpt-oss-20b",
        api_key=GROQ_API_KEY,
        temperature=0.0,
        top_p=0.1,
        max_completion_tokens=512
    )
    return primary.with_fallbacks([fallback])

def get_discovery_llm():
    """Discovery Agent - Empathetic investigation with structured turns"""
    return ChatGroq(
        model=TRIAGE_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.1,
        max_completion_tokens=2048
    )

# ============================================================
# EXPORTS - Import these in agents
# ============================================================

# Pre-initialized instances for convenience
researcher = get_researcher_llm()
drafter = get_drafter_llm()
reviewer = get_reviewer_llm()
advocate = get_advocate_llm()
triage = get_triage_llm()
binary_gate = get_binary_gate_llm()
discovery = get_discovery_llm()