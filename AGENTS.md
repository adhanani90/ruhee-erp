# AGENTS.md — Ruhee ERP (New Depo pilot)

Instructions for every coding assistant working in this repository (Claude Code, Codex, ChatGPT, any other). Claude Code, Codex and ChatGPT all build and review (D-017).
Read this file, `docs/STATUS.md` and your task card before doing anything else.

## 1. What this project is

An ERPNext 16 system for Ruhee's three stores (Ruhee Depo and New Depo in Kinshasa, Mbanzangu outside Kinshasa), which trade as one company under one banner. The pilot is **New Depo, live on 1 December 2026, running alongside the old system**.

The business is cash-only. Every bill is in USD or CDF, every customer balance is in USD, each store sets two exchange rates a day, and billing PCs must keep working offline for up to a week.

### Sources of truth, in order

1. `docs/ACCOUNTING_RULES.md`: money rules R1–R17, invariants I1–I9, worked examples A–N.
2. `docs/SPEC.md`: requirements (`REQ-*`), scope, architecture.
3. `docs/DECISIONS.md`: decisions, and the M1 spike report.
4. `docs/ACCEPTANCE_TESTS.md`: spike checks C1–C13, automated tests `AUT-*`, manual tests `AT-*`.
5. `docs/STATUS.md`: current phase, open questions Q1–Q11, next tasks.
6. Your task card (a GitHub issue).

If two sources conflict, stop and report the conflict in your PR or issue. Do not pick one.

## 2. Stack and version pins

| Component | Version | Notes |
| --- | --- | --- |
| Frappe Framework | `version-16`, exact tag pinned in M1-02 | Never edit |
| ERPNext | `version-16`, exact tag pinned in M1-02 | Never edit |
| POS Awesome | Our fork of `defendicon/POS-Awesome-V15`, commit pinned in M1-02 | App name expected to be `posawesome` (verify in M1-01) |
| ruhee_erp | This repository | All our customisation |
| Hosting | Frappe Cloud private bench with a staging site and a production site | See `docs/DEPLOYMENT.md` |
| Python / Node | As Frappe 16 requires | Community v16 install guides say Python 3.14 and Node 24; confirm from the `frappe` repo before relying on it |

Pins are recorded in `docs/DEPLOYMENT.md`. Never upgrade or change a pin without a `docs/DECISIONS.md` entry approved by Sam.

## 3. Repository map

```
ruhee-erp/                  repository root = Frappe app root
├── AGENTS.md               this file
├── CLAUDE.md               imports this file, plus Claude Code notes
├── pyproject.toml          created by `bench new-app` (M1-01)
├── ruhee_erp/              Python package: hooks.py, module, doctypes, fixtures, print formats, reports
│   ├── spike/              M1 scripts only; never wired into hooks.py; never deployed to production
│   └── tests/              automated tests (AUT-*)
├── migration/              import templates and validators (P2/P3)
├── docs/                   SPEC, ACCOUNTING_RULES, ACCEPTANCE_TESTS, DATA_MAPPING (P2), DECISIONS, STATUS, DEPLOYMENT
└── .github/                CI workflow (from the scaffold) and pull-request template
```

## 4. Who builds what

| Module | Builds | Reviews |
| --- | --- | --- |
| M1 spike cards | Claude Code (Sam runs dashboard and PC steps) | Sam |
| Settings as code: company, stores, accounts, roles, permissions | Claude Code | ChatGPT |
| Rates and payment rules (R1–R12), with tests | Claude Code | ChatGPT, against ACCOUNTING_RULES |
| Returns, refunds and swaps (R13–R17), including the mixed-return fallback | Claude Code | ChatGPT, against ACCOUNTING_RULES |
| POS Awesome hooks: rates, split payments, offline rate entry | Claude Code | Sam, on two PCs |
| Daily close per currency | Claude Code | ChatGPT |
| Import templates, validators, `docs/DATA_MAPPING.md` | ChatGPT | Claude Code, by importing on staging |
| A4 bill print format | ChatGPT | Claude Code, rendered on staging |
| Reports: daily sales and expenses, ageing | ChatGPT | Claude Code |
| French quick guides, wording of the acceptance script | ChatGPT | Sam and the New Depo lead |
| SPEC, ACCOUNTING_RULES, DECISIONS | Claude (chat) | Sam; accounting sign-off by the Q6 signatory |

This split is the default. Codex builds and reviews too (D-017, amending D-012): Sam names one owner per card, and Codex may take any card, including code that runs against ERPNext.

