import os
import sys

# 1. ZeroGPU hook must be imported first before any other modules
import spaces

# 2. Disable Gradio SSR mode to avoid port collisions in Spaces
os.environ["GRADIO_SSR_MODE"] = "false"

# Set up paths so all backend imports resolve cleanly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Load environment variables (.env or Hugging Face Space secrets)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Ensure spacy model is available
import subprocess
try:
    import spacy
    if not spacy.util.is_package("en_core_web_sm"):
        print("Downloading en_core_web_sm...")
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=False)
except Exception as _e:
    print(f"spaCy init check: {_e}")

# Import backend dependencies
import gradio as gr
from api_server import app as fastapi_app
from database import init_db

# ZeroGPU decorated function bound directly to gr.Interface
@spaces.GPU
def predict(query: str):
    if not query or not query.strip():
        return "Please enter a legal query to analyze."
    try:
        from pipeline_orchestrator import run_saulgpt_pipeline
        res = run_saulgpt_pipeline(query.strip(), session_id="hf-space-live")
        return res.get("response", "No response generated.")
    except Exception as e:
        return f"Error executing pipeline: {e}"

# Build the Gradio interface
demo = gr.Interface(
    fn=predict,
    inputs=gr.Textbox(
        lines=3,
        placeholder="Enter your legal question under Indian Law (BNS, BNSS, BSA 2023)...",
        label="Indian Legal Query"
    ),
    outputs=gr.Markdown(label="SaulGPT Legal Intelligence Analysis"),
    title="⚖️ SaulGPT Legal Intelligence API Server",
    description="Backend engine for SaulGPT. Integrated with Supabase PostgreSQL, ChromaDB, and ZeroGPU acceleration. Multi-device web client available at https://legalgpt-india.web.app"
)

# Initialize Supabase database
try:
    init_db()
except Exception as _e:
    print(f"init_db check: {_e}")

# Pre-warm retrieval models on CPU
try:
    from layer2_retrieval import _ensure_models
    _ensure_models()
except Exception as _e:
    print(f"model pre-warm check: {_e}")

if __name__ == "__main__":
    # Launch Gradio server in non-blocking mode to attach FastAPI routes
    server_app, local_url, share_url = demo.launch(prevent_thread_lock=True)
    
    # Mount all FastAPI routes onto the live Gradio server
    server_app.include_router(fastapi_app.router)
    
    print(f"SaulGPT API & Gradio UI live on {local_url} with full routes attached.")
    
    # Block main thread to keep server alive
    demo.block_thread()
