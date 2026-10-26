"""
SAULGPT — INTERVIEW STATE MACHINE
====================================
Deterministic state manager for Interactive Document Drafting.

States:
  IDLE          → No draft in progress
  INTERVIEWING  → Collecting required fields from user
  DRAFTING      → All fields collected, generating document
  COMPLETE      → Document delivered

Now uses LLM-generated field questions instead of hardcoded schemas.
"""

import os, re, json
from typing import Optional, List

# ─────────────────────────────────────────────────────────────
# LEGACY DOCUMENT SCHEMAS — kept for transition only
# Will be removed when triage spec flow is fully verified
# ─────────────────────────────────────────────────────────────

DOCUMENT_SCHEMAS = {
    "legal_notice": {
        "display_name": "Legal Notice",
        "fields": {
            "sender_name":     {"label": "Your Full Name",                    "example": "Ravi Kumar"},
            "recipient_name":  {"label": "Recipient's Full Name / Company",   "example": "ABC Pvt Ltd"},
            "amount":          {"label": "Amount Involved (in rupees)",        "example": "50,000"},
            "incident_date":   {"label": "Date of Incident / Default",         "example": "15 January 2025"},
            "reason":          {"label": "Reason for Notice (brief)",          "example": "3 months unpaid salary"},
        },
        "days_to_respond": 15,
    },
    "cheque_bounce": {
        "display_name": "Cheque Bounce Notice (NIA Section 138)",
        "fields": {
            "payee_name":    {"label": "Your Name (Payee)",          "example": "Ravi Kumar"},
            "drawer_name":   {"label": "Cheque Issuer's Name",       "example": "Mohan Sharma"},
            "amount":        {"label": "Cheque Amount (in rupees)",  "example": "3,00,000"},
            "cheque_number": {"label": "Cheque Number",              "example": "004521"},
            "cheque_date":   {"label": "Date on Cheque",             "example": "10 January 2025"},
            "bank_name":     {"label": "Bank Name",                  "example": "State Bank of India"},
            "return_date":   {"label": "Date Bank Returned Cheque",  "example": "12 January 2025"},
        },
        "days_to_respond": 15,
    },
    "employment_notice": {
        "display_name": "Employment Grievance Notice",
        "fields": {
            "employee_name": {"label": "Your Full Name",          "example": "Priya Singh"},
            "employer_name": {"label": "Employer / Company Name", "example": "XYZ Corp Pvt Ltd"},
            "job_title":     {"label": "Your Job Title",          "example": "Software Engineer"},
            "issue":         {"label": "The Issue (brief)",       "example": "Unpaid salary for 3 months"},
            "start_date":    {"label": "Employment Start Date",   "example": "March 2022"},
        },
        "days_to_respond": 14,
    },
    "fir_complaint": {
        "display_name": "FIR / Police Complaint",
        "fields": {
            "complainant":     {"label": "Your Full Name",           "example": "Anita Verma"},
            "accused_name":    {"label": "Accused Person's Name",    "example": "Unknown / John Doe"},
            "incident_date":   {"label": "Date of Incident",         "example": "5 February 2025"},
            "incident_location": {"label": "Location of Incident",   "example": "MG Road, Bengaluru"},
            "incident_details": {"label": "Describe what happened",  "example": "My phone was snatched..."},
        },
        "days_to_respond": None,
    },
    "eviction_notice": {
        "display_name": "Eviction Notice",
        "fields": {
            "landlord_name":   {"label": "Landlord's Full Name",        "example": "Ramesh Gupta"},
            "tenant_name":     {"label": "Tenant's Full Name",          "example": "Suresh Patel"},
            "property_address": {"label": "Full Property Address",      "example": "Flat 4B, Green Tower, Mumbai"},
            "monthly_rent":    {"label": "Monthly Rent (in rupees)",    "example": "45,000"},
            "default_date":    {"label": "Date Rent Default Started",   "example": "1 December 2025"},
            "lease_end_date":  {"label": "Lease Expiry Date (if known)", "example": "24 June 2026"},
        },
        "days_to_respond": 15,
    },
    "rental_agreement": {
        "display_name": "Rental Agreement",
        "fields": {
            "landlord_name":   {"label": "Landlord's Full Name",        "example": "Suresh Patel"},
            "tenant_name":     {"label": "Tenant's Full Name",          "example": "Amit Shah"},
            "property_address": {"label": "Full Property Address",      "example": "Flat 4B, Green Tower, Mumbai"},
            "monthly_rent":    {"label": "Monthly Rent (in rupees)",    "example": "25,000"},
            "start_date":      {"label": "Lease Start Date",            "example": "1 March 2025"},
            "duration_months": {"label": "Lease Duration (months)",     "example": "11"},
            "deposit":         {"label": "Security Deposit (in rupees)", "example": "75,000"},
        },
        "days_to_respond": None,
    },
}

DOCUMENT_TRIGGERS = {
    "court_plaint":     ["court plaint", "plaint", "court petition", "file petition", "civil suit",
                         "suit for eviction", "injunction petition", "plaint under cpc", "order 7 cpc", "plaint for eviction"],
    "consumer_complaint": ["consumer complaint", "consumer forum", "consumer court", "consumer dispute", "ncdrc", "dcdrc", "scdrc"],
    "fir_complaint":    ["fir", "police complaint", "file a complaint", "complaint to police", "fir draft", "section 154", "section 173 bnss"],
    "eviction_notice":  ["eviction notice", "evict tenant", "notice to tenant", "notice for eviction", "eviction demand"],
    "legal_notice":     ["legal notice", "notice to", "send a notice", "formal notice", "demand notice", "advocate notice"],
    "cheque_bounce":    ["cheque bounce", "bounced cheque", "section 138", "dishonoured cheque",
                         "cheque returned", "insufficient funds notice", "138 notice"],
    "employment_notice":["salary notice", "employment notice", "hr notice", "unpaid salary notice",
                         "grievance notice", "wage notice"],
    "rental_agreement": ["rental agreement", "lease agreement", "rent agreement", "tenancy agreement", "commercial lease"],
}