- **Review:** the author is never the only reviewer. For money, stock and permission code at minimum, Codex reviews Claude Code's PRs and Claude Code reviews Codex's, in addition to the reviewers above.
- **Conflicts:** no two tools work on the same card, or on the same files in parallel. This file is the single source of shared instructions.

If one assistant is out of usage, another takes the next **unstarted** card, never a card already in progress.

## 5. Hard rules

1. **One card at a time, allowed paths only.** If you find something outside your card, list it in the PR under "Found, not done".
2. **Never invent behaviour or APIs.** Read the installed source (`apps/frappe`, `apps/erpnext`, `apps/posawesome`) and cite `file:function` in your PR. If you can't verify something, write "unverified".
3. **Never edit `frappe` or `erpnext`.** Customise through `ruhee_erp`: hooks, `doc_events`, whitelisted methods, and custom fields or property setters exported as fixtures. Use `override_doctype_class` only when there is no alternative, and record it in DECISIONS.
4. **Change POS Awesome only in our fork,** minimally, one commit per change, each listed in DECISIONS. Prefer hooks in `ruhee_erp`.
5. **Money follows ACCOUNTING_RULES exactly.** Use Frappe's `flt` and currency precision. Never hard-code a rate. Every CDF document references a store rate record (I6). Never alter a submitted document to fix a rate (I8).
6. **Open questions Q1–Q11 are not yours to answer.** If your card depends on one, stop and report it. Do not implement anything that presumes an answer.
7. **Printed documents show exactly what is recorded** (I1). No alternate prices on any print.
8. **Settings live in code** (fixtures, patches, setup scripts), never only in the browser.
9. **No secrets in the repo:** passwords, API keys, `site_config.json` values.
10. **Spike code lives in `ruhee_erp/spike/`,** is not referenced from `hooks.py`, and is never deployed to production.
11. **Scope:** do not add the DGI facture normalisée, delegates, purchase orders, landed costs, batch or expiry tracking, cold-chain records, payroll, assets, projects, WhatsApp or pre-orders.
12. Never commit real customer, supplier, price, stock or cash data, or exports from the old system, including in tests, fixtures and docs. Use invented data. Real data goes only through Frappe Cloud uploads or the git-ignored /data/ folder.

## 6. Conventions

- Code, comments, commit messages and PRs are in English. User-facing labels are in French, with translations in `ruhee_erp/translations/fr.csv`.
- Custom field names are prefixed `ruhee_`. Custom DocType names start with "Ruhee " (the exact name is decided in its card).
- One module, "Ruhee ERP", unless a card says otherwise.
- Test files are `ruhee_erp/tests/test_<group>.py`, with groups `currency`, `rates`, `stock`, `offline`, `returns`, `permissions`, `migration`. Each test names the rule or example it covers, e.g. `test_example_C_usd_bill_paid_in_cdf`.
- Branch names are `<card-id>-<slug>`, e.g. `M1-01-scaffold-app`, `T-014-store-rate`.

## 7. Running things

From the bench directory:

```bash
bench --site dev.localhost set-config allow_tests true      # once per site
bench --site dev.localhost run-tests --app ruhee_erp
bench --site dev.localhost run-tests --module ruhee_erp.tests.test_currency
bench --site dev.localhost migrate
bench build --app ruhee_erp
bench --site dev.localhost execute ruhee_erp.spike.<module>.<function>
```

Verify every command against the installed bench (`bench --help`) before relying on it.

## 8. Pull requests and definition of done

- One card is one branch and one PR. Never push to `main`. Sam squash-merges.
- Every PR links its card, lists its spec references (`REQ-`, `R`, `I`, `C`, `AUT-`, `AT-`), lists the tests run with results, attaches the evidence the card asks for, names the source files and functions consulted, and updates `docs/STATUS.md`.
- Cross-review is required for money rules, permissions, imports and migration, offline settings, and POS Awesome hooks. The reviewer gets the diff and the rules it must meet.
- A card is done when its acceptance criteria are met with evidence, tests pass locally and in CI, the PR contains no unrelated changes, and the docs are updated.

## 9. Session ritual

- **Start:** read `docs/STATUS.md`, the card, and only the sections and files the card references. Don't load whole documents or the whole POS Awesome app.
- **End:** update `docs/STATUS.md` (done, next, blockers, questions raised), push the branch, and write the PR description as the session record.

## 10. Documentation rules

- `docs/SPEC.md` and `docs/ACCOUNTING_RULES.md` change only through a docs-only PR approved by Sam. ACCOUNTING_RULES changes also need a fresh sign-off.
- `docs/DECISIONS.md` is append-only, and every entry is dated.
- `docs/STATUS.md` stays one screen long.
