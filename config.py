"""
Central configuration for the AI Research Assistant backend.
Reads settings from environment variables (see .env.example).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Anthropic API ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))

# --- Storage paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "app.db")

os.makedirs(UPLOADS_DIR, exist_ok=True)

# --- Agent behavior ---
MAX_REASONING_STEPS = int(os.getenv("MAX_REASONING_STEPS", "6"))   # multi-step reasoning cap
MEMORY_SUMMARY_TRIGGER = int(os.getenv("MEMORY_SUMMARY_TRIGGER", "20"))  # messages before summarizing
DOC_CHUNK_SIZE = 800        # characters per document chunk
DOC_CHUNK_OVERLAP = 150
DOC_TOP_K = 4                # chunks returned per document search

# --- Web search ---
WEB_SEARCH_MAX_RESULTS = 5
