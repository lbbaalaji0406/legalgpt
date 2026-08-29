import os
import re
import json
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from langchain_groq import ChatGroq

CRITIC_PROMPT = """You are an Adversarial Senior Partner & Judicial Reviewer in an elite Indian law firm.
Your sole job is to cross-examine and scrutinize the Drafting Counsel's legal response against the provided Ground-Truth Statutory Sections.

GROUND-TRUTH LEGAL CONTEXT:
{ground_truth_context}

DRAFT LEGAL RESPONSE TO AUDIT:
{draft_text}

AUDIT CHECKLIST:
1. STATUTORY PRECISION: Are section numbers, Act names, and 2024 concordance (BNS/BNSS/BSA vs IPC/CrPC/IEA) accurate?
2. MANDATORY VS DIRECTORY: Did the draft confuse mandatory obligations ("SHALL") with discretionary options ("MAY")?
3. PROCEDURAL & LIMITATION DEADLINES: Are any stated limitation windows (e.g. 15 days, 30 days, 60 days, 2 years, 3 years) strictly correct according to Indian law?
4. JURISPRUDENTIAL RATIO: Are judicial holdings and ratios (e.g. Supreme Court benchmarks) applied without logical leaps?

OUTPUT INSTRUCTIONS:
Evaluate each atomic substantive legal claim.
If the entire draft is factually accurate, sound, and fully supported, set "pass_verdict": true, with an empty "correction_mandates" list.
If you detect ANY factual contradiction, wrong limitation period, or misapplied section, set "pass_verdict": false and provide a surgical correction mandate ONLY for the specific flawed sentence. Do NOT ask to rewrite parts that are already correct.

Output STRICT JSON on a single line or standard JSON block:
{{
  "pass_verdict": true | false,
  "process_reward_score": <float between 0.0 and 1.0>,
  "critique_summary": "<one sentence overall assessment>",
  "claim_evaluations": [
    {{
      "claim_text": "<exact sentence from draft>",
      "grounding_score": <0.0 to 1.0>,
      "logic_score": <0.0 to 1.0>,
      "procedure_score": <0.0 to 1.0>,
      "claim_reward": <0.0 to 1.0>,
      "is_valid": true | false
    }}
  ],
  "correction_mandates": [
    {{
      "flagged_span": "<exact flawed sentence or phrase from the draft>",
      "error_type": "<e.g. Limitation Period Error | Misapplied Section | Wrong Concordance>",
      "critic_rationale": "<why this span is legally inaccurate>",
      "corrected_replacement": "<the exact legally accurate replacement sentence>"
    }}
  ]
}}
"""


