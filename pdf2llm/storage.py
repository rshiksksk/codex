"""Storage and filesystem helpers."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_doc_id(sha256_hex: str) -> str:
    return f"sha256_{sha256_hex[:16]}"


def ensure_output_dir(base_dir: Path, doc_id: str) -> Path:
    out_dir = base_dir / doc_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def copy_original_pdf(src_pdf: Path, out_dir: Path) -> Path:
    dst = out_dir / "original.pdf"
    data = src_pdf.read_bytes()
    atomic_write_bytes(dst, data)
    return dst


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, content.encode(encoding))


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
