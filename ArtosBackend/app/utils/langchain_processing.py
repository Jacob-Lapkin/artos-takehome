"""LangChain-based document processing for RAG pipeline.

This module provides a simpler, more robust alternative to the custom
PDF parsing, section detection, and chunking logic.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional
import logging

try:
    from langchain_community.document_loaders import PyMuPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    import tiktoken
except ImportError as e:
    raise ImportError(f"Required LangChain dependencies not installed: {e}")


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken, with fallback to character-based estimation."""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Fallback: ~4 chars per token
        return max(1, len(text) // 4)


