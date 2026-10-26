# 🏛️ SaulGPT — System Architecture & Component Specification
**Document Version:** 2.2.0  
**Status:** Active Production  
**Hosting Architecture:** Hugging Face Spaces (ZeroGPU Backend) + Supabase Managed PostgreSQL + Firebase Hosting (Web SPA)

---

## 1. High-Level Architecture Overview

SaulGPT is an AI-powered Indian Legal Intelligence platform operating on a **Two-Tier Neuro-Symbolic Architecture**:
1. **The Multi-Agent Workflow Layer (UX & Client Lifecycle):** Omni-Box Routing $\rightarrow$ 3-Phase Virtual Counsel (Discovery $\rightarrow$ Strategy $\rightarrow$ Execution) $\rightarrow$ Pre-Trial Studio & Moot Court Arena.
2. **The 6-Layer Deterministic Substantive Legal Engine:** 6-Layer RAG $\rightarrow$ Actor-Critic Process Reward Model $\rightarrow$ 4-Family Document Drafter $\rightarrow$ Supabase PostgreSQL Cloud Persistence.

```
┌────────────────────────────────────────────────────────────────────────┐
│                    Frontend (React 18 + Vite 5 SPA)                    │
│  Hosted at: https://legalgpt-india.web.app (Firebase Hosting)          │
│                                                                        │
│  ├── App.jsx                   Core Omni-Box chat & session state      │
│  ├── AuthPage.jsx              JWT Auth & Guest Session Manager        │
│  ├── ConversationsSidebar.jsx  Multi-Device Supabase chat history      │
│  ├── TrialStudio.jsx           Pre-Trial Moot Court & Cross-Examiner   │
│  ├── EvidenceUploader.jsx      Sec 63 BSA Digital Evidence Processor   │
│  ├── TriageCards.jsx           Strategic SWOT Option Cards             │
│  ├── VetoCard.jsx              Scrutiny Gatekeeper & Limitation Alert  │
│  ├── BNSCorrectionNotice.jsx   2024 Transition Warnings (BNS/BNSS/BSA) │
│  ├── JurisdictionBadge.jsx     Court Pecuniary / Territorial Badging   │
│  ├── UrgencyBanner.jsx         Statutory Limitation Countdown          │
│  ├── ApiKeyModal.jsx           BYOK Groq API Key Management            │
│  └── usePDF.js                 Browser-Side Vector PDF Generator       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS REST (port 443 / 7860)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Backend API Server (Hugging Face Spaces ZeroGPU)           │
│  Hosted at: https://lvvbaaal-legalgpt-api.hf.space                    │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ app.py (ZeroGPU Gradio 5.20 + FastAPI Unification)              │  │
│  │  - demo.launch(server_port=7860, prevent_thread_lock=True)       │  │
│  │  - server_app.include_router(fastapi_app.router)                 │  │
│  │  - demo.block_thread() keeps server active                       │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
│                                    │                                   │
│  ┌─────────────────────────────────▼────────────────────────────────┐  │
│  │ api_server.py (Core Dispatcher & Route Handlers)                 │  │
│  │  - Omni-Box Autonomous Intent Routing (Layer 1)                  │  │
│  │  - 3-Phase Discovery State Machine (triage_state.py)             │  │
│  │  - 4-Family Document Drafting Engine (interview_state.py)       │  │
│  │  - Adversarial IRAC Advocate Mode (irac_agent.py)                │  │
│  │  - Pre-Trial Moot Court & Precedent Engine (trial_studio/)       │  │
│  │  - Sec 63 BSA Electronic Certificate Generator                  │  │
│  │  - Contract Risk Evaluator (layer6_evaluator.py)                 │  │
│  │  - Actor-Critic Fine-Grained PRM (actor_critic.py)               │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
└────────────────────────────────────┼───────────────────────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌────────────────────────────────────────┐  ┌────────────────────────────────────────┐
│   SUPABASE POSTGRESQL CLOUD DATABASE   │  │         LOCAL CHROMADB VECTOR STORE    │
│  Host: aws-0-ap-southeast-1.pooler...  │  │  Path: data/vector_db/                 │
│  Port: 5432 (Session) / 6543 (Tx)      │  │  Model: all-MiniLM-L6-v2 (CPU-pinned)  │
│  Tables: users, conversations, messages│  │  Collections: saulgpt_indian_laws,     │
│  Engine: IPv4 Connection Pooler        │  │               landmark_precedents      │
└────────────────────────────────────────┘  └────────────────────────────────────────┘
```

---

## 2. The 3-Phase Virtual Counsel Workflow

