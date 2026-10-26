---
title: SaulGPT Legal Intelligence API
emoji: ⚖️
colorFrom: yellow
colorTo: indigo
sdk: gradio
sdk_version: 5.20.0
app_file: app.py
pinned: false
license: mit
---

# ⚖️ SaulGPT — Autonomous Indian Legal Intelligence & GraphRAG Platform

> **A Neuro-Symbolic Legal Intelligence Platform for Indian Jurisprudence.**  
> Powered by a **6-Layer Deterministic RAG Pipeline**, a native **PyTorch Relational Graph Neural Network (GNN)**, a **Self-Learning Continuous Vector Store**, and an **Interactive Virtual Counsel Workflow (Discovery → Strategy → Court-Ready Drafting → 120B Advocate Courtroom Rehearsal)**.

---

## 🌟 Key Architectural Innovations

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CORE SYSTEM CAPABILITIES                        │
├────────────────────────────────────────────────────────────────────────┤
│ 1. 🕸️ Relational GNN GraphRAG (PyTorch TransE/RotatE Pathway Discovery) │
│ 2. 🔄 Self-Learning ChromaDB & Dynamic Auto-Triplification (ADR-020)   │
│ 3. 🇮🇳 2024 Criminal Law Transition Engine (BNS / BNSS / BSA 2023)       │
│ 4. 🛡️ Constitutional Struck-Down Firewall (Landmark SC Rulings)       │
│ 5. 🌾 Cross-Lingual Devanagari Hindi HyDE (Rural Legal Intelligence)   │
│ 6. 📄 Court-Grade Document Factory (Order VII CPC Plaints & PDFs)      │
│ 7. 👑 Pre-Trial Studio & Moot Court Arena (Sec 146 BSA Interrogation)  │
│ 8. 🛡️ Sec 63 BSA Multimodal Evidence Grounding (Audio & Cheques)       │
│ 9. 🧠 Precedent Intelligence Engine (50,000+ Landmark Case Index)     │
│ 10. 💾 Universal Multi-Session SQLite Persistence (WAL Mode)           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ System Architecture

SaulGPT operates on a **Two-Tier Neuro-Symbolic Architecture**:
1. **The Multi-Agent Workflow Layer (UX & Client Lifecycle):** TriageAgent $
ightarrow$ DiscoveryAgent $
ightarrow$ StrategyAgent $
ightarrow$ InteractiveDrafter $
ightarrow$ AdvocateCourtroomSimulator.
2. **The 6-Layer Deterministic Substantive Legal Engine:**

```
                                [USER GRIEVANCE / QUERY]
                                           │
         ┌─────────────────────────────────┴─────────────────────────────────┐
         ▼                                                                   ▼
[LAYER 1: Query Understanding]                                  [LAYER 2: Hybrid Retrieval]
• Devanagari Hindi HyDE Translation                             • Dense ChromaDB (2,449+ chunks)
• Citation Regex & NER Extraction                               • Sparse BM25 + Cross-Encoder Reranking
         │                                                                   │
         └─────────────────────────────────┬─────────────────────────────────┘
                                           │
                                           ▼
                           [LAYER 6: Relational GNN Engine]
                           • 73 Canonical Relations | 268 Graph Nodes | 172 Triples
                           • PyTorch TransE/RotatE Continuous Vector Embeddings
                           • Discovers Parallel Judicial Pathways (SDM vs Magistrate vs Civil)
                                           │
                                           ▼
                           [LAYER 3: Big Model Reasoning]
                           • 120B Senior-Counsel Synthesis & Strategic Roadmap
                                           │
                                           ▼
                           [LAYER 4: Validation & Firewall]
                           • NLI DeBERTa Faithfulness Entailment Check
                           • Deterministic 2024 Transition (IPC➔BNS, CrPC➔BNSS, IEA➔BSA)
                           • Supreme Court Struck-Down Guardrail (S.66A, S.497, S.377)
                                           │
                                           ▼
                           [LAYER 5: External Search & Auto-Ingest]
                           • Live Web Search Fallback + Dynamic Triplifier
                           • Automatic Real-Time Ingestion into ChromaDB & GNN
```

