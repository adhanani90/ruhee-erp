"""Read-only C7 verifier (M1-05, PR #25). Spike code only.

Reads saved invoices by client request ID: invoice, lines, payments, linked Payment
Entries, GL, stock ledger, POS Awesome's submission ledger and the bound rate
record. No save, insert, submit, set_value, commit, raw SQL or resubmission.

    bench --site <site> execute ruhee_erp.spike.store_rate_verify.run \
        --kwargs '{"request_ids": ["inv-..."], "expect": {"inv-...": {...}}}'
"""

import hashlib
import json
from pathlib import Path

import frappe
from frappe.utils import flt

from ruhee_erp.spike.store_rate_hooks import RATE_TYPE, site_enabled

LEDGER = "POS Invoice Submission Ledger"
GL_FIELDS = [
	"name",
	"account",
	"account_currency",
	"debit",
	"credit",
	"debit_in_account_currency",
	"credit_in_account_currency",
	"transaction_exchange_rate",
	"is_cancelled",
]


def _gl(voucher_type, voucher_no):
	return frappe.get_all(
		"GL Entry",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "is_cancelled": 0},
		fields=GL_FIELDS,
		order_by="account, name",
	)


def _account_totals(rows):
	out = {}
	for row in rows:
		name = row.account.rsplit(" - ", 1)[0]
		entry = out.setdefault(name, {"debit": 0, "credit": 0, "debit_fc": 0, "credit_fc": 0})
		entry["debit"] = flt(entry["debit"] + row.debit, 2)
		entry["credit"] = flt(entry["credit"] + row.credit, 2)
		entry["debit_fc"] = flt(entry["debit_fc"] + row.debit_in_account_currency, 2)
		entry["credit_fc"] = flt(entry["credit_fc"] + row.credit_in_account_currency, 2)
	return out


def _digest(value):
	return hashlib.sha256(frappe.as_json(value).encode()).hexdigest()


def invoice_state(name):
	si = frappe.get_doc("Sales Invoice", name)
	pe_names = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": "Sales Invoice", "reference_name": name, "docstatus": 1},
		pluck="parent",
	)
	payments = []
	for pe_name in sorted(set(pe_names)):
		pe = frappe.get_doc("Payment Entry", pe_name)
		payments.append(
			{
				"name": pe.name,
				"docstatus": pe.docstatus,
				"ruhee_c7_rate": pe.get("ruhee_c7_rate"),
				"paid_amount": pe.paid_amount,
				"received_amount": pe.received_amount,
				"base_received_amount": pe.base_received_amount,
				"target_exchange_rate": pe.target_exchange_rate,
				"deductions": [{"account": d.account, "amount": d.amount} for d in pe.deductions],
				"gl": _account_totals(_gl("Payment Entry", pe.name)),
			}
		)
	sle = frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_type": "Sales Invoice", "voucher_no": name, "is_cancelled": 0},
		fields=["item_code", "actual_qty"],
	)
	state = {
		"name": si.name,
		"docstatus": si.docstatus,
		"currency": si.currency,
		"conversion_rate": si.conversion_rate,
		"posa_client_request_id": si.get("posa_client_request_id"),
		"ruhee_c7_rate": si.get("ruhee_c7_rate"),
		"ruhee_c7_base": si.get("ruhee_c7_base"),
		"ruhee_c7_higher": si.get("ruhee_c7_higher"),
		"ruhee_c7_issued_at": si.get("ruhee_c7_issued_at"),
		"ruhee_c7_issued_at_local": str(si.get("ruhee_c7_issued_at_local") or ""),
		"ruhee_c7_hold": si.get("ruhee_c7_hold"),
		"ruhee_c7_tender_cdf": si.get("ruhee_c7_tender_cdf"),
		"ruhee_c7_allocation_usd": si.get("ruhee_c7_allocation_usd"),
		"posting_date": str(si.posting_date),
		"posting_time": str(si.posting_time),
		"created": str(si.creation),
		"items": [
			{
				"item_code": i.item_code,
				"qty": i.qty,
				"ruhee_c7_usd_price": i.get("ruhee_c7_usd_price"),
				"price_list_rate": i.price_list_rate,
				"rate": i.rate,
				"amount": i.amount,
				"base_amount": i.base_amount,
			}
			for i in si.items
		],
		"grand_total": si.grand_total,
		"rounded_total": si.rounded_total,
		"base_grand_total": si.base_grand_total,
		"base_rounded_total": si.base_rounded_total,
		"paid_amount": si.paid_amount,
		"base_paid_amount": si.base_paid_amount,
		"outstanding_amount": si.outstanding_amount,
		"invoice_payments": [
			{
				"mode_of_payment": p.mode_of_payment,
				"amount": p.amount,
				"base_amount": p.base_amount,
				"posa_payment_currency": p.get("posa_payment_currency"),
				"posa_original_amount": p.get("posa_original_amount"),
			}
			for p in si.payments
			if flt(p.amount) or flt(p.get("posa_original_amount"))
		],
		"gl": _account_totals(_gl("Sales Invoice", si.name)),
		"payment_entries": payments,
		"stock_ledger_entries": len(sle),
	}
	if si.get("ruhee_c7_rate"):
		rate = frappe.get_doc(RATE_TYPE, si.ruhee_c7_rate)
		state["rate_record"] = {
			"name": rate.name,
			"pos_profile": rate.pos_profile,
			"effective_from": str(rate.effective_from),
			"base": rate.base,
			"higher": rate.higher,
		}
	state["digest"] = _digest({k: v for k, v in state.items() if k != "digest"})
	return state


