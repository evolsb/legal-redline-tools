"""Compare two .docx files and generate redlines from the differences.

Produces a list of redline-format changes that can be fed into render_redline_pdf
or generate_summary_pdf.
"""

import re
from difflib import SequenceMatcher

from docx import Document


def _extract_paragraphs(docx_path):
    """Extract paragraph texts from a docx file."""
    doc = Document(docx_path)
    return [para.text or "" for para in doc.paragraphs]


def _word_diff(old_text, new_text):
    """
    Compute word-level diff between two strings.

    Returns list of (tag, old_words, new_words) where tag is
    'equal', 'replace', 'delete', or 'insert'.
    """
    old_words = old_text.split()
    new_words = new_text.split()

    sm = SequenceMatcher(None, old_words, new_words)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        ops.append((tag, " ".join(old_words[i1:i2]), " ".join(new_words[j1:j2])))
    return ops


def _detect_section(text):
    """Try to extract a section number from paragraph text (e.g. '7.2 Fees')."""
    m = re.match(r'^(\d+(?:\.\d+)*)\s', text.strip())
    if m:
        return m.group(1)
    return ""


def _detect_title(text, max_len=60):
    """Extract a short title from paragraph text for human readability."""
    text = text.strip()
    if not text:
        return ""
    # If it starts with a section number, skip it for the title
    m = re.match(r'^\d+(?:\.\d+)*\s+(.+)', text)
    title_text = m.group(1) if m else text
    # Take first sentence or first N chars
    first_sentence = re.split(r'[.;:]', title_text)[0].strip()
    if len(first_sentence) > max_len:
        return first_sentence[:max_len] + "..."
    return first_sentence


def _get_unique_anchor(paragraphs, idx, max_len=80):
    """Get an anchor from paragraph at idx that's reasonably unique.

    Uses longer text to reduce false matches in other paragraphs.
    """
    if idx < 0 or idx >= len(paragraphs):
        return ""
    text = paragraphs[idx].strip()
    if not text:
        # Walk backwards to find non-empty paragraph
        for i in range(idx - 1, max(idx - 5, -1), -1):
            if i >= 0 and paragraphs[i].strip():
                text = paragraphs[i].strip()
                break
    if not text:
        return ""
    # Use more text for uniqueness (up to max_len)
    if len(text) > max_len:
        return text[:max_len]
    return text


def diff_documents(old_docx_path, new_docx_path, context_words=5):
    """
    Compare two .docx files and produce redline-format changes.

    Args:
        old_docx_path: Path to original document
        new_docx_path: Path to revised document
        context_words: Number of context words around changes

    Returns:
        List of redline dicts compatible with render_redline_pdf/apply_redlines
    """
    old_paras = _extract_paragraphs(old_docx_path)
    new_paras = _extract_paragraphs(new_docx_path)

    # Match paragraphs
    sm = SequenceMatcher(None, old_paras, new_paras)
    redlines = []
    change_num = 0

    # Track current section context from headings
    current_section = ""

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            # Update section context from equal paragraphs
            for k in range(i1, i2):
                sec = _detect_section(old_paras[k])
                if sec:
                    current_section = sec
            continue

        if tag == "replace":
            # Paragraphs were modified -- do word-level diff within each pair
            old_slice = old_paras[i1:i2]
            new_slice = new_paras[j1:j2]

            # Update section context
            for text in old_slice:
                sec = _detect_section(text)
                if sec:
                    current_section = sec

            # Pair up paragraphs for word-level diff
            max_len = max(len(old_slice), len(new_slice))
            for k in range(max_len):
                old_text = old_slice[k] if k < len(old_slice) else ""
                new_text = new_slice[k] if k < len(new_slice) else ""

                if not old_text.strip() and not new_text.strip():
                    continue

                if not old_text.strip():
                    # Pure insertion — use preceding paragraph as anchor
                    change_num += 1
                    # Use the last old paragraph or the new paragraph before this one
                    anchor_idx = j1 + k - 1
                    if k > 0 and k - 1 < len(new_slice):
                        # Use the previous new paragraph (just inserted)
                        anchor = new_slice[k - 1].strip()[:80] if new_slice[k - 1].strip() else _get_unique_anchor(old_paras, i1 - 1)
                    else:
                        anchor = _get_unique_anchor(old_paras, i1 - 1)
                    redlines.append({
                        "type": "insert_after",
                        "anchor": anchor,
                        "text": new_text,
                        "section": current_section,
                        "title": _detect_title(new_text),
                    })
                elif not new_text.strip():
                    # Pure deletion
                    change_num += 1
                    redlines.append({
                        "type": "delete",
                        "text": old_text,
                        "section": current_section,
                        "title": _detect_title(old_text),
                    })
                else:
                    # Replacement -- find the actual changed portions
                    word_ops = _word_diff(old_text, new_text)

                    # Check similarity — if mostly different, treat as whole-paragraph replace
                    equal_words = sum(1 for op, _, _ in word_ops if op == "equal")
                    total_words = max(len(old_text.split()), len(new_text.split()), 1)
                    similarity = equal_words / total_words

                    if similarity < 0.3:
                        # Mostly rewritten — treat as full paragraph replacement
                        change_num += 1
                        redlines.append({
                            "type": "replace",
                            "old": old_text,
                            "new": new_text,
                            "section": current_section,
                            "title": _detect_title(old_text),
                        })
                    else:
                        # Targeted changes within paragraph
                        for op_tag, old_words, new_words in word_ops:
                            if op_tag == "equal":
                                continue
                            change_num += 1
                            if op_tag == "replace":
                                redlines.append({
                                    "type": "replace",
                                    "old": old_words,
                                    "new": new_words,
                                    "section": current_section,
                                    "title": _detect_title(old_text),
                                })
                            elif op_tag == "delete":
                                redlines.append({
                                    "type": "delete",
                                    "text": old_words,
                                    "section": current_section,
                                    "title": _detect_title(old_text),
                                })
                            elif op_tag == "insert":
                                redlines.append({
                                    "type": "insert_after",
                                    "anchor": _get_preceding_context(old_text, new_words),
                                    "text": new_words,
                                    "section": current_section,
                                    "title": _detect_title(old_text),
                                })

        elif tag == "delete":
            for k in range(i1, i2):
                if old_paras[k].strip():
                    sec = _detect_section(old_paras[k])
                    if sec:
                        current_section = sec
                    change_num += 1
                    redlines.append({
                        "type": "delete",
                        "text": old_paras[k],
                        "section": current_section,
                        "title": _detect_title(old_paras[k]),
                    })

        elif tag == "insert":
            # Each inserted paragraph gets a unique anchor
            last_anchor = _get_unique_anchor(old_paras, i1 - 1)
            for k in range(j1, j2):
                if new_paras[k].strip():
                    change_num += 1
                    redlines.append({
                        "type": "insert_after",
                        "anchor": last_anchor,
                        "text": new_paras[k],
                        "section": current_section,
                        "title": _detect_title(new_paras[k]),
                    })
                    # Update anchor to this paragraph so next insert chains correctly
                    last_anchor = new_paras[k].strip()[:80]

    return redlines


def _get_preceding_context(full_text, inserted_text):
    """Try to find what comes before the inserted text as an anchor."""
    words = full_text.split()
    if len(words) >= 5:
        return " ".join(words[:5])
    if len(words) >= 3:
        return " ".join(words[:3])
    return full_text[:60] if full_text else ""
