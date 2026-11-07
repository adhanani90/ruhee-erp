# Combined #24 + #25 validation evidence (7 Nov 2026)

Review and validation evidence only. **C3 and C7 remain unaccepted. #24 and #25 stay in
draft.** Queues, tender handling, staging and both PRs' code are unchanged, and nothing is
merged. All data is invented: company Ruhee Spike, customer SPIKE-02 Client A, and
`@example.com` users.

## Code tested

| Component | Revision |
| --- | --- |
| #25 ruhee_erp (code tested) | `7f91668f0f321f3810ff1c906af9bed1e0d6695c` |
| POS Awesome fork (code tested) | `71fcee8ecb3391ebb0bbba8934ff2acc18bfbf99` |
| #24 ruhee_erp | `8ba5b32b8c1d150c8c4682b1b8619fdb3afdb060` |
| Local combined merge, installed on S1 and S2 | `054d9c6dd72234e17cae207185ed473e020b37c3` |
| Frappe / ERPNext | `2fcb939` / `9cd11b1` |

- `054d9c6` merges `7f91668` and `8ba5b32` with no conflicts, because the two PRs change different files. It was never pushed.
- The commit that adds this folder changes evidence only.
- The fork bundle was rebuilt from the clean `71fcee8` (version `1794032729238`). `bundle_compare.json` shows it is code-identical, 150/150 files, to the bundle #25's formal run used (`1794004035820`). The comparison normalises chunk-hash names and the version stamp.
- The #24 suite reproduction ran `8ba5b32` alone with fork `71fcee8`. The fork's diff from `89ae16d` is frontend-only, so the server code is the same as Codex's.

## Labels

Every site is named `c3-precision-review.localhost`, the disposable name #24's guard
allows, and document numbering restarts on each site. **Always cite a document with its
label**, for example "S1 `ACC-SINV-2026-00005`".

| Label | What | Where |
| --- | --- | --- |
| **S1** | First fresh combined site | isolated bench `sites/`, port 8021 |
| **S1-A0** | S1's first #24 step: stopped before any change (F1) | `s1/precision/a0_before_pos_patch/` |
| **S1-A1** | S1's first browser attempt, stopped as `line_3200` started | `s1/a1/` |
| **S1-A2** | Full scenario list rerun on S1 with the warmed browser profile | `s1/a2/` |
| **S2** | Second fresh combined site, same sequence, for `recovery_offline_draft` | isolated bench `sites-combo2/`, port 8041; `s2/` |
| **suite24** | #24's own `c3_suite.py` on a third fresh site | isolated bench `sites-suite/`; `suite24/` |

## Sequence on S1 and S2

1. `new-site`; site config `ruhee_c7_spike=1` and `pause_scheduler=1`; install erpnext, posawesome and ruhee_erp.
2. M1-03: `ruhee_erp.spike.setup_spike.run`.
3. `posawesome.patches.add_per_payment_multi_currency_fields.execute`.
   - A fresh install marks POS Awesome's patches done without running them (`frappe/installer.py:install_app`, line 372).
   - So without this step `Sales Invoice Payment.posa_company_exchange_rate` does not exist. S1-A0 shows that state.
4. Default precision recorded: `precision/default_columns.json`, `default_trace.json` and `default_precision_state.json`.
5. #24 applied:
   - `c3_precision.run`, `audit_all` before and after, `inspect`, applied columns;
   - a second `run`, which returned `changes=[]`.
6. C7 setup: `store_rate_setup.run`, output in `c7_setup.json`. Company rate 9999, store rate 2300/2320. Precision captured again afterwards.
7. Browser: `c7_browser.mjs` in headless Chromium.
8. Read-only checks: the grader `store_rate_verify.from_harness`, #24's `c3_verify`, and `c3_precision.inspect` after the browser run.

`s1/steps.txt` and `s2/steps.txt` list the timestamped steps.

## Five-column precision

`s1/precision_summary.json` and `s2/precision_summary.json` show each field at four points:
default, after #24, after C7 setup, and after the browser run.

| Field | Default | After #24, after C7 setup, after browser |
| --- | --- | --- |
| Currency Exchange.exchange_rate | decimal(21,9), precision 9 | decimal(21,12), setter 12 |
| Sales Invoice.conversion_rate | decimal(21,9), precision 9 | decimal(21,12), setter 12 |
| Sales Invoice Payment.posa_company_exchange_rate | decimal(21,9), precision "" | decimal(21,12), setter 12 |
| GL Entry.transaction_exchange_rate | decimal(21,9), precision 9 | decimal(21,12), setter 12 |
| Payment Entry.target_exchange_rate | decimal(21,9), precision 9 | decimal(21,12), setter 12 |

