"""Generate a summary-only redline PDF (schedule of proposed changes)."""

from datetime import datetime
from fpdf import FPDF


RED = (200, 30, 30)
BLUE = (30, 60, 180)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
LIGHT_GRAY = (200, 200, 200)


def _sanitize(text):
    """Replace non-latin1 characters with ASCII equivalents."""
    replacements = {
        "\u2014": "--", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u2022": "*",
        "\u00a0": " ", "\u200b": "", "\u2003": "  ", "\u2002": " ",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _wrap_text(text, max_chars=90):
    """Word-wrap text to fit within PDF columns."""
    text = _sanitize(text)
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines


def generate_summary_pdf(redlines, output_path, doc_title=None,
                         author=None, date_str=None,
                         doc_parties=None, mode="external"):
    """
    Generate a summary-only redline PDF showing each proposed change
    with strikethrough/underline formatting.

    Args:
        redlines: List of redline dicts
        output_path: Output PDF path
        doc_title: Document title
        author: Author name
        date_str: Date string
        doc_parties: Parties description
        mode: "external" (clean, no rationale/tier/walkaway) or
              "internal" (includes rationale, walkaway, precedent)

    Each redline can optionally include:
        section: Contract section reference (e.g. "7.2")
        title: Human-readable title (e.g. "Liability Cap")
        rationale: Why this change is proposed (internal only)
        walkaway: Walk-away position (internal only)
        precedent: Market precedent (internal only)
        tier: Priority tier 1-3 (internal only)
    """
    internal = mode == "internal"
    if date_str is None:
        date_str = datetime.now().strftime("%B %d, %Y")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    # ── Title ──
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*BLACK)
    pdf.cell(0, 12, "PROPOSED REDLINES", new_x="LMARGIN", new_y="NEXT", align="C")

    if doc_title:
        pdf.set_font("Helvetica", "", 13)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 8, _sanitize(doc_title), new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(4)

    # Meta
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRAY)
    meta = []
    if doc_parties:
        meta.append(f"Parties: {doc_parties}")
    meta.extend([f"Prepared by: {author}", f"Date: {date_str}",
                 f"Total proposed changes: {len(redlines)}"])
    for line in meta:
        pdf.cell(0, 5, _sanitize(line), new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(4)

    # Legend
    x_start = pdf.l_margin
    x_end = pdf.w - pdf.r_margin
    pdf.set_draw_color(*LIGHT_GRAY)
    pdf.set_line_width(0.3)
    pdf.line(x_start, pdf.get_y(), x_end, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*BLACK)
    pdf.cell(15, 5, "Legend:", new_x="END")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*RED)
    y = pdf.get_y()
    x = pdf.get_x()
    pdf.cell(35, 5, "Deleted text", new_x="END")
    pdf.set_draw_color(*RED)
    pdf.set_line_width(0.2)
    pdf.line(x + 1, y + 2.8, x + 32, y + 2.8)

    pdf.set_text_color(*BLUE)
    pdf.set_font("Helvetica", "U", 8)
    pdf.cell(35, 5, "Inserted text", new_x="END")

    pdf.set_text_color(*BLACK)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, "Unchanged context", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_draw_color(*LIGHT_GRAY)
    pdf.line(x_start, pdf.get_y(), x_end, pdf.get_y())
    pdf.ln(6)

    # ── Each Redline ──
    for idx, redline in enumerate(redlines):
        rtype = redline["type"]
        section = redline.get("section", "")
        title = redline.get("title", "")
        rationale = redline.get("rationale", "")
        walkaway = redline.get("walkaway", "")
        precedent = redline.get("precedent", "")
        tier = redline.get("tier", 0)

        if pdf.get_y() > pdf.h - 60:
            pdf.add_page()

        # Header
        header_parts = []
        if section:
            header_parts.append(f"Section {section}")
        if title:
            header_parts.append(f"-- {title}" if section else title)
        header_text = " ".join(header_parts) if header_parts else f"Change {idx + 1}"

        change_label = {"replace": "REPLACEMENT", "delete": "DELETION",
                        "insert_after": "INSERTION",
                        "add_section": "NEW SECTION"}.get(rtype, rtype.upper())

        # Tier badge (internal only)
        tier_suffix = ""
        if internal and tier:
            tier_labels = {1: "NON-STARTER", 2: "IMPORTANT", 3: "DESIRABLE"}
            tier_suffix = f"  [T{tier}: {tier_labels.get(tier, '')}]"

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*BLACK)
        pdf.cell(0, 6, _sanitize(f"{idx + 1}.  {header_text}{tier_suffix}"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 4, f"Type: {change_label}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        left_margin = pdf.l_margin + 5

        # Render based on type
        if rtype == "replace":
            _render_labeled_text(pdf, left_margin, "Current:", redline["old"],
                                 RED, strikethrough=True)
            pdf.ln(1.5)
            _render_labeled_text(pdf, left_margin, "Proposed:", redline["new"],
                                 BLUE, underline=True)

        elif rtype == "delete":
            _render_labeled_text(pdf, left_margin, "Delete:", redline["text"],
                                 RED, strikethrough=True)

        elif rtype == "insert_after":
            _render_labeled_text(pdf, left_margin, "After:", redline["anchor"],
                                 BLACK)
            pdf.ln(1)
            _render_labeled_text(pdf, left_margin, "Insert:", redline["text"],
                                 BLUE, underline=True)

        elif rtype == "add_section":
            after_sec = redline.get("after_section", "")
            new_sec = redline.get("new_section_number", "")
            if after_sec:
                _render_labeled_text(pdf, left_margin, "After:", after_sec, BLACK)
                pdf.ln(1)
            sec_label = f"New {new_sec}:" if new_sec else "New:"
            _render_labeled_text(pdf, left_margin, sec_label, redline["text"],
                                 BLUE, underline=True)

        pdf.ln(2)

        # Internal-only fields: rationale, walkaway, precedent
        if internal:
            if rationale:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(*GRAY)
                for line in _wrap_text(f"Rationale: {rationale}", 100):
                    pdf.cell(0, 4, line, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
            if walkaway:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(*GRAY)
                for line in _wrap_text(f"Walkaway: {walkaway}", 100):
                    pdf.cell(0, 4, line, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
            if precedent:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(*GRAY)
                for line in _wrap_text(f"Precedent: {precedent}", 100):
                    pdf.cell(0, 4, line, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
            if rationale or walkaway or precedent:
                pdf.ln(1)

        pdf.set_draw_color(*LIGHT_GRAY)
        pdf.line(x_start + 10, pdf.get_y(), x_end - 10, pdf.get_y())
        pdf.ln(6)

    # Footer
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 4, "This document summarizes proposed changes. "
             "A marked-up .docx with tracked changes is available upon request.",
             new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.output(output_path)
    print(f"Summary PDF: {output_path}")


def _render_labeled_text(pdf, left_margin, label, text, color,
                         strikethrough=False, underline=False):
    """Render a labeled text block (e.g. 'Current: <text>')."""
    pdf.set_x(left_margin)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*BLACK)
    pdf.cell(18, 4.5, label, new_x="END")

    style = ""
    if underline:
        style = "U"
    pdf.set_font("Courier", style, 7.5)
    pdf.set_text_color(*color)

    lines = _wrap_text(text, 85)
    for i, line in enumerate(lines):
        if i > 0:
            pdf.set_x(left_margin + 18)
        x_before = pdf.get_x()
        y_before = pdf.get_y()
        pdf.cell(0, 4.5, line, new_x="LMARGIN", new_y="NEXT")

        if strikethrough:
            pdf.set_draw_color(*color)
            pdf.set_line_width(0.15)
            line_w = pdf.get_string_width(line)
            pdf.line(x_before, y_before + 2.5, x_before + line_w, y_before + 2.5)

    pdf.ln(1)
