"""StateService: JSON-backed registry for files, indexes, and runs.

Minimal helpers to support the ingest flow prior to embeddings:
- resolve_file_path(file_id): locate uploaded file under data/files/{file_id}/
- create_index(file_id): allocate index_id and create index directory
- write_index_artifacts(index_id, meta, sections, chunks): persist artifacts
"""

from __future__ import annotations

import glob
import json
import os
import time
from typing import Any, Dict, List, Optional

from app.config import Config, ensure_data_dirs
from app.utils.ids import new_id
from app.utils.io_utils import ensure_dir, read_json, write_json


FILES_DB = os.path.join(Config.DB_DIR, "files.json")
INDEXES_DB = os.path.join(Config.DB_DIR, "indexes.json")
RUNS_DB = os.path.join(Config.DB_DIR, "runs.json")


def _load_db(path: str) -> Dict[str, Any]:
    ensure_data_dirs()
    data = read_json(path, default=None)
    if not isinstance(data, dict):
        return {}
    return data


def _save_db(path: str, data: Dict[str, Any]) -> None:
    ensure_data_dirs()
    write_json(path, data)


def resolve_file_path(file_id: str) -> Optional[str]:
    """Return absolute path to uploaded file for given file_id.

    First checks files DB registry; falls back to probing the directory
    data/files/{file_id}/* for a single .pdf or .docx.
    """
    ensure_data_dirs()
    files_db = _load_db(FILES_DB)
    rec = files_db.get(file_id)
    if isinstance(rec, dict):
        path = rec.get("path")
        if path and os.path.exists(path):
            return os.path.abspath(path)

    # Fallback to probing directory
    fdir = os.path.join(Config.FILES_DIR, file_id)
    if os.path.isdir(fdir):
        cand = []
        cand.extend(glob.glob(os.path.join(fdir, "*.pdf")))
        cand.extend(glob.glob(os.path.join(fdir, "*.docx")))
        if len(cand) == 1 and os.path.exists(cand[0]):
            return os.path.abspath(cand[0])
    return None


def create_index(file_id: str) -> str:
    """Allocate a new index_id and create its directory."""
    ensure_data_dirs()
    index_id = new_id("index")
    idir = os.path.join(Config.INDEXES_DIR, index_id)
    ensure_dir(idir)

    # Persist in indexes DB
    idx_db = _load_db(INDEXES_DB)
    idx_db[index_id] = {
        "file_id": file_id,
        "created_at": int(time.time()),
    }
    _save_db(INDEXES_DB, idx_db)
    return index_id


def write_index_artifacts(
    index_id: str,
    meta: Dict[str, Any],
    sections: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
) -> None:
    """Persist index artifacts to disk under data/indexes/{index_id}."""
    idir = os.path.join(Config.INDEXES_DIR, index_id)
    ensure_dir(idir)
    write_json(os.path.join(idir, "meta.json"), meta)
    write_json(os.path.join(idir, "sections.json"), sections)
    write_json(os.path.join(idir, "chunks.json"), chunks)


def register_uploaded_file(
    file_id: str,
    *,
    filename: str,
    mime: str,
    size: int,
    sha1: str,
    ext: str,
    path: str,
) -> Dict[str, Any]:
    """Persist uploaded file metadata in files DB."""
    ensure_data_dirs()
    rec = {
        "file_id": file_id,
        "filename": filename,
        "mime": mime,
        "size": size,
        "sha1": sha1,
        "ext": ext,
        "path": os.path.abspath(path),
        "created_at": int(time.time()),
    }
    db = _load_db(FILES_DB)
    db[file_id] = rec
    _save_db(FILES_DB, db)
    return rec


# -------- Index lookup helpers --------

