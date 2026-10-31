# STATUS — as of 30 Oct 2026

**Phase:** P0 Foundations, in progress. **Next gate:** the M1 go/no-go, Mon 9 Nov (D-018).

## Schedule note

The plan set P0 for 26–29 Oct and M1 for 27 Oct – 2 Nov. P0 actually started on 30 Oct. M1 needs about 3 assistant days, 1 day of Sam's, and a 24-hour offline test (C8), so D-018 moves the go/no-go from 2 Nov to **Mon 9 Nov**. The 20 Nov freeze and the 1 Dec go-live are unchanged.

## Done

- Architecture and implementation plan approved (30 Oct).
- *Confirmed:* GitHub repository `adhanani90/ruhee-erp` with the docs on `main` (AGENTS, CLAUDE, SPEC, ACCOUNTING_RULES, ACCEPTANCE_TESTS, DECISIONS, STATUS, DEPLOYMENT).
- *Confirmed:* POS Awesome fork `adhanani90/POS-Awesome-V15` (parent `defendicon/POS-Awesome-V15`).
- *Confirmed:* M1 cards are GitHub issues #1 (M1-00) to #12 (M1-11): #1 (M1-00) and #2 (M1-01) closed, #3 to #12 open.
- *Confirmed:* `CLAUDE.md` already imports `AGENTS.md` (line 1 is `@AGENTS.md`), followed by the Claude Code notes.
- *Reported by Sam:* Windows clone of the repository; ChatGPT Project configured with initial instructions and source documents.
- *Confirmed:* M1-01 (#2) done: PR #15 merged 30 Oct.
- *Reported by Sam:* Codex audit of P0 and M1-01 done (30 Oct).
- *Confirmed:* M1 cards #3–#12 updated to the audit (30 Oct).
- *Confirmed:* docs audit PR #16 merged 30 Oct (`ffd9766`); M1-02 prep PR #17 (`required_apps`) merged 30 Oct (`e68168c`).
- *Confirmed:* M1-00 (#1) closed 30 Oct. *Reported by Sam,* with screenshots in #1: bench group on v16 in Cape Town; first deploy succeeded with frappe `2fcb939`, erpnext `9cd11b1`, posawesome `89ae16d`; Builder removed.

## In progress

- **M1-02 (#3):** staging site to be created Mon 2 Nov.
- **M1-03 (#4):** setup script done and run locally (`ruhee_erp/spike/setup_spike.py`); staging run and C1's screenshot wait on the M1-02 site.
- **M1-05 (#6), Codex; Claude Code reviews:** [draft PR #20](https://github.com/adhanani90/ruhee-erp/pull/20); scratch native C4 fails CDF-account validation. Store-rate/Payment Entry prototype passes C/$10,000 GL and C7 online locally. Invoice-only precision fails; full column sync + fresh 12-place source fixes C3 drifts. No native 50 FC payment rounding. [Evidence/design](../ruhee_erp/spike/M1-05.md). #5 draft/dev queue untouched.

## Next

1. M1-02 (#3) Deploy to the Frappe Cloud staging site and pin versions (Sam with Claude Code).
2. M1-03 to M1-10 (#4 to #11): the spike checks; M1-03 also captures C1's billing-screen screenshot.
3. M1-11 (#12) Spike report and go/no-go.

## Blocked or waiting

- M1-03's staging run waits on the M1-02 staging site.
- M1-05: scratch work complete; Claude Code review, browser/staging and offline integration remain. Staging freeze 4-6 Nov: no new rate records, item imports or config changes. No experiments on dev.localhost.
- *Reported by Sam:* a trial site, `ruhee-staging.v.frappe.cloud`, exists on a shared bench. It is not used for M1 and is deleted once staging is up.
- C1 and C12 need to know New Depo's browser and PC specification (Q9). Until then M1 uses any two PCs, and that is noted in the evidence.

## Open questions

| Q | Question | Needed before | Blocks |
| --- | --- | --- | --- |
| Q1 | Round CDF to the nearest 50 FC, or always up? | P2 rates work | R1, R3, R5; AUT-CUR-08, AUT-CUR-14; AT-03 |
| Q2 | Which rate applies to change given in the other currency? | P2 payment hooks | R12; AUT-CUR-18 |
| Q3 | Load opening customer debts at go-live, or keep them in the old system? | P3 migration | REQ-MIG-01, AUT-MIG-02, limits and ageing at go-live |
| Q4 | Is the remise X% of the amount paid or of the bill? Default X and number of days? | Go-live (manual remise in the MVP) | R9; AUT-CUR-07 (basis and amounts) |
| Q5 | With no rate entered, block CDF bills or use yesterday's with a warning? | P2 rates work | R11, I6; AUT-CUR-13 |
| Q6 | Who signs off ACCOUNTING_RULES: the parents, an accountant, or both? | P2 money code | All of P2 money work |
| Q7 | Small cash sales at New Depo: keep paper plus one end-of-day bill, or enter each sale? | Go-live | AT-17 |
| Q8 | Preset discount values, expense categories, and petty-cash float amounts if Q10 approves the float? | Go-live | REQ-PRICE-04, REQ-CASH-04 |
| Q9 | New Depo: number of PCs and facturiers, browser and OS, internet provider; add a hotspot? | M1 (C1, C12) and go-live | Evidence quality; offline planning |
| Q10 | Approve or change the proposals in SPEC §16? | Go-live | Listed items |
| Q11 | A later-day cash refund: return the amount originally paid in its currency, or the bill's USD value at that day's rate (base or higher)? | P2 returns work | R16; AUT-RET-05; AT-16 |

**Values not yet given:** Mbanzangu's X% (needed for the Mbanzangu rollout, not New Depo).

**Interpretations to confirm:** see `SPEC.md` §17.

**Working model:** Claude Code, Codex and ChatGPT build and review; Claude (chat) maintains the spec and the accounting rules. D-017 amends D-012.

## Risks to watch now

1. POS Awesome on v16 (C1, C2), and holding the 9 Nov gate (D-018), which leaves 9 working days before the 20 Nov freeze.
2. Accounting sign-off timing (Q6), since it gates the P2 money work.
3. Offline data safety: verified in C8 and C9.
