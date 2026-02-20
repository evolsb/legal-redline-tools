"""Tests for section remapping."""

import copy

from docx import Document

from legal_redline.remap import remap_redlines, _find_best_match, _get_paragraphs


def _make_docx(tmp_path, name, paragraphs):
    """Helper to create a .docx with given paragraph texts."""
    path = tmp_path / name
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    doc.save(str(path))
    return path


class TestRemapDoesNotMutateInput:
    def test_deep_copy(self, tmp_path):
        old_doc = _make_docx(tmp_path, "old.docx", [
            "1.1 Original section text here",
        ])
        new_doc = _make_docx(tmp_path, "new.docx", [
            "2.1 Original section text here",
        ])
        original_redlines = [
            {"type": "replace", "section": "1.1",
             "old": "Original section text here", "new": "Updated text"}
        ]
        input_copy = copy.deepcopy(original_redlines)
        updated, report = remap_redlines(
            str(old_doc), str(new_doc), original_redlines
        )
        # Original should be unchanged
        assert original_redlines == input_copy
        # Updated copy should have new section
        assert updated[0]["section"] == "2.1"


class TestRemapSectionMapping:
    def test_section_remapped(self, tmp_path):
        old_doc = _make_docx(tmp_path, "old.docx", [
            "1.0 Some heading",
            "The liability cap shall be limited.",
        ])
        new_doc = _make_docx(tmp_path, "new.docx", [
            "3.0 Different heading",
            "The liability cap shall be limited.",
        ])
        redlines = [
            {"type": "replace", "section": "1.0",
             "old": "The liability cap shall be limited.",
             "new": "The liability cap is unlimited."}
        ]
        updated, report = remap_redlines(
            str(old_doc), str(new_doc), redlines
        )
        assert report[0]["status"] == "REMAPPED"
        assert updated[0]["section"] == "3.0"

    def test_section_unchanged(self, tmp_path):
        doc = _make_docx(tmp_path, "same.docx", [
            "1.0 Heading",
            "The text is here.",
        ])
        redlines = [
            {"type": "replace", "section": "1.0",
             "old": "The text is here.", "new": "New text."}
        ]
        updated, report = remap_redlines(str(doc), str(doc), redlines)
        assert report[0]["status"] == "UNCHANGED"

    def test_text_not_found(self, tmp_path):
        doc = _make_docx(tmp_path, "doc.docx", ["1.0 Heading", "Some text."])
        redlines = [
            {"type": "replace", "section": "1.0",
             "old": "Completely different text not in document",
             "new": "Replacement"}
        ]
        updated, report = remap_redlines(str(doc), str(doc), redlines)
        assert report[0]["status"] == "NOT_FOUND"


class TestFindBestMatch:
    def test_exact_substring(self):
        paras = [{"text": "The quick brown fox jumps", "index": 0, "section": None}]
        match, ratio = _find_best_match("brown fox", paras)
        assert match is not None
        assert ratio == 1.0

    def test_fuzzy_match_above_threshold(self):
        paras = [{"text": "The total aggregate liability", "index": 0, "section": None}]
        match, ratio = _find_best_match("total aggregate liabilities", paras, threshold=0.6)
        assert match is not None
        assert ratio >= 0.6

    def test_no_match_below_threshold(self):
        paras = [{"text": "Completely unrelated text", "index": 0, "section": None}]
        match, ratio = _find_best_match("liability cap provision", paras, threshold=0.6)
        # Ratio should be very low
        assert match is None or ratio < 0.6
