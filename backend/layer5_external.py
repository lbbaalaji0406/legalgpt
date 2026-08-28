"""
SAULSGPT — LAYER 5: EXTERNAL TOOLS
=====================================
Two tools:

Tool 1 — IndiaKanoon Case Law Fetcher
  Scrapes indiankanoon.org for relevant judgments
  Called AFTER Layer 3 for Case Analysis mode only
  Appended to final response as supplementary section
  Gracefully skipped if offline or blocked

Tool 2 — APScheduler Background Auto-Updater
  Re-runs scraper + chunk_and_embed every 30 days
  Keeps ChromaDB current with latest amendments
  Runs as background daemon
  Called once when FastAPI server starts

Run standalone to test IndiaKanoon:
    python layer5_external.py

Import in orchestrator:
    from layer5_external import fetch_case_law, start_auto_updater
"""

import os
import sys
import time
import threading
import hashlib
import subprocess
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict

# DuckDuckGo search — free, no API key needed
# Install: pip install duckduckgo-search
try:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("[Layer 5] WARNING: duckduckgo-search not installed.")
    print("          Run: pip install duckduckgo-search")

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

# Absolute paths for subprocess updater
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
REPO_DIR    = os.path.dirname(BASE_DIR)
SCRAPER     = os.path.join(BASE_DIR, "01_scraper.py")
CHUNKER     = os.path.join(BASE_DIR, "02_chunk_and_embed.py")

# IndiaKanoon config
IK_BASE_URL = "https://indiankanoon.org"
IK_TIMEOUT  = 8    # seconds — don't block main pipeline long
IK_MAX_RESULTS = 2 # only top 2 judgments

# Browser User-Agent — required to avoid being blocked
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-IN,en;q=0.9",
}


# ─────────────────────────────────────────────────────────────
# TOOL 1 — INDIAKANOON CASE LAW FETCHER
# ─────────────────────────────────────────────────────────────

