"""
SAULGPT TRIAL STUDIO — HOSTILE CROSS-EXAMINER AGENT (THE STRIKER)
==================================================================
Persona: Ruthless Adverse Trial Advocate conducting cross-examination under:
- Section 146 Bharatiya Sakshya Adhiniyam, 2023 (BSA) / Section 143 Indian Evidence Act, 1872 (IEA) — Leading Questions.
- Section 148 BSA / Section 145 IEA — Cross-Examination as to Previous Statements in Writing.
- Section 158 BSA / Section 155 IEA — Impeaching Credit of Witness.

STRICT COURTROOM BREVITY & PROGRESSIVE ENTRAPMENT MANDATE:
- Exactly 1 leading question per turn.
- Under 50 words total.
- ZERO conversational filler, zero throat-clearing, zero lectures.
- Anti-repetition memory: Never repeat questions or loop.
- Multi-vector progressive attack: Factual delivery -> Bank trail -> Tax compliance (Sec 269SS IT Act) -> Contemporaneous conduct -> Statutory checkmate.
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


class HostileCrossExaminerAgent:
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

    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 250) -> Optional[str]:
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
                    temperature=0.15,
                    max_tokens=max_tokens
                )
                content = res.choices[0].message.content.strip()
                if content:
                    return content
            except Exception as e:
                print(f"[CrossExaminerAgent] Model {model} call failed: {e}")
        return None

    def generate_opening_attack(
        self,
        scenario: str,
        witness_role: str = "accused",
        grounded_evidence: Optional[Dict[str, Any]] = None,
        act_hint: Optional[str] = None
    ) -> AdversarialTurnResponse:
        """
        Formulates the lethal opening line of cross-examination tailored to the witness's exact role.
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
            ev_context = f"Grounded Evidence on Record: {ev_type} (Hash: {ev_hash}). Certificate status: {grounded_evidence.get('sec63_bsa_certified', False)}."

        role_matrix = get_act_role_matrix(
            matched_act=matched_act,
            witness_role=witness_role,
            scenario=scenario,
            fatal_flaw=fatal_flaw,
            precedent=precedent
        )

        role_directives = role_matrix["attack_strategy"]
        case_vuln = role_matrix["case_vuln"]
        case_precedent_ratio = role_matrix["precedent_ratio"]

        system_prompt = (
            "You are an elite Indian Trial Advocate conducting adverse cross-examination under Section 146 BSA (Section 143 IEA).\n"
            "MANDATE: Output EXACTLY 1 leading question. Maximum 45 words. Zero pleasantries, zero filler.\n"
            "Demand an affirmative or trapped answer (e.g., 'Is it not a fact that...', 'Isn't it true that...', 'You cannot produce any...').\n\n"
            f"{role_directives}"
        )

        user_prompt = (
            f"GOVERNING ACT: {matched_act}\n"
            f"CASE FACTS: {scenario}\n"
            f"WITNESS ON STAND: {role_matrix['witness_title']}\n"
            f"OPPOSING COUNSEL: {role_matrix['opposing_counsel_title']}\n"
            f"CORE VULNERABILITY TO EXPLOIT: {case_vuln}\n"
            f"CONTROLLING PRECEDENT RATIO: {case_precedent_ratio}\n"
            f"{ev_context}\n\n"
            "Generate the lethal opening leading question now:"
        )

        question = None
        raw_llm = self._call_llm(system_prompt, user_prompt, max_tokens=100)
        if raw_llm:
            clean_q = re.sub(r'^(question|advocate|cross-examiner):\s*', '', raw_llm, flags=re.I).strip('"\' \n')
            if clean_q and len(clean_q.split()) <= 55 and clean_q.endswith("?"):
                question = clean_q

        # Fallback template if LLM is unavailable
        if not question:
            if witness_role == "accused":
                question = (
                    "You admit that the signature on this ₹15 Lakh cheque is yours, so isn't it a fact "
                    "that you issued it towards the discharge of your admitted legal liability?"
                )
            elif vuln_tag == "want_of_consideration_sec25" or "consideration" in fatal_flaw.lower():
                question = (
                    "You claim to have advanced ₹15 Lakhs in cash, but is it not a fact that you cannot produce "
                    "any bank withdrawal slip showing that amount was ever withdrawn on that date?"
                )
            elif vuln_tag == "cash_loan_itr_gap" or "cash" in fatal_flaw.lower():
                question = (
                    "Is it not true that you cannot produce any Income Tax Return showing this cash loan, "
                    "nor any bank withdrawal slip for the date in question?"
                )
            elif vuln_tag == "sec_63_bsa_failure" or "electronic" in fatal_flaw.lower():
                question = (
                    "Can you point to a single certificate under Section 63 BSA signed by the system administrator, "
                    "or did you simply print these electronic screenshots yourself?"
                )
            elif vuln_tag == "sec_38_2_c_expert_defect_gap" or "defect" in fatal_flaw.lower():
                question = (
                    "Is it correct that you never applied to have the component tested by an accredited laboratory under Section 38(2)(c) "
                    "before demanding a full replacement?"
                )
            elif vuln_tag == "liquidated_damages_unproved_loss" or "penalty" in fatal_flaw.lower():
                question = (
                    "Did your company place on record any audited balance sheet showing actual financial loss, "
                    "or did you forfeit the entire deposit purely as a penalty clause?"
                )
            elif vuln_tag == "limitation_clock_reset_sec18" or "limitation" in fatal_flaw.lower():
                question = (
                    "Isn't it a fact that more than three years elapsed before this claim was filed, "
                    "and you hold no signed written acknowledgment resetting the limitation clock?"
                )
            elif vuln_tag == "unilateral_arbitrator_appointment":
                question = (
                    "Is it not admitted that the sole arbitrator was appointed unilaterally by your Managing Director, "
                    "in direct violation of Section 12(5) of the Arbitration Act?"
                )
            else:
                turning_q = precedent.get("turning_point", {}).get("cross_question")
                if turning_q and len(turning_q.split()) <= 45:
                    question = turning_q
                else:
                    question = (
                        "Did you tender any contemporaneous written record of this agreement, "
                        "or does your entire claim rest upon uncorroborated oral assertions?"
                    )

        return AdversarialTurnResponse(
            mode="cross_examiner",
            turn_index=1,
            interrogation_content=question,
            vulnerability_score=vuln_score,
            vulnerability_delta=0,
            fatal_flaw_detected=fatal_flaw,
            precedent_backing=precedent,
            suggested_statutory_motions=analysis["suggested_motions"]
        )

    def generate_follow_up(
        self,
        scenario: str,
        previous_question: str,
        witness_answer: str,
        current_score: int,
        turn_index: int,
        witness_role: str = "accused",
        grounded_evidence: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> AdversarialTurnResponse:
        """
        Evaluates the witness's response dynamically using Groq LLM and the 50,000 precedent engine.
        Enforces progressive entrapment, anti-repetition memory, courtroom brevity, and role fidelity.
        """
        analysis = self.precedent_engine.analyze_vulnerabilities(scenario, grounded_evidence)
        precedent = analysis["controlling_precedent"]
        matched_act = analysis.get("matched_act", "Indian Law")

        # Collect past questions from history to guarantee anti-repetition
        past_questions = []
        if history:
            for item in history:
                if isinstance(item, dict):
                    q = item.get("interrogation_content") or item.get("turn_response", {}).get("interrogation_content")
                    if q:
                        past_questions.append(q)
        if previous_question and previous_question not in past_questions:
            past_questions.append(previous_question)

        past_questions_formatted = "\n".join([f"- Turn {i+1}: {q}" for i, q in enumerate(past_questions)])

        ev_context = ""
        if grounded_evidence:
            ev_type = grounded_evidence.get("evidence_type", "document")
            ev_hash = grounded_evidence.get("sha256_hash", "")[:12]
            clock = grounded_evidence.get("statutory_clock", {})
            ev_context = f"Evidence on record: {ev_type} (SHA-256: {ev_hash}, Clock: {clock.get('days_remaining', 'N/A')} days)."

        role_matrix = get_act_role_matrix(
            matched_act=matched_act,
            witness_role=witness_role,
            scenario=scenario,
            precedent=precedent
        )
        role_directives = role_matrix["attack_strategy"]

        system_prompt = (
            "You are a ruthless, brilliant Indian Trial Advocate conducting hostile cross-examination under Section 146 BSA (Section 143 IEA).\n"
            "You are in trial against an adverse witness. Your goal is progressive entrapment and destruction of their credibility.\n\n"
            f"{role_directives}\n\n"
            "STRICT RULES:\n"
            "1. Output ONLY a valid JSON object with keys:\n"
            "   - 'witness_analysis': One short sentence evaluating the witness's reaction (e.g. admitted gap, stonewalled, evaded with legal presumption, wavered).\n"
            "   - 'vulnerability_delta': Integer between -15 and +25 reflecting trial impact (positive if witness conceded or evaded; negative if witness stood firm with proof).\n"
            "   - 'exposed_flaw': Concise phrase summarizing the fatal gap pinned on the witness.\n"
            "   - 'follow_up_question': Exactly 1 leading question. Maximum 45 words. Punchy, aggressive, direct courtroom phrasing.\n"
            "2. ANTI-REPETITION MANDATE: NEVER repeat any previous question, wording, or canvassed point. Advance to the next vector.\n"
            "3. Zero conversational filler, zero throat-clearing. Start the question directly with 'Is it not true...', 'Did you...', 'Can you produce...', etc."
        )

        user_prompt = (
            f"GOVERNING ACT: {matched_act}\n"
            f"CASE MATRIX: {scenario}\n"
            f"WITNESS ON STAND: {role_matrix['witness_title']}\n"
            f"OPPOSING COUNSEL: {role_matrix['opposing_counsel_title']}\n"
            f"CONTROLLING PRECEDENT: {precedent.get('title')} ({precedent.get('citation')}) - Ratio: {precedent.get('ratio_decidendi')}\n"
            f"{ev_context}\n\n"
            f"ALL PREVIOUS QUESTIONS ASKED (DO NOT REPEAT):\n{past_questions_formatted}\n\n"
            f"IMMEDIATE PREVIOUS QUESTION: {previous_question}\n"
            f"WITNESS TESTIMONY UNDER OATH: \"{witness_answer}\"\n"
            f"CURRENT VULNERABILITY SCORE: {current_score}%\n"
            f"CURRENT TURN: {turn_index}\n\n"
            "Generate the next attack turn in JSON format:"
        )

        follow_up = None
        delta = 0
        implication = "Witness maintained position under cross-examination."

        raw_llm = self._call_llm(system_prompt, user_prompt, max_tokens=300)
        if raw_llm:
            try:
                # Try parsing JSON directly or regex
                json_str = raw_llm
                m = re.search(r'\{[\s\S]*\}', raw_llm)
                if m:
                    json_str = m.group(0)
                data = json.loads(json_str)
                q_candidate = data.get("follow_up_question", "").strip()
                if q_candidate and len(q_candidate.split()) <= 55:
                    follow_up = q_candidate
                    delta = int(data.get("vulnerability_delta", 0))
                    implication = data.get("exposed_flaw") or data.get("witness_analysis") or implication
            except Exception as e:
                print(f"[CrossExaminerAgent] JSON parse error: {e}, raw: {raw_llm[:100]}")

        # Fallback heuristic if LLM call or parse failed
        if not follow_up:
            ans_lower = witness_answer.lower()
            if any(term in ans_lower for term in ["139", "presumption", "bir singh", "section 20", "signed"]):
                follow_up = (
                    "I am not asking about statutory presumptions. Can you produce a single bank statement showing "
                    "a withdrawal of ₹15 Lakhs on that date, or did you hold no such funds in any account?"
                )
                delta = +10
                implication = "Witness evaded factual banking trail by citing statutory presumption."
            elif any(term in ans_lower for term in ["savings", "cash in hand", "business", "friend"]):
                follow_up = (
                    "Did you declare this alleged cash advance of ₹15 Lakhs in your Income Tax Returns for that financial year "
                    "as mandated by Section 269SS of the Income Tax Act? Yes or no?"
                )
                delta = +15
                implication = "Witness admitted unbanked cash loan violating Section 269SS Income Tax Act."
            elif any(term in ans_lower for term in ["no", "cannot", "didn't", "not have"]):
                follow_up = (
                    "Having admitted there are no bank withdrawals and no ITR declarations, isn't it a fact that "
                    "no consideration ever passed, rendering this document void under Section 25 of the Contract Act?"
                )
                delta = +20
                implication = "Witness conceded lack of primary documentary proof of cash consideration."
            else:
                follow_up = (
                    "I put it to you that your refusal to produce contemporaneous financial records demonstrates "
                    "that this entire cash loan assertion is a post-facto fabrication. What do you say?"
                )
                delta = +5
                implication = "Witness evasive on key evidentiary inquiries."

        new_score = min(max(current_score + delta, 10), 95)

        return AdversarialTurnResponse(
            mode="cross_examiner",
            turn_index=turn_index,
            interrogation_content=follow_up,
            vulnerability_score=new_score,
            vulnerability_delta=delta,
            fatal_flaw_detected=implication,
            precedent_backing=precedent,
            suggested_statutory_motions=analysis["suggested_motions"]
        )
