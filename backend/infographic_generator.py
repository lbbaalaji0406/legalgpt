"""
SAULGPT — INFOGRAPHIC & ORAL BRIEFING GENERATOR
================================================
Generates structured visual flowchart data and executive oral briefings (audio pills)
for Knowledge Mode and statutory inquiries under Indian Law.
"""

import re
from typing import Dict, Any, Optional, List


def extract_oral_briefing(text: str) -> str:
    """
    Extracts a crisp, executive oral summary strictly <= 3 sentences and <= 75 words.
    Suitable for zero-latency browser speech synthesis.
    """
    if not text:
        return ""

    # Clean markdown formatting, headers, tables, citations
    clean = re.sub(r'#+\s*', '', text)
    clean = re.sub(r'\*{1,3}', '', clean)
    clean = re.sub(r'`{1,3}.*?`{1,3}', '', clean, flags=re.DOTALL)
    clean = re.sub(r'\[.*?\]\(.*?\)', '', clean)
    clean = re.sub(r'\|.*?\|', '', clean)
    clean = re.sub(r'^\s*[-*•]\s*', '', clean, flags=re.MULTILINE)

    # Split into clean sentences
    raw_sentences = [
        s.strip() for s in re.split(r'(?<=[.!?])\s+', clean)
        if len(s.strip()) > 20
        and not s.strip().lower().startswith("disclaimer")
        and not "procedural guidance only" in s.strip().lower()
        and not "warning: this law has been replaced" in s.strip().lower()
    ]

    selected = raw_sentences[:3] if raw_sentences else ["Here is the statutory guidance based on Indian law."]
    briefing = " ".join(selected)

    # Enforce word limit <= 75 words
    words = briefing.split()
    if len(words) > 75:
        briefing = " ".join(words[:75]) + "."

    return briefing


def detect_and_build_infographic(query: str, response_text: str = "") -> Optional[Dict[str, Any]]:
    """
    Detects if the query or response pertains to a known statutory flowchart domain:
    1. Capital Gains Tax Reinvestment (Sec. 54, 54EC, 54F IT Act)
    2. New Criminal Laws Transition (IPC -> BNS, CrPC -> BNSS, IEA -> BSA)
    3. Negotiable Instruments Dishonour Workflow (Sec. 138 NI Act)
    Returns structured JSON flowchart nodes or None.
    """
    q = (query + " " + response_text).lower()

    # ── 1. Capital Gains Tax Exemption Flowchart ──
    if ("capital gain" in q or "sec 54" in q or "section 54" in q or "reinvest" in q or "sell a property" in q or "sale of property" in q) and ("tax" in q or "property" in q or "gain" in q):
        return {
            "type": "decision_tree",
            "title": "Capital Gains Tax Exemption Roadmap (Income Tax Act, 1961)",
            "statute": "Sections 54, 54EC & 54F",
            "root": {
                "title": "Sale of Capital Asset (LTCG Trigger)",
                "desc": "Long-Term Capital Gains realized on transfer of residential or other capital assets.",
                "badge": "LTCG Applicable"
            },
            "nodes": [
                {
                    "id": "sec54",
                    "title": "Section 54: Residential House Exemption",
                    "target_asset": "Residential House Property",
                    "time_limit": "Purchase within 1 yr before or 2 yrs after sale, OR construct within 3 yrs",
                    "statutory_cap": "Exemption capped at ₹10 Crore (Budget 2023 amendment)",
                    "eligible_investment": "New Residential House in India",
                    "status_badge": "Full LTCG Exemption",
                    "color": "#7EB8C4"
                },
                {
                    "id": "sec54ec",
                    "title": "Section 54EC: Specified Capital Gains Bonds",
                    "target_asset": "Any Long-Term Capital Asset (Land/Building)",
                    "time_limit": "Strictly within 6 MONTHS from date of transfer",
                    "statutory_cap": "Maximum ₹50 Lakhs limit per financial year",
                    "eligible_investment": "NHAI, REC, PFC, IRFC 5-Year Lock-in Bonds",
                    "status_badge": "Bond Exemption",
                    "color": "#C9A84C"
                },
                {
                    "id": "sec54f",
                    "title": "Section 54F: Non-Residential to Residential",
                    "target_asset": "Any Asset OTHER than Residential House (Plots, Gold, Shares)",
                    "time_limit": "Reinvest ENTIRE Net Consideration within 2 yrs (purchase) or 3 yrs (construct)",
                    "statutory_cap": "Capped at ₹10 Crore; Assessee must not own >1 house on transfer date",
                    "eligible_investment": "One New Residential House in India",
                    "status_badge": "Proportionate Exemption",
                    "color": "#A8C49A"
                }
            ],
            "provisos": [
                "Deposit in Capital Gains Account Scheme (CGAS) before ITR due date if funds unutilized.",
                "Lock-in period of 3 years on new residential house; violation revokes exemption."
            ]
        }

    # ── 2. New Criminal Laws (IPC -> BNS / CrPC -> BNSS / IEA -> BSA) ──
    if ("bns" in q or "ipc" in q or "crpc" in q or "bnss" in q or "bsa" in q or "bharatiya nyaya" in q or "cheating" in q or "fir" in q or "theft" in q or "criminal" in q):
        return {
            "type": "transition_matrix",
            "title": "Statutory Transition Roadmap: Legacy Acts → 2023 Sanhitas",
            "statute": "BNS, 2023 · BNSS, 2023 · BSA, 2023",
            "root": {
                "title": "Offence / Procedure Transition Grid (In effect from 1 July 2024)",
                "desc": "Statutory concordance between repealed colonial codes and enacted reform statutes.",
                "badge": "Statutory Transition"
            },
            "nodes": [
                {
                    "id": "cheating",
                    "title": "Cheating & Dishonestly Inducing Delivery",
                    "legacy_law": "IPC Section 420",
                    "enacted_law": "BNS Section 318(4)",
                    "punishment": "Imprisonment up to 7 years + fine",
                    "key_change": "Clearer definition of digital transactions and fraudulent misrepresentation",
                    "color": "#C9A84C"
                },
                {
                    "id": "theft",
                    "title": "Theft & Snatching Offence",
                    "legacy_law": "IPC Sections 378 & 379",
                    "enacted_law": "BNS Section 303 & Section 304",
                    "punishment": "Up to 3 years; Community service for first offence where value < ₹5,000",
                    "key_change": "Introduced Community Service as alternative punishment under Section 4(f)",
                    "color": "#7EB8C4"
                },
                {
                    "id": "efir",
                    "title": "Electronic FIR & Zero-FIR Mandate",
                    "legacy_law": "CrPC Section 154",
                    "enacted_law": "BNSS Section 173",
                    "punishment": "Mandatory registration across jurisdictions",
                    "key_change": "Zero-FIR statutory right; e-FIR must be signed by complainant within 3 days",
                    "color": "#A8C49A"
                },
                {
                    "id": "evidence",
                    "title": "Electronic Evidence Admissibility",
                    "legacy_law": "IEA Section 65B",
                    "enacted_law": "BSA Section 63",
                    "punishment": "Court Admissibility Requirement",
                    "key_change": "Schedule Two-Part Certificate (Part A Custodian + Part B Technical Expert)",
                    "color": "#C44A4A"
                }
            ],
            "provisos": [
                "Article 20(1) Constitution prevents ex-post facto prosecution: Offences committed prior to 1 July 2024 remain governed by IPC/CrPC.",
                "Electronic records require Section 63 BSA certificate with SHA-256 hash match."
            ]
        }

    return None
