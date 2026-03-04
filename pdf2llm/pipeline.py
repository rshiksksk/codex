"""Core conversion pipeline."""

from __future__ import annotations

import importlib.metadata
import platform
import shutil
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .normalize import normalize_markdown
from .storage import (
    atomic_write_json,
    atomic_write_text,
    compute_sha256,
    copy_original_pdf,
    make_doc_id,
)
from .tables import extract_tables

STAGES = [
    "hash",
    "convert_docling",
    "fallback_markitdown",
    "normalize_markdown",
    "extract_tables",
    "write_outputs",
]


@dataclass
class ConversionResult:
    success: bool
    doc_id: str | None
    out_dir: Path | None
    metadata: dict[str, Any]


class StageProgress:
    def __init__(self, stages: Iterable[str]) -> None:
        self.stages = list(stages)
        self._backend = "none"
        self._state = None
        try:
            from rich.progress import (
                BarColumn,
                Progress,
                SpinnerColumn,
                TextColumn,
                TimeElapsedColumn,
            )

            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
            )
            task = progress.add_task("Converting PDF", total=len(self.stages))
            progress.start()
            self._backend = "rich"
            self._state = (progress, task)
            return
        except Exception:
            pass

        try:
            from tqdm import tqdm

            bar = tqdm(total=len(self.stages), desc="Converting PDF", unit="stage")
            self._backend = "tqdm"
            self._state = bar
        except Exception:
            self._backend = "none"

    def advance(self, stage: str) -> None:
        if self._backend == "rich":
            progress, task = self._state
            progress.update(task, advance=1, description=f"Stage: {stage}")
        elif self._backend == "tqdm":
            self._state.set_description(f"Stage: {stage}")
            self._state.update(1)

    def close(self) -> None:
        if self._backend == "rich":
            progress, _task = self._state
            progress.stop()
        elif self._backend == "tqdm":
            self._state.close()


