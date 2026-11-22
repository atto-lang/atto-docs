#!/usr/bin/env python3
"""Offline, read-only Atto contributor planning validator.

This is NOT a legal approval, share issuance, signature verification, or compensation
authorization. All input fixtures are synthetic. Standard library only.
"""

from __future__ import annotations

import argparse
from datetime import date
from fractions import Fraction
import json
from pathlib import Path
import re
import sys

BPS_DENOM = 10_000
GRANT_BPS = 400
MAX_GRANTS = 24
MAX_UNITS = 10**15
MAX_PERIODS = 240
MAX_BYTES = 1_000_000
STAGES = ("DRAFT", "READY_FOR_COUNSEL", "APPROVED", "EXECUTED")
REF_PATTERN = re.compile(r"^(?:entity|class|grant|contrib|reviewer|pr|issue|commit|ci|doc|cap|counsel|board|signature|ledger|ip):[a-z0-9][a-z0-9._/-]{2,90}$")
MONTH_PATTERN = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")


class ContractValidationError(ValueError):
    pass


def check(condition: bool, reason: str) -> None:
    if not condition:
        raise ContractValidationError(reason)


def require_keys(obj: object, keys: set[str], path: str) -> dict:
    check(type(obj) is dict, f"{path}: expected object")
    absent = keys - obj.keys()
    extra = obj.keys() - keys
    check(not absent, f"{path}: missing keys {','.join(sorted(absent))}")
    check(not extra, f"{path}: unrecognized keys {','.join(sorted(extra))}")
    return obj


def number(value: object, path: str, *, low: int = 0, high: int = MAX_UNITS) -> int:
    check(type(value) is int and low <= value <= high, f"{path}: invalid bounded integer")
    return value


def opaque(value: object, path: str) -> str:
    check(type(value) is str and bool(REF_PATTERN.fullmatch(value)),
          f"{path}: must be a short opaque namespaced reference, not a name, email or URL")
    return value


def month_index(value: object, path: str) -> int:
    check(type(value) is str and bool(MONTH_PATTERN.fullmatch(value)),
          f"{path}: invalid YYYY-MM month")
    year, month = map(int, value.split("-"))
    check(2000 <= year <= 2200, f"{path}: year outside 2000..2200")
    date(year, month, 1)
    return year * 12 + month - 1


def format_percent(bps: Fraction) -> str:
    # Fraction is stored in basis points. Exact decimal to six fractional digits
    # without float rounding, with a bounded output string.
    percent = bps / 100
    scaled = percent * 10**6
    integer = scaled.numerator // scaled.denominator
    return f"{integer // 10**6}.{integer % 10**6:06d}%"


def _periods(grant: dict, path: str, used_evidence: set[str]) -> dict:
    start = month_index(grant["start_month"], f"{path}.start_month")
    rows = grant["periods"]
    check(type(rows) is list and len(rows) <= MAX_PERIODS, f"{path}.periods: invalid list")
    cliff_accepted = 0
    installments = 0
    pauses = 0
    for i, raw in enumerate(rows):
        p = f"{path}.periods[{i}]"
        row = require_keys(raw, {"month", "review", "evidence_refs", "reviewer_ref"}, p)
        check(month_index(row["month"], p + ".month") == start + i,
              f"{p}.month: periods must be contiguous from start_month")
        decision = row["review"]
        check(decision in ("accepted", "rejected", "pending"), f"{p}.review: invalid state")
        refs = row["evidence_refs"]
        check(type(refs) is list and len(refs) <= 20, f"{p}.evidence_refs: invalid list")
        refs = [opaque(ref, p + ".evidence_refs") for ref in refs]
        check(all(ref.startswith(("pr:", "issue:", "commit:", "ci:", "doc:")) for ref in refs),
              f"{p}: evidence must refer to work/review artifacts, not payout or legal status")
        check(len(set(refs)) == len(refs), f"{p}: duplicate evidence within month")
        for ref in refs:
            check(ref not in used_evidence, f"{p}: evidence reused in another grant or month")
            used_evidence.add(ref)
        reviewer = row["reviewer_ref"]
        if decision in ("accepted", "rejected"):
            reviewer = opaque(reviewer, p + ".reviewer_ref")
            check(reviewer.startswith("reviewer:"), f"{p}: reviewer reference must use reviewer: prefix")
            check(reviewer.split(":", 1)[1] != grant["contributor_ref"].split(":", 1)[1],
                  f"{p}: contributor cannot self-review under different namespace")
        else:
            check(reviewer is None, f"{p}: pending review cannot claim a reviewer decision")
        if decision == "accepted":
            check(len(refs) >= 3, f"{p}: accepted month needs >=3 distinct substantial evidence refs")
            if cliff_accepted < 3:
                cliff_accepted += 1
            elif installments < 36:
                installments += 1
        elif decision == "rejected":
            pauses += 1
        # Pending periods are unvested, but not recorded as a rejection.
    return {
        "recorded_months": len(rows),
        "cliff_months_accepted": cliff_accepted,
        "cliff_satisfied": cliff_accepted == 3,
        "post_cliff_installments": installments,
        "fraction_of_original_grant": str(Fraction(installments, 36)),
        "rejected_months": pauses,
        "vesting_only": True,
    }


