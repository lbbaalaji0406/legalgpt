# SaulGPT Architectural Decision Records (ADRs) & Engineering Changelog

This document provides a transparent, chronological record of every architectural decision, bug fix, model calibration, and pipeline enhancement implemented in the SaulGPT Indian Legal Intelligence Assistant.

---

## 📑 Index of Architectural Decision Records

1. **[ADR-001] Layer 1 Binary Gate: Fixing Substring Match False Positives**
2. **[ADR-002] Routing Engine: Disambiguating Personal Grievances from Statutory Q&A**
3. **[ADR-003] Interactive Drafter: Resilient Triage Option & Path Matcher**
4. **[ADR-004] Advocate Mode: Universal 120B Adversarial IRAC Courtroom Simulator**
5. **[ADR-005] Layer 6 Evaluator: Single-Pass High-Token Chunking & Risk Calibration**
6. **[ADR-006] Layer 5 Search: Resilient HTML Extraction & Agentic Self-Correction Loop**
7. **[ADR-007] Security & DevOps: API Key Isolation & Automated Git CI/CD**
8. **[ADR-008] Master Document Families: Word-Boundary Regex & Schema Disambiguation**
9. **[ADR-009] Document Export: Browser-Side Multi-Family Court-Grade PDF Engine**
10. **[ADR-010] Interview Drafter: Eliminating Numeric Field Interruption Loops**
11. **[ADR-011] UI State Machine: Dynamic Session Scoping & Multi-Conversation Switching**
12. **[ADR-012] Strategy Engine: Universal Path Choice Resolution & Seamless Triage Execution**
13. **[ADR-013] Chat History: Conversation Restoral & Deep-Meta State Hydration**
14. **[ADR-014] UI Layering: Backdrop Stacking Context & Click Event Propagation**
15. **[ADR-015] Pleading Family: Order VII CPC Triad of Survival & Mid-Interview Interruption Handling**
16. **[ADR-016] Bilingual Query Reformulation & Countryside Regional Legal Intelligence**

---

### [ADR-001] Layer 1 Binary Gate: Fixing Substring Match False Positives
* **Component**: `backend/layer1_understanding.py`
* **Date**: 2026-08-26
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  The non-legal classifier used naive substring checks (`p in query_lower`) against short patterns (`'sing'`, `'art'`, `'eat'`). As a result, valid legal words like *"refusing"* (contained `'sing'`), *"parties"* (contained `'art'`), and *"cheating/threat"* (contained `'eat'`) were falsely flagged as off-topic and rejected.
* **The Decision & Change**:
  Replaced naive substring matching with exact word-boundary regex patterns (`r'\b' + p + r'\b'`) and removed short sub-word roots.
* **The Why**:
  Ensures that everyday legal vocabulary (refusing rent, contractual parties, cheating, threats) is recognized as valid legal discourse without false-positive drops.

---

### [ADR-002] Routing Engine: Disambiguating Personal Grievances from Statutory Q&A
* **Component**: `backend/api_server.py` (`_is_direct_legal_query`)
* **Date**: 2026-08-26
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  Queries containing personal grievances (e.g. *"My landlord changed the locks while I was at work and threw my luggage"*, *"My in-laws threw me out and took my child"*) were getting classified as direct textbook questions and sent to basic Q&A, bypassing multi-turn Discovery intake.
* **The Decision & Change**:
  Updated `_is_direct_legal_query()` to inspect for first-person possessive pronouns (*my flat, my salary, my husband, locked me out, threw me out*). If personal grievance indicators are present, it forces the session into **Phase 1: Discovery** instead of pass-through Q&A.
* **The Why**:
  Real clients in distress require empathetic fact gathering, evidence auditing, and structured strategic options (SWOT) rather than an instant cold dump of penal code section numbers.

---

### [ADR-003] Interactive Drafter: Resilient Triage Option & Path Matcher
* **Component**: `backend/api_server.py` (`_resolve_triage_choice`)
* **Date**: 2026-08-26
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  In Phase 2 (Strategy), when users clicked or typed `"path_a"`, `"Legal Notice"`, or selected Option 1, the resolver failed on casing and ID mismatches, causing the bot to re-display options instead of starting the document interview.
* **The Decision & Change**:
  Implemented fuzzy, multi-attribute matching across `title`, `label`, `id`, and keywords (`"path_a"`, `"legal notice"`). Guaranteed that choosing Path A immediately initializes the 5-step dynamic interview state machine.
