"""Generate route: POST /generate

Runs per-section retrieval and generation for the requested sections.
Supports multi-query retrieval per section, fuses results, and persists artifacts.
"""

from __future__ import annotations

from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.services.section_queries import SECTION_QUERIES
from app.services.state_service import (
    create_run,
    finalize_run,
    get_latest_index_for_file,
    write_section_artifacts,
)

generate_bp = Blueprint("generate", __name__)


def _resp_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


DEFAULT_SECTIONS = ["Purpose", "Procedures", "Risks", "Benefits"]


@generate_bp.route("/generate", methods=["POST"])
def generate():
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    file_id = payload.get("file_id")
    sections: List[str] = payload.get("sections") or DEFAULT_SECTIONS
    options = payload.get("options") or {}
    mode = options.get("mode", "dense")
    use_section_filter = bool(options.get("use_section_filter", False))

    if not file_id:
        return _resp_error("Missing file_id in request body.")

    index_id = get_latest_index_for_file(file_id)
    if not index_id:
        return _resp_error("No index found for file_id. Run /ingest first.", 404)

    run_id = create_run(file_id, index_id)
    print(f"[RUN {run_id}] Starting parallel generation for sections: {sections}")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def run_section(sec: str) -> tuple[str, Dict[str, Any]]:
        # Create per-thread services to avoid shared-state contention
        rsvc = RetrievalService()
        lsvc = LLMService()

        queries = SECTION_QUERIES.get(sec, [])
        if isinstance(queries, str):  # backward compatibility
            queries = [queries]

        section_arg = sec if use_section_filter else None
        print(f"[RUN {run_id}] [{sec}] Using {len(queries)} queries")

        # Multi-query retrieval + fusion
        all_hits: Dict[str, Dict[str, Any]] = {}
        for q in queries:
            print(f"[RUN {run_id}] [{sec}] → Query: {q[:80]}...")
            results_list = rsvc.search(
                index_id=index_id,
                query=q,
                section=section_arg,
                mode=mode,
                # Optional: bump per-query caps if you want more recall
                # k_dense=20, k_final=20,
            )
            print(f"[RUN {run_id}] [{sec}] → Retrieved {len(results_list)} hits")
            for r in results_list:
                cid = r["chunk_id"]
                if cid not in all_hits:
                    all_hits[cid] = r
                else:
                    all_hits[cid]["score"] += r["score"]

        hits = sorted(all_hits.values(), key=lambda x: x["score"], reverse=True)[:12]
        print(f"[RUN {run_id}] [{sec}] Final fused hits: {len(hits)}")
        # Log each chunk used for generation for visibility
        for rank, h in enumerate(hits, start=1):
            try:
                cid = h.get("chunk_id")
                page = h.get("page")
                sect = h.get("section_path")
                heading = h.get("heading_norm")
                score = h.get("score")
                print(
                    f"[RUN {run_id}] [{sec}]  #{rank:02d} "
                    f"chunk_id={cid} page={page} heading='{heading}' section='{sect}' score={score}"
                )
            except Exception:
                # best-effort logging; do not fail generation on logging
                pass

        # Facts (Procedures only) → write → self-check
        facts = lsvc.extract_procedure_facts(hits) if sec == "Procedures" else None
        draft = lsvc.write_section(sec, hits, facts)
        final = lsvc.self_check(sec, draft, hits)

        warnings: List[str] = []
        if "[[" not in (final or "") or "]]" not in (final or ""):
            warnings.append("No inline citations detected in final text for this section.")
            print(f"[RUN {run_id}] [{sec}] WARNING: No inline citations")

        # Persist section artifacts
        write_section_artifacts(
            run_id,
            sec,
            snippets=hits,
            draft_text=draft,
            final_text=final,
            warnings=warnings,
            facts=facts,
        )

        return sec, {"text": final}

    results: Dict[str, Any] = {}
    # Tune max_workers as you like (I/O + network → threads are fine)
    with ThreadPoolExecutor(max_workers=min(4, len(sections))) as ex:
        futures = [ex.submit(run_section, sec) for sec in sections]
        for f in as_completed(futures):
            sec, out = f.result()
            results[sec] = out

    finalize_run(run_id, status="succeeded")
    print(f"[RUN {run_id}] Completed parallel generation")

    return jsonify({"run_id": run_id, "status": "succeeded", "sections": results})
