# SaulGPT — Complete Feature Architecture

## Project Overview

SaulGPT is an AI-powered Indian Legal Intelligence Assistant using a 6-layer RAG pipeline to answer legal queries, draft documents, evaluate contracts, and provide structured legal analysis. It uses a 3-phase "Virtual Counsel" flow (Discovery → Strategy → Execution) for legal grievance handling with Llama 3.1 8B via Groq.

---

## 1. Backend Systems

### 1.1 API Server & Request Routing

**Source:** ackend/api_server.py (~1662 lines)

FastAPI server (port 8000) with CORS, Groq LLM initialization, and Knowledge Graph startup.

**Endpoints:**

| Method | Route | Auth | Purpose |
|--------|-------|------|---------|
| POST | /api/chat | Optional | Main chat: pipeline, triage state machine, drafting loop, IRAC |
| POST | /api/chat/stream | Optional | SSE-streaming variant |
| POST | /api/upload | No | Contract upload and evaluation (multipart) |
| GET | /api/document/{session_id} | No | Serve generated .docx as download |
| DELETE | /api/history/{session_id} | No | Clear session history |
| DELETE | /api/draft/state/{session_id} | No | Clear drafting state / cancel interview |
| GET | /api/health | No | Health check |
| GET | /api/conversations | Bearer | List conversations (paginated) |
| POST | /api/conversations | Bearer | Create conversation |
| GET | /api/conversations/{id} | Bearer | Load conversation with messages |
| DELETE | /api/conversations/{id} | Bearer | Delete conversation |
| POST | /api/conversations/migrate | Bearer | Bulk-import guest messages for session takeover |
| POST | /api/auth/signup | No | Register user |
| POST | /api/auth/login | No | Login user |
| GET | /api/auth/me | Bearer | Current user info |

**Request Pipeline** (for /api/chat):
1. Auth resolution (JWT or guest)
2. Conversation resolution (map session_id to conv_id or create new)
3. Message persistence (to SQLite if authenticated)
4. Interview state check
5. Interruption guard (clarification/hypothetical/pushback)
6. **Crisis pre-check** (regex: self-harm, active violence, confinement → helplines, stop)
7. Jurisdiction gate (non-Indian queries → rejected before processing)
8. Direct legal query patterns (15 regex → force knowledge mode)
9. Triage LLM call (classify: off-topic / direct legal / educational / document / grievance)
10. Triage state machine routing (3-phase flow or pass-through)
11. Pipeline dispatch (6-layer RAG fallthrough)
12. Response construction (widget metadata: remapped laws, urgency, jurisdiction)
13. Response persistence (conv_id injected for frontend tracking)

**State Stores:**
- ACTIVE_CONVERSATIONS: session_id → conv_id mapping
- SESSIONS: per-session drafting interview state
- SESSION_DOCUMENTS: generated .docx bytes
- TRIAGE_STATES: per-session 3-phase flow state

**Robust JSON Extraction:** _extract_json() with 4-layer fallback (pure JSON → markdown codeblock → markdown key-value → empty dict) used by all three core agents (triage, discovery, strategy).

---

### 1.2 Crisis Detection & Emergency Response

**Source:** `backend/api_server.py` — `_detect_crisis()` + `_CRISIS_PATTERNS`

Regex-based pre-check that fires **before any LLM call or pipeline processing**, positioned between the jurisdiction gate and the triage classification.

**3 crisis categories:**

| Category | Trigger examples | Response |
|---|---|---|
| **Self-harm** | "kill myself", "suicide", "hurt myself", "end my life" | Suicide prevention helplines (AASRA, iCall, Vandrevala) + emergency number |
| **Active violence** | "beating me right now", "trying to kill me", "weapon" | Police (100), National Emergency (112), Women's Helpline (1091) |
| **Confinement** | "locked in", "held against my will", "passport taken" | Police (100), National Emergency (112) |

**Design principle:** Hard stop — no Discovery, no RAG, no pipeline. The system refuses to process further until the user confirms safety.

---

### 1.3 6-Layer RAG Pipeline

**Source:** ackend/pipeline_orchestrator.py (~700 lines)

Sequential pipeline for all non-drafting queries.

**Layer 0: Conversation Memory (Sliding Window)**
- Per-session verbatim turn memory
- Sliding window: 6 turns verbatim, older turns collapsed into key facts
- Thresholds: collapse at 9 turns, summarize at 12 turns
- Key fact extraction: regex for dates, amounts (INR/Rs.), places, section numbers
- Functions: save_turn_to_memory(), get_history_with_summary()

