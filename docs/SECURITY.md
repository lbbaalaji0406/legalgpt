# SaulGPT Security Model (v2.4)

The API is public on the internet, so it is **default-deny**. Code: `backend/security.py` (one dependency attached to
the app, so it also protects the routes that `app.py` copies into Gradio's server), `backend/auth.py`.
Tests: `backend/tests/test_security.py` (15 checks, including one that calls *every* route without a login).

## What is enforced
| Rule | Detail |
| :--- | :--- |
| Login required | Every `/api/*` route answers **401** without a valid login, except `GET /api/health`, `POST /api/auth/signup`, `POST /api/auth/login`. A new route is protected automatically. |
| Login token | JWT, 30 days, signed with **`JWT_SECRET`** (Space secret, 32+ chars). Read from `X-SaulGPT-Token`, else `Authorization: Bearer`. Both UIs send both. If `JWT_SECRET` is missing a random per-process secret is used (everyone is logged out on restart); there is no built-in default. |
| Bring your own key | AI routes (`/api/chat`, `/upload`, `/evidence/upload`, `/bench/*`, `/trial/*`, `/test/*`) need the user's `X-Groq-Api-Key: gsk_...` (**400** otherwise). Every AI client is built per request with that key. The server's `GROQ_API_KEY` is used only if `ALLOW_SERVER_GROQ_KEY=1`. The public Gradio page asks visitors for their key too. |
| Rate limits | Login/sign-up: 20/min per IP; sign-ups: 10/hour per IP. Login attempts: 10 per account per IP and 50 per account (all IPs) per 15 min, so one attacker cannot lock a user out. AI routes: 20/min per user. Everything else: 120/min per user. Over the limit: **429** "Too many requests". In-memory, single process. |
| Private sessions | Client session ids are validated (`[A-Za-z0-9_-]{1,100}`) and prefixed with the user id server-side (`u<id>_...`): no reading another user's chat memory, draft state or documents, and no path tricks in file names. |
| Downloads | `.docx` only for its owner or a signed link (`?t=`, 24 h). Certificate PDFs only with the signed link given to the uploader (24 h). |
| Sign-up input | Valid email, password 8 to 72 characters, username up to 50. |

## Operating it
* Set `JWT_SECRET` (Hugging Face: Space → Settings → Variables and secrets). Changing it logs everyone out once.
* To remove the old server key entirely, delete `GROQ_API_KEY` from the Space secrets: the app no longer needs it.
* Run the tests: `python -m pytest backend/tests -q`.

## Known limits (accepted, not fixed)
* No email verification (needs an email-sending service): anyone can create accounts, capped at 10 per IP per hour.
* Limits are per process: a multi-instance deployment needs a shared store such as Redis.
* An attacker with 50+ different IP addresses can still pause logins to one known email for 15 minutes; a single machine cannot.
* Gradio's own `/gradio_api` endpoints are untouched; the only function exposed there now needs the visitor's key.
