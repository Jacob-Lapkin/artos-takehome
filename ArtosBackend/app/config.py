"""Configuration for environment variables and runtime knobs.

Provides a simple config object with data paths and chunking parameters.
This keeps the rest of the codebase decoupled from direct env access.
"""

from __future__ import annotations

import os


class Config:
    # Base
    ARTOS_ENV = os.getenv("ARTOS_ENV", "dev")
    DATA_DIR = os.getenv("ARTOS_DATA_DIR", os.path.abspath(os.path.join(os.getcwd(), "data")))

    # Subdirs
    FILES_DIR = os.path.join(DATA_DIR, "files")
    INDEXES_DIR = os.path.join(DATA_DIR, "indexes")
    RUNS_DIR = os.path.join(DATA_DIR, "runs")
    DB_DIR = os.path.join(DATA_DIR, "db")

    # Chunking defaults
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1100"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

    # Embedding/LLM placeholders (not used in this step)
    # Gemini embedding model via langchain-google-genai
    EMBED_MODEL = os.getenv("EMBED_MODEL", "models/gemini-embedding-001")
    # Default chat model for generation (can override via env)
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

    # Upload limits and whitelist
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
    ALLOWED_EXTS = {".pdf", ".docx"}

    # Section-specific dense retrieval defaults (LangChain retriever)
    # NOTE: Removed duplicate, and removed risky score_threshold for "Risks".
    SECTION_RETRIEVAL_CONFIGS = {
        "Purpose": {
            "search_type": "mmr",
            "search_kwargs": {"k": 6, "lambda_mult": 0.75, "fetch_k": 20},
        },
        "Procedures": {
            "search_type": "mmr",
            "search_kwargs": {"k": 12, "lambda_mult": 0.25, "fetch_k": 40},
        },
        "Risks": {
            # Use plain similarity (no threshold) to avoid empty results
            "search_type": "similarity",
            "search_kwargs": {"k": 12},
        },
        "Benefits": {
            "search_type": "similarity",
            "search_kwargs": {"k": 8},
        },
    }

def ensure_data_dirs(cfg: Config = Config) -> None:
    """Ensure required data directories exist."""
    for p in [cfg.DATA_DIR, cfg.FILES_DIR, cfg.INDEXES_DIR, cfg.RUNS_DIR, cfg.DB_DIR]:
        os.makedirs(p, exist_ok=True)