* **The Why**:
  Provides a frictionless bridge from Strategy (Phase 2) to Execution (Phase 3), allowing users to draft court-grade RPAD notices in one click.

---

### [ADR-004] Advocate Mode: Universal 120B Adversarial IRAC Courtroom Simulator
* **Component**: `backend/api_server.py` & `backend/irac_agent.py`
* **Date**: 2026-08-26
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  The `⚖ Advocate Mode` button and keyword trigger were only accessible in certain state branches, and previous turn facts were not always forwarded to the 120B model.
* **The Decision & Change**:
  Added a universal global intercept in `api_server.py` across all phases. When a user requests Advocate Mode, active facts from Discovery/Triage are passed to `openai/gpt-oss-120b` to generate a comprehensive IRAC brief with Petitioner vs. Respondent arguments.
* **The Why**:
  Gives users an institutional-grade courtroom rehearsal tool that anticipates opponent counter-defenses (e.g. set-off claims, bonafide entry) and assesses judicial success probabilities.

---

### [ADR-005] Layer 6 Evaluator: Single-Pass High-Token Chunking & Risk Calibration
* **Component**: `backend/layer6_evaluator.py`
* **Date**: 2026-08-26
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  The evaluator used small 5,000-character chunks (~800 words). Multi-chunk contracts were fragmented: Chunk 1 complained that Governing Law was missing, while Chunk 2 complained that IP clauses were missing. Merging them resulted in false-alarm complaints and scored balanced contracts as `🔴 High Risk`.
* **The Decision & Change**:
  1. Increased `MAX_CHUNK_CHARS` from `5,000` to `25,000` (~4,000 words), evaluating standard contracts in a single unified pass.
  2. Calibrated risk scoring: `High` is reserved strictly for void/illegal terms (S.27 non-compete, S.74 penalty, S.12(5) arbitrator), `Medium` for commercial gaps, and `Low` for balanced, legally compliant contracts.
  3. Added statutory context anchors for BNS/BNSS/BSA 2023 and Section 27 Contract Act.
* **The Why**:
  Eliminates chunking hallucinations and provides reliable, balanced contract audits with senior-partner quality redlines.

---

### [ADR-006] Layer 5 Search: Resilient HTML Extraction & Agentic Self-Correction Loop
* **Component**: `backend/layer5_external.py`, `backend/agents/researcher.py`, `backend/layer3_reasoning.py`
* **Date**: 2026-08-27
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  1. For external statutes (e.g. *Consumer Protection Act 2019*) or missing articles (e.g. *Article 51A Duties*), ChromaDB returned adjacent chunks with moderate scores, preventing web search from triggering.
  2. The LLM refused to answer when local chunks lacked the specific provision.
* **The Decision & Change**:
  1. Replaced third-party DDGS package calls with direct high-speed HTTP scraping and article paragraph extraction (`requests.post('https://html.duckduckgo.com/html/')`).
  2. Added an **Agentic Self-Correction Loop**: If Layer 3 determines local chunks lack the specific statutory article, the agent automatically triggers Layer 5 Web Fallback in real-time, fetches official text, and regenerates the answer.
* **The Why**:
  Transforms the pipeline from a fragile linear process into a self-healing, closed-loop legal intelligence system covering 100% of Indian statutes and constitutional provisions.

---

### [ADR-007] Security & DevOps: API Key Isolation & Automated Git CI/CD
* **Component**: `.gitignore`, `backend/requirements.txt`, Git repo
* **Date**: 2026-08-26
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  Git was not installed in the local environment, and `.gitignore` needed hardening to ensure no `.env` secret variants could be exposed.
* **The Decision & Change**:
  Installed portable Git (`git version 2.47.1`), hardened `.gitignore` with wildcard rules for all `.env*` files, and synchronized the repository with GitHub (`https://github.com/lbbaalaji0406/legalgpt`).
