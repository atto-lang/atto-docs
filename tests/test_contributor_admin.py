#!/usr/bin/env python3
"""Negative and arithmetic tests for synthetic, non-executable legal planning."""

from contextlib import redirect_stdout
from copy import deepcopy
from fractions import Fraction
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts import contributor_admin as admin

ROOT = Path(__file__).resolve().parents[1]
MULTI = ROOT / "fixtures/multi_grant_simulation.json"
SEQ = ROOT / "fixtures/sequential_dilution_simulation.json"
SCHEMA = ROOT / "schemas/contributor-registry.schema.json"


class ContributorAdministrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simultaneous = json.loads(MULTI.read_text(encoding="utf-8"))
        cls.sequential = json.loads(SEQ.read_text(encoding="utf-8"))

    def altered(self):
        return deepcopy(self.simultaneous)

    def rejected(self, doc, fragment):
        with self.assertRaises(admin.ContractValidationError) as err:
            admin.validate_registry(doc)
        self.assertIn(fragment, str(err.exception))

    def test_synthetic_simultaneous_three_awards(self):
        report = admin.validate_registry(self.altered())
        self.assertEqual(report["total_grants"], 3)
        self.assertEqual(report["base_fully_diluted_units"], 22000)
        self.assertEqual(report["planned_post_grants_fully_diluted_units"], 25000)
        self.assertEqual([r["proposed_units"] for r in report["awards"]], [1000] * 3)
        self.assertEqual([r["at_grant_percent"] for r in report["awards"]], ["4.000000%"] * 3)
        self.assertEqual([r["post_all_grants_percent"] for r in report["awards"]], ["4.000000%"] * 3)

    def test_synthetic_sequential_shows_dilution(self):
        report = admin.validate_registry(deepcopy(self.sequential))
        self.assertEqual(report["company_strategy"], "sequential")
        self.assertEqual(report["base_fully_diluted_units"], 57600)
        self.assertEqual(report["planned_post_grants_fully_diluted_units"], 62500)
        self.assertEqual([r["proposed_units"] for r in report["awards"]], [2400, 2500])
        self.assertEqual([r["at_grant_percent"] for r in report["awards"]],
                         ["4.000000%", "4.000000%"])
        self.assertEqual([r["post_all_grants_percent"] for r in report["awards"]],
                         ["3.840000%", "4.000000%"])

    def test_company_awards_are_only_plans_not_issuance(self):
        report = admin.validate_registry(self.altered())
        self.assertEqual(report["legal_effect"], "NONE")
        self.assertFalse(report["human_approval_and_signatures_authenticated"])
        self.assertFalse(report["shares_issued"])
        self.assertFalse(report["foundation_salary_or_royalty_authorized"])
        self.assertEqual(report["foundation_ownership_bps"], 0)
        self.assertEqual(report["machine_validation"], "SCHEMA_AND_ARITHMETIC_ONLY")

    def test_accepted_months_cliff_and_pause(self):
        report = admin.validate_registry(self.altered())
        alpha, beta, gamma = [row["vesting"] for row in report["awards"]]
        self.assertEqual((alpha["cliff_months_accepted"], alpha["post_cliff_installments"],
                          alpha["rejected_months"]), (3, 2, 1))
        self.assertEqual(alpha["fraction_of_original_grant"], str(Fraction(1, 18)))
        self.assertEqual((beta["cliff_months_accepted"], beta["post_cliff_installments"]), (3, 1))
        self.assertEqual(gamma["cliff_months_accepted"], 0)
        self.assertEqual(gamma["post_cliff_installments"], 0)
        self.assertFalse(gamma["cliff_satisfied"])

    def test_fractional_units_not_silently_rounded(self):
        report = admin.validate_registry(self.altered())
        self.assertEqual(report["awards"][0]["vested_units_fractional_theoretical"], "500/9")
        self.assertTrue(report["awards"][0]["unit_rounding_requires_definitive_instrument"])

    def test_39_month_maximum_is_exact(self):
        doc = self.altered()
        for grant in doc["grants"]:
            grant["periods"] = []
        for month in range(1, 51):
            year = 2026 + (month - 1) // 12
            mon = (month - 1) % 12 + 1
            doc["grants"][0]["periods"].append({
                "month": f"{year}-{mon:02d}",
                "review": "accepted",
                "evidence_refs": [f"pr:alpha-{month}-unit-{n}" for n in range(3)],
                "reviewer_ref": "reviewer:board-independent"
            })
        report = admin.validate_registry(doc)
        vest = report["awards"][0]["vesting"]
        self.assertEqual(vest["post_cliff_installments"], 36)
        self.assertEqual(vest["fraction_of_original_grant"], "1")

    def test_stage_ready_for_counsel_not_actual_approval(self):
        doc = self.altered()
        doc["stage"] = "READY_FOR_COUNSEL"
        doc["counsel_packet_refs"] = {
            "entity_verification": "entity:verification-file",
            "cap_table_draft": "cap:draft-cap-table",
            "nonvoting_class_draft": "class:nonvoting-proposal",
            "outside_counsel_packet": "counsel:packet-ref",
            "authorized_signatory_plan": "doc:signatory-plan",
        }
        report = admin.validate_registry(doc)
        self.assertEqual(report["source_stage_claim"], "READY_FOR_COUNSEL")
        self.assertEqual(report["legal_effect"], "NONE")
        self.assertFalse(report["human_approval_and_signatures_authenticated"])

    def test_ready_for_counsel_requires_all_packet_references(self):
        doc = self.altered()
        doc["stage"] = "READY_FOR_COUNSEL"
        self.rejected(doc, "counsel_packet_refs")

    def test_ready_for_counsel_rejects_wrong_category(self):
        doc = self.altered()
        doc["stage"] = "READY_FOR_COUNSEL"
        doc["counsel_packet_refs"] = {
            "entity_verification": "entity:verification-file",
            "cap_table_draft": "cap:draft-cap-table",
            "nonvoting_class_draft": "class:nonvoting-proposal",
            "outside_counsel_packet": "counsel:packet-ref",
            "authorized_signatory_plan": "pr:some-approval",
        }
        self.rejected(doc, "incorrect evidence category")

    def test_claimed_approved_fails_closed(self):
        doc = self.altered()
        doc["stage"] = "APPROVED"
        self.rejected(doc, "APPROVED or EXECUTED")

    def test_claimed_executed_fails_closed(self):
        doc = self.altered()
        doc["stage"] = "EXECUTED"
        self.rejected(doc, "APPROVED or EXECUTED")

    def test_legal_attestation_cannot_be_true(self):
        doc = self.altered()
        doc["legal_claims_verified"] = True
        self.rejected(doc, "legal_claims_verified must be false")

    def test_live_registry_prohibited_in_repo(self):
        doc = self.altered()
        doc["mode"] = "production"
        self.rejected(doc, "simulation only")

    def test_foundation_receives_no_shares(self):
        doc = self.altered()
        doc["foundation"]["ownership_bps"] = 400
        self.rejected(doc, "cannot grant private ownership")

    def test_foundation_no_auto_salary(self):
        doc = self.altered()
        doc["foundation"]["compensation"] = "automatic_salary"
        self.rejected(doc, "independently approved")

    def test_foundation_no_auto_four_percent_royalty(self):
        doc = self.altered()
        doc["foundation"]["royalties"] = "four_percent_of_donations"
        self.rejected(doc, "no automatic royalty")

    def test_foundation_no_voting(self):
        doc = self.altered()
        doc["foundation"]["voting_rights"] = True
        self.rejected(doc, "no ordinary voting")

    def test_foundation_cannot_claim_tax_exemption(self):
        doc = self.altered()
        doc["foundation"]["nonprofit_status"] = "irs_approved"
        self.rejected(doc, "may not assert tax exemption")

    def test_company_grant_nonvoting_only(self):
        doc = self.altered()
        doc["grants"][1]["non_voting"] = False
        self.rejected(doc, "ordinary voting rights prohibited")

    def test_company_grant_percentage_exact_4(self):
        doc = self.altered()
        doc["grants"][0]["target_bps"] = 500
        self.rejected(doc, "400 basis points")

    def test_miscomputed_simultaneous_grant(self):
        doc = self.altered()
        doc["grants"][0]["proposed_units"] = 1001
        self.rejected(doc, "does not produce 4%")

    def test_simultaneous_integer_unit_gate(self):
        doc = self.altered()
        doc["company"]["base_fully_diluted_units"] = 22001
        self.rejected(doc, "integral units")

    def test_sequential_integer_unit_gate(self):
        doc = deepcopy(self.sequential)
        doc["company"]["base_fully_diluted_units"] = 22000
        self.rejected(doc, "integral new units")

    def test_sequential_unit_issuance_gate(self):
        doc = deepcopy(self.sequential)
        doc["grants"][1]["proposed_units"] = 2501
        self.rejected(doc, "does not produce 4% at issuance")

    def test_more_than_24_fully_diluted_grants_disallowed(self):
        doc = self.altered()
        doc["grants"] = [deepcopy(doc["grants"][0]) for _ in range(25)]
        self.rejected(doc, "1..24")

    def test_duplicate_contributor_disallowed(self):
        doc = self.altered()
        doc["grants"][1]["contributor_ref"] = doc["grants"][0]["contributor_ref"]
        self.rejected(doc, "duplicate contributor")

    def test_duplicate_grant_ref_disallowed(self):
        doc = self.altered()
        doc["grants"][1]["grant_ref"] = doc["grants"][0]["grant_ref"]
        self.rejected(doc, "repeated grant")

    def test_reused_evidence_cannot_double_count(self):
        doc = self.altered()
        doc["grants"][1]["periods"][0]["evidence_refs"][0] = \
            doc["grants"][0]["periods"][0]["evidence_refs"][0]
        self.rejected(doc, "evidence reused")

    def test_same_month_duplicate_evidence_cannot_count(self):
        doc = self.altered()
        doc["grants"][0]["periods"][0]["evidence_refs"][1] = \
            doc["grants"][0]["periods"][0]["evidence_refs"][0]
        self.rejected(doc, "duplicate evidence")

    def test_accepted_month_requires_three_distinct_evidence_refs(self):
        doc = self.altered()
        doc["grants"][0]["periods"][0]["evidence_refs"] = ["pr:only-one-evidence"]
        self.rejected(doc, ">=3 distinct")

    def test_pending_cannot_claim_reviewed(self):
        doc = self.altered()
        doc["grants"][2]["periods"][0]["reviewer_ref"] = "reviewer:fake-accepted"
        self.rejected(doc, "pending review cannot claim")

    def test_self_review_rejected_across_namespace(self):
        doc = self.altered()
        doc["grants"][0]["periods"][0]["reviewer_ref"] = "reviewer:alpha-demo"
        self.rejected(doc, "cannot self-review")

    def test_invalid_reviewer_reference(self):
        doc = self.altered()
        doc["grants"][0]["periods"][0]["reviewer_ref"] = "grant:unrelated-stake"
        self.rejected(doc, "reviewer: prefix")

    def test_evidence_must_be_actual_work_reference(self):
        doc = self.altered()
        doc["grants"][0]["periods"][0]["evidence_refs"][0] = "board:approved-salary"
        self.rejected(doc, "work/review artifacts")

    def test_unrecorded_month_cannot_vest(self):
        doc = self.altered()
        doc["grants"][0]["periods"][2]["month"] = "2026-04"
        self.rejected(doc, "contiguous from start_month")

    def test_invalid_month_rejected(self):
        doc = self.altered()
        doc["grants"][0]["periods"][0]["month"] = "2026-13"
        self.rejected(doc, "invalid YYYY-MM")

    def test_personal_email_in_registry_rejected(self):
        doc = self.altered()
        doc["grants"][0]["contributor_ref"] = "contrib:alex@example.com"
        self.rejected(doc, "short opaque")

    def test_unknown_pii_key_rejected(self):
        doc = self.altered()
        doc["grants"][0]["email_address"] = "dont-store@example.com"
        self.rejected(doc, "unrecognized keys")

    def test_bool_cannot_be_an_integer(self):
        doc = self.altered()
        doc["grants"][0]["target_bps"] = True
        self.rejected(doc, "bounded integer")

    def test_unrecognized_field_rejected(self):
        doc = self.altered()
        doc["FoundationProfitShare"] = "4%"
        self.rejected(doc, "unrecognized keys")

    def test_number_bound_prevents_overflow(self):
        doc = self.altered()
        doc["company"]["base_fully_diluted_units"] = 10**20
        self.rejected(doc, "invalid bounded integer")

    def test_empty_list_disallowed(self):
        doc = self.altered()
        doc["grants"] = []
        self.rejected(doc, "1..24")

    def test_fixture_schema_is_strict(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["foundation"]["properties"]["ownership_bps"]["const"], 0)
        self.assertEqual(schema["properties"]["grants"]["maxItems"], 24)
        self.assertEqual(schema["properties"]["grants"]["items"]["properties"]["target_bps"]["const"], 400)
        self.assertEqual(schema["properties"]["legal_claims_verified"]["const"], False)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "duplicate.json"
            p.write_text('{"status":"DRAFT","status":"EXECUTED"}', encoding="utf-8")
            with self.assertRaisesRegex(admin.ContractValidationError, "duplicate JSON object key"):
                admin.load_registry(p)

    def test_noninteger_float_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "float.json"
            p.write_text('{"units":22000.0}', encoding="utf-8")
            with self.assertRaisesRegex(admin.ContractValidationError, "floating point"):
                admin.load_registry(p)

    def test_nan_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "nan.json"
            p.write_text('{"units":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(admin.ContractValidationError, "NaN"):
                admin.load_registry(p)

    def test_oversized_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "oversized.json"
            p.write_text("x" * (admin.MAX_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(admin.ContractValidationError, "size limit"):
                admin.load_registry(p)

    def test_cli_audit_success_never_calls_it_legally_executed(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = admin.main(["audit", str(MULTI)])
        self.assertEqual(code, 0)
        report = json.loads(buf.getvalue())
        self.assertEqual(report["legal_effect"], "NONE")
        self.assertFalse(report["shares_issued"])

    def test_cli_invalid_registry_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fake.json"
            fake = self.altered()
            fake["stage"] = "EXECUTED"
            p.write_text(json.dumps(fake), encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = admin.main(["audit", str(p)])
            self.assertEqual(code, 2)
            result = json.loads(buf.getvalue())
            self.assertEqual(result["machine_validation"], "REJECTED")
            self.assertEqual(result["legal_effect"], "NONE")


if __name__ == "__main__":
    unittest.main()
