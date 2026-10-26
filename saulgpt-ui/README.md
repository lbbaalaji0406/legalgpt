# ⚖️ SaulGPT Web Client (saulgpt-ui)

**Document Version:** 2.2.0  
**Stack:** React 18, Vite 5, Axios, jsPDF, Lucide Icons  
**Hosting:** Firebase Hosting ([https://legalgpt-india.web.app](https://legalgpt-india.web.app))  

The frontend of **SaulGPT** is an institutional-grade, dark-courtroom-themed Single Page Application (SPA) engineered for high accessibility, low latency, and intuitive interaction with Indian legal workflows.

---

## 🏛️ Component Architecture

```
saulgpt-ui/src/
├── App.jsx                 # Omni-Box chat interface, turn loop, and session coordinator
├── AuthPage.jsx            # JWT Login & Signup with seamless guest session migration
├── ConversationsSidebar.jsx# Multi-session cloud history with Supabase sync
├── TrialStudio.jsx         # Pre-Trial Moot Court Arena (Courtroom Chamber & Corner Coach)
├── EvidenceUploader.jsx    # Section 63 BSA drag-and-drop evidence ingestion & hash verification
├── TriageCards.jsx         # Phase 2 Virtual Counsel SWOT matrix & strategic action paths
├── VetoCard.jsx            # Scrutiny blocker card (limitation warnings, legal defects)
├── BNSCorrectionNotice.jsx # 2024 Transition banner (IPC➔BNS, CrPC➔BNSS, IEA➔BSA)
├── JurisdictionBadge.jsx   # Court pecuniary & territorial jurisdiction indicator
├── UrgencyBanner.jsx       # Statutory limitation countdown alerts
├── ApiKeyModal.jsx         # Bring-Your-Own-Key (BYOK) Groq key management modal
├── LegalGlossary.js        # Comprehensive dictionary of 200+ Indian legal terms
├── usePDF.js               # Client-side jsPDF A4 court vector styling engine
├── App.css                 # Primary courtroom styling & glassmorphism theme
├── TrialStudio.css         # Split-chamber layout & badge animations
└── EvidenceUploader.css    # Hash verification & evidence badge styles
```

---

## ⚙️ Configuration & Environment

The application dynamically detects its API target:
- **Local Development:** Proxies requests to `http://localhost:8000`
- **Production Cloud:** Points to the live Hugging Face ZeroGPU backend

Create or verify `.env.production`:
```ini
VITE_API_BASE=https://lvvbaaal-legalgpt-api.hf.space
```

The app automatically intercepts document downloads and rewrites any legacy `localhost:8000` URLs to `VITE_API_BASE` for zero-friction mobile and desktop downloads.

---

## 🚀 Development Scripts

```bash
# Install dependencies
npm install

# Start Vite dev server on http://localhost:5173
npm run dev

# Build optimized production bundle into dist/
npm run build

# Preview production build locally
npm run preview
```

---

## 🔥 Deploying to Firebase Hosting

To deploy the production build to Google Firebase CDN:

```bash
# 1. Build the frontend
npm run build

# 2. Deploy from root or saulgpt-ui
npx --yes firebase-tools deploy --only hosting
```

Your live web application will be accessible at:
👉 **`https://legalgpt-india.web.app`**