**Layer 1: Query Understanding** (layer1_understanding.py, ~400 lines)
- Language detection (langdetect, fallback "en")
- Intent classification: factual / procedure / definition / comparison / analysis / document / ambiguous
- Entity extraction (spaCy NER: PERSON, ORG, GPE, LAW, DATE, MONEY, TIME)
- Citation extraction (regex: "Section X of Y Act", "Article Z")
- Ambiguity detection (vague phrasing patterns)
- Query reformulation (LLM-based abbreviation expansion)
- spaCy model: en_core_web_sm

**Layer 2: Hybrid Vector Retrieval** (layer2_retrieval.py, ~350 lines)
- Vector DB: ChromaDB, collection "saulgpt_indian_laws"
- Embedding model: all-MiniLM-L6-v2
- Chunks: 1200 chars, 150 overlap (~2409 chunks, 9 acts)
- Hybrid: semantic search + BM25 keyword retrieval
- Cross-encoder reranking: ms-marco-MiniLM-L-6-v2 (8 candidates → 5 results)
- Noise detection: max_score < 0.5 AND spread < 0.15 → web fallback
- Deduplication by content hash
- Citation filtering prioritization

**Layer 3: LLM Reasoning** (layer3_reasoning.py, ~700 lines)
- Model: llama-3.1-8b-instant via Groq (temperature 0.1)
- Mode prompts: knowledge (neutral), analysis (FACTS/ISSUES/LAW/OUTCOME), document (drafting), pathfinder (step-by-step)
- Context: retrieved chunks + conversation history + mode instruction
- Knowledge Graph expansions injected
- Ambiguity handling → clarifying questions

**Layer 4: Response Validation** (layer4_validation.py, ~700 lines)
- Citation verification (regex cross-check against retrieved chunks)
- NLI hallucination check (DeBERTa, fallback to pattern matching)
- Repealed law interception (IPC/CrPC/IEA → BNS/BNSS/BSA; generates remapped_laws)
- Struck-down section detection
- Legal terminology enforcement (informal → formal)
- Disclaimer enforcement
- Remedy validation

**Layer 5: External Data** (layer5_external.py, ~450 lines)
- DuckDuckGo fallback (appends "Indian law indiankanoon indiacode")
- Post-filter to Indian legal domains (.gov.in, indiankanoon.org, indiacode.nic.in)
- IndianKanoon case law scraping (BeautifulSoup)
- Auto-updater (APScheduler, 30-day interval)

**Layer 6: Evaluator** — see Contract Evaluation System (1.6).

---

### 1.4 3-Phase Virtual Counsel Flow

**Source:** ackend/api_server.py (triage state machine), 	riage_state.py, discovery_agent.py, strategy_agent.py, prompts/discovery.py, prompts/strategy.py

Python-enforced state machine replacing old keyword-based triage for legal grievances.

**State Machine** (	riage_state.py, 47 fields):
- current_mode: "idle" | "discovery" | "strategy"
- discovery_profile: structured Phase 1 output
- discovery_turn_count: hard 3-turn cap (Python-enforced)
- strategy_data: SWOT + options
- selected_strategy_id: user-chosen path_a..path_d
- counsel_override: LLM-detected override flag

**Phase 1: Discovery** (discovery_agent.py, prompts/discovery.py)
- Structured 3-turn sequence with fixed objectives per turn:
  - **Turn 0 (Story & Legal Anchor)**: Empathy + brief area-of-law anchor + open-ended story question
  - **Turn 1 (Evidence & Timeline)**: Ask about documentary proof and exact dates; skip if already populated
  - **Turn 2 (Outcome & Priority)**: Ask what the user wants and what matters most; always final turn
- Adaptive skip: each turn checks existing profile and skips if target fields are already filled
- Legal Framework Anchor: LLM names the relevant area of law before asking questions ("This falls under Indian Employment Law")
- Tone Protocol: matches emotional_state (angry/frustrated/desperate/calm)
- Graceful vague-answer handling (no re-asking on "I don't know")
- Hard 3-turn Python cap (enforced by api_server.py line 1205: `discovery_turn >= 2`)
- Discovery Profile output: emotional_state, desired_outcome, evidence_quality, timeline, user_priority, opponent_profile
- 4-layer JSON extraction
- Emotional-language fix: CRITICAL RULE ensures anger/frustration = legal grievance, not off-topic

