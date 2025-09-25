"""Runs routes: GET /runs/<run_id>, /runs/<run_id>/logs, /runs/<run_id>/docx

Provides pollable status and partial results for a generation run and returns
a consolidated log JSON with provenance and facts. (DOCX download TBD.)
"""

from __future__ import annotations

import os
from typing import Any, Dict

from flask import Blueprint, jsonify, send_file

from app.services.state_service import run_dir, build_and_write_run_logs
from app.services.assembly_service import AssemblyService
from app.utils.io_utils import read_json


runs_bp = Blueprint("runs", __name__)


@runs_bp.get("/runs/<run_id>")
def get_run(run_id: str):
    rdir = run_dir(run_id)
    meta = read_json(os.path.join(rdir, "meta.json"), default=None)
    if not isinstance(meta, dict):
        return jsonify({"error": "run not found"}), 404

    # Collect final texts per section
    sections_dir = os.path.join(rdir, "sections")
    sections: Dict[str, Any] = {}
    if os.path.isdir(sections_dir):
        for name in os.listdir(sections_dir):
            if not name.endswith(".json"):
                continue
            sec = os.path.splitext(name)[0]
            data = read_json(os.path.join(sections_dir, name), default={}) or {}
            sections[sec] = {
                "text": data.get("final_text") or data.get("draft_text"),
                "warnings": data.get("warnings") or [],
            }

    return jsonify({"run_id": run_id, "status": meta.get("status"), "sections": sections})


@runs_bp.get("/runs/<run_id>/logs")
def get_run_logs(run_id: str):
    rdir = run_dir(run_id)
    logs_path = os.path.join(rdir, "logs.json")
    logs = read_json(logs_path, default=None)
    if not isinstance(logs, dict):
        # Build logs on-the-fly if missing
        try:
            logs = build_and_write_run_logs(run_id)
        except Exception as e:
            return jsonify({"error": f"failed to build logs: {e}"}), 500
    return jsonify(logs)


@runs_bp.get("/runs/<run_id>/docx")
def get_run_docx(run_id: str):
    rdir = run_dir(run_id)
    # If assembled doc exists, serve it; else build it
    try:
        for name in os.listdir(rdir):
            if name.startswith("ICF_") and name.endswith(".docx"):
                return send_file(os.path.join(rdir, name), as_attachment=True)
    except Exception:
        pass
    try:
        svc = AssemblyService()
        out = svc.render_docx(run_id)
        return send_file(out, as_attachment=True)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"DOCX Generation Error: {error_details}")  # This will show in Flask logs
        return jsonify({"error": f"failed to render docx: {str(e)}", "details": error_details}), 500