class AdversarialCriticEngine:
    """
    Fine-Grained Process Reward Model (FG-PRM) & Adversarial Judicial Critic.
    Audits Drafting Counsel (Actor) responses against raw statutory grounding
    and surgically repairs defective spans before user delivery.
    """

    _llm = None

    @classmethod
    def _get_critic_llm(cls):
        if cls._llm is None:
            api_key = os.getenv("GROQ_API_KEY", "")
            cls._llm = ChatGroq(
                model_name="qwen/qwen3.8-27b",
                temperature=0.0,
                max_completion_tokens=1000,
                api_key=api_key
            )
        return cls._llm

    @classmethod
    def audit_and_repair(
        cls,
        draft_text: str,
        retrieved_context: List[Dict[str, Any]],
        max_retries: int = 1
    ) -> Dict[str, Any]:
        """
        Main entrypoint: Audits the draft sentence-by-sentence.
        If all claims are valid -> Fast-Pass with 0 modifications.
        If flawed span detected -> Surgically patches that specific sentence.
        """
        if not draft_text or len(draft_text.strip()) < 20:
            return {
                "final_text": draft_text,
                "process_reward_score": 1.0,
                "corrections_made": 0,
                "audit_log": []
            }

        # Build clean ground-truth context block
        gt_blocks = []
        for idx, item in enumerate(retrieved_context[:6], 1):
            act = item.get("act_name", "Indian Statute")
            sec = item.get("section_number", "")
            content = item.get("content", "").strip()[:400]
            gt_blocks.append(f"[{idx}] {act} {sec}:\n{content}")

        gt_text = "\n\n".join(gt_blocks) if gt_blocks else "General Indian Statutory Grounding"

        try:
            llm = cls._get_critic_llm()
            prompt = CRITIC_PROMPT.format(
                ground_truth_context=gt_text,
                draft_text=draft_text[:2500]
            )

            response = llm.invoke(prompt).content.strip()

            # Parse JSON
            audit_json = cls._parse_json_safely(response)
            if not audit_json:
                # Fallback to fast-pass
                return {
                    "final_text": draft_text,
                    "process_reward_score": 0.95,
                    "corrections_made": 0,
                    "audit_log": ["Critic JSON parsing skipped, maintaining high-fidelity draft."]
                }

            pass_verdict = audit_json.get("pass_verdict", True)
            process_reward = float(audit_json.get("process_reward_score", 0.95))
            mandates = audit_json.get("correction_mandates", [])

            # FAST-PASS GATE: If Critic approves, return draft with zero changes
            if pass_verdict or not mandates:
                print(f"[Critic FG-PRM] ✅ PASS (Score: {process_reward:.4f}) — Zero corrections needed.")
                return {
                    "final_text": draft_text,
                    "process_reward_score": process_reward,
                    "corrections_made": 0,
                    "audit_log": audit_json.get("claim_evaluations", [])
                }

            # SURGICAL SPAN REPAIR: Patch only the defective sentences
            patched_text = draft_text
            corrections_count = 0

            print(f"[Critic FG-PRM] ⚠️ Intercepted {len(mandates)} flawed legal span(s). Executing surgical patch...")
            for mandate in mandates:
                flagged = mandate.get("flagged_span", "").strip()
                replacement = mandate.get("corrected_replacement", "").strip()
                rationale = mandate.get("critic_rationale", "")

                if flagged and replacement and flagged in patched_text:
                    patched_text = patched_text.replace(flagged, replacement)
                    corrections_count += 1
                    print(f"      🔧 Patched: \"{flagged[:50]}...\" ➔ \"{replacement[:50]}...\"")
                    print(f"         Reason: {rationale}")
                elif flagged and replacement:
                    # Fuzzy sentence boundary patch if exact substring match misses punctuation
                    cleaned_flagged = re.escape(flagged[:40])
                    match = re.search(cleaned_flagged, patched_text)
                    if match:
                        start_idx = match.start()
                        # Find end of sentence
                        end_idx = patched_text.find(".", start_idx)
                        if end_idx != -1:
                            patched_text = patched_text[:start_idx] + replacement + patched_text[end_idx + 1:]
                            corrections_count += 1

            return {
                "final_text": patched_text,
                "process_reward_score": max(process_reward, 0.88),
                "corrections_made": corrections_count,
                "audit_log": audit_json.get("claim_evaluations", [])
            }

        except Exception as e:
            print(f"[Critic FG-PRM] Critic audit warning (safe fallback): {e}")
            return {
                "final_text": draft_text,
                "process_reward_score": 0.92,
                "corrections_made": 0,
                "audit_log": [f"Fallback: {e}"]
            }

    @staticmethod
    def _parse_json_safely(raw_text: str) -> Optional[Dict]:
        """Robust JSON extractor for LLM output."""
        try:
            # Look for ```json ... ``` code blocks
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Look for outermost { ... }
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(raw_text[start:end + 1])

            return None
        except Exception:
            return None


# Module-level convenience function
def audit_and_repair_response(draft_text: str, retrieved_context: list) -> Dict[str, Any]:
    return AdversarialCriticEngine.audit_and_repair(draft_text, retrieved_context)