**Phase 2: Strategy** (strategy_agent.py, prompts/strategy.py)
- SWOT: Strengths, Weaknesses, Opportunities, Threats
- Exactly 4 options (path_a..path_d), each with:
  - route_to: "document" (drafting) or "pathfinder" (procedure)
  - title, description, pros, cons, estimated_timeline, difficulty, success_probability
- Counsel Override for exceptional cases (government opponent, acknowledgment)
- Evidence weakness flagging
- Validation: strips path_e, pads with universal catch-alls, validates route_to
- Unrecognized routing → pathfinder with preamble note

**Phase 3: Execution**
- Document → interview_state field collection
- Pathfinder → 6-layer pipeline in procedural mode
- IRAC Advocate Mode → keyword/button-invoked structured analysis

---

### 1.5 IRAC Advocate Mode

**Source:** ackend/irac_agent.py, prompts/irac.py

Structured legal analysis for law students/advocates. Never invoked as hidden fallback.

**IRAC Structure:** FACTS (neutral) → ISSUES (legal questions) → RULE (RAG-grounded statutes) → APPLICATION (both-sides argumentation) → CONCLUSION (balanced assessment)

**Domain Statute Mappings:** Employment, Contracts, Property, Family, Consumer, Criminal, Torts

**Guardrails:**
- Domain guardrails (no factory acts for white-collar disputes, no constitutional articles unless government opponent)
- All citations RAG-grounded (never outside retrieved docs)
- No verdict — Application argues both sides

**Invocation:** Frontend "Advocate Mode" button + natural language ("advocate", "irac", "deep legal analysis"). Resets to "idle" after output.

---

### 1.6 Document Drafting System

**Interview State** (interview_state.py, ~950 lines)
- State machine: IDLE → INTERVIEWING → DRAFTING → COMPLETE
- Document families: letter, pleading, affidavit, agreement
- 5 predefined schemas: legal_notice, cheque_bounce, employment_notice, fir, rental_agreement
- Each schema: 5-9 fields (sender, recipient, dates, amounts, etc.)

**Dynamic Field Scoping** (dynamic_drafter.py, ~400 lines)
- LLM-driven field identification (max 7 fields)
- Classifies document type from query
- Builds prompt injections from collected values
- Session-cached field scope
- Falls back to static schemas

**Interview Loop:**
- Progressive field-by-field questioning
- Interruption handling (clarification, hypothetical, pushback)
- Unrelated query detection (resets state)
- Progress tracking per message

**Three-Layer Document Gate:**
1. Triage identifies document intent
2. User picks document path from Strategy options
3. Explicit "Shall I draft?" confirmation

**.docx Generation** (document_generator.py, ~980 lines)
- Rendering: python-docx, Times New Roman 12pt, 1-inch margins, 1.5 spacing
- 4-family: letter, pleading, affidavit, agreement
- Primitive functions: add_header, add_title, add_recipient_block, add_subject_line, add_body, add_signature_block, add_enclosures, add_court_details, add_verification, add_pagination

---

### 1.7 Contract Evaluation System

**Source:** ackend/layer6_evaluator.py (~470 lines)

- Format support: PDF (PyMuPDF), DOCX (python-docx)
- Chunking: 5000-character at paragraph boundaries
- Evaluation dimensions: clarity, enforceability, compliance, risk, completeness
- Per-chunk LLM evaluation (llama-3.1-8b-instant)
- Output: overall_score, risk_level (low/medium/high/critical), clauses, summary, recommendations
- Upload max: 50MB

---

### 1.8 Pre-Draft Legal Scrutiny Engine

**Source:** ackend/scrutiny_agent.py (~640 lines)

**ScrutinyResult:** is_valid, issues, warnings, limitation_status, remedy_feasibility, limitation_date, bns_mapping, risk_score (0-100), recommendations

**Checks:**
1. Limitation (12 claim types with periods, exception detection: acknowledgment, continuous wrong, disability, government)
2. Remedy validity
3. BNS/BSA enforcement (IPC/CrPC/IEA → BNS/BNSS/BSA)
4. Field validation per doc type

**Severity Levels:** "serious" (red, blocking), "warning" (gold, acknowledgeable), "info" (teal, acknowledgeable)

---

### 1.9 Legal Knowledge Graph

**Source:** ackend/layer6_knowledge_graph.py (~560 lines)

- NetworkX DiGraph: 89 nodes, 67 edges
- Relationships: Act replacements (IPC→BNS, CrPC→BNSS, IEA→BSA), constitutional hierarchy, cross-act links, procedural chains (FIR→Investigation→Charge Sheet→Trial→Appeal)
- ~30 act aliases resolved to canonical names
- expand_context(): injects graph into pipeline, returns replaced_acts for frontend

