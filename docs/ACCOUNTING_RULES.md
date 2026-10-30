# ACCOUNTING_RULES — Ruhee ERP

**Status:** approved as part of the plan on 30 Oct 2026. **Awaiting accounting sign-off** (§9). The signatory is still to be decided (Q6).
**Change control:** changes only through a docs-only PR approved by Sam, followed by a fresh sign-off.
**Tests:** every example in §7 and every invariant in §6 has a planned automated test; see `ACCEPTANCE_TESTS.md` §2.

---

## 1. The model

The books run in USD, and every customer owes in USD. Each store holds USD and CDF cash in separate accounts. CDF is valued at that store's base rate for the day, so the spread between the base and higher rates lands in Exchange income. Later rate movements land in FX gain/loss.

## 2. ERPNext behaviour this model relies on

Source: ERPNext multi-currency accounting and credit-note documentation. Each point is confirmed in the M1 check shown.

- One account holds one currency, so each store gets a Cash USD and a Cash CDF account. ERPNext blocks changing an account's currency once it has submitted, uncancelled entries.
- With the customer account in USD (company currency), the setting **Allow multi-currency invoices against single party account** lets CDF bills post to it, and the ledger stays in USD. (C3)
- The USD price list converts through its own rate, separate from the bill's exchange rate.
- A cross-currency payment is a Payment Entry. Its exchange difference is cleared through a deduction row before submitting. (C4)
- Open balances at a reporting date are revalued with Exchange Rate Revaluation.
- With no stored rate, ERPNext can call an outside rate provider. **That fallback must be switched off** (REQ-CUR-07).
- A credit note is created from the original bill. It copies the bill's items, prices and accounts, can't exceed the quantity sold, can skip the stock update, and is refunded by a payment or allocated against later bills. Whether it also keeps the original exchange rate is checked in C13.

## 3. Accounts

These are management accounts, not SYSCOHADA, plus Sales, Cost of goods sold, Stock per store and expense categories (categories Open, Q8).

| Account | Currency | Purpose |
| --- | --- | --- |
| Debtors | USD | Every customer balance |
| Cash USD – store | USD | Sales drawer |
| Cash CDF – store | CDF | Sales drawer |
| Petty cash USD / CDF – store | USD / CDF | Expense float; **proposal, Q10** |
| Office cash USD / CDF | USD / CDF | Takings carried from the Kinshasa stores |
| Bank | per account | Mbanzangu wires |
| Exchange income | USD | Spread from the higher rate (R3, R5) |
| FX gain/loss | USD | Revaluation, transfers, refunds paid at a later day's rate |
| Round-off | USD | 50 FC rounding |
| Remises accordées | USD | Early-payment discounts |
| Cash over/short | USD | Daily count variances |

## 4. Rules

"Base" and "higher" mean the store's two rates for the day, for example 2300 and 2320 CDF per USD.

| Rule | When | Calculation | Status |
| --- | --- | --- | --- |
| R1 | CDF bill | Each USD price × base rate; total rounded to 50 FC | Confirmed by owner; rounding direction Open (Q1) |
| R2 | CDF bill paid in USD | USD = CDF ÷ base rate, to the cent | Confirmed by owner |
| R3 | USD bill paid in CDF | CDF = USD × higher rate, rounded to 50 FC | Confirmed by owner; rounding direction Open (Q1) |
| R4 | Any unpaid part | Becomes a USD balance; for a CDF bill, unpaid CDF ÷ that day's base rate | Confirmed by owner |
| R5 | USD balance paid later in CDF | CDF = USD × the payment day's higher rate | Confirmed by owner |
| R6 | USD balance paid in USD | No conversion | Confirmed by owner |
| R7 | Valuing CDF received | At the store's base rate of the day. The whole gap to the USD settled, including any 50 FC rounding of the payment (R3, R5), goes to Exchange income; it can be negative on small amounts. | Plan-approved; payment rounding included by Sam, 30 Oct 2026; awaiting sign-off |
| R8 | Month end | CDF accounts revalued at head office's base rate; the change goes to FX gain/loss | Plan-approved; awaiting sign-off |
| R9 | Remise | X% of the amount settled within N days, to Remises accordées | Plan-approved; basis and defaults Open (Q4) |
| R10 | Daily close | Each drawer counted in its own currency; differences to Cash over/short, with a reason | Plan-approved; awaiting sign-off |
| R11 | Rates | One or more records per store per day, each with base, higher and an effective time, entered by the manager before the first CDF bill. A mid-day change adds a record effective from its time; earlier records, and the documents that used them, are unchanged. Offline PCs take a manual entry with a manager PIN | Plan-approved; no-rate behaviour Open (Q5) |
| R12 | Change given in the other currency | Base rate assumed | Open (Q2) |
| R13 | Any return | A credit note created from the original bill: it copies the bill's items, prices and accounts and can't return more than was sold. Goods sold before go-live use POS Awesome's return without invoice, managers and head office only | Plan-approved |
| R14 | Restocking | The manager marks each returned line back on the shelf or not. Back on the shelf re-adds stock at its original cost; otherwise no stock moves (an item missing at livraison, or damaged). See the mixed-return fallback below | Plan-approved; mechanism confirmed in C13 |
| R15 | Credit-note rate | The credit note keeps the original bill's currency and rate, reversing exactly the USD value first recorded | Plan-approved; to confirm in C13 |
| R16 | Settling a return | On an unpaid bill, the credit note lowers the USD balance. As credit, it becomes a USD credit used against later bills. As a cash refund, it is a negative payment from the drawer, in the currency and at the rate set by Q11 | Plan-approved; refund currency and rate Open (Q11) |
| R17 | Swap | A return of the line plus a new bill for the replacement, billed like any sale. Any difference is collected or refunded under R1–R6 and R16 | Plan-approved |

