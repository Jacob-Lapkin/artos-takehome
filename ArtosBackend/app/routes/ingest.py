from __future__ import annotations

import os
import time
from typing import Any, Dict
import logging

from flask import Blueprint, jsonify, request

from app.config import Config, ensure_data_dirs
from app.services.state_service import create_index, resolve_file_path
from app.services.vectorstore_service import VectorStoreService

"""Ingest route: POST /ingest

Simple route that delegates everything to VectorStoreService.

Request JSON: { file_id, store? }
Response JSON: { index_id, n_chunks, store, pages, created_at }
"""

ingest_bp = Blueprint("ingest", __name__)


def _resp_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@ingest_bp.route("/ingest", methods=["POST"])
def ingest():
    ensure_data_dirs()
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    file_id = payload.get("file_id")
    
    if not file_id:
        return _resp_error("Missing file_id in request body.")

    # Resolve file path
    path = resolve_file_path(file_id)
    if not path or not os.path.exists(path):
        return _resp_error("File not found for given file_id.", 404)

    # Validate file type
    ext = os.path.splitext(path)[1].lower()
    if ext != ".pdf":
        return _resp_error("Unsupported file type; only .pdf is supported.", 400)

    # Create index
    index_id = create_index(file_id)
    logging.info(f"Processing PDF {file_id} → index {index_id}")

    # Let VectorStoreService handle EVERYTHING
    vss = VectorStoreService()
    try:
        vstats = vss.build_from_pdf(path, file_id, index_id)
        
        # Extract response data from stats
        n_chunks = vstats.get("n_chunks", 0)
        pages = vstats.get("chunk_stats", {}).get("total_chunks", 1)  # fallback
        toc_detected = vstats.get("toc_detected", False)
        text_enhanced = vstats.get("text_sections_enhanced", 0)
        
        logging.info(
            f"Successfully processed {file_id}: {n_chunks} chunks, "
            f"TOC: {toc_detected}, enhanced: {text_enhanced}"
        )
        
        return jsonify({
            "index_id": index_id,
            "n_chunks": n_chunks,
            "store": "faiss",
            "pages": pages,
            "created_at": int(time.time()),
            "enhancement_stats": {
                "toc_detected": toc_detected,
                "text_sections_enhanced": text_enhanced
            }
        })
        
    except Exception as e:
        logging.exception("PDF processing failed for %s", file_id)
        return jsonify({
            "error": f"PDF processing failed: {str(e)}",
            "index_id": index_id,
            "stage": "processing_failed"
        }), 500