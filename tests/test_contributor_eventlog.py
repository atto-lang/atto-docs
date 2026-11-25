#!/usr/bin/env python3
"""Adversarial synthetic-review-chain tests; no authenticated legal actions."""

from copy import deepcopy
from contextlib import redirect_stdout
from fractions import Fraction
import io
import json
from pathlib import Path
import random
import tempfile
import unittest

from scripts import contributor_admin as admin
from scripts import contributor_eventlog as events

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/multi_grant_simulation.json"


class SyntheticReviewEvents(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for grant in self.registry["grants"]:
            grant["periods"] = []
        self.ledger = {"schema_version": 1, "mode": "simulation",
                       "log_ref": "ledger:synthetic-review-chain",
                       "registry_ref": self.registry["registry_ref"], "events": []}

    def add(self, kind, month, *, grant="alpha", refs=None,
            actor=None, depends=None):
        g = f"grant:{grant}-demo"
        actor = actor or (f"contrib:{grant}-demo" if kind in ("SUBMIT", "CURE")
                          else "reviewer:independent-verifier")
        event = {"seq": len(self.ledger["events"])+1,
                 "kind": kind, "grant_ref": g, "month": month,
                 "actor_ref": actor, "evidence_refs": refs if refs is not None else [],
                 "ref_event_seq": depends, "prev_sha256": (
                     self.ledger["events"][-1]["sha256"] if self.ledger["events"] else events.GENESIS)}
        event["sha256"] = events.digest_event(event)
        self.ledger["events"].append(event)
        return event["seq"]

    def submit(self, month, *, grant="alpha", attempt=1):
        first = self.add("SUBMIT", month, grant=grant,
                         refs=[f"pr:{grant}-{month}-a{attempt}-work{k}" for k in range(3)])
        return first

    def decided(self, month, decision, seq, *, grant="alpha"):
        self.add(decision, month, grant=grant, depends=seq)

    def validated(self, root=None):
        return events.validate_events(self.ledger, self.registry, root)

    def fails(self, phrase):
        with self.assertRaises(admin.ContractValidationError) as err:
            self.validated()
        self.assertIn(phrase, str(err.exception))

    def test_genesis_empty_chain_has_no_legal_effect(self):
        report = self.validated()
        self.assertEqual(report["chain_root_sha256"], events.GENESIS)
        self.assertFalse(report["signatures_authenticated"])
        self.assertFalse(report["grant_or_salary_authorized"])
        self.assertEqual(report["legal_effect"], "NONE")

    def test_accept_after_three_month_cliff_and_cure(self):
        s = self.submit("2026-01"); self.decided("2026-01", "ACCEPT", s)
        s = self.submit("2026-02"); self.decided("2026-02", "REJECT", s)
        self.add("CURE", "2026-02", refs=[
            f"pr:alpha-2026-02-cure-work{i}" for i in range(3)], depends=4)
        self.decided("2026-02", "ACCEPT", 5)
        s = self.submit("2026-03"); self.decided("2026-03", "ACCEPT", s)
        s = self.submit("2026-04"); self.decided("2026-04", "ACCEPT", s)
        report = self.validated(self.ledger["events"][-1]["sha256"])
        item = report["awards"][0]
        self.assertEqual((item["accepted_months"], item["rejected_months"],
                          item["post_cliff_installments"]), (4, 0, 1))
        self.assertEqual(item["not_a_legal_vesting_certification"], True)
        self.assertTrue(report["external_root_was_supplied"])
        self.assertFalse(report["signatures_authenticated"])

    def test_rejected_month_can_pause_without_vesting(self):
        for month, kind in (("2026-01", "ACCEPT"), ("2026-02", "REJECT"),
                            ("2026-03", "ACCEPT"), ("2026-04", "ACCEPT"),
                            ("2026-05", "ACCEPT")):
            s = self.submit(month)
            self.decided(month, kind, s)
        r = self.validated()["awards"][0]
        self.assertEqual((r["accepted_months"], r["rejected_months"],
                          r["post_cliff_installments"]), (4, 1, 1))

    def test_unresolved_gap_prevents_later_acceptance(self):
        self.submit("2026-01")
        s = self.submit("2026-02"); self.decided("2026-02", "ACCEPT", s)
        self.fails("acceptance after unresolved/missing month")

    def test_missing_month_prevents_later_acceptance(self):
        s = self.submit("2026-02"); self.decided("2026-02", "ACCEPT", s)
        self.fails("acceptance after unresolved/missing month")

    def test_duplicate_submissions_blocked(self):
        self.submit("2026-01"); self.submit("2026-01", attempt=2)
        self.fails("duplicate submission")

    def test_double_decision_blocked(self):
        s = self.submit("2026-01")
        self.decided("2026-01", "ACCEPT", s)
        self.decided("2026-01", "ACCEPT", s)
        self.fails("double decision")

    def test_cure_without_rejection_blocked(self):
        self.add("CURE", "2026-01", refs=[
            "pr:alpha-cure-work1", "pr:alpha-cure-work2", "pr:alpha-cure-work3"], depends=None)
        self.fails("cure requires rejected")

    def test_cure_stale_rejection_reference_blocked(self):
        s = self.submit("2026-01"); self.decided("2026-01", "REJECT", s)
        self.add("CURE", "2026-01", refs=[
            f"pr:alpha-stale-cure-work{i}" for i in range(3)], depends=s)
        self.fails("stale cure reference")

    def test_reviewer_stale_submission_reference_blocked(self):
        self.submit("2026-01")
        self.add("ACCEPT", "2026-01", depends=None)
        self.fails("stale decision")

    def test_reviewer_is_not_contributor_even_if_namespace_changes(self):
        s = self.submit("2026-01")
        self.add("ACCEPT", "2026-01", depends=s, actor="reviewer:alpha-demo")
        self.fails("self-review")

    def test_reviewer_is_required_for_decision(self):
        s = self.submit("2026-01")
        self.add("ACCEPT", "2026-01", depends=s, actor="contrib:alpha-demo")
        self.fails("independent reviewer required")

    def test_reused_evidence_across_cure_blocked(self):
        s = self.submit("2026-01")
        self.decided("2026-01", "REJECT", s)
        self.add("CURE", "2026-01", depends=2, refs=self.ledger["events"][0]["evidence_refs"])
        self.fails("evidence reused")

    def test_evidence_cannot_be_an_approval_reference(self):
        self.add("SUBMIT", "2026-01", refs=[
            "board:legal-status1", "pr:valid-work2", "pr:valid-work3"])
        self.fails("invalid evidence category")

    def test_reject_review_cannot_add_unreviewed_evidence(self):
        s = self.submit("2026-01")
        self.add("REJECT", "2026-01", depends=s, refs=["pr:extra-new-work"])
        self.fails("review may not add")

    def test_submission_must_have_three_distinct_items(self):
        self.add("SUBMIT", "2026-01", refs=["pr:only-one-evidence"])
        self.fails("3 distinct")

    def test_mismatched_registry_id_blocked(self):
        self.ledger["registry_ref"] = "doc:other-registry"
        self.fails("registry reference differs")

    def test_unknown_grant_blocked(self):
        self.add("SUBMIT", "2026-01", grant="never", refs=[
            "pr:unknown-one", "pr:unknown-two", "pr:unknown-three"])
        self.fails("unknown grant")

    def test_replayed_event_sequence_blocked(self):
        self.submit("2026-01")
        self.ledger["events"][0]["seq"] = 2
        self.fails("noncontiguous/replayed")

    def test_prev_digest_mismatch_blocked(self):
        s = self.submit("2026-01"); self.decided("2026-01", "ACCEPT", s)
        self.ledger["events"][1]["prev_sha256"] = events.GENESIS
        self.fails("predecessor hash mismatch")

    def test_changed_content_without_rehash_blocked(self):
        self.submit("2026-01")
        self.ledger["events"][0]["month"] = "2026-02"
        self.fails("event hash mismatch")

    def test_external_root_anchor_blocks_rewritten_chain(self):
        self.submit("2026-01")
        prior_root = self.ledger["events"][-1]["sha256"]
        self.ledger["events"][0]["month"] = "2026-02"
        self.ledger["events"][0]["sha256"] = events.digest_event(self.ledger["events"][0])
        self.assertNotEqual(prior_root, self.validated()["chain_root_sha256"])
        with self.assertRaisesRegex(admin.ContractValidationError,
                                    "external pinned root digest mismatch"):
            self.validated(prior_root)

    def test_wrong_external_root_syntax_blocked(self):
        self.submit("2026-01")
        with self.assertRaisesRegex(admin.ContractValidationError, "expected lowercase sha256"):
            self.validated("faked-signature")

    def test_mixing_mutable_period_snapshot_with_events_blocked(self):
        self.registry["grants"][0]["periods"] = json.loads(FIXTURE.read_text())["grants"][0]["periods"]
        self.fails("cannot mix immutable events")

    def test_fake_legal_approval_blocked(self):
        self.registry["stage"] = "EXECUTED"
        self.fails("APPROVED or EXECUTED")

    def test_foundation_ownership_blocked(self):
        self.registry["foundation"]["ownership_bps"] = 400
        self.fails("cannot grant private ownership")

    def test_bounded_events(self):
        self.ledger["events"] = [None] * (events.MAX_EVENTS + 1)
        self.fails("exceeded bound")

    def test_cli_reads_file_but_does_not_authenticate_people(self):
        s = self.submit("2026-01"); self.decided("2026-01", "ACCEPT", s)
        with tempfile.TemporaryDirectory() as d:
            registry, log = Path(d) / "registry.json", Path(d) / "log.json"
            registry.write_text(json.dumps(self.registry), encoding="utf8")
            log.write_text(json.dumps(self.ledger), encoding="utf8")
            out = io.StringIO()
            with redirect_stdout(out):
                result = events.main([str(registry), str(log),
                                      "--expected-root", self.ledger["events"][-1]["sha256"]])
            self.assertEqual(result, 0)
            report = json.loads(out.getvalue())
            self.assertFalse(report["signatures_authenticated"])
            self.assertEqual(report["legal_effect"], "NONE")

    def test_strict_legacy_registry_does_not_vest_past_pending(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf8"))
        alpha = raw["grants"][0]
        alpha["periods"][2]["review"] = "pending"
        alpha["periods"][2]["reviewer_ref"] = None
        alpha["periods"][3]["review"] = "accepted"
        with self.assertRaisesRegex(admin.ContractValidationError, "unresolved pending period"):
            admin.validate_registry(raw)

    def test_deterministic_arithmetic_property_24_cohort_sizes(self):
        for n in range(1, admin.MAX_GRANTS+1):
            base = (25-n)*1000
            units = base*admin.GRANT_BPS // (admin.BPS_DENOM - admin.GRANT_BPS*n)
            self.assertEqual(units, 1000)
            self.assertEqual((units*10000) // (base+n*units), 400)

    def test_randomized_actual_registry_vesting_transitions(self):
        rng = random.Random(20261122)
        for case_id in range(75):
            count = rng.randrange(0, 70)
            registry = deepcopy(self.registry)
            accepted = 0
            rows = []
            for idx in range(count):
                month = f"{2026 + idx // 12:04d}-{idx % 12 + 1:02d}"
                decision = rng.choice(["accepted", "rejected"])
                accepted += decision == "accepted"
                rows.append({
                    "month": month,
                    "review": decision,
                    "evidence_refs": [
                        f"pr:random-case{case_id}-month{idx}-work{j}" for j in range(3)
                    ] if decision == "accepted" else [],
                    "reviewer_ref": "reviewer:independent-qa"
                })
            registry["grants"][0]["periods"] = rows
            report = admin.validate_registry(registry)
            result = report["awards"][0]["vesting"]
            self.assertEqual(result["post_cliff_installments"],
                             min(36, max(0, accepted-3)))
            self.assertEqual(result["cliff_months_accepted"], min(3, accepted))
            self.assertEqual(result["fraction_of_original_grant"],
                             str(Fraction(min(36, max(0, accepted-3)), 36)))

    def test_unhashable_event_kind_rejected_without_crashing(self):
        self.submit("2026-01")
        self.ledger["events"][0]["kind"] = ["ACCEPT"]
        self.fails("unknown event kind")

    def test_registry_symlink_input_is_denied(self):
        with tempfile.TemporaryDirectory() as d:
            real = Path(d) / "safe.json"
            link = Path(d) / "alias.json"
            real.write_text(json.dumps(self.registry), encoding="utf8")
            link.symlink_to(real)
            with self.assertRaisesRegex(admin.ContractValidationError, "symlinked"):
                admin.load_registry(link)


if __name__ == "__main__":
    unittest.main()
