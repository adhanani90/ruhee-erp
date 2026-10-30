# M1-09 Returns, including the mixed return (C13)
<!-- labels: owner:claude-code -->

**Owner:** Claude Code; Sam does a pass in the billing screen if needed · **Size:** 1 day · **Depends on:** M1-04, M1-05 (M1-07 for the offline answer)
**Refs:** C13; ACCOUNTING_RULES R13–R17, I8, I9, examples K, L, mixed-return fallback; SPEC REQ-RET-01..07

### Goal
Establish how POS Awesome and ERPNext handle returns on v16 with our currency setup, including one return that mixes restocked and non-restocked lines.

### Allowed paths
`ruhee_erp/spike/**`, `docs/DECISIONS.md`, `docs/STATUS.md`

### Steps
1. Make the original bills at 2300, then enter a new store rate (2400) before making the returns, so the rate test is meaningful.
2. **Example K:** return a line of a paid CDF bill without stock, and refund it from the CDF drawer.
3. **Example L:** return a line of a credit bill to the shelf, against the balance.
4. **Mixed:** one return containing a back-on-the-shelf line and a no-stock line.

### Acceptance criteria (C13)
- [ ] K and L post as in ACCOUNTING_RULES, and each credit note reverses at its original bill's rate, not 2400.
- [ ] Stock moves only for L.
- [ ] Whether returns work offline is recorded (from M1-07).
- [ ] The mixed-return result is recorded: does stock move for the restocked line only? If not, a design note for the fallback (two credit notes against the same bill, created and printed together) is in DECISIONS. It is built in P2, not here.

### Evidence
GL and stock ledger extracts for K, L and the mixed return, plus the note.

### Out of scope
Later-day refunds (Q11) and building the fallback.
