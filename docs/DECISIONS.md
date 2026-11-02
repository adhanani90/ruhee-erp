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

## D-021 Staging freeze during the C8 offline test
- **Decision:** staging is frozen Wed 4 – Fri 6 Nov 2026 while C8 runs: no new rate records, item imports or configuration changes, with no exceptions. Card M1-08's step that enters a server rate during the outage moves to a separate short offline run after the freeze (Sat 7 or Sun 8 Nov). Other staging work happens before or after the freeze.
- **Why:** with staging unchanged, any bill lost, duplicated or re-rated during C8 is down to POS Awesome. PRs #19 and #20 proposed the freeze; issue #9's amendment of 31 Oct entered a server rate during the outage (31 Oct audit, F-01).
- **Alternatives:** exempt that one rate entry; no freeze.
- **Status:** Approved by Sam, 2 Nov 2026.

## D-022 M1 currency coverage
- **Decision:**
  - M1 proves examples A, C and D (C3–C5). Examples B, E and F are recorded as unproven at the go/no-go and are proven in P2 by AUT-CUR-02, AUT-CUR-05 and AUT-CUR-06.
  - C8 uses card M1-08's latest mix (issue #9, 31 Oct, 05:41Z): CDF bills paid in CDF, USD or both; no francs against USD bills or USD balances; no change given in another currency. C8 checks sync, not amounts, so its CDF bills paid in USD don't prove example B.
