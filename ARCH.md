# 🏛️ SaulGPT Architecture & Systems Specification (Quick Reference)

**Document Version:** 2.2.0  
**Target Release:** Production Cloud (Hugging Face Spaces + Supabase + Firebase)  
**System Classification:** Neuro-Symbolic Indian Legal Intelligence Platform  

For exhaustive documentation, refer to:
- 👉 **[Comprehensive Architecture Document](docs/ARCHITECTURE.md)** — In-depth architectural specification and pipeline flows.
- 👉 **[Technical Design Document (TDD)](docs/TDD.md)** — Infrastructure, schemas, CPU pinning, and PRM token budgeting.
- 👉 **[Functional Design Document (FDD)](docs/FDD.md)** — User journeys, 4 document families, and constitutional guardrails.
- 👉 **[Architectural Decision Records (ADRs)](docs/CHANGELOG_DECISIONS.md)** — All 30 ADRs (ADR-001 through ADR-030).
- 👉 **[Complete Feature Breakdown](docs/FEATURES.md)** — Deep dive into all 10 core system modules.
- 👉 **[REST API Reference](docs/API_REFERENCE.md)** — All HTTP endpoints, schemas, and request/response models.
- 👉 **[Deployment Guide](DEPLOYMENT_GUIDE.md)** — Production deployment steps for HF Spaces, Supabase, and Firebase.
- 👉 **[Setup & Developer Guide](docs/SETUP_GUIDE.md)** — Local development, testing, and environment setup.

---

## 1. High-Level Cloud Topology

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (Web Browser)                     │
│  Hosted at: https://legalgpt-india.web.app (Firebase Hosting)          │
│  Stack: React 18, Vite 5, Axios Interceptors, jsPDF A4 Engine          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS REST + CORS (Port 443)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             BACKEND API LAYER (Hugging Face Spaces - ZeroGPU)          │
│  Hosted at: https://lvvbaaal-legalgpt-api.hf.space                    │
│  Hardware: zero-a10g (16 GB VRAM, Dynamic GPU Allocation)              │
│  Server: FastAPI mounted inside Gradio 5.20 ASGI Server (Port 7860)   │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ app.py (ZeroGPU Entrypoint)                                      │  │
│  │ ├─ demo.launch(server_port=7860, prevent_thread_lock=True)       │  │
│  │ ├─ server_app.include_router(fastapi_app.router)                 │  │
│  │ └─ demo.block_thread() keeps container alive                     │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
│                                    │                                   │
│  ┌─────────────────────────────────▼────────────────────────────────┐  │
│  │ api_server.py (Core Controller & Pipeline Dispatcher)            │  │
│  │ ├─ Omni-Box Autonomous Routing & Devanagari Hindi HyDE (Layer 1) │  │
│  │ ├─ 3-Phase Discovery State Machine (triage_state.py)             │  │
│  │ ├─ 4-Family Document Factory & Fallback Engine (interview_state) │  │
│  │ ├─ IRAC Advocate Mode & Courtroom Simulator (irac_agent.py)      │  │
│  │ ├─ Pre-Trial Studio & Precedent Engine (trial_studio/)           │  │
│  │ ├─ Sec 63 BSA Digital Evidence Processor (evidence_processor.py) │  │
│  │ ├─ Contract Risk Evaluator (layer6_evaluator.py, 25K chars)      │  │
│  │ └─ Actor-Critic FG-PRM Token Budgeting (actor_critic.py)         │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
└────────────────────────────────────┼───────────────────────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌────────────────────────────────────────┐  ┌────────────────────────────────────────┐
│    SUPABASE MANAGED POSTGRESQL CLOUD   │  │         LOCAL CHROMADB VECTOR STORE    │
│  Host: aws-0-ap-southeast-1.pooler...  │  │  Storage: data/vector_db/              │
│  Port: 5432 (Session) / 6543 (Tx)      │  │  Model: all-MiniLM-L6-v2 (CPU-pinned)  │
│  Tables: users, conversations, messages│  │  Collections: saulgpt_indian_laws,     │
│  Engine: IPv4 Connection Pooler        │  │               landmark_precedents      │
└────────────────────────────────────────┘  └────────────────────────────────────────┘
```

---

## 2. Core Subsystems & Components

| Subsystem | Primary Implementation | Architectural Highlights |
| :--- | :--- | :--- |
| **Omni-Box & Routing** | `backend/layer1_understanding.py`, `backend/api_server.py` | Eliminates manual mode dropdowns; classifies intent across Q&A, Grievance, Drafter, Reviewer, and Studio. Devanagari Hindi cross-lingual HyDE. |
| **Virtual Counsel** | `backend/triage_state.py`, `backend/discovery_agent.py`, `backend/strategy_agent.py` | 3-Phase grievance workflow (Discovery $\rightarrow$ Strategy $\rightarrow$ Execution) capped at 3 turns with SWOT analysis and 4 action paths. |
| **6-Layer RAG Engine** | `backend/pipeline_orchestrator.py`, `backend/layer[1-6]*.py` | Dense vector retrieval (2,449+ chunks) + BM25 Okapi + Cross-Encoder reranking + PyTorch TransE/RotatE GNN ($\mathbb{R}^{64}$) + SC Struck-Down Firewall. |
| **Actor-Critic FG-PRM** | `backend/actor_critic.py`, `backend/layer4_validation.py` | Fine-Grained Process Reward Model evaluating factuality, legal soundness, and tone. Token budget strictly capped at `max_tokens=800` to avoid Groq OTPM rate limits. |
| **4-Family Document Drafter** | `backend/interview_state.py`, `backend/document_generator.py` | Generates `.docx` and `.pdf` across 4 families (`letter`, `pleading`, `affidavit`, `agreement`). 100% prompt sanitization, canonical Indian legal formatting, and deterministic fallback spec engine. |
| **Pre-Trial Studio** | `backend/trial_studio/`, `saulgpt-ui/src/TrialStudio.jsx` | 2-column judicial chamber: Hostile Sec 146 BSA cross-examination vs. confidential Corner Coach tactical counsel. Indexed over 50,000 SC/HC precedents. |
| **Sec 63 BSA Evidence** | `backend/evidence_processor.py`, `saulgpt-ui/src/EvidenceUploader.jsx` | Cryptographic SHA-256 digital certificate generation, cheque OCR extraction, and debtor voice admission limitation extension under S.18 Limitation Act. |
| **Contract Risk Evaluator** | `backend/layer6_evaluator.py` | Single-pass evaluation of full agreements up to 25,000 characters against Indian Contract Act 1872 (Sections 27, 28, 74). |
| **Persistence Engine** | `backend/database.py`, Supabase PostgreSQL | Supabase PostgreSQL IPv4 pooler (:5432) for zero-connection-drop cloud deployment across mobile/desktop, with local SQLite WAL fallback. |
| **Security & BYOK** | `backend/api_server.py`, `saulgpt-ui/src/ApiKeyModal.jsx` | User Groq API keys (`gsk_...`) stored client-side in `localStorage`, injected per-request via `X-Groq-Api-Key` headers; zero server-side key logging. |

---

## 3. Environment & Configuration Reference

```bash
# Core LLM API
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant

# Cloud Database (Supabase IPv4 Pooler)
DATABASE_URL=postgresql://postgres.lxnrfznxvnjlpginivob:PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres

# JWT Security
JWT_SECRET=super-secret-jwt-key-change-in-production

# Public API URL for Document Downloads
PUBLIC_API_URL=https://lvvbaaal-legalgpt-api.hf.space
```
