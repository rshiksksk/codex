"""CLI entrypoints for pdf2llm."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import already_processed, convert_pdf, ensure_base_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pdf2llm", description="Convert scientific PDFs to markdown + tables")
    sub = parser.add_subparsers(dest="command", required=True)

    p_convert = sub.add_parser("convert", help="Convert one PDF")
    p_convert.add_argument("pdf", type=Path, help="Path to input PDF")
    p_convert.add_argument("--data-dir", type=Path, default=Path("data"), help="Output base directory")

    p_batch = sub.add_parser("batch", help="Convert a folder of PDFs")
    p_batch.add_argument("folder", type=Path, help="Folder containing PDFs")
    p_batch.add_argument("--glob", default="*.pdf", help="Glob pattern (default: *.pdf)")
    p_batch.add_argument("--data-dir", type=Path, default=Path("data"), help="Output base directory")

    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "convert":
            ensure_base_dir(args.data_dir)
            result = convert_pdf(args.pdf, base_data_dir=args.data_dir, verbose=True)
            if result.doc_id:
                print(f"doc_id={result.doc_id}")
            return 0 if result.success else 1

        if args.command == "batch":
            ensure_base_dir(args.data_dir)
            pdfs = sorted(args.folder.glob(args.glob))
            failures: list[tuple[Path, str | None]] = []
            converted = 0
            skipped = 0

            for pdf in pdfs:
                if not pdf.is_file():
                    continue
                if already_processed(args.data_dir, pdf):
                    skipped += 1
                    print(f"skip (already processed): {pdf}")
                    continue

                result = convert_pdf(pdf, base_data_dir=args.data_dir, verbose=True)
                if result.success:
                    converted += 1
                    print(f"ok: {pdf} -> {result.doc_id}")
                else:
                    failures.append((pdf, result.doc_id))
                    print(f"failed: {pdf}")

            print(f"batch summary: converted={converted} skipped={skipped} failed={len(failures)}")
            if failures:
                for pdf, doc_id in failures:
                    print(f" - {pdf} (doc_id={doc_id})")
                return 1
            return 0

        parser.print_help()
        return 2
    except Exception as exc:
        print(f"fatal cli error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run())
