# DEPLOYMENT — Ruhee ERP

## 1. Environments

| Environment | Where | Purpose | Data |
| --- | --- | --- | --- |
| Local dev | Sam's machine: a native bench, or a `frappe_docker` dev container | Claude Code builds and runs the tests | Test data only |
| Staging | Frappe Cloud private bench; a site such as `ruhee-staging.frappe.cloud` | M1 spike, acceptance tests, migration rehearsal | Test and rehearsal data |
| Production | Same bench group, a separate site created in P5 | New Depo live | Real |

Staging and production share one bench group. Each deploy creates a new bench version, and each site is then updated on its own. **Verify in M1-02** that per-site updating works this way. If it doesn't, use two bench groups and record the change in DECISIONS.

## 2. Version pins

*Filled in by M1-02, and changed only through DECISIONS.*

| App | Repository | Branch | Commit or tag | Pinned on |
| --- | --- | --- | --- | --- |
| frappe | frappe/frappe | version-16 | | |
| erpnext | frappe/erpnext | version-16 | | |
| posawesome | our fork of defendicon/POS-Awesome-V15 | develop (candidate, M1-01) | `89ae16d872e90727086b2550d7ca97958c9c4aa4` (candidate, M1-01) | |
| ruhee_erp | ruhee-erp | main | | |

*M1-01 notes (candidates only; M1-02 pins).*

- **posawesome:** upstream has no `version-16` branch, and its tags stop at `15.36.0`. The upstream README claims v15 and v16 support, and its v16 manifest (`docker/apps.json`) pairs ERPNext `version-16` with POS Awesome `develop`. `pyproject.toml` on `develop` declares `frappe`/`erpnext` `>=15.0.0,<17.0.0`; the app name is `posawesome` (`pyproject.toml`, `hooks.py`), with `required_apps = ["erpnext"]`. Our fork's only branch, `develop`, equals upstream `develop` at `89ae16d` (26 Oct 2026). Upstream `production` (`03c6fd3`, Jan 2026) has diverged (`develop` is 1,716 commits ahead and 1 behind). Upstream `stage-develop` (`da1f1f4`) is `develop` plus 4 commits, including "fix(closing): preserve counted amounts and resolve tender currency"; flagged for the C10 closing check.
- **Local dev bench (M1-01), for reference:** frappe `16.54.0` (`2fcb939`), erpnext `16.53.0` (`9cd11b1`), both `version-16`.

## 3. Local development setup (Claude Code, M1-01)

Frappe 16's requirements have to be met. Community v16 install guides list Python 3.14, Node 24, MariaDB 11.8+, Redis 6+ and Yarn 1.22. **Confirm these from the `frappe` repository before installing.** The `frappe_docker` dev container avoids most environment problems and is the recommended route on Windows. Otherwise use Ubuntu 22.04+ (or WSL2) or macOS.

```bash
uv tool install frappe-bench                      # or: pipx install frappe-bench
bench init --frappe-branch version-16 frappe-bench
cd frappe-bench
bench get-app --branch version-16 erpnext
bench get-app --branch <v16-branch> <url-of-our-POS-Awesome-fork>
bench new-site dev.localhost --admin-password <local-only> --mariadb-root-password <local-only>
bench --site dev.localhost install-app erpnext
bench --site dev.localhost install-app posawesome  # confirm the app name from the fork
bench --site dev.localhost set-config developer_mode 1
bench --site dev.localhost set-config allow_tests true
bench start
```

- **First time only (M1-01):** scaffold the app with `bench new-app ruhee_erp` and merge it with this repository, as the M1-01 card describes.
- **After that:** `bench get-app <ruhee-erp repo URL>`, then `bench --site dev.localhost install-app ruhee_erp`.
- **M1-01 as built:** native WSL2 Ubuntu 26.04, not `frappe_docker`. Python 3.14 and MariaDB 11.8 come from apt; Node 24 comes from nvm (`nvm alias default 24`); bench comes from `uv tool install --python /usr/bin/python3.14 frappe-bench`. The bench is at `~/frappe-bench` on the WSL filesystem.
- Working copy for every tool: `~/frappe-bench/apps/ruhee_erp`. Don't work in any other clone.
- Restart `bench start` after `bench new-app` or `bench get-app`. Processes started earlier cannot import the new app, and the scheduler then stops the whole bench.

## 4. Frappe Cloud setup (Sam, M1-00 and M1-02)

1. Create a Frappe Cloud account and add a payment method. Private benches aren't available on the trial.
2. Install the Frappe Cloud GitHub app on the GitHub account that owns `ruhee-erp` and the POS Awesome fork, with access to both.
3. Create a bench group on **Version 16**. Pick the region with the lowest latency from Kinshasa; test from New Depo if possible.
4. Add the apps: frappe, erpnext, POS Awesome (our fork, pinned branch) and `ruhee_erp` (main). Deploy.
5. Create the staging site on a plan of $25 or more a month (the minimum for private benches) and install erpnext, posawesome and ruhee_erp.
6. Turn off automatic updates for the bench and site. Note in this file where the setting lives.
7. Turn on two-factor login for the Administrator and System Manager accounts.
8. Record the commit of every app in the pins table (§2).

## 5. Deploy flow

1. A PR is merged into `main` (Sam).
2. Sam deploys on the bench group, then updates the **staging** site only.
3. The relevant acceptance checks run on staging.
4. Production is updated from tested `main` on a fixed day each week. After the 20 Nov freeze, only fixes go out.

Never change configuration in a browser without a matching fixture or PR. The only exceptions are user accounts, opening data and daily rates.

## 6. Backups and restore

- Confirm the Frappe Cloud backup schedule and retention for the chosen plan (M1-10), and record them here.
- Weekly from go-live: Sam downloads the latest production backup (database and files) to separate storage.
- Restore tests: staging to a fresh site in M1-10 (C12), and again in P4 before go-live (AT-27).

## 7. Production setup and cutover (P5, 29–30 Nov)

1. Create the production site and install the apps; settings arrive as fixtures.
2. Create users and roles. Turn on two-factor login for head office and admin.
3. Import items and prices, after the validators pass.
4. Import customers, with credit limits. Opening debts depend on Q3.
5. Count stock at New Depo (29 Nov) and load the opening stock.
6. Enter opening cash for each currency.
7. Smoke test: one bill of each type, one return, one daily close, one A4 print, and a short offline test. Cancel the test documents afterwards.
8. Sam signs off the cutover in STATUS.md.

## 8. Go-live and parallel run

- From 1 Dec both systems run at New Depo.
- Every day, compare sales totals by currency, cash counts by currency and customer balances.
- **Exit criterion:** 10 consecutive trading days match. Then Sam stops the old system at New Depo (D-014).

## 9. Rollback

- **Before the exit criterion:** the old system remains the record. If the new system fails, staff continue on the old system and paper. Fix the problem and resume.
- **After the exit criterion:** restore the latest backup, key in the paper bills issued since, and investigate the cause before resuming.

## 10. Access and secrets

- Passwords, database credentials and API keys live only in Frappe Cloud or a password manager, never in the repository.
- The System Manager role belongs to Sam only.
- Head-office and admin accounts use two-factor login.

## 11. Costs

Two sites on $25–50 plans come to about $50–75 a month, under the $100 ceiling. Watch usage after go-live, and move up a plan only if needed.