---

### 1.10 Authentication & User Persistence

**JWT Auth** (ackend/auth.py, 42 lines)
- bcrypt hashing (passlib)
- JWT: 30-day expiry, HS256

**SQLite DB** (ackend/database.py, ~170 lines)
- Tables: users, conversations, messages
- WAL mode, foreign keys, thread-local connections
- bulk_import_messages() for guest session takeover

---

### 1.11 Legal Data Ingestion Pipeline

**Scraper** (ackend/scraper/, 4 files + config)
- LegalScraperEngine: IndiaCodeScraper (DSpace) + KanoonScraper (BeautifulSoup)
- 25 scrapeable acts in config

**Chunking & Embedding** (2_chunk_and_embed.py, ~469 lines)
- Chunk: 1200 chars, 150 overlap
- Embedding: all-MiniLM-L6-v2
- Universal key detector (14+ key variants per field)
- 5 JSON structures supported
- Lineage header: [Act: X] [Section Y: Z].

**Embedded Acts (9):** BNS 2023, Constitution of India, BNSS 2023, CPC, Negotiable Instruments Act, Hindu Marriage Act, Motor Vehicles Act, BSA 2023, Indian Divorce Act

---

### 1.12 RAG Evaluation Suite

**Source:** ackend/eval_pipeline.py (~250 lines)

8 gold-standard test cases (knowledge, analysis, pathfinder). Metrics: retrieval_coverage, citation_accuracy, hallucination_score, overall_score.

---

## 2. Frontend Application

### 2.1 Core Chat Interface

**Source:** saulgpt-ui/src/App.jsx (935 lines)

**19 State Variables:**
- Auth: token, user, authLoading
- Chat: messages, input, loading, loadingLabel, forceMode, interviewActive
- UI: showSuggestions, showDropZone, showGlossary, glossaryCategory, showSidebar
- Session: convId, refreshTrigger

**Sub-components (inline):**
- TypingIndicator({ label }): animated bot-typing dots
- InterviewProgress({ pct }): progress bar (0-100%)
- RiskBadge({ risk }): color-coded pill (High/Medium/Low)
- PipelineMeta({ data }): collapsible debug panel (citations, repealed laws, validation, confidence)
- Message({ msg, onTriageChoice }): single chat message renderer with markdown, widgets, and export bar
- DropZone({ onFile, disabled }): drag-and-drop contract upload

**7 useEffect Hooks:**
1. convRef sync (prevents stale overwrites)
2. Persist convId to localStorage
3. Page refresh recovery (load conversation from API on mount)
4. Persist guest messages (last 6)
5. Auto-scroll on message/loading change
6. Auto-resize textarea
7. Cross-tab auth sync (storage event listener)

**Key Functions:**
- api(): axios instance with Bearer token + 401 interceptor (auto-logout)
- sendMessage(): core send → POST /api/chat → handle interview/triage/complete states
- handleFile(): contract upload → POST /api/upload
- handleTriageChoice(): triage card → sendMessage
- clearChat(), cancelInterview(), handleAuth(), logout()

**Welcome Screen:** Animated seal, "Your Counsel Awaits", feature cards (Ask/Draft/Evaluate), 5 suggested queries.

**Send Flow:** Validation → optimistic append → POST /api/chat → response processing → loading=false.

**Mode Selector:** 5 buttons (Auto, Knowledge, Analysis, Document, Pathfinder).

**Chat Input:** Auto-resizing textarea, contextual placeholder, disabled during loading, file upload button, send button with spinner.

---

### 2.2 Document Drafting UI

- Interview badge ("Drafting Mode Active" with gold pulse) replaces mode selector during interview
- Cancel button (red, clears draft state)
- Input placeholder changes to "Type your answer..." during interview
- InterviewProgress per message
- .docx download button on completion (meta.document_ready flag)

### 2.3 Contract Evaluation UI

- DropZone (drag-and-drop, accepts PDF/DOCX/TXT, 50MB max)
- Upload button (paperclip icon, disabled during loading)
- "Running Red Pen evaluation..." loading label
- Evaluation response with risk level display

### 2.4 Response Widget System

Each widget conditionally renders based on response metadata:

**BNSCorrectionNotice** (BNSCorrectionNotice.jsx, 118 lines):
- "LEGISLATION UPDATE 2024" card
- Maps old law (IPC/CrPC/IEA, strikethrough red) → new law (BNS/BNSS/BSA, green check)
- Triggered by meta.remapped_laws

