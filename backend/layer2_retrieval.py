"""
SAULGPT — LAYER 2: HYBRID RETRIEVAL
======================================
Techniques:
1. Semantic Search      — ChromaDB (all-MiniLM-L6-v2)
2. BM25 Keyword Search  — rank_bm25
3. Metadata Citation    — exact section_number filter
4. CrossEncoder         — ms-marco-MiniLM reranker
5. Deduplication        — content hash merge

Input:  UnderstandingResult dict from Layer 1
Output: Top k most relevant law section dicts

Run standalone to test:
    python layer2_retrieval.py

When used by pipeline_orchestrator.py:
    from layer2_retrieval import retrieve_with_hybrid_logic
    results = retrieve_with_hybrid_logic(layer1_payload)

IMPORTANT — matches 02_chunk_and_embed.py exactly:
    Embedding model : all-MiniLM-L6-v2
    Vector DB path  : vector_db
    Collection name : saulgpt_indian_laws
    Metadata keys   : act_name, section_number,
                      is_repealed, law_type
"""

import os
import re

from rank_bm25 import BM25Okapi

# ─────────────────────────────────────────────────────────────
# CONFIG — must match 02_chunk_and_embed.py exactly
# Changing any of these will cause zero results
# ─────────────────────────────────────────────────────────────

# Same model used in chunk_and_embed
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"

# Same absolute path logic used in 02_chunk_and_embed.py
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
REPO_DIR         = os.path.dirname(BASE_DIR)
VECTOR_DB_PATH = os.path.join(REPO_DIR, "data", "vector_db")

# Same collection name used in chunk_and_embed
COLLECTION_NAME  = "saulgpt_indian_laws"

# CrossEncoder reranker — scores results by true relevance
RERANKER_MODEL   = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Number of results to return after reranking
TOP_K            = 3

# ─────────────────────────────────────────────────────────────
# LAZY LOADING — heavy imports deferred until first query
# SentenceTransformer (~18s) + ChromaDB (~2s) loaded on demand
# ─────────────────────────────────────────────────────────────

_models_loaded = False
embedder = None
chroma_client = None
collection = None
reranker = None


def _ensure_models():
    """Load SentenceTransformer + ChromaDB on first call only."""
    global _models_loaded, embedder, chroma_client, collection, reranker
    if _models_loaded:
        return

    print("Loading retrieval models (first query)...")
    from sentence_transformers import SentenceTransformer, CrossEncoder
    import chromadb
    from chromadb.config import Settings

    embedder = SentenceTransformer(EMBEDDING_MODEL)

    chroma_client = chromadb.PersistentClient(
        path=VECTOR_DB_PATH,
        settings=Settings(anonymized_telemetry=False)
    )
    collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

    reranker = CrossEncoder(RERANKER_MODEL)

    print(f"ChromaDB loaded. Collection: {COLLECTION_NAME}")
    print(f"Total chunks in DB: {collection.count()}\n")
    _models_loaded = True


# ─────────────────────────────────────────────────────────────
# BM25 INDEX BUILDER
# Loads all documents from ChromaDB and builds BM25 index
# ─────────────────────────────────────────────────────────────

def build_bm25_index(act_name_filter: str = None):
    """
    Builds BM25 keyword index from ChromaDB documents.
    Optionally filters by act_name for focused search.

    Args:
        act_name_filter: if provided filters docs to this act only
                         e.g. "Payment of Wages Act"

    Returns:
        bm25 index object,
        list of document texts,
        list of metadata dicts

    Example:
        bm25, docs, metas = build_bm25_index()
    """
    # Fetch all documents from collection
    # ChromaDB get() returns all stored chunks
    if act_name_filter:
        result = collection.get(
            where={"act_name": act_name_filter}
        )
    else:
        result = collection.get()

    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])

    if not documents:
        return None, [], []

    # Tokenize documents for BM25
    tokenized_corpus = [doc.lower().split() for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)

    return bm25, documents, metadatas


# ─────────────────────────────────────────────────────────────
# MAIN RETRIEVAL FUNCTION
# ─────────────────────────────────────────────────────────────

