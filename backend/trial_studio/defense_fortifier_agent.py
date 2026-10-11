"""
SAULGPT TRIAL STUDIO — DEFENSE STRATEGIST AGENT (THE CORNER COACH)
===================================================================
Persona: Chief Trial Strategist & Witness Defense Coach.
Focus: Fortifies vulnerabilities before filing and coaches witnesses through live cross-examination sparring.

MULTI-TURN WITNESS PREPARATION MANDATE:
Turn 1: Master Pre-Trial Defense Brief (Audit, Rejoinder Script, Evidentiary Checklist).
Turn 2+: Interactive Witness Coaching (Admission Audits, Live Exposure Recalculation,
         Verbatim Rejoinder Scripts, and Section 146 BSA Objections for Counsel).
"""

import os
import re
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from groq import Groq

from .schema import AdversarialTurnResponse
from .precedent_engine import get_precedent_engine, get_act_role_matrix

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class DefenseStrategistAgent:
    _client = None

    def __init__(self):
        self.precedent_engine = get_precedent_engine()

    @classmethod
    def _get_client(cls) -> Optional[Groq]:
        if cls._client is None:
            api_key = os.getenv("GROQ_API_KEY", "")
            if api_key:
                cls._client = Groq(api_key=api_key)
        return cls._client

    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 400) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None

        primary_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        fallback_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

        for model in [primary_model] + fallback_models:
            try:
                res = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=max_tokens
                )
                content = res.choices[0].message.content.strip()
                if content:
                    return content
            except Exception as e:
                print(f"[DefenseStrategistAgent] Model {model} call failed: {e}")
        return None

    def generate_defense_fortification(
        self,
        scenario: str,
        witness_role: str = "accused",
        grounded_evidence: Optional[Dict[str, Any]] = None,
        act_hint: Optional[str] = None
    ) -> AdversarialTurnResponse:
        """
        Generates the 3-part tactical defense brief (Turn 1) tailored to the witness's role.
        """
        analysis = self.precedent_engine.analyze_vulnerabilities(
            scenario=scenario,
            grounded_evidence=grounded_evidence,
            act_hint=act_hint
        )

        fatal_flaw = analysis["fatal_flaw"]
        vuln_score = analysis["vulnerability_score"]
        precedent = analysis["controlling_precedent"]
        vuln_tag = precedent.get("vulnerability_tag", "")
        matched_act = analysis.get("matched_act", "Indian Law")

        ev_context = ""
        if grounded_evidence:
            ev_type = grounded_evidence.get("evidence_type", "document")
            ev_hash = grounded_evidence.get("sha256_hash", "")[:12]
            ev_context = f"Available Evidence: {ev_type} (Hash: {ev_hash}, BSA 63 Certified: {grounded_evidence.get('sec63_bsa_certified', False)})."

        role_matrix = get_act_role_matrix(
            matched_act=matched_act,
            witness_role=witness_role,
            scenario=scenario,
            fatal_flaw=fatal_flaw,
            precedent=precedent
        )
        role_directives = role_matrix["defense_strategy"]

        system_prompt = (
            "You are a Senior Indian Trial Defense Strategist and Evidence Counsel.\n"
            f"{role_directives}\n\n"
            "Generate a crisp 3-part tactical defense brief:\n"
            "1. VULNERABILITY AUDIT (2 sentences identifying opponent's attack vector under controlling precedent)\n"
            "2. WITNESS REJOINDER SCRIPT (verbatim 2-3 sentence answer the witness should memorize for the stand)\n"
            "3. PRE-TRIAL EVIDENTIARY CHECKLIST (3 bullet points of concrete filings, bank slips, certificates, or affidavits to submit)"
        )

        user_prompt = (
            f"GOVERNING ACT: {matched_act}\n"
            f"CASE MATRIX: {scenario}\n"
            f"WITNESS ON STAND: {role_matrix['witness_title']}\n"
            f"OPPOSING COUNSEL: {role_matrix['opposing_counsel_title']}\n"
            f"VULNERABILITY DETECTED: {role_matrix['case_vuln']}\n"
            f"CONTROLLING PRECEDENT: {precedent.get('title')} ({precedent.get('citation')}) - Ratio: {role_matrix['precedent_ratio']}\n"
            f"{ev_context}\n\n"
            "Produce the structured defense brief now:"
        )

        raw_llm = self._call_llm(system_prompt, user_prompt, max_tokens=350)
        if raw_llm and len(raw_llm.strip()) > 80:
            content = raw_llm.strip()
        else:
            # Fallback template
            if witness_role == "accused":
                rejoinder = (
                    'Instruct the witness to state firmly: "I admit my signature on the cheque, but deny that any consideration was ever received. '
                    'Under Rangappa v. Sri Mohan and Basalingappa v. Mudibasappa, the burden shifts to the complainant to establish financial capacity, '
                    'which is completely unproven due to the absence of bank withdrawal slips or ITR disclosures."'
                )
                checklist = [
                    "File notice to summon Complainant's Income Tax Returns and bank statements for the relevant period",
                    "Move application under Section 146 BSA to cross-examine complainant on financial capacity",
                    "Submit memo on rebuttal of Section 139 presumption on preponderance of probabilities"
                ]
            elif vuln_tag == "want_of_consideration_sec25" or "consideration" in fatal_flaw.lower():
                rejoinder = (
                    'Instruct the witness to state firmly: "The loan was disbursed in cash from accounted business withdrawals and family capital, '
                    'which is reflected in our contemporaneous business accounts. Under Section 118 of the Negotiable Instruments Act and Section 91/92 IEA '
                    '(Sec 94/95 BSA), the execution of the formal Promissory Note creates a statutory presumption that consideration passed, '
                    'which cannot be negated by mere oral denial without documentary proof."'
                )
                checklist = [
                    "File original Promissory Note and Loan Agreement bearing respondent's admitted signature",
                    "Place on record certified bank statements of that month corroborating cash availability",
                    "Submit Section 118 / Section 139 statutory presumption memo shifting burden to the borrower"
                ]
            else:
                rejoinder = (
                    'Instruct the witness to state firmly: "The contractual obligations were performed in good faith according to standard trade usage. '
                    'Every assertion is corroborated by contemporaneous email confirmations and WhatsApp communications on record."'
                )
                checklist = [
                    "Compile chronologically indexed master documents bundle with Section 63 BSA certificate",
                    "Issue interrogatories under Order XI Rule 1 CPC to compel respondent's admissions",
                    "File evidence affidavit adhering strictly to pleaded facts"
                ]

            content = (
                f"**1. VULNERABILITY AUDIT**:\n"
                f"Your trial exposure centers on: *{fatal_flaw}*. "
                f"Opposing counsel will invoke *{precedent['title']}* ({precedent['citation']}) to dispute consideration or corroboration.\n\n"
                f"**2. WITNESS REJOINDER SCRIPT**:\n"
                f"{rejoinder}\n\n"
                f"**3. PRE-TRIAL EVIDENTIARY CHECKLIST**:\n" +
                "\n".join([f"• {item}" for item in checklist])
            )

        # Extract rejoinder if present in LLM content
        extracted_rejoinder = None
        if "WITNESS REJOINDER SCRIPT" in content:
            parts = content.split("WITNESS REJOINDER SCRIPT")
            if len(parts) > 1:
                sub = parts[1].split("**3.")[0].split("3.")[0].strip(":* \n")
                if len(sub) > 10:
                    extracted_rejoinder = sub.split("\n")[0].strip('"\' ')
        
        if not extracted_rejoinder:
            extracted_rejoinder = (
                rejoinder if 'rejoinder' in locals() 
                else f"Maintain consistent adherence to pleaded defense and demand primary proof under {matched_act}."
            )

        coach_advice = {
            "audit_critique": f"Target vulnerability: {role_matrix['case_vuln']}. Opponent relies on {precedent.get('title', 'Precedents')} ({precedent.get('citation', '')}).",
            "optimized_rejoinder": extracted_rejoinder,
            "counsel_objection": f"Ready to object under Section 146 BSA if opposing counsel assumes facts not in evidence or violates {matched_act}.",
            "evidentiary_plug": checklist[0] if 'checklist' in locals() and checklist else f"Place primary documents and Section 63 BSA certificate on record under {matched_act}.",
            "exposure_delta": -15
        }

        return AdversarialTurnResponse(
            mode="defense_fortifier",
            turn_index=1,
            interrogation_content=content,
            vulnerability_score=max(vuln_score - 15, 10),
            vulnerability_delta=-15,
            fatal_flaw_detected=fatal_flaw,
            precedent_backing=precedent,
            suggested_statutory_motions=analysis["suggested_motions"],
            coach_advice=coach_advice
        )

    def generate_defense_rejoinder_turn(
        self,
        scenario: str,
        previous_brief_or_question: str,
        witness_answer: str,
        current_score: int,
        turn_index: int,
        witness_role: str = "accused",
        grounded_evidence: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> AdversarialTurnResponse:
        """
        Interactive Witness Coaching Turn (Turn 2+).
        Audits the witness's practice answer for accidental leaks or fatal admissions,
        recalculates exposure in real-time, provides verbatim optimized rejoinder scripts,
        and equips counsel with Section 146 BSA procedural objections.
        """
        analysis = self.precedent_engine.analyze_vulnerabilities(scenario, grounded_evidence)
        precedent = analysis["controlling_precedent"]
        matched_act = analysis.get("matched_act", "Indian Law")

        ev_context = ""
        if grounded_evidence:
            ev_type = grounded_evidence.get("evidence_type", "document")
            ev_hash = grounded_evidence.get("sha256_hash", "")[:12]
            ev_context = f"Evidence in file: {ev_type} (SHA-256: {ev_hash})."

        role_matrix = get_act_role_matrix(
            matched_act=matched_act,
            witness_role=witness_role,
            scenario=scenario,
            precedent=precedent
        )
        role_directives = role_matrix["defense_strategy"]

        system_prompt = (
            "You are a master Indian Defense Trial Strategist and Witness Corner Coach.\n"
            f"{role_directives}\n\n"
            "The witness (your client) is practicing their testimony against aggressive cross-examination.\n"
            "Your job is to audit their answer, protect them from self-incrimination, provide a polished rejoinder, "
            "and give counsel a formal evidentiary objection under the Bharatiya Sakshya Adhiniyam, 2023 (BSA).\n\n"
            "OUTPUT FORMAT: Return a valid JSON object with EXACTLY these keys:\n"
            "{\n"
            "  \"exposure_delta\": <integer from -25 to +20, negative if witness answered well and lowered exposure, positive if they wavered or admitted a gap>,\n"
            "  \"audit_critique\": \"<1-2 sentences evaluating the witness's practice answer: did they accidentally concede a gap, waver, or speak too loosely?>\",\n"
            "  \"optimized_rejoinder\": \"<verbatim 2-sentence script for the witness to say firmly on the stand under oath, turning the opponent's pressure into an affirmative statutory defense>\",\n"
            "  \"counsel_objection\": \"<formal Section 146 BSA / Evidence Act objection for defending advocate to raise in court, e.g. 'Objection under Section 146 BSA: Question assumes facts not in evidence...'>\",\n"
            "  \"evidentiary_plug\": \"<concrete documentary filing, passbook entry, or Section 63 BSA certificate to tender to close this loophole>\"\n"
            "}"
        )

        user_prompt = (
            f"GOVERNING ACT: {matched_act}\n"
            f"CASE MATRIX: {scenario}\n"
            f"WITNESS ON STAND: {role_matrix['witness_title']}\n"
            f"OPPOSING COUNSEL: {role_matrix['opposing_counsel_title']}\n"
            f"CONTROLLING PRECEDENT: {precedent.get('title')} ({precedent.get('citation')}) - Ratio: {role_matrix['precedent_ratio']}\n"
            f"{ev_context}\n\n"
            f"LAST POINT / QUESTION POSED: {previous_brief_or_question}\n"
            f"WITNESS'S PRACTICE ANSWER: \"{witness_answer}\"\n"
            f"CURRENT EXPOSURE SCORE: {current_score}%\n\n"
            "Deliver your tactical coaching assessment in JSON format:"
        )

        delta = -10
        critique = "Witness maintained core position, but needs tighter phrasing to avoid cross-examination traps."
        optimized_rejoinder = (
            "Under Section 118 NI Act / Section 91/92 IEA (Sec 94/95 BSA), the admitted signature on the agreement "
            "creates a statutory presumption of consideration. The financial availability of funds is corroborated by contemporaneous business accounts."
        )
        counsel_objection = (
            "Objection under Section 146 BSA: Opposing counsel is asking misleading questions regarding oral cash transactions "
            "when a written instrument with an admitted signature is already on record."
        )
        plug = "File certified bank withdrawal summary and business cash ledger entry for that month."

        raw_llm = self._call_llm(system_prompt, user_prompt, max_tokens=400)
        if raw_llm:
            try:
                m = re.search(r'\{[\s\S]*\}', raw_llm)
                json_str = m.group(0) if m else raw_llm
                data = json.loads(json_str)
                delta = int(data.get("exposure_delta", -10))
                critique = data.get("audit_critique", critique)
                optimized_rejoinder = data.get("optimized_rejoinder", optimized_rejoinder)
                counsel_objection = data.get("counsel_objection", counsel_objection)
                plug = data.get("evidentiary_plug", plug)
            except Exception as e:
                print(f"[DefenseStrategistAgent] JSON parse error: {e}")

        new_score = min(max(current_score + delta, 10), 90)

        formatted_content = (
            f"🛡️ **WITNESS TESTIMONY AUDIT**:\n"
            f"{critique}\n\n"
            f"🗣️ **OPTIMIZED WITNESS REJOINDER (Memorize for the Stand)**:\n"
            f'"{optimized_rejoinder}"\n\n'
            f"⚖️ **DEFENSE COUNSEL'S OBJECTION (Sec. 146 BSA)**:\n"
            f'"{counsel_objection}"\n\n'
            f"📁 **EVIDENTIARY PLUG**:\n"
            f"• {plug}"
        )

        coach_advice = {
            "audit_critique": critique,
            "optimized_rejoinder": optimized_rejoinder,
            "counsel_objection": counsel_objection,
            "evidentiary_plug": plug,
            "exposure_delta": delta
        }

        return AdversarialTurnResponse(
            mode="defense_fortifier",
            turn_index=turn_index,
            interrogation_content=formatted_content,
            vulnerability_score=new_score,
            vulnerability_delta=delta,
            fatal_flaw_detected=critique,
            precedent_backing=precedent,
            suggested_statutory_motions=[counsel_objection, plug],
            coach_advice=coach_advice
        )
