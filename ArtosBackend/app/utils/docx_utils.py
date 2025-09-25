"""DOCX parsing helpers using python-docx.

Functions:
- ``extract_docx_blocks(path)``: returns a list of paragraph blocks with
  heading levels when available. Page numbers are not available in DOCX;
  we set page=1 as a placeholder.

Block schema:
- ``page``: always 1 (DOCX has no fixed pagination here)
- ``text``: paragraph text
- ``level``: int heading level if style indicates a heading, else None
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

try:
    from docx import Document
except Exception:  # pragma: no cover - import optional
    Document = None  # type: ignore


def _heading_level(style_name: Optional[str]) -> Optional[int]:
    if not style_name:
        return None
    name = style_name.strip().lower()
    if name.startswith("heading "):
        try:
            return int(name.split(" ", 1)[1])
        except Exception:
            return 1
    return None


def extract_docx_blocks(path: str) -> List[Dict[str, Any]]:
    """Extract paragraphs and heading levels from a DOCX file.

    If python-docx is unavailable, returns an empty list.
    """
    if Document is None:
        return []

    doc = Document(path)
    blocks: List[Dict[str, Any]] = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        level = _heading_level(getattr(p.style, "name", None))
        blocks.append({"page": 1, "text": text, "level": level})
    return blocks

