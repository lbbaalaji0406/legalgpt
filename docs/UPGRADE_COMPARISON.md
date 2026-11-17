# Upgrade Comparison: `claude/masterclass-upgrades` vs `claude/intelligent-lamport-znls45`

**Baseline branch:** `claude/intelligent-lamport-znls45` (two frontends, plus the v2.3 fixes)  
**Upgrade branch:** `claude/masterclass-upgrades` (this branch = baseline + the upgrades below)

Every upgrade started from a test against the **live production backend** (`lvvbaaal-legalgpt-api.hf.space`, 16 Nov 2026), not from documentation. Each was then re-tested on the same input with the real Groq models.

## Live feature audit (baseline, production)

| Feature | Verdict | What the live test showed |
| :--- | :--- | :--- |
| Knowledge Q&A | ⚠️ Medium | Well structured, but called §318 BNS cheating "generally non-cognizable and bailable" (wrong for §318(4)), then said "file an FIR". `citations: []` despite 7 laws retrieved. "Validated, 85%" was hard-coded. |
| Pathfinder | ✅ Good | Correct §173(4) BNSS escalation route |
| Contract review | ⚠️ Good, not great | 5/8 planted defects; cited the repealed Payment of Wages Act; praised a one-sided notice period; never named §28 |
| Drafting (.docx) | ❌ Unusable | Cheque-bounce request got a generic 5-question notice; the fact paragraph was pasted into FROM, TO (wrong party) and the signature |
| Evidence (images) | ❌ Broken | Clean memo → nothing extracted, yet "95% confidence". The vision model had been decommissioned by Groq. |
| Trial Studio | ✅ Strong | Sharp questions, correct precedent (*Basalingappa*, (2019) 5 SCC 418); the shown delta contradicted the score |
| Sign-up | ❌ Broken | 9/9 attempts failed (Postgres sequence). Fixed on both branches; needs deploy. |

## Upgrades: before → after (same input)

### 1. Evidence Locker: reads the document, computes the deadline, admits uncertainty
Input: a printed SBI cheque-return memo (amount Rs 2,00,000, return date 02/11/2026, "FUNDS INSUFFICIENT").

| | Before | After |
| :--- | :--- | :--- |
| Amount / cheque no. | "Not visible in OCR extraction" | Rs. 2,00,000/- · 448812 |
| Parties | "Bank (Drawee Bank)" / "Payee" | Suresh Patel (Drawer) / Ramesh Kumar (Payee) |
| Return reason | "Specific reason not extracted" | FUNDS INSUFFICIENT |
| §138(b) notice deadline | "30 days from the date of the bank return memo" | **02 December 2026, 16 days left** (computed in code) |
| Confidence when nothing is read | 0.95, no manual check | ≤ 0.3, so the UI's manual-date guardrail appears |

Changes: vision via `qwen/qwen3.8-27b` (env `GROQ_VISION_MODEL`), a deterministic date and deadline calculator (adds an EXPIRED state), confidence capping, no placeholder numbers in the prompt, and no "today" used as the return date on failure. Tests: `backend/tests/test_evidence_clock.py`.

### 2. Document drafting: one message in, a correct notice out
Input: "I need to draft a legal notice for a bounced cheque", then one paragraph with all the facts.

| | Before | After |
| :--- | :--- | :--- |
| Document type | Generic "Legal Notice" (5 generic fields) | **Cheque Bounce Notice (NIA §138)** (10 fields incl. bank, return date, reason) |
| Messages needed | 6 | **1**: all 10 fields extracted from the paragraph |
| FROM / TO | Whole paragraph in both (TO showed the sender) | Ramesh Kumar, 14 MG Road… / Suresh Patel, 22 Brigade Road… |
| Signature | Client name labelled "Advocate" | Client as "(Sender)" plus an optional "Through Advocate" line |

Tests: `backend/tests/test_interview_extraction.py`. *Known nit:* the model-written body may still cite §141 (company offences) for an individual drawer.

### 3. Contract review: current law, every clause, no praise for one-sided terms
Same 8-defect employment contract. After: names §28 for the Singapore-only courts clause, cites the **Code on Wages, 2019** and **Social Security Code, 2020** instead of repealed Acts, flags the 6-months-vs-7-days notice imbalance, and lists only neutral facts as positives.

### 4. Honest answer metadata
The researcher agent now returns the retrieved sections as `citations` (web sources labelled as such) and passes Layer 4's real `is_hallucinating`, `confidence_score`, `flagged_citations` and `repealed_warnings`, instead of a fixed "validated, 85%". The Sources panel and chips in both UIs pick this up unchanged. Test: `backend/tests/test_researcher_citations.py`.

### 5. Trial Studio score
The delta shown is now the net change since the previous turn (live example: a +10 shown against an unchanged 65 becomes 0).

### 6. Model hygiene
The nonexistent fallback `qwen/qwen3.6-27b` is replaced with models available on Groq. The models the app actually uses are `qwen/qwen3.8-27b` (primary, also vision) and `openai/gpt-oss-120b` / `gpt-oss-20b`.

## How to compare
```bash
git diff claude/intelligent-lamport-znls45..claude/masterclass-upgrades --stat
python backend/tests/test_evidence_clock.py
python backend/tests/test_interview_extraction.py
python backend/tests/test_researcher_citations.py
```
The backend changes only take effect for users after the Hugging Face Space is redeployed from this branch. The frontend change (Evidence expiry state and caveat) is in both UIs.

## Not changed (still open)
- **Knowledge-answer legal accuracy** (cognizable/bailable classification): needs a grounded check of the classification against the BNS schedule, not just a prompt tweak.
- **Latency:** 2–4 minutes per answer on the Space.
- **Guest fallback (G-2)** and **unauthenticated tool endpoints (G-3)** from FDD §7: these change backend auth behaviour and need your decision.
