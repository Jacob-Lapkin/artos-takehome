"""Upload route: POST /upload

Accepts a multipart file (.pdf or .docx), validates type and size,
persists the raw file in `data/files/{file_id}/source.ext`, and returns
metadata: { file_id, filename, mime, size }.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from flask import Blueprint, jsonify, request

from app.config import Config, ensure_data_dirs
from app.services.state_service import register_uploaded_file
from app.utils.ids import new_id
from app.utils.io_utils import ensure_dir, file_sha1

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None  # type: ignore


upload_bp = Blueprint("upload", __name__)


def _resp_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _validate_pdf_not_encrypted(path: str) -> Tuple[bool, str]:
    if fitz is None:
        return True, ""
    try:
        doc = fitz.open(path)
        # older versions: check needs_pass; newer: is_encrypted
        needs = getattr(doc, "needs_pass", False) or getattr(doc, "is_encrypted", False)
        if needs:
            return False, "PDF is password-protected."
        return True, ""
    except Exception:
        # If open fails, let ingest report issues later
        return True, ""


@upload_bp.route("/upload", methods=["POST"])
def upload():
    ensure_data_dirs()
    if "file" not in request.files:
        return _resp_error("No file part in the request.")
    f = request.files["file"]
    if not f or f.filename == "":
        return _resp_error("No file selected for upload.")

    orig_name = f.filename
    mime = f.mimetype or "application/octet-stream"
    ext = os.path.splitext(orig_name)[1].lower()
    if ext not in Config.ALLOWED_EXTS:
        return _resp_error("Only .pdf or .docx files are allowed.")

    # Save to destination folder
    file_id = new_id("file")
    fdir = os.path.join(Config.FILES_DIR, file_id)
    ensure_dir(fdir)
    dest = os.path.join(fdir, f"source{ext}")
    f.save(dest)

    # Size check
    size = os.path.getsize(dest)
    if size > Config.MAX_UPLOAD_MB * 1024 * 1024:
        try:
            os.remove(dest)
        except Exception:
            pass
        return _resp_error(f"File too large; max {Config.MAX_UPLOAD_MB} MB.")

    # PDF encryption check
    if ext == ".pdf":
        ok, msg = _validate_pdf_not_encrypted(dest)
        if not ok:
            try:
                os.remove(dest)
            except Exception:
                pass
            return _resp_error(msg)

    sha1 = file_sha1(dest)
    rec = register_uploaded_file(
        file_id,
        filename=orig_name,
        mime=mime,
        size=size,
        sha1=sha1,
        ext=ext,
        path=dest,
    )

    return jsonify({"file_id": file_id, "filename": rec["filename"], "mime": rec["mime"], "size": rec["size"]})

