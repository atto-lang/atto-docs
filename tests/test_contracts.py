#!/usr/bin/env python3
"""Offline invariants for UNEXECUTED Atto contributor contract drafts.

Not legal advice, not legal enforceability validation.
Run: python3 -m unittest discover -s tests -p 'test_*.py' -v
"""

from fractions import Fraction
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPANY_PATH = ROOT / "agreements" / "founding-contributor-dual-entity-nonvoting-ownership-agreement.md"
FOUNDATION_PATH = ROOT / "agreements" / "foundation-founding-contributor-compensation-and-ip-royalties.md"
FORK_PATH = ROOT / "agreements" / "founding-engineer-forking-and-naming-addendum.md"
README_PATH = ROOT / "README.md"


def require_phrases(text: str, phrases: tuple[str, ...], context: str) -> list[str]:
    low = text.casefold()
    return [f"{context} missing: {phrase}" for phrase in phrases
            if phrase.casefold() not in low]


def audit_company(text: str) -> list[str]:
    issues = require_phrases(text, (
        "DRAFT FOR LEGAL REVIEW",
        "4.00% of its fully diluted equity at the grant date",
        "**non-voting** class of shares",
        "**no ordinary voting rights**",
        "nonwaivable statutory",
        "Company equity only",
        "Foundation has no privately issued shares or 4% equity ownership award",
        "Foundation is **not an equity issuer under this Agreement**",
        "no fixed share of Foundation donations",
        "separate Foundation compensation",
        "no automatic Foundation payment",
        "three (3) qualifying months",
        "thirty-six (36) qualifying monthly installments",
        "earliest full vesting: **end of month 39**",
        "three (3) Qualifying Contributions per month",
        "at the initial lawful grant and may be diluted",
        "AttoLang is presently proprietary",
        "not open source",
        "Foundation compensation must be separately approved and contracted",
        "no Foundation equity is issued or contemplated",
    ), "Company")
    if "**Foundation grant (conditional):**" in text:
        issues.append("obsolete conditional Foundation equity grant")
    if re.search(r"(?i)\b5(?:\.0+)?\s*%(?!\w)", text):
        issues.append("stale 5% percentage")
    if re.search(r"(?im)\bFoundation\s+(?:shall|will)\s+(?:issue|grant)\s+(?:the Contributor )?(?:4(?:\.0+)?\s*%\s*)?(?:private )?(?:shares|equity)", text):
        issues.append("Foundation equity issuance asserted")
    if re.search(r"(?im)\bFoundation\s+(?:shall|will)\s+pay\s+(?:the Contributor )?4(?:\.0+)?\s*%", text):
        issues.append("automatic four-percent Foundation payout")
    numbers = [int(n) for n in re.findall(r"^# ARTICLE (\d+)\b", text, re.M)]
    if numbers != list(range(1, 13)):
        issues.append(f"article sequence incorrect: {numbers}")
    markers = ("# SCHEDULE A", "# SCHEDULE B", "# SCHEDULE C",
               "# SCHEDULE D", "# SIGNATURES", "**End of Agreement")
    places = [text.find(m) for m in markers]
    if any(p == -1 for p in places) or places != sorted(places):
        issues.append("schedules must precede execution signatures")
    for label in ("**Founder**", "**AttoPL Co — Authorized Representative**",
                  "**Founding Contributor**"):
        if label not in text:
            issues.append(f"missing expected signer: {label}")
    if "**Atto Foundation — Authorized Representative" in text:
        issues.append("Company contract wrongly asks Foundation to sign an equity instrument")
    return issues


def audit_foundation(text: str) -> list[str]:
    issues = require_phrases(text, (
        "DRAFT FOR LEGAL REVIEW",
        "not an equity grant",
        "does not own 4% of the Foundation",
        "no private equity",
        "no ordinary voting rights",
        "no ordinary voting",
        "no automatic salary",
        "no royalty rate",
        "30 calendar days",
        "Foundation's authorized **disinterested** decision-makers must approve",
        "in advance",
        "independent market comparables",
        "Schedule A — Paid Services Work Order",
        "before compensable services start",
        "earned and legally owed",
        "mandatory law",
        "no royalty exists unless",
        "specifically identified, independently owned",
        "chain of title",
        "demonstrated fair-market value",
        "no default 4% royalty",
        "Foundation-wide donations",
        "no double payment",
        "no perpetual Foundation economic entitlement",
        "No work order is authorized while these terms are blank",
        "No royalty is granted while these terms are blank",
        "three (3) accepted substantive contributions per month",
        "These periods do not vest Foundation shares",
        "not open source",
        "IRC 457/409A",
        "Form 990/Schedule L",
    ), "Foundation")
    if re.search(r"(?im)\bFoundation\s+(?:shall|will)\s+(?:issue|grant)\s+(?:the Contributor )?(?:4(?:\.0+)?\s*%\s*)?(?:private )?(?:shares|equity)", text):
        issues.append("Foundation falsely offering shares")
    if re.search(r"(?im)\bFoundation\s+(?:shall|will)\s+pay\s+(?:the Contributor )?4(?:\.0+)?\s*%", text):
        issues.append("Foundation falsely guaranteeing four-percent revenue")
    if text.find("## SCHEDULE A") > text.find("## SIGNATURES"):
        issues.append("Foundation schedules must precede signatures")
    return issues


def audit_fork(text: str) -> list[str]:
    return require_phrases(text, (
        "Proposed contractual addendum",
        "currently **proprietary software**",
        "independent **private forks**",
        "“Atto”",
        "“AttoLang”",
        "no corporate or Foundation equity",
        "4% interest in AttoPL Co / Atto Co",
        "Foundation, if organized as a charitable 501(c)(3), does not issue private equity",
        "non-voting",
        "no ordinary Foundation voting rights",
        "automatic salary",
        "cannot use",
    ), "Forking")


