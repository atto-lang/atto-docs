#!/usr/bin/env python3
"""Offline invariants for proposed Atto contracts. Does not assert legal validity."""

from fractions import Fraction
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRIBUTOR = ROOT / "agreements" / "founding-contributor-dual-entity-nonvoting-ownership-agreement.md"
FORKING = ROOT / "agreements" / "founding-engineer-forking-and-naming-addendum.md"


def audit_contributor(text: str) -> list[str]:
    problems = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    require("**Status:** DRAFT FOR LEGAL REVIEW" in text, "not marked as draft")
    require("not executable until" in text, "missing pre-execution warning")
    require("proprietary, not generally open source" in text, "proprietary status unclear")
    require(text.count("**Company grant:**") == 1, "expected one Company grant")
    require(text.count("**Foundation grant (conditional):**") == 1, "expected one conditional Foundation grant")

    for phrase in (
        "**4.00%** interest in the Company's", "**4.00%** interest in the Foundation's",
        "not a shared 4% pool", "fully diluted", "non-voting",
        "no ordinary votes", "no board or committee seat",
        "No clause purports to waive nonwaivable statutory rights",
        "Foundation grant is pending", "cannot legally be completed",
        "charitable nonprofit cannot grant", "No Foundation equity is represented as issued",
        "definitive instruments", "Neither 4% award conveys any ordinary voting right",
        "**without ordinary voting rights**",
        "not a separate contractual right", "No dividend or distribution is guaranteed",
        "three (3) Qualifying Contributions per month", "thirty-six (36)",
        "39 months", "0.111111 percentage points",
    ):
        require(phrase.lower() in text.lower(), f"missing protective language: {phrase}")

    require(not re.search(r"\b5(?:\.0+)?\s*%", text), "stale 5% grant/revenue percentage")
    require(not re.search(r"(?i)^\s*(?:[^#\n]*?)\b(?:Five Percent Equity|Revenue Participation and Future)\b", text, re.M),
            "stale article or commitment title")
    require("No provision authorizes distributions of charitable Foundation earnings" in text,
            "missing private-inurement prohibition")
    require("COMPANY GRANT TARGET".lower() in text.lower() and "FOUNDATION GRANT TARGET".lower() in text.lower(),
            "Schedule B is missing the dual entity targets")
    require("Additional Contractual Revenue Share:** None." in text,
            "revenue share not explicitly disclaimed")

    articles = [int(x) for x in re.findall(r"^# ARTICLE (\d+)\b", text, re.M)]
    require(articles == list(range(1, 13)), f"article numbering incorrect: {articles}")

    section_names = (
        "# SCHEDULE A", "# SCHEDULE B", "# SCHEDULE C",
        "# SCHEDULE D", "# SIGNATURES", "**End of Agreement",
    )
    places = [text.find(n) for n in section_names]
    require(all(x >= 0 for x in places) and places == sorted(places),
            "schedule/signature order missing or incorrect")
    require("**Atto Foundation — Authorized Representative" in text, "Foundation signature block missing")
    require("**AttoPL Co — Authorized Representative" in text, "Company signature block missing")
    require("**Founding Contributor**" in text, "Contributor signature block missing")
    require("**Founder**" in text, "Founder signature block missing")
    require("[TBD]" in text and "legal status:" in text.lower(),
            "entity/capitalization decisions appear falsely complete")
    require("no ordinary voting" in text.lower(), "non-voting scope unclear")
    return problems


def audit_forking(text: str) -> list[str]:
    problems = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    for phrase in (
        "Proposed contractual addendum", "currently **proprietary software**",
        "has **not** been released under a public open-source license",
        "independent **private forks**", "not** an open-source license",
        "“Atto”", "“AttoLang”", "own distinct project name",
        "without the Project Owner's prior written permission",
        "no corporate or Foundation equity", "no voting or governance rights",
        "conditional 4% ownership award", "non-voting",
        "charitable nonprofit Foundation cannot issue ordinary private equity",
    ):
        require(phrase.lower() in text.lower(), f"missing forking protection: {phrase}")

    require(not re.search(r"\b5(?:\.0+)?\s*%", text), "stale 5% reference")
    headings = [int(x) for x in re.findall(r"^## (\d+)\.", text, re.M)]
    require(headings == list(range(1, 9)), f"forking section numbering incorrect: {headings}")
    return problems


class ContractSafetyAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c = CONTRIBUTOR.read_text(encoding="utf-8")
        cls.f = FORKING.read_text(encoding="utf-8")

    def test_contributor_contract(self) -> None:
        self.assertEqual([], audit_contributor(self.c))

    def test_forking_addendum(self) -> None:
        self.assertEqual([], audit_forking(self.f))

    def test_monthly_vesting_fraction(self) -> None:
        # Percentage-points of entity ownership for a 4% grant, pre-dilution.
        award = Fraction(4, 1)
        for month, expected in (
            (3, Fraction(0)), (4, Fraction(1, 9)),
            (15, Fraction(4, 3)), (27, Fraction(8, 3)), (39, Fraction(4, 1))
        ):
            vested_installments = min(36, max(0, month - 3))
            self.assertEqual(expected, award * vested_installments / 36)

    def test_legacy_five_percent_is_rejected(self) -> None:
        changed = self.c.replace("**Company grant:**", "**Company grant:** 5% ", 1)
        self.assertIn("stale 5% grant/revenue percentage", audit_contributor(changed))

    def test_loss_of_foundation_grant_is_rejected(self) -> None:
        changed = self.c.replace("**Foundation grant (conditional):**", "**Foundation proposal:**", 1)
        self.assertTrue(any("Foundation grant" in m for m in audit_contributor(changed)))

    def test_loss_of_nonvoting_rights_is_rejected(self) -> None:
        changed = self.c.replace("**without ordinary voting rights**", "**with ordinary voting rights**", 1)
        # Check the unambiguous voting sentence, rather than relying on occurrence counts.
        self.assertIn("without ordinary voting rights", self.c)
        self.assertNotIn("without ordinary voting rights", changed)
        self.assertTrue(any("without ordinary voting rights" in m for m in audit_contributor(changed)))

    def test_misplaced_signature_page_is_rejected(self) -> None:
        changed = self.c.replace("# SCHEDULE D", "# WRONG SIGNATURE ORDER", 1)
        self.assertTrue(any("order" in m for m in audit_contributor(changed)))

    def test_unauthorized_public_forking_is_rejected(self) -> None:
        changed = self.f.replace("independent **private forks**", "independent public forks", 1)
        self.assertTrue(any("private forks" in m for m in audit_forking(changed)))

    def test_nonprofit_blocker_is_rejected_when_missing(self) -> None:
        changed = self.c.replace("Foundation grant is pending", "Foundation grant is vested", 1)
        self.assertTrue(any("Foundation grant is pending" in m for m in audit_contributor(changed)))

    def test_forking_does_not_auto_grant_equity(self) -> None:
        changed = self.f.replace("no corporate or Foundation equity", "equity in both corporations", 1)
        self.assertTrue(any("no corporate or Foundation equity" in m for m in audit_forking(changed)))


if __name__ == "__main__":
    unittest.main()