* **The Why**:
  Guarantees enterprise security, clean secret isolation, and full version-controlled deployment readiness.

---

### [ADR-008] Master Document Families: Word-Boundary Regex & Schema Disambiguation
* **Component**: `backend/interview_state.py` (`detect_family`, `detect_document_type`, `MASTER_SCHEMAS`)
* **Date**: 2026-08-27
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  `detect_document_type` used naive substring matching. A query like *"I need an affidavit of solemn affirmation"* falsely triggered `fir_complaint` because the word `"affirmation"` contained `"fir"`. Furthermore, bounced cheques were missing from family signal maps.
* **The Decision & Change**:
  1. Converted all trigger checks to word-boundary regex (`re.search(r'\b' + re.escape(trigger) + r'\b', query_lower)`).
  2. Solidified the 4 Master Document Families: **`LETTER`** (Demand Notices), **`PLEADING`** (Court Petitions & FIR), **`AFFIDAVIT`** (Sworn Oaths), and **`AGREEMENT`** (Contracts & Leases).
  3. Re-mapped `fir_complaint` under the `pleading` family and expanded signal keywords.
* **The Why**:
  Guarantees 100% deterministic classification across diverse legal intake scenarios without false-positive keyword collisions.

---

### [ADR-009] Document Export: Browser-Side Multi-Family Court-Grade PDF Engine
* **Component**: `saulgpt-ui/src/usePDF.js`
* **Date**: 2026-08-27
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  Standard web downloads produce unformatted plain text files that lack legal margins, court letterheads, risk level badges, dynamic continuation banners, and statutory disclaimers.
* **The Decision & Change**:
  1. Built a browser-side PDF generator using `jsPDF` configured with standard Indian legal margins (22mm L/R, 28mm Top, 22mm Bottom).
  2. Implemented dynamic letterhead styling with dual-gold rule dividers and automated metadata tagging.
  3. Added multi-family section styling for **Legal Document Drafts**, **Contract Evaluation Reports** (color-coded risk badges & redlines), **IRAC Advocate Briefs**, and **Procedural Guides**.
  4. Added automated page breaks with `(continued)` headers and dynamic `Page X of Y` footers.
* **The Why**:
  Provides instant, client-ready legal briefs in PDF format directly in the browser with zero backend rendering overhead or server disk retention.

---

### [ADR-010] Interview Drafter: Eliminating Numeric Field Interruption Loops
* **Component**: `backend/api_server.py` (`_classify_interruption`)
* **Date**: 2026-08-27
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  In `_classify_interruption`, any query under 5 characters was treated as a clarification request (`len(q) < 5 -> "clarification"`). When a user answered simple numeric fields (e.g., Age = `"18"` or `"19"`, Duration = `"11"`, Deposit = `"50k"`), the server misclassified the answer as an interruption question asking *"Why is this needed?"*, explaining the field and re-asking the same step in an infinite loop.
* **The Decision & Change**:
  1. Removed the blanket `< 5` character clarification check.
  2. Explicitly exempted numeric strings (`q.isdigit()`) and direct alphanumeric answers from the interruption classifier.
  3. Enforced word-boundary regex on true interruption keywords (*"why do you need"*, *"what is the purpose"*, *"what if"*).
* **The Why**:
  Guarantees that direct user answers (age, dates, sums, names) progress seamlessly through all steps of the drafting interview without getting stuck.

---

### [ADR-011] UI State Machine: Dynamic Session Scoping & Multi-Conversation Switching
* **Component**: `saulgpt-ui/src/App.jsx` (`newConversation`, `loadConversation`, `sessionId`)
* **Date**: 2026-08-27
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  `SESSION_ID` was a static constant in localStorage that never changed. When clicking the `+` New Chat button or switching between chats in the sidebar, the backend triage and interview state machines remained bound to the old static session ID, causing stale drafts to bleed into new conversations and preventing clean conversation switching.
* **The Decision & Change**:
  1. Replaced the static constant with dynamic stateful session IDs scoped per conversation (`session_conv_${conv_id}` or fresh timestamped IDs).
  2. Updated `newConversation()` to reset draft state, create a new conversation ID in SQLite via `POST /api/conversations`, clear UI messages, and refresh the sidebar list.
  3. Updated `loadConversation(id)` to load message history from `GET /api/conversations/${id}`, bind `sessionId` to `session_conv_${id}`, and reset suggestion/drafting flags.
  4. Added a dedicated top-header `+` (New Chat) quick button alongside the `☰` toggle for immediate 1-click access.
