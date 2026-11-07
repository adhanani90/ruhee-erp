# M1-05 (#6): C7 store-rate binding through the real POS client

Partially addresses #6 (D-026). **C7 is not marked passed.** Combined validation with
PR #24 is **pending** until Codex supplies its tested commit. Production work is
outside this spike.

## 1. Ownership, exception and affected paths

- **Ownership.** Sam transferred #25 and its POS Awesome fork work from Codex to
  Claude Code on 6 Nov (Prompt 6). This is an explicit handoff, not a parallel
  assignment. Codex owns #24 only and reviews #25 and the fork independently.
- **Fork.** Sam approved one minimal experimental change on `m1-c7-client-rate` in
  `adhanani90/POS-Awesome-V15`, starting from `89ae16d`. It is commit `71fcee8`.
- **`hooks.py` exception.** Sam authorized the spike-hook references in
  `ruhee_erp/hooks.py` **on branch `m1-c7-store-rate` only**. This does not authorize
  merging them into `main` or deploying them.
- **Paths changed by this rework:** `ruhee_erp/hooks.py`;
  `ruhee_erp/spike/store_rate_hooks.py`, `store_rate_setup.py` (new),
  `store_rate_verify.py` (new), `c7_browser.mjs` (new), `store_rate_probe.py` (marked
  superseded), `store_rate_report.md`; `ruhee_erp/spike/evidence/c7_independent/**`
  (new). Fork: the eight files in §4.
- **Not touched:** `docs/STATUS.md` and `docs/DECISIONS.md` (D-023 turn), `c3_*`
  files, #24's branch, `m1-07-offline-sync`, the shared bench's checkouts, sites and
  services, `frappe` and `erpnext`.

## 2. Results (independent run, default precision, company rate 9999)

Fresh site `c7run1.localhost`, built only by the steps in §14. PR #24 is **not**
applied, so precision is Frappe's default (9 places; `precision_state.json`).
Every bill was entered through the real POS client in headless Chromium. Saved
results were graded by the separate read-only verifier against the requirements
(`graded.json`).

| Check | Requirement | Result |
| --- | --- | --- |
| C3-01 | $100 → 230,000 FC | **Pass.** `ACC-SINV-2026-00004`: line 230,000 FC; Debtors Dr/Cr $100; Cash CDF 230,000 FC = $100.00 |
| C3-02 | $10,000 → 23,000,000 FC | **Fail at default precision.** Line and total 23,000,000 FC are right; base, Debtors and Cash CDF are **$10,000.01**. Depends on #24's widening: pending |
| C4 / C | $100 paid 232,000 FC | **Pass.** `00002` + `ACC-PAY-2026-00001`: Cash CDF 232,000 FC = $100.87; Cr Debtors $100; Cr Exchange income $0.87 |
| Large C4 | $10,000 paid 23,200,000 FC | **Pass.** `00003` + `ACC-PAY-…-00002`: Cash CDF $10,086.96; Cr Debtors $10,000; Cr Exchange income $86.96. Holds at 9 places because CDF received is valued as CDF ÷ base (fixes review B4) |
| C5 / D | 115,000 FC against 230,000 FC | **Pass.** `00005`: Cash CDF 115,000 FC = $50; $50 outstanding |
| $3,200 line | exactly 7,360,000 FC | **Pass.** `00006`: line 7,360,000.00 FC; $3,200.00 |
| 240,000 FC diagnostic | net payment only | **Rejected, nothing saved.** The server explains that 240,000 FC covers $103.45 of a $100 bill and that change is handled by hand |
| Effective time A | issued before replacement, synced after | **Pass.** `00013` kept 2300: 230,000 FC = $100 |
| Effective time B | new bill after replacement | **Pass.** `00015` bound 2400: 240,000 FC = $100 |
| Effective time C | issued after replacement with superseded rate | **Pass.** Not submitted, not repriced: draft `00014` keeps 2300 and 230,000 FC, with a visible hold reason |
| Recovery, online submit fails | retry without change | **Pass.** Same request ID posted later as `00008` + one Payment Entry, after a browser restart |
| Recovery, offline queue, submit fails | retry without change | **Fail.** Draft `00009` keeps binding, issue time and 232,000 FC net tender; the PC marks the bill synced and stops (§6) |
| Recovery, server unreachable | retry without change | **Pass.** `00010` + one Payment Entry + one stock entry, after a browser restart |
| Lost response, then same-screen retry | no duplicate | **Pass.** One invoice `00011`, one Payment Entry; the retry got `replayed: true` |
| 4 concurrent replays | no duplicate | **Pass.** One invoice `00012`, one Payment Entry, one stock entry; three `replayed: true` |
| Unresolved failures visible to the manager | visible | **Not met.** See §6 |
| B regression (CDF bill paid in USD) | Cash USD $100 | **Fail; outside D-022.** See §8 |

