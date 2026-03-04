# pdf2llm

Minimal local PDF converter for scientific papers.

## What it does

Given a PDF, `pdf2llm` writes:

- `document_text.md`: cleaned Markdown text
- `extracted_tables.json`: structured table arrays
- `conversion_metadata.json`: status, timings, counts, errors, versions

Outputs are stored next to the input PDF in:

```text
/path/to/input/converted_<input_name>/
  original.pdf
  document_text.md
  extracted_tables.json
  conversion_metadata.json
```

Example for `paper.pdf`:

```text
/path/to/input/converted_paper/
```

`doc_id` is deterministic from SHA256 bytes of the PDF:
`sha256_<first16hex>`.

## Install (recommended: Miniforge/Conda, no venv in project)

If you do **not** want a `.venv` folder inside the project, use Miniforge/Conda:

1. Install **Miniforge**: https://github.com/conda-forge/miniforge
2. Open terminal (or Miniforge Prompt)
3. Create an environment (stored outside your project):

```bash
conda create -n pdf2llm python=3.11 -y
conda activate pdf2llm
```

4. Go to your project folder and install:

```bash
cd /path/to/your/project
pip install -e .
```

Optional extras:

```bash
pip install -e .[rich]   # prettier progress bar
pip install -e .[api]    # tiny FastAPI endpoints (not required)
```

## Windows (easy step-by-step with Miniforge)

If you are on Windows and not very technical, follow this checklist:

1. Install **Miniforge for Windows** (link above).
2. Open **Miniforge Prompt** (from Start menu).
3. Create and activate env:

```bash
conda create -n pdf2llm python=3.11 -y
conda activate pdf2llm
```

4. Move to your project folder:

```bash
cd C:\path\to\your\project
```

5. Install this tool:

```bash
pip install -e .
```

6. Convert one PDF:

```bash
python -m pdf2llm convert "C:\path\to\paper.pdf"
```

7. Find outputs next to your PDF:

```text
C:\path\to\your\pdf\folder\converted_paper\
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
- skips already processed docs by checking `converted_<input_name>` folder
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

## Troubleshooting (Windows)

If conversion fails with `WinError 1314` during Docling model download:

- Enable **Developer Mode** in Windows, or run your terminal as Administrator once.
- Then retry conversion.

If fallback fails with a `markitdown` PDF dependency error:

```bash
pip install -U "markitdown[pdf]"
```

If you installed this package before this fix, reinstall dependencies:

```bash
pip install -U -e .
```

## Optional tiny API

If installed with `.[api]`, you can create a small wrapper service around the same pipeline.
This repo currently prioritizes CLI simplicity.
