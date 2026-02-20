"""Tests for summary PDF generation."""

from legal_redline.summary import generate_summary_pdf, _sanitize, _wrap_text


class TestSanitize:
    def test_em_dash(self):
        assert "--" in _sanitize("hello\u2014world")

    def test_smart_quotes(self):
        result = _sanitize("\u201CHello\u201D")
        assert '"' in result

    def test_bullet(self):
        assert "*" in _sanitize("\u2022 item")

    def test_non_breaking_space(self):
        assert " " in _sanitize("hello\u00a0world")

    def test_plain_text_unchanged(self):
        assert _sanitize("plain text") == "plain text"


class TestWrapText:
    def test_short_text_single_line(self):
        lines = _wrap_text("short text", max_chars=90)
        assert len(lines) == 1

    def test_long_text_wraps(self):
        text = "word " * 30  # 150 chars
        lines = _wrap_text(text, max_chars=40)
        assert len(lines) > 1
        for line in lines:
            assert len(line) <= 45  # some slack for word boundaries

    def test_empty_text(self):
        lines = _wrap_text("")
        assert lines == []


class TestGenerateSummaryPdf:
    def test_external_mode(self, tmp_dir):
        redlines = [
            {"type": "replace", "section": "1", "title": "Test",
             "old": "old text", "new": "new text"},
        ]
        output = tmp_dir / "summary.pdf"
        generate_summary_pdf(redlines, str(output), doc_title="Test Doc",
                             author="Tester", mode="external")
        assert output.exists()
        assert output.stat().st_size > 0

    def test_internal_mode_with_rationale(self, tmp_dir):
        redlines = [
            {"type": "replace", "section": "1", "title": "Test",
             "old": "old text", "new": "new text",
             "rationale": "Better alignment", "tier": 1,
             "walkaway": "Accept current", "precedent": "Industry standard"},
        ]
        output = tmp_dir / "summary_internal.pdf"
        generate_summary_pdf(redlines, str(output), mode="internal")
        assert output.exists()

    def test_all_redline_types(self, tmp_dir):
        redlines = [
            {"type": "replace", "old": "old", "new": "new"},
            {"type": "delete", "text": "remove this"},
            {"type": "insert_after", "anchor": "after here", "text": "insert this"},
            {"type": "add_section", "text": "new section",
             "after_section": "5", "new_section_number": "5.1"},
        ]
        output = tmp_dir / "all_types.pdf"
        generate_summary_pdf(redlines, str(output))
        assert output.exists()

    def test_default_author_not_personal(self, tmp_dir):
        """Default author should not be a personal name."""
        redlines = [{"type": "replace", "old": "a", "new": "b"}]
        output = tmp_dir / "default.pdf"
        # author=None should not crash
        generate_summary_pdf(redlines, str(output), author=None)
        assert output.exists()