def audit_readme(text: str) -> list[str]:
    return require_phrases(text, (
        "4.00% non-voting equity",
        "in AttoPL Co / Atto Co only",
        "foundation-founding-contributor-compensation-and-ip-royalties.md",
        "does not issue",
        "signed paid-service",
        "no automatic 4% Foundation ownership",
        "No Foundation salary/royalty is guaranteed",
        "not a legal approval",
        "private",
    ), "README")


class ContractDraftSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.company = COMPANY_PATH.read_text(encoding="utf-8")
        cls.foundation = FOUNDATION_PATH.read_text(encoding="utf-8")
        cls.fork = FORK_PATH.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")

    def test_company_invariants(self):
        self.assertEqual([], audit_company(self.company))

    def test_foundation_invariants(self):
        self.assertEqual([], audit_foundation(self.foundation))

    def test_fork_invariants(self):
        self.assertEqual([], audit_fork(self.fork))

    def test_readme_invariants(self):
        self.assertEqual([], audit_readme(self.readme))

    def test_company_vesting_arithmetic(self):
        company_award = Fraction(4)
        for month, expected_points in (
            (0, Fraction(0)), (3, Fraction(0)), (4, Fraction(1, 9)),
            (15, Fraction(4, 3)), (27, Fraction(8, 3)), (39, Fraction(4)),
            (52, Fraction(4))
        ):
            installments = min(36, max(0, month - 3))
            self.assertEqual(expected_points, company_award * installments / 36)

    def test_five_percent_company_grant_mutation_fails(self):
        altered = self.company.replace("**4.00%**", "**5.00%**", 1)
        self.assertTrue(audit_company(altered))

    def test_company_voting_mutation_fails(self):
        altered = self.company.replace("**no ordinary voting rights**",
                                       "**ordinary voting rights**", 1)
        self.assertTrue(any("no ordinary voting" in x for x in audit_company(altered)))

    def test_company_foundation_grant_mutation_fails(self):
        altered = self.company + "\nFoundation shall issue 4% equity.\n"
        self.assertTrue(any("Foundation equity issuance" in x for x in audit_company(altered)))

    def test_company_foundation_revenue_mutation_fails(self):
        altered = self.company + "\nFoundation shall pay 4% of gross donations.\n"
        self.assertTrue(any("four-percent" in x for x in audit_company(altered)))

    def test_company_39_month_schedule_mutation_fails(self):
        altered = self.company.replace("Earliest full vesting: **end of month 39**",
                                       "Earliest full vesting: **end of month 36**", 1)
        self.assertNotEqual(self.company, altered)
        self.assertTrue(audit_company(altered))

    def test_company_missing_proprietary_notice_fails(self):
        altered = self.company.replace("AttoLang is presently proprietary",
                                       "AttoLang is publicly licensed", 1)
        self.assertTrue(audit_company(altered))

    def test_company_missing_foundation_separation_fails(self):
        altered = self.company.replace(
            "Foundation is **not an equity issuer under this Agreement**",
            "Foundation is an equity issuer under this Agreement", 1)
        self.assertTrue(audit_company(altered))

    def test_company_invalid_signature_order_fails(self):
        altered = self.company.replace("# SCHEDULE D", "# INCORRECT SCHEDULE", 1)
        self.assertTrue(any("schedules must precede" in x for x in audit_company(altered)))

    def test_foundation_automatic_salary_mutation_fails(self):
        altered = self.foundation.replace("no automatic salary",
                                           "a guaranteed automatic salary", 1)
        self.assertTrue(audit_foundation(altered))

    def test_foundation_default_royalty_mutation_fails(self):
        altered = self.foundation.replace("no default 4% royalty",
                                           "a default 4% royalty", 1)
        self.assertTrue(audit_foundation(altered))

    def test_foundation_unauthorized_stock_mutation_fails(self):
        altered = self.foundation + "\nFoundation will issue 4% equity.\n"
        self.assertTrue(any("falsely offering shares" in x for x in audit_foundation(altered)))

    def test_foundation_donation_percent_mutation_fails(self):
        altered = self.foundation + "\nFoundation shall pay 4% of all donations.\n"
        self.assertTrue(any("falsely guaranteeing" in x for x in audit_foundation(altered)))

    def test_foundation_missing_disinterested_approval_fails(self):
        altered = self.foundation.replace(
            "Foundation\'s authorized **disinterested** decision-makers must approve",
            "Foundation\'s authorized interested decision-makers must approve", 1)
        self.assertTrue(audit_foundation(altered))

    def test_foundation_missing_chain_of_title_fails(self):
        altered = self.foundation.replace("chain of title", "ownership unspecified", 1)
        self.assertTrue(audit_foundation(altered))

    def test_foundation_missing_fair_market_comparables_fails(self):
        altered = self.foundation.replace("independent market comparables", "unsourced prices", 1)
        self.assertTrue(audit_foundation(altered))

    def test_fork_public_access_mutation_fails(self):
        altered = self.fork.replace("independent **private forks**",
                                    "independent public forks", 1)
        self.assertTrue(audit_fork(altered))

    def test_fork_wrong_foundation_stock_claim_fails(self):
        altered = self.fork.replace(
            "Foundation, if organized as a charitable 501(c)(3), does not issue private equity",
            "Foundation issues 4% private equity", 1)
        self.assertTrue(audit_fork(altered))

    def test_missing_separate_foundation_document_link_fails(self):
        altered = self.readme.replace(
            "foundation-founding-contributor-compensation-and-ip-royalties.md",
            "missing-foundation-document.md", 1)
        self.assertTrue(audit_readme(altered))


if __name__ == "__main__":
    unittest.main()
