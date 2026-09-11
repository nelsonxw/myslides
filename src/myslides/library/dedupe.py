"""
Deduplication utilities: SHA-256 and per-slide structural hashing.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def file_sha256(path: Path | str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_slide_structural_hash(slide_dict: dict) -> str:
    """
    Compute a normalized structural hash for a slide based on shape types,
    rough positions, and text lengths (ignoring exact wording to detect layout twins).
    """
    h = hashlib.sha256()
    shapes = slide_dict.get("shapes", [])
    # Sort shapes by rough coordinate (y // 50, x // 50)
    for s in shapes:
        shape_type = str(s.get("type", ""))
        left = int(s.get("left", 0) // 50)
        top = int(s.get("top", 0) // 50)
        width = int(s.get("width", 0) // 50)
        height = int(s.get("height", 0) // 50)
        text_len = len(s.get("text", "")) // 20
        h.update(f"{shape_type}:{left}:{top}:{width}:{height}:{text_len}|".encode("utf-8"))
    return h.hexdigest()
