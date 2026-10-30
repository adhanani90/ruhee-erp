# M1-00 Project setup: repository, fork, Frappe Cloud account
<!-- labels: owner:sam -->

**Owner:** Sam · **Size:** about 1 hour · **Depends on:** none
**Refs:** DEPLOYMENT.md §4 (steps 1–2); STATUS.md

### Goal
Everything the spike needs from outside the code exists, so Claude Code can start M1-01.

### Allowed paths
`docs/STATUS.md`

### Steps
1. Create the private GitHub repository `ruhee-erp`. Commit `AGENTS.md`, `CLAUDE.md`, `docs/*` and `.github/pull_request_template.md` to `main`.
2. Fork `defendicon/POS-Awesome-V15` into the same GitHub account.
3. Create a Frappe Cloud account and add a payment method. Private benches aren't available on the trial.
4. Install the Frappe Cloud GitHub app with access to `ruhee-erp` and the fork.
5. Create these issues: `./create_m1_issues.sh <owner>/ruhee-erp` (needs the GitHub CLI, logged in).
6. If you can, answer Q9 (New Depo's PCs, browser and internet provider) in STATUS.md.

### Acceptance criteria
- [ ] `ruhee-erp` exists, with the docs on `main`.
- [ ] The POS Awesome fork exists.
- [ ] The Frappe Cloud account is active, with a payment method, and its GitHub app can see both repositories.
- [ ] Issues M1-01 to M1-11 exist.

### Evidence
Links to the repository, the fork and the issues; a screenshot of the Frappe Cloud GitHub app's access.