def get_latest_index_for_file(file_id: str) -> Optional[str]:
    """Return the most recently created index_id for a given file_id, if any."""
    idx_db = _load_db(INDEXES_DB)
    candidates = [
        (iid, meta.get("created_at", 0))
        for iid, meta in idx_db.items()
        if isinstance(meta, dict) and meta.get("file_id") == file_id
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


# -------- Run state helpers --------

def create_run(file_id: str, index_id: str) -> str:
    ensure_data_dirs()
    run_id = new_id("run")
    rdir = os.path.join(Config.RUNS_DIR, run_id)
    ensure_dir(rdir)
    # init structure
    ensure_dir(os.path.join(rdir, "sections"))
    ensure_dir(os.path.join(rdir, "snippets"))
    meta = {
        "run_id": run_id,
        "file_id": file_id,
        "index_id": index_id,
        "status": "running",
        "started_at": int(time.time()),
    }
    write_json(os.path.join(rdir, "meta.json"), meta)
    # registry
    db = _load_db(RUNS_DB)
    db[run_id] = {"file_id": file_id, "index_id": index_id, "created_at": meta["started_at"], "status": "running"}
    _save_db(RUNS_DB, db)
    return run_id


def run_dir(run_id: str) -> str:
    return os.path.join(Config.RUNS_DIR, run_id)


def write_section_artifacts(
    run_id: str,
    name: str,
    *,
    snippets: List[Dict[str, Any]],
    draft_text: str,
    final_text: str,
    warnings: List[str],
    facts: Optional[Dict[str, Any]] = None,
) -> None:
    rdir = run_dir(run_id)
    write_json(os.path.join(rdir, "snippets", f"{name}.json"), snippets)
    write_json(
        os.path.join(rdir, "sections", f"{name}.json"),
        {"name": name, "draft_text": draft_text, "final_text": final_text, "warnings": warnings, "facts": facts},
    )


def finalize_run(run_id: str, status: str = "succeeded") -> None:
    rdir = run_dir(run_id)
    meta = read_json(os.path.join(rdir, "meta.json"), default={}) or {}
    meta.update({"status": status, "finished_at": int(time.time())})
    write_json(os.path.join(rdir, "meta.json"), meta)
    db = _load_db(RUNS_DB)
    if run_id in db:
        db[run_id].update({"status": status, "finished_at": meta["finished_at"]})
    _save_db(RUNS_DB, db)


def build_and_write_run_logs(run_id: str) -> dict:
    """Build a consolidated logs JSON for a run and persist it as logs.json.

    Includes file/index info, embedding model, snippets provenance per section,
    and Procedures facts if present.
    """
    rdir = run_dir(run_id)
    meta = read_json(os.path.join(rdir, "meta.json"), default={}) or {}
    file_id = meta.get("file_id")
    index_id = meta.get("index_id")

    index_meta = {}
    if index_id:
        index_meta = read_json(os.path.join(Config.INDEXES_DIR, index_id, "meta.json"), default={}) or {}

    # Collect snippets per section
    sections = {}
    snippets_dir = os.path.join(rdir, "snippets")
    if os.path.isdir(snippets_dir):
        for name in os.listdir(snippets_dir):
            if not name.endswith(".json"):
                continue
            sec = os.path.splitext(name)[0]
            items = read_json(os.path.join(snippets_dir, name), default=[]) or []
            # Only keep essential provenance fields
            prov = [
                {
                    "chunk_id": it.get("chunk_id"),
                    "page": it.get("page"),
                    "section_path": it.get("section_path"),
                    "heading_norm": it.get("heading_norm"),
                    "score": it.get("score"),
                }
                for it in items
            ]
            sections[sec] = prov

    # Procedures facts if present
    facts = {}
    proc_path = os.path.join(rdir, "sections", "Procedures.json")
    proc = read_json(proc_path, default=None)
    if isinstance(proc, dict) and proc.get("facts"):
        facts = proc.get("facts")

    logs = {
        "run_id": run_id,
        "file_id": file_id,
        "index_id": index_id,
        "embedding_model": index_meta.get("embed_model"),
        "sections": sections,
        "procedure_facts": facts,
    }
    write_json(os.path.join(rdir, "logs.json"), logs)
    return logs
