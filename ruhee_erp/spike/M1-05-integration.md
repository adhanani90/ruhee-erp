# M1-05 audit, integration gap and proposed implementation

Owner Codex; reviewer Claude Code. Draft PR #20 remains a feasibility investigation.
This note does not authorize deployment or claim POS/offline acceptance. C3 **fail
(precision)**; C4 **workaround proposed**; C7 **partial**. Correct GL in a bench
harness is narrower evidence than a working cashier/sync path.

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

## 3. Adapter wiring and AUT-OFF-01

**Current:** server-side bench harness only. Existing
`ruhee_erp/spike/store_payment_prototype.py:run` constructs a credit invoice payload,
calls POS Awesome update/submit, then explicitly calls `payment`. `payment` builds
and submits a Payment Entry. `store_rates` patches two resolver functions only
inside that Python process. Nothing is registered in hooks.py; there is no client
implementation and no facturier UI route to this adapter. A normal online or
offline-queued bill does **not** automatically pass through it.

The harness's `Payment Entry.references` links the invoice and
`ruhee_spike_rate` links the rate; `reference_no` contains the opening shift.
**None is a unique invoice request identity.** The harness does not pass a
client_request_id, set a PE idempotency key, enforce a unique payment operation or
handle replay. AUT-OFF-01 has not been run or passed. Allocation validation is not
duplicate protection; no guarantee against a second PE is claimed.

Source paths for a production integration, **not implemented**:

- UI tender capture:
  `frontend/src/posapp/composables/pos/payments/usePaymentCurrencies.ts:usePaymentCurrencies.updateOriginalAmount/normalizePayment`
  populates original CDF tender; `components/pos/invoice_utils/document.ts:get_payments`
  carries payment currency/amounts. It must additionally freeze the exact store
  record identity/base/higher, USD amount allocated and a stable payment-operation
  identity in the same submission intent, without replacing USD price authority.
- Online dispatch:
  `frontend/src/posapp/services/invoiceService.ts:submitInvoice`; intent persistence
  `composables/pos/payments/usePaymentSubmission.ts:usePaymentSubmission`.
  Its normal endpoint is `posawesome.posawesome.api.invoices.submit_invoice`.
- Outbox:
  `frontend/src/offline/invoiceOutbox.ts` dispatches to
  `posawesome/posawesome/api/offline_sync/invoices.py:submit_invoice_outbox_entry`,
  which normalizes client_request_id and directly calls the imported
  `invoice_processing/creation.py:submit_invoice`.
- Native request ledger:
  `creation.py:_submission_ledger_key/_get_or_create_submission_ledger/_submit_invoice_once`
  scopes identity to request/company/profile/doctype and can return an existing
  submitted invoice early. That does **not** automatically make our separate PE
  complete or idempotent. Existing payment-request helpers in `api/idempotency.py`
  and `payment_processing/processor.py:process_pos_payment` are separate machinery,
  not used by this harness.
- Frappe `frappe/handler.py:execute_cmd` applies a whitelisted-method override to
  an incoming HTTP command. It does not rewrite the outbox function's internal
  Python import. Overriding only the online submit endpoint is therefore not proof
  that offline replay enters the same adapter.

Proposed backend: one app-owned submit orchestrator shared by online and outbox
routes. It validates the submitted rate reference/tender, preserves tender data
for recorded printing, routes the CDF portion out of incompatible inline cash
posting, submits the invoice and linked PE, and acknowledges only completed work.
Use supported app hooks/wrappers if both entry points can be covered; otherwise
make one minimal POS Awesome fork change to delegate both paths to that app
service. Backend accounting belongs in ruhee_erp. Frontend/outbox rate/intent work
likely needs a POS fork unless a supported extension is proved. **Neither path is
currently implemented or verified.** No Frappe/ERPNext fork is proposed.

Proposed replay contract (schema/API names to be decided in the implementation
card): immutable bill request identity + stable per-CDF-payment operation ID,
scoped by company/store/profile, frozen into the queued payload. Server operation
record and/or PE business key must have a **database unique constraint**, with a
locked operation row, payload hash and stored SI/PE references. Replays return
those same documents; changed tender/rate under the same identity is rejected.
Do not rely on a pre-insert lookup alone. Scope and permission checks precede
replay; a key must not disclose another store's documents.

The operation must handle the native invoice ledger's early-return states and
recovery between SI and PE. If a native path commits an invoice before PE failure,
record resumable incomplete work and resume the **same** PE operation; never
acknowledge paid success or blindly create another invoice/payment. Prefer one
transaction where possible and verify actual boundaries. Test sequential replay,
concurrent replay, lost response, crash before/after SI/PE submit, offline reload,
and closed-shift retries: one SI, one PE, one SLE movement and identical GL.
These are AUT-OFF-01/02/03/04 requirements, not passed tests.

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

Proposed staging checks, **not executed**. Use only an authorized staging name,
invented invoices, and outside the 4-6 Nov schema/config freeze. First deploy the
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

**Estimate: 8-12 focused builder-days**, one owner, including AUT work; an additional
1-2 reviewer-days and at least a 24-hour two-PC offline soak are separate elapsed
dependencies. This is a planning estimate, not measured velocity or a promise.

| Work | Builder-days |
| --- | --- |
| Exact direct-rate service, validated record selection and durable invoice/PE orchestration | 2-3 |
| POS tender/rate snapshot, common online/outbox routing, replay identity and recovery | 3-4 |
| Ordered precision migration, repeated-migrate/old-data and amount-bound tests | 1-2 |
| AUT currency/rate/offline, cashier permissions, UI/printing and two-PC fixes | 2-3 |

These total **8-12 cumulatively** for online plus offline; an online-only milestone
is roughly 4-6 builder-days including its AUT subset, not a separate additive cost.
Allow another 2-4 builder-days if a maintained minimal POS fork is required after
extension points fail. Unproven: effective-time/store selection, role permissions,
exact direct arithmetic across supported amounts, schema persistence, real UI
payloads/prints, cached rates, split payments, replay/concurrency/crash boundaries,
closed shifts, returns and offline recovery. Required tests: AUT-CUR-01/03/04/05/06/
10/12/14 (14 awaits Q1), AUT-RATE-01..06, AUT-OFF-01..04 and relevant AUT-PERM-03/06/07.
Q6 gates production money work; Q1/Q2/Q5 paths remain gated rather than invented.

If extension routing fails, use a minimal reviewed POS fork delegating to the same
app service, with a dated DECISIONS entry and AUT coverage. If exact direct/native
amount equality fails, do not ship precision-only arithmetic: prototype the direct
backend calculation with explicit amount limits and repeat GL/large tests. If
replay cannot guarantee one SI/PE, keep CDF-on-USD queued/draft with visible failure,
never acknowledge it as paid or silently retry another payment. A proposed interim
supervised online-only Payment Entry workflow needs Sam's explicit scope decision;
it is not an automatic fallback. If those paths miss M1, report no-go/limited scope
to Sam; preserve old-system/paper operation rather than claim offline readiness.
