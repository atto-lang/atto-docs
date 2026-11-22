# AttoLang legal documents — private draft workspace

> **Private, unexecuted legal drafts.** Files in GitHub are **not** signed contracts, granted equity, a public open-source license, or authorization to take Foundation funds. AttoLang source remains proprietary unless a rights holder later explicitly releases it.

## Documents

- **[Founding Contributor Company Equity & Foundation Compensation Framework](agreements/founding-contributor-dual-entity-nonvoting-ownership-agreement.md)** — proposed **4.00% non-voting equity** in **AttoPL Co / Atto Co only**, with a 3-month cliff and 36 monthly installments, three substantive contributions per month, and BYO development tools. The legacy file path contains "dual-entity-nonvoting-ownership" for link compatibility; the **document itself no longer proposes Foundation shares**.
- **[Foundation Founding Contributor Services, Compensation & IP Royalty Agreement](agreements/foundation-founding-contributor-compensation-and-ip-royalties.md)** — a **separate agreement** for Atto Foundation (intended charitable 501(c)(3)). It grants a proposal/review process, not a guaranteed job. Reasonable salary, project fees and carefully approved bona fide royalties can be legally owed **only through authorized, signed paid-service or actual IP-license instruments** (or mandatory employment law). No automatic 4% Foundation ownership, residuals, revenue share, dividends or voting powers.
- **[Founding Engineer Forking & Naming Addendum](agreements/founding-engineer-forking-and-naming-addendum.md)** — private proprietary forks by eligible engineers subject to this agreement; independent fork names may not use "Atto"/"AttoLang"; no implied equity or governance rights.

The initial contributor agreement was based on the founder's [source gist](https://gist.github.com/ORESoftware/d857934cd5aed6e7cf71ca891165131e), which contained a 5% Company equity plus 5% net-receipts proposal. Those **old 5% economics are not the current drafts**.

## Economic and governance distinctions

| Entity | Proposed contributor consideration | Governance |
|---|---|---|
| **AttoPL Co / Atto Co** | 4% non-voting Company equity, issued only in definitive instruments; subject to vesting/dilution | No ordinary votes or board rights, subject to mandatory law |
| **Atto Foundation (501(c)(3) planned)** | Negotiated reasonable wages/service fees for real work, or a specific fair-value IP license | No private equity, no Founder votes or trustee appointment powers; independent board controls pay |

**Do not promise 4% of Foundation income, net proceeds, charitable grants or donations.** A charitable nonprofit cannot issue ordinary private economic equity or distribute net earnings to insiders. Merely renaming shares as "royalties", "residuals", "vested Foundation compensation" or "founder participation" does not avoid the private-inurement and excess-benefit rules.

## Legal and signing gates

Before signing, U.S. nonprofit/tax counsel and relevant local/employment counsel should resolve the actual legal entities, location and charitable classification; Company non-voting share class and 4% fully diluted cap table; statutory minority shareholder rights; wage/classification rules; reasonable nonprofit compensation; independent board approval, comparability and minutes; contributor IP chain of title; potential related-party and inter-company licensing; deferred compensation tax rules; and any Form 990/Schedule L reporting. **No Foundation salary/royalty is guaranteed or earned just from founding status.** An authorized, funded work order or written employment agreement creates an enforceable payment obligation when compensation is lawfully earned.

Reference guidance:
- [IRS: charitable private inurement and private benefit](https://www.irs.gov/charities-non-profits/charitable-organizations/inurement-private-benefit-charitable-organizations)
- [IRS: reasonable compensation](https://www.irs.gov/charities-non-profits/charitable-organizations/intermediate-sanctions-compensation)
- [IRS: advance independent authorization and comparable data](https://www.irs.gov/charities-non-profits/charitable-organizations/rebuttable-presumption-intermediate-sanctions)
- [IRS: intellectual-property arrangements in Form 1023](https://www.irs.gov/charities-non-profits/form-1023-information-about-ownership-of-intellectual-property)

## Offline automated checks

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The GitHub Actions workflow runs the same Python standard-library checks (no secrets, no external packages; SHA-pinned checkout). Checks enforce the proposed economics, absence of a default Foundation residual, disinterested review, IP title requirements, private fork naming, original 39-month Company vesting, signature schedules and refusal to claim legal effectiveness. Negative mutation tests make sure common contract regressions fail. **Passing automated checks is not a legal approval, execution, or equity issuance.**

When source GitHub Actions cannot start, run the exact Git tree in a preapproved **private** alternate-org mirror with **blob/tree SHA verification**, a temporary unmerged carrier branch, and no cross-organization tokens. Respect confidentiality/access restrictions and clean up the temporary branch afterward.
