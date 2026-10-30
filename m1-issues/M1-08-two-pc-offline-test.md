# M1-08 Two-PC offline test (C8, C9)
<!-- labels: owner:sam,owner:chatgpt,owner:claude-code -->

**Owners:** ChatGPT drafts the protocol sheet from this card; Sam runs it; Claude Code verifies the results · **Size:** 2 days elapsed (24+ hours offline) · **Depends on:** M1-03, M1-05, M1-07
**Refs:** C8, C9; SPEC REQ-OFF-01..05, REQ-FLOW-03, REQ-CRED-03; ACCOUNTING_RULES I7

### Goal
Prove on two real PCs that a long offline period loses nothing and duplicates nothing, and that oversold and over-limit bills behave as specified.

### Protocol (ChatGPT turns this into a one-page sheet in French)
1. Use PCs A and B, both online. Open a shift on each and let the catalogue load.
2. Disconnect both from the internet for at least 24 hours.
3. On each PC:
   - 15 bills: 5 cash (USD and CDF), 5 split, 5 credit;
   - 2 later payments;
   - 1 new customer;
   - 1 bill for an item with too little stock;
   - 1 credit bill over the $100 limit.
   Write every bill number and amount on paper.
4. Restart the browser once and the PC once during the outage.
5. Reconnect and wait for both queues to empty.

### Verification (Claude Code)
A script compares the system with the paper log: counts, totals, no duplicates (by request identity and by content), negative stock on the oversold item, and the over-limit bill present as a draft.

### Acceptance criteria
- [ ] **C8:** 30 bills, 4 payments and 2 customers synced, nothing lost, nothing duplicated.
- [ ] **C9:** the oversold item shows negative stock, and the over-limit bill is a draft visible to the manager.

### Evidence
Photo of the paper log, the verification output, and screenshots of empty queues and the draft.
