# legal-redline-tools

Apply tracked changes to Word documents and generate lawyer-style redline PDFs. Pure Python, JSON-driven, designed for AI agent pipelines.

## The Problem

Every AI contract review tool can *analyze* contracts, but none can produce the actual tracked-changes `.docx` or visual redline PDF that lawyers need. python-docx has [refused to add tracked changes for 9 years](https://github.com/python-openxml/python-docx/issues/340). This tool fills that gap.

## What It Does

Takes an original `.docx` and a list of text changes (as JSON), and produces:

1. **Tracked-changes `.docx`** — Real Word tracked changes (strikethrough + insertion) that recipients can accept/reject
2. **Full-document redline PDF** — The entire contract rendered with inline red strikethrough and blue underline, plus change bars and a summary page
3. **Summary PDF** — A schedule of proposed changes (external mode for counterparty, internal mode with rationale)
4. **Internal memo PDF** — Tier-grouped analysis with rationale, walkaway positions, and precedent citations
5. **Markdown** — Structured output for PRs, documentation, or AI pipeline chaining
6. **Document diff** — Compare two `.docx` files and generate redlines from differences
7. **Section remapping** — Remap redline section references when switching document versions
8. **Cross-agreement comparison** — Compare redline sets across multiple related agreements
9. **Placeholder scanner** — Find blank fields, `$X`, `TBD`, and missing exhibit references

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

## Quick Start

### CLI

```bash
# Apply redlines and generate all outputs:
legal-redline apply original.docx output.docx \
    --from-json redlines.json \
    --pdf full-redline.pdf \
    --summary-pdf summary.pdf \
    --memo-pdf internal-memo.pdf \
    --markdown redlines.md \
    --header "Proposed Redlines — Feb 2026"

# Inline changes (no JSON file needed):
legal-redline apply original.docx output.docx \
    --replace "old text" "new text" \
    --delete "text to remove" \
    --insert-after "anchor text" "new text"

# Compare two document versions:
legal-redline diff original.docx revised.docx -o changes.json

# Scan for blank fields and placeholders:
legal-redline scan contract.docx

# Remap section references to a new document:
legal-redline remap old-agreement.docx new-agreement.docx \
    --redlines redlines.json -o remapped.json

# Compare redlines across agreements:
legal-redline compare \
    --agreements msa=msa-redlines.json tri-party=triparty-redlines.json \
    -o comparison.md
```

### Python API

```python
from legal_redline import (
    apply_redlines, render_redline_pdf, generate_summary_pdf,
    generate_memo_pdf, generate_markdown, diff_documents,
    remap_redlines, compare_agreements, format_comparison_report,
    scan_document,
)

redlines = [
    {"type": "replace", "old": "20% of fees", "new": "100% of fees or $250K",
     "section": "7.2", "title": "Liability Cap", "tier": 1,
     "rationale": "20% is below market standard"},
    {"type": "delete", "text": "shall terminate without liability"},
    {"type": "insert_after", "anchor": "Effective Date",
     "text": ". 90-day termination right"},
    {"type": "add_section", "after_section": "Section 12",
     "text": "New audit rights clause...", "new_section_number": "12A"},
]

# Tracked-changes .docx
apply_redlines("original.docx", "output.docx", redlines)

# Full-document redline PDF
render_redline_pdf("original.docx", redlines, "redline.pdf",
                   header_text="Proposed Redlines")

# Summary PDF (external — clean, no rationale)
generate_summary_pdf(redlines, "summary.pdf",
                     doc_title="Merchant Agreement v3",
                     mode="external")

# Summary PDF (internal — includes rationale/walkaway/precedent)
generate_summary_pdf(redlines, "summary-internal.pdf",
                     doc_title="Merchant Agreement v3",
                     mode="internal")

# Internal memo PDF (tier-grouped analysis)
generate_memo_pdf(redlines, "memo.pdf",
                  doc_title="Merchant Agreement v3")

# Markdown output
md = generate_markdown(redlines, doc_title="Agreement", mode="internal")

# Diff two documents
changes = diff_documents("v1.docx", "v2.docx")

# Remap sections between document versions
updated, report = remap_redlines("old.docx", "new.docx", redlines)

# Cross-agreement comparison
result = compare_agreements({"msa": msa_redlines, "sow": sow_redlines})
print(format_comparison_report(result))

# Scan for placeholders
report = scan_document("contract.docx")
```

## JSON Format

```json
[
    {
        "type": "replace",
        "old": "text to find and replace",
        "new": "replacement text",
        "section": "7.2",
        "title": "Liability Cap",
        "tier": 1,
        "rationale": "Below market standard",
        "walkaway": "Accept 50% if pushed",
        "precedent": "Industry standard is 100% of fees"
    },
    {
        "type": "delete",
        "text": "text to remove"
    },
    {
        "type": "insert_after",
        "anchor": "text to insert after",
        "text": "new text to add"
    },
    {
        "type": "add_section",
        "after_section": "Section 12",
        "text": "New section content",
        "new_section_number": "12A"
    }
]
```

### Redline Types

| Type | Required Fields | Description |
|------|----------------|-------------|
| `replace` | `old`, `new` | Find and replace text with tracked change |
| `delete` | `text` | Delete text as tracked deletion |
| `insert_after` | `anchor`, `text` | Insert new text after anchor |
| `add_section` | `text`, `after_section` | Insert new paragraph/section |

### Optional Metadata

| Field | Used In | Description |
|-------|---------|-------------|
| `section` | All outputs | Contract section reference (e.g. "7.2") |
| `title` | All outputs | Human-readable title |
| `tier` | Internal only | Priority 1-3 (1=non-starter, 2=important, 3=desirable) |
| `rationale` | Internal only | Why the change is proposed |
| `walkaway` | Internal only | Fall-back position |
| `precedent` | Internal only | Market standard reference |

## Output Modes

### External (counterparty-facing)

Clean outputs showing only the proposed changes — no rationale, tiers, or walkaway positions. This is what you send to the other side.

- Tracked-changes `.docx`
- Full-document redline PDF
- Summary PDF (`mode="external"`)
- Markdown (`mode="external"`)

### Internal (team-facing)

Full analysis with strategy context. Never send these to the counterparty.

- Internal memo PDF — tier-grouped with rationale, walkaway, precedent
- Summary PDF (`mode="internal"`) — includes tier badges and strategy fields
- Markdown (`mode="internal"`) — grouped by tier with all metadata

## AI Skill

The included `skill.md` provides a complete prompt for AI agents (Claude, GPT, Codex, etc.) to:

1. Analyze a contract
2. Identify problematic provisions with tier classification
3. Generate the redlines JSON
4. Produce all output formats

Copy `skill.md` into your AI agent's skill/tool directory.

## Requirements

- Python 3.9+
- python-docx
- lxml
- fpdf2

## License

MIT
