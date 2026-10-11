# 🚀 SaulGPT Full-Stack Cloud Deployment Guide

This guide walks you through deploying **SaulGPT** so you can share a live 24/7 web link (`https://<project-id>.web.app`) with mentors and evaluators.

---

## 🏛️ Deployment Architecture

SaulGPT is a dual-tier full-stack system:
- **Frontend**: React 18 + Vite SPA (`saulgpt-ui/` built into `dist/`) $\rightarrow$ Hosted on **Firebase Hosting** (Google CDN, SSL, custom domain).
- **Backend**: Python 3.11 FastAPI (`backend/api_server.py`) $\rightarrow$ Hosted on **Render.com** (easiest 1-click via GitHub) or **Google Cloud Run** (Docker serverless).

---

## ⚡ Step 1: Deploy Backend to Cloud (Render)

Render connects directly to your GitHub repository [`lbbaalaji0406/legalgpt`](https://github.com/lbbaalaji0406/legalgpt) and deploys the Python FastAPI server for free:

1. Go to [dashboard.render.com](https://dashboard.render.com/) and sign in with GitHub.
2. Click **New +** $\rightarrow$ **Blueprint** (or **Web Service**).
3. Select your repository: `lbbaalaji0406/legalgpt`.
   - *If using Blueprint:* Render automatically detects `render.yaml` and configures everything.
   - *If using Web Service manually:*
     - **Name:** `saulgpt-backend`
     - **Region:** Singapore / Frankfurt / Oregon
     - **Branch:** `master`
     - **Root Directory:** *(leave blank)*
     - **Runtime:** `Python`
     - **Build Command:** `pip install -r backend/requirements.txt`
     - **Start Command:** `cd backend && uvicorn api_server:app --host 0.0.0.0 --port $PORT`
4. Add **Environment Variables**:
   - `GROQ_API_KEY`: *(paste your Groq API key from `.env`)*
   - `PYTHON_VERSION`: `3.11.9`
5. Click **Create Web Service**.
6. Once deployed, copy your live backend URL (e.g., `https://saulgpt-backend.onrender.com`).

---

## 🌐 Step 2: Configure Frontend for Live Backend

1. In `saulgpt-ui/`, create or edit `.env.production`:
   ```bash
   VITE_API_BASE=https://saulgpt-backend.onrender.com
   ```
   *(Replace with your actual Render backend URL)*

2. Test the build locally:
   ```bash
   cd saulgpt-ui
   npm.cmd run build
   ```
   *(This bakes your live backend URL into the production bundle in `dist/`)*

---

## 🔥 Step 3: Deploy Frontend to Firebase Hosting

### Option A: One-Click Script (Recommended)
Double-click **`Deploy_Frontend.bat`** in the project root! It will:
1. Rebuild the latest frontend into `dist/`.
2. Authenticate your Firebase Google account via your browser.
3. Deploy the site live to Firebase CDN.

### Option B: Command Line (Manual)
1. In the project root, log in to Firebase:
   ```powershell
   npx.cmd --yes firebase-tools login
   ```
2. If this is your first time deploying to Firebase:
   - Create a project on the [Firebase Console](https://console.firebase.google.com/) (e.g., `saulgpt-demo`).
   - Connect your project in your terminal:
     ```powershell
     npx.cmd --yes firebase-tools use --add
     ```
     *(Select your project from the list and give it an alias like `default`)*
3. Deploy to live hosting:
   ```powershell
   npx.cmd --yes firebase-tools deploy --only hosting
   ```

---

## 🎯 Verification & Mentor Hand-off
Once deployed, Firebase will print your live public URL:
```text
✔  Deploy complete!

Project Console: https://console.firebase.google.com/project/saulgpt-demo/overview
Hosting URL: https://saulgpt-demo.web.app
```

You can now share **`https://saulgpt-demo.web.app`** with your mentors! They will be able to:
1. Conduct legal queries, IRAC analyses, and BNS-BNSS-BSA statutory queries.
2. Enter the **Pre-Trial Studio & Moot Court Arena** with hostile Sec 146 BSA cross-examinations and real-time Corner Coach intercepts.
3. Ground multimodal evidence (cheques, audio confessions) under Section 63 BSA.
4. Export court-grade Order VII CPC plaints, legal notices, and formatted PDFs.
