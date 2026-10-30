# M1-07 Offline sync investigation (C7 offline; prepares C8, C9 and the AUT-OFF tests)
<!-- labels: owner:claude-code -->

**Owner:** Claude Code · **Size:** 1 day · **Depends on:** M1-05
**Refs:** C7, C8, C9; SPEC REQ-OFF-01..06, REQ-RET-07; ACCEPTANCE_TESTS AUT-OFF; ACCOUNTING_RULES I7, I8

### Goal
Document exactly how POS Awesome queues and syncs offline work, show from the server side that a replayed submission doesn't create duplicates, and show that an offline bill uses the store rate cached while online.

### Allowed paths
`ruhee_erp/spike/**`, `docs/DECISIONS.md` (sync design section), `docs/STATUS.md`

### Steps
1. From the source, document:
   - what is queued offline (bills, payments, customers, cash movements, returns?), and where it is stored;
   - which server methods are called on sync;
   - the request identity used for duplicate protection;
   - retry behaviour, and what happens on a server validation failure;
   - when prices, stock, credit limits and rates are cached and refreshed.
2. Write `spike/replay_check.py`: submit the same payload twice through the sync method and show that only one bill and one payment are created.
3. With the browser offline, make a CDF bill and confirm it used the store rate cached while online.

### Acceptance criteria
- [ ] The sync design note is in DECISIONS, with `file:function` references.
- [ ] The replay check shows exactly one bill and one payment.
- [ ] **C7 (offline):** the offline bill used the cached store rate.
- [ ] Whether returns are supported offline is answered, for C13.

### Evidence
The design note, the replay script output, and a screenshot of the offline bill.
