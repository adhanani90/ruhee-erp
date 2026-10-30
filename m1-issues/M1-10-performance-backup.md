# M1-10 Performance and backup (C12)
<!-- labels: owner:claude-code,owner:sam -->

**Owners:** Claude Code (item generator script); Sam (timings on a store PC, backup and restore) · **Size:** half a day · **Depends on:** M1-03
**Refs:** C12; SPEC REQ-STK-01; DEPLOYMENT.md §6

### Goal
Confirm the billing screen stays usable with a full-size catalogue, and that a staging backup really restores.

### Allowed paths
`ruhee_erp/spike/**`, `docs/DEPLOYMENT.md` (§6), `docs/DECISIONS.md`, `docs/STATUS.md`

### Steps
1. Claude Code writes `spike/load_items.py` to create 5,000 `SPIKE-` items with prices, idempotently.
2. Sam times the first catalogue load and ten item searches on a New Depo PC, or the closest available PC if Q9 is still open (note which).
3. Sam takes a staging backup in Frappe Cloud, restores it to a fresh site, and opens it. Record the plan's backup schedule and retention in DEPLOYMENT.md §6.

### Acceptance criteria (C12)
- [ ] With 5,000 items loaded, item search answers within a second.
- [ ] The backup restores to a fresh site that opens and shows the spike data.

### Evidence
The timing table, the PC model and browser, and the restore log or screenshot.
