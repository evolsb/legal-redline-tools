"""CLI entry point for legal-redline-tools."""

import argparse
import json
import sys

from legal_redline.apply import apply_redlines
from legal_redline.render import render_redline_pdf
from legal_redline.summary import generate_summary_pdf


def main():
    parser = argparse.ArgumentParser(
        prog="legal-redline",
        description="Apply tracked changes to Word documents and generate redline PDFs.",
        epilog="https://github.com/evolsb/legal-redline-tools",
    )
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
                        help="Generate summary-only redline PDF")
    parser.add_argument("--no-docx", action="store_true",
                        help="Skip .docx output (PDF only)")

    # PDF options
    parser.add_argument("--doc-title", metavar="TITLE",
                        help="Document title for PDF header")
    parser.add_argument("--doc-parties", metavar="PARTIES",
                        help="Parties for PDF header")
    parser.add_argument("--header", metavar="TEXT",
                        help="Header text on every page of full PDF")

    args = parser.parse_args()

    if not args.no_docx and not args.output and not args.pdf and not args.summary_pdf:
        parser.error("Specify an output: positional output .docx, --pdf, "
                     "--summary-pdf, or --no-docx")

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
        print(f"--- .docx with tracked changes ---")
        apply_redlines(args.input, args.output, redlines, args.author)
        print()

    # Generate full-document redline PDF
    if args.pdf:
        print(f"--- Full-document redline PDF ---")
        render_redline_pdf(
            args.input, redlines, args.pdf,
            header_text=args.header or args.doc_title,
            author=args.author,
        )
        print()

    # Generate summary PDF
    if args.summary_pdf:
        print(f"--- Summary redline PDF ---")
        generate_summary_pdf(
            redlines, args.summary_pdf,
            doc_title=args.doc_title,
            author=args.author,
            doc_parties=args.doc_parties,
        )


if __name__ == "__main__":
    main()
