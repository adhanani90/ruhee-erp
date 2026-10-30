# ACCEPTANCE_TESTS — Ruhee ERP

There are three kinds of test:

- **C1–C13:** M1 feasibility checks, run once on staging. Results go in the spike report in `DECISIONS.md`.
- **AUT-&lt;group&gt;-nn:** automated tests in `ruhee_erp/tests/test_<group>.py`, run by CI on every pull request.
- **AT-nn:** manual acceptance tests on staging and at New Depo (P4). Staff-facing wording comes from ChatGPT; Sam and the New Depo lead run them.

A test marked **Blocked by Qn** cannot pass until that question is answered (see `STATUS.md`).

---

## 1. M1 feasibility checks (C1–C13)

The setup is described in `SPEC.md` §14 and card M1-03: company in USD, CDF enabled, New Depo as a store, 20 test items, 5 test customers (one with a $100 credit limit), rates 2300/2320.

| ID | Check | Passes when | Evidence |
| --- | --- | --- | --- |
| C1 | Install | POS Awesome and `ruhee_erp` build and deploy on Frappe Cloud v16, and the billing screen opens over HTTPS in the browser New Depo uses | Deploy log, installed-apps screenshot, POS screenshot, pinned versions |
| C2 | Posting | Each bill creates its own Sales Invoice that updates stock on submit, with no end-of-shift consolidation | Document list and stock ledger extract for 3 bills |
| C3 | CDF bill | A $100 item billed in CDF shows 230,000 FC and posts Debtors $100 (example A) | GL extract, bill screenshot |
| C4 | Cross-currency payment | A $100 USD bill paid with 232,000 FC posts Cash CDF 232,000 FC valued at $100.87, Debtors −$100 and Exchange income $0.87 (example C), through POS Awesome or a prototype hook | GL extract; source file:function used |
| C5 | Part-payment | A 230,000 FC bill with 115,000 FC paid leaves a $50.00 balance, visible on the billing screen and in the Accounts Receivable report (example D) | GL extract, two screenshots |
| C6 | Rounding | A CDF total rounds to 50 FC, with the difference posted to Round-off. Record ERPNext's native direction (input for Q1) | Bill and GL extract |
| C7 | Store rate | A store-specific rate record, not ERPNext's company-wide rate, drives C3–C5 online, and is used by offline bills. A prototype is acceptable | GL extracts; note of the rate's code path |
| C8 | Offline | Two PCs offline for at least 24 hours, through a browser and PC restart, each create 15 bills (cash, split, credit) and 2 later payments. Everything syncs, nothing lost or duplicated | Paper log, verification script output, screenshots |
| C9 | Offline edge cases | An oversold item syncs into negative stock, and an over-limit credit bill lands as a draft for the manager. These bills are in addition to C8's: the same last unit of one item sold on both PCs, and one over-limit credit bill. Expected overall: 33 bills, 32 submitted, 1 draft. | Stock ledger, draft screenshot |
| C10 | Closing | The shift close shows the CDF drawer in CDF; if not, the gap is written down with an estimate for a custom view | Closing screenshot, note |
| C11 | Print | A bill prints from the billing screen through a custom A4 template | PDF |
| C12 | Performance and backup | With 5,000 items loaded, item search answers within a second on a New Depo PC, and a staging backup restores to a fresh site | Timings, restore log |
| C13 | Returns | See below | GL and stock ledger extracts, note |

**C13 in full:**

1. A manager returns a line of a paid CDF bill without stock and refunds it from the CDF drawer (example K).
2. The manager returns a line of a credit bill to the shelf, against the balance (example L).
3. K and L run at unchanged rates; L moves stock and K doesn't. Then a new rate record is entered, and a further credit note, with no stock movement and no refund, against a bill made at the earlier rate reverses at that rate.
4. Whether returns work offline is recorded.
5. A third return mixes a back-on-the-shelf line and a no-stock line in one document. Record whether stock moves for the first line only, since ERPNext's Update Stock setting applies to the whole credit note. If it doesn't, the fallback is two credit notes against the same bill, created and printed together (`ACCOUNTING_RULES.md` R14). M1 documents the fallback; P2 builds it.

## 2. Automated tests (AUT)

Each test names its rule or example. Tests marked "Blocked" are written with the mechanism and skipped until the question is answered.

### AUT-CUR — currency and payments (P2)