Every saved bill and Payment Entry links its store record (`ruhee_c7_rate`). No saved
amount or rate came from the 9999 Currency Exchange pair, except in B's failure.

## 3. Environment and reproducibility

- **Isolated bench** `/home/dhana/c7bench`, separate from Codex's #24 work:
  - `frappe` and `erpnext` are read-only symlinks to the shared checkouts;
  - `posawesome` and `ruhee_erp` are separate clones, selected with `PYTHONPATH`;
  - own sites folder and asset map (serves the fork's build);
  - private MariaDB 11.8.6 (socket only) and Redis (port 16401);
  - web server on port 8021.

  No shared checkout, site, service or asset was changed.
- **Versions** (`evidence/c7_independent/versions.txt`):
  - Frappe `2fcb9397`, ERPNext `9cd11b19` (both clean);
  - POS Awesome fork `71fcee8`, built bundle `1794004035820`;
  - `ruhee_erp` `bf8e3e9` at setup; `0a17e09` and `22aaa1a` for the browser runs (harness and verifier changes only);
  - Python 3.14.4, Node 24.22.2, Chromium 145 (headless shell).
- **No dependency on PR #20 or `m105.localhost`.** `store_rate_setup.run` builds the
  C7 profile from M1-03's "New Depo" profile, with PR #20's `setup_native` settings
  written out explicitly. It re-runs POS Awesome's own per-payment-currency patch.
- **Test date, not overwriting.** The 9999 company pair is created once, dated the
  test date, on a fresh site, and never edited. Setup refuses to run if a pair for
  that date holds another value. To use 2300 again, use another date or a new site.
- **#24 integration (pending).** The intended sequence:
  1. fresh site at default precision;
  2. M1-03;
  3. Codex's tested #24 revision (precision script), from an isolated combined checkout (a throwaway merge, never pushed);
  4. `store_rate_setup.run`;
  5. the same browser run.

  `formal-run.sh` accepts the #24 step and records every SHA.

## 4. Client: pricing, payment and payload (fork `71fcee8`)

The change is inert unless the POS Profile has the custom check `ruhee_c7_store_rate`.

| Fork file | Change |
| --- | --- |
| `frontend/src/posapp/services/storeRateBinding.ts` (new) | Fetches the record in force (`ruhee_erp.spike.store_rate_hooks.get_store_rate`): name, base, higher, effective time. Keeps the last one in localStorage for offline billing. Binds payloads; stamps the issue time once |
| `frontend/src/posapp/utils/erpnextCurrency.ts` | With a binding, `priceListToSelectedCurrency` and `fromCompanyCurrency` multiply by base; `toCompanyCurrency` divides by base. No reciprocal is used for CDF prices |
| `frontend/src/posapp/services/exchangeRateResolver.ts` | A bound profile's USD/CDF rates come from the record (USD→CDF = base), never from Currency Exchange or cached company rates |
| `frontend/src/posapp/composables/pos/payments/usePaymentCurrencies.ts` | USD bill paid in CDF: CDF due = USD × higher; recorded net CDF covers CDF ÷ higher USD |
| `frontend/src/posapp/components/pos/invoice_utils/document.ts` | Binding (name, base, higher) on every invoice doc; each line's USD basis `ruhee_c7_usd_price` |
| `frontend/src/posapp/composables/pos/payments/usePaymentSubmission.ts` | `buildSubmissionInvoiceDoc` stamps `ruhee_c7_issued_at` on the cart's own doc once, so the online submit, the offline queue, the outbox and the draft fallback all carry the same binding and issue time |
| `frontend/src/posapp/composables/pos/invoice/useInvoiceCurrency.ts` | Refreshes the binding whenever the invoice currency is set, including after each sale |
| `frontend/tests/storeRateBinding.spec.ts` (new) | Six unit tests |

**Observed in the browser:**
- The item selector and cart show FC 230,000 per $100 item, and FC 7,360,000 for the $3,200 item.
- "Price List USD to CDF" shows 2300 where the company rate is 9999.
- A USD bill's Cash CDF row with CDF tender auto-fills 232,000 FC (= $100.00) and 23,200,000 FC for $10,000.
- Each outbound payload carries `ruhee_c7_rate`, `ruhee_c7_base`, `ruhee_c7_higher`, `ruhee_c7_issued_at` with its offset (e.g. `2026-11-07T06:39:42.808+01:00`), and each line's `ruhee_c7_usd_price`.
- Offline bills carry the same fields in the client's IndexedDB `write_queue`. Failed online bills carry them in `invoice_outbox` and the localStorage journal.

**Other conversion paths: inspected, not covered.** The server rejects most of
these for bound bills, and none is claimed:

| Path | State |
| --- | --- |
| Item and invoice discounts, offers, coupons, pricing rules (`PosOffers.vue`, `invoice_utils`) | Client computes them in bill currency; server `check_lines` **rejects** any discount, margin or pricing rule |
| Manual rate edits, locked prices (`_manual_rate_set`, `changePriceListRate`) | Rejected when the line ≠ USD basis × base |
| UOM conversion factor ≠ 1 | USD basis is `original_rate`, assumed per selected UOM: **untested** |
| Returns and item exchanges | `bind_rate` **rejects** returns |
| CDF price lists, or price lists in a third currency | Binding applies only when the price-list currency is USD: **untested** |
| CDF bill paid in USD (B) and mixed tender (F) | B **fails** server-side (§8); F is rejected on a USD bill (one CDF tender only) |
| Change in the other currency (Q2) | Client shows "Change (USD)" for over-tender (240,000 FC case); server rejects. Not built |
| Background submission, `dual_write` and `coordinator` outbox modes | Background off (`posa_allow_submissions_in_background_job=0`); modes untested |
| Receipts, print formats, customer display, Payment Request / M-Pesa, write-off, customer credit, loyalty, gift cards | **Not inspected** |
| Bills created or submitted in Desk | `bind_rate` applies; Desk bills without an issue time cannot be submitted (fail closed) |

## 5. Server: binding validation and effective time

Hooks in `store_rate_hooks.py`. They do nothing unless site config sets
`ruhee_c7_spike: 1` with `pause_scheduler: 1` and the profile is flagged.

- **Missing binding** on a CDF bill or a USD bill paid in CDF is **rejected** (I6).
  This assumes a configured store rate; the Q5 no-rate policy is not decided.
- The record must be submitted, belong to the bill's **company and POS
  Profile/store**, and match the **quotes the bill was priced with**. Otherwise the
  bill is rejected.
- **Applicable rate:** the latest submitted record with `effective_from` ≤ the
  bill-issued time. Two records with the same effective time are a conflict. When
  submitting, a binding that is superseded, not yet effective or in conflict is
  **rejected**. A draft keeps the original binding and amounts, unrepriced, and
  records `ruhee_c7_hold` for the manager.
- **Prices:** `check_lines` (after ERPNext's totals) requires each CDF line =
  `flt(ruhee_c7_usd_price × base)`. It **rejects** discrepancies and never reprices.
  It never reads today's Item Price, so an older offline bill is judged on the USD
  basis it was billed with. *Limitation:* the basis itself is not checked against the
  price list in force at issue time; production needs price history.
- **Rate on the bill:** `conversion_rate = flt(1/base, field precision)`, never from
  Currency Exchange. At 9 places C3-02's base drifts by a cent: #24's domain.
- **C4:** the net CDF tender is folded into `ruhee_c7_tender_cdf`, with allocation =
  CDF ÷ higher, in two places: the HTTP submit override, and `bind_rate` for the draft
  fallback and the SyncCoordinator path. On submit, a separate Payment Entry posts it;
  `value_cdf_received` values CDF received as CDF ÷ base (R7) and sets the Exchange
  income deduction. A net tender worth more than the bill is rejected.

**Three times, kept separate.** Measured on bill A:

| Time | Field | A |
| --- | --- | --- |
| Bill issued | `ruhee_c7_issued_at` (PC clock, ISO 8601 with UTC offset), stamped at the first SUBMIT press and kept through retries and replays; `ruhee_c7_issued_at_local` is the same instant in the site timezone (Africa/Kinshasa) | 06:39:42.808 +01:00 |
| Synchronization | Server receipt: the submission ledger's `creation` (and the Sales Invoice's `creation` for offline bills) | 06:40:54.97 |
| Accounting posting | `posting_date` / `posting_time`, editable; POS Awesome set it at server receipt | 06:40:55 |

For online bills the draft is created when the payment screen opens, so the Sales
Invoice's `creation` can be *earlier* than the issue time (B: 06:41:15 vs 06:41:22).

**Limits, unresolved:**
- The issue time is the PC's clock and timezone setting. The server rejects only gross errors:
  - more than 5 minutes in the future;
  - more than 5 minutes before the bound record existed.
- A client timestamp does not prove authorization or chronology. Ordering across PCs is not provable.
- A PC kept offline on a superseded rate keeps billing at it; the server holds those bills.
- Not decided: who resolves a held bill, and how (re-issue, approve, variance).
- Not decided: whether "issued" should mean the print time.
- Not decided: a clock-sync policy.

## 6. Failure and payment preservation (measured)

Outbox mode is the default **`off`**: no `invoice_outbox_mode` exists in the
browser's IndexedDB `settings` or localStorage (`client_settings.json`). Background
submission is off. The client has **two** recovery mechanisms:

| Path | Where the bill and net payment live | What happened |
| --- | --- | --- |
| Online submit fails | IndexedDB `invoice_outbox` + localStorage journal, written before the request (`usePaymentSubmission.ts:submitInvoice`) | Survived a browser restart. POS Awesome's SyncCoordinator (`offline/sync/resourceRegistry.ts` `invoice_outbox` resource; triggers `online_resume`, `timer`, `user_action`; **in every outbox mode**) resent it to `offline_sync.invoices.submit_invoice_outbox_entry` with the same request ID. Posted `00008` and its Payment Entry. That endpoint bypasses the HTTP override; C4 still posts correctly through the document hooks |
| Offline bill (`write_queue`) | IndexedDB `write_queue` | Network outage: `failed`, kept through a restart, posted when reachable (`00010`). Application failure: `offline/invoices.ts:syncOfflineInvoices` calls `update_invoice`, which saves draft `00009` (binding, issue time, 232,000 FC tender and $100 allocation in its own fields; **no** 9999-valued payment row; no GL; $100 outstanding). Then it marks the entry **`synced`**: the PC stops and the toast says "saved as draft" |

- **Fixed in this PR:** the draft fallback no longer values the tender at 9999. The
  reported 240,000 FC case previously left a $24 Cash CDF row.
- **Pending payment is not shown as posted:**
  - the drafts are docstatus 0 with no GL and their tender in their own fields;
  - the online failure stays on the payment screen with an error.
- **Duplicates:** none for the lost response or the 4-way concurrent replay; one invoice, Payment Entry, GL set and stock entry each. This holds through the client's same-screen retry and the coordinator's resend, both with the same request ID.
- **Gaps, not met:**
  1. after the draft fallback the PC ends recovery (REQ-OFF-02 makes the draft the end state);
  2. an unresolved online failure retries up to five times, then becomes `dead_letter` in `invoice_outbox`, which nothing shows in `off` mode (the badge counts the write queue only, `stores/syncStore.ts:updatePendingCount`);
  3. queued bills show no per-entry status or error in `OfflineInvoices.vue`, and a profile may let the facturier delete them (`posa_allow_delete_offline_invoice`).
- **Client mislabels server validation errors.** A 417 (injected failure, superseded rate, 240,000 FC) is shown as "Connection problem while submitting invoice: Network request failed" (`usePaymentSubmission.ts:buildSubmissionFailureToast`).

Fixing the gaps needs queue-lifecycle changes in the fork, beyond the approved
pricing, binding and payload work. Per instructions, that work was **stopped**. The
smallest additional scope, about 3–4 builder-days:
1. `offline/invoices.ts:syncOfflineInvoices`: keep a bound bill's entry as `held`
   (with the draft's name) after the draft fallback, and retry the submit with the
   same request ID.
2. `offline/writeQueue.ts` and `invoiceOutbox.ts`: tell recoverable failures from
   permanent ones; permanent ones go to `held` at once.
3. `stores/syncStore.ts` and `components/OfflineInvoices.vue`: count and show held and
   dead-letter bills, from both queues, with their error and server draft; no delete
   for held bills.
4. `usePaymentSubmission.ts`: show validation errors as validation errors.

## 7. Layers observed and not observed

- **Observed for every graded bill:**
  - on-screen cart and payment values;
  - the outbound HTTP payload, or the persisted IndexedDB payload for offline bills;
  - the server response;
  - the saved invoice, its lines and payment rows;
  - the store-record link and quotes;
  - Payment Entries and GL by account, stock ledger entries, POS Awesome's submission ledger.

  All saved data was read by `store_rate_verify.py`: reads only, no resubmission.
- **Not observed:** printed bills and receipts (I1); Desk form display; reports
  (AR ageing); customer display; staging versions; two physical PCs; real network loss
  (simulated with Playwright offline mode and aborted requests); clock-skewed PCs;
  background jobs; `dual_write`/`coordinator` outbox modes.
- **Test-only arrangement:**
  - the replacement record was created through the bench, effective 20 s later;
  - the "recoverable" failure is a test-only switch in the submit override (`INJECT_KEY`), fired once;
  - the lost response is Playwright fetching the server's answer and dropping it.

## 8. Regression coverage outside D-022's formal M1 scope

- **B (CDF bill paid in USD): failed.**
  - The client is right: Cash USD $100 = FC 240,000 at the bound 2400.
  - POS Awesome's server normalization (`payment_currency.py:normalize_invoice_payment_currencies`) re-resolves USD→CDF from Currency Exchange.
  - The saved row reads 999,900 FC = $416.63, and the Cash USD GL row has 24.0 in account currency against $100 debit.
  - A fix belongs in `bind_rate` (normalize USD tender on bound CDF bills, R2) and is not made here.
- **F (USD bill, USD + CDF):** rejected by the server ("one CDF tender only"). Not run through the client.
- **CDF bill with mixed tender:** not run. Expected to share B's failure for the USD part.
- **E (later payment of a balance):** not covered.

## 9. Offline-entered rates: Option A (design only, REQ-OFF-04 not implemented)

Confirmed workflow (Sam, 6 Nov): the manager must update **every** offline PC before
further bills use a changed rate, and a rate may stay unchanged for several days.
Existing-server-rate offline tests (this PR) do not prove offline rate registration.

**Local record.** When the manager enters a rate on an offline PC (manager PIN), the
client creates a local rate record in IndexedDB:

| Field | Purpose |
| --- | --- |
| `local_rate_id` | Durable identity: PC id + monotonic counter + random suffix; created once, never reused |
| `company`, `pos_profile`, `store` | Scope, from the profile the PC is bound to |
| `base`, `higher` | Direct quotes as typed; no reciprocal stored |
| `effective_from` (PC time with UTC offset), `entered_at` | When it applies; when it was typed |
| `entered_by`, PIN-verification result, PC id | Authorization and audit |
| `supersedes` | The record (server name or `local_rate_id`) replaced |
| `state` | `local` → `registering` → `registered` (server name) / `conflict` / `rejected` |

**Billing.** A bill binds to the record in force on that PC: a server name or the
`local_rate_id`. It keeps that identity, the quotes it billed with and its issue
time. Amounts are never recomputed.

**Reconnection, in order.**
1. Register each `local` record idempotently, keyed by `local_rate_id`. The server
   stores the mapping `local_rate_id → server record` and returns the same server name
   to every repeat (lost response, retry, two tabs).
2. Only after the mapping is known, sync dependent bills. The server resolves the
   identity through the mapping, checks the quotes and posts the bill as billed.
   **No repricing.**
3. A bill whose record is in `conflict` or `rejected` is held with its original
   amounts for the manager (the hold this PR already uses). It is never posted and
   never deleted automatically.

**Several PCs.**
- *Equivalent* entries (same store and quotes, effective times within a tolerance the
  business sets) register one record. Every `local_rate_id` maps to it, and each
  mapping keeps its own audit.
- *Conflicting* entries (same store, overlapping time, different quotes), or a local
  entry that differs from a server record already in force, become a recorded
  conflict. All dependent bills are held and the conflict is escalated. **Never
  resolved by picking the last upload or the latest PC clock.**

**Chronology.** Effective times come from PC clocks. The server records its receipt
time beside every client time, flags gross clock errors, and treats ambiguous
ordering as a conflict. The manager's PIN entry is the authorization; a client
timestamp alone proves nothing.

**Escalation.** One manager screen lists conflicts and held bills by store and day,
with every entry's audit fields. Resolution choices are business decisions not
taken here.

**Not decided:** Q5, Q1, the equivalence tolerance, and who may resolve conflicts (P3).

## 10. Repository wording that needs reconciliation (not edited here)

1. **REQ-OFF-02** "Any that fail become drafts for the manager" conflicts with the
   confirmed requirement that saving a draft must not silently end recovery, and that
   the payment, binding and request identity survive durably (§6).
2. **R11** "entered by the manager before the first CDF bill" and **REQ-CUR-03**
   "enters two rates at opening" read as a daily entry. Confirmed: a rate may stay
   unchanged for several days, and every offline PC must be updated before further
   bills use a changed rate.
3. **R11** does not say which time selects the rate. This PR uses the bill-issued time
   (ac4b76b used posting time). Issue, synchronization and posting times need defining.
4. **I6:** under Option A an offline bill references a local record until it is
   registered. I6 needs wording for that interval.
5. **R3/R5/R7** say nothing about gross tender. The POS records the **net** payment
   (232,000 FC), and 240,000 FC tendered with 8,000 FC change is handled by hand. This
   is a spike-only clarification; it does not resolve **Q2/R12**. REQ-OFF-06 is
   consistent with it.
6. **§5 Rounding (50 FC):** this spike computes CDF at currency precision only (Q1 open).
7. **AGENTS.md hard rule 10** and card #6's allowed paths conflict with Sam's scoped
   `hooks.py` exception. The exception is recorded in this PR, not in the card or
   DECISIONS.
8. **Card #6** asks for a DECISIONS design note; D-023 keeps DECISIONS closed to this PR.
9. **Gate date:** STATUS says Mon 9 Nov (D-018); issue #9 proposes 12 Nov. Not assumed
   here.

## 11. Deployment boundaries and site artifacts

- #25 and its `hooks.py` references stay **off `main`**.
- A staging deployment needs Sam's specific approval of:
  - the fork pin (`71fcee8` instead of `89ae16d`);
  - the six hook entries;
  - `ruhee_c7_spike` in staging's site config.

  D-024's general fork rule and D-026 do not replace that approval.
- If the code ever reached production, the hooks would stay inert. But every POS
  Awesome submit would still pass through the delegating override (B3).

**Code references (D-025 removal list):**

| `hooks.py` entry | Target |
| --- | --- |
| `doc_events["Sales Invoice"]["before_validate"]` | `ruhee_erp.spike.store_rate_hooks.bind_rate` |
| `doc_events["Sales Invoice"]["validate"]` | `ruhee_erp.spike.store_rate_hooks.check_lines` |
| `doc_events["Sales Invoice"]["on_submit"]` | `ruhee_erp.spike.store_rate_hooks.settle_cdf_tender` |
| `doc_events["Payment Entry"]["before_validate"]` | `ruhee_erp.spike.store_rate_hooks.bind_payment_rate` |
| `doc_events["Payment Entry"]["validate"]` | `ruhee_erp.spike.store_rate_hooks.value_cdf_received` |
| `override_whitelisted_methods["posawesome.posawesome.api.invoices.submit_invoice"]` | `ruhee_erp.spike.store_rate_hooks.submit_invoice` |

The fork also calls the whitelisted `ruhee_erp.spike.store_rate_hooks.get_store_rate`
for flagged profiles.

**Keep or migrate. Never delete as generic cleanup:**

| Artifact | Why |
| --- | --- |
| Custom DocType `Ruhee C7 Store Rate` and its submitted records | Linked from submitted invoices and Payment Entries (I6, I8). Replace by migration |
| Custom fields `ruhee_c7_rate`, `_base`, `_higher`, `_issued_at`, `_issued_at_local`, `_hold`, `_tender_cdf`, `_allocation_usd` (Sales Invoice); `ruhee_c7_usd_price` (Sales Invoice Item); `ruhee_c7_rate`, `_tender_cdf`, `_allocation_usd` (Payment Entry) | Deleting a custom field drops the column and its values in submitted documents |
| POS Awesome per-payment currency fields | POS Awesome's own patch; its code reads them |
| Precision Property Setters | **None created by #25.** #24's, when applied, must stay: removal lets a forced resync narrow columns (#24 review N1) |

**Disposable test data. Never create on staging or production without approval:**

| Artifact | Note |
| --- | --- |
| Currency Exchange USD→CDF 9999 and CDF→USD 1/9999 on the test date | Would poison every document dated that day on a shared site. Created once, never edited |
| POS Profile `C7 New Depo`; `POS Profile.ruhee_c7_store_rate` | Referenced by test bills |
| Store records 2300/2320 and 2400/2420 | Referenced; retire the site rather than delete them |
| Item `C7-UNIT-3200`, its Item Price, the invented Material Receipt | |
| Facturier password and PIN (`sites/<site>/private/c7_secrets.json`, mode 600), POS Opening Shift | Never in the repo |
| All test invoices, Payment Entries and held drafts | Retire with the site |
| Site config `ruhee_c7_spike`, `pause_scheduler`; cache key `ruhee_c7_inject_submit_failure` | Guards and the test-only switch |

## 12. Production estimate (builder-days)

Assumes the 6 Nov clarifications hold, and that Q1, Q2, Q5 and Q6 are answered first.

| Area | Days | Notes |
| --- | --- | --- |
| Fork client, production quality | 4–6 | Rate display, refresh and per-bill freeze, repricing before issue, IndexedDB cache, discounts, manual rates, offers, UOM, returns and exchanges made consistent with the direct quote, receipts and prints (I1) |
| Server rate model, selection, validation, payment orchestration | 3–5 | Replaces the spike hooks; C4, E and F Payment Entries; B's USD-tender valuation |
| Durable failure recovery (fork queue lifecycle) | 3–5 | §6 scope plus manager-visible held bills |
| Offline rate registration (Option A) | 4–6 | |
| Effective time, clocks and conflicts | 2–3 | |
| Permissions | 1–2 | Rate entry, cashier-created Payment Entries, held-bill resolution (P3) |
| Precision fixtures | 0.5 | Integration only; #24 owns the widening and its fixtures; not double-counted |
| Automated tests (AUT-CUR, AUT-RATE, AUT-OFF) | 3–4 | |
| **Total** | **20.5–31.5** | |

**Excluded:** this spike; #24; returns (R13–R17); Q-dependent rounding and change;
staging deployment and the two-PC 24-hour soak (about 2–3 days, mostly Sam's time);
review (4–6 reviewer-days). This replaces #25's earlier 9–13 days, which excluded
offline rate registration, recovery lifecycle work and fork-wide conversion
consistency.

## 13. Found, not done

- B regression and its inconsistent Cash USD GL row (§8).
- Client shows server validation errors as network failures (§6).
- Client shows "Change (USD)" for over-tender on a USD bill paid in CDF (Q2).
- SyncCoordinator outbox sends bypass the HTTP submit override. The test-only failure switch lives in the override, so it never fires on that path.
- A facturier may delete queued bills when `posa_allow_delete_offline_invoice` is set.
- POS Awesome sets posting time at server receipt, not issue (§5).
- Fork full vitest suite: 1,210 of 1,211 passed. `itemsSelectorStockWiring.spec.ts` hit its 5 s timeout under full-suite load; it passes 3/3 alone, with and without this change.
- Upstream already fails Prettier on five of the touched fork files. They were left as they were to keep the diff minimal; only the new file is formatted.
- Fresh browser profiles need minutes to load the item catalogue; the harness waits for it.
- The WSL clock jumped about 2 h during one dev run. Effective-time arrangement uses server-relative times.

## 14. Reproduce

```bash
# isolated bench: ./c7 = PYTHONPATH=<fork clone>:<ruhee_erp clone> python -m frappe.utils.bench_helper frappe (cwd sites/)
./c7 new-site <site> --db-socket <private socket> --db-root-username <user> --db-root-password <pw> --admin-password <pw>
./c7 --site <site> set-config ruhee_c7_spike 1 --parse
./c7 --site <site> set-config pause_scheduler 1 --parse
./c7 --site <site> install-app erpnext && ./c7 --site <site> install-app posawesome && ./c7 --site <site> install-app ruhee_erp
./c7 --site <site> execute ruhee_erp.spike.setup_spike.run          # M1-03
# (pending) Codex's tested #24 precision revision here
./c7 --site <site> execute ruhee_erp.spike.store_rate_setup.run
cd <fork>/frontend && npx vite build                                  # fork bundle, served from the isolated sites/assets
./c7 --site <site> serve --port 8021 --noreload --nothreading
PW_MODULE=<fork>/frontend/node_modules/playwright/index.mjs SITE=<site> PORT=8021 OUT=<dir> \
  SECRETS=<bench>/sites/<site>/private/c7_secrets.json C7_RUNNER=<bench>/c7 \
  node ruhee_erp/spike/c7_browser.mjs c3_01 c3_02 c4 c4_large c5 line_3200 diag_240k \
  b_cdf_bill_usd_tender recovery_online recovery_offline_draft recovery_network \
  lost_response concurrent_replay effective_time client_settings
./c7 --site <site> execute ruhee_erp.spike.store_rate_verify.from_harness --kwargs '{"results_dir": "<dir>"}'
./c7 --site <site> execute ruhee_erp.spike.store_rate_verify.precision_state
```

Headless Chromium 145: `PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64 npx playwright
install chromium-headless-shell`. On this Ubuntu 26.04 WSL host, `libasound.so.2` is
supplied with `LD_LIBRARY_PATH`. `effective_time` must run last, because it installs a
2400/2420 replacement.

## 15. Installed source consulted

- **POS Awesome (fork clone, `89ae16d` base):**
  - `frontend/src/posapp/utils/erpnextCurrency.ts`
  - `composables/pos/items/useItemCurrency.ts:applyCurrencyConversionToItem`
  - `composables/pos/invoice/useInvoiceCurrency.ts:update_currency_and_rate/update_item_rates`
  - `services/exchangeRateResolver.ts:resolveExchangeRate`
  - `composables/pos/payments/usePaymentCurrencies.ts:normalizePayment/setInvoiceEquivalent`
  - `usePaymentSubmission.ts:buildSubmissionInvoiceDoc/submitInvoice`
  - `components/pos/invoice_utils/document.ts:get_invoice_doc/get_invoice_items`
  - `invoice_utils/server.ts:update_invoice`
  - `components/pos/employee/EmployeeSwitchDialog.vue`
  - `offline/invoices.ts:syncOfflineInvoices`
  - `offline/invoiceOutbox.ts:persistInvoiceIntentJournal/enqueueInvoiceOutboxEntry/syncInvoiceOutboxResource`
  - `offline/writeQueue.ts:claimRetryableQueueEntries/markWriteQueueEntrySynced/markWriteQueueEntryFailed/getQueueEntries`
  - `offline/sync/resourceRegistry.ts`, `offline/sync/resourceRunner.ts`
  - `offline/db.ts:isOffline/persist`
  - `stores/syncStore.ts`
  - `components/OfflineInvoices.vue`
  - `posawesome/api/invoice_processing/creation.py:update_invoice/_resolve_payment_amounts/_reapply_incoming_payment_amounts`
  - `posawesome/api/payment_currency.py:normalize_invoice_payment_currencies`
- **ERPNext:** `accounts/doctype/payment_entry/payment_entry.py:validate/set_amounts/set_amounts_in_company_currency/set_exchange_gain_loss/set_difference_amount/add_bank_gl_entries`.

## History

`store_rate_probe.py`, `store_rate_results.json`, `store_rate_readback.json` and
`store_rate_native_control.json` are the ac4b76b evidence. They were hand-built with
the answer in the payload (review B1), ran on `m105.localhost` with PR #20's 12-place
columns, and are kept unchanged as history. The probe now refuses to run.
