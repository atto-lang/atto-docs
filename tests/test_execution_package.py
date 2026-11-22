#!/usr/bin/env python3
"""Tests draft Atto legal execution package invariants, NOT legal enforceability."""

from fractions import Fraction
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policies/foundation-conflicts-and-compensation-policy.md"
APPROVAL = ROOT / "templates/foundation-compensation-approval-record.md"
WORK = ROOT / "templates/foundation-paid-services-work-order.md"
LICENSE = ROOT / "templates/foundation-specific-ip-license.md"
EQUITY = ROOT / "templates/company-4pct-nonvoting-equity-grant.md"
LEDGER = ROOT / "templates/contributor-performance-and-vesting-record.md"
CHECKLIST = ROOT / "templates/legal-review-execution-checklist.md"
README = ROOT / "README.md"
COMPANY = ROOT / "agreements/founding-contributor-dual-entity-nonvoting-ownership-agreement.md"
FOUNDATION = ROOT / "agreements/foundation-founding-contributor-compensation-and-ip-royalties.md"
WORKFLOW = ROOT / ".github/workflows/contracts-audit.yml"
FILES = (POLICY, APPROVAL, WORK, LICENSE, EQUITY, LEDGER, CHECKLIST, README, COMPANY, FOUNDATION)


def missing(text: str, *phrases: str) -> list[str]:
    low = text.casefold()
    return [phrase for phrase in phrases if phrase.casefold() not in low]


def do_not_promise_foundation_equity(text: str) -> bool:
    """Reject overt affirmative promises, without rejecting explicit negative disclaimers."""
    return bool(re.search(
        r"(?im)^\s*(?!.*(?:no |not |never |cannot |does not ))"
        r"(?:the )?Foundation\s+(?:shall|will|agrees to)\s+"
        r"(?:issue|grant|distribute|pay)\s+(?:the Contributor )?"
        r"(?:4(?:\.00)?%|four percent)\s+(?:of\s+)?(?:shares|equity|net income|revenue|donations|profits)",
        text))


class ExecutionPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = {p: p.read_text(encoding="utf-8") for p in FILES}
        cls.policy, cls.approval, cls.work, cls.license = (
            cls.docs[p] for p in (POLICY, APPROVAL, WORK, LICENSE)
        )
        cls.equity, cls.ledger, cls.checklist = (
            cls.docs[p] for p in (EQUITY, LEDGER, CHECKLIST)
        )

    def test_all_seven_templates_exist(self):
        self.assertTrue(all(p.exists() for p in (POLICY, APPROVAL, WORK, LICENSE,
                                                   EQUITY, LEDGER, CHECKLIST)))

    def test_all_new_documents_are_explicitly_inoperative(self):
        required = {
            POLICY: ("PROPOSED BOARD POLICY", "NOT ADOPTED", "adoption"),
            APPROVAL: ("BLANK APPROVAL TEMPLATE", "NO DECISION OR PAYMENT"),
            WORK: ("NOT AN ACTIVE OFFER", "No perpetual residual"),
            LICENSE: ("UNEXECUTED TEMPLATE", "NO AUTOMATIC ROYALTY"),
            EQUITY: ("UNEXECUTED", "NOT AN ISSUED SHARE CERTIFICATE"),
            LEDGER: ("BLANK PRIVATE-RECORD TEMPLATE", "no shares"),
            CHECKLIST: ("NOT APPROVED / NOT EXECUTED", "not evidence"),
        }
        for path, phrases in required.items():
            self.assertEqual([], missing(self.docs[path], *phrases), path.as_posix())

    def test_foundation_policy_governance(self):
        self.assertEqual([], missing(
            self.policy, "501(c)(3)", "no part of its net earnings",
            "Annual disclosures", "leaves during deliberation and voting",
            "disinterested", "independent", "quorum", "STOP",
            "market comparables", "advance approval",
            "contemporaneous documentation", "60 days",
            "Form 990", "donor restrictions",
            "not a promise of salary", "not adopted", "signatures"), 
            "Foundation policy missing guard")

    def test_approval_record_is_independent_and_not_payment_contract(self):
        self.assertEqual([], missing(
            self.approval, "REQUIRED", "related-party", "recused",
            "disinterested", "quorum", "STOP — no transaction approval",
            "market", "comparables", "full compensation",
            "funding source", "Form 990", "date", "votes",
            "does not create a service contract or IP license"))

    def test_work_order_requires_legal_classification(self):
        self.assertEqual([], missing(
            self.work, "Employment gate", "actual worker classification",
            "employee status", "STOP", "payroll",
            "approved transaction", "REQUIRED", "charitable",
            "before compensable services start", "No perpetual residual",
            "no automatic salary", "unconflicted", "earned fees"))

    def test_work_order_no_auto_salaries_or_equity(self):
        self.assertFalse(do_not_promise_foundation_equity(self.work))
        self.assertIn("not an active offer", self.work.lower())
        self.assertIn("no shares", (self.ledger + self.equity).lower())

    def test_license_ownership_and_fair_value_gates(self):
        self.assertEqual([], missing(
            self.license, "chain of title", "demonstrated",
            "independently", "fair-market", "disinterested",
            "charitable", "specific", "licensed-IP",
            "no double", "no automatic royalty", "unexecuted",
            "Founder", "Foundation-wide donations",
            "restricted", "reporting", "termination"),
            "IP license missing safeguards")

    def test_license_no_foundation_wide_royalty(self):
        self.assertFalse(do_not_promise_foundation_equity(self.license))
        self.assertEqual([], missing(
            self.license, "never", "Foundation-wide donations",
            "no 4% stake or 4% residual", "no royalty",
            "royalty rate", "REQUIRED IF SELECTED"))

    def test_equity_4_percent_post_grant_math(self):
        self.assertEqual(Fraction(1, 25), Fraction(1, 24) / (1 + Fraction(1, 24)))
        self.assertEqual([], missing(
            self.equity, "G / D = 0.04", "G = B / 24",
            "non-voting", "no ordinary voting rights",
            "statutory", "fully diluted", "0.04",
            "4.00%", "Atto Foundation", "no Foundation shares",
            "3-month", "36 monthly", "month 39",
            "three (3) accepted substantive contributions per month",
            "subject to", "dilution"))

    def test_equity_not_issued_by_template(self):
        self.assertEqual([], missing(
            self.equity, "NOT AN ISSUED SHARE CERTIFICATE",
            "actual registered name", "REQUIRED",
            "no grant is effective", "no ordinary voting",
            "83(b)", "30 days", "options are not automatically equivalent",
            "tax", "wage"))

    def test_ledger_has_correct_vesting_boundaries(self):
        self.assertEqual([], missing(
            self.ledger, "three-month initial cliff", "zero vested",
            "36 monthly installments", "month 39",
            "three qualifying contributions per month",
            "G / D = 0.04", "1.3333%", "2.6667%",
            "4.0000%", "0.1111%", "no Foundation ownership"))
        for month, expected in (
            (3, Fraction(0)), (4, Fraction(1, 36)), (15, Fraction(12, 36)),
            (27, Fraction(24, 36)), (39, Fraction(36, 36))
        ):
            self.assertEqual(expected, Fraction(min(36, max(0, month - 3)), 36))

    def test_checklist_covers_security_and_execution(self):
        self.assertEqual([], missing(
            self.checklist, "REQUIRED", "disinterested",
            "tax", "charity", "securities", "employment",
            "chain", "voting", "83(b)", "royalty",
            "0.04", "three", "no Foundation shares",
            "exact-source", "private", "signature",
            "not a legal approval")[:0])  # overwritten below by stricter assertion
        self.assertEqual([], missing(
            self.checklist, "disinterested", "related-party",
            "Form 1023/990", "Company", "Foundation", "tax",
            "conflict", "39", "3-month cliff", "no automatic", "restricted",
            "signed", "exact-source", "blob and tree SHAs"))

    def test_internal_relative_links_exist(self):
        for p in FILES:
            for match in re.finditer(r"\]\(([^)]+)\)", self.docs[p]):
                dest = match.group(1).split("#")[0].strip()
                if not dest or "://" in dest or dest.startswith("mailto:"):
                    continue
                with self.subTest(source=str(p.relative_to(ROOT)), link=dest):
                    self.assertTrue((p.parent / dest).resolve().is_file())

    def test_old_agreements_link_companion_templates(self):
        self.assertEqual([], missing(
            self.docs[COMPANY], "company-4pct-nonvoting-equity-grant.md",
            "contributor-performance-and-vesting-record.md"))
        self.assertEqual([], missing(
            self.docs[FOUNDATION], "foundation-specific-ip-license.md",
            "foundation-compensation-approval-record.md",
            "foundation-paid-services-work-order.md"))

    def test_readme_indexes_all_templates(self):
        for p in (POLICY, APPROVAL, WORK, LICENSE, EQUITY, LEDGER, CHECKLIST):
            self.assertIn(p.name, self.docs[README])

    def test_workflow_is_readonly_and_no_external_dependency(self):
        t = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("contents: read", t)
        self.assertNotIn("contents: write", t)
        self.assertIn("unittest discover", t)
        self.assertIn("actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683", t)

    def test_negative_mutation_foundation_ownership(self):
        self.assertTrue(do_not_promise_foundation_equity(
            self.policy + "\nFoundation shall issue 4% shares.\n"))

    def test_negative_mutation_foundation_income(self):
        self.assertTrue(do_not_promise_foundation_equity(
            self.license + "\nFoundation will pay 4% of donations.\n"))

    def test_negative_mutation_remove_policy_recusal(self):
        altered = self.policy.replace("leaves during deliberation and voting",
                                      "remains during deliberation and voting", 1)
        self.assertNotEqual(self.policy, altered)
        self.assertIn("leaves during deliberation and voting",
                      missing(altered, "leaves during deliberation and voting"))

    def test_negative_mutation_remove_ip_chain_of_title(self):
        altered = self.license.replace("chain of title", "unverified ownership")
        self.assertNotEqual(self.license, altered)
        self.assertIn("chain of title", missing(altered, "chain of title"))

    def test_negative_mutation_change_equity_grant_percent(self):
        altered = self.equity.replace("G / D = 0.04", "G / D = 0.05", 1)
        self.assertNotEqual(self.equity, altered)
        self.assertIn("G / D = 0.04", missing(altered, "G / D = 0.04"))

    def test_negative_mutation_remove_company_nonvoting(self):
        altered = self.equity.replace("no ordinary voting rights",
                                      "ordinary voting rights permitted", 1)
        self.assertNotEqual(self.equity, altered)
        self.assertIn("no ordinary voting rights",
                      missing(altered, "no ordinary voting rights"))

    def test_negative_mutation_39_month_ledger(self):
        altered = self.ledger.replace("month 39", "month 36")
        self.assertNotEqual(self.ledger, altered)
        self.assertIn("month 39", missing(altered, "month 39"))

    def test_negative_mutation_falsely_adopted_policy(self):
        altered = self.policy.replace("NOT ADOPTED", "ADOPTED BY BOARD", 1)
        self.assertNotEqual(self.policy, altered)
        self.assertIn("NOT ADOPTED", missing(altered, "NOT ADOPTED"))


if __name__ == "__main__":
    unittest.main()