def fetch_case_law(
    query: str,
    act_name: str = "",
    section_num: str = ""
) -> str:
    """
    Fetches relevant Supreme Court / High Court judgments
    from IndiaKanoon for the given legal query.

    Called AFTER Layer 3 generates response.
    Result is APPENDED to final response — not used for reasoning.
    This avoids polluting the LLM context with unverified web data.

    Args:
        query      : user's legal query (reformulated from Layer 1)
        act_name   : act name from retrieved sections (improves search)
        section_num: section number from retrieved sections

    Returns:
        formatted string of top cases to append to response
        OR empty string if offline/blocked/no results

    Example:
        result = fetch_case_law(
            "employer unpaid wages",
            act_name="Payment of Wages Act",
            section_num="15"
        )
    """
    print("[Layer 5] 🌐 Fetching relevant case law from IndiaKanoon...")

    # 1. Clean database act name
    # ChromaDB stores names like "NIA_from_db" — IndiaKanoon won't understand
    # Strip "_from_db" suffix and underscores before searching
    clean_act = act_name.replace("_from_db", "").replace("_", " ").strip()

    # 2. Map common acronyms to full act names IndiaKanoon recognises
    ACT_MAP = {
        "NIA":  "Negotiable Instruments Act",
        "IPC":  "Indian Penal Code",
        "CRPC": "Criminal Procedure Code",
        "CrPC": "Criminal Procedure Code",
        "BNS":  "Bharatiya Nyaya Sanhita",
        "BNSS": "Bharatiya Nagarik Suraksha Sanhita",
        "BSA":  "Bharatiya Sakshya Adhiniyam",
        "CPC":  "Civil Procedure Code",
        "IEA":  "Indian Evidence Act",
        "HMA":  "Hindu Marriage Act",
        "MVA":  "Motor Vehicles Act",
        "IDA":  "Industrial Disputes Act",
    }
    search_act = ACT_MAP.get(clean_act.upper(), clean_act)

    # 3. Build STRICT search query — no user story, just law
    # Long user queries choke IndiaKanoon keyword search
    # Only use act name + section number for precise results
    if search_act and section_num:
        search_query = f'"{search_act}" AND "Section {section_num}"'
    elif search_act:
        search_query = f'"{search_act}"'
    else:
        # Fallback: first 4 words of query only
        search_query = " ".join(query.split()[:4])

    print(f"[Layer 5] Search query: {search_query}")

    search_url = (
        f"{IK_BASE_URL}/search/"
        f"?formInput={requests.utils.quote(search_query)}"
        f"&type=judgments"
    )

    try:
        response = requests.get(
            search_url,
            headers=HEADERS,
            timeout=IK_TIMEOUT
        )
        response.raise_for_status()

        soup    = response.text
        bsoup   = BeautifulSoup(soup, 'html.parser')

        # IndiaKanoon search result structure
        # Try multiple selectors — site structure can vary
        results = (
            bsoup.find_all('div', class_='result', limit=IK_MAX_RESULTS) or
            bsoup.find_all('div', class_='result_title', limit=IK_MAX_RESULTS) or
            bsoup.find_all('li', class_='result', limit=IK_MAX_RESULTS)
        )

        if not results:
            print("[Layer 5] ℹ️  No case law results found.")
            return ""

        cases = []
        for idx, res in enumerate(results, 1):
            try:
                # Try to extract title
                title_container = (
                    res.find('div', class_='result_title') or
                    res.find('a') or
                    res
                )
                title_tag = (
                    title_container.find('a')
                    if title_container.name != 'a'
                    else title_container
                )

                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                href  = title_tag.get('href', '')
                link  = f"{IK_BASE_URL}{href}" if href.startswith('/') else href

                # Try to extract snippet
                snippet_tag = (
                    res.find('div', class_='headline') or
                    res.find('div', class_='snippet') or
                    res.find('p')
                )
                snippet = (
                    snippet_tag.get_text(strip=True)[:200]
                    if snippet_tag
                    else "See full judgment at link."
                )

                cases.append(
                    f"Case {idx}: {title}\n"
                    f"  Summary: {snippet}\n"
                    f"  Link: {link}"
                )

            except Exception:
                # Skip malformed result — don't crash
                continue

        if not cases:
            return ""

        result_block = (
            "\n\n📚 RELEVANT CASE LAW (IndiaKanoon)\n"
            + "─" * 40 + "\n"
            + "\n\n".join(cases)
            + "\n" + "─" * 40
            + "\nNote: Case law provided for reference only. "
              "Verify judgments before citing."
        )

        print(f"[Layer 5] ✅ Found {len(cases)} relevant case(s).")
        return result_block

    except requests.exceptions.Timeout:
        print("[Layer 5] ⚠️  IndiaKanoon request timed out.")
        return ""

    except requests.exceptions.ConnectionError:
        print("[Layer 5] ⚠️  No internet connection. Skipping case law.")
        return ""

    except requests.exceptions.HTTPError as e:
        print(f"[Layer 5] ⚠️  IndiaKanoon HTTP error: {e}")
        return ""

    except Exception as e:
        print(f"[Layer 5] ⚠️  Case law fetch error: {e}")
        return ""


# ─────────────────────────────────────────────────────────────
# TOOL 2 — BACKGROUND AUTO-UPDATER
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# TOOL 2 — AGENTIC FALLBACK WEB SEARCH
# Triggered ONLY when Layer 2 ChromaDB returns zero results
# AND Knowledge Graph also found nothing
# Searches the web for Indian law info on the query
# Formats results to look like ChromaDB chunks
# So Layer 3 reads them without knowing the difference
# ─────────────────────────────────────────────────────────────