# ─────────────────────────────────────────────────────────────
# LLM-DRIVEN FIELD GENERATION
# ─────────────────────────────────────────────────────────────

# Lazy-loaded LLM for field question generation
_field_llm = None

def _ensure_field_llm():
    try:
        from langchain_groq import ChatGroq
        from key_context import get_effective_groq_key
        api_key = get_effective_groq_key()
        return ChatGroq(
            model=os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b"),
            groq_api_key=api_key,
            temperature=0.1,
            max_tokens=1000,
        )
    except Exception as e:
        print(f"[InterviewState] Field LLM init failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# 4 MASTER INTAKE SCHEMAS — deterministic field counts per family
# LLM is used ONLY for narrative content generation (spec),
# NOT for field question generation.
# ─────────────────────────────────────────────────────────────

MASTER_SCHEMAS = {
    "letter": [
        {"key": "sender_name",    "label": "Your Full Name",                          "example": "Ravi Kumar"},
        {"key": "sender_address", "label": "Your Full Postal Address",                "example": "12, Gandhi Nagar, Adyar, Chennai – 600020"},
        {"key": "recipient_name", "label": "Recipient's Full Name / Company",         "example": "ABC Pvt Ltd"},
        {"key": "recipient_address", "label": "Recipient's Full Registered Address",  "example": "5th Floor, Monarch Building, MG Road, Bengaluru – 560001"},
        {"key": "date_of_default", "label": "Date of Incident / Default",             "example": "15 January 2025"},
        {"key": "amount_involved", "label": "Amount Involved (in rupees)",            "example": "1,00,000"},
        {"key": "details",         "label": "Brief Description of the Incident",      "example": "3 months unpaid salary for work done Jan–Mar 2025"},
    ],
    "pleading": [
        {"key": "plaintiff_name",   "label": "Plaintiff / Petitioner Full Name",      "example": "Ravi Kumar"},
        {"key": "plaintiff_address","label": "Plaintiff's Full Postal Address",       "example": "12, Gandhi Nagar, Chennai – 600020"},
        {"key": "defendant_name",   "label": "Defendant / Respondent Full Name",      "example": "ABC Pvt Ltd"},
        {"key": "defendant_address","label": "Defendant's Full Registered Address",   "example": "5th Floor, Monarch Building, MG Road, Bengaluru – 560001"},
        {"key": "cause_of_action_date", "label": "Date of Cause of Action",           "example": "2 March 2026"},
        {"key": "court_location",   "label": "Court / Forum Location",                "example": "Chennai District Court, Egmore"},
        {"key": "details",          "label": "Brief Facts of the Case",               "example": "Tenant stopped paying rent from March 2026 despite multiple reminders."},
    ],
    "affidavit": [
        {"key": "deponent_name", "label": "Deponent's Full Name",                    "example": "Ravi Kumar"},
        {"key": "father_name",   "label": "Father's / Husband's Name",               "example": "Mohan Kumar"},
        {"key": "deponent_age",  "label": "Age of Deponent",                         "example": "35"},
        {"key": "deponent_address", "label": "Deponent's Full Residential Address",  "example": "12, Gandhi Nagar, Chennai – 600020"},
        {"key": "details",       "label": "Facts to Be Sworn (brief)",               "example": "I witnessed the accident on 5 March 2026 at the junction of Mount Road."},
    ],
    "agreement": [
        {"key": "party1_name",       "label": "First Party Full Name",               "example": "Ravi Kumar"},
        {"key": "party1_address",    "label": "First Party's Registered Address",    "example": "12, Gandhi Nagar, Chennai – 600020"},
        {"key": "party2_name",       "label": "Second Party Full Name / Company",    "example": "ABC Pvt Ltd"},
        {"key": "party2_address",    "label": "Second Party's Registered Address",   "example": "5th Floor, Monarch Building, MG Road, Bengaluru – 560001"},
        {"key": "agreement_subject", "label": "Purpose / Subject of Agreement",       "example": "Commercial lease of ground floor office space"},
        {"key": "consideration_amount", "label": "Consideration / Payment (in rupees)", "example": "5,00,000"},
        {"key": "details",           "label": "Brief Background of the Agreement",    "example": "Party 1 is the owner of the property and Party 2 wishes to lease it for 11 months."},
    ],
}


def generate_field_questions(doc_family: str, doc_type: str, user_query: str) -> list:
    """
    Return deterministic field questions for the given document family.
    Uses the 4 Master Intake Schemas — no LLM call.
    Falls back to DOCUMENT_SCHEMAS if doc_type matches a known key.

    Returns:
        List of dicts: [{"key": str, "label": str, "example": str}, ...]
    """
    # Check legacy schemas first (specific doc_type overrides family)
    if doc_type in DOCUMENT_SCHEMAS:
        schema = DOCUMENT_SCHEMAS[doc_type]
        return [
            {"key": k, "label": v["label"], "example": v.get("example", "")}
            for k, v in schema["fields"].items()
        ]

    # Use 4 Master Schemas by family
    return MASTER_SCHEMAS.get(doc_family, MASTER_SCHEMAS["letter"])


# ─────────────────────────────────────────────────────────────
# DOCUMENT SPEC GENERATION — 4 Master System Prompts
# Each family has its own persona, guardrails, and output schema.
# ─────────────────────────────────────────────────────────────

FAMILY_SPEC_PROMPTS = {
    "letter": """You are SaulGPT, a meticulous Corporate Lawyer in India.
Your task is to draft a formal Legal Notice / Demand Letter.
You must output a strictly valid JSON object representing the document structure.

CRITICAL LEGAL GUARDRAILS:
1. STATUTORY DEMAND: The body MUST contain a strict demand clause (e.g., "I hereby call upon you to pay the sum of Rs. X within 15/30 days of receiving this notice, failing which my client shall be constrained to initiate civil/criminal proceedings without further notice."). Always state the exact timeline.
2. FACTUAL NARRATION: Begin with the relationship between parties (e.g., landlord-tenant, lender-borrower, employer-employee), then describe the specific default/breach/incident with exact dates and amounts.
3. STATUTORY BACKING: Cite the relevant provision (e.g., Section 138 of the Negotiable Instruments Act, 1881 for cheque bounce; Terms of contract for breach). Do not cite statutes you are uncertain about.
4. NO EMOTION: Maintain a cold, professional, and threatening legal tone throughout.

DOCUMENT STRUCTURE PRIMITIVES (use only these):
- "heading": For titles.
- "body_p": For introductory text and narrative paragraphs.
- "field_row": For key data points.
- "numbered_list": For listing facts or demands chronologically.
- "cc": For copy to (e.g., "Police Commissioner", "Advocate for the other side").
- "enclosure": For supporting documents mentioned.

DO NOT generate sender/recipient addresses, TO: block, or signatures. The Python backend handles formatting.

User's Problem: {problem_description}

Collected Fields:
{field_summary}

JSON SCHEMA:
{{
  "family": "letter",
  "dispatch_mode": "Registered Post with Acknowledgment Due (RPAD) / Speed Post",
  "sections": [
    {{"type": "heading", "text": "LEGAL NOTICE", "alignment": "center"}},
    {{"type": "body_p", "text": "Under instructions from my client {{sender_name}}, I hereby serve you with the following notice:"}},
    {{"type": "numbered_list", "items": ["Fact 1...", "Fact 2...", "Breach detail..."]}},
    {{"type": "body_p", "text": "I hereby call upon you to pay the sum of Rs. X within 15 days of receiving this notice, failing which my client shall be constrained to initiate civil/criminal proceedings without further notice."}},
    {{"type": "enclosure", "items": ["Copy of contract", "Salary/Work records"]}}
  ]
}}
""",

    "pleading": """You are SaulGPT, a Senior Advocate at a High Court in India.
Your task is to draft a formal Court Pleading (Plaint/Petition) based on the provided facts.
You must output a strictly valid JSON object representing the document structure.

CRITICAL LEGAL GUARDRAILS (ORDER 7 RULE 11 CPC):
1. FACTUAL NARRATIVE: Write 5-7 numbered paragraphs in chronological order covering: (a) description of parties, (b) background facts leading to the dispute, (c) the exact cause of action with date, (d) details of demand and refusal, if any.
2. THE TRIAD OF SURVIVAL: The last three numbered_list items MUST be:
   — LIMITATION: "The cause of action arose on [date]. The present suit is within the period of limitation."
   — JURISDICTION: "This Hon'ble Court has territorial and pecuniary jurisdiction to try the present suit as [reason]."
   — VALUATION: "The suit is valued at Rs. [amount] for the purpose of court fees and jurisdiction."
3. PRAYER: Draft 3-5 specific relief items — each must be quantifiable and actionable (e.g., "Pass a decree for recovery of Rs. 5,00,000 with interest at 12% per annum from the date of suit till realisation").

DOCUMENT STRUCTURE PRIMITIVES (use only these):
- "body_p": For introductory text.
- "numbered_list": For the main factual narrative, cause of action, and jurisdiction clauses.
- "prayer": For the final relief sought.
- "attestation": REQUIRED — use {{knowledge_range}} and {{advice_index}} as literal placeholders. The Python engine will replace these with correct paragraph numbers.
- "field_row": For listing key dates/amounts not covered in body.

DO NOT generate Cause Titles, Signatures, or Verification headings. The Python backend handles these automatically.

User's Problem: {problem_description}

Collected Fields:
{field_summary}

JSON SCHEMA:
{{
  "family": "pleading",
  "sub_jurisdiction": "DISTRICT_CIVIL",
  "parties": {{"plaintiff": "plaintiff_name", "defendant": "defendant_name"}},
  "sections": [
    {{"type": "body_p", "text": "The Plaintiff most respectfully showeth as under:"}},
    {{"type": "numbered_list", "items": ["Fact 1...", "Fact 2...", "Limitation clause...", "Jurisdiction clause...", "Valuation clause..."]}},
    {{"type": "field_row", "label": "Date of Cause of Action", "value_field": "cause_of_action_date"}},
    {{"type": "attestation", "paragraphs": ["Verified at ________ on this [DATE], that the contents of paragraphs {{knowledge_range}} are true to my personal knowledge, and paragraphs {{advice_index}} is based on legal advice which I believe to be true. Nothing material has been concealed."]}},
    {{"type": "prayer", "items": ["Pass a decree for Rs. X...", "Award costs..."]}}
  ]
}}
""",

    "affidavit": """You are SaulGPT, an expert Indian Notary and Legal Draftsman.
Your task is to draft a sworn Affidavit.
You must output a strictly valid JSON object representing the document structure.

CRITICAL LEGAL GUARDRAILS (ORDER 19 CPC):
1. FIRST PERSON: Every statement must be in the first person ("I say that...", "I submit that...", "That I am...").
2. FACTUAL SEGREGATION: Paragraphs 1-X should cover facts within the deponent's personal knowledge (what they saw, heard, did). The last paragraph should be a legal submission based on advice.
3. COMPREHENSIVE COVERAGE: Cover all relevant facts — identity of deponent, relationship to the case, sequence of events, documents executed, losses suffered, and the grounds for making this affidavit.
4. VERIFICATION: You MUST include an "attestation" section with template string containing {{knowledge_range}} and {{advice_index}} placeholders.

DOCUMENT STRUCTURE PRIMITIVES (use only these):
- "numbered_list": For the main sworn statements. Each item is a numbered paragraph starting with "I say that..." or "That I am...".
- "attestation": Exactly one paragraph containing {{knowledge_range}} and {{advice_index}} placeholders.

DO NOT generate the Oath Heading ("I, Name, aged...") or Signature/Identification blocks. The Python backend handles these.

User's Problem: {problem_description}

Collected Fields:
{field_summary}

JSON SCHEMA:
{{
  "family": "affidavit",
  "requires_stamp_paper": true,
  "display_name": "AFFIDAVIT IN SUPPORT",
  "sections": [
    {{"type": "numbered_list", "items": [
      "I say that I am the deponent herein and am well conversant with the facts of this case.",
      "I say that the original Sale Deed dated ... was executed in my favour and was in my lawful possession.",
      "I say that the said document has been lost despite diligent search.",
      "I submit that the non-production of the original is not deliberate and that the certified copy may be read in evidence."
    ]}},
    {{"type": "attestation", "paragraphs": [
      "Verified at Chennai on this date, that the contents of paragraphs {{knowledge_range}} are true to my personal knowledge, and paragraph {{advice_index}} is based on legal advice which I believe to be true. Nothing material has been concealed."
    ]}}
  ]
}}
""",

    "agreement": """You are SaulGPT, a Tier-1 Corporate Transactional Attorney.
Your task is to draft a binding Agreement or Contract.
You must output a strictly valid JSON object representing the document structure.

CRITICAL LEGAL GUARDRAILS:
1. RECITALS (WHEREAS clauses): 2-5 body_p paragraphs covering: (a) identity and capacity of each party, (b) background/context leading to the agreement, (c) mutual desire to enter into this agreement. Each recital must start with "WHEREAS".
2. OPERATIVE CLAUSES: After recitals, include "NOW THEREFORE, in consideration of the mutual covenants, it is agreed as follows:" as a body_p. Then 10-20 numbered_list items covering all operative terms — payment, term, delivery, representations, warranties, indemnification, confidentiality, termination, force majeure.
3. SCHEDULE: If the agreement involves property, include a schedule_box with exact boundaries and description.
4. DISPUTE RESOLUTION: The last numbered_list item MUST include an arbitration clause specifying the seat (e.g., "Subject to the exclusive jurisdiction of the courts at Chennai. Any dispute shall be resolved through arbitration under the Arbitration and Conciliation Act, 1996.").
5. BOILERPLATE: Include standard clauses — entire agreement, amendment in writing, severability, notice, assignment, governing law, and waiver.

DOCUMENT STRUCTURE PRIMITIVES (use only these):
- "body_p": For WHEREAS recitals and introductory text.
- "numbered_list": For operative clauses.
- "schedule_box": For property/asset schedules (required when property is involved).

DO NOT generate "BETWEEN Party A AND Party B" block, witness blocks, or signatures. The Python backend handles these.

User's Problem: {problem_description}

Collected Fields:
{field_summary}

JSON SCHEMA:
{{
  "family": "agreement",
  "requires_stamp_paper": true,
  "display_name": "AGREEMENT",
  "sections": [
    {{"type": "body_p", "text": "WHEREAS the First Party is the absolute owner of the property situated at..."}},
    {{"type": "body_p", "text": "WHEREAS the Second Party desires to take the said property on lease..."}},
    {{"type": "body_p", "text": "NOW THEREFORE, in consideration of the mutual covenants, it is agreed:"}},
    {{"type": "numbered_list", "items": ["Term and Rent: ...", "Maintenance and Repairs: ...", "Security Deposit: ...", "Termination: ...", "Arbitration and Jurisdiction: ..."]}},
    {{"type": "schedule_box", "title": "SCHEDULE OF PROPERTY", "boundaries": {{"North": "...", "South": "...", "East": "...", "West": "..."}}}}
  ]
}}
""",
}



def sanitize_narrative_text(text: str) -> str:
    """Strip prompt artifacts, [User Goal: ...], and command phrases."""
    if not text:
        return ""
    cleaned = re.sub(r"\[User Goal:\s*[^\\\]]+\]", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?i)\b(please\s+)?(assist|help)\s+me\s+(to\s+)?(do|draft|write|create|make)\b.*", "", cleaned)
    cleaned = re.sub(r"(?i)\b(draft|generate|prepare)\s+(a|an|the)?\s+[a-z\s]+notice.*", "", cleaned)
    return cleaned.strip()


def build_fallback_spec(
    doc_family: str,
    doc_type: str,
    display_name: str,
    filled_fields: dict,
    problem_description: str = "",
) -> dict:
    """
    Deterministic fallback document spec that generates clean, formal,
    professional Indian legal drafts without ever leaking user prompts or raw key-value dumps.
    """
    family = doc_family or "letter"
    display = (display_name or doc_type or "LEGAL NOTICE").replace("_", " ").title()

    sender_name = filled_fields.get("sender_name") or filled_fields.get("sender_full_name") or "Sender"
    sender_addr = filled_fields.get("sender_address") or filled_fields.get("sender_full_address") or ""
    recipient_name = filled_fields.get("recipient_name") or filled_fields.get("recipient_full_name") or "Recipient"
    recipient_addr = filled_fields.get("recipient_address") or filled_fields.get("recipient_full_address") or ""
    amount = filled_fields.get("amount_involved") or filled_fields.get("amount") or filled_fields.get("cheque_amount") or ""
    date_val = filled_fields.get("date_of_default") or filled_fields.get("incident_date") or filled_fields.get("cheque_date") or ""
    raw_details = filled_fields.get("details") or filled_fields.get("reason") or ""
    clean_details = sanitize_narrative_text(raw_details)

    if family == "letter":
        is_cheque = "cheque" in (doc_type or "").lower() or "cheque" in display.lower() or "138" in display.lower()
        title_text = "LEGAL NOTICE UNDER SECTION 138 OF THE NEGOTIABLE INSTRUMENTS ACT, 1881" if is_cheque else f"LEGAL NOTICE: {display.upper()}"

        items = [
            f"That my client, {sender_name}, entered into lawful business / contractual dealings with you, {recipient_name}.",
        ]
        if is_cheque:
            items.extend([
                f"That in discharge of your legally enforceable debt and liability towards my client, you issued a cheque for an amount of Rs. {amount or '__________'}/-.",
                f"That my client presented the said cheque for encashment through their bank, but the same was dishonoured and returned unpaid by the drawee bank on or around {date_val or 'the due date'} with the remark 'Insufficient Funds' / 'Exceeds Arrangement'.",
                f"Particulars of transaction & default: {clean_details}." if clean_details else "That the cheque was dishonoured willfully despite prior assurance of sufficient balance.",
                "That the dishonour of the aforesaid cheque constitutes a criminal offence punishable under Section 138 of the Negotiable Instruments Act, 1881, as well as an offence under the Bharatiya Nyaya Sanhita (BNS), 2023."
            ])
            demand_para = f"NOW THEREFORE, I hereby call upon you to pay the aforesaid cheque amount of Rs. {amount or '__________'}/- to my client within a period of 15 (fifteen) days from the date of receipt of this notice, failing which my client shall be constrained to initiate criminal proceedings under Section 138 of the Negotiable Instruments Act, 1881, and file civil recovery proceedings, holding you fully liable for all costs and consequences thereof."
        else:
            items.extend([
                f"That on or around {date_val or 'the material date'}, you incurred a clear and undisputed legal and monetary obligation towards my client amounting to Rs. {amount or '__________'}/-.",
                f"Factual particulars of default: {clean_details}." if clean_details else "That you committed a material breach of the agreed terms and statutory obligations.",
                "That despite repeated demands and reminders, you have failed and neglected to clear the outstanding sum or remedy the default."
            ])
            demand_para = f"NOW THEREFORE, I hereby call upon you to clear the outstanding sum of Rs. {amount or '__________'}/- and remedy the said default within 15 (fifteen) days from the receipt of this legal notice, failing which my client shall initiate appropriate legal proceedings before the competent court of law, entirely at your risk, costs, and consequences."

        return {
            "family": "letter",
            "dispatch_mode": "Registered Post with Acknowledgment Due (RPAD) / Speed Post",
            "sections": [
                {"type": "heading", "text": title_text, "alignment": "center"},
                {"type": "body_p", "text": f"Under instructions from and on behalf of my client, {sender_name}, having address at {sender_addr or '__________'}, I hereby serve you with this formal Legal Notice:"},
                {"type": "numbered_list", "items": items},
                {"type": "body_p", "text": demand_para},
                {"type": "enclosure", "items": ["Copy of relevant documents / default records / dishonoured instruments", "Bank return memo / evidence of default"]}
            ]
        }

    elif family == "pleading":
        plaintiff = filled_fields.get("plaintiff_name") or sender_name
        defendant = filled_fields.get("defendant_name") or recipient_name
        cause_date = filled_fields.get("cause_of_action_date") or date_val or "recently"
        court_loc = filled_fields.get("court_location") or "District Court"
        return {
            "family": "pleading",
            "sub_jurisdiction": "DISTRICT_CIVIL",
            "parties": {"plaintiff": "plaintiff_name", "defendant": "defendant_name"},
            "sections": [
                {"type": "body_p", "text": f"The Plaintiff, {plaintiff}, most respectfully showeth as under:"},
                {"type": "numbered_list", "items": [
                    f"That the Plaintiff is a law-abiding citizen residing at {filled_fields.get('plaintiff_address', sender_addr or '__________')}.",
                    f"That the Defendant, {defendant}, is residing / carrying on business at {filled_fields.get('defendant_address', recipient_addr or '__________')}.",
                    f"Facts of the dispute: {clean_details or 'The Defendant defaulted on lawful obligations owed to the Plaintiff.'}",
                    f"The cause of action arose on {cause_date} when the Defendant failed and refused to comply with the Plaintiff\'s lawful demands.",
                    f"This Hon\'ble Court has territorial and pecuniary jurisdiction to try the present suit as the cause of action substantially arose within the local limits of {court_loc}.",
                    f"The suit is valued at Rs. {amount or '50,000'}/- for the purpose of court fees and jurisdiction, and the appropriate court fee has been affixed."
                ]},
                {"type": "prayer", "items": [
                    f"Pass a decree directing the Defendant to pay the sum of Rs. {amount or '__________'}/- along with interest at 18% per annum till realisation.",
                    "Award costs of the present suit in favour of the Plaintiff.",
                    "Pass any other relief that this Hon\'ble Court deems fit in the interests of justice."
                ]},
                {"type": "attestation", "paragraphs": [
                    "Verified at _________ on this [DATE], that the contents of paragraphs {knowledge_range} are true to my personal knowledge, and paragraph {advice_index} is based on legal advice which I believe to be true. Nothing material has been concealed."
                ]}
            ]
        }

    elif family == "affidavit":
        deponent = filled_fields.get("deponent_name") or sender_name
        father = filled_fields.get("father_name") or "__________"
        age = filled_fields.get("deponent_age") or "Adult"
        addr = filled_fields.get("deponent_address") or sender_addr or "__________"
        return {
            "family": "affidavit",
            "requires_stamp_paper": True,
            "display_name": display.upper(),
            "sections": [
                {"type": "numbered_list", "items": [
                    f"I say that I am the deponent herein, aged about {age} years, s/o or d/o {father}, residing at {addr}, and I am well conversant with the facts of this case.",
                    f"I say that: {clean_details or 'the statements made herein are true and correct to the best of my knowledge and belief.'}",
                    f"I say that the monetary amount involved in the subject matter is Rs. {amount or '__________'}/- and default occurred on or around {date_val or 'material time'}.",
                    "I submit that the present affidavit is executed bona fide in support of the prayer made herein."
                ]},
                {"type": "attestation", "paragraphs": [
                    "Verified at _________ on this [DATE], that the contents of paragraphs {knowledge_range} are true to my personal knowledge, and paragraph {advice_index} is based on legal advice which I believe to be true. Nothing material has been concealed."
                ]}
            ]
        }

    elif family == "agreement":
        p1 = filled_fields.get("party1_name") or sender_name
        p1_addr = filled_fields.get("party1_address") or sender_addr or "__________"
        p2 = filled_fields.get("party2_name") or recipient_name
        p2_addr = filled_fields.get("party2_address") or recipient_addr or "__________"
        subject = filled_fields.get("agreement_subject") or display
        return {
            "family": "agreement",
            "requires_stamp_paper": True,
            "display_name": display.upper(),
            "sections": [
                {"type": "body_p", "text": f"WHEREAS the First Party, {p1}, residing/situated at {p1_addr}, is legally competent to enter into this Agreement;"},
                {"type": "body_p", "text": f"WHEREAS the Second Party, {p2}, residing/situated at {p2_addr}, desires to enter into terms regarding {subject};"},
                {"type": "body_p", "text": "NOW THEREFORE, in consideration of the mutual covenants, it is agreed as follows:"},
                {"type": "numbered_list", "items": [
                    f"Scope: The parties agree to the following terms regarding: {clean_details or subject}.",
                    f"Consideration: The agreed financial consideration is Rs. {amount or '__________'}/-, payable as per mutually agreed milestones.",
                    "Term: This agreement shall take effect from the date of execution and shall remain in force until fulfilled or terminated.",
                    "Dispute Resolution: Subject to the exclusive jurisdiction of the competent civil courts. Any dispute shall be resolved through arbitration under the Arbitration and Conciliation Act, 1996."
                ]}
            ]
        }

    return {
        "family": "generic_instrument",
        "display_name": display,
        "sections": [
            {"type": "heading", "text": display.upper(), "alignment": "center"},
            {"type": "body_p", "text": f"This legal instrument is made on behalf of {sender_name} in relation to {recipient_name}."},
            {"type": "numbered_list", "items": [
                f"Factual background: {clean_details or 'The parties entered into an agreement/transaction.'}",
                f"Amount involved: Rs. {amount or '__________'}/-.",
                f"Date of default/incident: {date_val or '__________'}."
            ]},
            {"type": "signature", "party1_label": sender_name, "party2_label": recipient_name}
        ]
    }


def generate_document_spec(
    doc_family: str,
    doc_type: str,
    display_name: str,
    problem_description: str,
    filled_fields: dict,
) -> Optional[dict]:
    """
    Ask LLM to generate a structured document spec using the family-specific prompt.
    Returns spec dict or None on failure.
    """
    clean_prob = sanitize_narrative_text(problem_description or "")
    llm = _ensure_field_llm()
    if not llm:
        print(f"[InterviewState] LLM unavailable, using deterministic fallback spec for {doc_family}")
        return build_fallback_spec(doc_family, doc_type, display_name, filled_fields, clean_prob)

    # Select the per-family prompt template
    family = doc_family or "letter"
    prompt_template = FAMILY_SPEC_PROMPTS.get(family)
    if not prompt_template:
        print(f"[InterviewState] No spec prompt for family '{family}', falling back to letter")
        prompt_template = FAMILY_SPEC_PROMPTS["letter"]

    field_summary = "\n".join(
        f"  {k}: {v}" for k, v in filled_fields.items() if v
    ) if filled_fields else "  (no fields collected yet)"

    try:
        raw = ""
        prompt = prompt_template.format(
            problem_description=clean_prob,
            field_summary=field_summary,
        )
        resp = llm.invoke(prompt, max_tokens=1000, response_format={"type": "json_object"})
        raw = resp.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        try:
            spec = json.loads(raw)
        except json.JSONDecodeError:
            brace_start = raw.find("{")
            brace_end = raw.rfind("}")
            if brace_start != -1 and brace_end > brace_start:
                raw = raw[brace_start:brace_end+1]
                spec = json.loads(raw)
            else:
                raise
        if isinstance(spec, dict) and "sections" in spec and spec["sections"]:
            return spec
        else:
            print(f"[InterviewState] Spec missing 'sections' key or empty. Using fallback spec.")
    except Exception as e:
        print(f"[InterviewState] Spec generation LLM call failed ({e}). Using robust fallback spec.")
        if raw:
            print(f"[InterviewState] Raw LLM output (first 500): {raw[:500]}")

    return build_fallback_spec(doc_family, doc_type, display_name, filled_fields, clean_prob)


# ─────────────────────────────────────────────────────────────
# LEGACY DETECTION FUNCTIONS
# ─────────────────────────────────────────────────────────────

def detect_document_type(query: str) -> Optional[str]:
    """
    Word-boundary regex keyword document type detection.
    Checked first; if no match, returns None for LLM-based detection.
    """
    query_lower = query.lower()
    for doc_type, triggers in DOCUMENT_TRIGGERS.items():
        for trigger in triggers:
            if re.search(r'\b' + re.escape(trigger) + r'\b', query_lower):
                return doc_type
    return None


FAMILY_MAP = {
    "court_plaint":       "pleading",
    "fir_complaint":      "pleading",
    "consumer_complaint": "pleading",
    "court_petition":     "pleading",
    "eviction_notice":    "letter",
    "legal_notice":       "letter",
    "cheque_bounce":      "letter",
    "employment_notice":  "letter",
    "rental_agreement":   "agreement",
    "partnership_deed":   "agreement",
    "affidavit_general":  "affidavit",
}

def map_doc_type_to_family(doc_type: str) -> str:
    """Map a legacy doc_type to its document family."""
    return FAMILY_MAP.get(doc_type, "letter")


def detect_family(query: str) -> Optional[str]:
    """
    Detect document family from triage output or fallback to query analysis.
    Returns one of: letter, pleading, affidavit, agreement, generic_instrument
    """
    FAMILY_SIGNALS = {
        "letter":    ["legal notice", "notice to", "send a notice", "eviction", "cheque bounce",
                      "bounced cheque", "dishonour", "dishonored", "demand notice", "termination notice",
                      "recovery of dues", "unpaid salary"],
        "pleading":  ["suit", "petition", "plaint", "written statement", "complaint before",
                      "file a case", "file a suit", "appeal", "application before", "fir",
                      "police complaint", "criminal complaint", "injunction"],
        "affidavit": ["affidavit", "sworn statement", "undertaking on oath",
                      "declaration under oath", "solemn affirmation", "deponent"],
        "agreement": ["agreement", "contract", "deed", "mou", "memorandum of understanding",
                      "settlement", "lease deed", "sale deed", "partnership deed", "lease agreement",
                      "nda", "non-disclosure", "tenancy agreement"],
    }
    query_lower = query.lower()
    scores = {}
    for family, signals in FAMILY_SIGNALS.items():
        score = sum(1 for s in signals if re.search(r'\b' + re.escape(s) + r'\b', query_lower))
        if score > 0:
            scores[family] = score
    if scores:
        return max(scores, key=scores.get)
    return None


# ─────────────────────────────────────────────────────────────
# INTERVIEW STATE MANAGER
# ─────────────────────────────────────────────────────────────

class InterviewState:
    """
    Tracks the state of a document drafting interview for one session.

    States: idle → interviewing → drafting → complete
    """

    def __init__(self):
        self._state_stack       = ["idle"]
        self._context_stack     = [{}]
        self.doc_type           = None
        self.doc_family         = None
        self.collected          = {}
        self.current_field      = None
        self.doc_schema         = None
        self.is_dynamic         = False
        self.problem_description = ""
        self.last_problem_description = ""
        self._dynamic_fields    = []
        self._field_index       = 0
        self._supplementary     = []
        self._pending_fields    = []
        # Confirm / scrutiny state
        self.confirm_generation = False
        self.scrutiny_result    = None
        self.display_name       = ""
        self.pending_generation = False
        self.interrupted        = False
        # Interruption context (stored per stack entry)
        self._interrupt_ctx_stack = []

    @property
    def state(self):
        return self._state_stack[-1] if self._state_stack else "idle"

    @state.setter
    def state(self, value):
        if self._state_stack:
            self._state_stack[-1] = value
        else:
            self._state_stack.append(value)

    @property
    def interruption_context(self) -> dict:
        """Context for the current stack entry."""
        if self._interrupt_ctx_stack:
            return self._interrupt_ctx_stack[-1]
        idx = max(0, len(self._state_stack) - 1)
        while idx >= len(self._interrupt_ctx_stack):
            self._interrupt_ctx_stack.append({})
        return self._interrupt_ctx_stack[-1]

    @interruption_context.setter
    def interruption_context(self, value: dict):
        if self._interrupt_ctx_stack:
            self._interrupt_ctx_stack[-1] = value
        else:
            self._interrupt_ctx_stack.append(value)

    def push_state(self, new_state: str, context: dict = None):
        """Push a new state onto the stack (e.g. entering an interruption handler).
        The previous state is preserved and will be resumed on pop."""
        self._state_stack.append(new_state)
        self._interrupt_ctx_stack.append(context or {})

    def pop_state(self) -> str:
        """Pop the top state, returning to the previous one.
        Returns the new current state."""
        if len(self._state_stack) > 1:
            self._state_stack.pop()
            self._interrupt_ctx_stack.pop()
        return self._state_stack[-1] if self._state_stack else "idle"

    @property
    def state_stack_depth(self) -> int:
        return len(self._state_stack)

    def start_interview(self, doc_type: str, problem_description: str = "",
                        doc_family: str = None, dynamic_fields: list = None) -> str:
        """
        Start a new interview for a document type.

        Args:
            doc_type: Document type key (legacy) or LLM-chosen name
            problem_description: User's original query
            doc_family: one of letter/pleading/affidavit/agreement
            dynamic_fields: optional pre-generated field list

        Returns:
            First question to ask the user
        """
        self._state_stack = ["interviewing"]
        self._interrupt_ctx_stack = [{}]
        self.doc_type = doc_type
        self.doc_family = doc_family or map_doc_type_to_family(doc_type)
        self.collected = {}
        self._supplementary = []
        self._pending_fields = []
        self.problem_description = problem_description
        self.confirm_generation = False
        self.scrutiny_result = None
        self.pending_generation = False
        self.interrupted = False
        self.interruption_context = {}

        if dynamic_fields:
            fields = dynamic_fields
        elif doc_type in DOCUMENT_SCHEMAS:
            schema = DOCUMENT_SCHEMAS[doc_type]
            fields = [
                {"key": k, "label": v["label"], "example": v.get("example", "")}
                for k, v in schema["fields"].items()
            ]
        else:
            fields = generate_field_questions(self.doc_family, doc_type, problem_description)

        self._pending_fields = fields
        self._field_index = 0
        self._dynamic_fields = fields
        self.is_dynamic = doc_type not in DOCUMENT_SCHEMAS

        if not fields:
            self.state = "idle"
            return "I couldn't determine what information is needed. Please describe your situation in more detail."

        return self._ask_next()

    def _ask_next(self) -> str:
        """Return the next unanswered question."""
        if self._field_index >= len(self._pending_fields):
            return self._summarize()
        field = self._pending_fields[self._field_index]
        self.current_field = field["key"]
        label = field.get("label", field["key"].replace("_", " ").title())
        example = field.get("example", "")
        ex = f"\n*(Example: {example})*" if example else ""
        total = len(self._pending_fields)
        current = self._field_index + 1
        self.doc_schema = {"display_name": self._doc_display_name(), "fields": {f["key"]: f for f in self._pending_fields}}
        return f"**Step {current} of {total}** — Please provide: **{label}**{ex}"

    def _doc_display_name(self) -> str:
        """Get display name for the current doc type."""
        if self.doc_type in DOCUMENT_SCHEMAS:
            return DOCUMENT_SCHEMAS[self.doc_type]["display_name"]
        try:
            return self._dynamic_fields[0].get("display_name", self.doc_type.replace("_", " ").title())
        except (IndexError, AttributeError):
            return self.doc_type.replace("_", " ").title()

    def _summarize(self) -> str:
        """All fields collected — show summary and ask confirmation."""
        self.state = "pending_generation"
        self.confirm_generation = True
        lines = [f"**{self._doc_display_name()}** — I have all the information needed.\n"]
        lines.append("Here's what you've provided:")
        for key, val in self.collected.items():
            label = key.replace("_", " ").title()
            lines.append(f"- **{label}**: {val}")
        lines.append("")
        lines.append("Shall I proceed to draft this document? (Yes / No)")
        return "\n".join(lines)

    def answer_field(self, answer: str) -> str:
        """
        Store the answer to the current field and move to the next.

        Returns:
            Next question or summary if all fields collected
        """
        return self.record_answer(answer)

    def record_answer(self, answer: str) -> str:
        """
        Store the answer to the current field and move to the next.

        Returns:
            Next question or summary if all fields collected
        """
        if self.state not in ("interviewing", "drafting"):
            return self._summarize()

        key = self.current_field
        if not key:
            return self._summarize()

        # Try to extract value after colon (in case user pastes "Step 2 of 7 ...")
        clean = re.sub(r"^\*\*Step \d+ of \d+\*\*.*?:\s*\*{0,2}", "", answer).strip()
        self.collected[key] = clean or answer.strip()
        self._field_index += 1
        return self._ask_next()

    @property
    def progress_pct(self) -> int:
        """Percentage of fields collected."""
        total = len(self._pending_fields)
        if total == 0:
            return 0
        return min(int(self._field_index / total * 100), 100)

    def get_draft_context(self) -> dict:
        """Return context dict for the document generator."""
        display_name = self._doc_display_name()
        schema = DOCUMENT_SCHEMAS.get(self.doc_type, {})
        return {
            "doc_type":      self.doc_type,
            "doc_family":    self.doc_family,
            "display_name":  display_name,
            "filled_fields": dict(self.collected),
            "days_to_respond": schema.get("days_to_respond"),
        }

    def add_supplementary_fields(self, fields: list):
        """Append extra fields discovered during intake (e.g., Triad questions)."""
        existing_keys = {f["key"] for f in self._pending_fields}
        new_fields = [f for f in fields if f["key"] not in existing_keys]
        if new_fields:
            self._supplementary.extend(new_fields)
            self._pending_fields.extend(new_fields)

    def reset(self):
        """Reset to idle state."""
        if getattr(self, "problem_description", None):
            self.last_problem_description = self.problem_description
        self._state_stack       = ["idle"]
        self._interrupt_ctx_stack = [{}]
        self.doc_type           = None
        self.doc_family         = None
        self.collected          = {}
        self.current_field      = None
        self._pending_fields    = []
        self._field_index       = 0
        self._supplementary     = []
        self.is_dynamic         = False
        self.problem_description = ""
        self.confirm_generation = False
        self.scrutiny_result    = None
        self.display_name       = ""
        self.pending_generation = False
        self.interrupted        = False


# ─────────────────────────────────────────────────────────────
# STATE STORE
# ─────────────────────────────────────────────────────────────

INTERVIEW_STATES: dict = {}  # session_id → InterviewState


def get_interview_state(session_id: str) -> InterviewState:
    """Get or create an InterviewState for a session."""
    if session_id not in INTERVIEW_STATES:
        INTERVIEW_STATES[session_id] = InterviewState()
    return INTERVIEW_STATES[session_id]


def clear_interview_state(session_id: str):
    """Reset interview state for a session."""
    state = INTERVIEW_STATES.get(session_id)
    if state:
        state.reset()


def check_draft_state(session_id: str) -> Optional[dict]:
    """
    Check if a session is in the middle of a draft.

    Returns:
        draft_context dict if drafting, None if idle
    """
    state = INTERVIEW_STATES.get(session_id)
    if state and state.state == "drafting":
        return state.get_draft_context()
    return None
