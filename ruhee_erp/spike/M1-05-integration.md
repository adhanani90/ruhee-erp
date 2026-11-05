# M1-05 audit, integration gap and proposed implementation

Owner Codex; reviewer Claude Code. Draft PR #20 remains a feasibility investigation.
Reconciled against merged PRs #19, #22 and #23 on 2 Nov; corrected 5 Nov 2026.
This note does not authorize deployment or claim POS/offline acceptance. C3 remains
**failed** as in [merged PR #19](https://github.com/adhanani90/ruhee-erp/pull/19);
[scratch findings and the proposed follow-up](M1-05.md#measured-results) supplement
the native failure. Formal re-proof is proposed for M1-04 follow-up #5 after
staging is ready, replacing the M1-05/before-9-Nov condition; Sam's explicit
agreement in #20 remains pending. C4 **workaround proposed; server
harness only**. C7's final result belongs to #8; online laboratory evidence is in
the [design report](M1-05.md#design-report-online-store-rate-harness). Correct GL
in a bench harness is narrower evidence than a working facturier/sync path.

## 1. Creation, restoration and database authentication

I supplied these commands for Sam to run in his terminal; **I did not execute
site creation/restore or observe his terminal authentication**:

```bash
cd ~/frappe-bench
bench new-site m105.localhost
bench --site m105.localhost set-config pause_scheduler true
bench --site m105.localhost restore ~/frappe-bench/sites/dev.localhost/private/backups/20261031_011624-dev_localhost-database.sql.gz
```

Sam reported the site restored and paused. The installed CLI defaults its database
administrative username to root when no override is provided. I cannot confirm
whether Sam actually used a root password, socket authentication, another username,
or additional local flags; there is no terminal transcript in this session. No
root password was supplied to me, placed in a tool command or copied into the repo.

Subsequent bench execute/migrate commands used scratch's configured database
connection, with no --db-root-* options or root credential. A new read-only
`CURRENT_USER()` check confirms that connection is **not root**:
[audit](evidence/m105_readonly_precision_check.json). This does not establish the
authentication method used during the earlier manual restore.

The following distinct commands were executed by Codex after Sam's ready message,
in this order (several read-only checks were repeated). Helpers have an internal
m105-only guard; native and prototype runs make **new invented bills**, not retries:

```bash
bench --site m105.localhost execute --help
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.inspect
bench --site m105.localhost execute frappe.get_all --kwargs '{"doctype":"Company","fields":["name","default_currency"]}'
bench --site m105.localhost list-apps
bench --site m105.localhost execute frappe.db.count --args '["Sales Invoice"]'
bench --site m105.localhost execute ruhee_erp.spike.setup_spike.run
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.inspect
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.setup_native
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.run_native
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.inspect_precision --kwargs '{"old_invoice":"ACC-SINV-2026-00002"}'
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.set_precision
bench --site m105.localhost migrate --skip-search-index
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.inspect_precision --kwargs '{"old_invoice":"ACC-SINV-2026-00002"}'
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.run_native --kwargs '{"label":"invoice_only_12"}'
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.payment_rounding_probe
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.set_precision --kwargs '{"scope":"chain"}'
bench --site m105.localhost migrate --skip-search-index
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.refresh_scratch_reciprocal
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.inspect_precision --kwargs '{"old_invoice":"ACC-SINV-2026-00002"}'
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.run_native --kwargs '{"label":"full_chain_12"}'
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.synchronize_precision_columns
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.inspect_precision --kwargs '{"old_invoice":"ACC-SINV-2026-00002"}'
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.refresh_scratch_reciprocal
bench --site m105.localhost execute ruhee_erp.spike.cross_currency.run_native --kwargs '{"label":"synced_chain_12"}'
bench --site m105.localhost execute ruhee_erp.spike.store_payment_prototype.setup
bench --site m105.localhost execute ruhee_erp.spike.store_payment_prototype.run
bench --site m105.localhost execute ruhee_erp.spike.store_payment_prototype.verify_existing
bench --site m105.localhost execute ruhee_erp.spike.precision_checks.run --kwargs '{"expected_site":"m105.localhost","expected_precision":12,"invoice":"ACC-SINV-2026-00002"}'
```

An earlier syntax check was `bench --site dev.localhost restore --help`: **help
only**, with no restore or dev database connection. `bench new-site --help` and
`bench --site m105.localhost migrate --help` were also help-only reads.

Also executed: source/doc/git reads; a read-only gzip
inspection of the named backup for Company/Sales Invoice INSERTs; Ruff/AST/JSON
checks; git commits/pushes on #6; GitHub draft PR updates. These do not change dev
business configuration/precision/data. No command in #6 targeted dev's database,
read its site_config or synchronized/retried its queued bill. **I made no dev
config, precision or data changes during #6.** I have not taken before/after dev
checksums or queried it to certify unrelated activity; this is a scoped action
audit, not a claim that no other actor changed dev. #5's earlier intentional test
changes are outside this statement; its branch/PR has not been changed by #6.

## 2. Empty backup and equivalence

The SQL artifact has no Company/Sales Invoice INSERTs; the restored scratch had
zero of both. That proves its business setup was absent, **not why**. Its content
is consistent with a pre-business-setup snapshot; I do not have provenance proving
why this timestamped backup lacks the M1-03 data. No current dev comparison was
performed, and the filename alone cannot establish that history.

M1-03 seeding reproduced the intended invented business baseline (company, items,
prices, drawers, customers, rates and profile) from the same script. **It did not
prove full equivalence to dev.** Historical invoices, patch state, permissions,
settings, keys/sessions, caches and compiled browser assets were not compared.
After the experiments scratch deliberately differs further: new feature schema,
12-place fields, profiles, fake bills, store records and company rate 9999. Do not
treat it as a current dev clone or an end-to-end restored #5 acceptance environment.

## 3. DRAFT, not approved — submission and payment integration

This relocates and revises PR #20's former DECISIONS proposal. It is **DRAFT, not
approved or implemented**; it selects no production hook, migration, setting or
fork change and does not authorize P2 money work. Keep one authoritative USD price
list and immutable exact direct store quotes. The compatibility precision and
migration proposal is in §5; the planning estimate and future regressions are in
§6. No Frappe/ERPNext edit is proposed.

### Current adapter and exact C4 evidence

`store_payment_prototype.py:run` constructs a credit invoice, calls native
update/submit, then explicitly calls `payment`. `store_rates` patches two resolvers
only inside that process. No hook or UI/submit/sync registration exists. The
status remains **workaround proposed; server harness only**. Recorded C4 PE GL:
Dr Cash CDF **232,000 FC = $100.87**, Cr Debtors **$100.00** (balance −$100),
Cr Exchange income **$0.87**. See [actual extracts](evidence/m105_store_prototype.json).
The two open items are **missing POS integration** and **Payment Entry replay
protection**. `payment` sets `reference_no` to the opening shift, not a payment
operation ID. Its invoice/rate links do not prevent duplicate PEs. AUT-OFF-01
has not been run or passed for this adapter.

### Store-rate binding gap

At POS Awesome `89ae16d`, `invoice_processing/creation.py:_submit_invoice_once`
calls the local `update_invoice` when creating a new invoice (around line 2011).
`update_invoice` calls `invoice_processing/utils.py:resolve_erpnext_currency_rates`
with the invoice's posting date (around lines 1647–1671), then assigns the result
to `invoice_doc.conversion_rate`. The resolver's `get_latest_rate` looks up
Currency Exchange by currency pair/date; it does not read our store record.
Supplying a store rate in the incoming invoice therefore does not bind the saved
rate through this path. This affects online submission as well as replay, not
only sync. The existing-draft branch instead updates the document from the
payload; early replay returns can skip creation entirely, so each path needs proof.

`store_payment_prototype.py:store_rates` uses `unittest.mock.patch.object` to
replace `creation.resolve_erpnext_currency_rates` and `payment_currency._resolve_rate`
inside the harness context, restoring them on exit. That is how 00009 uses the
explicit store record despite company rate 9999. It is **not a production
integration**: no app hook registers it, other processes/workers do not inherit it,
and a module-global replacement is not isolated to concurrent requests. It proves
the selected calculations only under controlled laboratory orchestration.

An HTTP `submit_invoice` wrapper that simply supplies a rate and delegates still
reaches this internal overwrite. Likewise, Frappe
`frappe/handler.py:execute_cmd` applies `override_whitelisted_methods` at HTTP
dispatch; overriding the HTTP `update_invoice` endpoint does **not** intercept
`_submit_invoice_once`'s direct Python call. A production replacement must bind
the immutable store-record identity and direct quotes through draft creation,
validation, submit, worker and replay, and keep line/tender/base amounts consistent.

Candidate mechanisms, **all unverified and none selected or implemented**:

| Candidate | Open mechanism and required proof |
| --- | --- |
| Sales Invoice `doc_events.before_validate` | Frappe `Document.run_before_save_methods` invokes it for save/submit. Whether it runs at the right point to restore the bound rate and recalculate all dependent amounts before every later normalization/validation is **unverified**. Prove new/existing drafts, sync and worker paths; an `on_submit` handler alone is too late to establish invoice valuation. |
| `update_invoice` override or wrapper | An HTTP override alone misses the internal call. A supported way to cover both external draft saves and internal submission calls without runtime patching is **unverified**; demonstrate actual dispatch coverage before selecting this approach. |
| Minimal POS Awesome fork under D-024 | A separately approved change could delegate rate binding to an app service at the internal resolution boundary. Exact extension point, ordering and coverage are **unverified**; requires Sam's approval, a dated decision and the fork change/review rules, not authorization from this spike. |

Required future proof: compete with a different company/date rate, retain the
original store snapshot across rate changes and replay, and assert exact saved
line/tender/GL values for new/existing drafts and background work (C3–C5, C7,
R11, I6/I8, AUT-RATE-01..06 and AUT-OFF-01). No such integration test was run.
This gap is included in §6's **2–3 builder-day direct-rate service** line within
the **8–12 day total**, not a completed prerequisite or a separate estimate.
If no candidate covers these boundaries, reassess that estimate before committing
to implementation; the successful runtime patch does not retire this work.

### Verified submission routes

Source inspection only, at POS Awesome **89ae16d872e90727086b2550d7ca97958c9c4aa4**.
Paths beginning `frontend/` and `posawesome/` below are relative to that repository.
Frappe references are from installed **2fcb939**. No browser mode or site setting
was inspected, and no database experiment was run for this revision.

| Route/mode | Source file:function and dispatch |
| --- | --- |
| Online Sales Invoice | `frontend/src/posapp/services/invoiceService.ts:getSubmitInvoiceCall/submitInvoice` calls `posawesome.posawesome.api.invoices.submit_invoice`. `posawesome/posawesome/api/invoices.py` re-exports `invoice_processing/creation.py:submit_invoice`. |
| `off` (source default) | `frontend/src/offline/db.ts` initializes `invoice_outbox_mode="off"`; `invoiceOutbox.ts:getInvoiceOutboxMode` falls back to `off`. `frontend/src/offline/invoices.ts:syncOfflineInvoices` calls the same HTTP submit endpoint as online. |
| `dual_write` | `invoiceOutbox.ts:shouldWriteInvoiceOutbox` and `invoices.ts:saveOfflineInvoice` also write an outbox copy. `invoices.ts:syncOfflineInvoices` branches only on `coordinator`, so `dual_write` uses the same default HTTP submit path as `off`. This describes that dispatcher, not a runtime proof of all queue interactions. |
| `coordinator` | `invoices.ts:syncOfflineInvoices` calls `invoiceOutbox.ts:syncInvoiceOutboxResource`, which calls `posawesome.posawesome.api.offline_sync.invoices.submit_invoice_outbox_entry`. `posawesome/posawesome/api/offline_sync/invoices.py:submit_invoice_outbox_entry` normalizes request identity, enters `trusted_invoice_shift_reassignment`, and calls its imported `creation.py:submit_invoice` directly with `submit_in_background=0`. |

One HTTP override is a candidate for online plus `off`/`dual_write` replay, not
proof of completed invoice/payment integration. `frappe/handler.py:execute_cmd`
applies `override_whitelisted_method` to HTTP dispatch; it does not intercept the
coordinator's internal Python call. Mode selection and real replay proof belong
to M1-07 (#8). **The design and estimate assume replay in `off` mode** through the
same HTTP endpoint as online billing; this planning assumption is not an approved
mode selection or runtime acceptance. `setInvoiceOutboxMode` has no caller in the
inspected `frontend/src` tree; no browser's persisted mode was checked.

### Background submission and acknowledgement

`invoiceService.ts:getSubmitInvoiceCall` passes `submit_in_background` from
`POS Profile.posa_allow_submissions_in_background_job`. In
`creation.py:_submit_invoice_once`, the request flag and the server profile's
`allow_background_submit` gate cause `enqueue(submit_in_background_job,
enqueue_after_commit=True)` around line 2170. It returns the saved draft identity
and docstatus before the worker submits it. An HTTP wrapper that assumes the
returned invoice is submitted therefore cannot simply create its PE at that point.
Default replay supplies no background flag; coordinator explicitly supplies zero.

Alternatives to investigate, **none selected**: export the background setting as
off in an app-owned fixture and verify the server gate; use document-level hooks
for submission timing; or use durable worker-aware orchestration with completion
tracking. A response naming a draft or queued job must not acknowledge completed
payment. Test queued response, worker success/failure, lost notification and reload
before claiming completion (proposed background-acknowledgement test; not run).

### Sales Invoice on_submit alternative: source-only assessment

New synchronous submissions reach `invoice_doc.submit` through
`creation.py:_submit_invoice_once` around line 2193; background submissions call it
in `submit_in_background_job` around line 2362. Coordinator uses the synchronous
route. Native replay may return an already submitted invoice without submitting
again. Frappe `frappe/model/document.py:Document.run_post_save_methods` invokes
`run_method("on_submit")`; `Document.run_method/Document.hook` runs the controller
method followed by `doc_events` handlers. This supports investigating one Sales
Invoice hook across these modes, without choosing it.

| Question | Source-based assessment and required confirming test |
| --- | --- |
| Does it fit the separate PE? | **Unverified.** An on_submit handler could invoke an adapted PE service after the core invoice GL exists. The current `store_payment_prototype.py:payment` uses `get_payment_entry`, insert and submit with no explicit commit. It is not a drop-in hook: original tender, allocation, rate identity and stable payment ID must be persisted on the invoice, and incompatible inline CDF cash posting must be removed before core submission. The core controller runs before the app handler, so on_submit alone cannot fix native C4's earlier account-currency failure. Confirm with a proposed hook-fit C4 test (AUT-CUR-03): submit through each mode, assert exact SI/PE GL, allocation, print data and permitted user context. Not implemented/run. |
| Same transaction as invoice submit? | **Unverified.** A synchronous handler runs on the same Frappe connection during submit; `Document.hook` disables transaction control while invoking handlers. A PE created without an independent commit is a candidate to share the invoice submission transaction, including the worker's submission transaction. The background draft was saved in the earlier HTTP transaction. Nested accounting/notification code and subsequent post-submit work still require rollback proof. Confirm with a proposed transaction-failure test: inject failure before/after PE insert/submit, and after the hook, in synchronous and worker paths; assert no partial submitted SI/PE/GL/SLE survives rollback and recovery retains the draft/intent. Not implemented/run. |
| How would replay idempotency work? | **Unverified.** `creation.py:_submit_invoice_once` can return from `_ledger_final_replay_response` or an existing submitted invoice before any on_submit hook runs; `submit_in_background_job` also returns early for docstatus 1. The invoice ledger does not protect our separate PE. Require a database-unique scoped payment-operation ID, immutable payload hash, locked state and stored SI/PE references. Completed replays return the same PE; incomplete work needs an explicit recovery path rather than re-submitting the invoice to rerun its hook. Confirm with proposed sequential/concurrent/lost-response/crash/reload tests (AUT-OFF-01), including worker redelivery and an existing submitted SI with incomplete PE state. Not implemented/run. |

The hook remains a candidate combined with pre-submit payload preparation and
recovery orchestration. It is insufficient as an on_submit-only replacement; no
production extension is approved. If supported app hooks/wrappers cannot cover
these boundaries, a separately approved minimal POS Awesome fork could delegate
to the same app service. Backend accounting remains in ruhee_erp.

### Recovery requirements retained in every candidate

`invoices.ts:syncOfflineInvoices` catches default-path submit errors, calls
`posawesome.posawesome.api.invoices.update_invoice` to save a draft, then calls
`markWriteQueueEntrySynced` (around lines 342–356). This also applies to
`dual_write` in this dispatcher. Recovery must retain visible unfinished
invoice/payment work after that fallback, distinguish drafted from paid, and
preserve the original operation identity across retry. A proposed fallback test
must fail submission, observe the saved draft and queue acknowledgement, then
recover one invoice and one PE without duplicate stock/GL. Not implemented/run.

Native `creation.py:_submission_ledger_key/_get_or_create_submission_ledger`
scopes invoice identity by request/company/profile/doctype. It does not establish
uniqueness of this separate PE. Proposed durable state scopes bill/payment keys
by company/store/profile, checks permissions before replay, rejects changed
payloads under used IDs and stores SI/PE references. Test native early returns,
partial completion and closed-shift recovery before any paid acknowledgement.
Prefer one transaction where possible; actual boundaries remain unverified.

## 4. Exact direct rate versus reciprocal

The harness **hard-codes the invented test inputs when creating the record**:
`run` inserts submitted `Ruhee Spike Store Rate` `5otibkapm6` with base=2300 and
higher=2320. Calculation functions then read `record.base` / `record.higher` and
documents retain that record link; they do not independently substitute company
rate 9999. A later 2400/2420 record tests history. This is explicit record binding,
not a proved manager-entry/effective-time/store-selection workflow.

The source record stores the direct exact integer quotes, **not their reciprocal**.
But the compatibility arithmetic is still reciprocal-based:
`store_rates.invoice_rates` sets SI conversion_rate to flt(1/base,12), and
`payment` sets PE target_exchange_rate likewise (or deliberately nine places in
the counterexample). These are finite approximations, **not the exact rate**.
The successful example GL does not prove exact valuation at all amounts.

For production, base/higher direct quotes and immutable record identity must be
authoritative. Derive FC demand with USD x higher and value cash with CDF / base,
rounding only monetary results with Frappe precision. Derive reciprocals only as
ERPNext compatibility fields; verify native computed amounts equal the direct
calculation before submit. If they differ, fail safely with a retained draft/
pending operation until a verified direct-calculation adapter is available. Do
not invent compensating GL or change historical rates. The current harness does
not implement that general direct-arithmetic guarantee or a supported-amount bound.

## 5. Exact tested precision fields and proposed shipment

All six below were widened to **decimal(21,12)** in the successful scratch
experiment. This is the tested configuration, not proof each field is minimally
necessary in every route (USD PE source rate is 1); the shared paths need auditing.

| DocType / table | Column |
| --- | --- |
| Sales Invoice / tabSales Invoice | conversion_rate |
| Currency Exchange / tabCurrency Exchange | exchange_rate |
| Sales Invoice Payment / tabSales Invoice Payment | posa_exchange_rate |
| Sales Invoice Payment / tabSales Invoice Payment | posa_company_exchange_rate |
| Payment Entry / tabPayment Entry | source_exchange_rate |
| Payment Entry / tabPayment Entry | target_exchange_rate |

USD-price-list plc_conversion_rate stays 1 in these tests. No POS Invoice precision
change is proposed: C2 uses Sales Invoice mode. Direct base/higher source fields
are distinct from these compatibility columns and must retain entered quote
precision; increasing reciprocal scale is not a replacement for exact direct rates.

Proposed production PR: export these precision Property Setters as ruhee_erp
fixtures (no upstream edit), then a versioned/idempotent app patch plus ordered
post-fixture/after-migrate schema synchronization using Frappe `updatedb` and final
fresh metadata. Assert metadata and real DB types after **every** migrate. The
ordinary scratch migrate left three columns at 9 despite metadata=12, so fixture
alone is not accepted. Test the second migrate too. Choose deployment ordering
only after that proof; no production hook/patch is included in PR #20.

Preserve old recorded rates/documents/GL. Create new effective rate records from
direct quotes rather than updating an old used record or padding lost digits;
refresh client caches by rate identity. Assess the loss of integer capacity at
width 21 and binary-float error against supported bill/tender maxima. The scratch
helper that overwrote its disposable Currency Exchange rate is **not** the
production R11 migration method.

Proposed staging checks, **not executed or authorized by this note**. See D-021
for the existing staging restriction. First deploy the
approved metadata/schema/integration change; current PR #20 alone does not install it.
The read-only checker below exists in this PR and refuses dev/cc.

```bash
M105_STAGING_SITE='confirmed-staging-hostname'
# Before migration: capture the old invented invoice's accounting_sha256.
bench --site "$M105_STAGING_SITE" execute ruhee_erp.spike.precision_checks.run --kwargs "{\"expected_site\":\"$M105_STAGING_SITE\",\"invoice\":\"OLD-SPIKE-INVOICE\"}"
# After approved integration/fixtures/patches are deployed:
bench --site "$M105_STAGING_SITE" migrate
bench --site "$M105_STAGING_SITE" execute ruhee_erp.spike.precision_checks.run --kwargs "{\"expected_site\":\"$M105_STAGING_SITE\",\"expected_precision\":12,\"invoice\":\"OLD-SPIKE-INVOICE\"}"
# Re-run migrate and the same check: columns stay at 12, old hash unchanged.
bench --site "$M105_STAGING_SITE" migrate
bench --site "$M105_STAGING_SITE" execute ruhee_erp.spike.precision_checks.run --kwargs "{\"expected_site\":\"$M105_STAGING_SITE\",\"expected_precision\":12,\"invoice\":\"OLD-SPIKE-INVOICE\"}"
# Once the production AUT cases are implemented, run them as part of the app suite.
bench --site "$M105_STAGING_SITE" set-config allow_tests true
bench --site "$M105_STAGING_SITE" run-tests --app ruhee_erp
```

The suite must include C3/C4 large amounts/direct-rate controls, old/new invoice
and PE saved values, two-rate history, UI-created tenders and AUT-OFF-01 concurrency/
failure replay. Replace OLD-SPIKE-INVOICE only with an invented control that receives
no new allocations during the before/after comparison. A schema check is not a GL,
frontend or replay test; current production AUT coverage is not claimed.

## 6. Estimate and fallback

**Planning input for M1-11, not authorization for P2.** Keep **8–12 builder-days**
as the single estimate, assuming online billing plus offline replay in **`off`
mode**, both through `posawesome.posawesome.api.invoices.submit_invoice`.
Default replay's draft fallback, background submission, unresolved store-rate
binding and PE idempotency still require work. Sharing an HTTP endpoint reduces
route count, but does not justify reducing this estimate. If M1-07 (#8) selects
another mode, reassess coverage and effort; `dual_write` and `coordinator` are
source comparisons, not proven modes within this estimate.

**Estimate: 8–12 focused builder-days**, one owner, including AUT work; an additional
1-2 reviewer-days and at least a 24-hour two-PC offline soak are separate elapsed
dependencies. This is a planning estimate, not measured velocity or a promise.

| Work | Builder-days |
| --- | --- |
| Exact direct-rate service, validated record selection, binding across `update_invoice` and durable invoice/PE orchestration | 2-3 |
| POS tender/rate snapshot, common online/`off` replay routing, replay identity and recovery | 3-4 |
| Ordered precision migration, repeated-migrate/old-data and amount-bound tests | 1-2 |
| AUT currency/rate/offline, cashier permissions, UI/printing and two-PC fixes | 2-3 |

These total **8–12 cumulatively** for online plus `off` replay, including binding,
background and fallback investigation. A different mode, extension coverage and a
possible fork are risks to this planning estimate, not separate approved scopes.
Unproven: effective-time/store selection, role permissions,
exact direct arithmetic across supported amounts, schema persistence, real UI
payloads/prints, cached rates, split payments, replay/concurrency/crash boundaries,
closed shifts, returns and offline recovery.
Future P2 regressions (not work performed or implemented in #6):
AUT-CUR-01/03/04/05/06/10/12/14 (14 awaits Q1), AUT-RATE-01..06,
AUT-OFF-01..04 and relevant AUT-PERM-03/06/07. Under D-022, examples B, E and F
remain unproven in M1 and assigned to P2 (AUT-CUR-02/05/06).
Q6 gates production money work; Q1/Q2/Q5 paths remain gated rather than invented.

If extension routing fails, a minimal reviewed POS fork delegating to the same
app service is an option requiring separate approval, a dated DECISIONS entry
and AUT coverage. If exact direct/native
amount equality fails, do not ship precision-only arithmetic: prototype the direct
backend calculation with explicit amount limits and repeat GL/large tests. If
replay cannot guarantee one SI/PE, keep CDF-on-USD queued/draft with visible failure,
never acknowledge it as paid or silently retry another payment. A proposed interim
supervised online-only Payment Entry workflow needs Sam's explicit scope decision;
it is not an automatic fallback. If those paths miss M1, report no-go/limited scope
to Sam; preserve old-system/paper operation rather than claim offline readiness.