```
[User Input] ──► Phase 1: Discovery (Max 3 Turns)
                      │
                      ├── Turn 1: Story & Relationship
                      ├── Turn 2: Key Evidence & Dates
                      └── Turn 3: Primary Desired Outcome
                      │
                      ▼
                 Phase 2: Strategy (SWOT Matrix)
                      │
                      ├── 4 Action Paths (path_a .. path_d)
                      ├── Success Probability & Time Horizon
                      └── Counsel Override for Exceptional Cases
                      │
                      ▼
                 Phase 3: Execution
                      ├── Document Factory (.docx & .pdf)
                      ├── Procedural Pathfinder Roadmap
                      └── Pre-Trial Moot Court Rehearsal
```

---

## 3. The 6-Layer Deterministic RAG Pipeline

| Layer | Component | File | Key Capabilities & Device Pinning |
| :---: | :--- | :--- | :--- |
| **0** | Conversational Memory | `pipeline_orchestrator.py` | Sliding window of 6 verbatim turns; older turns compressed. |
| **1** | Query Understanding | `layer1_understanding.py` | SpaCy NER, Devanagari Hindi HyDE translation, blank model fallback. |
| **2** | Hybrid Retrieval | `layer2_retrieval.py` | Dense ChromaDB (2,449+ chunks) + BM25 + CrossEncoder (`device="cpu"`). |
| **3** | Big Model Reasoning | `layer3_reasoning.py` | Groq `qwen/qwen3.8-27b` & `openai/gpt-oss-120b` synthesis. |
| **4** | Validation & Guardrails | `layer4_validation.py`, `actor_critic.py` | NLI DeBERTa (`device="cpu"`), Actor-Critic FG-PRM (`max_tokens=800`), 2024 Transition concordance, SC Struck-Down Firewall. |
| **5** | External Search & Triplifier | `layer5_external.py`, `auto_triplifier.py` | Live DuckDuckGo & IndianKanoon scraping; real-time $(h, r, t)$ ingestion. |
| **6** | Evaluator & Relational GNN | `layer6_evaluator.py`, `gnn_engine.py` | 25K character contract review (ICA 1872), PyTorch GNN TransE/RotatE ($\mathbb{R}^{64}$). |

---

## 4. Court-Grade Document Factory (4 Families)

The document drafting engine (`backend/document_generator.py` and `backend/interview_state.py`) implements a 4-Family Architecture:

```
                  DOCUMENT FACTORY
                         │
      ┌──────────────┬───┴──────────┬──────────────┐
      ▼              ▼              ▼              ▼
   LETTER        PLEADING       AFFIDAVIT      AGREEMENT
(Legal Notice, (Order VII CPC (Sworn Deponent (Commercial
 S.138 NIA,     Plaints, Civil Declarations,   Leases, SLAs,
 Demand RPAD)  Petitions)     Stamp Margin)    NDAs)
```

### Key Technical Guardrails:
1. **Dynamic Prompt Sanitization:** Strips all `[User Goal: document]` tags and conversational instruction artifacts before document generation.
2. **Deterministic Fallback Spec Engine (`build_fallback_spec`):** Automatically activated if LLM generation fails or times out. Synthesizes an authentic legal document with formal statutory clauses.
3. **Notice Elements:** RPAD header, Sender `FROM:` block with Date, Recipient `TO:` block, formal heading under Section 138 NIA / relevant Act, numbered factual recitals, statutory 15-day demand clause, enclosures, and advocate signature.
4. **Order VII Rule 11 CPC Triad of Survival:** Mandatory limitation clause, jurisdiction clause, and court valuation clause for plaints.
5. **Dual Cloud Storage & Delivery:** Cached in-memory in `SESSION_DOCUMENTS` and on disk in `./generated_docs/{session_id}.docx`. Delivered via Axios blob stream and browser jsPDF.

---

## 5. Persistence Architecture: Supabase Cloud PostgreSQL

To support high-concurrency cloud deployments across mobile and desktop clients without file lock errors, SaulGPT utilizes **Supabase Managed PostgreSQL** alongside local SQLite:

- **Connection Pooler:** Routed through `aws-0-ap-southeast-1.pooler.supabase.com:5432` (Session Mode) via IPv4, ensuring container accessibility without IPv6 requirements.
- **Relational Tables:**
  - `users`: User registration, bcrypt password hashes, timestamps.
  - `conversations`: Chat sessions with titles, linked to `user_id`.
  - `messages`: Multi-turn user and assistant messages with structured metadata JSON.
- **Failover & Safety:** Automatic fallback to SQLite if PostgreSQL credentials are unset in local test environments.

---

## 6. Security, Key Isolation, & Rate Limiting

- **Bring Your Own Key (BYOK):** Users provide personal Groq API keys (`gsk_...`), stored client-side in `localStorage`. Injected per-request via `X-Groq-Api-Key` headers.
- **Token Budget Guardrails:** Critic PRM calls calibrated to `max_tokens=800` to prevent Groq free-tier 1000 OTPM rate limit exceptions (`429 rate_limit_exceeded`).
- **Memory Stability:** Pre-initialized PyTorch and spaCy pipelines strictly isolated on CPU outside ZeroGPU calls, ensuring 0% OOM crashes.
