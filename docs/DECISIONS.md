# DECISIONS — Ruhee ERP

This file is append-only. Every entry gives the decision, the reason, the alternatives considered and the status. Decisions D-001 to D-016 were taken in the planning conversation during October 2026 and approved with the plan on 30 Oct 2026.

---

## D-001 ERPNext rather than Odoo
- **Decision:** ERPNext (open source, GPL).
- **Why:** no per-user licence fees, so adding stores and staff doesn't raise the monthly bill, and full accounting is included. The owners accepted a longer setup in exchange for the lower cost.
- **Alternatives:** Odoo Community (accounting gaps, add-on costs as the business grows) or Odoo Enterprise (per-user pricing).
- **Status:** Approved.

## D-002 DGI facture normalisée out of scope
- **Decision:** not built.
- **Why:** the owners decided it after checking on site in Kinshasa.
- **Status:** Approved. Do not reopen.

## D-003 Delegates out of scope
- **Decision:** the delegate (sales representative) features are not built.
- **Status:** Approved.

## D-004 Stack and hosting
- **Decision:**
  - ERPNext and Frappe 16, pinned.
  - POS Awesome from our fork of `defendicon/POS-Awesome-V15`, pinned.
  - All customisation in one app, `ruhee_erp`.
  - A Frappe Cloud private bench with a staging site and a production site.
- **Why:** POS Awesome provides offline billing, credit, part-payments and mixed-currency payment methods. A private bench allows custom apps.
- **Alternatives:** POSNext, ERPNext's own invoice screen, or a self-hosted server. These are the fallbacks in `SPEC.md` §14.
- **Status:** Approved, subject to the M1 go/no-go.

## D-005 Currency model
- **Decision:**
  - The company currency is USD, and every customer balance is in USD.
  - CDF cash is held in CDF accounts and valued at the store's base rate for the day.
  - The spread from the higher rate goes to Exchange income.
- **Status:** Approved; awaiting accounting sign-off (Q6).

## D-006 Two rates per store per day
- **Decision:** each store's manager sets a base rate and a higher rate at opening, from the market.
- **Rules:**
  - Bills in CDF, and USD paid against CDF bills, use the base rate.
  - CDF paid against USD bills or USD balances uses the higher rate (R3, R5). The owner confirmed this.
- **Status:** Approved.

## D-007 Counter flow without cashier PCs
- **Decision:**
  - Only managers and facturiers have PCs.
  - The cashier, packers and livraison work from the printed A4 bill.
  - The payment method and share are marked by the facturier at billing, and the cashier stamps the bill on receipt.
- **Status:** Approved. Do not reopen.

## D-008 Stock deducted at billing
- **Decision:** one Sales Invoice with stock update per bill, and negative stock allowed.
- **Why:** the owners accept stale stock and resolve overselling with a quick purchase or a refund.
- **Status:** Approved; the mechanism is confirmed in C2 and C9.

## D-009 Offline per billing PC
- **Decision:**
  - Each billing PC keeps its own offline queue and syncs on reconnection. There is no store server.
  - Returns are entered online until M1 shows they work offline.
- **Why:** outages can last up to a week, and only the billing PCs run the software.
- **Status:** Approved. Do not reopen.

## D-010 Returns as credit notes
- **Decision:**
  - Every return is a credit note against the original bill, made by a manager.
  - Restocking is marked per line.
  - Settlement is by refund, credit or swap, as today.
- **Mixed-return fallback:** if one credit note can't mix restocked and non-restocked lines, the app splits the return into two credit notes against the same bill, created and printed together.
- **Status:** Approved; the mechanism is confirmed in C13, and the refund currency is Open (Q11).

## D-011 Printed bill equals recorded invoice
- **Decision:** invariant I1. No print shows a price different from the recorded one.
- **Status:** Approved.

## D-012 Development model
- **Decision:**
  - The private GitHub repository is the source of truth.
  - Claude Code builds anything that must run against ERPNext. ChatGPT builds self-contained pieces. Claude (chat) maintains the spec and the accounting rules.
  - One card is one branch and one PR. Sam merges and releases.
- **Status:** Approved.