---

## 🚀 Key Features

### 1. 🕸️ Relational GNN & Multi-Hop Pathway Discovery (Layer 6)
* **Energy-Scoring Knowledge Embeddings:** Trained with MarginRankingLoss in PyTorch ($\mathbb{R}^{64}$ vector space).
* **Multi-Court Parallel Traversal:** Unlike flat vector search with single-statute tunnel vision, the GNN maps complex grievances across multiple courts simultaneously (*SDM Revenue Restitution $
ightarrow$ Criminal Magistrate FIR Escalation $
ightarrow$ Civil Court Stay Injunction Triad*).

### 2. 🔄 Dynamic Self-Learning ChromaDB & Auto-Triplification
* **Continuous Ingestion:** Novel statutory rules and circulars fetched from the web are dynamically embedded and permanently saved into ChromaDB (`saulgpt_indian_laws`).
* **Auto-Triplifier:** Automatically extracts structured $(h, r, t)$ triples from novel legal texts, normalizes them against our 73 canonical relations, and updates the GNN in real time with zero duplicates.

### 3. 🇮🇳 2024 Criminal Law Overhaul & Constitutional Guardrails
* **100% Active Law Mapping:** Translates legacy citations to active codes (*IPC 302 ➔ BNS 103*, *CrPC 154 ➔ BNSS 173*, *IEA 65B ➔ BSA 63*).
* **Struck-Down Protection:** Intercepts unconstitutional citations (*Shreya Singhal 2015* for Section 66A IT Act, *Joseph Shine 2018* for Adultery Section 497, *Puttaswamy 2018* for Section 57 Aadhaar Act) and provides immediate quashing guidance under Article 226 / Section 528 BNSS.

### 4. 🌾 Regional & Vernacular Intelligence (Devanagari Hindi)
* **Cross-Lingual HyDE Embeddings:** Translates colloquial countryside Hindi grievances (*dabang, zameen kabza, khadi fasal, thana*) into high-density English statutory vectors, providing equal legal access to rural litigants.
* **Native Hindi Language Matching:** Answers fluently in Devanagari Hindi when queried in Hindi/Hinglish.

### 5. 📄 Court-Grade Document Factory & Browser PDF Generator
* **Order VII Rule 11 CPC Triad of Survival:** Enforces strict compliance with Limitation, Territorial/Pecuniary Jurisdiction, Valuation (Court Fees Act 1870), and Order VI Rule 15 Verification clauses to prevent plaint rejection.
* **Instant Client-Ready PDFs:** Generates beautifully styled court documents, affidavits, demand letters, and contract risk audits directly in the browser via `jsPDF` with dual-gold letterheads.

### 6. ⚖️ 120B Adversarial Courtroom Simulator (Advocate Mode)
* **IRAC Briefing:** Synthesizes structured *FACTS / ISSUES / RULES / APPLICATION / CONCLUSION* analyses.
* **Adversarial Rehearsal:** Generates fierce Petitioner Arguments vs. Anticipated Respondent Counter-Defenses with probability-of-success scores.

### 7. 👑 Pre-Trial Studio & Moot Court Arena
* **Adverse Cross-Examiner (Sec 146 BSA):** Aggressive, hostile interrogation targeting documentary lacunae, tax filing contradictions, and uncorroborated oral claims across civil and criminal domains.
* **Corner Coach Intercept & Tactical Counsel:** Real-time confidential attorney-client auditing with live exposure tracking, formal procedural objections, safe verbatim witness rejoinders, and tangible evidentiary plugs.
* **Precedent Intelligence Engine:** Grounded in a comprehensive index of **50,000+ Supreme Court & High Court judgments** across 8 core statutory frameworks (BNS, BNSS, BSA, NI Act, CPA 2019, Contract Act, Limitation Act, Arbitration Act) with universal fallback detection.
* **Two-Column Split Chamber:** Seamless separation between the formal Courtroom Chamber (dialogue & witness stand) and the confidential Corner Coach Console.