def fallback_web_search(query: str) -> list:
    """
    Safety net when local database has no relevant data.
    Searches the live web for Indian law information.
    Formats results to mimic ChromaDB chunks so Layer 3
    can process them exactly like local database results.

    Triggered by orchestrator ONLY when:
    1. Layer 2 returns zero results AND
    2. Knowledge Graph found no relationships

    This guarantees SaulGPT always finds an answer
    even if local database is incomplete.

    Args:
        query: user query (reformulated from Layer 1)

    Returns:
        list of mock chunk dicts matching ChromaDB format
        OR empty list if web search also fails

    Example:
        results = fallback_web_search(
            "Industrial Disputes Act retrenchment definition"
        )
        # Returns list of dicts with act_name, section_number,
        # is_repealed, content — same format as ChromaDB chunks
    """
    print("[Layer 5] [Web] Local DB empty. Initiating Web Fallback Search...")

    if not DDGS_AVAILABLE:
        print("[Layer 5] WARNING: duckduckgo-search not installed. Skipping.")
        print("          Run: pip install duckduckgo-search")
        return []

    try:
        # ── PII Scrubber ──
        # Replace personal identifiers with category labels
        # to preserve search query structure without leaking data
        import re
        scrubbed_query = query

        # Replace email addresses with EMAIL label
        scrubbed_query = re.sub(r'[\w.+-]+@[\w-]+\.[a-z]+', '[EMAIL]', scrubbed_query)

        # Replace phone numbers with PHONE label
        scrubbed_query = re.sub(r'\b\d{10}\b|\b\+91\d{10}\b', '[PHONE]', scrubbed_query)

        # Replace Aadhaar-like numbers (12 digits) with ID label
        scrubbed_query = re.sub(r'\b\d{12}\b', '[ID_NUMBER]', scrubbed_query)

        # Replace individual person names (capitalized words not in legal vocab)
        LEGAL_CAPS = {
            "Industrial", "Disputes", "Act", "Supreme", "Court",
            "High", "Section", "Article", "India", "Indian",
            "Payment", "Wages", "Motor", "Vehicles", "Criminal",
            "Procedure", "Evidence", "Penal", "Code", "Hindu",
            "Marriage", "Negotiable", "Instruments", "Civil",
            "Constitution", "Labour", "Consumer", "Protection"
        }
        scrubbed_query = re.sub(
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',
            lambda m: m.group(0) if any(
                word in LEGAL_CAPS for word in m.group(0).split()
            ) else '[NAME]',
            scrubbed_query
        ).strip()

        # Clean up extra spaces from removed tokens
        scrubbed_query = re.sub(r'\s+', ' ', scrubbed_query).strip()

        if scrubbed_query != query:
            print(f"[Layer 5] [PII] PII scrubbed from query before web search")

        # Clean conversational filler to form a high-precision legal search query
        clean_keywords = re.sub(
            r'(?i)\b(i|my|me|we|us|what are|what is|tell me about|how to|a seller on|sent me a|and refused|what)\b',
            ' ',
            scrubbed_query
        )
        clean_keywords = re.sub(r'\s+', ' ', clean_keywords).strip()
        search_query = f"{clean_keywords} Indian law"
        print(f"[Layer 5] Searching: {search_query[:100]}...")

        results = []
        
        # Primary: Direct HTML DuckDuckGo Search (fast, reliable, no package breaking changes)
        try:
            ddg_headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-IN,en;q=0.9",
            }
            resp = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": search_query},
                headers=ddg_headers,
                timeout=8
            )
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for div in soup.find_all("div", class_="result"):
                    a_title = div.find("a", class_="result__a")
                    a_snippet = div.find("a", class_="result__snippet") or div.find("div", class_="result__snippet")
                    a_url = div.find("a", class_="result__url")
                    if a_title:
                        t = a_title.get_text(strip=True)
                        s = a_snippet.get_text(strip=True) if a_snippet else ""
                        u = a_url.get_text(strip=True) if a_url else a_title.get("href", "")
                        if t and (s or u):
                            results.append({"title": t, "body": s, "href": u})
        except Exception as html_err:
            print(f"[Layer 5] Direct HTML search error: {html_err}")

        # Secondary: DDGS package fallback if available
        if not results and DDGS_AVAILABLE:
            try:
                results = list(DDGS().text(search_query, max_results=6))
            except Exception as ddg_err:
                print(f"[Layer 5] DDGS error: {ddg_err}")

        if not results:
            print("[Layer 5] No matching web results.")
            return []

        # Prefer Indian legal sources if present, otherwise use top results
        INDIAN_DOMAINS = ("indiankanoon.org", "indiacode.nic.in", "scconline.com",
                          "manupatra.com", "barandbench.com", "livelaw.in",
                          "supremecourtcaselaw.com", "lawctopus.com", "vakilsearch.com", "legalserviceindia.com", "juristco.com", "lawcurb.com")
        legal_results = [r for r in results if any(d in r.get("href", "").lower() or d in r.get("body", "").lower() for d in INDIAN_DOMAINS)]
        final_results = legal_results[:4] if legal_results else results[:4]

        mock_chunks = []
        for i, res in enumerate(final_results, 1):
            href = res.get('href', '')
            is_primary = any(d in href.lower() for d in ["indiankanoon.org", "indiacode.nic.in", "scconline.com"])
            source_type = "primary" if is_primary else "commentary"
            SCORE_MAP = {"primary": 0.85, "commentary": 0.75}

            # Attempt to fetch rich body text from the article page
            body_content = res.get('body', '')
            if href.startswith('http') and i <= 2:
                try:
                    page_resp = requests.get(
                        href,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                        timeout=3.5
                    )
                    if page_resp.status_code == 200:
                        page_soup = BeautifulSoup(page_resp.text, "html.parser")
                        for tag in page_soup(["script", "style", "nav", "header", "footer"]):
                            tag.decompose()
                        paras = [p.get_text(strip=True) for p in page_soup.find_all("p") if len(p.get_text(strip=True)) > 40]
                        if paras:
                            extracted_text = " \n".join(paras[:6])
                            if len(extracted_text) > 150:
                                body_content = extracted_text[:1500]
                except Exception:
                    pass

            mock_chunks.append({
                "act_name":       "Live Web Search (Indian Law)",
                "section_number": f"Web Source {i}",
                "is_repealed":    False,
                "law_type":       "Web Search Legal Intelligence",
                "source_type":    source_type,
                "content": (
                    f"TOPIC / TITLE: {res.get('title', '')}\n"
                    f"LEGAL SUMMARY & PROVISIONS: {body_content}\n"
                    f"SOURCE REFERENCE: {href}"
                ),
                "relevance_score": SCORE_MAP.get(source_type, 0.75)
            })

        print(f"[Layer 5] [Web] Web fallback found {len(mock_chunks)} results.")
        
        # ── CONTINUOUS LEARNING: Auto-ingest into ChromaDB & Expand GNN Triples ──
        _auto_ingest_web_chunks_into_chromadb(mock_chunks)
        try:
            from auto_triplifier import auto_expand_knowledge_graph_from_web
            auto_expand_knowledge_graph_from_web(mock_chunks)
        except Exception as e:
            print(f"[Layer 5] Auto-triplifier trigger error: {e}")
        
        return mock_chunks

    except Exception as e:
        print(f"[Layer 5] WARNING: Web fallback failed: {e}")
        return []


