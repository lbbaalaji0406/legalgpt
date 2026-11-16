"""Self-check: ResearcherAgent returns citations and Layer 4's real verdict.

Stubs layers 1-5 (no network, no vector DB). Run: python backend/tests/test_researcher_citations.py
"""
import asyncio, os, sys
os.environ.setdefault("GROQ_API_KEY", "test-placeholder")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import agents.researcher as r  # noqa: E402

DOCS = [{"act_name": "BNS", "section_number": "318", "content": "cheating", "relevance_score": 0.9},
        {"act_name": "IPC", "section_number": "420", "is_repealed": True, "content": "old", "relevance_score": 0.8}]


def _patch(verdict):
    r.analyze_query = lambda q, h: {"original_query": q, "domain": "criminal"}
    r.retrieve_with_hybrid_logic = lambda l1, k=5: DOCS
    r.generate_legal_response = lambda *a, **k: "Answer citing Section 318 BNS."
    r.validate_legal_response = lambda resp, docs: {**verdict, "final_response": resp}
    r.fallback_web_search = lambda q: (_ for _ in ()).throw(AssertionError("web search must not run"))


def test_citations_and_verdict_pass_through():
    _patch({"is_hallucinating": True, "confidence_score": 0.42, "flagged_citations": ["Section 999 BNS"]})
    out = asyncio.run(r.ResearcherAgent().legal_qa("punishment for cheating"))
    assert [c["section_number"] for c in out["citations"]] == ["318", "420"]
    assert out["citations"][1]["is_repealed"] is True
    assert out["is_hallucinating"] is True and out["confidence_score"] == 0.42
    assert out["flagged_citations"] == ["Section 999 BNS"]


if __name__ == "__main__":
    test_citations_and_verdict_pass_through(); print("PASS test_citations_and_verdict_pass_through")