def validate_registry(doc: object) -> dict:
    data = require_keys(doc, {
        "schema_version", "mode", "stage", "registry_ref", "company",
        "foundation", "grants", "counsel_packet_refs", "legal_claims_verified"
    }, "registry")
    check(number(data["schema_version"], "schema_version") == 1, "schema_version: must be 1")
    check(data["mode"] == "simulation", "mode: checked-in data must be simulation only")
    stage = data["stage"]
    check(type(stage) is str and stage in STAGES, "stage: invalid lifecycle state")
    check(stage in ("DRAFT", "READY_FOR_COUNSEL"),
          "stage: APPROVED or EXECUTED must be validated outside this repository by authorized humans; CI cannot certify")
    check(data["legal_claims_verified"] is False,
          "legal_claims_verified must be false; documents and signatures are not authenticated by this tool")
    registry_ref = opaque(data["registry_ref"], "registry_ref")
    company = require_keys(data["company"], {
        "entity_ref", "non_voting_class_ref", "base_fully_diluted_units", "grant_strategy"
    }, "company")
    opaque(company["entity_ref"], "company.entity_ref")
    check(company["entity_ref"].startswith("entity:"), "company: require opaque entity: reference")
    opaque(company["non_voting_class_ref"], "company.non_voting_class_ref")
    check(company["non_voting_class_ref"].startswith("class:"), "company: require class: reference")
    base = number(company["base_fully_diluted_units"],
                  "company.base_fully_diluted_units", low=1)
    strategy = company["grant_strategy"]
    check(type(strategy) is str and strategy in ("simultaneous", "sequential"),
          "company.grant_strategy: must be simultaneous or sequential")
    foundation = require_keys(data["foundation"], {
        "entity_ref", "ownership_bps", "nonprofit_status",
        "compensation", "royalties", "voting_rights"
    }, "foundation")
    opaque(foundation["entity_ref"], "foundation.entity_ref")
    check(foundation["entity_ref"].startswith("entity:"), "foundation: require opaque entity: reference")
    check(number(foundation["ownership_bps"], "foundation.ownership_bps") == 0,
          "foundation: charitable nonprofit cannot grant private ownership")
    check(foundation["nonprofit_status"] == "intended_501c3_unverified",
          "foundation.nonprofit_status: may not assert tax exemption without external evidence")
    check(foundation["compensation"] == "separate_approved_signed_services_only",
          "foundation: salary requires an independently approved, signed engagement")
    check(foundation["royalties"] == "specific_independently_valued_ip_license_only",
          "foundation: no automatic royalty or revenue residual")
    check(foundation["voting_rights"] is False,
          "foundation: founding status conveys no ordinary voting or trustee rights")
    gate_keys = {"entity_verification", "cap_table_draft", "nonvoting_class_draft",
                 "outside_counsel_packet", "authorized_signatory_plan"}
    gates = require_keys(data["counsel_packet_refs"], gate_keys, "counsel_packet_refs")
    gate_prefixes = {"entity_verification": "entity:", "cap_table_draft": "cap:",
                     "nonvoting_class_draft": "class:", "outside_counsel_packet": "counsel:",
                     "authorized_signatory_plan": "doc:"}
    for key in sorted(gate_keys):
        value = gates[key]
        if stage == "READY_FOR_COUNSEL":
            opaque(value, f"counsel_packet_refs.{key}")
            check(value.startswith(gate_prefixes[key]),
                  f"counsel_packet_refs.{key}: incorrect evidence category")
        elif value is not None:
            opaque(value, f"counsel_packet_refs.{key}")
            check(value.startswith(gate_prefixes[key]),
                  f"counsel_packet_refs.{key}: incorrect evidence category")
    grants = data["grants"]
    check(type(grants) is list and 1 <= len(grants) <= MAX_GRANTS,
          f"grants: require 1..{MAX_GRANTS} non-voting Company awards")
    seen_grants: set[str] = set()
    seen_contributors: set[str] = set()
    used_evidence: set[str] = set()
    validated: list[tuple[dict, dict]] = []
    for i, raw in enumerate(grants):
        path = f"grants[{i}]"
        grant = require_keys(raw, {
            "grant_ref", "contributor_ref", "target_bps",
            "non_voting", "proposed_units", "start_month", "periods"
        }, path)
        grant_ref = opaque(grant["grant_ref"], path + ".grant_ref")
        contributor_ref = opaque(grant["contributor_ref"], path + ".contributor_ref")
        check(grant_ref.startswith("grant:"), path + ": grant_ref must have grant: prefix")
        check(contributor_ref.startswith("contrib:"),
              path + ": contributor_ref must have contrib: prefix")
        check(grant_ref not in seen_grants, path + ": repeated grant identifier")
        check(contributor_ref not in seen_contributors,
              path + ": duplicate contributor; legal approval required for additional awards")
        seen_grants.add(grant_ref)
        seen_contributors.add(contributor_ref)
        check(number(grant["target_bps"], path + ".target_bps") == GRANT_BPS,
              path + ": award must be 400 basis points (4%) at own grant date")
        check(grant["non_voting"] is True, path + ": ordinary voting rights prohibited")
        number(grant["proposed_units"], path + ".proposed_units", low=1)
        timeline = _periods(grant, path, used_evidence)
        validated.append((grant, timeline))
    if strategy == "simultaneous":
        denom = BPS_DENOM - GRANT_BPS * len(grants)
        check(denom > 0, "simultaneous: allocated grants exhaust fully diluted capitalization")
        exact_units = Fraction(base * GRANT_BPS, denom)
        check(exact_units.denominator == 1,
              "simultaneous: exact 4% requires integral units; revise base units or obtain legal rounding approval")
        planned = int(exact_units)
        for i, (grant, _) in enumerate(validated):
            check(grant["proposed_units"] == planned,
                  f"grants[{i}].proposed_units: does not produce 4% of post-issuance capitalization")
        ending_units = base + planned * len(grants)
        units = [planned] * len(grants)
        at_grant_denominators = [ending_units] * len(grants)
    else:
        current = base
        units = []
        at_grant_denominators = []
        for i, (grant, _) in enumerate(validated):
            exact = Fraction(current * GRANT_BPS, BPS_DENOM - GRANT_BPS)
            check(exact.denominator == 1,
                  f"grants[{i}]: exact 4% requires integral new units (no silent rounding)")
            planned = int(exact)
            check(planned == grant["proposed_units"],
                  f"grants[{i}].proposed_units: does not produce 4% at issuance")
            current += planned
            check(current <= MAX_UNITS, "company: unit count exceeds bound")
            units.append(planned)
            at_grant_denominators.append(current)
        ending_units = current
    check(ending_units <= MAX_UNITS, "company: unit count exceeds bound")
    rows = []
    for i, ((grant, timeline), grant_units) in enumerate(zip(validated, units)):
        at_issuance_bps = Fraction(grant_units * BPS_DENOM, at_grant_denominators[i])
        current_bps = Fraction(grant_units * BPS_DENOM, ending_units)
        check(at_issuance_bps == GRANT_BPS, "internal math error: not exactly 4% at issuance")
        vested_units = Fraction(grant_units * timeline["post_cliff_installments"], 36)
        rows.append({
            "grant_ref": grant["grant_ref"],
            "contributor_ref": grant["contributor_ref"],
            "proposed_units": grant_units,
            "at_grant_percent": format_percent(at_issuance_bps),
            "post_all_grants_percent": format_percent(current_bps),
            "vested_units_fractional_theoretical": str(vested_units),
            "unit_rounding_requires_definitive_instrument": True,
            "vesting": timeline,
        })
    return {
        "registry_ref": registry_ref,
        "machine_validation": "SCHEMA_AND_ARITHMETIC_ONLY",
        "source_stage_claim": stage,
        "legal_effect": "NONE",
        "human_approval_and_signatures_authenticated": False,
        "shares_issued": False,
        "foundation_ownership_bps": 0,
        "foundation_salary_or_royalty_authorized": False,
        "company_strategy": strategy,
        "base_fully_diluted_units": base,
        "planned_post_grants_fully_diluted_units": ending_units,
        "total_grants": len(grants),
        "awards": rows,
        "warning": "Synthetic planning only. 4% is per Company grant at issuance, not perpetual after dilution. APPROVED/EXECUTED only in restricted, independently verified legal records.",
    }


def load_registry(path: Path) -> object:
    check(path.is_file(), "registry file missing")
    check(path.stat().st_size <= MAX_BYTES, "registry exceeds size limit")
    raw = path.read_text(encoding="utf-8")
    def invalid_constant(_: str):
        raise ContractValidationError("NaN/infinite values are prohibited")
    def invalid_float(_: str):
        raise ContractValidationError("floating point JSON values are prohibited; use integers")
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ContractValidationError("duplicate JSON object key is prohibited")
            result[key] = value
        return result
    try:
        return json.loads(raw, parse_constant=invalid_constant, parse_float=invalid_float,
                          object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ContractValidationError(f"invalid JSON syntax at line {exc.lineno}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline, read-only legal-draft grant planning")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="validate synthetic grant registry and render math")
    audit.add_argument("registry", type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate_registry(load_registry(args.registry))
    except (ContractValidationError, OSError, UnicodeError) as exc:
        print(json.dumps({"machine_validation": "REJECTED", "legal_effect": "NONE",
                          "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
