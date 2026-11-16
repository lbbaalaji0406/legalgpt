# SaulGPT Security Model (v2.4)

The API is public on the internet, so it is **default-deny**. Code: `backend/security.py` (one dependency attached to
the app, so it also protects the routes that `app.py` copies into Gradio's server), `backend/auth.py`.
Tests: `backend/tests/test_security.py` (13 checks, including one that calls *every* route without a login).

## What is enforced
| Rule | Detail |
| :--- | :--- |
| Login required | Every `/api/*` route answers **401** without a valid login, except `GET /api/health`, `POST /api/auth/signup`, `POST /api/auth/login`. A new route is protected automatically. |
| Login token | JWT, 30 days, signed with **`JWT_SECRET`** (Space secret, 32+ chars). Read from `X-SaulGPT-Token`, else `Authorization: Bearer`. Both UIs send both. If `JWT_SECRET` is missing a random per-process secret is used (everyone is logged out on restart); there is no built-in default. |
| Bring your own key | AI routes (`/api/chat`, `/upload`, `/evidence/upload`, `/bench/*`, `/trial/*`, `/test/*`) need the user's `X-Groq-Api-Key: gsk_...` (**400** otherwise). Every AI client is built per request with that key. The server's `GROQ_API_KEY` is used only if `ALLOW_SERVER_GROQ_KEY=1`. The public Gradio page asks visitors for their key too. |
| Rate limits | Login/sign-up: 20/min per IP, and 10 login attempts per account per 15 min. AI routes: 20/min per user. Everything else: 120/min per user. Over the limit: **429** "Too many requests". In-memory, single process. |
| Private sessions | Client session ids are validated (`[A-Za-z0-9_-]{1,100}`) and prefixed with the user id server-side (`u<id>_...`): no reading another user's chat memory, draft state or documents, and no path tricks in file names. |
| Downloads | `.docx` only for its owner or a signed link (`?t=`, 24 h). Certificate PDFs only with a signed link or a login. |
| Sign-up input | Valid email, password 8 to 72 characters, username up to 50. |

## Operating it
* Set `JWT_SECRET` (Hugging Face: Space → Settings → Variables and secrets). Changing it logs everyone out once.
* To remove the old server key entirely, delete `GROQ_API_KEY` from the Space secrets: the app no longer needs it.
* Run the tests: `python -m pytest backend/tests -q`.

## Known limits (accepted, not fixed)
* No email verification, so anyone can create accounts (rate limited per IP). Add it before opening to untrusted crowds.
* Limits are per process: a multi-instance deployment needs a shared store such as Redis.
* A certificate PDF is reachable by any signed-in user who knows its file name (8 hex characters from the file hash, plus the rate limit); the link itself is not tied to the uploader.
* A determined attacker can lock a *known* email out of login for 15 minutes by guessing wrong passwords. The alternative (no per-account limit) allows password guessing.
* Gradio's own `/gradio_api` endpoints are untouched; the only function exposed there now needs the visitor's key.
