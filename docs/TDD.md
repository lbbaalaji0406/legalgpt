# 🛠️ SaulGPT — Technical Design Document (TDD)
**Document Version:** 2.2.0  
**Target Release:** Production Cloud (Hugging Face Spaces + Supabase + Firebase)  
**System Architecture:** Hybrid Cloud Neuro-Symbolic Micro-Services  
**Programming Languages:** Python 3.10/3.11, JavaScript (ES2022), React 18, SQL (PostgreSQL / SQLite)

---

## 1. Cloud Architecture & Infrastructure Topology

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (Web Browser)                     │
│  Hosted at: https://legalgpt-india.web.app (Firebase Hosting)          │
│  Technologies: React 18, Vite 5, Axios Interceptors, jsPDF, Vanilla CSS│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS REST + CORS (Port 443)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             BACKEND API LAYER (Hugging Face Spaces - ZeroGPU)          │
│  Hosted at: https://lvvbaaal-legalgpt-api.hf.space                    │
│  Hardware: zero-a10g (16 GB VRAM, Dynamic GPU Allocation)              │
│  Framework: FastAPI (mounted within Gradio 5.20 ASGI Server)           │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ app.py (ZeroGPU Entrypoint)                                      │  │
│  │ ├─ demo.launch(server_port=7860, prevent_thread_lock=True)       │  │
│  │ ├─ server_app.include_router(fastapi_app.router)                 │  │
│  │ └─ demo.block_thread()                                           │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
│                                    │                                   │
│  ┌─────────────────────────────────▼────────────────────────────────┐  │
│  │ api_server.py (Core Controller & Pipeline Dispatcher)            │  │
│  │ ├─ Layer 1: Query Analysis & Hindi HyDE                          │  │
│  │ ├─ Layer 2: Hybrid Retrieval (ChromaDB + CrossEncoder on CPU)    │  │
│  │ ├─ Layer 3: LLM Inference via Groq API (Qwen 2.5 / GPT-OSS 120B) │  │
│  │ ├─ Layer 4: Validation & Actor-Critic FG-PRM (max_tokens=800)    │  │
│  │ ├─ Layer 5: IndianKanoon / DDG Search Fallback                   │  │
│  │ ├─ Layer 6: Relational GNN & Contract Risk Evaluator             │  │
│  │ └─ Document Engine: 4-Family Spec Generator & Fallback Builder   │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
└────────────────────────────────────┼───────────────────────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌────────────────────────────────────────┐  ┌────────────────────────────────────────┐
│     PERSISTENCE (Supabase PostgreSQL)  │  │         VECTOR DB (Local ChromaDB)     │
│  Host: aws-0-ap-southeast-1.pooler...  │  │  Storage: data/vector_db/              │
│  Port: 5432 (Session) / 6543 (Tx)      │  │  Model: all-MiniLM-L6-v2 (CPU-pinned)  │
│  Tables: users, conversations, messages│  │  Collections: saulgpt_indian_laws,     │
│  Engine: IPv4 Connection Pooler        │  │               landmark_precedents      │
└────────────────────────────────────────┘  └────────────────────────────────────────┘
```

---

## 2. 6-Layer Deterministic RAG Pipeline Implementation

### Layer 0: Conversational Memory & Sliding Window (`pipeline_orchestrator.py`)
- **Memory Window:** Retains up to 6 most recent turns verbatim.
- **Older Turn Summarization:** Summarizes turns older than 6 to preserve essential facts while fitting within model context budgets.
- **Session Scoping:** Keyed by unique `session_id` or authenticated `conv_id`.

### Layer 1: Query Understanding & Devanagari Hindi HyDE (`layer1_understanding.py`)
- **Devanagari Hindi Detection:** Recognizes pure Hindi script and colloquial Hinglish legal terms (*chori, zameen, kabza, FIR, thana*).
- **Hypothetical Document Embeddings (HyDE):** Translates vernacular concepts into canonical statutory search vectors.
- **SpaCy NER & Blank Model Fallback:**
  ```python
  def _ensure_nlp():
      global _nlp
      if _nlp is None:
          try:
              import spacy
              _nlp = spacy.load("en_core_web_sm")
          except Exception:
              import spacy
              _nlp = spacy.blank("en")  # Fallback for Linux Cython 64-bit int compatibility
      return _nlp
  ```

### Layer 2: Hybrid Retrieval & Cross-Encoder Reranking (`layer2_retrieval.py`)
- **Dense Vector Search:** ChromaDB collection (`saulgpt_indian_laws`, 2,449+ statutory chunks).
- **Sparse BM25:** Lexical matching on exact section citations and penal acts.
- **CPU Device Pinning:**
  ```python
  _embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
  _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")
  ```
  *Note:* Explicitly pinned to `device="cpu"` to prevent ZeroGPU CUDA initialization errors (`torch._C._cuda_init`) outside decorated `@spaces.GPU` functions.

### Layer 3: Big Model Reasoning (`layer3_reasoning.py`)
- **Primary LLM:** Groq `qwen/qwen3.8-27b` (default high-throughput reasoning).
- **Secondary Fallback:** Groq `openai/gpt-oss-120b` (complex multi-issue synthesis).
- **System Prompt:** Enforces strict Indian jurisprudence, mandatory citation of enacted laws (BNS, BNSS, BSA 2023), and formal disclaimer notices.

### Layer 4: Validation, Fact-Checking, & Actor-Critic PRM (`layer4_validation.py`, `actor_critic.py`)
- **NLI Fact-Checking:** DeBERTa NLI cross-examines generated premises against retrieved statutory chunks (`device="cpu"`).
- **Actor-Critic Fine-Grained Process Reward Model (FG-PRM):**
  - **Critic Pass:** Performs fine-grained step-level auditing across statutory accuracy, completeness, and omission risk.
  - **Process Reward Score:** Computes a continuous metric (0.0 to 1.0).
  - **Token Budget Calibration:** Enforces `max_tokens=800` on Critic JSON calls to strictly honor Groq free tier 1000 OTPM output limits:
    ```python
    res = client.chat.completions.create(
        model=primary_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=800,
        response_format={"type": "json_object"}
    )
    ```

### Layer 5: External Search & Auto-Ingest (`layer5_external.py`, `scraper/`)
- **DuckDuckGo & IndianKanoon Scraper:** Scrapes live judgments when local vector confidence is low.
- **Dynamic Triplifier:** Extracts $(h, r, t)$ relational triples and updates the Knowledge Graph dynamically.

### Layer 6: Relational GNN & Evaluator (`gnn_engine.py`, `layer6_evaluator.py`)
- **PyTorch Relational GNN:** Embeds statutory pathways in 64-dimensional space using MarginRankingLoss.
- **Contract Risk Evaluator:** Single-pass evaluation of up to 25,000 characters against Indian Contract Act Sections 27, 28, and 74.

---

## 3. Interactive Document Drafter Technical Architecture

### 3.1 State Machine Lifecycle (`interview_state.py`)

```
   [IDLE]
     │ (User requests draft)
     ▼