**Mixed-return fallback (R14).** ERPNext's Update Stock setting applies to a whole credit note. If C13 shows that one credit note can't mix restocked and non-restocked lines, `ruhee_erp` splits the manager's single return into two credit notes against the same bill, created and printed together: one with stock update and one without. The manager still marks lines one by one, so the policy is unchanged.

## 5. Rounding

- CDF amounts on bill totals (R1) and on converted payments (R3, R5) are rounded to 50 FC, the smallest tender. **Direction: Open (Q1)**, to the nearest 50 or always up. M1 (C6) records what ERPNext does natively.
- USD amounts are rounded to the cent.
- Rounding on a bill total (R1) posts to Round-off. Rounding on a converted payment (R3, R5) is part of the R7 gap and posts to Exchange income.

## 6. Invariants

Each invariant has a planned automated test.

- **I1** A printed bill matches the recorded invoice: prices, discounts, totals.
- **I2** For each bill without returns, the USD amounts allocated to it by payments (remise deductions included), plus its USD balance, equal the USD amount debited to Debtors for it, to the cent. The base-rate value of the cash received can differ from the amount allocated; the difference is Exchange income (R7). Bills with returns are covered by I9.
- **I3** Customer balances exist only in USD.
- **I4** Exchange income arises only from R3 and R5. FX gain/loss arises only from revaluation, transfers and refunds paid at a later day's rate.
- **I5** After the daily close, each cash account's balance in its own currency equals the count, with any variance booked.
- **I6** Every CDF bill and cross-currency payment references a store rate record.
- **I7** Each bill moves stock exactly once, including after an offline sync.
- **I8** Every bill, payment and credit note keeps the rates it was made with. Adding or changing a rate never alters a submitted document, a balance or a reprint.
- **I9** A return never exceeds what was sold, counting earlier returns against the same bill. Stock re-enters only for lines marked back on the shelf, and only once. The reversal's USD value equals the original line's value for the quantity returned, after the line's discount, to the cent. Returns without an invoice (goods sold before go-live) are outside I9.

## 7. Worked examples

### Sales and payments (A–I and O)

Rates are 2300/2320 unless stated. Sales and stock lines are shown only in A.