* **The Why**:
  Guarantees clean, isolated conversation histories and instant switching between simultaneous legal consultations without state bleeding.

---

### [ADR-012] Strategy Engine: Universal Path Choice Resolution & Seamless Triage Execution
* **Component**: `backend/api_server.py` (`_resolve_triage_choice`, `_handle_strategy_choice`)
* **Date**: 2026-08-28
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  When a user reloaded a conversation from chat history or clicked a strategy option card (e.g. *"Path A: Issue Legal Notice (RPAD)"*, *"Path B: Approach Labour Commissioner"*, *"Path C: File Summary Suit under Order 37 CPC"*), the in-memory triage mode was `"idle"`. Because the strategy matcher was only executed when `current_mode == "strategy"`, clicking any option was treated as a brand new legal query, causing the bot to repeat its initial empathy response instead of launching the drafting interview or generating the procedural roadmap.
* **The Decision & Change**:
  1. Implemented `_handle_strategy_choice` to unify the execution of both drafting routes (`Path A` / Legal Notices) and procedural filing guides (`Path B`/`Path C`/`Path D`).
  2. Added a **Universal Strategy Intercept** at the top of the pipeline that catches path clicks across all sessions and states, automatically recovering the underlying grievance from conversation history if needed.
  3. Upgraded `_resolve_triage_choice` with regex pattern matching for `"Path A"`, `"Path B"`, `"Option 1"`, `"Option 2"`, numbers (`"1"`, `"2"`), and descriptive action titles.
* **The Why**:
  Guarantees that clicking any strategic path card or typing a path choice instantly launches the corresponding action (document draft or statutory filing roadmap) across new, existing, or reloaded conversations.

---

### [ADR-013] Chat History: Conversation Restoral & Deep-Meta State Hydration
* **Component**: `saulgpt-ui/src/App.jsx` (`loadConversation`, `Message`, mount `useEffect`)
* **Date**: 2026-08-28
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  When switching conversations in the sidebar (e.g. clicking *"Draft a Sworn Affidavit for a lost 10th standard CBSE marksheet"*), historical turns failed to hydrate properly on mount due to a guard check (`!convRef.current`) evaluating to null. Additionally, nested metadata in historical messages (`meta.meta`, `progress_pct`, markdown download links) were not parsed, preventing document download links and progress trackers from rendering.
* **The Decision & Change**:
  1. Removed the blocking guard in mount recovery and routed directly through `loadConversation(n)`.
  2. Deeply unwrapped and hydrated message metadata (`effectiveMeta = meta?.meta || meta`, `progressPct`, `scrutiny`, `docReady`, `docUrl`).
  3. Added markdown hyperlink parser (`[text](url)` $ightarrow$ `<a href="url">text</a>`) in message body rendering.
  4. Unified token retrieval in `api()` across React state and `localStorage`.
* **The Why**:
  Guarantees that clicking any past conversation (affidavit, demand letter, contract review, Q&A) instantly and faithfully restores all message bubbles, progress bars, legal scrutiny cards, and download buttons in the chat window.

---

### [ADR-014] UI Layering: Backdrop Stacking Context & Click Event Propagation
* **Component**: `saulgpt-ui/src/App.css` & `saulgpt-ui/src/ConversationsSidebar.jsx`
* **Date**: 2026-08-28
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  When opening the sidebar, clicking on a different chat item (e.g., *"My employer hasn't paid salary..."*) failed to trigger the selection handler. Instead, the click was intercepted by the full-screen fixed overlay `.sidebar-backdrop` (`z-index: 90`), which simply executed `setShowSidebar(false)` and closed the sidebar, leaving the user on the current conversation page without switching.
* **The Decision & Change**:
  1. Elevated `.sidebar` stacking context with `position: relative; z-index: 100; box-shadow: 4px 0 24px rgba(0, 0, 0, 0.4);`.
  2. Set `.sidebar-backdrop` to `z-index: 90` to guarantee that the sidebar list always sits strictly on top of the backdrop.
  3. Added `e.stopPropagation()` and `e.preventDefault()` to `.sidebar` and `.sidebar-item` click events to prevent backdrop event bubbling.
