"""Remap redline section references from one document to another.

When a redline set was written for Document A (e.g., merchant agreement)
but needs to target Document B (e.g., tri-party), this module fuzzy-matches
the redline text against the new document and updates section references.
"""

import json
import re
from difflib import SequenceMatcher

from docx import Document


# Pattern for section numbers like "Section 7.2", "7.2", "Section 13.4(iii)"
SECTION_PATTERN = re.compile(
    r'(?:Section\s+)?(\d+(?:\.\d+)*(?:\([a-z]+\))?)',
    re.IGNORECASE
)


def _get_paragraphs(docx_path):
    """Extract paragraphs with their text and detected section numbers."""
    doc = Document(docx_path)
    paras = []
    for idx, para in enumerate(doc.paragraphs):
        text = para.text or ""
        if not text.strip():
            continue

        # Try to detect section number from paragraph
        section_match = re.match(r'^\s*(\d+(?:\.\d+)*)\s', text)
        section_num = section_match.group(1) if section_match else None

        paras.append({
            "index": idx,
            "text": text,
            "section": section_num,
        })
    return paras


def _find_best_match(search_text, paragraphs, threshold=0.6):
    """Find the paragraph with the best fuzzy match for search_text."""
    best_ratio = 0
    best_para = None

    search_lower = search_text.lower().strip()

    for para in paragraphs:
        para_lower = para["text"].lower()

        # Exact substring match
        if search_lower in para_lower:
            return para, 1.0

        # Fuzzy match
        ratio = SequenceMatcher(None, search_lower, para_lower).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_para = para

    if best_ratio >= threshold:
        return best_para, best_ratio
    return None, 0


def _find_nearest_section(paragraphs, target_idx):
    """Find the nearest section number at or before target paragraph index."""
    # Look backwards from the target paragraph
    for para in reversed(paragraphs):
        if para["index"] <= target_idx and para["section"]:
            return para["section"]
    return None


def remap_redlines(old_docx_path, new_docx_path, redlines, threshold=0.6):
    """
    Remap redline section references from old_docx to new_docx.

    For each redline, finds the matching text in the new document and
    updates the section reference.

    Args:
        old_docx_path: Path to original document (redlines were written for)
        new_docx_path: Path to new document (redlines should target)
        redlines: List of redline dicts
        threshold: Minimum fuzzy match ratio (0-1)

    Returns:
        Tuple of (updated_redlines, report) where report is a list of
        mapping results for each redline.
    """
    new_paras = _get_paragraphs(new_docx_path)
    report = []

    for idx, rl in enumerate(redlines):
        rtype = rl["type"]
        old_section = rl.get("section", "")

        # Get the search text based on type
        if rtype == "replace":
            search_text = rl["old"]
        elif rtype == "delete":
            search_text = rl["text"]
        elif rtype == "insert_after":
            search_text = rl["anchor"]
        elif rtype == "add_section":
            search_text = rl.get("text", "")
        else:
            report.append({
                "index": idx, "status": "SKIP",
                "reason": f"Unknown type: {rtype}"
            })
            continue

        # Find in new document
        match_para, ratio = _find_best_match(search_text, new_paras)

        if match_para is None:
            report.append({
                "index": idx, "status": "NOT_FOUND",
                "old_section": old_section,
                "search_text": search_text[:60],
            })
            continue

        # Find the section number in the new document
        new_section = _find_nearest_section(new_paras, match_para["index"])

        if new_section and new_section != old_section:
            rl["section"] = new_section
            report.append({
                "index": idx, "status": "REMAPPED",
                "old_section": old_section,
                "new_section": new_section,
                "match_ratio": round(ratio, 2),
            })
        elif new_section == old_section:
            report.append({
                "index": idx, "status": "UNCHANGED",
                "section": old_section,
                "match_ratio": round(ratio, 2),
            })
        else:
            report.append({
                "index": idx, "status": "NO_SECTION",
                "old_section": old_section,
                "match_ratio": round(ratio, 2),
            })

    return redlines, report
