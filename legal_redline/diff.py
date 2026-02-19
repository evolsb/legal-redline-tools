"""Compare two .docx files and generate redlines from the differences.

Produces a list of redline-format changes that can be fed into render_redline_pdf
or generate_summary_pdf.
"""

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

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue

        if tag == "replace":
            # Paragraphs were modified -- do word-level diff within each pair
            old_slice = old_paras[i1:i2]
            new_slice = new_paras[j1:j2]

            # Pair up paragraphs for word-level diff
            max_len = max(len(old_slice), len(new_slice))
            for k in range(max_len):
                old_text = old_slice[k] if k < len(old_slice) else ""
                new_text = new_slice[k] if k < len(new_slice) else ""

                if not old_text.strip() and not new_text.strip():
                    continue

                if not old_text.strip():
                    # Pure insertion
                    change_num += 1
                    anchor = _get_context(new_paras, j1 + k - 1)
                    redlines.append({
                        "type": "insert_after",
                        "anchor": anchor,
                        "text": new_text,
                        "title": f"Change {change_num}",
                    })
                elif not new_text.strip():
                    # Pure deletion
                    change_num += 1
                    redlines.append({
                        "type": "delete",
                        "text": old_text,
                        "title": f"Change {change_num}",
                    })
                else:
                    # Replacement -- find the actual changed portions
                    word_ops = _word_diff(old_text, new_text)
                    for op_tag, old_words, new_words in word_ops:
                        if op_tag == "equal":
                            continue
                        change_num += 1
                        if op_tag == "replace":
                            redlines.append({
                                "type": "replace",
                                "old": old_words,
                                "new": new_words,
                                "title": f"Change {change_num}",
                            })
                        elif op_tag == "delete":
                            redlines.append({
                                "type": "delete",
                                "text": old_words,
                                "title": f"Change {change_num}",
                            })
                        elif op_tag == "insert":
                            # Find anchor from preceding equal block
                            anchor = old_words if old_words else old_text[:40]
                            redlines.append({
                                "type": "insert_after",
                                "anchor": _get_preceding_context(old_text, new_words),
                                "text": new_words,
                                "title": f"Change {change_num}",
                            })

        elif tag == "delete":
            for k in range(i1, i2):
                if old_paras[k].strip():
                    change_num += 1
                    redlines.append({
                        "type": "delete",
                        "text": old_paras[k],
                        "title": f"Change {change_num}",
                    })

        elif tag == "insert":
            for k in range(j1, j2):
                if new_paras[k].strip():
                    change_num += 1
                    anchor = _get_context(old_paras, i1 - 1)
                    redlines.append({
                        "type": "insert_after",
                        "anchor": anchor,
                        "text": new_paras[k],
                        "title": f"Change {change_num}",
                    })

    return redlines


def _get_context(paragraphs, idx, max_len=50):
    """Get context text from a paragraph index."""
    if idx < 0 or idx >= len(paragraphs):
        return ""
    text = paragraphs[idx].strip()
    if len(text) > max_len:
        return text[:max_len]
    return text


def _get_preceding_context(full_text, inserted_text):
    """Try to find what comes before the inserted text as an anchor."""
    words = full_text.split()
    if len(words) >= 3:
        return " ".join(words[:3])
    return full_text[:40] if full_text else ""
