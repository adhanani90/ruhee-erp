# M1-04 Posting model, CDF bill, part-payment, rounding (C2, C3, C5, C6)
<!-- labels: owner:claude-code -->

**Owner:** Claude Code; Sam does one pass in the billing screen · **Size:** half a day · **Depends on:** M1-03
**Refs:** C2, C3, C5, C6; ACCOUNTING_RULES R1, R2, R4, examples A, D, H; SPEC REQ-FLOW-02

### Goal
Establish, with evidence, how POS Awesome posts bills on v16, and whether examples A and D and the 50 FC rounding come out right.

### Allowed paths
`ruhee_erp/spike/**`, `docs/DECISIONS.md` (spike report rows), `docs/STATUS.md`

### Steps
1. Read POS Awesome's source to find the submit path: which document it creates (Sales Invoice or POS Invoice) and which profile settings control that. Cite `file:function`.
2. Exercise it through its own server methods from a spike script, plus one pass by Sam in the billing screen.
3. Extract the GL and stock ledger entries for each bill.

### Acceptance criteria
- [ ] **C2:** three bills each create their own Sales Invoice with stock updated at submit, and no consolidation happens at shift close. Any setting needed is documented.
- [ ] **C3:** a $100 item on a CDF bill shows 230,000 FC and posts Debtors $100 (example A).
- [ ] **C5:** a 230,000 FC bill with 115,000 FC paid leaves $50.00, visible on the billing screen and in the Accounts Receivable report (example D).
- [ ] **C6:** a CDF total rounds to 50 FC, with the difference in Round-off. ERPNext's native rounding direction is recorded as input for Q1.

### Tests
Spike scripts only. Production tests come in P2.

### Evidence
GL and stock ledger extracts, two screenshots, and the source references.

### Out of scope
Store-specific rates (M1-05) and cross-currency payments (M1-05).