def by_request_id(request_id):
	invoices = frappe.get_all(
		"Sales Invoice", filters={"posa_client_request_id": request_id}, pluck="name", order_by="name"
	)
	ledger = frappe.get_all(
		LEDGER,
		filters={"client_request_id": request_id},
		fields=["name", "state", "invoice_name", "error_message", "creation", "modified"],
	)
	return {
		"request_id": request_id,
		"invoice_count": len(invoices),
		"invoices": [invoice_state(n) for n in invoices],
		"ledger": [{k: str(v) if v is not None else None for k, v in row.items()} for row in ledger],
	}


def _check(state, expect):
	"""Compare a saved invoice with expected values; returns a list of mismatches."""
	errors = []
	inv = state["invoices"][0] if state["invoices"] else None
	if expect.get("invoice_count") is not None and state["invoice_count"] != expect["invoice_count"]:
		errors.append(f"invoice_count {state['invoice_count']} != {expect['invoice_count']}")
	if not inv:
		return errors + (["no invoice"] if expect.get("invoice_count", 1) else [])
	for key in (
		"docstatus",
		"currency",
		"grand_total",
		"base_grand_total",
		"outstanding_amount",
		"ruhee_c7_rate",
	):
		if key in expect and inv[key] != expect[key]:
			errors.append(f"{key} {inv[key]!r} != {expect[key]!r}")
	if "line_rate" in expect and [i["rate"] for i in inv["items"]] != expect["line_rate"]:
		errors.append(f"line rates {[i['rate'] for i in inv['items']]} != {expect['line_rate']}")
	for account, sides in (expect.get("gl") or {}).items():
		got = inv["gl"].get(account) or {}
		for side, value in sides.items():
			if flt(got.get(side), 2) != flt(value, 2):
				errors.append(f"SI GL {account}.{side} {got.get(side)} != {value}")
	if "payment_entries" in expect and len(inv["payment_entries"]) != expect["payment_entries"]:
		errors.append(f"payment entries {len(inv['payment_entries'])} != {expect['payment_entries']}")
	for account, sides in (expect.get("pe_gl") or {}).items():
		got = inv["payment_entries"][0]["gl"].get(account) if inv["payment_entries"] else None
		for side, value in sides.items():
			if flt((got or {}).get(side), 2) != flt(value, 2):
				errors.append(f"PE GL {account}.{side} {(got or {}).get(side)} != {value}")
	if "stock_ledger_entries" in expect and inv["stock_ledger_entries"] != expect["stock_ledger_entries"]:
		errors.append(f"SLE {inv['stock_ledger_entries']} != {expect['stock_ledger_entries']}")
	return errors