def convert_pdf(pdf_path: Path, output_dir: Path | None = None, verbose: bool = True) -> ConversionResult:
    source_file = pdf_path.name
    started_at = _now_iso()

    metadata: dict[str, Any] = {
        "status": "running",
        "stage": STAGES[0],
        "stage_index": 1,
        "num_stages": len(STAGES),
        "started_at": started_at,
        "finished_at": None,
        "source_file": source_file,
        "doc_id": None,
        "sha256": None,
        "timings_sec": {},
        "tool_versions": _tool_versions(),
        "counts": {"tables_detected": 0},
        "fallback_used": False,
        "errors": [],
    }

    doc_id: str | None = None
    out_dir: Path | None = None
    markdown_text = ""
    tables: list[dict[str, Any]] = []
    docling_document: Any | None = None

    progress = StageProgress(STAGES) if verbose else None

    try:
        sha_start = time.perf_counter()
        sha256 = compute_sha256(pdf_path)
        doc_id = make_doc_id(sha256)
        out_dir = output_dir or output_dir_for_pdf(pdf_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        metadata["sha256"] = sha256
        metadata["doc_id"] = doc_id
        metadata["timings_sec"]["hash"] = round(time.perf_counter() - sha_start, 4)
        _write_metadata(metadata, out_dir)
        _log(verbose, f"doc_id: {doc_id}")
        _advance_stage(metadata, out_dir, progress, "hash")

        convert_start = time.perf_counter()
        try:
            markdown_text, docling_document = _convert_with_docling(pdf_path)
        except Exception as exc:
            metadata["errors"].append(f"Docling conversion failed: {exc}")
            metadata["fallback_used"] = True
        metadata["timings_sec"]["convert_docling"] = round(time.perf_counter() - convert_start, 4)
        _advance_stage(metadata, out_dir, progress, "convert_docling")

        fallback_start = time.perf_counter()
        if not markdown_text:
            markdown_text = _convert_with_markitdown(pdf_path)
        metadata["timings_sec"]["fallback_markitdown"] = round(time.perf_counter() - fallback_start, 4)
        _advance_stage(metadata, out_dir, progress, "fallback_markitdown")

        norm_start = time.perf_counter()
        markdown_text = normalize_markdown(markdown_text)
        metadata["timings_sec"]["normalize_markdown"] = round(time.perf_counter() - norm_start, 4)
        _advance_stage(metadata, out_dir, progress, "normalize_markdown")

        tables_start = time.perf_counter()
        try:
            tables = extract_tables(markdown_text, docling_document=docling_document)
        except Exception as exc:
            metadata["errors"].append(f"Table extraction failed: {exc}")
            tables = []
        metadata["counts"]["tables_detected"] = len(tables)
        metadata["timings_sec"]["extract_tables"] = round(time.perf_counter() - tables_start, 4)
        _advance_stage(metadata, out_dir, progress, "extract_tables")

        write_start = time.perf_counter()
        copy_original_pdf(pdf_path, out_dir)
        atomic_write_text(out_dir / "document_text.md", markdown_text)
        atomic_write_json(out_dir / "extracted_tables.json", tables)
        metadata["timings_sec"]["write_outputs"] = round(time.perf_counter() - write_start, 4)
        _advance_stage(metadata, out_dir, progress, "write_outputs")

        metadata["status"] = "success"
        metadata["finished_at"] = _now_iso()
        _write_metadata(metadata, out_dir)
        return ConversionResult(success=True, doc_id=doc_id, out_dir=out_dir, metadata=metadata)

    except Exception as exc:
        metadata["status"] = "failed"
        metadata["finished_at"] = _now_iso()
        metadata["errors"].append(f"Pipeline failed: {exc}")
        metadata["errors"].append(traceback.format_exc())
        if out_dir is None:
            fallback = f"failed_{int(time.time())}"
            out_dir = pdf_path.parent / fallback
            out_dir.mkdir(parents=True, exist_ok=True)
        _write_metadata(metadata, out_dir)
        return ConversionResult(success=False, doc_id=doc_id, out_dir=out_dir, metadata=metadata)
    finally:
        if progress:
            progress.close()


def _convert_with_docling(pdf_path: Path) -> tuple[str, Any | None]:
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = getattr(result, "document", result)

    if hasattr(doc, "export_to_markdown"):
        markdown = doc.export_to_markdown()
    elif hasattr(result, "export_to_markdown"):
        markdown = result.export_to_markdown()
    else:
        raise RuntimeError("Docling did not expose markdown export")

    if not isinstance(markdown, str) or not markdown.strip():
        raise RuntimeError("Docling markdown output empty")
    return markdown, doc


def _convert_with_markitdown(pdf_path: Path) -> str:
    from markitdown import MarkItDown

    md = MarkItDown()
    result = md.convert(str(pdf_path))
    text = getattr(result, "text_content", None)
    if not text:
        raise RuntimeError("MarkItDown returned empty text")
    return text


def _tool_versions() -> dict[str, str]:
    versions = {"python": platform.python_version()}
    for pkg in ("docling", "markitdown"):
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = "not-installed"
    return versions


def _advance_stage(metadata: dict[str, Any], out_dir: Path, progress: StageProgress | None, stage: str) -> None:
    metadata["stage"] = stage
    metadata["stage_index"] = STAGES.index(stage) + 1
    _write_metadata(metadata, out_dir)
    if progress:
        progress.advance(stage)


def _write_metadata(metadata: dict[str, Any], out_dir: Path) -> None:
    atomic_write_json(out_dir / "conversion_metadata.json", metadata)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(verbose: bool, msg: str) -> None:
    if verbose:
        print(msg)


def compute_doc_id_for_file(pdf_path: Path) -> str:
    return make_doc_id(compute_sha256(pdf_path))


def output_dir_for_pdf(pdf_path: Path) -> Path:
    return pdf_path.parent / f"converted_{pdf_path.stem}"


def already_processed(pdf_path: Path) -> bool:
    return output_dir_for_pdf(pdf_path).exists()


def clear_doc_output(pdf_path: Path) -> None:
    """Helper for manual reruns/testing."""
    target = output_dir_for_pdf(pdf_path)
    if target.exists():
        shutil.rmtree(target)
