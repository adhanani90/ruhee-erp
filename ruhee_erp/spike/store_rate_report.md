# M1-05 (#6): C7 online supported-extension investigation

Partially addresses #6. Codex owns this spike; Claude Code cross-review is pending.
This supplements draft PR #20; it does not replace its original failures or change
any approved decision. **C7 is not marked passed.** Formal C3 re-proof, staging/UI
evidence and final online/offline C7 acceptance remain with their existing cards.

**Answer: yes for the tested server submission paths, without a fork or
monkeypatch.** A Sales Invoice `before_validate` doc event restores the explicit
store-record rate after POS Awesome's internal `update_invoice` overwrite and
before ERPNext's validation/recalculation. C4 additionally needs a supported HTTP
submit override to retain the CDF tender, remove incompatible inline cash, and an
`on_submit` doc event to create its separate Payment Entry after invoice posting.
The untouched frontend still needs a store-rate API/snapshot and display work.

## Environment and boundaries

- Disposable, paused `m105.localhost`, reused from PR #20. Invented data only.
  No staging, dev, c3-precision site, upstream source, pin or other branch changed.
- Isolated worktree `/tmp/ruhee-c7`, branch `m1-c7-store-rate`, from main `a8049ec`.
  `PYTHONPATH` selects this app copy for bench processes; the main bench checkout
  remains on `m1-c3-precision`. This does not deploy hooks to a running web worker.
- Frappe `2fcb9397a1f1da353b21e53d2f97ec56653acd02`, ERPNext
  `9cd11b19575bfc34f092a24f6c8b368c4dd69481`, POS Awesome
  `89ae16d872e90727086b2550d7ca97958c9c4aa4`. Staging-version equivalence unverified.
- Existing PR #20 scratch rate columns are **decimal(21,12)**, metadata precision
  12. No precision setter or DDL widening runs here. Native nine-place line-price
  drift remains with `m1-c3-precision`; this spike does not fix or judge it.
- Real Frappe `handler.execute_cmd` dispatch, whitelist check, registered hooks,
  native POS terminal PIN/profile/shift authorization, native submit, ERPNext
  validation and GL posting. The request object supplies only POST method for
  dispatch: this is a server harness, without an HTTP server, browser, cookie/CSRF,
  cashier-permission or screenshot acceptance claim. Python `sys.setprofile` only
  observes calls; it does not replace functions or modify framework hook maps.
- Native profile is copied to `C7 New Depo`; hooks act only on this profile and
  disposable site. One explicit submitted rate record is supplied, rather than
  implementing automatic effective-time selection or a Q5 no-rate policy.
- Native per-payment normalization remains enabled. Online submit is synchronous
  (`posa_allow_submissions_in_background_job=0` on the dedicated profile).

## Results per check

[Saved documents, GL, rate records, AR rows and 412 trace events](store_rate_results.json).
Both the new and existing-draft paths were executed for each check.
All six invoices link submitted **Ruhee C7 Store Rate `t1m8o0hspi`**, New Depo,
base **2300**, higher **2320**, effective 6 Nov 2026 00:00. Both C4 Payment Entries
also save that Link field, `ruhee_c7_rate`, satisfying the tested I6 binding.

The competing Currency Exchange records are **USD→CDF 9999** and
**CDF→USD 0.000100010001**, dated 6 Nov. The native resolver's actual returned
value is captured, not inferred from the configured competitor.

| Check | New / existing invoice suffix | Saved conversion_rate | Recorded amounts / comparison |
| --- | --- | --- | --- |
| C3, example A | 00015 / 00016 | 0.000434782609 | Line and bill 230,000 FC; Dr Debtors $100, Cr Sales $100; Dr Cash CDF 230,000 FC = $100, Cr Debtors $100; outstanding $0. Store binding demonstrated locally. |
| C4, example C | 00017 / 00018 | 1 (USD invoice) | Bill $100; separate PE 00005 / 00006 saves target_exchange_rate 0.000434782609 and the same rate link. Dr Cash CDF 232,000 FC = $100.87, Cr Debtors $100, Cr Exchange income $0.87. Outstanding $0 after reload. Supported prototype demonstrated locally. |
| C5, example D | 00019 / 00020 | 0.000434782609 | Bill 230,000 FC / $100; Dr Cash CDF 115,000 FC = $50, Cr Debtors $50; outstanding $50 on each saved invoice and the actual Accounts Receivable report in USD. Billing-screen evidence remains pending. |

Invoice names are prefixed `ACC-SINV-2026-`, PE names `ACC-PAY-2026-`.
CDF unit-price inputs mirror native price-list conversion from the explicit store
quote (USD 100 divided by its compatibility reciprocal), rounded to two monetary
places. At this site's inherited 12-place precision they equal 230,000 FC.
With nine places, the familiar 229,999.79 FC drift remains a separate concern;
rate binding must be judged by the linked record and saved rate, not by treating
that drift as company-rate selection. No alternate printed price is introduced.