[INTERVIEWING] <─── (Answers Field 1..N)
     │
     ├─ (Interruption: Clarification / Pushback / Hypothetical)
     │     ▼
     │   [INTERRUPTED] ─── (Resolved) ───► [INTERVIEWING]
     │
     │ (All fields collected)
     ▼
[PENDING_GENERATION] (Confirmation prompt: "Shall I generate?")
     │
     ├── (User confirms: "Yes") ────────► [DRAFTING] ──► [COMPLETE]
     └── (User cancels: "No") ──────────► [IDLE]
```

### 3.2 Dual-Tier Document Specification Generation
1. **Tier 1: LLM-Driven Dynamic Spec Generator (`generate_document_spec`):**
   - Injects family-specific system prompts (`FAMILY_SPEC_PROMPTS`) for `letter`, `pleading`, `affidavit`, and `agreement`.
   - Sanitizes problem description with `sanitize_narrative_text()` to prevent prompt leakage.
   - Outputs a validated JSON structure with 10+1 section primitives.
2. **Tier 2: Deterministic Fallback Spec Engine (`build_fallback_spec`):**
   - Automatically invoked if LLM is unavailable, rate-limited, or returns invalid JSON.
   - Constructs canonical, court-admissible legal notices (e.g. Section 138 NIA 15-day demand notices) from collected fields without ever leaking user prompts.

### 3.3 Word Document (.docx) Generator (`document_generator.py`)
- **Primitives Rendered:** `heading`, `subheading`, `body_p`, `numbered_list`, `field_row`, `schedule_box`, `signature`, `prayer`, `attestation`, `enclosure`, `cc`, `witness`.
- **Notice Structure:**
  - `RPAD` dispatch header.
  - Formatted `FROM:` block (Sender Name & Postal Address).
  - Formal `DATE:` run.
  - Formatted `TO:` block (Recipient Name & Registered Address).
  - Numbered factual & legal recitals.
  - Statutory 15-day demand clause.
  - Advocate signature & enrollment number footer.
- **Storage & Delivery:**
  - In-memory cache: `SESSION_DOCUMENTS: dict[str, bytes]`.
  - Disk cache: `./generated_docs/{session_id}.docx` for persistent cross-restart availability.
  - Endpoint: `GET /api/document/{session_id}` returns binary blob with `Content-Disposition: attachment`.

---

## 4. Database Schema & Persistence Architecture

### 4.1 Supabase Managed PostgreSQL DDL

```sql
-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversations Table
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New Chat',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages Table
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conv_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    meta TEXT,
    turn INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for Sub-Millisecond Conversation Fetching
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conv_id ON messages(conv_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
```

### 4.2 IPv4 Connection Pooler Configuration
- **Supabase Host:** `aws-0-ap-southeast-1.pooler.supabase.com`
- **Port:** `5432` (Session Mode) / `6543` (Transaction Mode)
- **User Format:** `postgres.[project-ref]`
- **Bypasses IPv6 Container Restrictions:** Directly accessible from Hugging Face Docker/Gradio containers without requiring an IPv6 gateway.

---

## 5. Security & BYOK Architecture

```
User Browser (React UI)
  │
  ├─ 1. User enters personal Groq key (gsk_...) in ApiKeyModal.jsx
  ├─ 2. Key validated via regex: /^gsk_[A-Za-z0-9]{40,}$/
  ├─ 3. Key stored strictly in browser localStorage ("saulgpt_user_groq_key")
  │
  ▼ (Every outgoing Axios HTTP Request)
Axios Request Interceptor (main.jsx)
  │
  ├─ Injects Header: "X-Groq-Api-Key: gsk_..."
  │
  ▼ (HTTPS encrypted payload)
Hugging Face Spaces Backend (api_server.py)
  │
  ├─ Reads header: fastapi_request.headers.get("x-groq-api-key")
  ├─ ContextVar injection: set_effective_groq_key(effective_key)
  ├─ Zero Database / Disk Logging of user API keys
  │
  ▼
Groq API Gateway (Executed using user's quota)
```

---

## 6. Frontend Architecture & Export Pipeline

### 6.1 State Management & Interceptors
- **`App.jsx`:** Manages conversation state, active evidence, sidebars, and chat turn lists.
- **`apiConfig.js`:** Centralizes `API_BASE` resolution:
  ```javascript
  export const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/+$/, "");
  ```
- **Global Response Interceptor:** Catches `429 Rate Limit` events and broadcasts custom events to display the BYOK modal.

### 6.2 Resilient Document Download Workflow
```javascript
const handleDocxDownload = async (e) => {
  e.preventDefault();
  const targetUrl = docUrl.startsWith("http") && !docUrl.includes("localhost:8000")
    ? docUrl
    : `${API_BASE}${docUrl.replace(/https?:\/\/(localhost|127\.0\.0\.1):8000/, "")}`;
  try {
    const res = await axios.get(targetUrl, { responseType: "blob" });
    const blob = new Blob([res.data], {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    });
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.setAttribute("download", `legal_document_${msg.session_id || "draft"}.docx`);
    document.body.appendChild(link);
    link.click();
    link.parentNode.removeChild(link);
    window.URL.revokeObjectURL(blobUrl);
  } catch (err) {
    window.open(targetUrl, "_blank");
  }
};
```