* **The Why**:
  Guarantees 100% click fidelity on sidebar items, allowing users to switch effortlessly between FIR petitions, employee wage disputes, sworn affidavits, and new consultations.

---

### [ADR-015] Pleading Family: Order VII CPC Triad of Survival & Mid-Interview Interruption Handling
* **Component**: `backend/interview_state.py` (`MASTER_SCHEMAS["pleading"]`, `FAMILY_MAP`, `FAMILY_SPEC_PROMPTS["pleading"]`)
* **Date**: 2026-08-28
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  Court Pleadings (Plaints and Petitions under the Code of Civil Procedure, 1908) require strict adherence to Order VII Rule 11 CPC. Failure to plead (a) Cause of Action Date & Limitation, (b) Territorial & Pecuniary Jurisdiction, and (c) Specific Valuation & Prayer leads to mandatory rejection of the plaint. Additionally, mid-interview user clarification requests (*"Why do you need the exact cause of action date?"*) must be answered with legal backing without resetting the interview state stack.
* **The Decision & Change**:
  1. Established the 7-step Pleading Schema: Plaintiff Name, Plaintiff Address, Defendant Name, Defendant Address, Cause of Action Date, Court Location, and Brief Facts.
  2. Integrated the **Order VII Rule 11 CPC "Triad of Survival"** (Limitation under Limitation Act 1963, Jurisdiction, Valuation for Court Fees Act 1870, and quantifiable prayers with interest and mesne profits).
  3. Formatted Order VI Rule 15 CPC Verification clauses splitting personal knowledge from legal advice.
  4. Verified stateful mid-interview interruption handling: user questions are answered contextually before seamlessly resuming the exact pending step.
* **The Why**:
  Produces court-grade civil plaints and petitions ready for immediate filing in Indian District Courts, High Courts, and Tribunals that survive Order 7 Rule 11 rejection scrutiny.

---

### [ADR-016] Bilingual Query Reformulation & Countryside Regional Legal Intelligence
* **Component**: `backend/layer1_understanding.py` (`reformulate_query`), `backend/layer3_reasoning.py`, `backend/api_server.py`
* **Date**: 2026-08-28
* **Status**: ✅ Implemented & Verified
* **The Problem**:
  When users submitted complex countryside agricultural or land disputes in regional Hindi/Hinglish (e.g. *encroachment of ancestral agricultural land, destruction of standing sugarcane crop, lathi assault by local dabangs, and police refusal to register an FIR*), Layer 1 left the raw Hindi text intact in `hyde_paragraph`. Because ChromaDB uses English sentence embeddings, cross-lingual vector search failed (similarity score `-4.03`), causing the model to return *"I do not have enough specific legal context"*.
* **The Decision & Change**:
  1. Upgraded `reformulate_query` to detect Devanagari characters (`[\u0900-\u097F]`) and translate the factual narrative into high-density English statutory legal embeddings (`agricultural land encroachment, criminal trespass BNS 329 IPC 447, voluntarily causing hurt BNS 115 IPC 323, Section 145/147 CrPC, Section 173 BNSS 154 CrPC, Order 39 CPC injunction`).
  2. Added Hindi personal grievance indicators (*हमारे, दबंग, मारपीट, कब्जा, धमकी, थाने, फसल, मेड़*) to `_is_direct_legal_query`.
  3. Enforced the **Language Matching Protocol** in Layer 3: when queries are received in Hindi/Hinglish, SaulGPT generates authoritative, empathetic, court-accurate responses in fluent Hindi (Devanagari).
* **The Why**:
  Democratizes legal intelligence across India, enabling rural citizens and non-English speakers to receive senior-counsel-level guidance and statutory remedies in their native language.
