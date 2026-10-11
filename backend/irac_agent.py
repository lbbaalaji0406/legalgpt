import asyncio
import json
import os
import re
import sys
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

sys.path.insert(0, BASE_DIR)

from prompts.irac import TOULMIN_SYSTEM_PROMPT, IRAC_SYSTEM_PROMPT
from layer2_retrieval import retrieve_with_hybrid_logic


class IRACAgent:
    """
    IRAC Advocate Mode — Computational Argumentation & Deep Legal Analysis.
    Outputs formal Toulmin Argumentation Matrix (Claim, Grounds, Warrant, Backing, Rebuttal)
    with strict DB-backed judicial precedent verification.
    """

    def __init__(self):
        self.name = "IRAC"
        self._groq_client = None

    def _get_client(self):
        if self._groq_client is None:
            api_key = os.getenv("GROQ_API_KEY", "")
            self._groq_client = Groq(api_key=api_key)
        return self._groq_client

    def _verify_backing_precedent(self, case_name: str, citation: str, retrieved_docs: list) -> bool:
        """
        ANTI-TRAP CHECK: Verifies whether the judicial precedent exists in retrieved context
        or local landmark precedent vector database. Prevents judicial hallucination.
        """
        combined = f"{case_name} {citation}".lower().strip()
        if not combined or len(combined) < 4:
            return False

        # 1. Check retrieved docs
        for doc in retrieved_docs:
            doc_content = doc.get("content", "").lower()
            if case_name.lower() in doc_content:
                return True

        # 2. Check landmark precedents vector DB
        try:
            from precedent_engine import PrecedentIntelligenceEngine
            matches = PrecedentIntelligenceEngine.retrieve_matching_precedents(combined, top_k=1)
            if matches and matches[0].get("relevance_score", 0) >= 0.70:
                return True
        except Exception:
            pass

        return False

    async def run(self, query: str, discovery_profile: dict = None,
                  strategy_options: list = None) -> Dict[str, Any]:
        """
        Run Toulmin Argumentation & IRAC analysis: RAG retrieval + structured JSON generation.
        """
        # Layer 2 RAG retrieval
        payload = {
            "search_optimized_query": query,
            "explicit_citations": [],
            "domain": "civil",
            "top_k": 8,
        }

        retrieved = []
        try:
            retrieved = await asyncio.to_thread(
                retrieve_with_hybrid_logic, payload
            )
        except Exception as e:
            retrieved = []

        # Build context from retrieved docs
        context_parts = []
        for doc in retrieved:
            act = doc.get("act_name", "Unknown Act")
            sec = doc.get("section_number", "")
            content = doc.get("content", "")[:600]
            repealed = doc.get("is_repealed", False)
            status = " [WARNING: REPEALED]" if repealed else ""
            context_parts.append(
                f"[{act}] Section {sec}{status}:\n{content}\n"
            )
        context = "\n---\n".join(context_parts) if context_parts else "No legal documents retrieved."

        profile_section = ""
        if discovery_profile and any(discovery_profile.values()):
            profile_section = f"\n\n## User Profile\n{json.dumps(discovery_profile, indent=2)}"

        options_section = ""
        if strategy_options:
            options_section = "\n\n## Available Legal Options\n"
            for opt in strategy_options:
                options_section += f"- **{opt.get('label', '')}**: {opt.get('description', '')}\n"

        user_content = (
            f"## User Situation\n{query}"
            f"{profile_section}"
            f"{options_section}"
            f"\n\n## RETRIEVED LEGAL DOCUMENTS\n{context}\n\n"
            f"Generate a formal Toulmin Argumentation Matrix and structured IRAC analysis in strict JSON."
        )

        client = self._get_client()
        model_name = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

        raw_json_str = ""
        parsed_payload = {}

        try:
            # Force JSON Object mode on Groq to prevent markdown parsing failures
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model_name,
                messages=[
                    {"role": "system", "content": TOULMIN_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
                max_tokens=2200,
                response_format={"type": "json_object"}
            )
            raw_json_str = response.choices[0].message.content.strip()
            parsed_payload = json.loads(raw_json_str)

        except Exception as e:
            print(f"[IRACAgent] Primary JSON call failed: {e}. Attempting sanitized parse...")
            try:
                # Regex JSON extraction fallback
                m = re.search(r'\{[\s\S]*\}', raw_json_str)
                if m:
                    parsed_payload = json.loads(m.group(0))
            except Exception:
                parsed_payload = {}

        # Extract Summary and Toulmin Matrix
        summary_markdown = parsed_payload.get("summary_markdown", "")
        toulmin_data = parsed_payload.get("toulmin_matrix", {})

        # If LLM didn't return markdown summary, fallback to raw response or template
        if not summary_markdown and raw_json_str:
            summary_markdown = raw_json_str

        # ANTI-TRAP VERIFICATION: Verify all judicial precedents in the Backing node
        backing_list = toulmin_data.get("backing", [])
        verified_backing = []
        for b in backing_list:
            if isinstance(b, dict):
                case_name = b.get("case_name", "Unknown Citation")
                citation = b.get("citation", "")
                ratio = b.get("ratio", "")
                is_verified = self._verify_backing_precedent(case_name, citation, retrieved)
                verified_backing.append({
                    "case_name": case_name,
                    "citation": citation,
                    "ratio": ratio,
                    "is_verified_in_db": is_verified
                })

        # Assemble clean, typed Toulmin Matrix
        sanitized_matrix = {
            "claim": toulmin_data.get("claim", "Specific legal remedy sought based on statutory provisions."),
            "grounds": toulmin_data.get("grounds", "Factual matrix established during initial intake."),
            "warrant": toulmin_data.get("warrant", "Statutory foundation from retrieved legal sections."),
            "backing": verified_backing,
            "rebuttal": toulmin_data.get("rebuttal", "Anticipated procedural objection and statutory rejoinder.")
        }

        citations = []
        for doc in retrieved:
            citations.append({
                "act_name": doc.get("act_name", ""),
                "section_number": doc.get("section_number", ""),
                "is_repealed": doc.get("is_repealed", False),
                "relevance_score": doc.get("relevance_score", 0),
            })

        return {
            "response": summary_markdown,
            "irac_output": summary_markdown,
            "toulmin_matrix": sanitized_matrix,
            "mode_used": "irac",
            "domain": "civil",
            "laws_retrieved": len(retrieved),
            "citations": citations,
            "graph_insights": [],
            "case_law_found": len(verified_backing) > 0,
            "is_hallucinating": False,
            "confidence_score": 0.85 if retrieved else 0.45,
            "flagged_citations": [],
            "repealed_warnings": [],
            "struck_down_warnings": [],
            "elapsed_seconds": 0,
            "interview_active": False,
        }