**Negative C4 control:** calling native `creation.submit_invoice` directly, with
the rate doc events active but bypassing the HTTP tender adapter, raises
`Account Cash CDF - New Depo - RS is invalid. Account Currency must be USD`.
The `on_submit` hook is never reached. The failed attempt was rolled back to a
savepoint. [Error and actual trace](store_rate_native_control.json). Thus an
`on_submit`-only fix or a rate-only fix is insufficient for C4.

## Execution-order evidence

The `trace` array's zero-based `seq` values identify observed events. These are
call/return events from the installed source, not an assumed lifecycle diagram.

| C3-new seq | Observed event and consequence |
| --- | --- |
| 0–3 | HTTP override → native submit → `_submit_invoice_once` → **direct Python `update_invoice` call**. An override of the HTTP update endpoint would miss this call. |
| 4–5 | Native company resolver returns `conversion_rate=0.000100010001` (9999). |
| 8–9 | `before_validate` enters with that company rate and returns with linked store rate `0.000434782609`. Base paid amount is still $23 at this point. |
| 10–15 | `SalesInvoice.validate` → `AccountsController.validate` → `calculate_taxes_and_totals`; returns base bill/paid $100. Recalculation happens after binding. |
| 23–30 | Native submit's further draft save repeats binding and validation. |
| 37–44 | Submit action repeats binding before controller validation/recalculation. |
| 49–52 | `SalesInvoice.on_submit` writes invoice GL before the app's `on_submit` event. |

For C3-existing, the **submit phase has no `update_invoice` call**: binding returns
at seq 82 (save) and 96 (submit), before controller validation in both cases.
The separately traced draft creation does call `update_invoice`. C5 new/existing
show the same ordering (binding returns 269/284/298 and 342/356 respectively).

C4-new seq **165–168** runs the invoice controller's `on_submit` and GL writer;
**169** then enters the app settlement handler. PE setup initially sees company
reciprocal `0.000100010001`; binding returns store reciprocal at **171**.
The registered PE `before_validate` runs again before PE validation on insert
(172–175) and submit (176–179), which calculates **$100.87**. PE GL writes at
**181–182**, and settlement returns at 184. No submitted rate/GL correction occurs.

This ordering explains the split: `before_validate` establishes invoice valuation;
`on_submit` is useful for the separate PE only after incompatible inline CDF cash
has been removed. POS Awesome's own later before-save/before-submit normalization
uses the already-bound CDF conversion rate for C3/C5. It cannot undo it in these
tested paths.

## I8 and sequential replay

Inserted later submitted rate **`t9s2l5797e`**, same store/profile, **2400/2420**,
effective 6 Nov 12:00. The original rate record was not edited. Before/after SHA256
values in `history` cover full saved invoice documents, their GL, full linked PEs
and PE GL: all six match. No later payment was allocated to the historical invoices.

Then replayed the six original requests, each with its original client request ID
and record link, through the same HTTP dispatcher. Native replay returned each
original invoice; no `on_submit` event ran, no extra PE appeared, and the same six
document/GL hashes still matched. A fresh bench process independently read back
the persisted documents and reasserted exact cash/debtor/spread GL amounts
([readback capture](store_rate_readback.json)).

This proves the measured I8 case and sequential replay with native identity. It
does **not** establish a durable payment operation key, changed-payload rejection,
concurrent replay, crash recovery, background redelivery or incomplete-payment
repair. The prototype deliberately does not claim those production guarantees.

## Outbox assumption and production estimate

Assume **`off`**, the source default recorded by M1-07: offline replay uses
`posawesome.posawesome.api.invoices.submit_invoice`, so it can reach this HTTP
override. No browser's persisted mode was checked, and no offline queue was run.
`coordinator` uses an internal Python submit call and bypasses the HTTP tender
adapter; C4 is not covered in that mode (as the negative control illustrates).
Background completion/acknowledgement also remains untested.

Revised production estimate: **9–13 builder-days**, excluding this spike,
deployment waiting, **1–2 reviewer-days**, and a **24-hour two-PC soak**. This
replaces PR #20's 8–12 planning estimate for the same online plus `off` scope.
One endpoint reduces route count, but does not remove payment/recovery work.

| Production work, including its automated tests | Builder-days |
| --- | --- |
| Direct-rate service, store/effective-time authorization, immutable links, invoice/PE orchestration | 3–4 |
| POS rate/tender snapshot and displays; common online/`off` replay; durable payment identity and draft-fallback recovery | 3–4 |
| Precision migration, repeat-migrate/old-data and supported-amount bounds (coordinate with precision card; count once) | 1–2 |
| Currency/rate/offline regressions, permissions, print/billing-screen consistency and two-PC fixes | 2–3 |