## D-013 Automated test scope
- **Decision:** seven automated groups: currency, rates history, stock exactly once, offline sync and duplicates, returns, permissions and credit limits, migration.
- **What stays manual:** browser-level offline behaviour and the paper flow.
- **Status:** Approved.

## D-014 Pilot and parallel run
- **Decision:** New Depo goes live on 1 Dec 2026 alongside the old system.
- **Exit criterion:** the old system stops at New Depo after 10 consecutive trading days in which sales, cash by currency and balances match.
- **Status:** Approved.

## D-015 Scope for 1 December
- **Decision:** the MVP and the after-launch order are as in `SPEC.md` §15.
- **Status:** Approved.

## D-016 Schedule
- **Decision:** feature freeze on 20 Nov; testing and stabilisation 23–28 Nov; cutover 29–30 Nov; go-live 1 Dec.
- **Planned M1 dates:** P0 26–29 Oct, M1 27 Oct – 2 Nov, go/no-go Mon 2 Nov.
- **Status:** Approved. P0 actually started on 30 Oct (see `STATUS.md`).

## D-017 Codex in the working model
- **Decision:** OpenAI Codex joins Claude Code and ChatGPT as a builder and
  reviewer. Sam names one owner per card; one card is one branch and one PR;
  Sam merges. Codex may take any card, including code that runs against
  ERPNext. Amends D-012, which reserved that work for Claude Code.
- **Review:** the author is never the only reviewer. Codex reviews Claude
  Code's PRs and Claude Code reviews Codex's, at minimum for money, stock
  and permission code.
- **Conflict rule:** no two tools work on the same card, or on the same
  files in parallel. AGENTS.md stays the single source of shared
  instructions.
- **Why:** a second model reviewing money and stock code catches errors the
  author misses; more than one builder speeds up P2.
- **Alternatives:** keep D-012 unchanged.
- **Status:** Approved by Sam, 30 Oct 2026, on merge of this PR.

## D-018 Move the M1 go/no-go to Mon 9 Nov 2026
- **Decision:** the M1 go/no-go moves from Mon 2 Nov to Mon 9 Nov 2026. The
  20 Nov feature freeze and the 1 Dec go-live are unchanged.
- **Why:** P0 started on 30 Oct instead of 26 Oct, and M1 needs about 3
  assistant days, 1 day of Sam's and a 24-hour offline test (C8).
- **Alternatives:** hold 2 Nov.
- **Status:** Approved by Sam, 30 Oct 2026.

## D-019 The repository stays public
- **Decision:** adhanani90/ruhee-erp stays public. Amends D-012, which
  describes it as private.
- **Guard:** no real customer, supplier, price, stock or cash data, and no
  exports from the old system, are ever committed (AGENTS.md). Revisit
  before P3 migration work.
- **Why:** the repository holds no sensitive data, and public repositories
  get free GitHub Actions minutes.
- **Alternatives:** make it private.
- **Status:** Approved by Sam, 30 Oct 2026.

## D-020 Returns by managers and head office
- **Decision:** managers and head office can process returns, refunds and
  swaps; facturiers cannot. Amends D-010 and REQ-RET-01, which said
  managers only.
- **Why:** Sam's decision after the 30 Oct audit found SPEC and AUT-RET-08
  disagreed.
- **Alternatives:** managers only.
- **Status:** Approved by Sam, 30 Oct 2026.

---

## Pending

These are proposals and questions, not decisions:

- Proposals awaiting the owners' approval: `SPEC.md` §16 (Q10).
- Open questions Q1–Q11: `STATUS.md`.

---

## M1 spike report

*Filled in by card M1-11. Evidence links point to PRs, issue comments or screenshots.*

