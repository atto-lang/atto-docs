# AttoLang legal documents (private draft workspace)

This **private** repository stores proposed contracts for legal review. GitHub Markdown files are not signed agreements, equity grants, shareholder registers, open-source licenses, or proof of employment status. Do not publish or replicate these contracts outside explicitly authorized private environments.

## Current contracts

- [Founding Contributor: dual-entity 4% non-voting ownership draft](agreements/founding-contributor-dual-entity-nonvoting-ownership-agreement.md). Based on the founder's [source gist](https://gist.github.com/ORESoftware/d857934cd5aed6e7cf71ca891165131e), but revised from a 5% Company-only proposal to **separate 4% non-voting stakes**, subject to lawful issuance. Preserves three substantial contributions each month, a 3-month cliff, 36 monthly installments and a BYO AI/tokens/tools policy. **The Foundation portion cannot be issued while it is a charitable nonprofit.** The draft intentionally does not claim that 4% Foundation equity exists now.
- [Founding Engineer: forking and naming addendum](agreements/founding-engineer-forking-and-naming-addendum.md). Expressly permits eligible engineers to make **private** proprietary forks subject to the agreement, reserves the Atto/AttoLang names and does not grant voting or ownership rights by virtue of forking.

## Review gates before execution

A licensed lawyer and the authorized representatives must settle the legal identity and jurisdiction of both proposed entities; whether the Foundation can legally issue private equity or needs a different legal structure; the capitalization schedules and actual non-voting share/unit classes; mandatory class and minority-holder rights; enforceable vesting, repurchase and tax provisions; securities compliance; and labor/contractor requirements across relevant jurisdictions. The underlying language and runtime code are **not yet open source**.

**No private equity can be issued by a charitable 501(c)(3) Foundation.** A non-voting nonprofit membership is not equivalent to a 4% economic ownership stake. Do not represent the Foundation portion as issued, earned ownership or legally enforceable without resolving that blocker and executing definitive instruments.

## Automated checks

Run offline using Python standard library:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The GitHub Actions workflow runs the same checks on relevant PRs and main. It uses no secrets, no paid external dependencies, and a SHA-pinned checkout action. Checks protect common drafting invariants (4% rather than 5%, two intended grants, non-voting, Foundation blocker, no hidden revenue share, vesting arithmetic, signatures after schedules, proprietary/private fork terms). Negative mutation tests verify that breaking protections causes failures. **Passing CI is not legal advice or certification.** Human legal review and signatures remain mandatory.