- **Why:** SPEC §14 required M1 to prove examples A–F, but the M1 checks cover only A, C and D, and the evidence #9 cited for B and mixed tender isn't in #6 or PR #20 (31 Oct audit, F-09, F-10, F-34).
- **Alternatives:** run B, E and F in M1-05 before the go/no-go; C8 without cross-currency payments (#9, 03:07Z); ACCEPTANCE C8 as first written.
- **Status:** Approved by Sam, 2 Nov 2026. SPEC §14 and ACCEPTANCE C8 updated to match.

## D-023 STATUS and DECISIONS, one open PR at a time
- **Decision:** only one open PR at a time edits `docs/STATUS.md` or `docs/DECISIONS.md`. The others keep their status lines and results in the PR description until Sam gives them the turn, then rebase on `main` and add them. STATUS names the next holder, and each PR updates that line as it merges. After the 31 Oct audit's docs PR, the order is #19, #20, then `m1-07-offline-sync`.
- **Why:** D-017 bars two tools from the same files in parallel, but every PR updates STATUS and each M1 card writes spike-report rows; PRs #19 and #20 and branch `m1-07-offline-sync` all edited both files (31 Oct audit, F-02).
- **Alternatives:** treat STATUS and the spike-report rows as shared, each PR editing only its own lines.
- **Status:** Approved by Sam, 2 Nov 2026. Amends D-017.

## D-024 Claude Code may change the POS Awesome fork
- **Decision:** the card's owner, Claude Code included, may commit changes Sam has approved to our fork in `apps/posawesome`, under AGENTS.md's fork rule. CLAUDE.md's read-only rule covers `apps/frappe` and `apps/erpnext` only.
- **Why:** CLAUDE.md barred Claude Code from editing `apps/posawesome`, the bench's checkout of our fork, while AGENTS.md allows minimal fork changes; M1-05 and M1-07 may need one (31 Oct audit, F-27).
- **Alternatives:** fork changes by Codex or Sam only.
- **Status:** Approved by Sam, 2 Nov 2026.

## D-025 Spike code never reaches production
- **Decision:** before the production site is created (P5), a PR removes `ruhee_erp/spike/` from `main` (history keeps it), and that build is deployed first. Code outside the spike folder never imports from it; a prototype worth keeping moves into a real module first.
- **Why:** staging and production share one bench group built from `main`, so the spike folder would otherwise reach production (31 Oct audit, F-04).
- **Alternatives:** let it ship but never run.
- **Status:** Approved by Sam, 2 Nov 2026.

## D-026 Cards over several PRs, and departures already merged
- **Decision:**
  - A card may take several PRs when each says "Partially addresses #n" and Sam agrees in it. Otherwise one card is one branch and one PR.
  - PR #16 (`.gitignore` alongside SPEC and ACCOUNTING_RULES), PR #17 (`pyproject.toml` outside its card's paths, no STATUS update), PR #21 (no STATUS update) and the 31 Oct audit's ACCOUNTING_RULES-only PR (no STATUS update) are approved exceptions. The rules are otherwise unchanged.
- **Why:** M1-02 (PR #17) and M1-03 (PR #18) are each partly delivered and need a further PR (31 Oct audit, F-31, F-32).
- **Alternatives:** one PR per card, with leftover work as new cards; loosening AGENTS.md to match the departures.
- **Status:** Approved by Sam, 2 Nov 2026. Amends D-012 and D-017.

## D-027 Phases stay undated
- **Decision:** P2–P4 are an order of work, not dated phases; their pace follows the time Sam has. The fixed dates stay the go/no-go (9 Nov), the freeze (20 Nov), testing and stabilisation (23–28 Nov), cutover (29–30 Nov) and go-live (1 Dec). An open question needed before a phase falls due when that phase starts.
- **Why:** STATUS and ACCOUNTING_RULES gate on phases that have no dates (31 Oct audit, F-24).
- **Alternatives:** date each phase.
- **Status:** Approved by Sam, 2 Nov 2026.

## D-028 Hosting plan split
- **Decision:** staging and production each run on a $25–50 plan: $50–100 a month in total, up to the $100 ceiling.
- **Why:** SPEC §14 and DEPLOYMENT §11 gave about $50–75 a month for two sites on $25–50 plans, which spans $50–100 (31 Oct audit, F-29).
- **Alternatives:** staging on $25 and production on $25–50, about $50–75 a month.
- **Status:** Approved by Sam, 2 Nov 2026.

---

## Pending

These are proposals and questions, not decisions:

- [M1-05 payment integration proposal — DRAFT, not approved](../ruhee_erp/spike/M1-05-integration.md#3-draft-not-approved--submission-and-payment-integration).
- Proposals awaiting the owners' approval: `SPEC.md` §16 (Q10).
- Open questions Q1–Q11: `STATUS.md`.

---

## M1 spike report

*Filled in by card M1-11. Evidence links point to PRs, issue comments or screenshots.*

| Check | Result (pass / fail / workaround) | Evidence | Notes |
| --- | --- | --- | --- |
| C1 Install | | | |
| C2 Posting | pass (local); staging/UI pending | [M1-04 local extracts](../ruhee_erp/spike/evidence/m1_04_local.json), [runbook](../ruhee_erp/spike/M1-04.md) | 30 Oct Toronto / 31 Oct site time: three separate Sales Invoices, one stock deduction each at submit; native shift close leaves invoice list and ledger hashes unchanged. Requires create_pos_invoice_instead_of_sales_invoice=0 and update_stock=1. |
| C3 CDF bill | fail; staging/UI pending | [Saved invoice/GL/precision](../ruhee_erp/spike/evidence/m1_04_saved_precision.json), [runbook](../ruhee_erp/spike/M1-04.md) | Saved $100 line and grand_total 229,999.79 FC; rounded_total 230,000 FC, adjustment +0.21 FC / $0, no Round Off GL; Debtors Dr/Cr $100. Exact-input 23,000,000 FC: no rounding, no Round Off GL, Debtors Dr $10,000.01 (expected $10,000.00). Both rate fields precision 9, decimal(21,9). No compensation here; #6 investigation is in progress in PR #20. |
| C4 Cross-currency payment | workaround proposed; server harness only | [Native failure](../ruhee_erp/spike/evidence/m105_native_9.json), [exact PE GL](../ruhee_erp/spike/evidence/m105_store_prototype.json), [design report](../ruhee_erp/spike/M1-05.md) | Cash CDF 232,000 FC valued at $100.87; Cr Debtors $100; Cr Exchange income $0.87. Native USD/CDF submit fails. Missing POS integration and Payment Entry replay protection remain open; no production or offline acceptance claimed. |
| C5 Part-payment | pass (local server/report); staging/UI pending | [M1-04 local extracts](../ruhee_erp/spike/evidence/m1_04_local.json), [runbook](../ruhee_erp/spike/M1-04.md) | Manually entered 230,000 FC line price (R1 value) less 115,000 FC paid posts Cash CDF $50 / Cr Debtors $50; invoice and Accounts Receivable outstanding USD $50. A natively priced equivalent was not executed. Screenshots pending. |
| C6 Rounding (native direction, for Q1) | partial overall; local proof complete, staging pending | [C6 bill/GL extracts](../ruhee_erp/spike/evidence/m1_04_rounding.json), [runbook](../ruhee_erp/spike/M1-04.md) | 30 Oct Toronto / 31 Oct site time: native nearest 50 FC; ties (remainder exactly 25 FC) round down per source, not exercised. H 00018: 77,310 -> 77,300 (-10 FC), base adjustment $0.00, Dr Debtors/Cr Sales $33.61, no Round Off. 00019: 77,326 -> 77,350 (+24 FC), base adjustment $0.01, Dr Debtors $33.63 / Cr Sales $33.62 / Cr Round Off $0.01; each also Dr COGS/Cr Stock $80. Both outcomes match C6's cent threshold as revised in PR #22; Q1 remains open. |
| C7 Store rate (online and offline) | | | |
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

## M1-05 design note — 2026-11-02

Card #6, owner Codex; independent reviewer Claude Code. C4 remains **workaround
proposed; server harness only**. [Design report and recorded GL](../ruhee_erp/spike/M1-05.md)
separate the laboratory observations from real POS operation and contain the
online store-rate findings; C7's final result belongs to #8. M1-04's C3 result
and later re-proof remain with [merged PR #19](https://github.com/adhanani90/ruhee-erp/pull/19)
under D-026. Existing merged spike results are unchanged.

[Draft integration assessment](../ruhee_erp/spike/M1-05-integration.md) compares
online, off, dual_write, coordinator and background submission paths at POS Awesome
89ae16d, including a source-only Sales Invoice on_submit hook alternative and
unverified transaction/replay tests. The Payment Entry adapter has neither POS
integration nor replay protection. The **8–12 builder-day** estimate is planning
input for M1-11, dependent on #8's mode findings; it does not authorize P2.
D-022 leaves examples B, E and F unproven in M1 and assigned to P2. Accounting
sign-off remains pending. No production hook, migration or fork change is selected.
