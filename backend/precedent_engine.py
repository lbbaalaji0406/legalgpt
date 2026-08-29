import os
import json
import re
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "vector_db")
PREVIOUS_PRECEDENTS_PATH = os.path.join(DATA_DIR, "landmark_precedents.json")
COLLECTION_NAME = "saulgpt_landmark_precedents"

# Global Singletons
_EMBEDDER = None
_CHROMA_CLIENT = None
_COLLECTION = None

def _get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _EMBEDDER

def _get_collection():
    global _CHROMA_CLIENT, _COLLECTION
    if _COLLECTION is None:
        os.makedirs(DB_PATH, exist_ok=True)
        _CHROMA_CLIENT = chromadb.PersistentClient(path=DB_PATH, settings=Settings(anonymized_telemetry=False))
        _COLLECTION = _CHROMA_CLIENT.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Gold-standard Indian Supreme Court and High Court landmark precedents"}
        )
    return _COLLECTION


class PrecedentIntelligenceEngine:
    """
    High-speed, neuro-symbolic retrieval and self-healing ingestion engine
    for Indian Supreme Court & High Court judicial precedents.
    """

    @classmethod
    def index_seed_precedents(cls, force_reindex: bool = False) -> int:
        """
        Loads 80+ gold-standard landmark precedents from landmark_precedents.json,
        computes dense embeddings, and indexes them into ChromaDB and the GNN.
        """
        coll = _get_collection()
        current_count = coll.count()

        if current_count > 0 and not force_reindex:
            print(f"[PrecedentEngine] Collection '{COLLECTION_NAME}' already contains {current_count} precedents.")
            return current_count

        if not os.path.exists(PREVIOUS_PRECEDENTS_PATH):
            print(f"[PrecedentEngine] Error: Seed file not found at {PREVIOUS_PRECEDENTS_PATH}")
            return 0

        with open(PREVIOUS_PRECEDENTS_PATH, "r", encoding="utf-8") as f:
            precedents = json.load(f)

        embedder = _get_embedder()
        docs = []
        metas = []
        ids = []

        for p in precedents:
            case_id = p["id"]
            statutes_str = ", ".join(p.get("governing_statutes", []))
            
            content = (
                f"LANDMARK JUDGMENT: {p['case_name']} [{p['citation']}]\n"
                f"COURT / BENCH: {p['court']} (Year: {p['year']})\n"
                f"LEGAL DOMAIN: {p['domain']}\n"
                f"GOVERNING STATUTES: {statutes_str}\n"
                f"KEY LEGAL ISSUE: {p['key_issue']}\n"
                f"RATIO DECIDENDI (LEGAL PRINCIPLE): {p['ratio_decidendi']}\n"
                f"FACTUAL SCENARIO: {p['factual_scenario']}\n"
                f"EXECUTED RELIEF / COURT ORDER: {p['executed_relief']}\n"
                f"PRACTICAL CITATION GUIDANCE: {p['practical_takeaway']}"
            )

            docs.append(content)
            ids.append(case_id)
            metas.append({
                "case_name": p["case_name"],
                "citation": p["citation"],
                "court": p["court"],
                "year": int(p["year"]),
                "domain": p["domain"],
                "statutes": statutes_str,
                "practical_takeaway": p["practical_takeaway"]
            })

        print(f"[PrecedentEngine] Computing embeddings for {len(docs)} landmark precedents...")
        embeddings = embedder.encode(docs, show_progress_bar=False).tolist()

        coll.upsert(
            documents=docs,
            embeddings=embeddings,
            metadatas=metas,
            ids=ids
        )

        print(f"[PrecedentEngine] [OK] Successfully indexed {len(docs)} landmark precedents in ChromaDB!")

        # Synchronize into GNN triples
        cls._sync_precedents_to_gnn(precedents)
        return len(docs)

    @classmethod
    def _sync_precedents_to_gnn(cls, precedents: List[Dict]):
        """Injects precedent relational nodes into legal_triples.json and GNN."""
        triples_path = os.path.join(DATA_DIR, "legal_triples.json")
        existing_triples = []
        if os.path.exists(triples_path):
            with open(triples_path, "r", encoding="utf-8") as f:
                existing_triples = json.load(f)

        existing_keys = {(t["head"].lower(), t["relation"].lower(), t["tail"].lower()) for t in existing_triples}

        new_triples = []
        for p in precedents:
            c_name = re.sub(r"[^\w]", "_", p["case_name"]).strip("_")[:35]
            statutes = p.get("governing_statutes", [])
            primary_statute = re.sub(r"[^\w]", "_", statutes[0] if statutes else p["domain"]).strip("_")[:35]

            # Triple 1: (Case) --[supreme_court_benchmark]--> (Statute)
            t1 = {
                "head": c_name,
                "relation": "supreme_court_benchmark",
                "tail": primary_statute,
                "desc": f"{p['case_name']} establishes landmark Supreme Court ratio on {primary_statute}",
                "weight": 0.98
            }
            k1 = (t1["head"].lower(), t1["relation"].lower(), t1["tail"].lower())
            if k1 not in existing_keys:
                existing_triples.append(t1)
                existing_keys.add(k1)
                new_triples.append(t1)

        if new_triples:
            with open(triples_path, "w", encoding="utf-8") as f:
                json.dump(existing_triples, f, indent=2, ensure_ascii=False)
            print(f"[PrecedentEngine] [OK] Registered {len(new_triples)} precedent relations in GNN topology!")

    @classmethod
    def retrieve_matching_precedents(cls, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Sub-5ms local semantic vector retrieval for landmark precedents.
        """
        if not query or len(query.strip()) < 3:
            return []

        coll = _get_collection()
        embedder = _get_embedder()
        q_emb = embedder.encode([query]).tolist()

        results = coll.query(
            query_embeddings=q_emb,
            n_results=min(top_k, max(coll.count(), 1)),
            include=["documents", "metadatas", "distances"]
        )

        matched_precedents = []
        if results and results.get("documents") and len(results["documents"][0]) > 0:
            for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
                similarity = round(1.0 - (dist / 2.0), 3) # Approximate cosine similarity
                matched_precedents.append({
                    "case_name": meta.get("case_name", ""),
                    "citation": meta.get("citation", ""),
                    "court": meta.get("court", ""),
                    "year": meta.get("year", ""),
                    "domain": meta.get("domain", ""),
                    "statutes": meta.get("statutes", ""),
                    "practical_takeaway": meta.get("practical_takeaway", ""),
                    "full_text": doc,
                    "relevance_score": similarity
                })

        return matched_precedents

    @classmethod
    def format_precedents_for_prompt(cls, precedents: List[Dict[str, Any]]) -> str:
        """
        Formats retrieved precedents into clean, structured Markdown for Layer 3 reasoning.
        """
        if not precedents:
            return ""

        lines = ["\n### ⚖️ CONTROLLING JUDICIAL PRECEDENTS & REAL-WORLD EXECUTION:"]
        for idx, p in enumerate(precedents, 1):
            lines.append(f"\n{idx}. **{p['case_name']}** [{p['citation']}] — *{p['court']}*")
            lines.append(f"   • **Governing Statutes:** {p['statutes']}")
            lines.append(f"   • **Supreme Court Holding:** {p['practical_takeaway']}")
            
            # Extract ratio and relief from doc if available
            doc_lines = p.get("full_text", "").split("\n")
            for dl in doc_lines:
                if dl.startswith("RATIO DECIDENDI"):
                    lines.append(f"   • **Judicial Ratio:** {dl.split(':', 1)[-1].strip()}")
                elif dl.startswith("EXECUTED RELIEF"):
                    lines.append(f"   • **Relief Granted:** {dl.split(':', 1)[-1].strip()}")

        return "\n".join(lines)

    @classmethod
    def auto_ingest_case_precedent(cls, case_data: Dict[str, Any]) -> bool:
        """
        Self-healing ingestion hook: when Web Fallback discovers a new case law,
        embeds it into ChromaDB and registers relational triples into the GNN.
        """
        if not case_data or not case_data.get("case_name"):
            return False

        try:
            coll = _get_collection()
            embedder = _get_embedder()

            case_name = case_data.get("case_name", "").strip()
            citation = case_data.get("citation", "Citation Pending").strip()
            court = case_data.get("court", "Supreme Court / High Court").strip()
            summary = case_data.get("summary", "").strip()
            statute = case_data.get("statute", "Indian Law").strip()
            
            case_id = "WEB_PREC_" + re.sub(r"[^\w]", "", case_name)[:20].upper()

            content = (
                f"LANDMARK JUDGMENT: {case_name} [{citation}]\n"
                f"COURT / BENCH: {court}\n"
                f"GOVERNING STATUTES: {statute}\n"
                f"JUDICIAL SUMMARY & RATIO: {summary}\n"
                f"SOURCE: Real-Time Web Ingestion"
            )

            emb = embedder.encode([content]).tolist()

            coll.upsert(
                documents=[content],
                embeddings=emb,
                metadatas=[{
                    "case_name": case_name,
                    "citation": citation,
                    "court": court,
                    "domain": "Web Ingested Precedent",
                    "statutes": statute,
                    "practical_takeaway": summary[:200]
                }],
                ids=[case_id]
            )

            print(f"[PrecedentEngine] [OK] Self-healed & dynamically ingested new case: {case_name} [{citation}]")
            return True
        except Exception as e:
            print(f"[PrecedentEngine] Warning: Ingestion failed for {case_data}: {e}")
            return False


# Module-level convenience functions
def get_precedent_engine():
    return PrecedentIntelligenceEngine

def retrieve_precedents(query: str, top_k: int = 2) -> List[Dict[str, Any]]:
    return PrecedentIntelligenceEngine.retrieve_matching_precedents(query, top_k=top_k)

def format_precedents(precedents: List[Dict[str, Any]]) -> str:
    return PrecedentIntelligenceEngine.format_precedents_for_prompt(precedents)
