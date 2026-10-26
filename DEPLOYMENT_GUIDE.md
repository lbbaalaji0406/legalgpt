# 🚀 SaulGPT Full-Stack Production Cloud Deployment Guide

**Document Version:** 2.2.0  
**Target Release:** Production Cloud (Hugging Face Spaces ZeroGPU + Supabase PostgreSQL + Firebase Hosting)  

This guide provides end-to-end instructions for deploying **SaulGPT** to production so users and evaluators can access a live 24/7 web application (`https://legalgpt-india.web.app`) backed by high-performance cloud infrastructure.

---

## 🏛️ 1. Production Architecture Overview

SaulGPT is deployed across three best-in-class cloud environments:

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React 18 + Vite)                │
│  Hosted at: https://legalgpt-india.web.app (Firebase)        │
│  CDN: Google Global Edge CDN, Automatic SSL, Zero Maintenance│
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS REST (Port 443)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│         Backend API (Hugging Face Spaces - ZeroGPU)          │
│  Hosted at: https://lvvbaaal-legalgpt-api.hf.space          │
│  Hardware: zero-a10g (16GB VRAM, Dynamic GPU Allocation)     │
│  Server: FastAPI inside Gradio 5.20 ASGI Server (Port 7860)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ IPv4 Connection Pooler (Port 5432)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Supabase Managed PostgreSQL                    │
│  Host: aws-0-ap-southeast-1.pooler.supabase.com             │
│  Persistence: Users, Multi-Turn Conversations, Messages      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ 2. Step 1: Database Setup (Supabase Managed PostgreSQL)

To enable multi-device sync and prevent SQLite file lock concurrency issues in cloud containers, SaulGPT uses **Supabase Managed PostgreSQL** via its **IPv4 Connection Pooler**.

