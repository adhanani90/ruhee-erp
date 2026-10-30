# M1-02 Deploy to the Frappe Cloud staging site and pin versions (C1)
<!-- labels: owner:sam,owner:claude-code -->

**Owner:** Sam (Frappe Cloud dashboard), with Claude Code preparing and verifying · **Size:** half a day · **Depends on:** M1-01 merged
**Refs:** C1; DEPLOYMENT.md §1, §2, §4; SPEC §14

### Goal
A Frappe Cloud v16 staging site running erpnext, posawesome (our fork) and ruhee_erp, with every version pinned.

### Allowed paths
`docs/DEPLOYMENT.md`, `docs/STATUS.md`, `docs/DECISIONS.md` (spike report, C1 row)

### Steps
1. Claude Code writes exact numbered steps for Sam from DEPLOYMENT.md §4, steps 3–8.
2. Sam creates the bench group (Version 16, region with the lowest latency from Kinshasa) with frappe, erpnext, the POS Awesome fork on its pinned branch, and ruhee_erp on main. Sam deploys.
3. Sam creates the staging site on a plan of $25 or more a month and installs erpnext, posawesome and ruhee_erp.
4. Sam turns off automatic updates and turns on two-factor login for the admin account.
5. Sam opens the POS Awesome billing screen over HTTPS in New Depo's browser (Q9). If that's unknown, use Chrome and note it.
6. Check whether sites on one bench group can be updated one at a time (DEPLOYMENT.md §1).
7. Claude Code records the exact commit of every app in DEPLOYMENT.md §2.

### Acceptance criteria (C1)
- [ ] The deploy succeeds, and all three apps show as installed on the staging site.
- [ ] The billing screen opens over HTTPS.
- [ ] Pins are recorded, automatic updates are off, and two-factor login is on for admin.
- [ ] Per-site update behaviour is recorded in DEPLOYMENT.md §1.

### If it fails
Claude Code reads the build log. Spend at most one day trying an earlier commit of the fork. If that fails, record C1 as failed and go straight to M1-11 for a fallback decision.

### Evidence
Deploy log screenshot, installed-apps screenshot, billing-screen screenshot (URL visible), and the PR with the pins.
