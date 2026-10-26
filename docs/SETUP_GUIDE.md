# 💻 SaulGPT Local Development & Setup Guide

**Document Version:** 2.2.0  
**Target Release:** Production Cloud & Local Workstation  

This guide walks you through setting up, configuring, and testing the full **SaulGPT** stack on your local development machine.

---

## 📋 1. Prerequisites

Before starting, ensure you have the following installed on your machine:
- **Python:** 3.10 or 3.11 ([python.org](https://www.python.org/downloads/))
- **Node.js:** 18+ LTS ([nodejs.org](https://nodejs.org/))
- **Git:** Latest version
- **A Groq Cloud API Key:** Free tier from [console.groq.com](https://console.groq.com/)

---

## ⚡ 2. One-Click Quick Start (Windows)

For rapid local testing on Windows:

1. **One-Time Setup:**
   Double-click `scripts\setup.bat` — This will create the Python virtual environment (`.venv`), install all backend dependencies, download the spaCy English NLP model, and run `npm install` in `saulgpt-ui/`.

2. **Run the Application:**
   Double-click `start.vbs` — It silently launches:
   - Python FastAPI backend on `http://localhost:8000`
   - React + Vite development server on `http://localhost:5173`
   - Automatically opens your default web browser to the app.

---

## 🛠️ 3. Step-by-Step Manual Setup

### 3.1 Backend Configuration
```bash
# 1. Clone the repository
git clone https://github.com/lbbaalaji0406/legalgpt.git
cd legalgpt

# 2. Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt
pip install -r requirements.txt

# 4. Download spaCy English model
python -m spacy download en_core_web_sm
```

### 3.2 Environment Variables Configuration
Create a `.env` file in the project root:
```bash
copy .env.example .env
```

Populate the following variables:
```ini
# LLM Provider (Groq Cloud)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant

# Persistence Mode:
# Leave blank to use local SQLite (backend/saulgpt.db)
# OR provide a Supabase IPv4 Pooler connection string for cloud sync:
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres

# Security & Public URL
JWT_SECRET=development-secret-key-replace-in-production
PUBLIC_API_URL=http://localhost:8000
```

### 3.3 Vector Database Verification
Pre-embedded ChromaDB vector collections are included in `data/vector_db/` (~2,449 chunks across 9 acts and landmark precedents). If you need to rebuild the vector database from raw JSON sources:
```bash
cd backend
python 02_chunk_and_embed.py
cd ..
```

### 3.4 Frontend Setup
```bash
cd saulgpt-ui
npm install
cd ..
```

---

## 🏃 4. Running the Application

### Terminal 1: Backend API Server
```bash
cd backend
..\.venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```
The FastAPI documentation is available at: `http://localhost:8000/docs`

### Terminal 2: React Frontend UI
```bash
cd saulgpt-ui
npm run dev
```
The development UI is available at: `http://localhost:5173`

---

## 🧪 5. Testing & Evaluation

### 5.1 Automated RAG Pipeline Evaluation
Run the automated evaluation suite to benchmark retrieval accuracy, hallucination prevention, and keyword precision across 8 gold-standard test scenarios:
```bash
cd backend
..\.venv\Scripts\python.exe eval_pipeline.py
```

### 5.2 Isolated Agent Endpoint Testing
You can test specific subsystems directly using `curl` or Postman:

```bash
# 1. Health & Database Check
curl http://localhost:8000/api/health

# 2. Knowledge Retrieval (Layer 2 + Layer 3)
curl "http://localhost:8000/api/test/knowledge?q=What+is+Section+138+of+Negotiable+Instruments+Act"

# 3. Advocate Mode IRAC Analysis
curl "http://localhost:8000/api/test/analysis?q=Employer+withheld+three+months+salary+without+cause"

# 4. Procedural Pathfinder
curl "http://localhost:8000/api/test/pathfinder?q=How+do+I+file+an+e-FIR+for+cyber+theft"

# 5. Document Drafter Scrutiny Test
curl -X POST http://localhost:8000/api/test/scrutiny \
  -H "Content-Type: application/json" \
  -d '{"doc_type": "cheque_bounce", "date_of_default": "2024-05-10", "notice_date": "2024-05-20"}'
```

---

## 📂 6. Repository Layout & File Map

```
legalgpt-master/
├── ARCH.md                     # Quick-Reference Architecture & Topology Map
├── CLAUDE.md                   # Agent Memory, Conventions & Session Logs
├── DEPLOYMENT_GUIDE.md         # Production Cloud Deployment Guide
├── README.md                   # Project Overview & Hugging Face Frontmatter
├── app.py                      # ZeroGPU Gradio 5.20 + FastAPI Entrypoint
├── deploy_hf.py                # Automated Hugging Face Space Deployment Script
├── requirements.txt            # Root dependencies for Hugging Face container
│
├── backend/                    # Python Backend
│   ├── api_server.py           # Core FastAPI application & route dispatcher
│   ├── pipeline_orchestrator.py# 6-Layer Deterministic RAG controller
│   ├── actor_critic.py         # Actor-Critic Fine-Grained Process Reward Model
│   ├── interview_state.py      # Document drafting state machine & fallback spec
│   ├── document_generator.py   # 4-Family .docx generator (RPAD, Pleadings, Affidavits)
│   ├── evidence_processor.py   # Section 63 BSA Digital Certs & Forensic Processor
│   ├── layer1_understanding.py # Query understanding, Hindi HyDE, spaCy NER
│   ├── layer2_retrieval.py     # ChromaDB vector retrieval & Cross-Encoder (CPU)
│   ├── layer3_reasoning.py     # Groq LLM synthesis & IRAC reasoning
│   ├── layer4_validation.py    # DeBERTa NLI & SC Struck-Down Firewall
│   ├── layer5_external.py      # IndianKanoon / DuckDuckGo live search fallback
│   ├── layer6_evaluator.py     # 25,000-character contract risk evaluation
│   ├── layer6_knowledge_graph.py# Relational legal knowledge graph (NetworkX)
│   ├── database.py             # Dual Supabase PostgreSQL + SQLite CRUD engine
│   ├── auth.py                 # JWT token generation & bcrypt authentication
│   ├── discovery_agent.py      # Phase 1: 3-turn empathetic investigation
│   ├── strategy_agent.py       # Phase 2: SWOT matrix & 4-path generation
│   ├── irac_agent.py           # Advocate Mode IRAC structured brief generator
│   ├── scrutiny_agent.py       # Pre-draft limitation and validity scrutiny
│   ├── eval_pipeline.py        # Automated RAG benchmarking test harness
│   │
│   ├── trial_studio/           # Pre-Trial Studio & Moot Court Subsystem
│   │   ├── cross_examiner_agent.py   # Hostile Sec 146 BSA cross-examination
│   │   ├── defense_fortifier_agent.py# Corner Coach procedural objections
│   │   ├── precedent_engine.py       # 50,000+ SC/HC landmark judgments index
│   │   └── session_manager.py        # Moot session persistence
│   │
│   ├── agents/                 # Specialized Agent Definitions
│   │   ├── manager.py          # Sub-agent dispatch manager
│   │   ├── llm_client.py       # Centralized Groq LLM client factory
│   │   ├── triage.py           # Query classification
│   │   ├── researcher.py       # Knowledge retrieval agent
│   │   ├── drafter.py          # Document interview agent
│   │   └── reviewer.py         # Contract reviewer agent
│   │
│   └── prompts/                # LLM Prompt Templates
│       ├── triage.py
│       ├── discovery.py
│       ├── strategy.py
│       └── irac.py
│
├── saulgpt-ui/                 # React 18 + Vite Frontend
│   ├── src/
│   │   ├── App.jsx             # Main Omni-Box interface & state router
│   │   ├── AuthPage.jsx        # JWT Authentication & guest session takeover
│   │   ├── ConversationsSidebar.jsx # Cloud-persisted conversation history
│   │   ├── TrialStudio.jsx     # Split-Chamber Pre-Trial Moot Court Arena
│   │   ├── EvidenceUploader.jsx# Sec 63 BSA drag-and-drop evidence uploader
│   │   ├── TriageCards.jsx     # Phase 2 SWOT strategic path cards
│   │   ├── VetoCard.jsx        # Scrutiny blocker & limitation warning
│   │   ├── BNSCorrectionNotice.jsx # 2024 Transition notification badge
│   │   ├── JurisdictionBadge.jsx   # Court pecuniary & territorial indicator
│   │   ├── UrgencyBanner.jsx   # Statutory limitation countdown banner
│   │   ├── ApiKeyModal.jsx     # Bring-Your-Own-Key (BYOK) settings modal
│   │   ├── LegalGlossary.js    # 200+ Indian legal term dictionary
│   │   └── usePDF.js           # Client-side jsPDF vector rendering engine
│   ├── package.json
│   └── vite.config.js
│
├── docs/                       # Technical & Architectural Documentation
│   ├── ARCHITECTURE.md         # Comprehensive system architecture & data flows
│   ├── FDD.md                  # Functional Design Document
│   ├── TDD.md                  # Technical Design Document
│   ├── CHANGELOG_DECISIONS.md  # Architectural Decision Records (ADRs 001 - 030)
│   ├── FEATURES.md             # Complete 10-module feature breakdown
│   ├── API_REFERENCE.md        # REST API endpoints & schemas
│   └── SETUP_GUIDE.md          # This setup guide
│
├── data/
│   ├── raw_data/               # JSON statutory texts (BNS, BNSS, BSA, CPC, NIA, etc.)
│   └── vector_db/              # Pre-embedded ChromaDB vector indexes
│
└── scripts/
    ├── setup.bat               # Windows automated setup script
    └── start.bat               # Windows startup batch script
```