- Unchanged at decimal(21,9): `Payment Entry.source_exchange_rate`, `Sales Invoice Payment.posa_exchange_rate`, `Sales Invoice.plc_conversion_rate` and `GL Entry.reporting_currency_exchange_rate`.
- Preflight planned exactly five `change_type` operations.
- M1-03's two pre-existing exchange records are identical, `modified` included, across #24 (`audit_before`/`audit_after`).

## Document map and results

### S1-A1 (`s1/a1/graded.json`)

| Scenario | Invoice | Payment Entry | Graded |
| --- | --- | --- | --- |
| c3_01 | none: item catalogue empty after 5 min, harness timeout before adding an item | none | fail (no invoice) |
| c3_02 | none: same | none | fail (no invoice) |
| c4 | S1 00001 | S1 00001 | pass |
| c4_large | S1 00002 | S1 00002 | pass |
| c5 | S1 00003 | none | pass |
| line_3200 | none: harness stopped as the scenario started | none | not run |

### S1-A2 (`s1/a2/graded.json`)

| Scenario | Invoice | Payment Entry | Graded / observed |
| --- | --- | --- | --- |
| c3_01 | S1 00004 | none | pass: 230,000 FC; $100 |
| c3_02 | S1 00005 | none | **pass**: 23,000,000 FC; base total, Debtors and Cash CDF **$10,000.00** |
| c4 | S1 00006 | S1 00003 | pass: Cash CDF $100.87; Exchange income $0.87 |
| c4_large | S1 00007 | S1 00004 | **pass**: Cash CDF **$10,086.96**; Debtors $10,000; Exchange income **$86.96**; rates 0.000434782609 |
| c5 | S1 00008 | none | pass: $50 outstanding |
| line_3200 | S1 00009 | none | **pass**: exactly 7,360,000 FC |
| diag_240k | S1 00010, **draft**: POS Awesome's working draft from `update_invoice`, no request ID | none | pass. Submit rejected with HTTP 417; nothing submitted. The rejected bill stays `pending` in the browser outbox. |
| b_cdf_bill_usd_tender | S1 00011 | none | **fail**: the $100 USD tender is stored as 999,900 FC (100 × 9999), base $434.74; Cash USD account amount 23.00, not 100 |
| recovery_online | S1 00012 | S1 00005 | pass |
| recovery_offline_draft | S1 00013, **draft** | none | **fail**, observed (see below) |
| recovery_network | S1 00014 | S1 00006 | pass |
| lost_response | S1 00015 | S1 00007 | pass |
| concurrent_replay | S1 00016 | S1 00008 | pass: one posting observed on replay (see below) |
| effective_time A | S1 00017 | none | pass: kept 2300 |
| effective_time C | S1 00018, **draft** held with its reason | none | pass |
| effective_time B | S1 00019 | none | pass: bound 2400 |
| client_settings | none | none | outbox mode `off`; no stored mode |

**S1-A2 `recovery_offline_draft`.** The scenario ran its offline sale, the injected failure and the
sync. Then the harness timed out waiting for the terminal-unlock PIN after the browser restart, so
its step capture was lost.

- What the browser JSON keeps is the reopened session's HTTP trace and queue:
  - `write_queue` entry `synced`;
  - the leftover `diag_240k` outbox entry re-sent through `submit_invoice_outbox_entry` and rejected with 417 each time (`retrying`, retry_count 4).
- `recovery_offline_draft_by_request_id.json` reads the saved bill, S1 00013:
  - docstatus 0, bound 2300/2320, issued 06:55:34Z;
  - net tender 232,000 FC, allocation $100;
  - no Payment Entry and no GL.
- The grader crashes on this scenario (`KeyError: 'queued_offline'`, `grade_full_dir_crash.txt`), so `graded.json` covers the other 14 scenarios.

### S2 (`s2/graded.json`)

Numbering restarts at 00001.

| Scenario | Invoice | Payment Entry | Graded |
| --- | --- | --- | --- |
| c4 (warm-up) | S2 00001 | S2 00001 | pass |
| c4_large (warm-up) | S2 00002 | S2 00002 | pass: $10,086.96 / $86.96 at 0.000434782609 |
| recovery_offline_draft | S2 00003, **draft** | none | **fail** |

