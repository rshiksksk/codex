# pdf2llm

Minimal local PDF converter for scientific papers.

## What it does

Given a PDF, `pdf2llm` writes:

- `document_text.md`: cleaned Markdown text
- `extracted_tables.json`: structured table arrays
- `conversion_metadata.json`: status, timings, counts, errors, versions

Outputs are stored in:

```text
data/{doc_id}/
  original.pdf
  document_text.md
  extracted_tables.json
  conversion_metadata.json
```

`doc_id` is deterministic from SHA256 bytes of the PDF:
`sha256_<first16hex>`.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Optional extras:

```bash
pip install -e .[rich]   # prettier progress bar
pip install -e .[api]    # tiny FastAPI endpoints (not required)
```

## Usage

### Convert one PDF

```bash
python -m pdf2llm convert /path/to/file.pdf
```

Behavior:

- prints `doc_id`
- stage-based progress bar
- writes partial metadata even if failure happens
- exits `0` on success, non-zero on failure

### Convert a folder

```bash
python -m pdf2llm batch /path/to/folder --glob "*.pdf"
```

Behavior:

- processes matching PDFs
- skips already processed docs by checking `data/{doc_id}`
- continues on errors and prints summary at the end

## Pipeline stages

In fixed order:

1. `hash`
2. `convert_docling`
3. `fallback_markitdown` (only used when Docling fails)
4. `normalize_markdown`
5. `extract_tables`
6. `write_outputs`

`conversion_metadata.json` is atomically rewritten after each stage.

## Extraction details

- Primary converter: Docling (`DocumentConverter`)
- Fallback for Markdown only: MarkItDown
- Markdown normalization:
  - newline normalization to `\n`
  - remove trailing spaces
  - fix hyphenated line breaks (`word-\nword -> wordword`)
  - collapse 3+ blank lines to 2
- Table extraction:
  - use Docling table objects if available
  - otherwise parse markdown tables (`|` format)

## Known limitations

- Table `caption` and `page` may be `null` when source tools do not provide them.
- Figure/image extraction is intentionally out of scope.
- No chunking, embeddings, or external LLM calls.

## Optional tiny API

If installed with `.[api]`, you can create a small wrapper service around the same pipeline.
This repo currently prioritizes CLI simplicity.
