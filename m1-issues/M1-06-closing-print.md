# M1-06 Shift close per currency and A4 print (C10, C11)
<!-- labels: owner:claude-code,owner:sam -->

**Owner:** Claude Code; Sam takes the screenshots · **Size:** half a day · **Depends on:** M1-04
**Refs:** C10, C11; ACCOUNTING_RULES R10, I1, I5; SPEC REQ-CASH-02, REQ-FLOW-04

### Goal
Find out whether POS Awesome's shift close can show the CDF drawer in CDF, and whether a custom A4 template prints from the billing screen.

### Allowed paths
`ruhee_erp/spike/**`, `docs/DECISIONS.md`, `docs/STATUS.md`. A non-standard print format may be created on staging only.

### Acceptance criteria
- [ ] **C10:** after a day with USD and CDF payments, the shift close shows the CDF drawer in CDF. If it doesn't, the gap is written down with an effort estimate for a custom view.
- [ ] **C11:** a bill prints from the billing screen through a minimal custom A4 Jinja template showing exactly the recorded values (I1).

### Evidence
Closing screenshot, the printed PDF, and a note.

### Out of scope
The real bill layout, which is ChatGPT's in P2.
