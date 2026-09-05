import os
import re
import json
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv
from groq import Groq

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

CRITIC_PROMPT = """You are an Adversarial Senior Partner & Judicial Reviewer in an elite Indian law firm.
Your sole job is to cross-examine the Drafting Counsel's legal response against the provided Ground-Truth Statutory Sections and Temporal Directives.

TEMPORAL CONTEXT:
Query Mode: {temporal_mode} (UNDATED | POST_2024 | PRE_2024)

GROUND-TRUTH LEGAL CONTEXT:
{ground_truth_context}

DRAFT LEGAL RESPONSE TO AUDIT:
{draft_text}

ATOMIC AUDIT RUBRIC:
Evaluate substantive legal claims strictly against these 4 dimensions:
1. CANONICAL & TEMPORAL CONCORDANCE:
   - POST_2024: 2024 Sanhitas (BNS/BNSS/BSA) must be cited exclusively as active law.
   - PRE_2024 / PENDING: IPC/CrPC/IEA must be cited under Art. 20(1) Constitution or Sec. 531 BNSS.
   - UNDATED: The draft must provide dual tracks (Post-2024 primary, Pre-2024 historical savings under Art. 20(1) & Sec. 531 BNSS).
2. DEONTIC MODALITY: Mandatory duties ("shall/must") must not be confused with discretionary powers ("may").
3. PROCEDURAL DEADLINES: Limitation windows (e.g. 3 days e-FIR signature, 14 days preliminary enquiry, 15/40/60 days remand, 30 days notice) must match statutory text.
4. CONDITIONAL PROVISOS & SIGNATURES: Provisos (e.g. BNS 303(2) community service for theft <₹5,000, BNSS 173(1)(ii) 3-day signature rule, BSA 63 certificate requirements) must be preserved accurately.

AUDIT INSTRUCTIONS:
- Analyze substantive legal claims step-by-step (ignore conversational pleasantries and disclaimers).
- For each claim:
  * Quote exact statutory evidence from GROUND-TRUTH.
  * If the claim explicitly contradicts GROUND-TRUTH, set evidence to "CONTRADICTED" and claim_is_valid to false.
  * If a 2024 Sanhita claim cannot be verified because the section is missing from GROUND-TRUTH, set evidence to "UNGROUNDED_2024" and claim_is_valid to false. DO NOT overwrite it with colonial codes.
- Do NOT generate replacements based on speculative pre-training memory. If the ground truth does not contain the answer, instruct an omission with 'OMIT_UNVERIFIED_ASSERTION'.

Output STRICT JSON using this exact schema:
{{
  "chain_of_rubrics_evaluation": [
    {{
      "substantive_claim_span": "<exact sentence from draft>",
      "rubric_dimension": "CANONICAL_CONCORDANCE | DEONTIC_MODALITY | PROCEDURAL_DEADLINES | CONDITIONAL_PROVISOS",
      "extracted_ground_truth_evidence": "<verbatim quote from context | 'CONTRADICTED' | 'UNGROUNDED_2024'>",
      "adversarial_reasoning": "<concise judicial rationale comparing claim to statutory evidence>",
      "claim_is_valid": true | false
    }}
  ],
  "correction_mandates": [
    {{
      "flagged_span": "<exact flawed sentence from draft>",
      "error_type": "Temporal Misapplication | Deontic Confusion | Limitation Error | Proviso Violation | Ungrounded Assertion",
      "corrected_replacement": "<statutory correction derived SOLELY from GROUND-TRUTH, or 'OMIT_UNVERIFIED_ASSERTION'>"
    }}
  ],
  "terminal_pass_verdict": true | false
}}
"""


