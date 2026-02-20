"""Tests for cross-agreement comparison."""

from legal_redline.compare import (
    compare_agreements,
    _classify_redline,
    format_comparison_report,
)


class TestClassifyRedline:
    def test_liability_classification(self):
        rl = {"type": "replace", "old": "liability cap of $1M", "new": "unlimited liability"}
        categories = _classify_redline(rl)
        assert "liability_cap" in categories

    def test_indemnification(self):
        rl = {"type": "delete", "text": "shall indemnify and hold harmless"}
        categories = _classify_redline(rl)
        assert "indemnification" in categories

    def test_multiple_categories(self):
        rl = {"type": "replace",
              "old": "liability for indemnification claims",
              "new": "total liability"}
        categories = _classify_redline(rl)
        assert "liability_cap" in categories
        assert "indemnification" in categories

    def test_unknown_falls_to_other(self):
        rl = {"type": "replace", "old": "xyz", "new": "abc"}
        categories = _classify_redline(rl)
        assert categories == ["other"]


class TestCompareAgreements:
    def test_finds_coverage_gaps(self):
        agreements = {
            "agreement_a": [
                {"type": "replace", "old": "liability cap", "new": "no cap"}
            ],
            "agreement_b": [
                {"type": "replace", "old": "indemnify", "new": "no indemnity"}
            ],
        }
        result = compare_agreements(agreements)
        assert len(result["coverage_gaps"]) > 0
        categories_missing = {g["category"] for g in result["coverage_gaps"]}
        assert "liability_cap" in categories_missing or "indemnification" in categories_missing

    def test_no_gaps_when_same_categories(self):
        agreements = {
            "a": [{"type": "replace", "old": "liability cap", "new": "no cap"}],
            "b": [{"type": "replace", "old": "total liability", "new": "unlimited"}],
        }
        result = compare_agreements(agreements)
        # Both should have liability_cap — no gap for that category
        liability_gaps = [g for g in result["coverage_gaps"] if g["category"] == "liability_cap"]
        assert len(liability_gaps) == 0

    def test_empty_agreements(self):
        result = compare_agreements({})
        assert result["agreements"] == []
        assert result["inconsistencies"] == []
        assert result["coverage_gaps"] == []


class TestFormatReport:
    def test_produces_markdown(self):
        result = compare_agreements({
            "a": [{"type": "replace", "old": "liability", "new": "no liability"}],
        })
        md = format_comparison_report(result)
        assert "# Cross-Agreement Comparison Report" in md
        assert "a" in md
