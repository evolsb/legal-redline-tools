"""Compare two .docx files and generate redlines from the differences.

Produces a list of redline-format changes that can be fed into render_redline_pdf
or generate_summary_pdf.
"""

import logging
from difflib import SequenceMatcher

from docx import Document

logger = logging.getLogger(__name__)


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


def _count_occurrences(full_text, search_text):
    """Count non-overlapping occurrences of search_text in full_text."""
    if not search_text:
        return 0
    count = 0
    start = 0
    while True:
        pos = full_text.find(search_text, start)
        if pos < 0:
            break
        count += 1
        start = pos + 1
    return count


def _expand_to_unique(snippet, source_para, full_doc_text, max_len=200):
    """Expand a text snippet within its source paragraph until it's unique in the document.

    Grows the snippet by adding characters from the source paragraph (before and
    after) until the snippet appears exactly once in the full document text.

    Args:
        snippet: The current (possibly ambiguous) text snippet.
        source_para: The full paragraph text the snippet was extracted from.
        full_doc_text: The full document text (all paragraphs joined).
        max_len: Maximum length for the expanded snippet.

    Returns:
        The expanded snippet (unique if possible within max_len), or the original
        snippet if it's already unique or can't be made unique.
    """
    if not snippet or not source_para:
        return snippet

    count = _count_occurrences(full_doc_text, snippet)
    if count <= 1:
        return snippet

    # Find the snippet's position within its source paragraph
    pos = source_para.find(snippet)
    if pos < 0:
        return snippet

    # Grow outward from the snippet within the paragraph
    left = pos
    right = pos + len(snippet)

    while _count_occurrences(full_doc_text, source_para[left:right]) > 1:
        if right - left >= max_len:
            break
        # Alternate expanding left and right
        expanded = False
        if left > 0:
            left -= 1
            expanded = True
        if right < len(source_para):
            right += 1
            expanded = True
        if not expanded:
            # Can't expand further within paragraph
            break

    result = source_para[left:right]

    # Snap to word boundaries so we don't cut words mid-character
    result = _snap_to_word_boundaries(result, source_para, left, right)

    final_count = _count_occurrences(full_doc_text, result)
    if final_count > 1:
        logger.warning(
            "Could not make snippet unique within %d chars "
            "(still %d occurrences): '%s...'",
            max_len, final_count, result[:60],
        )

    return result


def _snap_to_word_boundaries(text, source_para, left, right):
    """Adjust left/right to avoid cutting words mid-character.

    Expands outward to the nearest word boundary (space or paragraph edge).
    """
    # Expand left to word boundary
    while left > 0 and source_para[left - 1] not in (' ', '\t', '\n'):
        left -= 1
    # Expand right to word boundary
    while right < len(source_para) and source_para[right] not in (' ', '\t', '\n'):
        right += 1
    return source_para[left:right]


def _build_full_doc_text(paragraphs):
    """Join paragraphs into a single string for uniqueness checking.

    Uses newline as separator so paragraph-level snippets match correctly.
    """
    return "\n".join(paragraphs)


def _ensure_unique_anchors(redlines, old_paras, max_len=200):
    """Post-process redlines to ensure text anchors are unique in the source document.

    For each redline:
      - "replace": expand "old" field
      - "delete": expand "text" field
      - "insert_after": expand "anchor" field

    Args:
        redlines: List of redline dicts (with _source_para metadata).
        old_paras: List of paragraph texts from the source document.
        max_len: Maximum expanded snippet length.

    Returns:
        The redlines list, modified in place (with _source_para removed).
    """
    full_text = _build_full_doc_text(old_paras)

    for redline in redlines:
        source_para = redline.pop("_source_para", None)
        if source_para is None:
            continue

        rtype = redline.get("type")

        if rtype == "replace" and "old" in redline:
            original = redline["old"]
            expanded = _expand_to_unique(original, source_para, full_text, max_len)
            if expanded != original:
                redline["old"] = expanded
                # Also update "new" to include the same surrounding context
                # so the replacement is correct
                redline["new"] = _expand_replacement_new(
                    original, expanded, redline["new"], source_para,
                )

        elif rtype == "delete" and "text" in redline:
            redline["text"] = _expand_to_unique(
                redline["text"], source_para, full_text, max_len,
            )

        elif rtype == "insert_after" and "anchor" in redline:
            redline["anchor"] = _expand_to_unique(
                redline["anchor"], source_para, full_text, max_len,
            )

    return redlines


def _expand_replacement_new(original_old, expanded_old, original_new, source_para):
    """When expanding a 'replace' redline's 'old', also expand 'new' to match.

    The expansion adds context from the source paragraph around the changed text.
    The 'new' field should contain the same surrounding context, with only the
    actually-changed portion swapped.

    Example:
        original_old = "applicable Order Form"
        expanded_old = "set forth in the applicable Order Form and"
        original_new = "applicable Statement of Work"
        -> result = "set forth in the applicable Statement of Work and"
    """
    # Find what was added before and after the original old text
    pos = expanded_old.find(original_old)
    if pos < 0:
        # Fallback: the expansion changed the text in unexpected ways (word boundary snap)
        # Try to find the best match
        return original_new
    prefix = expanded_old[:pos]
    suffix = expanded_old[pos + len(original_old):]
    return prefix + original_new + suffix


def diff_documents(old_docx_path, new_docx_path, context_words=5,
                   ensure_unique=True):
    """
    Compare two .docx files and produce redline-format changes.

    Args:
        old_docx_path: Path to original document
        new_docx_path: Path to revised document
        context_words: Number of context words around changes
        ensure_unique: If True (default), expand text snippets to be unique
            in the source document so apply doesn't match the wrong location.

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
                        "_source_para": anchor,
                    })
                elif not new_text.strip():
                    # Pure deletion
                    change_num += 1
                    redlines.append({
                        "type": "delete",
                        "text": old_text,
                        "title": f"Change {change_num}",
                        "_source_para": old_text,
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
                                "_source_para": old_text,
                            })
                        elif op_tag == "delete":
                            redlines.append({
                                "type": "delete",
                                "text": old_words,
                                "title": f"Change {change_num}",
                                "_source_para": old_text,
                            })
                        elif op_tag == "insert":
                            # Find anchor from preceding equal block
                            anchor = old_words if old_words else old_text[:40]
                            redlines.append({
                                "type": "insert_after",
                                "anchor": _get_preceding_context(old_text, new_words),
                                "text": new_words,
                                "title": f"Change {change_num}",
                                "_source_para": old_text,
                            })

        elif tag == "delete":
            for k in range(i1, i2):
                if old_paras[k].strip():
                    change_num += 1
                    redlines.append({
                        "type": "delete",
                        "text": old_paras[k],
                        "title": f"Change {change_num}",
                        "_source_para": old_paras[k],
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
                        "_source_para": old_paras[i1 - 1] if i1 > 0 else "",
                    })

    if ensure_unique:
        _ensure_unique_anchors(redlines, old_paras)
    else:
        # Strip internal metadata
        for r in redlines:
            r.pop("_source_para", None)

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
