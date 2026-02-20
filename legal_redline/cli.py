"""CLI entry point for legal-redline-tools."""

import argparse
import json
import sys

from legal_redline.apply import apply_redlines
from legal_redline.compare import compare_agreements, format_comparison_report
from legal_redline.diff import diff_documents
from legal_redline.markdown import generate_markdown
from legal_redline.memo import generate_memo_pdf
from legal_redline.remap import remap_redlines
from legal_redline.render import render_redline_pdf
from legal_redline.scan import scan_document
from legal_redline.summary import generate_summary_pdf


def main():
    parser = argparse.ArgumentParser(
        prog="legal-redline",
        description="Apply tracked changes to Word documents and generate redline PDFs.",
        epilog="https://github.com/evolsb/legal-redline-tools",
    )
    sub = parser.add_subparsers(dest="command")

    # ── apply (default / legacy behavior) ──
    apply_p = sub.add_parser("apply", help="Apply redlines to a .docx")
    _add_apply_args(apply_p)

    # ── diff ──
    diff_p = sub.add_parser("diff", help="Compare two .docx files and generate redlines")
    diff_p.add_argument("old_docx", help="Original .docx file")
    diff_p.add_argument("new_docx", help="Revised .docx file")
    diff_p.add_argument("-o", "--output", help="Output JSON file for redlines")
    diff_p.add_argument("--context-words", type=int, default=5,
                        help="Context words around changes (default: 5)")

    # ── scan ──
    scan_p = sub.add_parser("scan", help="Scan .docx for blank fields and placeholders")
    scan_p.add_argument("input", help="Input .docx file")
    scan_p.add_argument("-o", "--output", help="Output JSON file")

    # ── remap ──
    remap_p = sub.add_parser("remap", help="Remap redline sections between documents")
    remap_p.add_argument("old_docx", help="Original .docx (redlines were written for)")
    remap_p.add_argument("new_docx", help="New .docx (redlines should target)")
    remap_p.add_argument("--redlines", required=True, help="Redlines JSON file")
    remap_p.add_argument("-o", "--output", help="Output remapped JSON file")
    remap_p.add_argument("--threshold", type=float, default=0.6,
                         help="Fuzzy match threshold 0-1 (default: 0.6)")

    # ── compare ──
    compare_p = sub.add_parser("compare",
                               help="Compare redlines across multiple agreements")
    compare_p.add_argument("--agreements", nargs="+", required=True,
                           metavar="NAME=FILE",
                           help="Agreement redlines as name=file.json pairs")
    compare_p.add_argument("-o", "--output", help="Output markdown file")

    # For backwards compat: if no subcommand, treat args as 'apply'
    # Parse and dispatch
    args, remaining = parser.parse_known_args()

    if args.command is None:
        # Legacy mode: treat everything as apply args
        apply_p2 = argparse.ArgumentParser(prog="legal-redline")
        _add_apply_args(apply_p2)
        args = apply_p2.parse_args()
        args.command = "apply"

    if args.command == "apply":
        _cmd_apply(args)
    elif args.command == "diff":
        _cmd_diff(args)
    elif args.command == "scan":
        _cmd_scan(args)
    elif args.command == "remap":
        _cmd_remap(args)
    elif args.command == "compare":
        _cmd_compare(args)


def _add_apply_args(parser):
    """Add arguments for the apply command."""
    parser.add_argument("input", help="Input .docx file")
    parser.add_argument("output", nargs="?",
                        help="Output .docx file with tracked changes")
    parser.add_argument("--author", default="Chris Sheehan",
                        help="Author name for tracked changes")

    # Redline specifications
    parser.add_argument("--replace", nargs=2, action="append",
                        metavar=("OLD", "NEW"),
                        help="Replace OLD with NEW as tracked change")
    parser.add_argument("--delete", action="append", metavar="TEXT",
                        help="Delete TEXT as tracked change")
    parser.add_argument("--insert-after", nargs=2, action="append",
                        metavar=("ANCHOR", "TEXT"),
                        help="Insert TEXT after ANCHOR as tracked change")
    parser.add_argument("--from-json", metavar="FILE",
                        help="Load redlines from JSON file")

    # Output options
    parser.add_argument("--pdf", metavar="FILE",
                        help="Generate full-document redline PDF")
    parser.add_argument("--summary-pdf", metavar="FILE",
                        help="Generate summary-only redline PDF (external)")
    parser.add_argument("--memo-pdf", metavar="FILE",
                        help="Generate internal analysis memo PDF")
    parser.add_argument("--markdown", metavar="FILE",
                        help="Generate markdown output")
    parser.add_argument("--no-docx", action="store_true",
                        help="Skip .docx output (PDF only)")
    parser.add_argument("--mode", choices=["external", "internal"],
                        default="external",
                        help="Output mode: external (clean) or internal (full analysis)")

    # PDF options
    parser.add_argument("--doc-title", metavar="TITLE",
                        help="Document title for PDF header")
    parser.add_argument("--doc-parties", metavar="PARTIES",
                        help="Parties for PDF header")
    parser.add_argument("--header", metavar="TEXT",
                        help="Header text on every page of full PDF")


