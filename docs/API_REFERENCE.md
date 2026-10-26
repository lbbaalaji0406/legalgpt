# 📜 SaulGPT API Reference Manual
**API Version:** 2.2.0  
**Cloud Base URL:** `https://lvvbaaal-legalgpt-api.hf.space`  
**Local Development Base URL:** `http://localhost:8000`  
**Transport Security:** HTTPS / TLS 1.3  
**Authentication Scheme:** Bearer Token (JWT, 30-day validity, HS256) + BYOK Header (`X-Groq-Api-Key`)

---

## 1. Authentication Endpoints

### `POST /api/auth/signup`
Registers a new user in the PostgreSQL (or local SQLite) database.
- **Request Body:**
  ```json
  {
    "username": "advocate_sharma",
    "email": "sharma@lawchambers.in",
    "password": "StrongPassword123!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "advocate_sharma",
      "email": "sharma@lawchambers.in"
    }
  }
  ```

### `POST /api/auth/login`
Authenticates existing users and issues a JWT token.
- **Request Body:**
  ```json
  {
    "email": "sharma@lawchambers.in",
    "password": "StrongPassword123!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "advocate_sharma",
      "email": "sharma@lawchambers.in"
    }
  }
  ```

### `GET /api/auth/me`
Retrieves current authenticated profile.
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):**
  ```json
  {
    "id": 1,
    "username": "advocate_sharma",
    "email": "sharma@lawchambers.in"
  }
  ```

---

## 2. BYOK (Bring Your Own Key) Security Endpoints

### `POST /api/keys/validate`
Validates a personal Groq API key format and live cloud quota.
- **Request Body:**
  ```json
  {
    "key": "gsk_live_sample_token..."
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "valid": true,
    "message": "Key is active and authenticated with Groq API"
  }
  ```

### `GET /api/keys/status`
Checks if the server environment has a default Groq key or requires BYOK.
- **Response (200 OK):**
  ```json
  {
    "server_key_present": true,
    "byok_required": false
  }
  ```

---

## 3. Core Chat & Document Pipeline Endpoints

### `POST /api/chat`
Main conversational query endpoint. Dispatches through the 6-layer RAG pipeline, triage state machine, or document drafting interview.
- **Headers:**
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>` *(Optional; guest session assumed if omitted)*
  - `X-Groq-Api-Key: gsk_...` *(Optional; forwards personal Groq quota)*
- **Request Body:**
  ```json
  {
    "message": "Draft a legal notice for cheque bounce of Rs 75,000",
    "session_id": "session_uuid_or_custom_id",
    "user_id": 1,
    "conv_id": 6
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "response": "**Cheque Bounce Notice** has been drafted successfully.\n\n[Download your document](https://lvvbaaal-legalgpt-api.hf.space/api/document/session_uuid_or_custom_id)",
    "mode_used": "document",
    "confidence_score": 0.85,
    "critic_reward_score": 0.95,
    "critic_deliberation": null,
    "is_hallucinating": false,
    "citations": [],
    "remapped_laws": {
      "IPC": "BNS (Bharatiya Nyaya Sanhita, 2023)",
      "CrPC": "BNSS (Bharatiya Nagarik Suraksha Sanhita, 2023)"
    },
    "meta": {
      "document_ready": true,
      "document_url": "https://lvvbaaal-legalgpt-api.hf.space/api/document/session_uuid_or_custom_id"
    },
    "conv_id": 6,
    "interview_active": false,
    "interview_complete": true
  }
  ```

### `GET /api/document/{session_id}`
Streams a generated Microsoft Word (`.docx`) file as a download attachment.
- **Response Headers:**
  - `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - `Content-Disposition: attachment; filename="legal_document_{session_id}.docx"`
  - `Access-Control-Allow-Origin: *`

### `GET /api/draft/state/{session_id}`
Returns active interview state, current progress percentage, and missing fields.
- **Response (200 OK):**
  ```json
  {
    "state": "interviewing",
    "doc_type": "cheque_bounce",
    "progress_pct": 57,
    "missing_fields": ["amount", "date_of_default"],
    "is_active": true
  }
  ```

### `DELETE /api/draft/state/{session_id}`
Cancels the active drafting interview and resets the session state.