- **AUT-CUR-01** Example A gives exactly its ledger lines.
- **AUT-CUR-02** Example B.
- **AUT-CUR-03** Example C: Exchange income $0.87.
- **AUT-CUR-04** Example D: $50.00 USD balance.
- **AUT-CUR-05** Example E: at 2400/2420, Exchange income $0.42.
- **AUT-CUR-06** Example F: split payment, Exchange income $0.43.
- **AUT-CUR-07** Example G: the remise as a deduction to Remises accordées. **Blocked by Q4** for the basis and amounts.
- **AUT-CUR-08** Example H: rounding direction. **Blocked by Q1.**
- **AUT-CUR-09** Example I: month-end revaluation, FX loss $9.25.
- **AUT-CUR-10** I2 holds for every bill in A–I.
- **AUT-CUR-11** I3: no customer entry posts to a non-USD receivable.
- **AUT-CUR-12** I4: Exchange income comes only from R3/R5 entries.
- **AUT-CUR-13** I6: a CDF document without a store rate record. **Blocked by Q5.**
- **AUT-CUR-14** Example O: payment rounding goes to Exchange income. **Blocked by Q1** for the direction.
- **AUT-CUR-15** I1: the A4 print of a bill shows the recorded prices, discounts and totals. Written with the print format (P2).
- **AUT-CUR-16** I5: after a close with a counted variance, each cash account equals the count in its own currency, and the variance is in Cash over/short.
- **AUT-CUR-17** R6: a USD balance paid later in USD posts with no conversion and no Exchange income.
- **AUT-CUR-18** R12: change given in the other currency. **Blocked by Q2.**

### AUT-RATE — historical rates, I8 (P2)

- **AUT-RATE-01** A bill made at 2300 keeps 2300 and its totals after a 2400 rate is entered.
- **AUT-RATE-02** Its reprint is unchanged.
- **AUT-RATE-03** A later payment uses the later day's rate.
- **AUT-RATE-04** A credit note reverses at the bill's rate.
- **AUT-RATE-05** A rate record already used by a submitted document can't be edited.
- **AUT-RATE-06** A mid-day rate record applies only to documents made after its effective time.

### AUT-STK — stock moves exactly once, I7 and I9 (P2)

- **AUT-STK-01** Submitting a bill moves stock once.
- **AUT-STK-02** An offline bill moves stock once when it syncs.
- **AUT-STK-03** A retried sync of the same bill doesn't move stock again.
- **AUT-STK-04** Cancel and amend leaves one net movement.
- **AUT-STK-05** A back-on-the-shelf return re-adds stock once; a no-stock return re-adds none.
- **AUT-STK-06** A return can't exceed the quantity sold.
- **AUT-STK-07** Overselling is allowed and shows as negative stock (REQ-FLOW-03).

### AUT-OFF — offline sync and duplicates (P2)

These use the sync calls documented in M1-07.

- **AUT-OFF-01** The same offline submission replayed twice, with the same request identity, creates one bill and one payment.
- **AUT-OFF-02** A bill refused at sync, for example over its credit limit, becomes a draft and never disappears.
- **AUT-OFF-03** A synced bill keeps the rate it was made with.
- **AUT-OFF-04** A payment queued offline against an offline bill posts against that bill after sync.

### AUT-RET — returns and refunds (P2)

- **AUT-RET-01** Example J: a swap.
- **AUT-RET-02** Example K: a no-stock return refunded from the CDF drawer.
- **AUT-RET-03** Example L: a return against the balance, stock back.
- **AUT-RET-04** Example M: credit applied to the next bill.
- **AUT-RET-05** Example N. **Blocked by Q11.**
- **AUT-RET-06** A mixed return gives correct stock, through one credit note or the split fallback.
- **AUT-RET-07** I9: the reversal's USD value equals the original line's.
- **AUT-RET-08** Only a manager or head office can create a return (with AUT-PERM-05).
- **AUT-RET-09** Returning one unit of a three-unit line reverses one unit's value; later returns can't exceed the two left.

### AUT-PERM — permissions and credit limits (P3)

- **AUT-PERM-01** A facturier can't edit Item Price.
- **AUT-PERM-02** A facturier or manager can't edit a credit limit; head office can.
- **AUT-PERM-03** A facturier can't change the posting date.
- **AUT-PERM-04** A facturier's discounts are limited to the presets.
- **AUT-PERM-05** A facturier can't cancel bills or create returns.
- **AUT-PERM-06** A store user sees only their own store's documents.
- **AUT-PERM-07** Store roles can't submit a credit sale over the limit.
- **AUT-PERM-08** Only head office can delete documents.