def retrieve_with_hybrid_logic(payload: dict, k: int = TOP_K) -> list:
    """
    Hybrid retrieval: semantic + BM25 + reranking.

    Takes Layer 1 output payload and returns
    top k most relevant law sections.

    Args:
        payload: dict from layer1_understanding.analyze_query()
                 must contain:
                 - search_optimized_query (str)
                 - explicit_citations (list)
                 - domain (str) [optional]

        k: number of results to return (default 8)

    Returns:
        list of result dicts each containing:
        content, act_name, section_number,
        is_repealed, law_type, relevance_score

    Example:
        results = retrieve_with_hybrid_logic({
            "search_optimized_query": "unpaid wages employer",
            "explicit_citations": ["SECTION 15"],
            "domain": "labour"
        })
    """

    _ensure_models()

    def _safe_top_k(value, default=TOP_K):
        """Guarantee a positive integer for ChromaDB n_results."""
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = default
        return value if value > 0 else default

    # Extract fields from Layer 1 payload
    semantic_query = payload.get("hyde_paragraph") or payload.get("search_optimized_query", "")
    keyword_query  = payload.get("keyword_synonyms") or payload.get("search_optimized_query", "")
    citations = payload.get("explicit_citations", [])
    top_k     = _safe_top_k(payload.get("top_k", k))
    temporal_status = payload.get("temporal_context", {}).get("temporal_status") or payload.get("temporal_status", "UNDATED")

    print(f"\n[Layer 2] Semantic  : {semantic_query[:70]}...")
    print(f"[Layer 2] Keywords  : {keyword_query[:70]}...")
    print(f"[Layer 2] Citations : {citations}")
    print(f"[Layer 2] Temporal  : {temporal_status}")
    print(f"[Layer 2] Top K     : {top_k}")

    # ── TECHNIQUE 1: Semantic Search via ChromaDB ──
    # Embeds query (uses HyDE paragraph) and finds nearest chunks by cosine similarity
    print("\n[1/3] Running semantic search (ChromaDB)...")

    query_embedding = embedder.encode(semantic_query).tolist()
    collection_count = collection.count()

    if collection_count <= 0:
        print("[Layer 2] WARNING: ChromaDB collection is empty.")
        return []

    # Check if we have an explicit citation to prioritize
    # If user mentioned "Section 138" fetch all matching chunks directly from ChromaDB
    semantic_results_raw = []
    target_sec_num = None

    if citations:
        sec_match = re.search(r'\d+[A-Za-z]*', citations[0])
        if sec_match:
            target_sec_num = sec_match.group()
            print(f"[Layer 2] Citation filter: section_number = {target_sec_num}")
            try:
                # Fetch all chunks with this exact section number across collection
                citation_chunks = collection.get(where={"section_number": str(target_sec_num)})
                if citation_chunks and citation_chunks.get("documents"):
                    for doc, meta in zip(citation_chunks["documents"], citation_chunks["metadatas"]):
                        semantic_results_raw.append((doc, meta))
                    print(f"[Layer 2] Direct citation chunks retrieved: {len(citation_chunks['documents'])}")
            except Exception as e:
                print(f"[Layer 2] Citation filter failed: {e}")

    # Always run broad semantic search too
    # Combines with citation results for broad coverage
    try:
        broad = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max(top_k * 2, 8), collection_count)
        )
        for doc, meta in zip(broad["documents"][0], broad["metadatas"][0]):
            semantic_results_raw.append((doc, meta))

        # ── PARTITION A: ACTIVE 2024 SANHITA RETRIEVAL (BNS / BNSS / BSA / Constitution) ──
        try:
            sanhita_broad = collection.query(
                query_embeddings=[query_embedding],
                where={"act_name": {"$in": ["BNS", "BNSS", "BSA", "Constitution"]}},
                n_results=min(4, collection_count)
            )
            if sanhita_broad and sanhita_broad.get("documents") and sanhita_broad["documents"][0]:
                for doc, meta in zip(sanhita_broad["documents"][0], sanhita_broad["metadatas"][0]):
                    semantic_results_raw.append((doc, meta))
                print(f"[Layer 2] ⚖️ Partition A (2024 Sanhitas): {len(sanhita_broad['documents'][0])} chunks retrieved.")
        except Exception as e_sanhita:
            pass

        # ── PARTITION B: LEGACY COLONIAL CODE RETRIEVAL (IPC / CrPC / IEA) FOR UNDATED DUAL-TRACK ──
        if temporal_status == "UNDATED":
            try:
                legacy_broad = collection.query(
                    query_embeddings=[query_embedding],
                    where={"act_name": {"$in": ["IPC_from_db", "CRPC_from_db", "IEA_from_db"]}},
                    n_results=min(4, collection_count)
                )
                if legacy_broad and legacy_broad.get("documents") and legacy_broad["documents"][0]:
                    for doc, meta in zip(legacy_broad["documents"][0], legacy_broad["metadatas"][0]):
                        semantic_results_raw.append((doc, meta))
                    print(f"[Layer 2] 📜 Partition B (Legacy Colonial): {len(legacy_broad['documents'][0])} chunks retrieved.")
            except Exception as e_legacy:
                pass
    except Exception as e:
        print(f"[Layer 2] ChromaDB query failed: {e}")
        return []

    print(f"[Layer 2] Semantic raw results: {len(semantic_results_raw)}")

    # ── TECHNIQUE 2: BM25 Keyword Search ──
    print("[2/3] Running BM25 keyword search...")

    bm25, bm25_docs, bm25_metas = build_bm25_index()
    bm25_results_raw = []

    if bm25 and bm25_docs:
        tokenized_query = keyword_query.lower().split()
        scores = bm25.get_scores(tokenized_query)

        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:max(top_k * 2, 8)]

        for idx in top_indices:
            if scores[idx] > 0:
                bm25_results_raw.append((
                    bm25_docs[idx],
                    bm25_metas[idx],
                    scores[idx]
                ))

    print(f"[Layer 2] BM25 raw results: {len(bm25_results_raw)}")

    # ── COMBINE AND DEDUPLICATE ──
    combined = {}

    for doc, meta in semantic_results_raw:
        if doc not in combined:
            act_n = meta.get("act_name") or meta.get("act_short") or meta.get("act") or ""
            sec_n = meta.get("section_number") or meta.get("section") or ""
            combined[doc] = {
                "content":        doc,
                "act_name":       act_n,
                "section_number": sec_n,
                "is_repealed":    meta.get("is_repealed", False),
                "law_type":       meta.get("law_type", "Statute"),
            }

    for doc, meta, score in bm25_results_raw:
        if doc not in combined:
            act_n = meta.get("act_name") or meta.get("act_short") or meta.get("act") or ""
            sec_n = meta.get("section_number") or meta.get("section") or ""
            combined[doc] = {
                "content":        doc,
                "act_name":       act_n,
                "section_number": sec_n,
                "is_repealed":    meta.get("is_repealed", False),
                "law_type":       meta.get("law_type", "Statute"),
                "bm25_score":     score,
            }

    all_results = list(combined.values())
    print(f"[Layer 2] Combined unique results: {len(all_results)}")

    if not all_results:
        print("[Layer 2] WARNING: No results found in DB.")
        return []

    # ── TECHNIQUE 3: CrossEncoder Reranker with Exact Citation Boosting ──
    print("[3/3] Reranking with CrossEncoder...")

    pairs  = [(semantic_query, r["content"]) for r in all_results]
    scores = reranker.predict(pairs)

    # Detect primary target act mentions in query to give strong affinity
    q_lower = (semantic_query + " " + keyword_query).lower()
    
    def _has_word(w, text):
        return bool(re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE))

    matched_target_acts = []
    if any(_has_word(w, q_lower) for w in ["negotiable", "cheque", "nia", "promissory"]):
        matched_target_acts = ["nia"]
    elif any(_has_word(w, q_lower) for w in ["fir", "crpc", "bnss", "bail", "anticipatory"]):
        matched_target_acts = ["crpc", "bnss"]
    elif any(_has_word(w, q_lower) for w in ["marriage", "divorce", "hindu marriage", "hma", "restitution"]):
        matched_target_acts = ["hma"]
    elif any(_has_word(w, q_lower) for w in ["cpc", "civil procedure", "written statement", "injunction"]):
        matched_target_acts = ["cpc"]
    elif any(_has_word(w, q_lower) for w in ["motor", "mva", "vehicle", "traffic"]):
        matched_target_acts = ["mva"]
    elif any(_has_word(w, q_lower) for w in ["evidence", "iea", "bsa", "witness", "certificate"]):
        matched_target_acts = ["iea", "bsa"]
    elif any(_has_word(w, q_lower) for w in ["industrial", "workman", "ida", "retrenchment", "layoff"]):
        matched_target_acts = ["ida"]
    elif any(_has_word(w, q_lower) for w in ["ipc", "penal code", "bns", "murder", "theft", "extortion", "community service"]):
        matched_target_acts = ["ipc", "bns"]
    elif any(_has_word(w, q_lower) for w in ["constitution", "article", "fundamental right"]):
        matched_target_acts = ["constitution"]

    is_modern_query = any(w in q_lower for w in ["today", "new law", "new", "2024", "bns", "bnss", "bsa"])

    boosted_ranked = []
    for score, r in zip(scores, all_results):
        adjusted_score = float(score)
        sec = str(r.get("section_number", "")).strip()
        act = str(r.get("act_name", "")).lower()
        content = r.get("content", "")

        # 1. Exact section citation boost
        if target_sec_num and sec == str(target_sec_num):
            adjusted_score += 12.0
            # Prefer substantive chunks over short 1-line amendment notes
            if len(content) > 120:
                adjusted_score += 8.0

        # 2. Target act affinity boost / penalty
        if matched_target_acts:
            act_tokens = set(re.split(r'[^a-z0-9]+', act))
            if any(target in act_tokens or target == act for target in matched_target_acts):
                adjusted_score += 25.0
            else:
                adjusted_score -= 15.0  # Penalize chunks from completely unrelated acts

        # 3. Modern 2024 Sanhita preference for queries with modern markers
        if is_modern_query and any(s in act for s in ["bns", "bnss", "bsa"]):
            adjusted_score += 10.0

        boosted_ranked.append((adjusted_score, r))

    # Sort by adjusted score descending
    ranked = sorted(boosted_ranked, key=lambda x: x[0], reverse=True)

    # Build final top k results (default min 5 for complete legal context)
    effective_k = max(top_k, 5)

    if temporal_status == "UNDATED":
        # Ensure representation: top 3 active 2024 Sanhita chunks (is_repealed == False)
        # and top 2 legacy colonial chunks (is_repealed == True)
        active_candidates = [r for score, r in ranked if not r.get("is_repealed")]
        legacy_candidates = [r for score, r in ranked if r.get("is_repealed")]

        balanced = []
        # Add up to 3 active 2024 chunks
        for c in active_candidates[:3]:
            if c not in balanced:
                balanced.append(c)
        # Add up to 2 legacy colonial chunks
        for c in legacy_candidates[:2]:
            if c not in balanced:
                balanced.append(c)
        # Fill remaining slots up to effective_k from highest ranked
        for score, r in ranked:
            if len(balanced) >= effective_k:
                break
            if r not in balanced:
                balanced.append(r)
        final_list = balanced
    else:
        final_list = [r for score, r in ranked[:effective_k]]

    top_results = []
    for result in final_list:
        top_results.append({
            "content":         result["content"],
            "act_name":        result["act_name"],
            "section_number":  result["section_number"],
            "is_repealed":     result["is_repealed"],
            "law_type":        result["law_type"],
            "relevance_score": round(float(result.get("relevance_score", 0.9)), 4),
        })

    print(f"[Layer 2] Final top {len(top_results)} sections ready for Layer 3 (Dual-Track balanced: {temporal_status == 'UNDATED'}).\n")
    return top_results