def run(request_ids=None, expect=None, out=None):
	if not site_enabled():
		raise ValueError("Read-only verifier for disposable C7 sites only")
	request_ids = frappe.parse_json(request_ids) if isinstance(request_ids, str) else (request_ids or [])
	expect = frappe.parse_json(expect) if isinstance(expect, str) else (expect or {})
	result = {"site": frappe.local.site, "cases": []}
	for request_id in request_ids:
		state = by_request_id(request_id)
		state["errors"] = _check(state, expect.get(request_id, {})) if request_id in expect else None
		result["cases"].append(state)
	text = json.dumps(result, indent=1, default=str, sort_keys=True)
	if out:
		Path(out).write_text(text)  # operator-supplied bench argument; never web-exposed
	print(text)


# Requirement-based expectations (ACCOUNTING_RULES R1-R7, examples A, C, D; Prompt 6
# sections 3-5). They state what SHOULD be saved, so a gap shows as a failure.
C4_PE = {
	"Cash CDF - New Depo": {"debit": 100.87, "debit_fc": 232000},
	"Debtors": {"credit": 100},
	"Exchange income": {"credit": 0.87},
}
EXPECT = {
	"c3_01": {
		"invoice_count": 1,
		"docstatus": 1,
		"rate_base": 2300,
		"grand_total": 230000,
		"base_grand_total": 100,
		"outstanding_amount": 0,
		"line_rate": [230000],
		"gl": {
			"Debtors": {"debit": 100, "credit": 100},
			"Cash CDF - New Depo": {"debit": 100, "debit_fc": 230000},
		},
		"stock_ledger_entries": 1,
	},
	"c3_02": {
		"invoice_count": 1,
		"docstatus": 1,
		"rate_base": 2300,
		"grand_total": 23000000,
		"base_grand_total": 10000,
		"outstanding_amount": 0,
		"line_rate": [230000],
		"gl": {
			"Debtors": {"debit": 10000, "credit": 10000},
			"Cash CDF - New Depo": {"debit": 10000, "debit_fc": 23000000},
		},
	},
	"c4": {
		"invoice_count": 1,
		"docstatus": 1,
		"rate_base": 2300,
		"currency": "USD",
		"grand_total": 100,
		"outstanding_amount": 0,
		"payment_entries": 1,
		"gl": {"Debtors": {"debit": 100}},
		"pe_gl": C4_PE,
		"stock_ledger_entries": 1,
	},
	"c4_large": {
		"invoice_count": 1,
		"docstatus": 1,
		"rate_base": 2300,
		"currency": "USD",
		"grand_total": 10000,
		"outstanding_amount": 0,
		"payment_entries": 1,
		"pe_gl": {
			"Cash CDF - New Depo": {"debit": 10086.96, "debit_fc": 23200000},
			"Debtors": {"credit": 10000},
			"Exchange income": {"credit": 86.96},
		},
	},
	"c5": {
		"invoice_count": 1,
		"docstatus": 1,
		"rate_base": 2300,
		"grand_total": 230000,
		"base_grand_total": 100,
		"outstanding_amount": 50,
		"gl": {
			"Debtors": {"debit": 100, "credit": 50},
			"Cash CDF - New Depo": {"debit": 50, "debit_fc": 115000},
		},
	},
	"line_3200": {
		"invoice_count": 1,
		"docstatus": 1,
		"rate_base": 2300,
		"grand_total": 7360000,
		"base_grand_total": 3200,
		"line_rate": [7360000],
		"gl": {
			"Debtors": {"debit": 3200, "credit": 3200},
			"Cash CDF - New Depo": {"debit": 3200, "debit_fc": 7360000},
		},
	},
	# Diagnostic: 240,000 FC tendered on a $100 bill is gross tender, not the net
	# payment, so nothing may be saved.
	"diag_240k": {"invoice_count": 0},
	# Regression only, outside D-022's formal M1 scope: example B (R2).
	"b_cdf_bill_usd_tender": {
		"invoice_count": 1,
		"docstatus": 1,
		"outstanding_amount": 0,
		"gl": {
			"Debtors": {"debit": 100, "credit": 100},
			"Cash USD - New Depo": {"debit": 100, "debit_fc": 100},
		},
	},
}
# Flows: requirement per bill, keyed by flow and role.
FLOW_EXPECT = {
	"recovery_online": {
		"failed_bill": {"invoice_count": 1, "docstatus": 1, "payment_entries": 1, "pe_gl": C4_PE}
	},
	"recovery_offline_draft": {
		"queued_bill": {"invoice_count": 1, "docstatus": 1, "payment_entries": 1, "pe_gl": C4_PE}
	},
	"recovery_network": {
		"queued_bill": {
			"invoice_count": 1,
			"docstatus": 1,
			"payment_entries": 1,
			"pe_gl": C4_PE,
			"stock_ledger_entries": 1,
		}
	},
	"lost_response": {
		"bill": {
			"invoice_count": 1,
			"docstatus": 1,
			"payment_entries": 1,
			"pe_gl": C4_PE,
			"stock_ledger_entries": 1,
		}
	},
	"concurrent_replay": {
		"bill": {
			"invoice_count": 1,
			"docstatus": 1,
			"payment_entries": 1,
			"pe_gl": C4_PE,
			"stock_ledger_entries": 1,
		}
	},
	"effective_time": {
		"A_before_replacement": {
			"invoice_count": 1,
			"docstatus": 1,
			"rate_base": 2300,
			"line_rate": [230000],
		},
		"C_after_replacement_superseded": {
			"invoice_count": 1,
			"docstatus": 0,
			"rate_base": 2300,
			"line_rate": [230000],
			"hold": True,
		},
		"B_new_after_replacement": {
			"invoice_count": 1,
			"docstatus": 1,
			"rate_base": 2400,
			"line_rate": [240000],
		},
	},
}


