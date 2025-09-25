from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify, request

from app.services.refinement_service import RefinementService


refine_bp = Blueprint("refine", __name__)


def _resp_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@refine_bp.route("/refine", methods=["POST"])
def refine():
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    run_id = payload.get("run_id")
    file_id = payload.get("file_id")
    try:
        svc = RefinementService()
        if run_id:
            out = svc.refine_run(run_id)
        elif file_id:
            sections = payload.get("sections")
            options = payload.get("options") or {}
            out = svc.generate_then_refine(
                file_id,
                sections=sections,
                mode=options.get("mode", "dense"),
                use_section_filter=bool(options.get("use_section_filter", False)),
            )
        else:
            return _resp_error("Provide either run_id to refine, or file_id to generate+refine.")
        return jsonify(out)
    except Exception as e:
        return _resp_error(f"Refinement failed: {e}", 500)