# ─────────────────────────────────────────────────────────────
# TEST RUNNER
# Only runs when executed directly:
#   python layer2_retrieval.py
#
# Uses a simulated Layer 1 payload
# In production this payload comes from analyze_query()
# Test query covers labour law + explicit section citation
# which exercises all 3 retrieval techniques at once
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Simulated Layer 1 output
    # In production: comes from layer1_understanding.analyze_query()
    test_payload = {
        "search_optimized_query": (
            "What are the legal conditions for a valid marriage regarding age and living spouses "
            "under Section 5 of the Hindu Marriage Act?"
        ),
        "domain":             "family",
        "explicit_citations": ["SECTION 5"],
        "is_ambiguous":       False,
    }

    print("-" * 55)
    print("SaulGPT — Layer 2 Hybrid Retrieval Test")
    print("-" * 55)

    results = retrieve_with_hybrid_logic(test_payload)

    print("\n" + "=" * 55)
    print("TOP RETRIEVED LEGAL SECTIONS")
    print("=" * 55)

    if not results:
        print("No results returned.")
        print("Troubleshooting:")
        print("  1. Run 02_chunk_and_embed.py first")
        print("  2. Check VECTOR_DB_PATH = 'vector_db'")
        print("  3. Check COLLECTION_NAME = 'saulgpt_indian_laws'")
    else:
        for i, result in enumerate(results, 1):
            print(f"\nRESULT {i}:")
            print(f"  ACT     : {result['act_name']}")
            print(f"  SECTION : {result['section_number']}")
            print(f"  SCORE   : {result['relevance_score']}")
            print(f"  REPEALED: {result['is_repealed']}")
            print(f"  CONTENT : {result['content'][:200]}...")

    print("\n" + "=" * 55)
    print("Layer 2 complete. Results ready for Layer 3.")
    print("=" * 55)