### AUT-MIG — migration (P3)

- **AUT-MIG-01** Validators reject missing prices or units, and duplicate codes.
- **AUT-MIG-02** Imported balances add up to the old system's totals. Depends on Q3.
- **AUT-MIG-03** Opening stock equals the count sheet totals.

## 3. Manual acceptance tests (AT), P4

Each test runs on staging first, then at New Depo with real bills. "Paper flow" means the printed bill goes to the cashier for stamping, then to the packers, then to livraison.

**AT-01 Opening rates.**
Refs: R11, REQ-CUR-03. The manager enters the base and higher rates at opening.
Expected: new bills use them; a CDF bill shows the rate used. (The behaviour when no rate is entered is blocked by Q5.)

**AT-02 USD bill paid in USD.**
Refs: REQ-FLOW-01–04. A facturier bills, prints on A4, and the paper flow completes.
Expected: one invoice; stock down; cash USD up; the bill matches the record (I1).

**AT-03 CDF bill paid in CDF.**
Refs: R1, example A.
Expected: amounts as in R1; rounding to 50 FC. **Blocked by Q1** for the direction.

**AT-04 USD bill paid in CDF.**
Refs: R3, example C.
Expected: CDF due at the higher rate; Exchange income posted.

**AT-05 Split payment.**
Refs: example F.
Expected: both drawers go up; Exchange income on the CDF part.

**AT-06 Part-payment.**
Refs: R4, example D.
Expected: USD balance on the customer, on the billing screen and in the ageing list.

**AT-07 Credit sale and limit.**
Refs: REQ-CRED-02/03.
Expected: within the limit it goes through; over the limit it is refused for store roles.

**AT-08 Later payment in CDF.**
Refs: R5, example E.
Expected: CDF at the payment day's higher rate; balance cleared.

**AT-09 Discounts.**
Refs: REQ-PRICE-04.
Expected: a facturier can use only the presets; a manager can enter any amount; both are recorded per line with the user.

**AT-10 Price change.**
Refs: REQ-PRICE-03, REQ-CTRL-04.
Expected: a manager changes a price, and the change history shows who, when, old and new.

**AT-11 Wrong item at livraison.**
Refs: R17, example J.
Expected: a return plus a new bill; stock correct for both items.

**AT-12 Missing item at livraison.**
Refs: R14, R16, example K.
Expected: a no-stock credit note; refund from the drawer.

**AT-13 Return on an unpaid bill.**
Refs: example L.
Expected: balance reduced; stock back.

**AT-14 Return for credit.**
Refs: example M.
Expected: the credit is used on the next bill.

**AT-15 Mixed return.**
Refs: R14 fallback.
Expected: stock moves only for the back-on-the-shelf line.

**AT-16 Later-day refund.**
Refs: example N. **Blocked by Q11.**

**AT-17 Small cash sales.**
Refs: REQ-FLOW-06. **Blocked by Q7**; the current practice (one end-of-day bill) must work.

**AT-18 Daily close.**
Refs: R10, REQ-CASH-02.
Expected: USD and CDF counted separately; variance booked with a reason; the shift closes only with an empty queue.

**AT-19 Receipt from Importation.**
Refs: REQ-STK-03.
Expected: the manager confirms the receipt; stock up.

**AT-20 Local cash purchase.**
Refs: REQ-CASH-05.
Expected: stock up; cash down in the right currency.

**AT-21 Offline day.**
Refs: REQ-OFF-01/02.
Steps: two PCs offline; bills, payments, a new customer and a cash movement; a PC restart; reconnect.
Expected: everything syncs once.

**AT-22 Drafts after sync.**
Refs: REQ-OFF-02.
Expected: refused items appear as drafts; the manager resolves them.

**AT-23 Offline rate entry.**
Refs: REQ-OFF-04.
Expected: the manager's PIN is required; offline bills use the entered rate.

**AT-24 Visibility.**
Refs: REQ-USER-04, REQ-CRED-06.
Expected: head office sees all stores; a manager sees only their own store, including in ageing.

**AT-25 Daily report.**
Refs: REQ-REP-01.
Expected: sales by currency and expenses match a hand count for one day.

**AT-26 Negative stock list.**
Refs: REQ-STK-07.
Expected: oversold items are listed for the manager.

**AT-27 Backup and restore.**
Refs: `DEPLOYMENT.md`.
Expected: the latest backup restores to a fresh site and opens.
