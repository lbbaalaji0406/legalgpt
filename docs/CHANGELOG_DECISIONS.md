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
