# SPEC — Ruhee ERP, New Depo pilot

**Status:** v1.0, from the architecture and implementation plan approved on 30 Oct 2026.
**Related:** money rules in `ACCOUNTING_RULES.md`; tests in `ACCEPTANCE_TESTS.md`; open questions Q1–Q11 in `STATUS.md`; decisions in `DECISIONS.md`.

Requirements are numbered `REQ-<area>-nn`. Anything not yet decided is marked **Open (Qn)**. Proposals the owners have not yet approved are listed in §16 and are not requirements.

---

## 1. Purpose and scope

- **REQ-SCOPE-01** Replace the current system at Ruhee's three stores: Ruhee Depo and New Depo (Kinshasa) and Mbanzangu (outside Kinshasa). They trade under one banner as one company.
- **REQ-SCOPE-02** The pilot is New Depo, live on 1 Dec 2026 alongside the old system until the exit criteria in `DEPLOYMENT.md` are met.
- **REQ-SCOPE-03** At least two more stores are planned, each with its own stock and till. Adding a store must be configuration, not code.
- **REQ-SCOPE-04** Ruhee Importation is a separate company, built after the stores. Whether it goes on the same site or a separate installation is **Open (Q10 proposal)**. Until then, Importation is a supplier to the stores.

**Out of scope (do not build):** the DGI facture normalisée (the owners' decision), delegates, purchase orders and supplier advances, landed costs in the system, batch and expiry tracking, cold-chain or controlled-drug registers, SYSCOHADA statements, payroll, fixed assets, projects.

**Later, not v1:** WhatsApp statements, pre-orders, expiry alerts, a returns time-limit policy, Importation.

## 2. Users and roles

- **REQ-USER-01** Only managers and facturiers have PCs and logins. Each store has 1–4 facturiers, configurable; today there are 3 managers, 7 facturiers and 2 head-office users.
- **REQ-USER-02** The cashier, packers (préparation) and livraison have no login. They work from the printed bill.
- **REQ-USER-03** Roles: Facturier, Store Manager, Head Office, and System Manager (Sam only). Permissions must stay adjustable without code changes.
- **REQ-USER-04** Store users see only their own store's warehouse, billing profile, cost centre and documents. Head office sees all stores.
- **REQ-USER-05** The interface is in French; a per-user switch to English is acceptable.

## 3. Counter sales flow

- **REQ-FLOW-01** The facturier makes the bill with the customer. It records the customer (named, or "Client comptant"), the bill currency (USD or CDF, chosen with the customer), items in selling units, preset discounts only, and the payment method and share paid (full, part or credit), all known at billing.
- **REQ-FLOW-02** Stock is deducted when the bill is submitted, as one Sales Invoice per bill, with no end-of-shift consolidation.
- **REQ-FLOW-03** Stale stock figures are acceptable. Overselling is allowed (negative stock) and is resolved by a quick purchase or a refund.
- **REQ-FLOW-04** The bill prints on A4 in French. The cashier collects the money and stamps the bill (manual cash drawer, no PC). Packers fill the order from the bill. Livraison checks each item with the client and validates.
- **REQ-FLOW-05** Goods leave even when the bill is not fully paid.
- **REQ-FLOW-06** The flow is the same for every customer type. Small cash sales: today the manager notes them on paper and enters one combined bill at day end. The system must support that practice; whether to change it is **Open (Q7)**.
- **REQ-FLOW-07** A wrong or missing item found at livraison is handled by the manager as a return with a refund, or as a swap, depending on the customer (§7).

## 4. Currency and rates

Detailed rules: `ACCOUNTING_RULES.md` R1–R12.

- **REQ-CUR-01** The company currency is USD. Prices are kept in USD.
- **REQ-CUR-02** Each bill is in one currency and shows only that currency. Printing the remaining balance in USD and the split amounts per currency is a proposal (§16).
- **REQ-CUR-03** Each store's manager enters two rates at opening, from the market: a base rate (e.g. 2300) and a higher rate (e.g. 2320). Rates may differ between stores and may change during the day, though rarely.
- **REQ-CUR-04** Conversions follow R1–R6, and unpaid amounts become USD balances (R4). The smallest CDF tender is 50 FC. The rounding direction is **Open (Q1)**.
- **REQ-CUR-05** What happens when no rate has been entered is **Open (Q5)**.
- **REQ-CUR-06** Every document keeps the rates it was made with (I8).
- **REQ-CUR-07** ERPNext's external exchange-rate provider is never used for transactions.
- **REQ-CUR-08** The rate for change given in the other currency is **Open (Q2)**.

## 5. Pricing and discounts

- **REQ-PRICE-01** There is one base USD price list.
- **REQ-PRICE-02** Mbanzangu's prices are base +X%, with individual price edits. X has not yet been given. The price-list builder is a proposal for after launch (§16).
- **REQ-PRICE-03** Managers may change prices. Every change is logged with who, when, the old value and the new value.
- **REQ-PRICE-04** Facturiers apply only discounts the manager has preset (values **Open (Q8)**). Managers may give any discount. Discounts are recorded per line with the user.
- **REQ-PRICE-05** Customer-specific price lists, including percentage changes, are supported as standard price lists. Printed prices always equal recorded prices (I1).
- **REQ-PRICE-06** Store managers may see cost prices and margins.

## 6. Credit and collections

- **REQ-CRED-01** A bill can be fully paid, part-paid or on credit. The unpaid part becomes a USD balance (R4).
- **REQ-CRED-02** Managers decide who gets credit. Credit limits, in USD, are set and changed only by head office.
- **REQ-CRED-03** Store roles cannot submit a credit sale beyond the customer's limit. There is no minimum upfront payment, no block on overdue customers who are under their limit, and no late fees.
- **REQ-CRED-04** Later payments are taken at the billing PC, in USD or CDF (R5, R6).
- **REQ-CRED-05** Early-payment remise: X% off if paid within N days, usually the same for all customers, booked as an expense (Remises accordées). The basis and the defaults are **Open (Q4)**. In the MVP a manager applies it at payment; automation comes after launch.
- **REQ-CRED-06** The collections view shows head office all stores and managers their own, sorted oldest first in the MVP. Colour coding at 7/10/15/30 days comes after launch. The ageing basis and buckets are a proposal (§16). There are no push alerts.
- **REQ-CRED-07** Statements are printed; WhatsApp comes later. Showing the CDF equivalent at today's rate on statements is a proposal (§16).
- **REQ-CRED-08** Whether opening customer debts are loaded at go-live is **Open (Q3)**.

## 7. Returns, refunds and swaps

The policies below are the owners'; the mechanics are rules R13–R17.

- **REQ-RET-01** Only managers and head office process returns, refunds and swaps.
- **REQ-RET-02** Outcomes:
  - A cash refund or credit, depending on how long it's been. Time limits come later.
  - At livraison, a refund or a swap, depending on the customer.
  - Goods unpaid for too long can be taken back as a stock return.
- **REQ-RET-03** Every return is a credit note against the original bill (R13). Goods sold before go-live use POS Awesome's return without invoice, managers and head office only.
- **REQ-RET-04** The manager marks each returned line as back on the shelf or not (R14). One return may contain both kinds of line.
  - If one credit note can't handle both, the system splits the return into two credit notes against the same bill: one updating stock, one not, created and printed together.
  - This fallback is confirmed or ruled out in M1 (C13).
- **REQ-RET-05** A credit note reverses at the original bill's currency and rate (R15). The currency and rate for a refund made on a later day are **Open (Q11)**.
- **REQ-RET-06** A swap is a return plus a new bill (R17).
- **REQ-RET-07** POS Awesome may not support returns offline. Until M1 shows otherwise, returns are entered once the connection is back, from the printed bill.

## 8. Cash

- **REQ-CASH-01** Each store has a USD drawer and a CDF drawer, counted daily. Each drawer is its own account in its own currency.
- **REQ-CASH-02** The manager closes the day by counting each currency. Variances are booked with a reason (R10). A shift closes only when the PC's offline queue is empty.
- **REQ-CASH-03** Kinshasa stores carry cash to the office; Mbanzangu sends it by bank wire. Both are recorded as transfers and confirmed on receipt. The office holds the stores' cash and Importation's cash in separate accounts.
- **REQ-CASH-04** Expenses and local cash purchases are paid from store takings today, and the owners want better practice. A petty-cash float per store is a proposal (§16). Expense categories are **Open (Q8)**.
- **REQ-CASH-05** Stores may buy locally from any supplier, paying in cash, recorded as a purchase invoice with stock update. Centralised purchasing is planned for later.

## 9. Stock

- **REQ-STK-01** There are 1,000–5,000 products, each with one selling unit set per product (a strip, a 10×10 box, and so on). Purchases are entered as counts of selling units.
- **REQ-STK-02** Each store has one stock location.
- **REQ-STK-03** Receipts from Importation are purchases from the supplier "Ruhee Importation" until Importation is in the system. The receiving manager confirms them.
- **REQ-STK-04** Store-to-store transfers stay in transit until the receiving manager confirms them. This comes after launch, since only one store is live at go-live.
- **REQ-STK-05** Stock is counted quarterly, with a head-office person present.
- **REQ-STK-06** Product codes are typed; barcodes are not required.
- **REQ-STK-07** The manager gets a daily list of items with negative stock.

## 10. Offline

- **REQ-OFF-01** Each billing PC works on its own, offline, for up to a week: bills, payments, new customers and cash movements. At minimum, billing must work.
- **REQ-OFF-02** When the connection returns, queued items sync automatically with nothing lost or duplicated. Any that fail become drafts for the manager.
- **REQ-OFF-03** Offline PCs use the last synced prices, stock and credit limits. Head office sees a store's sales after they sync.
- **REQ-OFF-04** The manager can enter the day's rates on each PC while offline, using a manager PIN.
- **REQ-OFF-05** Staff never clear browser data on billing PCs. The printed bills are the backup.
- **REQ-OFF-06** Payments are handled by hand at the cash desk and may be recorded after the fact.

## 11. Controls and audit

- **REQ-CTRL-01** Facturiers cannot change prices, credit limits or posting dates, give discounts beyond the presets, cancel bills, or process returns.
- **REQ-CTRL-02** Managers can change prices (logged), give any discount, cancel bills, process returns and close shifts. They cannot change credit limits.
- **REQ-CTRL-03** Only head office can delete documents. Submitted documents are cancelled and amended, never edited.
- **REQ-CTRL-04** Track Changes is on for prices, items, customers, billing profiles and rate records, and login history is kept.
- **REQ-CTRL-05** Head-office and admin accounts use two-factor login.
- **REQ-CTRL-06** Head office sees everything centrally. A nightly exceptions report comes after launch.

## 12. Reports

- **REQ-REP-01** Daily, in the MVP: sales by store and currency, payment status, expenses, and an ageing list sorted oldest first.
- **REQ-REP-02** Monthly, after launch and ready for the 31 Dec close: P&L per store and combined.
- **REQ-REP-03** After launch: colour-coded ageing, price-change alerts, and a nightly exceptions email.

## 13. Data migration

- **REQ-MIG-01** The source is Excel exports from the old system. Load:
  - items: code, name, selling unit, USD price;
  - customers: name, phone, credit limit;
  - opening stock, from a physical count;
  - opening cash per currency.
  Whether opening debts are loaded is **Open (Q3)**.
- **REQ-MIG-02** Sales history stays in the old system for now.
- **REQ-MIG-03** Validation scripts run before every import, and imported totals must reconcile with the old system. Mappings are in `DATA_MAPPING.md` (ChatGPT, P2).

## 14. Platform and architecture

**Components**

- A Frappe Cloud private bench with two sites, staging and production. Each site needs a plan of $25 or more a month; the target is about $50–75 a month in total, under the $100 ceiling.
- ERPNext and Frappe 16, pinned to one release.
- POS Awesome, forked and pinned to a tested commit. It is the facturiers' billing screen and offline queue.
- `ruhee_erp`: store rates, payment and return rules, print format, reports, settings as code, and tests.
- A browser on each store PC and head-office laptop. Nothing is installed locally.

| Need | How | Type | Status |
| --- | --- | --- | --- |
| Stores with their own stock and results | A warehouse and cost centre per store | Config | Standard |
| USD books, CDF bills on USD customer accounts | Company in USD; the "Allow multi-currency invoices against single party account" setting | Config | Documented; test in M1 |
| Daily base and higher rate per store | A custom rate record and hooks | Custom | To build after M1 |
| Cross-currency payments and exchange income | Payment Entry with a deduction to Exchange income | Native plus custom glue | Documented; test in M1 |
| CDF rounding to 50 FC | Currency rounding setting | Config | Test in M1 |
| Billing, credit, part-payments, later collections | POS Awesome | App | README; test on v16 |
| Offline bills and payments | POS Awesome offline queue | App | README; test on v16 |
| Stock deducted per bill | Each bill its own Sales Invoice with stock update | Config | Test in M1 (standard POS posts only at shift close) |
| Overselling | Negative stock allowed | Config | Test with offline sync |
| Credit limits set only at head office | Field permissions; no store user has the credit-override role | Config | Standard |
| Daily close per currency | POS Awesome shift close, with a custom view if needed | App or custom | Test in M1 (its cash movements reconcile in company currency) |
| Returns, refunds and swaps | Credit note against the original bill; POS Awesome returns and customer payouts | Native plus app | Documented; test in M1 (C13) |
| A4 bill | Print format in the app | Custom | To build (ChatGPT, P2) |
| Ageing by store | Accounts Receivable report; colour view later | Config, then custom | Documented |
| Audit trail | Track Changes and Activity Log | Config | Documented |
| Data import | ERPNext Data Import plus validation scripts | Config and scripts | To build |
| Backups | Frappe Cloud site backups | Config | Confirm schedule; restore test |

**Assumptions M1 must prove (none may be relied on before then)**

- POS Awesome installs and runs on v16 on Frappe Cloud. One user reported a blank screen on v16 in February 2026.
- It posts each bill as its own Sales Invoice with stock update.
- Its multi-currency handling produces examples A–F using our store rates, not a fetched rate.
- Offline queues survive PC restarts and multi-day outages on two PCs.
- A 5,000-item catalogue performs on New Depo's PCs.
- A credit note on a CDF bill reverses at the bill's own rate, and refunds work from either drawer.
- Whether returns work offline, and whether one credit note can mix restocked and non-restocked lines.

**Fallbacks if M1 fails** (decided by Sam at the go/no-go)

| Option | Keeps | Costs |
| --- | --- | --- |
| An earlier POS Awesome commit, or ERPNext 15 where the fork is mature | Everything planned | Older platform; an upgrade in 2027 |
| POSNext | Offline billing, part-payments, credit | Mixed-currency payment to build; its production branch targets v15 |
| ERPNext's own invoice screen, online, with a hotspot and a paper fallback keyed in after outages | Accounting correctness; simplest build | Offline billing in the system |

**How things are built**

- Print formats, reports, custom fields and roles live in the app, versioned in Git.
- Imports use templates defined in `DATA_MAPPING.md`, run through a validation script, then ERPNext's Data Import.
- One pinned ERPNext release and one POS Awesome commit, recorded in `DEPLOYMENT.md`. Auto-updates are off; upgrades happen only after a staging test.

## 15. Minimum viable system for 1 Dec, and what follows

**MVP, New Depo only**

- Bills in USD or CDF at the store's rates under R1–R6, with payment method and share marked at billing, and CDF rounded to 50 FC.
- Part-payments and credit as USD balances, with limits set only by head office. Later payments in either currency.
- Stock deducted per bill, with overselling allowed. Opening stock loaded; receipts from Importation and local cash purchases recorded.
- Returns, refunds and swaps by managers.
- The A4 bill, matching the paper flow.
- Daily close per currency, with variances booked.
- Offline billing and payments on each PC, or the fallback chosen at the M1 go/no-go.
- Roles, store restrictions, preset discounts and the audit trail.
- A daily sales and expenses report, and an ageing list sorted oldest first.
- Backups, with one tested restore.

**After launch, in this order**

1. Colour-coded ageing view.
2. Price-change alerts and a nightly exceptions email.
3. Automatic early-payment remise.
4. The petty-cash float, if approved.
5. Monthly P&L by store and combined, ready for the 31 Dec close.
6. The Mbanzangu price builder, then Ruhee Depo and Mbanzangu go live.
7. Store-to-store transfers.
8. Later: Importation, WhatsApp statements, pre-orders, batch and expiry.

## 16. Proposals awaiting the owners' approval (Q10)

These are **not requirements** until approved:

- Importation as a second company on the same site, rather than a separate installation.
- The bill prints the remaining balance in USD and, for split payments, the amount to collect in each currency.
- A petty-cash float per store, kept apart from sales cash.
- Each small cash sale entered as it happens.
- A second internet connection (mobile-data hotspot) per store.
- Ageing counted from the bill date, in buckets of 0–7, 8–10, 11–15, 16–30 and over 30 days.
- Statements showing the CDF equivalent at today's rate.
- A price-list builder for Mbanzangu (base +X%, keeping manual edits).

## 17. Interpretations to confirm

- "Functions yeah, not a record": fridges and storage exist, but no temperature or controlled-drug register is needed.
- "All 3 open at once": the three stores trade the same hours, and no till is shared between stores.
- "Production launch on 1 Dec": New Depo is live alongside the old system, not replacing it on day one.
