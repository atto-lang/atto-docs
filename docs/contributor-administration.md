# Founding Contributor Administration and Fail-Closed Execution Gates

**Status:** Proposed internal operating procedure and deterministic planning tool; **not adopted governance, executed contracts, real grants, counsel verification or evidence of IRS recognition**.

This document implements the [Company founding-contributor agreement](../agreements/founding-contributor-dual-entity-nonvoting-ownership-agreement.md), the [Foundation compensation agreement](../agreements/foundation-founding-contributor-compensation-and-ip-royalties.md), and the [signing checklist](../templates/legal-review-execution-checklist.md) without inventing legal facts.

## 1. Economic boundaries

**AttoPL Co / Atto Co:** A proposed **4.00% non-voting interest per authorized commercial grant**, measured against the **fully diluted Company capitalization at that grant's actual issuance**, subject to the three-month qualifying cliff, 36 monthly installments and lawful dilution. This is a **grant target**, not a guaranteed permanent percentage.

**Atto Foundation:** **Zero private ownership, zero shareholder distribution, zero ordinary voting rights from founding status**. A charitable 501(c)(3) Foundation may pay reasonable compensation for actual approved services, or royalties under a bona fide, independently valued license for **specifically identified IP genuinely owned by the licensor**. Compensation requires a separately signed contract, independent disinterested approval, and applicable labor/tax compliance. There is **no automatic 4% of Foundation receipts, donations, grants, earnings or net assets**.

**Do not count a reviewer’s approval of a GitHub PR as Foundation compensation authorization, Company share issuance, counsel review or executed signatures.**

## 2. Safety and record boundaries

The committed JSON examples under [fixtures/](../fixtures/multi_grant_simulation.json) and [fixtures/](../fixtures/sequential_dilution_simulation.json) are explicitly **synthetic**. They contain only opaque `contrib:`, `grant:`, `reviewer:`, `pr:`, `issue:` and similar references. Do **not** replace them with real identities or production evidence. The repository contains no real legal approval records.

Maintain actual signed grants, individual names, addresses, emails, tax IDs, payroll data, cap tables, authentic corporate minutes, founder disclosures, IP title exhibits and identifying contribution evidence in **separately access-controlled legal record storage**. Never put them in a broadly accessible GitHub repo or public CI artifacts. See the .gitignore protection, but recognize .gitignore **does not prevent deliberate git adds, GitHub API uploads, screenshots, branch leaks or access by existing collaborators**.

Access to real records should follow least privilege, encryption at rest, audit trails, retention/destruction policy, and a required dual-control authorized approval for equity issuance or nonprofit pay. Real signatory identity and authorization must be independently verified, not inferred from a string such as `board:approval`.

## 3. Machine-readable schema and CLI

- [Registry schema](../schemas/contributor-registry.schema.json) describes the strict synthetic record shape.
- [Offline Python validator](../scripts/contributor_admin.py) uses only the Python 3 standard library, rejects unknown keys, duplicate JSON keys, arbitrary real-name/email strings, floating-point grant units, reused evidence references and invented statuses.
- All accepted source records have `mode = "simulation"` and `legal_claims_verified = false`. For version-controlled records, `APPROVED` and `EXECUTED` **always fail**, regardless of user-supplied evidence references. The validator cannot verify signatures or enact legal rights.

Run:

```sh
python3 scripts/contributor_admin.py audit fixtures/multi_grant_simulation.json
python3 scripts/contributor_admin.py audit fixtures/sequential_dilution_simulation.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The CLI prints a deterministic JSON planning report. It deliberately reports `machine_validation = "SCHEMA_AND_ARITHMETIC_ONLY"`, `legal_effect = "NONE"`, `shares_issued = false` and `human_approval_and_signatures_authenticated = false`. A zero exit code **means mathematical/schema validation only**, never legally executed or approved.

The schema is a structural contract, not a substitute for the stricter standard-library CLI application logic. CI validates both example registries and runs negative tests against the same logic.

## 4. Grant cohort sizing and dilution

**Each 4% applies to its own legal grant**, not the combined cohort as a single 4% pool. No system may represent 4% of an unspecified cap table as an actual ownership interest.

Let **B** be fully diluted Company units before the proposed new grants; **n** be the count of 4%-each grants; **G** be each newly issued grant unit count; and **D** be fully diluted units after all grants. Assume the cap table, option pool, convertible securities and non-voting class are already consistently counted in B. Exact simultaneous issuing requires:

```text
D = B + n * G
G / D = 4 / 100
G = B / (25 - n), with 1 <= n <= 24
```

For a **synthetic simultaneous** cohort with `B=22,000`, `n=3`, `G=1,000`, the total becomes `D=25,000`, and **each** grant is exactly 4% at that grant-date capitalization. The original holdings are 88%; the Company has not actually approved or issued any of these hypothetical shares.

For **sequential** grants, each new grant is 4% **at its own issuance**, but earlier grants are diluted. With hypothetical `B=57,600`: first grant `G1=2,400` makes `D1=60,000` and 4%; second `G2=2,500` makes `D2=62,500`, the second is 4% and **the first has become 3.84%**. Do not silently claim both still own 4% of the resulting cap table.

The CLI uses integer unit counts and exact `fractions.Fraction` arithmetic; it **rejects nonintegral exact issuance counts** instead of silently rounding. Real legal rounding, unit denomination, transfer vs issue, vesting and dilution must be resolved by Company counsel in the [grant instrument](../templates/company-4pct-nonvoting-equity-grant.md). No perpetual anti-dilution promise exists.

**Important scaling gate:** With positive pre-existing equity, simultaneously giving 25 or more people 4% each cannot leave any residual stake for the pre-existing capitalization. The tool rejects cohorts larger than 24, but **capacity to grant 4% each still depends on actual authorized share counts, investor rights, employee pool, agreements and cap table**. A Company may decide to use a limited contributor pool; no such policy is imposed by these examples.

## 5. Evidence, vesting and audit trail

A monthly row is `accepted`, `rejected` or `pending`. Every recorded month must be continuous from that contributor's `start_month`. **Accepted** requires at least three distinct work-evidence references (e.g., a substantial PR, verified tests and an approved design deliverable) plus a reviewer reference distinct from the contributor. Evidence cannot be reused in a different month or another contributor grant in the same synthetic registry. A human still must determine whether a contribution is genuinely substantial and appropriately credited; a hash or PR ID alone cannot prove quality.

The first **three accepted qualifying months** satisfy the initial cliff but vest **nothing**. Each subsequent accepted month vests **1/36 of the original Company award**, capped at 36. Rejected and pending months do not vest. They can extend the date of full vesting, subject to the actual agreement's notice/cure provisions. At uninterrupted acceptance, first installment is month 4 and last month 39. A rejected month is recorded, not secretly skipped. This tool records **theoretical fractional units** and never asserts that those fractions have actually been transferred or legally rounded.

A self-assigned review is invalid, including when the same opaque ID appears in `contrib:` and `reviewer:` namespaces. Reject duplicate evidence, reused award IDs and duplicated contributor awards rather than declaring a passing 4% cohort. If a genuine co-authorship exception is needed, counsel and authorized maintainer must approve a revised evidence-allocation rule outside this strict initial system.

## 6. Execution-readiness lifecycle (no fake approvals)

| State | Administrative meaning | What automated CI may claim |
|---|---|---|
| **DRAFT** | Proposed fictional plan; evidence/cap table may be incomplete | Valid arithmetic and schema only |
| **READY_FOR_COUNSEL** | A packet lists entity, draft cap table, non-voting class, outside-counsel review packet and authorized-signatory plan | Presence/type of references only; **not** their authenticity, completeness, or legal sufficiency |
| **APPROVED** | Actual duly authorized board/company and counsel approvals documented in restricted legal records | **Always rejected by this repository CLI**; requires external authenticated approval and proper organizational authority |
| **EXECUTED** | Actual signed definitive instruments, issued Company shares and ledger entries, or signed Foundation paid-engagement/license contracts | **Always rejected by this repository CLI**; requires external verification and lawful corporate/contractual action |

In particular, passing GitHub Actions **cannot move any record to APPROVED or EXECUTED**. The words must not be interpreted as GitHub labels, PR approvals or a casual checkbox. A future production administrator would need an appropriately authenticated signing/approval system with immutable audit evidence, proper separation of duties, revocation and reliable transfer ledger integration.

## 6A. Hardened synthetic review transitions

The [synthetic contributor event-chain protocol](contributor-review-event-protocol.md) and [bounded event-chain validator](../scripts/contributor_eventlog.py) add explicit submission, independent review, rejection and cure state transitions. A source-only SHA-256 event chain may be checked against an **independently pinned** root; that is **not** a trusted signature or immutable production store. Legacy monthly snapshots and event-chain decisions are mutually exclusive. The tool rejects accepted months after unresolved earlier decisions, so pending review cannot manufacture vesting in later periods. Full identity, contract, cap-table and approval authentication remains outside this repo.

## 7. Review/approval evidence checks (for authorized humans)

**Company equity readiness:** exact entity legal name, legal jurisdiction, actual non-voting share class authorization, signed fully diluted cap table with explicit grants and dilution, management/board resolution, securities and tax review, 83(b) applicability where appropriate, classified worker obligations, vesting/repurchase and issued share ledger. Attach signed agreement and restricted record IDs outside GitHub.

**Foundation compensation readiness:** actual nonprofit formation and any IRS recognition verified, appropriate charity governance, [adopted conflicts policy](../policies/foundation-conflicts-and-compensation-policy.md), disinterested quorum/recusal and comparable pay or IP valuation, donor and program budget restrictions, actual IP chain of title (if royalties), signed [work order](../templates/foundation-paid-services-work-order.md) or [specific IP license](../templates/foundation-specific-ip-license.md). The Foundation **never issues private equity or a passive founder residual**.

**Separation and access:** AttoPL Co equity records and Foundation compensation records belong to distinct legal parties and restricted access groups. Do not copy grant data into Foundation grant/donation distributions. No ordinary voting rights arise from the proposed Company class or Foundation founding status, except mandatory statutory rights.

The final go/no-go decision remains with competent licensed nonprofit, securities, tax and employment counsel and duly authorized parties. **This tooling does not certify legal enforceability.**