| Ex | Situation | Customer pays | Ledger (USD values) | Balance after |
| --- | --- | --- | --- | --- |
| A | $100 item on a CDF bill: 230,000 FC | 230,000 FC | Dr Debtors $100, Cr Sales $100; Dr Cash CDF 230,000 FC ($100.00), Cr Debtors $100 | $0 |
| B | Same CDF bill | $100 | Dr Cash USD $100, Cr Debtors $100 | $0 |
| C | $100 USD bill | 232,000 FC | Dr Cash CDF 232,000 FC ($100.87); Cr Debtors $100, Cr Exchange income $0.87 | $0 |
| D | 230,000 FC CDF bill | 115,000 FC now | Dr Cash CDF 115,000 FC ($50.00), Cr Debtors $50 | $50.00 |
| E | D's balance on a later day at 2400/2420 | 121,000 FC | Dr Cash CDF 121,000 FC ($50.42); Cr Debtors $50, Cr Exchange income $0.42 | $0 |
| F | $100 USD bill, split | $50 + 116,000 FC | Dr Cash USD $50, Dr Cash CDF 116,000 FC ($50.43); Cr Debtors $100, Cr Exchange income $0.43 | $0 |
| G | $50 balance paid inside the remise window, 2% of the amount settled (illustrative; basis, X and N Open, Q4) | $49 | Dr Cash USD $49, Dr Remises accordées $1; Cr Debtors $50 | $0 |
| H | CDF bill: a $34 item less a 890 FC manager discount, 77,310 FC | – | Nearest: 77,300 FC, -10 FC, under a cent, so no Round-off entry. Up: 77,350 FC, +40 FC, $0.02 to Round-off. **Depends on Q1** | – |
| I | 1,000,000 FC held, booked at 2300; month-end base 2350 | – | Revaluation from $434.78 to $425.53: Dr FX gain/loss $9.25, Cr Cash CDF $9.25 | – |
| O | $1.00 balance paid later in CDF | 2,320 FC before rounding | Nearest: 2,300 FC ($1.00), Cr Debtors $1, no Exchange income. Up: 2,350 FC ($1.02), Cr Debtors $1, Cr Exchange income $0.02. **Depends on Q1** | $0 |

Check figures: 232,000 ÷ 2300 = 100.8696; 121,000 ÷ 2400 = 50.4167; 116,000 ÷ 2300 = 50.4348; 1,000,000 ÷ 2300 = 434.7826; 1,000,000 ÷ 2350 = 425.5319; 2,350 ÷ 2300 = 1.0217.

### Returns, refunds and swaps (J–N)

Rates are 2300/2320, same day unless stated. Cost-of-goods lines are left out.

| Ex | Situation | Ledger (USD values) | Balance after |
| --- | --- | --- | --- |
| J | Wrong item at livraison on a USD bill, swapped for another $20 item | Credit note: Dr Sales $20, Cr Debtors $20, wrong item back on the shelf. New bill: Dr Debtors $20, Cr Sales $20, correct item out. No cash moves | Unchanged |
| K | Item missing at livraison on a 46,000 FC bill paid in CDF, refunded the same day | Credit note: Dr Sales $20, Cr Debtors $20, no stock movement. Refund: Dr Debtors $20, Cr Cash CDF 46,000 FC ($20.00) | $0 |
| L | D's $50 balance; the customer returns goods worth 115,000 FC on the original bill | Credit note at the bill's 2300: Dr Sales $50, Cr Debtors $50; goods back on the shelf at original cost | $0 |
| M | $30 item on a paid USD bill returned for credit; next bill $50 | Credit note: Dr Sales $30, Cr Debtors $30; the $30 credit is applied to the next bill | $20 owed |
| N | 230,000 FC paid bill refunded a week later, at 2400/2420 | Credit note at the bill's 2300: Dr Sales $100, Cr Debtors $100. Then the refund, **depending on Q11**: Refunding the original francs: Dr Debtors $100; Cr Cash CDF 230,000 FC ($95.83), Cr FX gain/loss $4.17. Refunding the USD value at the base rate: 240,000 FC out, no FX | $0 |

Check figures: 46,000 ÷ 2300 = 20.00; 230,000 ÷ 2400 = 95.8333.

## 8. Open points affecting these rules

| Q | Affects | What's needed |
| --- | --- | --- |
| Q1 | R1, R3, R5, examples H and O | Round to the nearest 50 FC, or always up? |
| Q2 | R12 | Which rate applies to change given in the other currency? |
| Q4 | R9, example G | Is the remise a percentage of the amount paid or of the bill? What are the default X and number of days? |
| Q5 | R11, I6 | With no rate entered: block CDF bills, or use yesterday's with a warning? |
| Q6 | Sign-off | Who signs these rules off: Sam's parents, an accountant, or both? |
| Q11 | R16, example N | A later-day cash refund: return the amount originally paid in its currency, or the bill's USD value at that day's rate (and if so, base or higher)? |

## 9. Sign-off

| Role | Name | Date | Scope signed |
| --- | --- | --- | --- |
| Owner (Sam) | | | R1–R6 confirmed in conversation, Oct 2026; full document pending |
| Accounting signatory (Q6) | | | Pending |

Rates code (P2) does not start until this table is signed, apart from rules that depend on an open question; those wait for the answer.