def _cmd_apply(args):
    """Run the apply command."""
    if not args.no_docx and not args.output and not args.pdf \
       and not args.summary_pdf and not args.memo_pdf and not args.markdown:
        print("Error: Specify an output: positional output .docx, --pdf, "
              "--summary-pdf, --memo-pdf, --markdown, or --no-docx")
        sys.exit(1)

    # Build redlines list
    redlines = []

    if args.from_json:
        with open(args.from_json) as f:
            redlines = json.load(f)

    if args.replace:
        for old, new in args.replace:
            redlines.append({"type": "replace", "old": old, "new": new})

    if args.delete:
        for text in args.delete:
            redlines.append({"type": "delete", "text": text})

    if args.insert_after:
        for anchor, text in args.insert_after:
            redlines.append({"type": "insert_after", "anchor": anchor, "text": text})

    if not redlines:
        print("Error: No redlines specified. Use --replace, --delete, "
              "--insert-after, or --from-json.")
        sys.exit(1)

    print(f"Input:    {args.input}")
    print(f"Author:   {args.author}")
    print(f"Redlines: {len(redlines)}")
    print()

    # Generate tracked-changes .docx
    if not args.no_docx and args.output:
        print("--- .docx with tracked changes ---")
        apply_redlines(args.input, args.output, redlines, args.author)
        print()

    # Generate full-document redline PDF
    if args.pdf:
        print("--- Full-document redline PDF ---")
        render_redline_pdf(
            args.input, redlines, args.pdf,
            header_text=args.header or args.doc_title,
            author=args.author,
        )
        print()

    # Generate summary PDF
    if args.summary_pdf:
        print("--- Summary redline PDF ---")
        generate_summary_pdf(
            redlines, args.summary_pdf,
            doc_title=args.doc_title,
            author=args.author,
            doc_parties=args.doc_parties,
            mode=args.mode,
        )
        print()

    # Generate internal memo PDF
    if args.memo_pdf:
        print("--- Internal memo PDF ---")
        generate_memo_pdf(
            redlines, args.memo_pdf,
            doc_title=args.doc_title,
            author=args.author,
            doc_parties=args.doc_parties,
        )
        print()

    # Generate markdown
    if args.markdown:
        print("--- Markdown output ---")
        md = generate_markdown(
            redlines,
            doc_title=args.doc_title,
            author=args.author,
            doc_parties=args.doc_parties,
            mode=args.mode,
        )
        with open(args.markdown, "w") as f:
            f.write(md)
        print(f"Markdown: {args.markdown}")


def _cmd_diff(args):
    """Run the diff command."""
    print(f"Comparing: {args.old_docx} vs {args.new_docx}")
    redlines = diff_documents(args.old_docx, args.new_docx,
                              context_words=args.context_words)
    print(f"Found {len(redlines)} changes")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(redlines, f, indent=2)
        print(f"Output: {args.output}")
    else:
        print(json.dumps(redlines, indent=2))


def _cmd_scan(args):
    """Run the scan command."""
    print(f"Scanning: {args.input}")
    report = scan_document(args.input)

    placeholders = report.get("placeholders", [])
    references = report.get("references", {})
    missing = references.get("missing", [])

    print(f"Placeholders found: {len(placeholders)}")
    print(f"Missing references: {len(missing)}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Output: {args.output}")
    else:
        if placeholders:
            print("\nPlaceholders:")
            for p in placeholders:
                print(f"  [{p.get('type', '?')}] {p.get('text', '')[:60]} "
                      f"(para {p.get('paragraph', '?')})")
        if missing:
            print("\nMissing references:")
            for m in missing:
                print(f"  {m}")


def _cmd_remap(args):
    """Run the remap command."""
    with open(args.redlines) as f:
        redlines = json.load(f)

    print(f"Remapping {len(redlines)} redlines")
    print(f"  From: {args.old_docx}")
    print(f"  To:   {args.new_docx}")

    updated, report = remap_redlines(
        args.old_docx, args.new_docx, redlines,
        threshold=args.threshold,
    )

    # Print report summary
    statuses = {}
    for r in report:
        s = r.get("status", "?")
        statuses[s] = statuses.get(s, 0) + 1
    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(updated, f, indent=2)
        print(f"Output: {args.output}")
    else:
        print(json.dumps(updated, indent=2))


def _cmd_compare(args):
    """Run the compare command."""
    agreement_redlines = {}
    for pair in args.agreements:
        if "=" not in pair:
            print(f"Error: Expected name=file.json, got: {pair}")
            sys.exit(1)
        name, filepath = pair.split("=", 1)
        with open(filepath) as f:
            agreement_redlines[name] = json.load(f)

    print(f"Comparing {len(agreement_redlines)} agreements: "
          f"{', '.join(agreement_redlines.keys())}")

    result = compare_agreements(agreement_redlines)
    report = format_comparison_report(result)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Output: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