### `DELETE /api/history/{session_id}`
Purges the in-memory conversation history for a given session.

---

## 4. Pre-Trial Studio & Moot Court Endpoints

### `POST /api/trial/start`
Initializes an adversarial Moot Court chamber.
- **Request Body:**
  ```json
  {
    "case_title": "State vs. Accused (Section 103 BNS)",
    "scenario_description": "Accused allegedly assaulted complainant on 10 July 2024...",
    "session_id": "trial_session_001"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "trial_id": "trial_session_001",
    "judge_summary": "Issue framed under Section 103 BNS 2023...",
    "petitioner_strategy": "Argue premeditation and direct ocular evidence...",
    "respondent_strategy": "Assert right of private defense under Section 34 BNS..."
  }
  ```

### `POST /api/trial/turn`
Executes an adversarial interrogation turn with the judicial cross-examiner under Section 146 BSA 2023.
- **Request Body:**
  ```json
  {
    "trial_id": "trial_session_001",
    "user_statement": "The witness claims he saw the incident under street lighting from 50 meters away.",
    "role": "petitioner"
  }
  ```

### `POST /api/trial/conclude`
Concludes the moot proceedings, tallies evidence scores, and renders a judicial verdict.

### `GET /api/trial/precedents/{case_id}`
Retrieves verbatim precedent holdings and coram metadata from the 50,000+ landmark judgment index.

---

## 5. Multimodal Evidence & Section 63 BSA Certification

### `POST /api/evidence/upload`
Uploads digital evidence (audio files, WhatsApp chat exports, invoice PDFs, cheque scans) for forensic verification.
- **Form Data:**
  - `file`: Binary file upload
  - `session_id`: Session string
  - `evidence_type`: `audio` | `document` | `cheque`
- **Response (200 OK):**
  ```json
  {
    "evidence_id": "EVID-2024-99182",
    "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "certificate": {
      "certificate_id": "BSA-63-2024-99182",
      "pdf_url": "/api/certificates/BSA-63-2024-99182.pdf"
    },
    "extracted_data": {
      "summary": "Audio conversation between tenant and landlord regarding rent default."
    }
  }
  ```

### `GET /api/certificates/{cert_filename}`
Serves court-admissible Section 63 BSA PDF certificates.

---

## 6. Contract Risk Evaluator (Layer 6)

### `POST /api/upload`
Evaluates contracts and master agreements up to 25,000 characters in a single pass.
- **Form Data:**
  - `file`: Contract document (`.pdf`, `.docx`, `.txt`)
  - `session_id`: String
- **Response (200 OK):**
  ```json
  {
    "session_id": "contract_audit_001",
    "evaluation": {
      "overall_score": 72,
      "risk_level": "Medium Risk",
      "summary": "Standard SaaS subscription agreement with void post-termination non-compete.",
      "void_clauses": [
        {
          "clause": "Clause 14.2: Employee non-compete for 2 years across India",
          "statute": "Section 27, Indian Contract Act 1872",
          "remedy": "Delete non-compete; replace with strict customer non-solicitation."
        }
      ]
    }
  }
  ```

---

## 7. Cloud Persistence & Conversations

### `GET /api/conversations`
Lists past conversations for the authenticated user from Supabase.
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):**
  ```json
  {
    "conversations": [
      {
        "id": 6,
        "title": "Cheque Bounce Notice under Section 138 NIA",
        "created_at": "2026-10-26T14:44:43Z",
        "updated_at": "2026-10-26T14:51:03Z"
      }
    ],
    "total": 1
  }
  ```

### `GET /api/conversations/{id}`
Loads full turn history and structured metadata for conversation ID.
- **Headers:** `Authorization: Bearer <token>`

### `DELETE /api/conversations/{id}`
Permanently deletes a conversation and cascades through messages.

---

## 8. System Diagnostics

### `GET /api/health`
Checks server vitality and returns feature capabilities.
- **Response (200 OK):**
  ```json
  {
    "status": "SaulGPT API is Online ⚖️",
    "version": "2.0.0",
    "features": [
      "6-layer RAG",
      "Contract Evaluation",
      "Interactive Drafter"
    ]
  }
  ```
