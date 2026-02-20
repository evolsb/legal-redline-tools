# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-02-20

### Added
- Full-document redline PDF with inline strikethrough/underline, change bars, and summary page
- Internal memo PDF with tier-grouped analysis (rationale, walkaway, precedent)
- Markdown output with external/internal modes
- Document diff — compare two `.docx` files and auto-generate redlines
- Cross-agreement comparison — flag inconsistencies across related agreements
- Placeholder scanner — find blank fields, `$X`, `TBD`, and missing exhibit references
- Section remapping — remap redline section references between document versions
- `add_section` redline type for inserting new paragraphs/sections
- Subcommand CLI: `apply`, `diff`, `scan`, `remap`, `compare`
- AI agent skill prompt (`skill.md`)
- Normalized text matching for PDF-converted documents (smart quotes, whitespace, en/em dashes)

### Changed
- Summary PDF now supports `external` and `internal` modes
- `_find_text_across_runs` returns matched document text for accurate tracked changes
- Paragraph-level filtering uses normalized matching consistently

## [0.1.1] - 2026-02-18

### Fixed
- Summary PDF table formatting — use block layout instead of cramped columns

## [0.1.0] - 2026-02-17

### Added
- Initial release
- Tracked-changes `.docx` generation via OOXML manipulation
- Summary-only redline PDF
- CLI with JSON input and inline change flags (`--replace`, `--delete`, `--insert-after`)
- Python API: `apply_redlines`, `generate_summary_pdf`, `render_redline_pdf`

[0.2.0]: https://github.com/evolsb/legal-redline-tools/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/evolsb/legal-redline-tools/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/evolsb/legal-redline-tools/releases/tag/v0.1.0
