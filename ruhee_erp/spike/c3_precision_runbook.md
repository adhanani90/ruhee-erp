# PR #24 precision experiment and handoff

**C3 remains failed/unaccepted.** Server arithmetic for the bounded $100 and
$10,000 controls does not prove general R1 compliance, client behavior or staging
acceptance. Native reciprocal pricing still records the $3,200 line as
**7,359,999.99 FC**, rather than 7,360,000.00 FC.

**Never delete or reset the precision Property Setters on a populated site as
cleanup or rollback.** Removing a setter can allow a later forced DocType JSON
re-import to narrow its column to `decimal(21,9)` and rewrite submitted rates.
Customize Form's Reset to defaults can remove setters too. D-025 removal must
preserve the required precision settings. Production fixtures and a production
migration require separate approval and are outside this PR.

## Changes since the reviewed `0d1c502`

The final widened set is:

| DocType.field | Final precision | Final physical column |
| --- | --- | --- |
| Currency Exchange.exchange_rate | 12 | decimal(21,12) |
| Sales Invoice.conversion_rate | 12 | decimal(21,12) |
| Sales Invoice Payment.posa_company_exchange_rate | 12 | decimal(21,12) |
| GL Entry.transaction_exchange_rate | 12 | decimal(21,12) |
| Payment Entry.target_exchange_rate | 12 | decimal(21,12) |

The history differs from that final configuration. At `0d1c502`, #24 retained
**three of #20's six fields**, dropped three, and added GL transaction precision:

| Original #20 field | At `0d1c502` | Revised #24 |
| --- | --- | --- |
| Currency Exchange.exchange_rate | Retained | Retained |
| Sales Invoice.conversion_rate | Retained | Retained |
| Sales Invoice Payment.posa_company_exchange_rate | Retained | Retained |
| Sales Invoice Payment.posa_exchange_rate | Omitted: exactly 1 for CDF tender on a CDF bill; #25's C4 adapter removes that inline CDF row | Still unchanged: default decimal(21,9); native B/F are unproven |
| Payment Entry.source_exchange_rate | Omitted: the original C3 suite had no Payment Entry | Still unchanged: default decimal(21,9); in #25's Receive path USD Debtors and USD company give exactly 1 |
| Payment Entry.target_exchange_rate | Omitted: the original C3 suite had no Payment Entry | Restored: C4's CDF cash valuation depends on it and the large control fails at 9 places |
| GL Entry.transaction_exchange_rate | Added to preserve submitted transaction rates | Retained; also asserted on Payment Entry GL |

The source-rate decision is supported by
`erpnext/accounts/doctype/payment_entry/payment_entry.py:PaymentEntry.set_source_exchange_rate`
and the saved native controls. It does not cover CDF party accounts or other
payment directions. `posa_exchange_rate` is not widened merely for symmetry.

## Preflight and preservation

`c3_precision.preflight` checks all selected fields and existing setters before
the first write. It proposes precision 12 in fresh in-memory metadata, reads all
columns of every affected table, and uses Frappe's
`MariaDBTable`/`DbColumn.build_for_alter_table` to plan additions, type changes,
defaults, nullability and indexes. It also checks the primary key, orphan unique
indexes and the implicit modified index. It accepts only selected rate-column
type changes. An unrelated change raises an error **without repairing it**.
`c3_probe.preflight_control` proves rejection of an in-memory proposal to alter
the unrelated source rate; it does not alter the database for that test.

The implementation is specific to the inspected MariaDB/Frappe revision. DDL
commits independently and requires an exclusive maintenance window; this is not
an atomic production migration or protection against concurrent schema changes.

The read-only `c3_verify` captures every stored parent column and every child
row, plus all voucher GL. It includes `modified` and captures referenced store
records, complete exchange records, complete Property Setters and physical
column descriptions. Sales Invoice and Payment Entry populations are captured
separately. No save, submit, insert, SQL, set_value or commit is called by the
verifier. `bench execute` itself commits on successful return; there are no
verifier writes to commit.

For each of the five widening stages, the suite closes the preceding POS shift,
captures the complete submitted population, applies precision with no business
operation in between, then captures immediately again. Complete business/rate
records must be equal, including timestamps. After the final fresh payment,
two idempotence runs, Customize Form save on all five DocTypes, forced re-import
of all five and migrate each require the same complete business/rate records,
unchanged required precision setters (all fields and timestamps), column descriptions and
precision traces. Native Customize Form adds four `field_order` setters; native
forced re-import adds `naming_series.options` setters on Sales Invoice and
Payment Entry. These six full rows are explicitly recorded as metadata additions;
they neither replace precision setters nor change a column. Migrate reimports
POS Awesome fixtures and changes only `creation` on
`Sales Invoice-posa_pos_opening_shift-no_copy` and
`Sales Invoice-update_outstanding_for_self-default`. Full before/after rows are
retained for these two unrelated setters; their values and modified timestamps
remain unchanged. Frappe's `modules/import_file.py:import_doc` deletes/reinserts
existing fixture documents, and these fixtures omit creation. Any other metadata
addition or existing-setter change fails the comparison. **All Property Setter
records are therefore not byte-identical across migrate; all five precision
setters are.** No precision repair is run after lifecycle operations.