def _auto_ingest_web_chunks_into_chromadb(mock_chunks: list, async_mode: bool = True):
    """
    Continuous Self-Learning Ingester:
    Automatically embeds and upserts newly retrieved high-quality web legal chunks
    directly into ChromaDB (`saulgpt_indian_laws`) so the database expands over time.
    """
    if not mock_chunks:
        return

    def _ingest_worker():
        try:
            import hashlib
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer

            # Setup ChromaDB persistent client pointing to official vector_db path
            chroma_dir = os.path.join(REPO_DIR, "data", "vector_db")
            if not os.path.exists(chroma_dir):
                chroma_dir = os.path.join(os.path.dirname(__file__), "data", "vector_db")

            client = chromadb.PersistentClient(
                path=chroma_dir,
                settings=Settings(anonymized_telemetry=False)
            )
            collection = client.get_or_create_collection(
                name="saulgpt_indian_laws",
                metadata={"hnsw:space": "cosine"}
            )

            model = SentenceTransformer("all-MiniLM-L6-v2")

            ids_to_add = []
            docs_to_add = []
            metas_to_add = []
            embs_to_add = []

            for chunk in mock_chunks:
                content = chunk.get("content", "")
                if len(content) < 100:
                    continue

                # Deterministic MD5 ID based on content
                chunk_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:12]
                chunk_id = f"web_ingest_{chunk_hash}"

                # Check if already present
                existing = collection.get(ids=[chunk_id])
                if existing and existing.get("ids"):
                    continue

                emb = model.encode(content).tolist()

                ids_to_add.append(chunk_id)
                docs_to_add.append(content)
                embs_to_add.append(emb)
                metas_to_add.append({
                    "act_name": "Web Ingested Legal Rule",
                    "section_number": str(chunk.get("section_number", "Web Source")),
                    "law_type": "web_live_ingest",
                    "source_type": chunk.get("source_type", "primary"),
                    "status": "active",
                    "ingestion_date": datetime.now().isoformat()
                })

            if ids_to_add:
                collection.upsert(
                    ids=ids_to_add,
                    documents=docs_to_add,
                    embeddings=embs_to_add,
                    metadatas=metas_to_add
                )
                print(f"[ChromaDB Ingest] [OK] Dynamically learned {len(ids_to_add)} new web statute chunk(s) into saulgpt_indian_laws! Total chunks now: {collection.count()}")

        except Exception as err:
            import traceback
            print(f"[ChromaDB Ingest] WARNING: Dynamic ingestion failed: {err}")
            traceback.print_exc()

    if async_mode:
        t = threading.Thread(target=_ingest_worker, daemon=True, name="ChromaDB_Dynamic_Ingester")
        t.start()
        return t
    else:
        _ingest_worker()


