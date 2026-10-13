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
_cached_bm25 = None
_cached_docs = None
_cached_metas = None


def _ensure_models():
    """Load SentenceTransformer + ChromaDB on first call only, with graceful fallbacks."""
    global _models_loaded, embedder, chroma_client, collection, reranker
    if _models_loaded:
        return

    print("Loading retrieval models (first query)...")
    try:
        import chromadb
        from chromadb.config import Settings
        chroma_client = chromadb.PersistentClient(
            path=VECTOR_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
        print(f"ChromaDB loaded. Collection: {COLLECTION_NAME}")
        print(f"Total chunks in DB: {collection.count()}\n")
    except Exception as e:
        print(f"[Layer 2 Warning] ChromaDB load failed or unavailable: {e}")
        collection = None

    try:
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer(EMBEDDING_MODEL)
    except Exception as e:
        print(f"[Layer 2 Warning] SentenceTransformer load skipped/failed: {e}")
        embedder = None

    # Load CrossEncoder only if not disabled (avoids OOM on cloud free tiers)
    disable_ce = os.environ.get("DISABLE_CROSS_ENCODER", "").lower() in ("1", "true")
    if disable_ce:
        print("[Layer 2] CrossEncoder disabled (low-memory cloud mode).")
        reranker = None
    else:
        try:
            from sentence_transformers import CrossEncoder
            reranker = CrossEncoder(RERANKER_MODEL)
        except Exception as e:
            print(f"[Layer 2 Warning] CrossEncoder load skipped: {e}")
            reranker = None

    _models_loaded = True


# ─────────────────────────────────────────────────────────────
# BM25 INDEX BUILDER
# Loads all documents from ChromaDB and builds BM25 index (cached)
# ─────────────────────────────────────────────────────────────

def build_bm25_index(act_name_filter: str = None):
    """
    Builds BM25 keyword index from ChromaDB documents.
    Caches global index to avoid expensive re-indexing and RAM churn.
    """
    global _cached_bm25, _cached_docs, _cached_metas

    if not act_name_filter and _cached_bm25 is not None:
        return _cached_bm25, _cached_docs, _cached_metas

    if collection is None:
        return None, [], []

    try:
        if act_name_filter:
            result = collection.get(where={"act_name": act_name_filter})
        else:
            result = collection.get()
    except Exception as e:
        print(f"[BM25 Warning] collection.get failed: {e}")
        return None, [], []

    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])

    if not documents:
        return None, [], []

    tokenized_corpus = [doc.lower().split() for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)

    if not act_name_filter:
        _cached_bm25 = bm25
        _cached_docs = documents
        _cached_metas = metadatas

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

    def _has_word(w, text):
        return bool(re.search(rf"\b{re.escape(w)}\b", str(text), re.IGNORECASE))

    # Extract fields from Layer 1 payload
    semantic_query = payload.get("hyde_paragraph") or payload.get("semantic_query") or payload.get("search_optimized_query", "")
    keyword_query  = payload.get("keyword_synonyms") or payload.get("keywords") or payload.get("search_optimized_query", "")
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
    semantic_results_raw = []
    if embedder is not None and collection is not None:
        print("\n[1/3] Running semantic search (ChromaDB)...")
        try:
            query_embedding = embedder.encode(semantic_query).tolist()
            collection_count = collection.count()
        except Exception as e:
            print(f"[Layer 2 Warning] Embedding generation failed: {e}")
            query_embedding = None
            collection_count = 0
    else:
        print("\n[1/3] Semantic search skipped (fast keyword / low-memory mode).")
        query_embedding = None
        collection_count = 0
    target_sec_nums = set()
    if citations:
        for c in citations:
            m = re.search(r'\d+[A-Za-z]*', str(c))
            if m:
                target_sec_nums.add(m.group())

    # Detect implied statutory sections from core legal topics
    q_all = (semantic_query + " " + keyword_query).lower()
    if any(_has_word(w, q_all) for w in ["cheat", "cheated", "cheating", "fraud", "scam"]):
        target_sec_nums.update(["318", "420"])
    if any(_has_word(w, q_all) for w in ["fir", "zero fir", "e-fir"]):
        target_sec_nums.update(["173", "154"])
    if any(_has_word(w, q_all) for w in ["certificate", "electronic evidence"]):
        target_sec_nums.update(["63", "65B"])
    if any(_has_word(w, q_all) for w in ["community service"]):
        target_sec_nums.update(["4", "23"])

    if collection and target_sec_nums:
        print(f"[Layer 2] Citation/Topic filter: section_numbers = {list(target_sec_nums)}")
        for s_num in target_sec_nums:
            try:
                c_chunks = collection.get(where={"section_number": str(s_num)})
                if c_chunks and c_chunks.get("documents"):
                    for doc, meta in zip(c_chunks["documents"], c_chunks["metadatas"]):
                        semantic_results_raw.append((doc, meta))
            except Exception as e:
                pass

    # Always run broad semantic search too
    # Combines with citation results for broad coverage
    if collection and query_embedding and collection_count > 0:
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
                    where={"is_active_2024": True},
                    n_results=min(max(top_k, 5), collection_count)
                )
                if sanhita_broad and sanhita_broad.get("documents") and sanhita_broad["documents"][0]:
                    for doc, meta in zip(sanhita_broad["documents"][0], sanhita_broad["metadatas"][0]):
                        semantic_results_raw.append((doc, meta))
                    print(f"[Layer 2] Partition A (2024 Sanhitas): {len(sanhita_broad['documents'][0])} chunks retrieved.")
            except Exception as e_sanhita:
                print(f"[Layer 2] Partition A query error: {e_sanhita}")

            # ── PARTITION B: LEGACY COLONIAL CODE RETRIEVAL (IPC / CrPC / IEA) FOR UNDATED DUAL-TRACK ──
            if temporal_status == "UNDATED":
                try:
                    legacy_broad = collection.query(
                        query_embeddings=[query_embedding],
                        where={"is_repealed": True},
                        n_results=min(max(top_k, 5), collection_count)
                    )
                    if legacy_broad and legacy_broad.get("documents") and legacy_broad["documents"][0]:
                        for doc, meta in zip(legacy_broad["documents"][0], legacy_broad["metadatas"][0]):
                            semantic_results_raw.append((doc, meta))
                        print(f"[Layer 2] Partition B (Legacy Colonial): {len(legacy_broad['documents'][0])} chunks retrieved.")
                except Exception as e_legacy:
                    print(f"[Layer 2] Partition B query error: {e_legacy}")
        except Exception as e:
            print(f"[Layer 2] ChromaDB query failed: {e}")

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
        )[:max(top_k * 4, 25)]

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
    if reranker is not None:
        print("[3/3] Reranking with CrossEncoder...")
        pairs  = [(semantic_query, r["content"]) for r in all_results]
        try:
            scores = reranker.predict(pairs)
        except Exception as e:
            print(f"[Layer 2 Warning] CrossEncoder inference failed ({e}), using default scores.")
            scores = [0.8] * len(all_results)
    else:
        print("[3/3] CrossEncoder skipped (low-memory / fast mode). Using relevance scoring.")
        scores = [0.8] * len(all_results)

    # Detect primary target act mentions in query to give strong affinity
    q_lower = (semantic_query + " " + keyword_query).lower()

    matched_target_acts = set()
    if any(_has_word(w, q_lower) for w in ["negotiable", "cheque", "nia", "promissory"]):
        matched_target_acts.add("nia")
    if any(_has_word(w, q_lower) for w in ["fir", "crpc", "bnss", "bail", "anticipatory", "cognizable", "complaint", "police"]):
        matched_target_acts.update(["crpc", "bnss"])
    if any(_has_word(w, q_lower) for w in ["marriage", "divorce", "hindu marriage", "hma", "restitution"]):
        matched_target_acts.add("hma")
    if any(_has_word(w, q_lower) for w in ["cpc", "civil procedure", "written statement", "injunction"]):
        matched_target_acts.add("cpc")
    if any(_has_word(w, q_lower) for w in ["motor", "mva", "vehicle", "traffic"]):
        matched_target_acts.add("mva")
    if any(_has_word(w, q_lower) for w in ["evidence", "iea", "bsa", "witness", "certificate"]):
        matched_target_acts.update(["iea", "bsa"])
    if any(_has_word(w, q_lower) for w in ["industrial", "workman", "ida", "retrenchment", "layoff"]):
        matched_target_acts.add("ida")
    if any(_has_word(w, q_lower) for w in [
        "ipc", "penal code", "bns", "cheated", "cheating", "fraud", "scam",
        "deception", "theft", "murder", "extortion", "dishonest", "misappropriation",
        "breach of trust", "community service", "420", "318"
    ]):
        matched_target_acts.update(["ipc", "bns"])
    if any(_has_word(w, q_lower) for w in ["constitution", "article", "fundamental right"]):
        matched_target_acts.add("constitution")

    is_modern_query = any(w in q_lower for w in ["today", "new law", "new", "2024", "bns", "bnss", "bsa"])

    boosted_ranked = []
    for score, r in zip(scores, all_results):
        adjusted_score = float(score)
        sec = str(r.get("section_number", "")).strip()
        act = str(r.get("act_name", "")).lower()
        content = r.get("content", "")

        # 1. Exact section citation boost
        if target_sec_nums and (sec in target_sec_nums or any(s in sec for s in target_sec_nums)):
            adjusted_score += 15.0
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
        def _is_legacy_chunk(item):
            a = (item.get("act_name") or item.get("act") or "").lower()
            return bool(item.get("is_repealed")) or "from_db" in a or a in ["ipc", "crpc", "iea"]

        def _is_active_sanhita(item):
            a = (item.get("act_name") or item.get("act") or "").lower()
            return bool(item.get("is_active_2024")) or a in ["bns", "bnss", "bsa", "constitution"]

        active_candidates = [r for score, r in ranked if _is_active_sanhita(r)]
        legacy_candidates = [r for score, r in ranked if _is_legacy_chunk(r)]

        balanced = []
        # Add up to 3 active 2024 chunks
        for c in active_candidates[:3]:
            if c not in balanced:
                balanced.append(c)
        # Add up to 3 legacy colonial chunks
        for c in legacy_candidates[:3]:
            if c not in balanced:
                balanced.append(c)
        # Fill remaining slots up to effective_k from highest ranked
        for score, r in ranked:
            if len(balanced) >= max(effective_k, 6):
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

    # ── TECHNIQUE 6: Shared Precedent Engine Integration (50,000+ Case Matrix) ──
    try:
        try:
            from backend.trial_studio.precedent_engine import get_precedent_engine
        except ImportError:
            from trial_studio.precedent_engine import get_precedent_engine
        pe = get_precedent_engine()
        precedent_matches = pe.search(query=semantic_query, top_k=2)
        for pm in precedent_matches:
            top_results.append({
                "content": f"[Ratio Decidendi]: {pm.ratio_decidendi} [Key Fact Anchor]: {pm.fact_anchor}",
                "act_name": f"{pm.court} Precedent — {pm.citation} ({pm.title})",
                "section_number": ", ".join(pm.sections_invoked),
                "is_repealed": False,
                "law_type": "CONTROLLING PRECEDENT RATIO",
                "relevance_score": 0.95,
            })
    except Exception as e:
        print(f"[Layer 2] Note: Precedent engine optional link skipped: {e}")

    print(f"[Layer 2] Final top {len(top_results)} sections & precedents ready for Layer 3 (Dual-Track balanced: {temporal_status == 'UNDATED'}).\n")
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