## Reproduce in an isolated bench

Use a fresh site named **c3-precision-review.localhost** in its own bench/sites
directory. The earlier c3-precision.localhost hostname is no longer this
revision's disposable allow-list entry. Never change a shared app checkout or
restart another task's services to reproduce this suite.

Install the pinned Frappe, ERPNext and POS Awesome plus this #24 checkout. Use
separate MariaDB and Redis endpoints; keep site credentials outside Git. The
tested bench is `/tmp/ruhee-c3-bench`, using independent app clones, private
MariaDB socket `/tmp/ruhee-c3-revision-db/mysql.sock` with networking disabled,
and loopback Redis port 16424 (cache DB 0, queue DB 1). Its site configuration
pauses the scheduler. The shared environment is used only as a Python runtime;
no dependencies or shared app files are changed.

Verified provisioning shape (supply an Administrator password interactively or
from a private local file, never in evidence):

```bash
bench new-site c3-precision-review.localhost --db-root-username dhana --db-root-password socket-auth --db-socket /tmp/ruhee-c3-revision-db/mysql.sock --install-app erpnext --install-app posawesome --install-app ruhee_erp
```

`socket-auth` is a non-secret placeholder used with this private server's OS
socket authentication, not a shared database credential. All commands run from
the isolated bench root, with its app paths first on PYTHONPATH when using a
shared Python runtime. The suite refuses non-default initial rate columns and
uses fresh dated rates; no used Currency Exchange record is overwritten.

```bash
python apps/ruhee_erp/ruhee_erp/spike/c3_suite.py --output /tmp/c3-review-evidence
node --preserve-symlinks-main apps/ruhee_erp/ruhee_erp/spike/c3_client_probe.mjs
```

The suite records every actual bench command in `summary.json`; its full JSON
captures are losslessly gzip-compressed. Decompress with Python's `gzip` module
or `gzip -dc`. Phase files describe native submissions before close; the
dedicated `before_*`/`after_*` audits supply the preservation evidence after
closing. Do not use the phase file's pre-close timestamps as the preservation
baseline.

The tested local full-application and inspection commands are:

```bash
bench --site c3-precision-review.localhost execute ruhee_erp.spike.c3_precision.run --kwargs '{"site":"c3-precision-review.localhost"}'
bench --site c3-precision-review.localhost execute ruhee_erp.spike.c3_precision.inspect --kwargs '{"site":"c3-precision-review.localhost"}'
```

For #25's independently provisioned combination, the staging candidate commands
after review/approval and baseline setup are below. These staging invocations
were **not executed** in this delivery:

```bash
bench --site ruhee-staging.c.frappe.cloud execute ruhee_erp.spike.c3_precision.run --kwargs '{"site":"ruhee-staging.c.frappe.cloud"}'
bench --site ruhee-staging.c.frappe.cloud execute ruhee_erp.spike.c3_precision.inspect --kwargs '{"site":"ruhee-staging.c.frappe.cloud"}'
```

These are candidate application commands, **not deployment approval**. Exact
site matching, the recorded staging freeze, paused disposable scheduler and
Administrator guard remain enforced. No other hostname is accepted. For a
different disposable combination hostname, use an independently reviewed
throwaway guard adaptation and record it; do not remove the guards. Before
any application, capture all existing invented invoices/payments and their
rate context after all closing operations. Require unchanged full records
immediately afterward. Stop on unrelated schema drift or conflicting setters.

## Scope and artifacts

Everything changed by #24 remains under `ruhee_erp/spike/`. There are no hook,
fixture, production DocType, upstream-app, fork, STATUS or DECISIONS edits.
The lab creates invented company/accounts/items/customers/users/profile data
through `setup_spike`; a custom Ruhee C3 Spike Rate DocType; read-only
`ruhee_c3_rate` links on Sales Invoice, Payment Entry and Currency Exchange;
the C3 Precision Lab profile; dated rates; submitted invoices/payments;
closed test shifts; and the six native layout/naming metadata additions described
above. Those records are disposable evidence, not production
configuration. On a populated staging site, retain referenced rates and all
five precision setters when removing experimental code. No generic cleanup is
part of this suite.

Native C3 payloads reproduce the installed client conversion formula in Python;
the supplied tender is the exact R1 control amount. The Node probe executes the
installed TypeScript pricing utility. Neither establishes a complete browser
payload, offline persistence, store selection, actual display or a print.
The Payment Entry control uses standard ERPNext creation, insert/validation and
submission with the same explicit rate/amount/deduction inputs as #25's C4
server path, without importing #25 or installing its hooks. #25's client and
combined validation remain Claude Code's responsibility. Real cashier
permissions, browser/cache behavior, staging and production remain unproven.