# ─────────────────────────────────────────────────────────────
# THREAD-SAFE DATABASE AUTO-UPDATER & SCHEDULER
# ─────────────────────────────────────────────────────────────

_UPDATE_LOCK = threading.Lock()
_IS_UPDATING = False

def run_database_update():
    """
    Executes scraper + chunker to refresh ChromaDB.
    Guarded with strict thread locking to prevent overlapping runs under high load.
    """
    global _IS_UPDATING
    if not _UPDATE_LOCK.acquire(blocking=False):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏳ DB Update already running in background. Skipping duplicate trigger.")
        return

    _IS_UPDATING = True
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{timestamp}] 🔄 SCHEDULED DB UPDATE STARTING...")

    try:
        if os.path.exists(SCRAPER):
            print("  → Running 01_scraper.py...")
            subprocess.run([sys.executable, SCRAPER], check=True, cwd=REPO_DIR, timeout=300)
            print("  → Scraper complete.")

        if os.path.exists(CHUNKER):
            print("  → Running 02_chunk_and_embed.py...")
            subprocess.run([sys.executable, CHUNKER], check=True, cwd=REPO_DIR, timeout=300)
            print("  → Chunker complete.")

        done_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{done_time}] ✅ DATABASE UPDATE COMPLETE.\n")

    except subprocess.CalledProcessError as e:
        print(f"🚨 UPDATE FAILED: Script crashed. Error: {e}")
    except subprocess.TimeoutExpired:
        print("🚨 UPDATE FAILED: Process timed out after 300s.")
    except Exception as e:
        print(f"🚨 UPDATE FAILED: Unknown error: {e}")
    finally:
        _IS_UPDATING = False
        _UPDATE_LOCK.release()


def run_database_update_async():
    """Non-blocking asynchronous wrapper for scheduler and manual triggers."""
    worker = threading.Thread(target=run_database_update, daemon=True, name="ChromaDB_Auto_Updater")
    worker.start()


def start_auto_updater():
    """
    Starts the APScheduler background job.
    Uses asynchronous worker so it never blocks web requests or API threads.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            run_database_update_async,
            trigger   = 'interval',
            days      = 30,
            id        = 'monthly_law_update',
            replace_existing = True,
            max_instances = 1
        )
        scheduler.start()

        next_run = datetime.now().strftime('%Y-%m-%d')
        print(f"⏳ Auto-updater started. DB will refresh every 30 days.")
        print(f"   Next update: 30 days from {next_run}")

        return scheduler

    except ImportError:
        print("⚠️  APScheduler not installed. Auto-updater disabled.")
        return None
    except Exception as e:
        print(f"⚠️  Auto-updater failed to start: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# TEST RUNNER
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("-" * 55)
    print("SaulGPT — Layer 5 External Tools Test")
    print("-" * 55)

    # Test IndiaKanoon fetcher
    print("\nTest: Fetching case law for wage dispute...")
    result = fetch_case_law(
        query       = "employer unpaid wages legal remedy",
        act_name    = "Payment of Wages Act",
        section_num = "15"
    )

    if result:
        print("\n" + result)
    else:
        print("No results (offline or blocked)")

    print("\n" + "=" * 55)
    print("Layer 5 External Tools test complete.")