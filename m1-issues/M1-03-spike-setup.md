# M1-03 Spike baseline configuration
<!-- labels: owner:claude-code,owner:sam -->

**Owner:** Claude Code (script); Sam runs it on staging · **Size:** half a day · **Depends on:** M1-02
**Refs:** SPEC §14; ACCOUNTING_RULES §2–3; ACCEPTANCE_TESTS §1 (setup)

### Goal
One idempotent script that creates the test configuration every later spike check uses, on dev and on staging.

### Allowed paths
`ruhee_erp/spike/**`, `docs/STATUS.md`

### What the script sets up
Sam runs the ERPNext setup wizard on staging by hand first: company in USD, country DRC, standard chart of accounts. Then the script, `ruhee_erp/spike/setup_spike.py`, creates:

- The CDF currency enabled, with its smallest fraction set to 50.
- Accounts from ACCOUNTING_RULES §3: Debtors (USD), Cash USD – New Depo, Cash CDF – New Depo (CDF), Exchange income, FX gain/loss, Round-off, Remises accordées, Cash over/short.
- A New Depo warehouse and cost centre.
- Accounts Settings: *Allow multi-currency invoices against single party account* on.
- The external exchange-rate provider off. Find the setting in the installed ERPNext and cite it.
- Stock Settings: negative stock allowed.
- Modes of payment Cash USD and Cash CDF, linked to the drawer accounts, and a POS Awesome profile for New Depo.
- 20 items prefixed `SPIKE-`, priced in USD, and 5 customers prefixed `SPIKE-`, one with a $100 credit limit.
- A USD→CDF rate of 2300 for the spike date, as ERPNext's standard rate record. The store-specific rate is M1-05.
- Two test users, a facturier and a manager, using standard roles for now (the real roles are P3).

### Acceptance criteria
- [ ] Running the script twice creates no duplicates.
- [ ] Every record above exists on dev and on staging.
- [ ] The script lives in `ruhee_erp/spike/` and is not referenced in `hooks.py`.

### Tests
The second run of the script reports "nothing to create".

### Evidence
Output of both runs on staging, and a list of the records created.

### Out of scope
Production fixtures and the real roles.
