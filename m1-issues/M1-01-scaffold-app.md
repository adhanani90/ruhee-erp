# M1-01 Scaffold ruhee_erp and the local dev bench
<!-- labels: owner:claude-code -->

**Owner:** Claude Code · **Reviewer:** Sam · **Size:** half a day · **Depends on:** M1-00
**Refs:** SPEC §14; DEPLOYMENT.md §2–3; AGENTS.md §3, §5, §7

### Goal
An installable, empty `ruhee_erp` app, merged with the docs already in the repository, plus a CI workflow and a local v16 bench with ERPNext and our POS Awesome fork installed.

### Allowed paths
`pyproject.toml`, `ruhee_erp/**` (scaffold, `spike/__init__.py`, `tests/`), `.github/workflows/**`, `README.md`, the license file, `.gitignore`, `docs/STATUS.md`, `docs/DEPLOYMENT.md`

### Steps
Verify every command against the installed bench before relying on it.

1. Set up the local bench as in DEPLOYMENT.md §3. Confirm the Python and Node versions Frappe 16 needs from the `frappe` repository first. On Windows, use the `frappe_docker` dev container.
2. `bench get-app --branch version-16 erpnext`.
3. Read the fork's README and branches to find the branch for v16, then `bench get-app` it. Confirm the app name (expected `posawesome`) from its `pyproject.toml` or `hooks.py`. Record the branch and current commit as **candidate** pins in DEPLOYMENT.md §2.
4. Run `bench new-app ruhee_erp`.
   - Title: Ruhee ERP. Publisher: Ruhee Pharma. Email and license: ask Sam.
   - Accept the GitHub Actions workflow for unit tests.
   - If asked for a branch, use `main`.
5. In `apps/ruhee_erp`:
   - add the GitHub repository as `origin`, fetch, and create branch `M1-01-scaffold-app`;
   - merge `origin/main` with `--allow-unrelated-histories`, keeping all docs files;
   - push and open a PR.
6. Declare ERPNext as a required app in `hooks.py`, in the format the installed Frappe expects. Check `frappe` for how `required_apps` is read.
7. Add `ruhee_erp/spike/__init__.py` and `ruhee_erp/tests/__init__.py`. Add `ruhee_erp/tests/test_smoke.py`, which asserts that `erpnext`, `posawesome` and `ruhee_erp` are installed. Use the test base class the installed Frappe provides (check `frappe/tests`).
8. Install the app on `dev.localhost` and run the tests.
9. Make CI install ERPNext `version-16` before `ruhee_erp`, using Frappe 16's Python and Node. POS Awesome is added to CI only when a test needs it.
10. Update STATUS.md.

### Acceptance criteria
- [ ] The repository root is a valid Frappe app (`pyproject.toml`, `ruhee_erp/hooks.py`) and still contains every docs file.
- [ ] `bench --site dev.localhost install-app ruhee_erp` succeeds on a site that has erpnext and posawesome installed.
- [ ] `bench --site dev.localhost run-tests --app ruhee_erp` passes.
- [ ] CI runs on the PR and passes.
- [ ] The candidate POS Awesome branch and commit are recorded in DEPLOYMENT.md §2.

### Tests
`test_smoke.py`, locally and in CI.

### Evidence
`bench version` output, install log, test output, CI run link.

### Out of scope
Any DocType, fixture, setting or business logic.
