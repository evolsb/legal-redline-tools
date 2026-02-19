# legal-redline-tools

Apply tracked changes to Word documents and generate lawyer-style redline PDFs. Pure Python, JSON-driven, designed for AI agent pipelines.

## The Problem

Every AI contract review tool can *analyze* contracts, but none can produce the actual tracked-changes `.docx` or visual redline PDF that lawyers need. python-docx has [refused to add tracked changes for 9 years](https://github.com/python-openxml/python-docx/issues/340). This tool fills that gap.

## What It Does

Takes an original `.docx` and a list of text changes (as JSON), and produces:

1. **Tracked-changes `.docx`** — Real Word tracked changes (strikethrough + insertion) that recipients can accept/reject
2. **Full-document redline PDF** — The entire contract rendered with inline red strikethrough and blue underline, plus a summary page (like Workshare/DeltaView output)
3. **Summary PDF** — A schedule of proposed changes with section references and rationale

## Install

```bash
pip install legal-redline-tools
```

Or from source:
```bash
git clone https://github.com/evolsb/legal-redline-tools.git
cd legal-redline-tools
pip install -e .
```

## Usage

### CLI

```bash
# All three outputs at once:
legal-redline original.docx output.docx \
    --from-json redlines.json \
    --pdf full-redline.pdf \
    --summary-pdf summary.pdf \
    --header "Proposed Redlines — Feb 2026"

# Just the tracked-changes .docx:
legal-redline original.docx output.docx \
    --replace "old text" "new text" \
    --delete "text to remove" \
    --insert-after "anchor text" "new text to add"

# Just the full-document redline PDF:
legal-redline original.docx --no-docx \
    --from-json redlines.json \
    --pdf redline.pdf \
    --header "MC Comments — 01.09.26"
```

### Python API

```python
from legal_redline import apply_redlines, render_redline_pdf, generate_summary_pdf

redlines = [
    {"type": "replace", "old": "20% of fees", "new": "100% of fees or $250K"},
    {"type": "delete", "text": "shall terminate without liability"},
    {"type": "insert_after", "anchor": "Effective Date", "text": ". 90-day termination right"},
]

# Tracked-changes .docx
apply_redlines("original.docx", "output.docx", redlines, author="Chris Sheehan")

# Full-document redline PDF
render_redline_pdf("original.docx", redlines, "redline.pdf",
                   header_text="Proposed Redlines")

# Summary PDF
generate_summary_pdf(redlines, "summary.pdf",
                     doc_title="Merchant Agreement v3",
                     doc_parties="Acme Corp / Vendor Inc.")
```

### JSON Format

```json
[
    {
        "type": "replace",
        "old": "text to find and replace",
        "new": "replacement text",
        "section": "7.2",
        "title": "Liability Cap",
        "rationale": "20% is below market standard"
    },
    {
        "type": "delete",
        "text": "text to remove"
    },
    {
        "type": "insert_after",
        "anchor": "text to insert after",
        "text": "new text to add"
    }
]
```

Optional fields (`section`, `title`, `rationale`) are used in PDF outputs for section references and explanatory notes.

## Output Formats

### Tracked-Changes `.docx`

Produces a standard Word document with OOXML tracked changes (`w:ins` / `w:del` elements). Recipients can:
- View changes in Word's Review pane
- Accept or reject individual changes
- Accept all changes at once

**Note:** Google Docs does not properly render Word tracked changes. Use Word (desktop or online), LibreOffice, or any app that supports OOXML revisions.

### Full-Document Redline PDF

Renders the entire contract as a PDF with:
- **Red strikethrough** for deleted text
- **Blue underline** for inserted text
- **Change bars** in the left margin next to modified paragraphs
- **Header** on every page
- **Page numbers**
- **Summary page** at the end with legend, statistics, and a table of all changes

This matches the output format of professional document comparison tools like Workshare and DeltaView.

### Summary PDF

A standalone schedule of proposed changes showing:
- Each change with section reference, type, current/proposed text
- Strikethrough and underline formatting
- Rationale for each change
- Legend and metadata

## Use with AI Agents

This tool is designed to be the "last mile" in AI contract review pipelines. A typical workflow:

1. **AI analyzes** the contract and identifies issues
2. **AI generates** a JSON list of proposed changes
3. **legal-redline-tools** produces the tracked-changes `.docx` and redline PDF
4. **Lawyer reviews** the output and sends to counterparty

Works with any AI system that can output JSON — Claude, GPT, or custom pipelines.

## Requirements

- Python 3.9+
- python-docx
- lxml
- fpdf2

## Related

- [claude-legal-skill](https://github.com/evolsb/claude-legal-skill) — AI contract review skill for Claude Code that can feed into this tool

## License

MIT
