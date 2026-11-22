# Founding Contributor Review Event Protocol (synthetic v1)

**Status: TEST CANDIDATE ONLY.** No legal approvals, ownership, wages, IP royalties, signatures, or authentic personnel records are created by the tool.

## Intent and boundary

The existing contributor_admin.py validates a synthetic 4% non-voting Company grant cap table and mutable monthly snapshots. The new contributor_eventlog.py is a separate review transition verifier. In event mode, the linked synthetic registry must have empty monthly period arrays; do not combine conflicting mutable and event-chain records as if both were authoritative.

This system is **not the AttoLang compiler borrow checker**. Core borrow safety must be enforced by each compiler at typed MIR/source admission, including code inside backend-local core/alloc/std modules. Library state predicates cannot mint a valid loan or bypass owner identity and lifetime checks.

## Trust model

- SHA-256 linked event hashes provide a deterministic change detector, **not a signature, authenticated reviewer identity, trusted append-only database, or legal authorization**.
- A writer with access to all event data can rewrite history and rehash it. Use an externally pinned independent expected root to catch a different chain; if the writer can also overwrite the root, this check offers no protection.
- Contributor and reviewer references are synthetic opaque strings, not verified accounts. The validator catches direct same-ID self review and stale decision references but not collusion or aliasing.
- No check proves work quality or whether three linked PRs were genuinely three substantive contributions. A human must make that determination.
- Passing the CLI means **SYNTHETIC_EVENT_CHAIN_ONLY** and **legal_effect NONE**; no Company shares issued or Foundation compensation authorized.

## Event format and transitions

Every synthetic event has exactly: seq, kind, grant_ref, month, actor_ref, evidence_refs, ref_event_seq, prev_sha256, sha256. seq is contiguous starting at 1. The supported kinds are SUBMIT, ACCEPT, REJECT and CURE. Every event references a known synthetic Company grant and a bounded calendar month.

SUBMIT: From the contributor identified in the registry, at least three distinct candidate evidence references, no prior decision for that month and no stale dependency.

ACCEPT or REJECT: A distinct synthetic reviewer: identifier, no new contribution evidence and a dependency on the active submission. A decision cannot be repeated or applied after acceptance.

CURE: Only after a rejected month, from the original synthetic contributor, with at least three new evidence references and explicit dependency on the latest rejection. Previously submitted evidence cannot be recycled.

A later accepted month is prohibited if an earlier month has no accepted/rejected decision. Rejected periods pause the service-credit clock; accepted months one through three satisfy the cliff without vesting; subsequent accepted months earn at most 36 theoretical Company installments. This model is intentionally more conservative than some employment leave/cure policies. No fractional Company unit is actually granted by this math.

## Digest protocol

For each event, use SHA256 over the UTF-8 concatenation of the domain separator ATTO-DRAFT-REVIEW-CHAIN-V1 plus a newline and canonical JSON of the event excluding its sha256 field. Canonical JSON uses sorted keys, compact separators, ASCII escaping, and no NaN. The initial previous digest is 64 zeros. The --expected-root CLI option checks an independently provided final lowercase hexadecimal digest.

This proves **consistency of supplied bytes with a supplied root, not signer or legal authorization**.

## Manual and automated test command

    python3 -m unittest discover -s tests -p 'test_*.py' -v

For a separately generated *synthetic* event log only:

    python3 scripts/contributor_eventlog.py synthetic_registry.json synthetic_log.json --expected-root YOUR_INDEPENDENT_64_HEX_ROOT

There is no execute, approve, sign, issue-shares, pay-salary or transfer-funds command. Do not commit actual identities, tax numbers, employee records, compensation approvals or signed board records.

## Production prerequisites (NOT IMPLEMENTED)

1. Independent access-controlled record service; least-privilege RBAC/ABAC, verified human identities, two-person approval, real restrictions on reviewer and interested-party conflicts.
2. Durable, authenticated, independently rooted append-only evidence; transactional compare-and-swap revisions; replay resistance, restricted backups, deletion/retention and auditable access.
3. Proof of actual source PRs and substantive contributions, a lawful missed-month cure/leave policy, and a disinterested qualified reviewer.
4. Actual Company capitalization, non-voting class, legal/tax approval, signatures and issuance ledger before 4% equity can vest or be transferred.
5. Separate independent Foundation approvals for salary/project work and bona fide independently licensed IP. A nonprofit Foundation cannot issue founder stock or distribute 4% of donations or Foundation profits.

**No CI run upgrades this candidate to a production administrator, compiler ownership checker, or binding agreement.**