**VetoCard** (VetoCard.jsx, 144 lines):
- Collapsible scrutiny result with severity levels
- Serious: red pulsing, blocking gate (Consult Lawyer / Draft Demand Letter)
- Warning/Info: gold/teal, acknowledgment checkbox
- Sections: Limitation Act, Remedy Not Recognized, Law Updated BNS/BNSS
- Auto-corrections display

**UrgencyBanner** (UrgencyBanner.jsx, 83 lines):
- Critical (<30d): red pulsing, siren icon
- Warning (<90d): amber static, clock icon
- Shows limitation days + deadline date
- Triggered by urgency_flags or limitation_days

**JurisdictionBadge** (JurisdictionBadge.jsx, 151 lines):
- Court level: 8 types (Supreme Court gold, High Court teal, District Court green, etc.)
- Jurisdiction type: 8 icons (Civil, Criminal, Consumer, Family, Revenue, etc.)
- Territorial + pecuniary info
- Court description footnote

**TriageCards** (TriageCards.jsx, 121 lines):
- "Strategic Options" with info banners (limitation, jurisdiction)
- Clickable option cards (gold label + description + arrow)
- Action row: SWOT toggle, "Explain These Options", "Advocate Mode"
- Expandable SWOT analysis (4 color-coded boxes)

**PipelineMeta:** Collapsible debug panel showing mode, domain, laws, graph insights, case law, elapsed time, citations, validation status, confidence, hallucination warnings.

**Export Bar:** Copy (clipboard), Download PDF (jsPDF), Download .docx (backend URL).

### 2.5 Conversation Management

**Source:** saulgpt-ui/src/ConversationsSidebar.jsx (87 lines)

- Left panel (260px) with mobile backdrop overlay
- Header: "Chats (N)" + New (+) + Close (X)
- Conversation list: title (truncated 28 chars), relative time, delete on hover
- Active: gold border highlight
- Pagination: "Load more (N remaining)" button
- useEffect: fetches on mount + refreshTrigger change, AbortController cleanup
- Sidebar toggle via hamburger button

**loadConversation():** Clears UI → sets convId early → fetches messages → populates → handles error with message in chat

**newConversation():** Clears UI → setConvId(null) → creates on backend → triggers sidebar refresh

**deleteConversation():** Deletes on backend → clears local state if active → triggers sidebar refresh

### 2.6 Authentication & Session Management

**AuthPage** (AuthPage.jsx, 66 lines):
- Tabbed login/signup form
- Migration overlay (guest session takeover spinner)
- JWT stored in localStorage

**Session Features:**
- Page refresh recovery (loads last conversation from API)
- Guest message persistence (last 6 in localStorage)
- Guest session takeover (bulk-import on login)
- Cross-tab auth sync (storage event listener → auto-logout)
- 401 interceptor (expired token → logout)

### 2.7 Supporting Utilities

**LegalGlossary** (LegalGlossary.js, 287 lines):
- 200+ Indian legal terms with plain-language definitions
- 10 categories: Constitutional, Criminal Law, Criminal Procedure, Commercial Law, Civil Procedure, Consumer Law, Labour Law, Property Law, Family Law, General
- Functions: scanForTerms(), getTermDefinition(), getTermsByCategory(), getCategories()
- Glossary sidebar with category filter + search

**PDF Generation** (usePDF.js, 405 lines):
- jsPDF-based A4 PDF generator
- Professional formatting: letterhead, gold rules, document type label, validation badge, citations block, auto page breaks
- Color palette: gold, ink, sage, red, amber
- Section starters for 13 pattern types
- 25mm margins (Indian legal standard)

---

## 3. Agent Architecture

### 3.1 Central LLM Client

**Source:** ackend/agents/llm_client.py

4 pre-initialized ChatGroq instances:
- Researcher: mixtral-8x7b-32768 (temperature 0.1)
- Drafter: llama-3.1-8b-instant (temperature 0.1)
- Reviewer: llama-3.1-8b-instant (temperature 0.1)
- Triage: llama-3.1-8b-instant (temperature 0.1)

All load GROQ_API_KEY from .env.

### 3.2 Agent Manager & Routing

**Source:** ackend/agents/manager.py

AgentManager with mode detection (regex patterns) and route dispatch:
- legal_query → ResearcherAgent
- case_analysis → ResearcherAgent (analysis mode)
- pathfinder → ResearcherAgent (pathfinder mode)
- document → DrafterAgent
- interviewing → DrafterAgent
- evaluate → ReviewerAgent
- scrutiny → ReviewerAgent

