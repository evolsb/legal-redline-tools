"""Generate an internal analysis memo PDF with tiers, rationale, walkaway positions."""

from datetime import datetime
from fpdf import FPDF


RED = (200, 30, 30)
BLUE = (30, 60, 180)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
LIGHT_GRAY = (200, 200, 200)
DARK_RED = (160, 20, 20)
AMBER = (180, 120, 0)
GREEN = (30, 120, 50)

TIER_LABELS = {
    1: ("TIER 1 -- NON-STARTERS", DARK_RED),
    2: ("TIER 2 -- IMPORTANT", AMBER),
    3: ("TIER 3 -- DESIRABLE", GREEN),
}


def _sanitize(text):
    replacements = {
        "\u2014": "--", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u2022": "*",
        "\u00a0": " ", "\u200b": "", "\u2003": "  ", "\u2002": " ",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def generate_memo_pdf(redlines, output_path, doc_title=None,
                      author=None, date_str=None, doc_parties=None):
    """
    Generate an internal analysis memo PDF.

    Redlines should include optional fields:
        tier: 1, 2, or 3
        rationale: Why this change is proposed
        walkaway: Fallback position
        precedent: Cross-reference to other agreements

    This is for INTERNAL USE ONLY -- not sent to counterparty.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%B %d, %Y")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    # ── Title ──
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*BLACK)
    pdf.cell(0, 10, "INTERNAL REDLINE ANALYSIS", new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*DARK_RED)
    pdf.cell(0, 5, "CONFIDENTIAL -- ATTORNEY WORK PRODUCT -- DO NOT DISTRIBUTE",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(2)

    if doc_title:
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 7, _sanitize(doc_title), new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(3)

    # Meta
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRAY)
    meta = []
    if doc_parties:
        meta.append(f"Parties: {doc_parties}")
    if author:
        meta.append(f"Prepared by: {author}")
    meta.append(f"Date: {date_str}")
    meta.append(f"Total proposed changes: {len(redlines)}")

    # Count by tier
    tier_counts = {}
    for rl in redlines:
        t = rl.get("tier", 0)
        tier_counts[t] = tier_counts.get(t, 0) + 1
    for t in sorted(tier_counts):
        label = TIER_LABELS.get(t, (f"Tier {t}", GRAY))[0]
        meta.append(f"  {label}: {tier_counts[t]}")

    for line in meta:
        pdf.cell(0, 5, _sanitize(line), new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(4)
    _draw_separator(pdf)
    pdf.ln(4)

    # ── Group by tier ──
    grouped = {}
    for idx, rl in enumerate(redlines):
        t = rl.get("tier", 0)
        grouped.setdefault(t, []).append((idx, rl))

    for tier in sorted(grouped):
        tier_label, tier_color = TIER_LABELS.get(tier, (f"TIER {tier}", GRAY))

        # Tier header
        if pdf.get_y() > pdf.h - 50:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*tier_color)
        pdf.cell(0, 8, _sanitize(tier_label), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        for idx, rl in grouped[tier]:
            _render_redline_block(pdf, idx, rl)

        pdf.ln(4)

    # Uncategorized (tier=0 or missing)
    if 0 in grouped:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 8, "UNCATEGORIZED", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        for idx, rl in grouped[0]:
            _render_redline_block(pdf, idx, rl)

    # Footer
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 4, "Internal analysis memo -- not for distribution to counterparty",
             new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.output(output_path)
    print(f"Internal memo PDF: {output_path}")


def _render_redline_block(pdf, idx, rl):
    """Render a single redline with full internal analysis."""
    rtype = rl["type"]
    section = rl.get("section", "")
    title = rl.get("title", "")
    rationale = rl.get("rationale", "")
    walkaway = rl.get("walkaway", "")
    precedent = rl.get("precedent", "")

    if pdf.get_y() > pdf.h - 55:
        pdf.add_page()

    # Header
    header_parts = [f"{idx + 1}."]
    if section:
        header_parts.append(f"Section {section}")
    if title:
        sep = " -- " if section else ""
        header_parts.append(f"{sep}{title}")

    change_label = {
        "replace": "REPLACEMENT", "delete": "DELETION",
        "insert_after": "INSERTION", "add_section": "NEW SECTION"
    }.get(rtype, rtype.upper())

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*BLACK)
    pdf.cell(0, 6, _sanitize(" ".join(header_parts)),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 4, f"Type: {change_label}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    indent = pdf.l_margin + 5
    usable_w = pdf.w - pdf.r_margin - indent - 2

    # Change content
    if rtype == "replace":
        _render_field(pdf, indent, usable_w, "Current:", rl["old"], RED, strike=True)
        pdf.ln(1)
        _render_field(pdf, indent, usable_w, "Proposed:", rl["new"], BLUE, underline=True)
    elif rtype == "delete":
        _render_field(pdf, indent, usable_w, "Delete:", rl["text"], RED, strike=True)
    elif rtype == "insert_after":
        _render_field(pdf, indent, usable_w, "After:", rl["anchor"], BLACK)
        pdf.ln(1)
        _render_field(pdf, indent, usable_w, "Insert:", rl["text"], BLUE, underline=True)
    elif rtype == "add_section":
        if rl.get("after_section"):
            _render_field(pdf, indent, usable_w, "After:",
                          f"Section {rl['after_section']}", BLACK)
            pdf.ln(1)
        sec_num = rl.get("new_section_number", "NEW")
        _render_field(pdf, indent, usable_w, f"Add {sec_num}:",
                      rl["text"], BLUE, underline=True)

    pdf.ln(2)

    # Rationale
    if rationale:
        _render_meta_field(pdf, indent, usable_w, "Rationale:", rationale)

    # Walkaway
    if walkaway:
        _render_meta_field(pdf, indent, usable_w, "Walkaway:", walkaway,
                           label_color=DARK_RED)

    # Precedent
    if precedent:
        _render_meta_field(pdf, indent, usable_w, "Precedent:", precedent,
                           label_color=BLUE)

    pdf.ln(1)
    _draw_separator(pdf, light=True)
    pdf.ln(4)


def _render_field(pdf, indent, usable_w, label, text, color,
                  strike=False, underline=False):
    """Render a labeled text field."""
    pdf.set_x(indent)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*BLACK)
    pdf.cell(18, 4.5, label, new_x="END")

    style = "U" if underline else ""
    pdf.set_font("Courier", style, 7.5)
    pdf.set_text_color(*color)

    text = _sanitize(text)
    x_start = pdf.get_x()
    pdf.multi_cell(usable_w - 18, 4, text, new_x="LMARGIN", new_y="NEXT")

    if strike:
        # Draw strikethrough lines over the text
        # This is approximate -- covers the text block area
        y_end = pdf.get_y()
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.15)
        line_y = y_end - 2  # approximate center of last line
        text_w = min(pdf.get_string_width(text), usable_w - 18)
        pdf.line(x_start, line_y, x_start + text_w, line_y)


def _render_meta_field(pdf, indent, usable_w, label, text, label_color=GRAY):
    """Render a metadata field (rationale, walkaway, precedent)."""
    pdf.set_x(indent)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*label_color)
    pdf.cell(18, 4, label, new_x="END")

    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(usable_w - 18, 3.5, _sanitize(text),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _draw_separator(pdf, light=False):
    x_start = pdf.l_margin + (10 if light else 0)
    x_end = pdf.w - pdf.r_margin - (10 if light else 0)
    pdf.set_draw_color(*LIGHT_GRAY)
    pdf.set_line_width(0.3)
    pdf.line(x_start, pdf.get_y(), x_end, pdf.get_y())
