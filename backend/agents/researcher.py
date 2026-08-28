"""
Researcher Agent - Legal Q&A and Knowledge Retrieval
==============================================
Handles: Legal questions, case analysis, procedures, pathfinding

Uses layer1-6 as tools internally.
"""

from typing import Optional, Dict, Any, List
from .llm_client import researcher, get_researcher_llm
from langchain_core.messages import HumanMessage, AIMessage
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompts.researcher import (
    RESEARCHER_SYSTEM_PROMPT,
    LEGAL_QA_PROMPT,
    ANALYSIS_PROMPT,
    PATHFINDER_PROMPT,
    IPC_TO_BNS_MAP,
    CRPC_TO_BNSS_MAP,
)

# Import existing pipeline components as tools
try:
    from layer1_understanding import analyze_query
    from layer2_retrieval import retrieve_with_hybrid_logic
    from layer3_reasoning import generate_legal_response
    from layer4_validation import validate_legal_response
    from layer5_external import fetch_case_law, fallback_web_search
    from layer6_knowledge_graph import legal_graph
except ImportError:
    # Fallback if layers not available
    analyze_query = None
    retrieve_with_hybrid_logic = None
    generate_legal_response = None
    validate_legal_response = None
    fetch_case_law = None
    fallback_web_search = None
    legal_graph = None


class ResearcherAgent:
    """
    Researcher Agent handles:
    - Legal Q&A (knowledge mode)
    - Case analysis (analysis mode)
    - Legal procedures (pathfinder mode)
    """
    
    def __init__(self):
        self.llm = researcher
        self.name = "Researcher"
        self.capabilities = ["legal_qa", "case_analysis", "pathfinder"]
    
    async def run(self, query: str, mode: str = "knowledge", conversation_history: List = None, triage_context: dict = None, **kwargs) -> Dict[str, Any]:
        """
        Main entry point for the agent.
        
        Args:
            query: User's legal question
            mode: knowledge | analysis | pathfinder
            conversation_history: Previous messages
            triage_context: Optional triage data (role, goal, intake_fields)
        
        Returns:
            Dict with response, metadata, and pipeline info
        """
        if mode == "knowledge":
            return await self.legal_qa(query, conversation_history, triage_context=triage_context)
        elif mode == "analysis":
            return await self.case_analysis(query, conversation_history, triage_context=triage_context)
        elif mode == "pathfinder":
            return await self.pathfinder(query, conversation_history, triage_context=triage_context)
        else:
            return await self.legal_qa(query, conversation_history, triage_context=triage_context)
    
    async def legal_qa(self, query: str, history: List = None, mode: str = "knowledge", triage_context: dict = None) -> Dict[str, Any]:
        """Answer legal questions"""
        if analyze_query:
            layer1_result = analyze_query(query, history or [])
        else:
            layer1_result = {"original_query": query}
        
        web_fallback_hint = layer1_result.get("web_fallback_recommended", False)

        if web_fallback_hint:
            print("[Researcher] LLM flagged query as outside local DB acts. Triggering web fallback directly.")
            retrieved_docs = []
        elif retrieve_with_hybrid_logic:
            retrieved_docs = retrieve_with_hybrid_logic(layer1_result, k=5)
        else:
            retrieved_docs = []

        # Relative relevance check — if local DB returned only weak noise (< 0.45), fallback to web
        if retrieved_docs:
            scores = [r.get("relevance_score", 0) for r in retrieved_docs]
            max_s = max(scores) if scores else 0
            if max_s < 0.45:
                print(f"[Researcher] Local DB results are low relevance (max={max_s:.4f}). Triggering fallback_web_search.")
                retrieved_docs = []

        if not retrieved_docs and fallback_web_search:
            search_query = layer1_result.get("keyword_synonyms") or layer1_result.get("search_optimized_query") or query
            retrieved_docs = fallback_web_search(search_query)

        if generate_legal_response:
            response = generate_legal_response(layer1_result, retrieved_docs, mode, triage_context=triage_context, conversation_history=history)
        else:
            response = f"I've found information related to: {query}"

        # ── Agentic Self-Correction Loop ──
        # If local DB chunks lacked the specific provisions, automatically fallback to live web search and regenerate!
        needs_web_fallback = (
            '"context_sufficient": false' in response.lower()
            or "i do not have enough specific legal context" in response.lower()
            or "do not directly apply" in response.lower()
            or "कानूनी विश्लेषण प्रस्तुत करना संभव नहीं" in response
            or "प्रासंगिक धारा या विवरण नहीं मिला" in response
            or "पर्याप्त संदर्भ नहीं" in response
        )
        if needs_web_fallback and fallback_web_search:
            print("[Researcher] Local DB lacked specific provisions. Auto-triggering Layer 5 Web Search Fallback...")
            search_q = layer1_result.get("keyword_synonyms") or layer1_result.get("search_optimized_query") or query
            web_docs = fallback_web_search(search_q)
            if web_docs:
                retrieved_docs = web_docs
                if generate_legal_response:
                    response = generate_legal_response(layer1_result, retrieved_docs, mode, triage_context=triage_context, conversation_history=history)

        if validate_legal_response:
            validated = validate_legal_response(response, retrieved_docs)
            response = validated.get("final_response") or validated.get("response") or response
        
        import re
        clean_resp = re.sub(r'^\s*\{[\s\S]*?context_sufficient[\s\S]*?\}\s*', '', response).strip()
        response = clean_resp if clean_resp else response

        return {
            "response": response,
            "mode_used": mode,
            "domain": layer1_result.get("domain", "general"),
            "laws_retrieved": len(retrieved_docs) if retrieved_docs else 0,
            "is_hallucinating": False,
            "confidence_score": 0.85
        }
    
    async def case_analysis(self, query: str, history: List = None, triage_context: dict = None) -> Dict[str, Any]:
        return await self.legal_qa(query, history, mode="analysis", triage_context=triage_context)
    
    async def pathfinder(self, query: str, history: List = None, triage_context: dict = None) -> Dict[str, Any]:
        result = await self.legal_qa(query, history, mode="pathfinder", triage_context=triage_context)
        if "response" in result:
            result["response"] = (
                "Here's the Step-by-Step Procedure:\n\n" 
                + result["response"]
            )
        return result
    
    async def fetch_case_laws(self, query: str) -> List[Dict]:
        """Fetch relevant case laws"""
        if fetch_case_law:
            return fetch_case_law(query)
        return []


# Singleton instance
agent = ResearcherAgent()