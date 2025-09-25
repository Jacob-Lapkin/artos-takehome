"""Search route (debug): POST /search

Uses RetrievalService to perform hybrid retrieval over an index and
returns top hits with metadata and fused scores for debugging/tuning.
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify, request

from app.services.retrieval_service import RetrievalService


search_bp = Blueprint("search", __name__)


def _resp_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@search_bp.route("/search", methods=["POST"])
def search():
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    index_id = payload.get("index_id")
    query = payload.get("query")
    section = payload.get("section")
    k = int(payload.get("k", 8))
    mode = payload.get("mode", "dense")
    search_type = payload.get("search_type", "mmr")
    search_kwargs = payload.get("search_kwargs") or {}
    if not index_id or not query:
        return _resp_error("Missing index_id or query.")

    svc = RetrievalService()
    try:
        hits = svc.search(
            index_id=index_id,
            query=query,
            section=section,
            mode=mode,
            k_dense=k,
            k_final=k,
            search_type=search_type,
            search_kwargs=search_kwargs,
        )
    except Exception as e:
        return _resp_error(f"Retrieval error: {e}", 500)

    # Shape concise output for debug
    out_hits = [
        {
            "chunk_id": h.get("chunk_id"),
            "page": h.get("page"),
            "section_path": h.get("section_path"),
            "heading_norm": h.get("heading_norm"),
            "preview": (h.get("text") or "")[:300],
            "score": h.get("score"),
            "source_scores": h.get("source_scores"),
        }
        for h in hits
    ]
    return jsonify({"hits": out_hits})
