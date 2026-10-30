# M1-05 Cross-currency payment and store-rate prototype (C4, C7 online)
<!-- labels: owner:claude-code -->

**Owner:** Claude Code · **Size:** 1 day · **Depends on:** M1-04
**Refs:** C4, C7; ACCOUNTING_RULES R3, R5, R7, R11, I6, I8, examples C, E, F; SPEC REQ-CUR-03/06/07

### Goal
Find out whether POS Awesome posts a USD bill paid in CDF as example C, and prove that a store-specific rate record, rather than ERPNext's company-wide rate, can drive CDF bills and payments.

### Allowed paths
`ruhee_erp/spike/**`, `docs/DECISIONS.md` (spike report rows, design note), `docs/STATUS.md`.
A custom DocType created only on staging is allowed for the prototype. No production DocType is committed.

### Steps
1. Find where POS Awesome gets exchange rates, and whether it caches them for offline use. Cite `file:function`.
2. Pay a $100 USD bill with 232,000 FC through POS Awesome. If its result differs from example C, build a prototype hook in `spike/`.
3. Prototype a store rate record (store, date, base, higher) and route C3–C5 through it instead of the company-wide rate.

### Acceptance criteria
- [ ] **C4:** Cash CDF 232,000 FC valued at $100.87, Debtors −$100, Exchange income $0.87, exactly.
- [ ] **C7 (online):** the store rate record, not the company-wide rate, drives the amounts in C3–C5.
- [ ] A design note for the production rates implementation is in DECISIONS: where to hook, and what to override in POS Awesome, if anything.

### Tests
Spike script asserting the example C ledger lines.

### Evidence
GL extracts, source references, and the design note.

### Out of scope
Manual offline rate entry with a manager PIN (P2), and Q1, Q2 and Q5 behaviour.