Supported binding is now demonstrated for the measured paths. The previous 2–3
day rate/orchestration line was optimistic about production selection, immutable
payment intent and verification. No fork is needed for this prototype. If a
different mode or unhandled production boundary requires one, describe a minimal
diff and seek Sam's separate D-024 approval; none was edited or committed here.

## Hook inventory for the D-025 removal PR

These are **every active hooks.py entry pointing into spike/** on this branch:

| Hook | Target |
| --- | --- |
| `doc_events["Sales Invoice"]["before_validate"]` | `ruhee_erp.spike.store_rate_hooks.bind_rate` |
| `doc_events["Sales Invoice"]["on_submit"]` | `ruhee_erp.spike.store_rate_hooks.settle_cdf_tender` |
| `doc_events["Payment Entry"]["before_validate"]` | `ruhee_erp.spike.store_rate_hooks.bind_payment_rate` |
| `override_whitelisted_methods["posawesome.posawesome.api.invoices.submit_invoice"]` | `ruhee_erp.spike.store_rate_hooks.submit_invoice` |

Sam explicitly allowed hooks.py for this experiment. Remove all four entries
before removing spike/; retaining dangling targets breaks dispatch. Hooks are
site/profile guarded, but that is not authorization to ship spike code.

## Reproduction and validation

From the installed bench, with its local Redis cache/queue running, paused
`m105.localhost` baseline from PR #20, and the isolated worktree available:

```bash
env PYTHONPATH=/tmp/ruhee-c7 bench --site m105.localhost execute ruhee_erp.spike.store_rate_probe.run
env PYTHONPATH=/tmp/ruhee-c7 bench --site m105.localhost execute ruhee_erp.spike.store_rate_probe.native_c4_control
env PYTHONPATH=/tmp/ruhee-c7 bench --site m105.localhost execute ruhee_erp.spike.store_rate_probe.verify_saved
```

`run` creates new invented bills; it is not an idempotent setup/retry command.
Do not rerun it against the preserved capture simply to repeat a readback.
Commands were verified against installed `bench --help` / `bench execute --help`.
Initial attempts stopped at missing Redis Queue/Cache before invoice submission;
services were started locally without persistence, then all measured checks ran.
Fresh-process readback and ledger assertions passed. Ruff lint/format and
whitespace checks are recorded in the PR; CI and independent review remain
separate from these experiment results.

## Source consulted, blockers and found, not done

Paths below are relative to each installed app; no APIs were assumed:

- Frappe `frappe/handler.py:execute_cmd`; `frappe/model/document.py:Document.run_before_save_methods`,
  `Document.hook`, `Document.run_post_save_methods`; `frappe/commands/utils.py:execute`.
- POS Awesome `posawesome/posawesome/api/invoice_processing/creation.py:update_invoice`,
  `_submit_invoice_once`, `submit_invoice`, `submit_in_background_job`;
  `invoice_processing/utils.py:resolve_erpnext_currency_rates`;
  `payment_currency.py:normalize_invoice_payment_currencies/preserve_multi_currency_payment_amounts`;
  `invoice.py:before_submit`; `idempotency.py:normalize_invoice_request_identity`;
  `employees.py:save_cashier_pin/verify_terminal_employee_pin`.
- ERPNext `erpnext/controllers/accounts_controller.py:AccountsController.validate/calculate_taxes_and_totals`;
  `accounts/doctype/sales_invoice/sales_invoice.py:SalesInvoice.validate/on_submit/make_gl_entries`;
  `accounts/doctype/payment_entry/payment_entry.py:get_payment_entry/PaymentEntry.validate/set_target_exchange_rate/on_submit`;
  `accounts/report/accounts_receivable/accounts_receivable.py:execute`.
- PR #20's design note and `store_payment_prototype.py:store_rates/payment` were
  read, not imported/copied wholesale; its process-scoped resolver patches are
  replaced by the supported registration tested here.

Refs: C3–C5/C7; R1–R5/R7/R11, I6/I8; examples A/C/D;
REQ-CUR-03/06/07. Future P2 regression scope includes AUT-CUR-01/03/04,
AUT-RATE-01..06 and AUT-OFF-01; no production AUT suite is claimed here.

No blocker to this bounded server experiment remains. Production/gate blockers:
Q6 accounting sign-off; unresolved Q1/Q2/Q5 paths; nine-place price/amount bounds;
staging/version/UI/print evidence; store permission and effective-time selection;
durable payment intent/recovery/concurrency; background and actual offline proof;
Claude Code cross-review. B/E/F, manager PIN entry of offline rates, returns,
and production migration remain out of scope. STATUS/DECISIONS were not edited
under D-023. C7 stays open for M1-07's final result.