S2's offline-draft result: the queue goes `queued_offline` (pending) → inject → `after_sync`, where
the `write_queue` entry is `synced`, and it stays `synced` after the browser restart. The server
keeps S2 00003 as a draft with its binding (2300/2320), issue time and net tender (232,000 FC / $100),
with no 9999 valuation and no Payment Entry.

### Four-request replay

`concurrent_replay` sends the client's own outbox payload four times from the page with `Promise.all`.

- The responses show **one posting observed on replay**: S1 00016, with three responses `replayed: true`.
- The grader finds one invoice and one Payment Entry, S1 00008.
- The server ran `serve --nothreading` (`frappe/app.py`, `threaded=not no_threading`), so it processed the four requests one at a time.
- **Overlapping server transactions are unproven.**

### #24's verifiers on #25's records

| File | Result |
| --- | --- |
| `s1/a2/c3_verify_payment_ACC-PAY-2026-00004.json` | `errors=[]` |
| `s2/c3_verify_payment_ACC-PAY-2026-00002.json` | `errors=[]` |
| `s1/a2/c3_verify_run_ACC-SINV-2026-00005.json` | Only its two C3-lab checks fail, by design: there is no `ruhee_c3_rate` link, and the latest Currency Exchange is the 9999 decoy |

In the `c3_verify_run` file, every amount, payment-row and GL check passes.

## suite24: #24's own suite, reproduced

- `summary.json` is the suite's command ledger: 40 commands, all exit 0, plus its preservation hashes.
- Selected captures are included as `*.json.gz`. `all_captures_sha256.json` hashes every capture the run produced.
- Native large Payment Entry:
  - `payment_baseline`: `PAY-00001` at default precision, $10,086.97 / −86.97 (8 verifier errors, kept);
  - `payment_revised`: `PAY-00002` after widening, target 0.000434782609, $10,086.96 / −86.96, `errors=[]`.
- Native $3,200 line, suite `SINV-00021` (`phase_ledger`): 7,359,999.99 FC.

## Excluded

- Browser profiles: cookies, IndexedDB and session storage.
- `site_config.json`, `private/c7_secrets.json`, database credentials, server logs, raw install logs and the suite's per-command bench logs.
- The browser JSONs' HTTP traces hold only the request bodies and responses of four POS methods, without headers. Queue captures hold only `write_queue` and `invoice_outbox`.
- `c7_setup.json` names where the credentials file lives, not what it contains.

## Reproduce

```bash
# isolated bench; ./c7 = PYTHONPATH=<fork 71fcee8>:<ruhee_erp 054d9c6> python -m frappe.utils.bench_helper frappe (cwd sites/)
./c7 new-site c3-precision-review.localhost --db-socket <private socket> ...
./c7 --site c3-precision-review.localhost set-config ruhee_c7_spike 1 --parse
./c7 --site c3-precision-review.localhost set-config pause_scheduler 1 --parse
./c7 --site c3-precision-review.localhost install-app erpnext   # then posawesome, ruhee_erp
./c7 --site c3-precision-review.localhost execute ruhee_erp.spike.setup_spike.run
./c7 --site c3-precision-review.localhost execute posawesome.patches.add_per_payment_multi_currency_fields.execute
./c7 --site c3-precision-review.localhost execute ruhee_erp.spike.c3_precision.run --kwargs '{"site":"c3-precision-review.localhost"}'
./c7 --site c3-precision-review.localhost execute ruhee_erp.spike.c3_precision.inspect --kwargs '{"site":"c3-precision-review.localhost"}'
./c7 --site c3-precision-review.localhost execute ruhee_erp.spike.store_rate_setup.run
./c7 --site c3-precision-review.localhost serve --port 8021 --noreload --nothreading
# browser: see store_rate_report.md section 14; run the item catalogue warm-up before c3_01 on a fresh profile
./c7 --site c3-precision-review.localhost execute ruhee_erp.spike.store_rate_verify.from_harness --kwargs '{"results_dir": "<dir>"}'
./c7 --site c3-precision-review.localhost execute ruhee_erp.spike.c3_verify.payment --kwargs '{"site":"c3-precision-review.localhost","name":"<PE>"}'
```

`manifest.json` lists the SHA-256 of every file in this folder.
