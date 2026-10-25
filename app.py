"""
SaulGPT — Hugging Face Spaces Deployment Entrypoint
===================================================
Runs the complete SaulGPT FastAPI backend with Supabase PostgreSQL
and mounts a Gradio status & monitoring interface on port 7860.
"""

import sys
import os

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

# Import the production FastAPI application
from api_server import app as fastapi_app
import gradio as gr
import uvicorn

# Build a clean Gradio status block
with gr.Blocks(title="SaulGPT Legal Intelligence API Server") as demo:
    gr.Markdown("# ⚖️ SaulGPT Legal Intelligence API Server")
    gr.Markdown(
        """
        ### 🟢 Engine Status: ONLINE & ACTIVE
        Welcome to the **SaulGPT Legal Intelligence Cloud Backend**.
        
        - **Hardware**: ZeroGPU / 16 GB High-Performance Environment
        - **Database**: Supabase PostgreSQL (Permanent History Persistence)
        - **Vector Engine**: ChromaDB Hybrid Retrieval (BNS 2023, BNSS 2023, BSA 2023, Constitution)
        - **Verification**: Actor-Critic PRM & Scrutiny Hallucination Guardrails
        - **Trial Studio**: Moot Court Arena & Section 63 BSA Evidence Grounding
        
        #### Available API Endpoints:
        - `POST /api/chat` — Complete legal intelligence pipeline (BNS/BNSS/BSA + IPC/CrPC)
        - `GET /api/conversations` — Synced multi-device conversation history
        - `POST /api/auth/login` & `register` — Cloud authentication
        - `POST /api/upload` — Contract Red Pen Evaluator
        - `POST /api/trial/start` — Trial Studio & Moot Court simulation
        """
    )

# Mount FastAPI app onto Gradio (FastAPI handles all /api routes; Gradio handles /)
app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting SaulGPT API server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
