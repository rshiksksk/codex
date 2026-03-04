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

## Windows (easy step-by-step)

If you are on Windows and not very technical, follow this exact checklist:

1. Install **Python 3.10+** from https://www.python.org/downloads/windows/
   - During install, check **"Add Python to PATH"**.
2. Open **PowerShell** (Start menu -> type `PowerShell`).
3. Go to your project folder:

```powershell
cd C:\path\to\your\project
```

4. Create a virtual environment:

```powershell
py -m venv .venv
```

5. Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

6. Install this tool:

```powershell
pip install -e .
```

7. Convert one PDF:

```powershell
python -m pdf2llm convert "C:\path\to\paper.pdf"
```

8. Find outputs in:

```text
C:\path\to\your\project\data\sha256_xxxxxxxxxxxxxxxx\
```

If PowerShell blocks activation, run this once in PowerShell and try step 5 again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
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