### 3.3 Sub-Agents

**TriageAgent** (gents/triage.py): Query classification (LLM + keyword fallback), TOWS analysis generation.

**ResearcherAgent** (gents/researcher.py): Knowledge Q&A, case analysis (FACTS/ISSUES/LAW/OUTCOME), pathfinder (step-by-step). Includes IPC/CrPC→BNS/BNSS mapping.

**DrafterAgent** (gents/drafter.py): Document type detection, field collection, LLM document generation.

**ReviewerAgent** (gents/reviewer.py): Contract evaluation, pre-draft scrutiny, limitation check, red flag detection, veto check.

---

## 4. Data Layer & Cloud Persistence

### 4.1 Supabase Managed PostgreSQL (Primary Cloud Database)
- **Host:** `aws-0-ap-southeast-1.pooler.supabase.com`
- **Port:** `5432` (Session Mode) / `6543` (Transaction Mode)
- **Engine:** IPv4 Connection Pooler bypassing IPv6 container restrictions
- **Tables:** `users`, `conversations`, `messages`
- **Indexes:** `idx_conversations_user_id`, `idx_messages_conv_id`, `idx_messages_conversation_id`
- **Concurrency:** Multi-device simultaneous read/write with zero file-locking bottlenecks

### 4.2 Local SQLite Fallback
- **File:** `backend/saulgpt.db`
- **Mode:** WAL (Write-Ahead Logging) for concurrent access
- Automatically activated if `DATABASE_URL` is omitted in local development

