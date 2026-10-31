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
| C3 CDF bill | | | |
| C4 Cross-currency payment | | | |
| C5 Part-payment | | | |
| C6 Rounding (native direction, for Q1) | | | |
| C7 Store rate (online and offline) | | | |
| C8 Offline, two PCs | | | |
| C9 Offline edge cases | | | |
| C10 Closing per currency | | | |
| C11 A4 print | | | |
| C12 Performance and backup | | | |
| C13 Returns, including the mixed return | | | |

**POS Awesome sync design (from M1-07):** endpoints, request identity, retry and failure behaviour, cache refresh.

*Written 31 Oct 2026 from posawesome `89ae16d`. Paths are relative to `apps/posawesome`; `frontend/src/` is shortened to `src/`. Evidence: `ruhee_erp/spike/replay_check.py`, `ruhee_erp/spike/evidence/m107_*.json` (cc.localhost).*

- **Queue.** Offline bills go into the IndexedDB `write_queue` table (`src/offline/invoices.ts:saveOfflineInvoice`) as the same `{invoice, data}` pair an online submit sends, including `invoice.payments` (`src/posapp/composables/pos/payments/usePaymentSubmission.ts`, offline branch). Exchanges and gift-card redemptions are refused offline (same function). Customers, payments and cash movements have their own queues (`src/offline/customers.ts`, `payments.ts`, `cash_movements.ts`); not traced further here.
- **Sync method.** `src/offline/invoices.ts:syncOfflineInvoices` posts each entry to `posawesome.posawesome.api.invoices.submit_invoice`, which is also the online method, with no `submit_in_background` argument (so 0, always in-request). A second path, `api/offline_sync/invoices.py:submit_invoice_outbox_entry`, runs only in outbox mode `"coordinator"`; the default is `"off"` (`src/offline/db.ts`, `MEMORY_DEFAULTS`) and nothing sets it.
- **Request identity.** `posa_client_request_id` = `inv-<time>-<uuid>`, created once per bill (`src/offline/idempotency.ts:ensureInvoiceSubmissionIdentity`) and kept in the queued payload. The server dedupes in `api/invoice_processing/creation.py:_submit_invoice_once` on (a) the POS Invoice Submission Ledger, keyed by SHA-256 of request id, company, profile and doctype (`_submission_ledger_key`), and (b) `idempotency.py:find_invoice_by_client_request_id`. Both are unique in the database: `ledger_key` is the primary key, and `posa_client_request_id` has a UNIQUE index on Sales Invoice, POS Invoice and Payment Entry (checked on cc.localhost). **Replay check (I7, AUT-OFF-01): PASS.** Three submits of the same payload gave one invoice, one payment row, one stock movement and one ledger row, and no Payment Entry, for a CDF bill paid in CDF and a USD bill paid in USD; replays returned `replayed: true`.
- **Retry and failure.** If `submit_invoice` throws, the request rolls back (`frappe/app.py`), then the client calls `update_invoice` with the same invoice. If that saves, the server keeps a **draft** with the request id, the queue entry is marked synced and is never retried, and the facturier sees "N offline invoice(s) saved as draft" (`src/posapp/stores/syncStore.ts`). If that fails too, the entry is marked `failed` and retried on each sync, and after 5 failures it becomes `dead_letter` (`src/offline/writeQueue.ts:markWriteQueueEntryFailed`), which is no longer retried (`RETRYABLE_STATUSES`). The server keeps nothing.
- **Rates.** The browser's rate comes from `src/posapp/services/exchangeRateResolver.ts:resolveExchangeRate`, called by `useInvoiceCurrency.ts:update_currency_and_rate` with the PC's date. It checks, in order: the in-memory list, `src/offline/cache.ts:getCachedExchangeRate` (24 h), `CurrencyRateRepository.findLatestOnOrBefore`, then the server. The rate records refresh at boot, on reconnection, on a profile change or when the user presses sync, with no timer (`src/offline/sync/resourceRegistry.ts`, `currency_matrix`). **On sync the server discards the browser's rate:** `creation.py:update_invoice` recomputes `conversion_rate` with `invoice_processing/utils.py:get_latest_rate` (latest record on or before the bill's date, newest created first). Probe (`replay_check.rate_probe`): a 57,500 FC bill made at 2300 for 29 Oct, followed by a newer 29 Oct record at 2400, was stored with `conversion_rate` 0.000416667 and $23.96 in every USD total and GL line, instead of $25.00. That breaks I6 and I8 (the bill doesn't keep the rate it was made with) and C7's offline criterion. The fix belongs to the store-rate design (M1-05, P2): the bill must carry its store rate record and the server must use it.
- **Prices, stock, credit limits:** not traced in this pass.
- **Returns offline (for C13):** not answered yet.

**REQ-OFF-02 gaps ("any that fail become drafts for the manager"), with the smallest fix for each:**

| Gap | Today | Smallest fix |
| --- | --- | --- |
| Dead letters | After 5 failed syncs the bill stays only in that PC's IndexedDB. The Offline Invoices dialog (`src/posapp/components/OfflineInvoices.vue`) lists it but offers only Delete and "Sync All", which skips it. The only export is the console call `window.__POS_OFFLINE_DIAGNOSTICS__.exportRecoveryData()` (`src/offline/db.ts`). | **ruhee_erp only, to verify:** `override_whitelisted_methods` on `update_invoice`. When the sync fallback's draft save fails validation, store the raw payload and the error in a ruhee record for the manager and return success, so the entry never dead-letters. Open point: online draft saves call the same method, so the override must tell the two apart. **Otherwise a fork change:** a Retry and an Export button on dead letters in `OfflineInvoices.vue`. |
| Drafts that stop retries | The draft exists on the server, but nothing tells the manager, and the error the bill failed on is lost (browser console only). | **Configuration:** a Notification and a saved list filter (fixtures) on Sales Invoice drafts that carry `posa_client_request_id`. **Plus ruhee_erp only:** an `override_whitelisted_methods` wrapper on `submit_invoice` that writes the error, keyed by request id, before re-raising. |
| No warning when an offline PC uses yesterday's rate | `findLatestOnOrBefore` returns the latest cached record silently. `update_currency_and_rate` only warns when no rate is found at all. | **Fork change** in `useInvoiceCurrency.ts:update_currency_and_rate`: compare the returned `rateDate` with the bill's date. Whether to warn or block is Q5, which is open, so this waits on Q5. |

**Changes made in our POS Awesome fork:** *none yet.*

**Recommendation:** *to fill.*

**Go/no-go decision (Sam):** *to fill*, with the date and the chosen path if a fallback is used.
