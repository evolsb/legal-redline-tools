# legal-redline-tools

[![GitHub stars](https://img.shields.io/github/stars/evolsb/legal-redline-tools)](https://github.com/evolsb/legal-redline-tools/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.2.0-blue)](CHANGELOG.md)

Apply tracked changes to Word documents and generate lawyer-style redline PDFs. Pure Python, JSON-driven, built for AI contract review pipelines.

## The Problem

Every AI contract review tool can *analyze* contracts, but none produce the actual tracked-changes `.docx` or visual redline PDF that lawyers need. python-docx has [refused to add tracked changes for 9 years](https://github.com/python-openxml/python-docx/issues/340). Legal teams still email marked-up Word files back and forth. AI tools that can't produce those artifacts are stuck behind a manual copy-paste wall.

This tool bridges that gap: give it a `.docx` and a list of changes (as JSON), and it produces every deliverable a legal workflow needs — tracked-changes Word files, full-document redline PDFs, negotiation memos, and structured markdown for AI pipeline chaining.

## What It Does

| # | Capability | Description |
|---|-----------|-------------|
| 1 | **Tracked-changes `.docx`** | Real Word tracked changes (strikethrough + insertion) that recipients can accept/reject |
| 2 | **Full-document redline PDF** | Entire contract with inline red strikethrough and blue underline, change bars, and summary page |
| 3 | **Summary PDF** | Schedule of proposed changes (external mode for counterparty, internal mode with rationale) |
| 4 | **Internal memo PDF** | Tier-grouped analysis with rationale, walkaway positions, and precedent citations |
| 5 | **Markdown** | Structured output for PRs, documentation, or AI pipeline chaining |
| 6 | **Document diff** | Compare two `.docx` files and auto-generate redlines from differences |
| 7 | **Section remapping** | Remap redline section references when switching between document versions |
| 8 | **Cross-agreement comparison** | Compare redline sets across multiple related agreements for consistency |
| 9 | **Placeholder scanner** | Find blank fields, `$X`, `TBD`, and missing exhibit references |

## Install

From source (recommended):

```bash
git clone https://github.com/evolsb/legal-redline-tools.git
cd legal-redline-tools
pip install -e .
```

Or directly from GitHub:

```bash
pip install git+https://github.com/evolsb/legal-redline-tools.git
```

## Quick Start

### CLI

```bash
# Apply redlines from JSON and generate all outputs
legal-redline apply original.docx output.docx \
    --from-json redlines.json \
    --pdf full-redline.pdf \
    --summary-pdf summary.pdf \
    --memo-pdf internal-memo.pdf \
    --markdown redlines.md \
    --header "Proposed Redlines — Feb 2026"

# Inline changes (no JSON file needed)
legal-redline apply original.docx output.docx \
    --replace "old text" "new text" \
    --delete "text to remove" \
    --insert-after "anchor text" "new text"

# Compare two document versions
legal-redline diff original.docx revised.docx -o changes.json

# Scan for blank fields and placeholders
legal-redline scan contract.docx

# Remap section references to a new document
legal-redline remap old-agreement.docx new-agreement.docx \
    --redlines redlines.json -o remapped.json

# Compare redlines across agreements
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
                     doc_title="Merchant Agreement v3", mode="external")

# Internal memo PDF (tier-grouped analysis)
generate_memo_pdf(redlines, "memo.pdf", doc_title="Merchant Agreement v3")

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

Redlines are a JSON array. Each entry has a `type` and type-specific fields, plus optional metadata.

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

### Example

```json
[
    {
        "type": "replace",
        "old": "SHALL BE LIMITED TO 20% OF FEES PAID",
        "new": "SHALL BE LIMITED TO 100% OF FEES PAID, OR $250,000, WHICHEVER IS GREATER",
        "section": "7.2",
        "title": "Liability Cap",
        "tier": 1,
        "rationale": "20% is well below market standard (100% of trailing 12-month fees).",
        "walkaway": "Accept 50% with $100K floor.",
        "precedent": "Industry standard B2B SaaS is 100% of trailing 12-month fees."
    },
    {
        "type": "delete",
        "text": "shall be entitled to immediately terminate this Agreement without liability",
        "section": "9.4",
        "title": "Delete At-Will Termination",
        "tier": 2,
        "rationale": "Vague standard gives Company unilateral termination right."
    },
    {
        "type": "insert_after",
        "anchor": "This Agreement shall commence on the Effective Date",
        "text": ". Either party may terminate for convenience upon 90 days' written notice",
        "section": "9.1",
        "title": "Mutual Termination Right",
        "tier": 2,
        "rationale": "Adding symmetrical termination rights."
    },
    {
        "type": "add_section",
        "after_section": "COMPANY PROVIDES THE SOFTWARE AND SERVICES",
        "text": "Service Level Agreement. Company targets 99.9% monthly API uptime.",
        "section": "NEW 11.X",
        "title": "SLA with Credits",
        "tier": 1,
        "rationale": "No SLA means no recourse for outages."
    }
]
```

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

## Text Matching

Redline text fields (`old`, `text`, `anchor`, `after_section`) must match text in the document. The matching engine handles common mismatches automatically:

- **Smart quotes** — `\u2018`/`\u2019` (curly single) and `\u201C`/`\u201D` (curly double) are normalized to straight quotes
- **Whitespace** — Tabs, double spaces, and other whitespace variations (common in PDF-to-docx conversions) are collapsed
- **Dashes** — En-dashes and em-dashes are treated as hyphens
- **Cross-run matching** — Text split across bold/italic/formatting runs is matched as plain text

Copy text directly from the document when possible. The normalizer handles the rest.

## AI Agent Skill

The included [`skill.md`](skill.md) is a prompt for AI agents (Claude, GPT, Codex) that instructs them to:

1. Read and analyze a contract
2. Identify problematic provisions with tier classification
3. Generate the redlines JSON with rationale and walkaway positions
4. Produce all output deliverables

To use with Claude Code, copy `skill.md` to your skills directory:

```bash
mkdir -p ~/.claude/skills/contract-redline
cp skill.md ~/.claude/skills/contract-redline/skill.md
```

## License

[MIT](LICENSE)