def _check_extra(state, expect):
	errors = []
	inv = state["invoices"][0] if state["invoices"] else None
	if not inv:
		return errors
	if "rate_base" in expect and flt((inv.get("rate_record") or {}).get("base")) != expect["rate_base"]:
		errors.append(f"bound base {(inv.get('rate_record') or {}).get('base')} != {expect['rate_base']}")
	if expect.get("hold") and not inv.get("ruhee_c7_hold"):
		errors.append("no hold reason recorded")
	return errors


def _request_id(sale):
	return ((sale or {}).get("outbound") or {}).get("posa_client_request_id")


def _flow_bills(name, steps):
	by_step = {s["step"]: s for s in steps}
	if name == "effective_time":
		return {
			"A_before_replacement": _request_id(by_step["A_offline_before_replacement"]["sale"]),
			"C_after_replacement_superseded": _request_id(
				by_step["C_offline_after_replacement_superseded_rate"]["sale"]
			),
			"B_new_after_replacement": _request_id(by_step["B_online_after_replacement"]["sale"]),
		}
	if name == "recovery_online":
		return {"failed_bill": _request_id(by_step["first_attempt_failed"]["sale"])}
	if name in ("recovery_offline_draft", "recovery_network"):
		return {"queued_bill": _request_id(by_step["queued_offline"]["sale"])}
	if name == "lost_response":
		return {"bill": _request_id(by_step["first_submit_response_lost"]["sale"])}
	if name == "concurrent_replay":
		return {"bill": by_step["four_concurrent_replays"]["request_id"]}
	return {}


def from_harness(results_dir, out=None):
	"""Grade every c7_browser.mjs output in ``results_dir`` against the requirements above."""
	if not site_enabled():
		raise ValueError("Read-only verifier for disposable C7 sites only")
	summary = {"site": frappe.local.site, "scenarios": {}}
	for path in sorted(Path(results_dir).glob("*.json")):
		data = json.loads(path.read_text())
		name = data.get("scenario")
		if not name or name not in {**EXPECT, **FLOW_EXPECT}:
			continue
		bills = {"sale": _request_id(data)} if name in EXPECT else _flow_bills(name, data.get("steps") or [])
		expectations = {"sale": EXPECT[name]} if name in EXPECT else FLOW_EXPECT[name]
		graded = {}
		for role, request_id in bills.items():
			state = (
				by_request_id(request_id)
				if request_id
				else {"invoice_count": 0, "invoices": [], "ledger": []}
			)
			errors = _check(state, expectations[role]) + _check_extra(state, expectations[role])
			graded[role] = {"request_id": request_id, "pass": not errors, "errors": errors, "saved": state}
		summary["scenarios"][name] = {"harness_error": data.get("harness_error"), "bills": graded}
	text = json.dumps(summary, indent=1, default=str, sort_keys=True)
	if out:
		Path(out).write_text(text)  # operator-supplied bench argument; never web-exposed
	print(
		json.dumps(
			{
				name: {role: (b["pass"], b["errors"]) for role, b in s["bills"].items()}
				for name, s in summary["scenarios"].items()
			},
			indent=1,
		)
	)
