"""Cross-agreement comparison report.

Compares redline sets across multiple related agreements to flag
inconsistencies in provisions that should be aligned.
"""

from difflib import SequenceMatcher


# Common provision categories for matching across agreements
PROVISION_KEYWORDS = {
    "liability_cap": ["liability", "cap", "aggregate", "limitation"],
    "indemnification": ["indemnif", "hold harmless", "losses"],
    "arbitration": ["arbitration", "dispute", "lcia", "aaa", "jams"],
    "termination": ["terminat", "expir"],
    "assignment": ["assign", "transfer", "successor"],
    "change_of_control": ["change of control", "merger", "acquisition"],
    "confidentiality": ["confidential", "non-disclosure"],
    "sla": ["uptime", "availability", "service level"],
    "fees": ["fee", "pricing", "payment", "compensation"],
    "ip_ownership": ["intellectual property", "ip", "ownership", "license"],
    "governing_law": ["governing law", "jurisdiction", "venue"],
    "non_compete": ["non-compete", "non compete", "competitive"],
    "data_protection": ["data protection", "privacy", "gdpr", "personal data"],
    "insurance": ["insurance", "coverage"],
    "audit": ["audit", "inspect", "record"],
    "force_majeure": ["force majeure"],
    "warranty": ["warranty", "warrant", "as-is", "as is"],
    "amendment": ["amend", "modif", "waiver"],
    "renewal": ["renew", "auto-renew", "non-renewal"],
    "notice": ["notice", "notification"],
}


def _classify_redline(redline):
    """Classify a redline into provision categories based on text content."""
    # Combine all text fields for matching
    text_parts = []
    for field in ("title", "old", "new", "text", "anchor", "rationale"):
        if field in redline:
            text_parts.append(redline[field])
    combined = " ".join(text_parts).lower()

    categories = []
    for category, keywords in PROVISION_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            categories.append(category)

    return categories if categories else ["other"]


def compare_agreements(agreement_redlines):
    """
    Compare redline sets across multiple agreements.

    Args:
        agreement_redlines: Dict of {agreement_name: [redlines]}
            e.g. {"tri-party": [...], "bpa": [...]}

    Returns:
        Dict with:
            "agreements": list of agreement names
            "provisions": dict of {category: {agreement: [redlines]}}
            "inconsistencies": list of flagged inconsistencies
            "coverage_gaps": list of categories present in one but not all
    """
    agreements = list(agreement_redlines.keys())

    # Classify all redlines
    provisions = {}
    for name, redlines in agreement_redlines.items():
        for rl in redlines:
            categories = _classify_redline(rl)
            for cat in categories:
                provisions.setdefault(cat, {}).setdefault(name, []).append(rl)

    # Find inconsistencies -- provisions present in multiple agreements
    inconsistencies = []
    for cat, by_agreement in provisions.items():
        if len(by_agreement) < 2:
            continue

        # Compare the redlines across agreements
        agreement_names = list(by_agreement.keys())
        for i in range(len(agreement_names)):
            for j in range(i + 1, len(agreement_names)):
                a1, a2 = agreement_names[i], agreement_names[j]
                rls1, rls2 = by_agreement[a1], by_agreement[a2]

                # Check if the proposed changes are aligned
                for rl1 in rls1:
                    for rl2 in rls2:
                        similarity = _compare_redlines(rl1, rl2)
                        if similarity["conflict"]:
                            inconsistencies.append({
                                "category": cat,
                                "agreement_1": a1,
                                "agreement_2": a2,
                                "redline_1": _summarize_redline(rl1),
                                "redline_2": _summarize_redline(rl2),
                                "issue": similarity["issue"],
                            })

    # Find coverage gaps
    coverage_gaps = []
    for cat, by_agreement in provisions.items():
        missing = set(agreements) - set(by_agreement.keys())
        if missing:
            present = set(by_agreement.keys())
            coverage_gaps.append({
                "category": cat,
                "present_in": sorted(present),
                "missing_from": sorted(missing),
            })

    return {
        "agreements": agreements,
        "provisions": provisions,
        "inconsistencies": inconsistencies,
        "coverage_gaps": coverage_gaps,
    }


def _compare_redlines(rl1, rl2):
    """Compare two redlines for consistency."""
    # If both are replacements, check if new text is similar
    if rl1["type"] == "replace" and rl2["type"] == "replace":
        old_sim = SequenceMatcher(
            None, rl1["old"].lower(), rl2["old"].lower()
        ).ratio()
        new_sim = SequenceMatcher(
            None, rl1["new"].lower(), rl2["new"].lower()
        ).ratio()

        if old_sim > 0.5 and new_sim < 0.5:
            return {
                "conflict": True,
                "issue": "Same provision type but different proposed changes"
            }

    # Different types for similar provisions
    if rl1["type"] != rl2["type"]:
        title1 = rl1.get("title", "").lower()
        title2 = rl2.get("title", "").lower()
        if SequenceMatcher(None, title1, title2).ratio() > 0.6:
            return {
                "conflict": True,
                "issue": f"Different approaches: {rl1['type']} vs {rl2['type']}"
            }

    return {"conflict": False, "issue": None}


def _summarize_redline(rl):
    """Create a brief summary of a redline for reporting."""
    rtype = rl["type"]
    title = rl.get("title", "")
    section = rl.get("section", "")

    parts = []
    if section:
        parts.append(f"Section {section}")
    if title:
        parts.append(title)
    parts.append(f"({rtype})")

    if rtype == "replace":
        parts.append(f"'{rl['old'][:30]}...' -> '{rl['new'][:30]}...'")
    elif rtype == "delete":
        parts.append(f"Delete '{rl['text'][:40]}...'")

    return " ".join(parts)


def format_comparison_report(result):
    """Format comparison result as markdown."""
    lines = ["# Cross-Agreement Comparison Report\n"]
    lines.append(f"**Agreements:** {', '.join(result['agreements'])}\n")

    # Inconsistencies
    if result["inconsistencies"]:
        lines.append("## Inconsistencies\n")
        for inc in result["inconsistencies"]:
            lines.append(f"### {inc['category'].replace('_', ' ').title()}")
            lines.append(f"- **{inc['agreement_1']}**: {inc['redline_1']}")
            lines.append(f"- **{inc['agreement_2']}**: {inc['redline_2']}")
            lines.append(f"- **Issue**: {inc['issue']}\n")
    else:
        lines.append("## Inconsistencies\n\nNone found.\n")

    # Coverage gaps
    if result["coverage_gaps"]:
        lines.append("## Coverage Gaps\n")
        lines.append("| Provision | Present In | Missing From |")
        lines.append("|-----------|-----------|--------------|")
        for gap in result["coverage_gaps"]:
            lines.append(
                f"| {gap['category'].replace('_', ' ').title()} "
                f"| {', '.join(gap['present_in'])} "
                f"| {', '.join(gap['missing_from'])} |"
            )
    else:
        lines.append("## Coverage Gaps\n\nAll provisions covered across all agreements.\n")

    # Provision mapping
    lines.append("\n## Provision Coverage Matrix\n")
    agreements = result["agreements"]
    header = "| Provision | " + " | ".join(agreements) + " |"
    sep = "|-----------|" + "|".join(["---"] * len(agreements)) + "|"
    lines.append(header)
    lines.append(sep)

    for cat, by_agreement in sorted(result["provisions"].items()):
        row = f"| {cat.replace('_', ' ').title()} |"
        for name in agreements:
            count = len(by_agreement.get(name, []))
            row += f" {count} |" if count else " - |"
        lines.append(row)

    return "\n".join(lines)