### 2.1 Obtain Connection String
1. Go to your [Supabase Dashboard](https://supabase.com/dashboard) and select your project.
2. Navigate to **Project Settings** $\rightarrow$ **Database** $\rightarrow$ **Connection Pooling**.
3. Select **Session Mode** (Port `5432`) or **Transaction Mode** (Port `6543`).
4. Ensure you use the **IPv4 Pooler hostname**:
   ```
   aws-0-ap-southeast-1.pooler.supabase.com
   ```
5. Your connection URI format:
   ```
   postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
   ```
   *(Note: URL-encode any special characters in your password, e.g. `@` as `%40`)*

### 2.2 Schema Initialization
SaulGPT automatically creates the required tables (`users`, `conversations`, `messages`) and indexes upon server startup via `backend/database.py`. You do not need to run manual SQL migrations.

---

## ⚡ 3. Step 2: Deploy Backend to Hugging Face Spaces (ZeroGPU)

The backend runs on Hugging Face Spaces configured with a **ZeroGPU** (`zero-a10g`) accelerator, providing 16 GB VRAM on-demand while running CPU-pinned tasks at zero idle cost.

### 3.1 Create Space
1. Log in to [Hugging Face](https://huggingface.co).
2. Click **New Space**:
   - **Space Name:** `legalgpt-api` (e.g., `Lvvbaaal/legalgpt-api`)
   - **SDK:** `Gradio` (SDK version `5.20.0`)
   - **Hardware:** `ZeroGPU` (Free Tier: `zero-a10g`, 16 GB VRAM)
   - **Visibility:** `Public`

### 3.2 Configure Environment Secrets
In your Space settings (**Settings** $\rightarrow$ **Variables and secrets**), add the following:

| Secret Name | Value | Purpose |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | `gsk_...` | Groq API key for Llama 3.1 8B, Qwen 2.5, GPT-OSS 120B |
| `DATABASE_URL` | `postgresql://postgres...` | Supabase IPv4 Pooler connection string |
| `JWT_SECRET` | `your-secure-jwt-secret-key` | Secret key for signing user authentication tokens |
| `PUBLIC_API_URL` | `https://<user>-<space-name>.hf.space` | Public base URL used for `.docx` download link rewriting |

### 3.3 Deploy Using `deploy_hf.py` (Automated)
We provide an automated synchronization script [`deploy_hf.py`](file:///c:/Users/lbbaa/OneDrive/Desktop/legalgpt-master/deploy_hf.py) that stages required backend files, assets, and data files, and pushes them to your Space:

```powershell
.venv\Scripts\python.exe deploy_hf.py
```

The script:
1. Validates `README.md` metadata frontmatter (`sdk: gradio`, `sdk_version: 5.20.0`, `app_file: app.py`).
2. Syncs `backend/`, `data/`, `app.py`, and `requirements.txt`.
3. Pushes directly to the Hugging Face Space remote repository.
4. Hugging Face automatically builds the container and launches FastAPI on port 7860.

### 3.4 Verification
Once deployed and the Space status shows **`RUNNING`**, verify the health endpoint:
```bash
curl https://<user>-legalgpt-api.hf.space/api/health
# Response: {"status":"healthy","database":"connected","version":"2.2.0"}
```

---

## 🌐 4. Step 3: Deploy Frontend to Firebase Hosting

The React SPA is hosted on **Firebase Hosting** for low latency and zero downtime.

### 4.1 Set Production API Endpoint
Edit `saulgpt-ui/.env.production` to point to your live Hugging Face Space backend:
```bash
VITE_API_BASE=https://lvvbaaal-legalgpt-api.hf.space
```

### 4.2 Build Production Bundle
```powershell
cd saulgpt-ui
npm.cmd run build
cd ..
```
This generates the optimized production build in `saulgpt-ui/dist/`.

### 4.3 Deploy via Firebase CLI
Deploy the static assets directly to Firebase CDN:
```powershell
npx.cmd --yes firebase-tools deploy --only hosting
```

Your live frontend URL will be printed:
```
✔  Deploy complete!
Hosting URL: https://legalgpt-india.web.app
```

---

## 🎯 5. End-to-End Verification Checklist

Verify all major platform features on your production deployment:

1. **Omni-Box Legal Q&A:**
   - Query: *"What is Section 138 of Negotiable Instruments Act?"*
   - Verify: Detailed statutory analysis, citations, and BNS/BNSS cross-references rendered.
2. **Virtual Counsel Grievance Workflow:**
   - Query: *"My landlord locked me out and kept my deposit."*
   - Verify: 3-phase empathetic discovery triggers $\rightarrow$ SWOT analysis $\rightarrow$ 4 actionable strategy paths.
3. **Court-Grade Document Drafter (.docx):**
   - Query: *"Draft a cheque bounce notice for 50000 rupees against ABC Pvt Ltd."*
   - Verify: Interview questionnaire completes $\rightarrow$ Scrutiny validation passes $\rightarrow$ Word doc download button appears.
   - Click **Download Your Document**:
     - Verify: Browser downloads `legal_document_<session_id>.docx`.
     - Open document: Verify 0% prompt leakage (no `[User Goal: document]`), formal RPAD header, Section 138 NIA citation, statutory 15-day demand clause, and advocate signature block.
4. **Pre-Trial Studio & Moot Court Arena:**
   - Open Pre-Trial Studio tab $\rightarrow$ Input case summary.
   - Verify: Hostile Section 146 BSA cross-examination in Courtroom Chamber; real-time procedural objections and tactical advice in Corner Coach Console.
5. **Section 63 BSA Evidence Certification:**
   - Upload sample cheque image or audio recording.
   - Verify: Client-side + server-side SHA-256 hash chaining and court-admissible Section 63 BSA certificate generation.
6. **Supabase Cloud Persistence:**
   - Sign up or log in $\rightarrow$ Send a message $\rightarrow$ Refresh page or open from another browser.
   - Verify: Chat history, conversations list, and message turns persist seamlessly.

---

## 🔄 6. Alternative Hosting Options

### Option A: Render.com (Container Web Service)
If you prefer Render:
1. Connect GitHub repo `lbbaalaji0406/legalgpt`.
2. Select **Web Service**, Python 3.11 runtime.
3. Build command: `pip install -r backend/requirements.txt`
4. Start command: `cd backend && uvicorn api_server:app --host 0.0.0.0 --port $PORT`
5. Set `GROQ_API_KEY`, `DATABASE_URL`, `JWT_SECRET`, and `PUBLIC_API_URL`.

### Option B: Google Cloud Run (Serverless Docker)
Build and deploy a container image using Google Cloud Build:
```bash
gcloud run deploy saulgpt-backend --source . --platform managed --region asia-south1 --allow-unauthenticated
```