Refs: C3/C4, R1/R7, I1/I2/I6/I8, examples A/C; REQ-CUR-06/07,
REQ-PRICE-01; D-023/D-025/D-026. Q1/Q2/Q5/Q6 remain unanswered.

## Installed source consulted

- Frappe `database/mariadb/database.py:updatedb/get_table_columns_description/get_column_type`;
  `database/schema.py:DBTable.get_columns_from_docfields/DbColumn.build_for_alter_table/get_definition`;
  `database/mariadb/schema.py:MariaDBTable.alter/alter_primary_key`.
- Frappe `custom/doctype/property_setter/property_setter.py:make_property_setter`;
  `custom/doctype/customize_form/customize_form.py:fetch_to_customize/save_customization`;
  `__init__.py:reload_doctype`; `core/doctype/doctype/doctype.py:DocType.on_update`;
  `commands/utils.py:execute`; `installer.py:_new_site/install_db`.
- ERPNext `accounts/doctype/payment_entry/payment_entry.py:get_payment_entry`,
  `PaymentEntry.validate/set_source_exchange_rate/set_target_exchange_rate/set_amounts_in_company_currency/set_transaction_currency_and_rate/build_gl_map`.
- POS Awesome `api/invoice_processing/creation.py:update_invoice/submit_invoice`,
  `utils.py:resolve_erpnext_currency_rates`; native closing methods named in
  `c3_probe.phase`; frontend `utils/erpnextCurrency.ts:priceListToSelectedCurrency`.
- #25 at reviewed `ac4b76b`, read only:
  `store_rate_hooks.py:bind_payment_rate/settle_cdf_tender`. No #25 code is
  imported into this experiment or changed for integration.

## Executed local handoff

Tested source handoff: `8f81a3aa47b5a9ef02f755ee76ef45ef16dc4f1d`. Fresh default-precision
financial phases ran at `de9cbdbf777736024d62db9ee67dbef6956d1825`. Collector assertions were
corrected and resumed at native metadata boundaries; no business or precision
operation was replayed in those resumes. The precision, native probe, Payment
Entry probe and read-only verifier hashes are identical throughout. The command
ledger and complete before/after captures are in
[evidence/c3_review/summary.json](evidence/c3_review/summary.json), with a
[manifest](evidence/c3_review/manifest.json) and
[readable results](evidence/c3_review/results.json).

| App | Actual SHA |
| --- | --- |
| Frappe | `2fcb9397a1f1da353b21e53d2f97ec56653acd02` |
| ERPNext | `9cd11b19575bfc34f092a24f6c8b368c4dd69481` |
| POS Awesome | `89ae16d872e90727086b2550d7ca97958c9c4aa4` |
| ruhee_erp, fresh financial run | `de9cbdbf777736024d62db9ee67dbef6956d1825` |
| ruhee_erp, final collector/readback | `8f81a3aa47b5a9ef02f755ee76ef45ef16dc4f1d` |

- Default C3: $100 line 229,999.79 FC; the 100-unit base rounded total and
  Debtors post $10,000.01. Those failures remain in the baseline capture.
- Default native large C4: Cash CDF $10,086.97, Exchange income $86.97; saved
  target rate 0.000434783. No historical failure was corrected in place.
- Revised C3-01 `ACC-SINV-2026-00018`: 230,000 FC, Debtors $100, verifier errors=[].
- Revised C3-02 `ACC-SINV-2026-00019`: 23,000,000 FC, Debtors $10,000, errors=[].
- Native $3,200 boundary `ACC-SINV-2026-00021`: recorded line **7,359,999.99 FC**;
  base $3,200 and rounded total 7,360,000 FC. R1 line compliance still fails.
- Revised native large C4 `ACC-SINV-2026-00022` / `ACC-PAY-2026-00002`:
  Cash CDF 23,200,000 FC / $10,086.96; Debtors credit $10,000; Exchange income
  credit $86.96; source rate exactly 1, target 0.000434782609; outstanding 0;
  independent Payment Entry verifier errors=[].
- Complete 22 invoices, 2 payments, all children, 125 invoice GL rows, 6 payment
  GL rows, 9 exchange records and 7 store records preserved, including modified.
- All five precision setters (complete rows and timestamps) and physical
  `decimal(21,12)` columns survive idempotence, form save, forced re-import and
  migrate. The unrelated native metadata differences are disclosed above.
- Local repository smoke: 1 integration test passed. Cached pre-commit checks
  passed; final CI results and exact PR head are recorded in the PR description.

Claude Code can use the PR head containing this source, apply the full script
before #25 setup, and independently validate the combination. The original
reciprocal boundary, browser/cache evidence, staging evidence, other tender
paths, production fixtures and cashier permissions remain unproven. Never mark
C3 passed from this handoff.
