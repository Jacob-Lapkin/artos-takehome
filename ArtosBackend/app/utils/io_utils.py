"""IO utilities for safe JSON and file operations.

Provides:
- ``ensure_dir(path)``: create directories if missing (no error if exists).
- ``read_json(path, default=None)``: read JSON file; return default on missing.
- ``write_json(path, data)``: atomic write of JSON to file.
- ``file_sha1(path)``: compute sha1 digest of a file.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Optional
import hashlib


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def read_json(path: str, default: Optional[Any] = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write_json(path: str, data: Any) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def file_sha1(path: str, chunk_size: int = 1024 * 1024) -> str:
    sha1 = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha1.update(chunk)
    return sha1.hexdigest()