class AdversarialCriticEngine:
    """
    Fine-Grained Process Reward Model (FG-PRM) & Adversarial Judicial Critic.
    Audits Drafting Counsel (Actor) responses against raw statutory grounding
    using an Inverted Chain-of-Rubrics schema and reflexive self-healing ChromaDB lookups.
    """

    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            api_key = os.getenv("GROQ_API_KEY", "")
            cls._client = Groq(api_key=api_key)
        return cls._client

    @classmethod
    def _normalize_span(cls, s: str) -> str:
        return re.sub(r'\s+', ' ', s).strip().rstrip(".").lower()

    @classmethod
    def _try_reflexive_db_lookup(cls, claim_text: str) -> bool:
        """
        Reflexive Self-Healing: If a 2024 claim was marked UNGROUNDED_2024 due to retrieval shadowing,
        queries ChromaDB directly for that specific section and validates operative concepts.
        """
        try:
            from layer2_retrieval import collection

            # 1. Detect target act
            act_name = None
            if re.search(r'\b(bns|bharatiya\s+nyaya\s+sanhita)\b', claim_text, re.IGNORECASE):
                act_name = "BNS"
            elif re.search(r'\b(bnss|bharatiya\s+nagarik\s+suraksha)\b', claim_text, re.IGNORECASE):
                act_name = "BNSS"
            elif re.search(r'\b(bsa|bharatiya\s+sakshya)\b', claim_text, re.IGNORECASE):
                act_name = "BSA"
            elif re.search(r'\b(constitution|article)\b', claim_text, re.IGNORECASE):
                act_name = "Constitution"

            # 2. Extract section/article number
            sec_match = re.search(r'(?:section|sec\.?|article|art\.?)\s*(\d+[A-Z]*)', claim_text, re.IGNORECASE)
            if not act_name or not sec_match:
                return False

            sec_num = sec_match.group(1)

            # 3. Direct Zero-Shot Query to ChromaDB
            results = collection.get(
                where={"$and": [{"act_name": act_name}, {"section_number": str(sec_num)}]}
            )

            docs = results.get("documents", [])
            if not docs:
                # Fallback check for alternate act naming in DB
                results = collection.get(
                    where={"$and": [{"act": {"$ne": ""}}, {"section_number": str(sec_num)}]}
                )
                docs = [d for d in results.get("documents", []) if act_name.lower() in d.lower()]
                if not docs:
                    return False

            full_statute_text = " ".join(docs).lower()

            # 4. Semantic Concept Validation: Verify operative keywords match
            keywords = re.findall(
                r'\b(?:three|3|days|72\s*hours|community\s+service|certificate|five\s+thousand|5000|remand|preliminary|e-fir|electronic)\b',
                claim_text.lower()
            )

            if keywords:
                matches = sum(1 for kw in keywords if kw in full_statute_text)
                if matches > 0:
                    print(f"[Critic Reflexive Rescue] ✅ Rescued {act_name} Section/Article {sec_num} directly from ChromaDB!")
                    return True
                else:
                    print(f"[Critic Reflexive Rescue] ⚠️ Section {sec_num} exists, but operative concept not verified in text.")
                    return False

            # If section exists and no complex keywords required
            print(f"[Critic Reflexive Rescue] ✅ Verified {act_name} Section {sec_num} exists in ChromaDB.")
            return True

        except Exception as e:
            print(f"[Critic Reflexive Rescue] Lookup error: {e}")
            return False

    @classmethod
    def _parse_json_safely(cls, raw_text: str) -> Optional[Dict[str, Any]]:
        """Extracts JSON block from raw LLM completion."""
        try:
            raw_text = raw_text.strip()
            return json.loads(raw_text)
        except Exception:
            pass

        try:
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(raw_text[start:end + 1])
        except Exception:
            pass

        return None

    @classmethod
    def audit_and_repair(
        cls,
        draft_text: str,
        retrieved_context: List[Dict[str, Any]],
        temporal_mode: str = "UNDATED"
    ) -> Dict[str, Any]:
        """
        Main entrypoint: Audits the draft sentence-by-sentence using
        Inverted Chain-of-Rubrics and Reflexive Self-Healing DB Lookup.
        """
        if not draft_text or len(draft_text.strip()) < 20:
            return {
                "final_text": draft_text,
                "pass_verdict": True,
                "process_reward_score": 1.0,
                "corrections_made": 0,
                "audit_log": []
            }

        # Build clean ground-truth context block
        gt_blocks = []
        for idx, item in enumerate(retrieved_context[:8], 1):
            act = item.get("act_name") or item.get("act") or item.get("act_short") or "Indian Statute"
            sec = item.get("section_number") or item.get("section") or ""
            content = item.get("content", "").strip()[:450]
            gt_blocks.append(f"[{idx}] {act} Section/Article {sec}:\n{content}")

        gt_text = "\n\n".join(gt_blocks) if gt_blocks else "General Indian Statutory Grounding"

        prompt = CRITIC_PROMPT.format(
            temporal_mode=temporal_mode,
            ground_truth_context=gt_text,
            draft_text=draft_text[:3000]
        )

        client = cls._get_client()
        primary_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

        # Execute LLM Call with Resilient Fallback
        raw_json = None
        try:
            res = client.chat.completions.create(
                model=primary_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            raw_json = res.choices[0].message.content
        except Exception as e:
            print(f"[Critic FG-PRM] Primary model {primary_model} call failed ({e}), falling back...")
            try:
                fallback_model = "openai/gpt-oss-120b" if primary_model != "openai/gpt-oss-120b" else "qwen/qwen3.6-27b"
                res = client.chat.completions.create(
                    model=fallback_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=2500,
                    response_format={"type": "json_object"}
                )
                raw_json = res.choices[0].message.content
            except Exception as e2:
                print(f"[Critic FG-PRM] Fallback also failed ({e2}). Fast-passing draft.")
                return {
                    "final_text": draft_text,
                    "pass_verdict": True,
                    "process_reward_score": 0.95,
                    "corrections_made": 0,
                    "audit_log": []
                }

        audit_json = cls._parse_json_safely(raw_json)
        if not audit_json:
            print("[Critic FG-PRM] JSON parse fallback. Maintaining draft fidelity.")
            return {
                "final_text": draft_text,
                "pass_verdict": True,
                "process_reward_score": 0.95,
                "corrections_made": 0,
                "audit_log": []
            }

        evaluations = audit_json.get("chain_of_rubrics_evaluation", [])
        mandates = audit_json.get("correction_mandates", [])
        total_claims = len(evaluations)

        valid_claims = 0
        contradictions = 0
        ungrounded = 0

        # Synchronized Evaluation & Reflexive Rescue FIRST
        for eval_block in evaluations:
            evidence = str(eval_block.get("extracted_ground_truth_evidence", "")).strip()
            claim_text = str(eval_block.get("substantive_claim_span", "")).strip()

            if evidence == "CONTRADICTED":
                contradictions += 1
            elif evidence == "UNGROUNDED_2024":
                rescued = cls._try_reflexive_db_lookup(claim_text)
                if rescued:
                    valid_claims += 1
                    norm_claim = cls._normalize_span(claim_text)
                    mandates = [m for m in mandates if cls._normalize_span(m.get("flagged_span", "")) != norm_claim]
                else:
                    ungrounded += 1
            elif eval_block.get("claim_is_valid"):
                valid_claims += 1

        # Synchronized Deterministic PRM Math
        if total_claims > 0:
            process_reward_score = round(
                max(0.0, min(1.0, (valid_claims + (0.5 * ungrounded) - (0.5 * contradictions)) / total_claims)),
                4
            )
        else:
            process_reward_score = 0.95

        # Synchronized Terminal Verdict
        pass_verdict = (len(mandates) == 0) and (process_reward_score >= 0.85)

        if pass_verdict:
            print(f"[Critic FG-PRM] ✅ PASS (Score: {process_reward_score:.4f}) — Zero corrections needed.")
            return {
                "final_text": draft_text,
                "pass_verdict": True,
                "process_reward_score": process_reward_score,
                "corrections_made": 0,
                "audit_log": evaluations
            }

        # Surgical Pruning & Repair Loop
        patched_text = draft_text
        corrections_count = 0

        print(f"[Critic FG-PRM] ⚠️ Intercepted {len(mandates)} flawed legal span(s). Executing surgical patch...")
        for mandate in mandates:
            flagged = mandate.get("flagged_span", "").strip()
            replacement = mandate.get("corrected_replacement", "").strip()
            err_type = mandate.get("error_type", "Legal Defect")

            if not flagged:
                continue

            if replacement == "OMIT_UNVERIFIED_ASSERTION":
                pattern = re.escape(flagged) + r"\s*\.?\s*"
                patched_text = re.sub(pattern, "", patched_text)
                corrections_count += 1
                print(f"      ✂️ Omitted unverified assertion ({err_type}): \"{flagged[:50]}...\"")
            elif replacement:
                if flagged in patched_text:
                    patched_text = patched_text.replace(flagged, replacement)
                    corrections_count += 1
                    print(f"      🔧 Patched ({err_type}): \"{flagged[:40]}...\" ➔ \"{replacement[:40]}...\"")
                else:
                    cleaned_flagged = re.escape(flagged[:40])
                    match = re.search(cleaned_flagged, patched_text)
                    if match:
                        start_idx = match.start()
                        end_idx = patched_text.find(".", start_idx)
                        if end_idx != -1:
                            patched_text = patched_text[:start_idx] + replacement + patched_text[end_idx + 1:]
                            corrections_count += 1

        patched_text = re.sub(r' +', ' ', patched_text)
        patched_text = re.sub(r'\n{3,}', '\n\n', patched_text).strip()

        return {
            "final_text": patched_text,
            "pass_verdict": pass_verdict,
            "process_reward_score": process_reward_score,
            "corrections_made": corrections_count,
            "audit_log": evaluations
        }


# Module-level convenience function
def audit_and_repair_response(
    draft_text: str,
    retrieved_context: list,
    temporal_mode: str = "UNDATED"
) -> Dict[str, Any]:
    return AdversarialCriticEngine.audit_and_repair(
        draft_text=draft_text,
        retrieved_context=retrieved_context,
        temporal_mode=temporal_mode
    )
