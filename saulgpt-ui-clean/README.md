# SaulGPT — Clean UI

A second, simpler frontend for SaulGPT, in a clean three-pane "Antigravity" layout (light & dark).
It talks to the **same backend** with the **same API calls** as the classic UI in
[`../saulgpt-ui`](../saulgpt-ui). The classic UI is untouched — the two can run side by side.

| | Classic UI (`saulgpt-ui`) | Clean UI (`saulgpt-ui-clean`) |
|---|---|---|
| Dev URL | http://localhost:5173 | http://localhost:5174 |
| Build output | `../dist` | `../dist-clean` |
| Firebase config | `firebase.json` | `firebase.clean.json` |
| Deploy script | `Deploy_Frontend.bat` | `Deploy_Frontend_Clean.bat` |
| Styling | Hand-written CSS, mahogany & gold | Tailwind CSS, zinc + blue, light/dark toggle |

Both UIs use the same browser `localStorage` keys (`saulgpt_token`, `saulgpt_user_groq_key`,
`saulgpt_conv_id`, …). Note that browsers keep storage separate per origin, so port 5173 and port 5174
each have their own login. Your conversations live on the server, so you see the same history in both.

## Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⚖ SaulGPT          ● Connected  [☀ Light | ☾ Dark]  you   [Log Out]      │
├──────────────┬─────────────────────────────────────────┬─────────────────┤
│ + New Conv.  │ Conversation title          [READY]  ▣  │ Sources│Glossary│
│              │                                         │ │Guide          │
│ TOOLS        │   Welcome / messages                    │                 │
│  Legal Chat  │   • strategy option cards (A–D)         │ citations,      │
│  Trial Studio│   • BNS notice, urgency, veto card …    │ validation,     │
│  Evidence    │   • Copy · Sources · Trial · PDF · docx │ confidence      │
│  Contract    │                                         │                 │
│  Glossary    │  ┌───────────────────────────────────┐  │                 │
│ HISTORY      │  │ Describe your legal problem…      │  │                 │
│  …           │  │ 📎 Contract  🛡 Evidence        ⬆ │  │                 │
│ 🔑 API Key   │  └───────────────────────────────────┘  │                 │
└──────────────┴─────────────────────────────────────────┴─────────────────┘
```

On phones the sidebar opens from the ☰ button and the right panel slides in as an overlay.

## Run locally

```bash
# Terminal 1: backend (same as for the classic UI)
cd backend
python api_server.py

# Terminal 2: clean UI
cd saulgpt-ui-clean
npm install
npm run dev        # → http://localhost:5174
```

On Windows you can double-click `scripts\start_clean.bat` instead.

## Deploy (Firebase Hosting, separate site)

1. One-time: create a second Hosting site in the same Firebase project (Console → Hosting → *Add another site*),
   e.g. `saulgpt-clean`. If you pick a different name, update `"site"` in `firebase.clean.json`.
2. Run `Deploy_Frontend_Clean.bat`. It runs `firebase deploy --only hosting --config firebase.clean.json`.

`.env.production` points the build at the Hugging Face backend (`VITE_API_BASE`), the same as the classic UI.

## How "everything is the same inside" is kept true

* **Shell** (`src/App.jsx`, `src/components/*`) is new markup, but its state and API logic are carried over
  line for line from the classic `App.jsx`: sessions, conversations, guest messages, the drafting interview,
  triage choices, contract upload, BYOK key checks, the 401 auto-logout and the 429 rate-limit modal.
* **Feature components** (`src/features/*`): Trial Studio, Evidence uploader, Virtual Bench, Veto card,
  Toulmin matrix, BNS notice, Urgency banner, Jurisdiction badge, Decoded-terms ribbon, Glossary data and the
  PDF exporter are **copied from the classic UI** by a script. Their JSX logic is unchanged. Only their CSS colours
  are rewritten to the new theme.

When you change one of those components in `saulgpt-ui/src`, re-sync:

```bash
python saulgpt-ui-clean/scripts/sync_features.py
```

Don't edit `src/features/*` by hand, because the next sync overwrites it. Make the change in the classic UI and re-run the script.
