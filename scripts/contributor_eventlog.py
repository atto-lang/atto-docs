#!/usr/bin/env python3
"""Synthetic event-chain validator for Atto contributor reviews.

A SHA-256 chain detects accidental edits against an independently pinned root.
It does NOT authenticate actors, prevent a writer from rehashing a rewritten
history, grant shares, authorize pay, or prove a legal signature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

if __package__:
    from . import contributor_admin as admin
else:
    import contributor_admin as admin

DOMAIN = b"ATTO-DRAFT-REVIEW-CHAIN-V1\n"
GENESIS = "0" * 64
MAX_EVENTS = 4096
MAX_BYTES = 1_000_000
EVENT_KEYS = {"seq", "kind", "grant_ref", "month", "actor_ref",
              "evidence_refs", "ref_event_seq", "prev_sha256", "sha256"}
EVENT_KINDS = {"SUBMIT", "ACCEPT", "REJECT", "CURE"}


def digest_event(event: dict) -> str:
    """Domain-separated canonical digest; no assertion of cryptographic signer identity."""
    data = {k: v for k, v in event.items() if k != "sha256"}
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(DOMAIN + encoded).hexdigest()


def check_digest(value: object, where: str) -> str:
    admin.check(type(value) is str and len(value) == 64
                and all(c in "0123456789abcdef" for c in value),
                where + ": expected lowercase sha256")
    return value


def validate_events(log: object, registry: object, expected_root: str | None) -> dict:
    base = admin.validate_registry(registry)
    data = admin.require_keys(log, {"schema_version", "mode", "log_ref",
                                    "registry_ref", "events"}, "log")
    admin.check(admin.number(data["schema_version"], "log.schema_version") == 1,
                "log version must be 1")
    admin.check(data["mode"] == "simulation", "log is simulation only")
    admin.opaque(data["log_ref"], "log.log_ref")
    admin.check(data["log_ref"].startswith("ledger:"), "log_ref must use ledger:")
    admin.check(data["registry_ref"] == base["registry_ref"],
                "log registry reference differs from checked synthetic registry")
    events = data["events"]
    admin.check(type(events) is list and len(events) <= MAX_EVENTS,
                "events: exceeded bound or wrong list")
    if expected_root is not None:
        check_digest(expected_root, "expected_root")
    grants = {g["grant_ref"]: g for g in registry["grants"]}
    for grant in registry["grants"]:
        admin.check(grant["periods"] == [],
                    "event-chain mode cannot mix immutable events with mutable period snapshots")
    state: dict[tuple[str, str], dict] = {}
    evidence_seen: set[str] = set()
    previous = GENESIS
    max_month: dict[str, int] = {}
    for i, event in enumerate(events):
        tag = f"events[{i}]"
        admin.require_keys(event, EVENT_KEYS, tag)
        admin.check(admin.number(event["seq"], tag + ".seq", low=1) == i+1,
                    tag + ": noncontiguous/replayed sequence")
        admin.check(event["kind"] in EVENT_KINDS, tag + ": unknown event kind")
        grant_ref = admin.opaque(event["grant_ref"], tag + ".grant_ref")
        admin.check(grant_ref in grants, tag + ": unknown grant")
        grant = grants[grant_ref]
        index = admin.month_index(event["month"], tag + ".month")
        start = admin.month_index(grant["start_month"], tag + ".start")
        admin.check(start <= index < start + admin.MAX_PERIODS,
                    tag + ": event outside bounded grant vesting calendar")
        month = event["month"]
        key = grant_ref, month
        actor = admin.opaque(event["actor_ref"], tag + ".actor_ref")
        refs = event["evidence_refs"]
        admin.check(type(refs) is list and len(refs) <= 20,
                    tag + ": invalid bounded evidence")
        for ref in refs:
            admin.opaque(ref, tag + ".evidence_refs")
            admin.check(ref.startswith(("pr:", "issue:", "commit:", "ci:", "doc:")),
                        tag + ": invalid evidence category")
        admin.check(len(set(refs)) == len(refs), tag + ": duplicate evidence")
        prior = event["ref_event_seq"]
        admin.check(prior is None or (type(prior) is int and 1 <= prior < event["seq"]),
                    tag + ": invalid event dependency sequence")
        admin.check(check_digest(event["prev_sha256"], tag + ".prev") == previous,
                    tag + ": predecessor hash mismatch")
        reported_digest = check_digest(event["sha256"], tag + ".sha256")
        admin.check(reported_digest == digest_event(event),
                    tag + ": event hash mismatch")
        previous = reported_digest
        prior_state = state.get(key, {"status": "ABSENT", "last_seq": None})
        status = prior_state["status"]
        if event["kind"] == "SUBMIT":
            admin.check(status == "ABSENT", tag + ": duplicate submission or illegal transition")
            admin.check(actor == grant["contributor_ref"],
                        tag + ": only matching contributor may submit in synthetic model")
            admin.check(prior is None, tag + ": first submission cannot depend on another event")
            admin.check(len(refs) >= 3, tag + ": submission needs 3 distinct contribution refs")
            state[key] = {"status": "PENDING", "last_seq": event["seq"]}
        elif event["kind"] == "CURE":
            admin.check(status == "REJECTED", tag + ": cure requires rejected review")
            admin.check(prior == prior_state["last_seq"], tag + ": stale cure reference")
            admin.check(actor == grant["contributor_ref"],
                        tag + ": only same contributor can resubmit cure")
            admin.check(len(refs) >= 3, tag + ": cure needs 3 distinct contribution refs")
            state[key] = {"status": "PENDING", "last_seq": event["seq"]}
        else:
            admin.check(status == "PENDING", tag + ": double decision or no pending submission")
            admin.check(prior == prior_state["last_seq"], tag + ": stale decision/replay")
            admin.check(actor.startswith("reviewer:"), tag + ": independent reviewer required")
            admin.check(actor.split(":", 1)[1] != grant["contributor_ref"].split(":", 1)[1],
                        tag + ": contributor self-review")
            admin.check(refs == [], tag + ": review may not add unreviewed work evidence")
            state[key] = {"status": "ACCEPTED" if event["kind"] == "ACCEPT" else "REJECTED",
                          "last_seq": event["seq"]}
        for ref in refs:
            admin.check(ref not in evidence_seen, tag + ": evidence reused across attempts")
            evidence_seen.add(ref)
        max_month[grant_ref] = max(max_month.get(grant_ref, start-1), index)
    # A later accepted month cannot skip an earlier unreviewed or absent period:
    # a rejected period may be skipped for service-vesting purposes, but not silently
    # converted into accepted work; cure must be explicitly committed.
    rows = []
    for grant_ref, grant in grants.items():
        start = admin.month_index(grant["start_month"], "grant.start_month")
        highest = max_month.get(grant_ref, start-1)
        accepted = rejected = pending = 0
        for idx in range(start, highest+1):
            month = f"{idx // 12:04d}-{idx % 12 + 1:02d}"
            outcome = state.get((grant_ref, month), {"status": "ABSENT"})["status"]
            if outcome == "ACCEPTED":
                admin.check(pending == 0,
                            f"{grant_ref}: acceptance after unresolved/missing month")
                accepted += 1
            elif outcome == "REJECTED":
                rejected += 1
            else:
                pending += 1
        installments = min(36, max(0, accepted-3))
        rows.append({"grant_ref": grant_ref,
                     "accepted_months": accepted,
                     "rejected_months": rejected,
                     "unresolved_or_missing_months": pending,
                     "cliff_satisfied": accepted >= 3,
                     "post_cliff_installments": installments,
                     "not_a_legal_vesting_certification": True})
    if expected_root is not None:
        admin.check(previous == expected_root, "external pinned root digest mismatch")
    return {"machine_validation": "SYNTHETIC_EVENT_CHAIN_ONLY",
            "legal_effect": "NONE", "grant_or_salary_authorized": False,
            "signatures_authenticated": False,
            "external_root_was_supplied": expected_root is not None,
            "event_count": len(events), "chain_root_sha256": previous,
            "awards": rows,
            "warning": "Unpinned hashes can be recomputed by a writer; external root proves only byte consistency, never reviewer identity or legal approval."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit synthetic event chain, without legal effect")
    parser.add_argument("registry", type=Path)
    parser.add_argument("eventlog", type=Path)
    parser.add_argument("--expected-root", help="independently pinned lowercase SHA-256 root")
    args = parser.parse_args(argv)
    try:
        admin.check(args.eventlog.is_file() and not args.eventlog.is_symlink()
                    and args.eventlog.stat().st_size <= MAX_BYTES,
                    "log missing, symlinked or exceeds size cap")
        registry = admin.load_registry(args.registry)
        log = admin.load_registry(args.eventlog)
        report = validate_events(log, registry, args.expected_root)
    except (admin.ContractValidationError, UnicodeError, OSError, RecursionError) as exc:
        print(json.dumps({"machine_validation": "REJECTED", "legal_effect": "NONE",
                          "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