### 8. 🛡️ Section 63 BSA Multimodal Evidence Grounding
* **Cryptographic BSA Certificates:** Generates tamper-proof Section 63 BSA Digital Evidence Certificates with SHA-256 hash chaining (client + server).
* **Cheque OCR & 30-Day Statutory Clock:** Extracts bank return memos, dishonour codes, drawer/payee entities, and calculates statutory legal notice windows.
* **Voice Admission & Limitation Extender:** Performs audio transcription and semantic analysis of debtor admissions to trigger limitation extensions under Section 18 of the Limitation Act, 1963.
* **1-Click Pre-Trial Integration:** Instantly loads grounded evidence into the Moot Court Arena for live adversarial testing.

---

## ⚡ Quick Start

### 1. One-Click Launch (Windows)
Double-click `start.vbs` — it automatically launches the FastAPI backend, the React frontend, and opens your default browser!

### 2. Manual Startup
```bash
# Terminal 1 — Backend API Server
cd backend
..\.venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000

# Terminal 2 — React UI
cd saulgpt-ui
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite 5, jsPDF (A4 Court Vector Engine), Lucide Icons, Glassmorphism CSS |
| **Cloud Hosting** | **Hugging Face Spaces ZeroGPU** (`zero-a10g`) + **Firebase Hosting** (Google Global CDN) |
| **Backend API** | Python 3.10/3.11, FastAPI, Gradio 5.20 ASGI Server, Uvicorn, python-docx |
| **Reasoning & Reward** | Groq (`qwen/qwen3.8-27b`, `openai/gpt-oss-120b`), Actor-Critic FG-PRM (`max_tokens=800`) |
| **GNN & ML** | PyTorch (TransE & RotatE embeddings, MarginRankingLoss, AdamW), NetworkX |
| **Vector DB** | ChromaDB (Dense Cosine Similarity + HNSW Index, 2,449+ Chunks, CPU-pinned) |
| **Retrieval & Rerank** | `sentence-transformers/all-MiniLM-L6-v2`, BM25 Okapi, `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **Validation & NLI** | DeBERTa-v3 NLI Cross-Encoder, SC Struck-Down Firewall, 2024 Transition Concordance |
| **Database & Persistence** | **Supabase Managed PostgreSQL** (IPv4 Session Pooler :5432) + Local SQLite Fallback |

---

## 📚 Architectural Decisions & Research Documentation

SaulGPT maintains exhaustive, production-grade technical and functional documentation:

| Document | Description |
| :--- | :--- |
| [ARCH.md](ARCH.md) | **Quick-Reference Cloud Topology & Architecture Map** |
| [docs/FDD.md](docs/FDD.md) | **Functional Design Document (FDD)**: User personas, workflows, 4 document families, guardrails |
| [docs/TDD.md](docs/TDD.md) | **Technical Design Document (TDD)**: Cloud topology, 6-layer RAG, DDL schemas, BYOK security |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Comprehensive system architecture, data flows, and layer specifications |
| [docs/CHANGELOG_DECISIONS.md](docs/CHANGELOG_DECISIONS.md) | **All 30 Architectural Decision Records (ADRs: ADR-001 through ADR-030)** |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | Complete REST API reference, endpoints, schemas, and payloads |
| [docs/FEATURES.md](docs/FEATURES.md) | Complete feature breakdown across all 10 core system modules |
| [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | Local and cloud environment setup, configuration, and testing |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Production cloud deployment guide (Hugging Face Spaces + Supabase + Firebase) |

---

## 📄 License & Disclaimer

* **Disclaimer:** SaulGPT provides AI-assisted legal intelligence, procedural routing, and document drafting based on Indian statutes. It is designed to assist citizens and advocates and does not constitute formal attorney-client representation.
* **License:** MIT License.
