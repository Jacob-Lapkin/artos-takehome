"""ID helpers for run/file/index IDs and content hashes.

Provides:
- ``new_id(prefix)``: returns a time-sortable ID string with the given prefix
  (e.g., ``file_0001695400000-3f2a...``). Not a true ULID but stable and sortable.
- ``compute_sha1(data)``: returns a sha1 hex digest for strings or bytes.
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from typing import Union


def new_id(prefix: str) -> str:
    """Generate a time-sortable unique ID with the given prefix.

    Format: ``{prefix}_{millis}-{uuid16}``
    """
    millis = int(time.time() * 1000)
    rand = uuid.uuid4().hex[:16]
    return f"{prefix}_{millis:013d}-{rand}"


def compute_sha1(data: Union[str, bytes]) -> str:
    """Compute a sha1 hex digest of input data.

    Accepts a string (encoded as utf-8) or bytes and returns the
    hexadecimal digest string.
    """
    if isinstance(data, str):
        data = data.encode("utf-8", errors="ignore")
    h = hashlib.sha1()
    h.update(data)
    return h.hexdigest()