| Check | Result (pass / fail / workaround) | Evidence | Notes |
| --- | --- | --- | --- |
| C1 Install | | | |
| C2 Posting | | | |
| C3 CDF bill | fail (precision) | [Native scratch GL](../ruhee_erp/spike/evidence/m105_native_9.json), [audit](../ruhee_erp/spike/M1-05-integration.md), [#5 draft](https://github.com/adhanani90/ruhee-erp/pull/19) | Native $100 line 229,999.79 FC; exact 23,000,000 FC bill posts $10,000.01. Scratch precision experiments do not close C3 or change dev/#5. |
| C4 Cross-currency payment | workaround proposed | [Native failure](../ruhee_erp/spike/evidence/m105_native_9.json), [store/PE GL](../ruhee_erp/spike/evidence/m105_store_prototype.json), [integration gap](../ruhee_erp/spike/M1-05-integration.md) | Native USD/CDF rejected. Server bench harness gives exact example C/large PE GL, but no UI/submit/outbox wiring or unique PE request identity; AUT-OFF-01 unproven. Not an accepted online/offline workaround. |
| C5 Part-payment | | | |
| C6 Rounding (native direction, for Q1) | | | |
| C7 Store rate (online and offline) | partial | [Store-record harness](../ruhee_erp/spike/evidence/m105_store_prototype.json), [integration audit](../ruhee_erp/spike/M1-05-integration.md) | Direct base/higher record is stored and linked; explicit harness binding beats company rate 9999 and history is unchanged. Compatibility arithmetic still uses reciprocals. Manager entry, effective-time/store selection, UI and common submit/sync integration unproven; offline final result belongs to M1-07. |
| C8 Offline, two PCs | | | |
| C9 Offline edge cases | | | |
| C10 Closing per currency | | | |
| C11 A4 print | | | |
| C12 Performance and backup | | | |
| C13 Returns, including the mixed return | | | |

**POS Awesome sync design (from M1-07):** endpoints, request identity, retry and failure behaviour, cache refresh. *To fill.*

**Changes made in our POS Awesome fork:** *none yet.*

**Recommendation:** *to fill.*

**Go/no-go decision (Sam):** *to fill*, with the date and the chosen path if a fallback is used.

## M1-05 design note — 2026-10-30 (scratch execution pending)

This is a source-backed investigation note, not approval of a production money
change. [M1-05 audit, source references, candidate rankings and scratch runbook](../ruhee_erp/spike/M1-05.md).
The native Sales Invoice mixin values and settles each tender through one effective
conversion and handles excess as change; no separate R7 Exchange income line is
constructed there. A USD invoice has conversion_rate=1, so raising that invoice
field's precision alone cannot fix its CDF payment valuation or introduce the
2320/2300 split. Payment Entry, app hook and minimal-fork routes must be compared
against native scratch GL, preserving I2/I4/I6/I8 and one USD price list.

Prepared code is guarded to `m105.localhost`, a restore of an existing dev backup.
Sam must enter MariaDB root credentials locally; no site configuration secret is
read into the report. Actual missing prerequisites, native C3/C4/large/O results,
12-place migration/new/old document evidence and C7 routing remain pending. No
production hook, precision fixture or fork change is selected or deployed.

## M1-05 measured design note — 2026-10-30 (31 Oct site time)

[Complete source references, scratch results, route ranking and caveats](../ruhee_erp/spike/M1-05.md).
The restored backup was pre-setup (zero Company/Sales Invoice rows). M1-03 seeded
invented data on scratch only; this is not a current dev settings audit.

Native Sales Invoice cannot post a CDF drawer when company/invoice currencies are
both USD: `erpnext/controllers/accounts_controller.py:AccountsController.get_gl_dict`
calls `validate_account_currency`. Configuration enables the feature but cannot
remove this restriction. C4 fails at submit with no committed GL.

Ranked candidate: retain a USD invoice allocation and post its CDF part through a
Payment Entry orchestrated by a ruhee_erp rate adapter. The scratch prototype uses
ERPNext `get_payment_entry`, ordinary insert/submit and a pre-submit deduction to
Exchange income. It proves C's exact $100.87/$100/$0.87 GL and the large
$10,086.96/$10,000/$86.96 GL using a referenced store record, even against company
rate 9999. A deliberately truncated nine-place-value PE instead posts $10,086.97
cash and $86.97 income; I2 can still balance while exact R7 valuation fails.

The prototype is process-scoped, not a hooks.py registration or a production
decision. Its scratch-only submitted rate record/link schema is not exported as
a production DocType. App hooks/PE orchestration rank above a direct POS fork;
browser integration, atomic/idempotent offline replay and returns remain unverified.
Any production/fork choice needs approval, a dated DECISIONS entry and the listed
AUT-CUR-01/03/04/05/06/10/12 and AUT-RATE-01 regressions. Payment rounding remains
Q1-dependent (AUT-CUR-14); native normalization preserved 2320 FC with no 50 FC step.

Precision is an independent prerequisite: invoice-only 12 places did not fix the
source error or native C4. Six Property Setters plus migrate left three real
columns at 9 despite metadata=12. Explicit final-metadata `MariaDBDatabase.updatedb`
sync plus a freshly recomputed 12-place reciprocal fixed both measured C3 drifts;
old saved invoices/GL remained unchanged. App-owned metadata with verified schema
ordering could be a production route; a fixture alone is not proven sufficient.
No Frappe, ERPNext or POS Awesome source edit, pin change, dev data change or queued
bill retry occurred. No production precision fixture is selected here.

## DRAFT — M1-05 POS payment integration and precision — 2026-10-30

**Status: proposed, not approved or implemented.** No new D-number or production
authorization is implied. [Full audit, command history, staging checks and estimate](../ruhee_erp/spike/M1-05-integration.md).

Keep one authoritative USD price list and immutable store records containing exact
direct base/higher quotes. The harness used literal 2300/2320 to create test data,
then read those fields; it did not implement manager/effective-time selection.
Reciprocals are compatibility values, not the accounting rate source. Derive cash
valuation by direct division and assert native stored results agree to the cent;
if not, block/retain the pending operation rather than compensate submitted GL.

Propose a ruhee_erp server orchestrator for invoice plus linked CDF Payment Entry,
shared by online submit and outbox replay. Capture tender currency/original amount,
USD allocation, rate identity/direct quotes and stable operation identity in the
same queued intent. Current `store_payment_prototype.run/payment` is a bench-only
harness: no UI/submit/sync registration, request key or replay protection. Merely
overriding the online HTTP method does not cover the outbox's internal Python call.
Use verified app hooks/wrappers for both endpoints or a minimal POS Awesome fork
delegating to the same service; no Frappe/ERPNext edits. Fork changes require their
own approved dated entry and AUT coverage.

Use a database-unique scoped bill/payment operation key, locked operation state,
payload hash and persisted SI/PE references. Replay returns the same documents;
changed payload under a used key is rejected. Handle incomplete invoice/payment
states before acknowledgement, including native early replay returns and any
commit boundaries. AUT-OFF-01 must prove sequential/concurrent/reload/crash replay
creates one SI, one PE and one stock movement; AUT-OFF-02/03/04 cover failure/rate/
association. This is a proposed design, not a passed idempotency result.

Tested compatibility precision candidate: 12 places for Sales Invoice.conversion_rate,
Currency Exchange.exchange_rate, Sales Invoice Payment.posa_exchange_rate and
posa_company_exchange_rate, Payment Entry.source_exchange_rate and target_exchange_rate.
Export app Property Setters/fixtures; use a versioned app migration plus verified
ordered post-fixture schema sync and repeated-migrate assertions. Fixture alone
left three columns at 9 in the observed migration. Preserve old recorded rates/GL;
new direct quotes become new effective rate records, never rewritten history.
All six are a tested configuration, not a proved minimal set for every route.

Estimate **8-12 builder-days** including AUT integration (online milestone roughly
4-6 within that total), plus 1-2 reviewer-days and at least a 24-hour offline soak;
allow 2-4 extra builder-days if a maintained POS fork is required. Required evidence:
AUT-CUR-01/03/04/05/06/10/12/14 (14 waits for Q1), AUT-RATE-01..06,
AUT-OFF-01..04, relevant permissions and real POS-created bills/prints.
Q1/Q2/Q5/Q6 remain gates, not assumed answers.

If common routing fails, evaluate the minimal fork. If exact arithmetic or duplicate
safety cannot be proved, do not acknowledge the CDF-on-USD transaction as paid or
ship it as offline-ready. Report no-go/limited scope to Sam; an interim supervised
online-only PE workflow needs an explicit scope decision. Staging migration/config
work remains outside the 4-6 Nov freeze. PR #20 remains draft.
