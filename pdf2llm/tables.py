"""Table extraction utilities."""

from __future__ import annotations

import re
from typing import Any

_ALIGN_CELL_RE = re.compile(r"^:?-{3,}:?$")


def extract_tables(markdown: str, docling_document: Any | None = None) -> list[dict[str, Any]]:
    """Extract tables preferring docling table data if available, else markdown parsing."""
    docling_tables = _extract_docling_tables(docling_document)
    if docling_tables:
        return docling_tables
    return _extract_markdown_tables(markdown)


def _extract_docling_tables(doc: Any | None) -> list[dict[str, Any]]:
    if doc is None:
        return []

    tables_attr = getattr(doc, "tables", None)
    if not tables_attr:
        return []

    parsed: list[dict[str, Any]] = []
    for idx, table in enumerate(tables_attr, start=1):
        columns: list[str] = []
        rows: list[list[str]] = []

        table_data = getattr(table, "data", None)
        if isinstance(table_data, dict):
            columns = [str(c) for c in table_data.get("columns", [])]
            rows = [[str(cell) for cell in r] for r in table_data.get("rows", [])]
        elif hasattr(table, "to_dict"):
            as_dict = table.to_dict()
            columns = [str(c) for c in as_dict.get("columns", [])]
            rows = [[str(cell) for cell in r] for r in as_dict.get("rows", [])]

        if not columns and not rows:
            continue

        parsed.append(
            {
                "table_id": f"table_{idx:03d}",
                "caption": getattr(table, "caption", None),
                "page": getattr(table, "page", None),
                "columns": columns,
                "rows": rows,
            }
        )
    return parsed


def _extract_markdown_tables(markdown: str) -> list[dict[str, Any]]:
    lines = markdown.splitlines()
    tables: list[dict[str, Any]] = []
    i = 0
    while i < len(lines) - 1:
        if "|" not in lines[i] or "|" not in lines[i + 1]:
            i += 1
            continue

        header = _split_md_row(lines[i])
        align = _split_md_row(lines[i + 1])

        if not header or not _is_alignment_row(align):
            i += 1
            continue

        data_rows: list[list[str]] = []
        j = i + 2
        while j < len(lines) and "|" in lines[j]:
            parsed_row = _split_md_row(lines[j])
            if parsed_row:
                data_rows.append(_normalize_row_len(parsed_row, len(header)))
            j += 1

        tables.append(
            {
                "table_id": f"table_{len(tables) + 1:03d}",
                "caption": None,
                "page": None,
                "columns": _normalize_row_len(header, len(header)),
                "rows": data_rows,
            }
        )
        i = j
    return tables


def _split_md_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    cells = [cell.strip() for cell in text.split("|")]
    return cells if any(cells) else []


def _is_alignment_row(row: list[str]) -> bool:
    return bool(row) and all(_ALIGN_CELL_RE.match(cell.replace(" ", "")) for cell in row)


def _normalize_row_len(row: list[str], length: int) -> list[str]:
    if len(row) == length:
        return row
    if len(row) < length:
        return row + [""] * (length - len(row))
    return row[:length]