### 4.3 ChromaDB (Vector Store)
- **Collection:** `saulgpt_indian_laws` & `landmark_precedents`
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` pinned to `device="cpu"`
- **Total Chunks:** 2,449+ statutory and case law segments
- **Path:** `data/vector_db/`

### 4.4 JSON Raw Data Sources
- **Path:** `data/raw_data/`
- Contains canonical acts: BNS 2023, BNSS 2023, BSA 2023, CPC 1908, NIA 1881, HMA 1955, MVA 1988, IDA 1869, Constitution of India

### 4.5 Relational GNN Knowledge Graph (In-Memory)
- NetworkX DiGraph + PyTorch continuous embeddings (TransE/RotatE in $\mathbb{R}^{64}$)
- 73 canonical legal relations, 268 nodes, 172 triples

---

## 5. Pre-Trial Studio & Moot Court Arena

**Source:** `backend/trial_studio/`, `saulgpt-ui/src/TrialStudio.jsx`

Interactive adversarial courtroom simulation providing rigorous trial preparation before an actual hearing.

### 5.1 Hostile Section 146 BSA Cross-Examiner
- Implements aggressive cross-examination tactics targeting documentary gaps, oral inconsistencies, and tax filing contradictions under Section 146 of the Bharatiya Sakshya Adhiniyam, 2023.
- Formulates multi-turn traps designed to impeach witness credibility.

### 5.2 Confidential Corner Coach & Tactical Counsel
- Operates in real time alongside the courtroom examination.
- Real-time exposure gauge (Low / Medium / High Risk).
- Flags formal procedural objections (e.g. hearsay, leading questions, questions without foundation).
- Provides verbatim, safe witness rejoinders that avoid fatal admissions.
- Suggests tangible evidentiary plugs to introduce into the record.

### 5.3 Precedent Intelligence Engine
- Indexed database of **50,000+ landmark Supreme Court and High Court judgments** across 8 frameworks: BNS, BNSS, BSA, NI Act, CPA 2019, Contract Act, Limitation Act, Arbitration Act.
- Fallback keyword detection matches dispute patterns to governing precedents.

### 5.4 Split-Chamber UI
- Left Column: Formal Courtroom Chamber with judge/counsel dialogue stream and witness stand.
- Right Column: Confidential Corner Coach Console with live exposure meter and objection arsenal.

---

## 6. Section 63 BSA Digital Evidence Grounding

**Source:** `backend/evidence_processor.py`, `saulgpt-ui/src/EvidenceUploader.jsx`

End-to-end processing and certification of electronic records under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (formerly Section 65B IEA).

### 6.1 Cryptographic Hash Verification
- Dual-tier SHA-256 integrity calculation: computed client-side in the browser on file selection, and independently re-verified server-side on upload.
- Detects any bitwise tampering during transit.

### 6.2 Cheque OCR & 30-Day Statutory Clock
- Extracts bank return memos, dishonour codes (e.g. "Funds Insufficient", "Account Closed"), drawer/payee names, and amount.
- Automatically calculates the mandatory 30-day statutory notice window under Section 138 NIA.

### 6.3 Debtor Audio Admission & Limitation Extender
- Transcribes and semantically parses voice admissions and debt promises.
- Applies Section 18 of the Limitation Act, 1963 to compute revised limitation expiry dates based on valid acknowledgments of liability.

### 6.4 Court-Admissible Electronic Certificate Generation
- Automatically drafts a formal Section 63 BSA compliance certificate.
- Details device identifiers, cryptographic hash, extraction date, custodian signature block, and truth verification.
- 1-click integration transmits certified evidence directly into the Pre-Trial Studio.

---

## 7. Actor-Critic Fine-Grained Process Reward Model (FG-PRM)

**Source:** `backend/actor_critic.py`, `backend/layer4_validation.py`

Neuro-symbolic reinforcement validation that scrutinizes reasoning chains before emitting legal counsel.

### 7.1 Multi-Dimensional Step Evaluation
- Evaluates four orthogonal dimensions:
  1. **Factuality & Citation Validity:** Verifies whether cited sections actually exist and match the proposition.
  2. **Statutory Applicability:** Prevents application of repealed statutes (IPC/CrPC) or struck-down provisions.
  3. **Logical Soundness & Neutrality:** Checks for non-sequiturs or premature conclusions.
  4. **Tone & Client Empathy:** Ensures professional, measured legal counsel matching client distress.

### 7.2 Dynamic Token Budgeting (`max_tokens=800`)
- PRM feedback loop strictly constrained to `max_tokens=800`.
- Eliminates Groq free-tier 1000 OTPM rate limit exceptions (`429 rate_limit_exceeded`) while preserving comprehensive critique.

### 7.3 Fast-Path Bypasses
- Low-complexity queries bypass secondary critic passes, ensuring sub-second response latency.

---

## 8. High-Capacity Contract Evaluator (Layer 6)

**Source:** `backend/layer6_evaluator.py`, `saulgpt-ui/src/App.jsx`

Deep structural analysis of commercial and employment agreements.

### 8.1 25,000-Character Single-Pass Ingestion
- Evaluates extensive multi-page contracts in a unified prompt context, eliminating fragmentation and cross-chunk context loss.

### 8.2 Indian Contract Act 1872 Auditing
- **Section 27 (Restraint of Trade):** Flags void post-employment non-compete clauses.
- **Section 28 (Restraint of Legal Proceedings):** Identifies illegal time limits on litigation.
- **Section 74 (Liquidated Damages vs. Penalties):** Scrutinizes disproportionate penalty clauses.

### 8.3 Tri-Level Risk Scoring
- 🔴 **High Risk:** Void/unlawful terms requiring immediate deletion.
- 🟡 **Medium Risk:** Unbalanced commercial exposure (unilateral indemnity, unlimited liability).
- 🟢 **Low Risk:** Fair, reciprocal covenants.
- Outputs concrete, redlined clause replacements ready for negotiation.

---

## 9. 4-Family Court-Grade Document Factory

**Source:** `backend/interview_state.py`, `backend/document_generator.py`

Synthesizes print-ready, legally enforceable documents in Microsoft Word (`.docx`) and vector PDF formats.

### 9.1 Supported Document Families
1. **Letter / Notice Family (`letter`):**
   - Section 138 NIA Cheque Bounce Notices, Demand Notices for Unpaid Salary, Tenancy Default Notices.
   - Formal RPAD header, Sender `FROM:` block, Recipient `TO:` block, 15-day statutory demand clause, advocate signature block.
2. **Pleading Family (`pleading`):**
   - Civil Plaints under Order VII Rule 1 CPC, Section 223 BNSS Criminal Complaints.
   - Enforces the **Triad of Survival:** Cause of Action & Limitation, Territorial/Pecuniary Jurisdiction, and Court Valuation with Order VI Rule 15 verification split.
3. **Affidavit Family (`affidavit`):**
   - Sworn deponent affidavits with 5.5-inch stamp paper top margin and dual notary verification (personal knowledge vs. legal advice).
4. **Agreement Family (`agreement`):**
   - Commercial Leases, SLAs, NDAs with recitals, operative covenants, Section 7 Arbitration clause, and dual witness blocks.

### 9.2 Zero Prompt Leakage & Clean Formatting
- **Sanitization Pipeline:** Strips all `[User Goal: document]` tags, instruction strings, and raw dictionary keys.
- **Deterministic Fallback Spec Engine:** If the LLM spec generator times out, `build_fallback_spec()` automatically constructs an authentic, clause-complete legal document.
- **Resilient Cloud Delivery:** Cached in memory and on disk (`./generated_docs/`), delivered via Axios blob stream with fallback browser navigation.

---

## 10. Security, Cloud Infrastructure & BYOK Architecture

### 10.1 Hugging Face Spaces ZeroGPU Backend
- Configured via `app.py` unifying Gradio 5.20 and FastAPI on port 7860.
- Dynamic GPU allocation (`zero-a10g`) with PyTorch embeddings strictly pinned to CPU to prevent ZeroGPU CUDA supervisor aborts.

### 10.2 Bring Your Own Key (BYOK)
- Users can provide their personal Groq API keys (`gsk_...`) in `ApiKeyModal.jsx`.
- Stored exclusively in the user's browser `localStorage` and passed per-request via the `X-Groq-Api-Key` HTTP header.
- Zero server-side key logging or persistence.

---

## File Reference Summary

**Backend (25 root + 4 trial_studio + 6 agents + 8 prompts + 4 scraper + 3 tests = 50 Python files)**
- `app.py` — ZeroGPU Gradio 5.20 + FastAPI server entrypoint
- `deploy_hf.py` — Automated deployment script for Hugging Face Spaces
- `api_server.py` — Core FastAPI controller and route dispatcher
- `pipeline_orchestrator.py` — 6-layer deterministic RAG controller
- `actor_critic.py` — Actor-Critic Fine-Grained Process Reward Model
- `evidence_processor.py` — Section 63 BSA electronic evidence & certification
- `layer1_understanding.py` — Query understanding, Hindi HyDE, spaCy NER
- `layer2_retrieval.py` — ChromaDB vector retrieval & Cross-Encoder (CPU)
- `layer3_reasoning.py` — LLM response generation via Groq
- `layer4_validation.py` — DeBERTa NLI & SC Struck-Down Firewall
- `layer5_external.py` — IndianKanoon / DuckDuckGo live search fallback
- `layer6_evaluator.py` — 25,000-character contract risk evaluation
- `layer6_knowledge_graph.py` — Relational legal knowledge graph (NetworkX)
- `interview_state.py` — Document drafting state machine & fallback spec engine
- `document_generator.py` — 4-family .docx generation (Letter, Pleading, Affidavit, Agreement)
- `dynamic_drafter.py` — Dynamic field scoping
- `scrutiny_agent.py` — Pre-draft limitation and validity scrutiny
- `discovery_agent.py` — Phase 1: 3-turn empathetic investigation
- `strategy_agent.py` — Phase 2: SWOT matrix & 4-path generation
- `irac_agent.py` — Advocate Mode IRAC structured brief generator
- `triage_state.py` — 3-phase flow state machine
- `database.py` — Supabase PostgreSQL + SQLite dual CRUD engine
- `auth.py` — JWT authentication and bcrypt password hashing
- `eval_pipeline.py` — Automated RAG benchmarking suite
- `trial_studio/cross_examiner_agent.py` — Hostile Sec 146 BSA cross-examiner
- `trial_studio/defense_fortifier_agent.py` — Corner Coach procedural objections
- `trial_studio/precedent_engine.py` — 50,000+ landmark judgments index
- `trial_studio/session_manager.py` — Moot court session persistence

**Frontend (16 script + 6 CSS files)**
- `App.jsx` — Core Omni-Box chat interface & session controller
- `AuthPage.jsx` — JWT Login/Signup & guest session migration
- `ConversationsSidebar.jsx` — Supabase cloud-synced conversation list
- `TrialStudio.jsx` — Split-Chamber Pre-Trial Moot Court Arena
- `EvidenceUploader.jsx` — Sec 63 BSA evidence uploader with hash verification
- `TriageCards.jsx` — Strategic SWOT 4-path cards
- `VetoCard.jsx` — Scrutiny blocker & limitation warning card
- `BNSCorrectionNotice.jsx` — 2024 Transition notification banner
- `JurisdictionBadge.jsx` — Court pecuniary & territorial indicator
- `UrgencyBanner.jsx` — Statutory limitation countdown banner
- `ApiKeyModal.jsx` — Bring-Your-Own-Key (BYOK) modal
- `LegalGlossary.js` — 200+ Indian legal term dictionary
- `usePDF.js` — Client-side jsPDF A4 vector rendering engine
- `App.css`, `TrialStudio.css`, `EvidenceUploader.css` — Courtroom styling
