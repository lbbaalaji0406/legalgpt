import os
import sys
from huggingface_hub import HfApi

TOKEN = os.environ.get("HF_TOKEN")
if not TOKEN and os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("HF_TOKEN="):
                TOKEN = line.strip().split("=", 1)[1].strip("\"'")

REPO_ID = os.environ.get("HF_REPO_ID", "Lvvbaaal/legalgpt-api")

if not TOKEN:
    print("Error: HF_TOKEN environment variable not set. Please set it or add to .env")
    sys.exit(1)

print(f"Connecting to Hugging Face Space: {REPO_ID}...")
api = HfApi(token=TOKEN)

ignore = [
    "deploy_hf.py",
    ".git/**",
    ".venv/**",
    "node_modules/**",
    "saulgpt-ui/node_modules/**",
    "**/__pycache__/**",
    "*.pyc",
    ".env*",
    "*.env",
    "backend/.env",
    ".firebase/**",
    "dist/**",
    "saulgpt-ui/dist/**",
    "scratch/**",
    "build/**"
]

print("Uploading workspace folder directly to Space...")
try:
    api.upload_folder(
        folder_path=".",
        repo_id=REPO_ID,
        repo_type="space",
        ignore_patterns=ignore,
        commit_message="Deploy backend updates from local workspace"
    )
    print("Successfully uploaded workspace to Hugging Face Space!")
except Exception as e:
    print(f"Upload failed: {e}")
    sys.exit(1)
