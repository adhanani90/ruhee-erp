"""M1-07: replay check for POS Awesome's offline sync (I7, AUT-OFF-01).

Spike code only: never referenced from hooks.py, never run on production. All data is
invented (D-019). Run on cc.localhost only, after setup_spike.run, with this worktree
first on the import path (the bench's own checkout belongs to another card):

    PYTHONPATH=<worktree> bench --site cc.localhost execute ruhee_erp.spike.replay_check.run
    PYTHONPATH=<worktree> bench --site cc.localhost execute ruhee_erp.spike.replay_check.rate_probe

What it reproduces. On reconnect, frontend/src/offline/invoices.ts:syncOfflineInvoices
posts each queued {invoice, data} to posawesome.posawesome.api.invoices.submit_invoice
with no submit_in_background argument (so 0). When the response is lost, the queue entry
is retried with the same payload and the same posa_client_request_id. This script makes
those calls in-process, in separate transactions, on a profile with background submit
off, and counts what the server created.

Only the cases ERPNext submits natively today: a CDF bill paid in CDF and a USD bill paid
in USD. A USD bill paid in CDF needs a separate Payment Entry and is out of scope here.
"""

import json
import secrets
import uuid

import frappe
from frappe.utils import flt, now_datetime, nowdate

from ruhee_erp.spike.setup_spike import COMPANY, STORE

SITE = "cc.localhost"
PROFILE = "M1-07 Replay"
SUBMIT_METHOD = "posawesome.posawesome.api.invoices.submit_invoice"
CUSTOMER = "SPIKE-02 Client A"

# (label, invoice currency, item, qty, unit price in the bill's currency, mode of payment).
# SPIKE-002 is $25.00; at the spike rate of 2300 FC/USD that is 57,500 FC, a multiple of
# 50 FC, so no rounding question (Q1) arises.
CASES = (
	("CDF bill paid in CDF", "CDF", "SPIKE-002", 1, 57500, "Cash CDF"),
	("USD bill paid in USD", "USD", "SPIKE-004", 2, 12.50, "Cash USD"),
)
REPLAYS = 2


def guard():
	if frappe.local.site != SITE:
		frappe.throw(f"replay_check runs on {SITE} only, not {frappe.local.site}")
	if not frappe.db.exists("Company", COMPANY) or not frappe.db.exists("POS Profile", STORE):
		frappe.throw("Run ruhee_erp.spike.setup_spike.run on this site first")


def run():
	"""Replay check: each case submitted once and replayed REPLAYS times."""
	results = in_pos_session(lambda profile, shift: [replay_case(profile, shift, *c) for c in CASES])
	profile = frappe.get_doc("POS Profile", PROFILE)
	evidence = {
		"site": SITE,
		"captured_at": str(now_datetime()),
		"method": SUBMIT_METHOD,
		"profile": {
			"name": profile.name,
			"posa_allow_submissions_in_background_job": profile.posa_allow_submissions_in_background_job,
			"create_pos_invoice_instead_of_sales_invoice": profile.create_pos_invoice_instead_of_sales_invoice,
		},
		"multi_currency_payment_fields": multi_currency_fields(),
		"cases": results,
	}
	print(frappe.as_json(evidence, indent=2))

	failures = [f"{r['case']}: {f}" for r in results for f in r["failures"]]
	print("FAIL" if failures else "PASS")
	if failures:
		frappe.throw("replay_check failed: " + "; ".join(failures))


def in_pos_session(work):
	"""Unlock the terminal with a throwaway cashier, open (or reuse) a shift, run work,
	and always disable the cashier afterwards."""
	guard()
	frappe.flags.mute_emails = True
	profile = ensure_profile()
	cashier = unlock_terminal(profile)
	shift = ensure_opening_shift(profile)
	ensure_stock(profile)
	frappe.db.commit()
	try:
		return work(profile, shift)
	finally:
		frappe.db.rollback()
		frappe.get_doc("User", cashier).update({"enabled": 0}).save(ignore_permissions=True)
		frappe.db.commit()


def multi_currency_fields():
	"""POS Awesome's per-payment multi-currency fields (patches/add_per_payment_multi_
	currency_fields.py). Reported, never created here."""
	return {
		f"{dt}.{f}": bool(frappe.get_meta(dt).has_field(f))
		for dt, f in (
			("Sales Invoice Payment", "posa_payment_currency"),
			("Sales Invoice Payment", "posa_original_amount"),
			("POS Profile", "posa_enable_multi_currency_payments"),
		)
	}


def ensure_profile():
	"""A copy of New Depo with background submit explicitly off, matching offline sync."""
	if not frappe.db.exists("POS Profile", PROFILE):
		profile = frappe.copy_doc(frappe.get_doc("POS Profile", STORE))
		profile.name = PROFILE
		profile.__newname = PROFILE
		profile.update(
			{
				"create_pos_invoice_instead_of_sales_invoice": 0,
				"update_stock": 1,
				"posa_allow_submissions_in_background_job": 0,
			}
		)
		if not any(row.user == "Administrator" for row in profile.applicable_for_users):
			profile.append("applicable_for_users", {"user": "Administrator"})
		profile.insert()
	profile = frappe.get_doc("POS Profile", PROFILE)
	if (
		profile.posa_allow_submissions_in_background_job
		or profile.create_pos_invoice_instead_of_sales_invoice
	):
		frappe.throw(f"{PROFILE} must have background submit and POS Invoice mode off")
	return profile


def unlock_terminal(profile):
	"""submit_invoice resolves the cashier from the unlocked terminal state
	(posawesome/posawesome/api/terminal_state.py:get_active_terminal_cashier). A fresh
	invented cashier per run, disabled at the end, as a facturier would unlock with a PIN."""
	from posawesome.posawesome.api.employees import save_cashier_pin, verify_terminal_employee_pin

	cashier = f"m107-{frappe.generate_hash(length=10).lower()}@example.com"
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": cashier,
			"first_name": "M1-07",
			"last_name": "Replay",
			"send_welcome_email": 0,
		}
	)
	user.flags.no_welcome_mail = True
	user.append_roles("Sales User")
	user.insert(ignore_permissions=True)
	profile.append("applicable_for_users", {"user": cashier})
	profile.save()
	pin = str(100000 + secrets.randbelow(900000))
	save_cashier_pin(profile.name, cashier, pin)
	verify_terminal_employee_pin(profile.name, cashier, pin)
	return cashier


def ensure_opening_shift(profile):
	name = frappe.db.get_value(
		"POS Opening Shift",
		{"pos_profile": profile.name, "user": frappe.session.user, "status": "Open", "docstatus": 1},
	)
	if name:
		return frappe.get_doc("POS Opening Shift", name)
	shift = frappe.get_doc(
		{
			"doctype": "POS Opening Shift",
			"company": COMPANY,
			"pos_profile": profile.name,
			"user": frappe.session.user,
			"period_start_date": now_datetime(),
			"posting_date": nowdate(),
			"balance_details": [
				{"mode_of_payment": "Cash USD", "amount": 0},
				{"mode_of_payment": "Cash CDF", "amount": 0},
			],
		}
	).insert()
	shift.submit()
	return shift


# POS Awesome blocks sales beyond available stock on this profile
# (invoice_processing/stock.py:_profile_blocks_sale), as the store will. Receive invented
# stock dated before PROBE_DATE so every bill here, including the back-dated probe, has it.
STOCK_DATE = "2026-10-28"
STOCK_QTY = 50


def ensure_stock(profile):
	from erpnext.stock.utils import get_stock_balance

	rows = []
	for item_code in ("SPIKE-002", "SPIKE-004"):
		if flt(get_stock_balance(item_code, profile.warehouse)) < 10:
			rows.append(
				{
					"item_code": item_code,
					"qty": STOCK_QTY,
					"t_warehouse": profile.warehouse,
					"basic_rate": frappe.db.get_value("Item", item_code, "valuation_rate"),
				}
			)
	if rows:
		entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": COMPANY,
				"posting_date": STOCK_DATE,
				"set_posting_time": 1,
				"items": rows,
			}
		)
		entry.insert()
		entry.submit()


def client_request_id():
	# Same shape as frontend/src/offline/idempotency.ts:generateClientRequestId("inv").
	return f"inv-{int(now_datetime().timestamp() * 1000):x}-{uuid.uuid4()}"


def build_payload(
	profile, shift, currency, item_code, qty, rate, mode_of_payment, request_id, posting_date=None, rates=None
):
	"""The {invoice, data} pair the browser queues
	(posapp/composables/pos/payments/usePaymentSubmission.ts, offline branch)."""
	total = flt(qty * rate, 2)
	invoice = {
		"doctype": "Sales Invoice",
		"company": COMPANY,
		"pos_profile": profile.name,
		"posa_pos_opening_shift": shift.name,
		"customer": frappe.db.get_value("Customer", {"customer_name": CUSTOMER}),
		"currency": currency,
		"price_list_currency": "USD",
		"selling_price_list": profile.selling_price_list,
		"posting_date": posting_date or nowdate(),
		"set_posting_time": 1 if posting_date else 0,
		"is_pos": 1,
		"update_stock": 1,
		"set_warehouse": profile.warehouse,
		"cost_center": profile.cost_center,
		"posa_client_request_id": request_id,
		"items": [
			{
				"item_code": item_code,
				"qty": qty,
				"rate": rate,
				"price_list_rate": rate,
				"warehouse": profile.warehouse,
			}
		],
		"payments": [{"mode_of_payment": mode_of_payment, "amount": total}],
	}
	# Rates the browser resolved and cached while online (useInvoiceCurrency.ts:
	# update_currency_and_rate); only the rate probe sets them explicitly.
	invoice.update(rates or {})
	data = {
		"total_change": 0,
		"paid_change": 0,
		"credit_change": 0,
		"is_credit_sale": 0,
		"is_write_off_change": 0,
		"write_off_amount": 0,
		"redeemed_customer_credit": 0,
		"customer_credit_dict": [],
		"gift_card_redemptions": [],
		"is_cashback": True,
		"idempotency_key": request_id,
		"client_request_id": request_id,
	}
	return json.dumps(invoice), json.dumps(data)


def replay_case(profile, shift, label, currency, item_code, qty, rate, mode_of_payment):
	submit = frappe.get_attr(SUBMIT_METHOD)
	request_id = client_request_id()
	invoice_json, data_json = build_payload(
		profile, shift, currency, item_code, qty, rate, mode_of_payment, request_id
	)
	before = totals()

	responses = []
	for attempt in range(1 + REPLAYS):
		# Fresh copies of the same queued payload; one transaction per sync attempt.
		response = submit(invoice_json, data_json)
		frappe.db.commit()
		responses.append(
			{
				"attempt": attempt + 1,
				**{k: response.get(k) for k in ("name", "docstatus", "replayed", "ledger_state")},
			}
		)

	after = totals()
	delta = {k: after[k] - before[k] for k in before}
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"posa_client_request_id": request_id},
		fields=[
			"name",
			"docstatus",
			"currency",
			"conversion_rate",
			"grand_total",
			"base_grand_total",
			"paid_amount",
			"outstanding_amount",
		],
	)
	name = invoices[0].name if invoices else None
	ledgers = frappe.get_all(
		"POS Invoice Submission Ledger",
		filters={"client_request_id": request_id},
		fields=["name", "state", "invoice_name"],
	)
	payments = frappe.get_all(
		"Sales Invoice Payment",
		filters={"parent": name, "parenttype": "Sales Invoice", "amount": ["!=", 0]},
		fields=["mode_of_payment", "account", "amount", "base_amount"],
	)
	sle = frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_type": "Sales Invoice", "voucher_no": name, "is_cancelled": 0},
		fields=["item_code", "warehouse", "actual_qty"],
	)
	gl = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Sales Invoice", "voucher_no": name, "is_cancelled": 0},
		fields=["account", "debit", "credit", "debit_in_account_currency", "credit_in_account_currency"],
		order_by="account",
	)

	failures = []
	if len(invoices) != 1 or invoices[0].docstatus != 1:
		failures.append(f"expected one submitted invoice for the request id, found {invoices}")
	if {r["name"] for r in responses} != {name}:
		failures.append("replays did not return the original invoice")
	if responses[0]["replayed"] or not all(r["replayed"] for r in responses[1:]):
		failures.append("first call should create, every replay should report replayed")
	if len(ledgers) != 1:
		failures.append(f"expected one submission ledger row, found {len(ledgers)}")
	if len(payments) != 1 or payments[0].mode_of_payment != mode_of_payment:
		failures.append(f"expected one {mode_of_payment} payment row, found {payments}")
	if len(sle) != 1 or flt(sle[0].actual_qty) != -qty:
		failures.append(f"expected one stock movement of -{qty}, found {sle}")
	expected_delta = {"Sales Invoice": 1, "Payment Entry": 0, "Stock Ledger Entry": 1}
	for doctype, count in expected_delta.items():
		if delta[doctype] != count:
			failures.append(f"{doctype} count changed by {delta[doctype]}, expected {count}")

	return {
		"case": label,
		"client_request_id": request_id,
		"attempts": responses,
		"invoices_with_request_id": invoices,
		"submission_ledger": ledgers,
		"payment_rows": payments,
		"stock_ledger_entries": sle,
		"gl_entries": gl,
		"site_wide_count_delta": delta,
		"failures": failures,
	}


def totals():
	return {
		doctype: frappe.db.count(doctype, filters)
		for doctype, filters in (
			("Sales Invoice", {"docstatus": ["<", 2]}),
			("Payment Entry", {"docstatus": ["<", 2]}),
			("Stock Ledger Entry", {"is_cancelled": 0}),
			("GL Entry", {"is_cancelled": 0}),
			("POS Invoice Submission Ledger", {}),
		)
	}


# Rate-on-sync probe (C7, I6, I8). A CDF bill is made offline on PROBE_DATE while the PC
# holds 2300 FC/USD; before it syncs, a newer record for the same day says 2400. A past
# date keeps the site's current rates (setup_spike.check_rate, browser tests) at 2300.
# One Currency Exchange record per date, pair and purpose (erpnext/setup/doctype/
# currency_exchange/currency_exchange.py:autoname), so the newer record is "Selling".
# POS Awesome picks date desc, creation desc, with no purpose filter
# (posawesome/posawesome/api/invoice_processing/utils.py:get_latest_rate).
PROBE_DATE = "2026-10-29"
CACHED_RATE = 2300
NEWER_RATE = 2400


def rate_probe():
	result = in_pos_session(probe_case)
	print(frappe.as_json(result, indent=2))


def ensure_rate(date, usd_to_cdf, for_buying):
	names = []
	for from_currency, to_currency, value in (
		("USD", "CDF", usd_to_cdf),
		("CDF", "USD", flt(1 / usd_to_cdf, 9)),
	):
		filters = {
			"date": date,
			"from_currency": from_currency,
			"to_currency": to_currency,
			"for_selling": 1,
			"for_buying": for_buying,
		}
		name = frappe.db.get_value("Currency Exchange", filters)
		if name and flt(frappe.db.get_value("Currency Exchange", name, "exchange_rate"), 9) != flt(value, 9):
			frappe.throw(f"{name} exists with a different rate; inspect before probing")
		if not name:
			name = (
				frappe.get_doc({"doctype": "Currency Exchange", **filters, "exchange_rate": value})
				.insert()
				.name
			)
		names.append(name)
	frappe.db.commit()
	return names


def probe_case(profile, shift):
	from posawesome.posawesome.api.invoice_processing.utils import get_latest_rate

	cached = ensure_rate(PROBE_DATE, CACHED_RATE, for_buying=1)
	cached_cdf_to_usd = flt(1 / CACHED_RATE, 9)
	request_id = client_request_id()
	# 57,500 FC = $25.00 at 2300; the browser's own conversion rate goes in the payload.
	invoice_json, data_json = build_payload(
		profile,
		shift,
		"CDF",
		"SPIKE-002",
		1,
		57500,
		"Cash CDF",
		request_id,
		posting_date=PROBE_DATE,
		rates={"conversion_rate": cached_cdf_to_usd, "plc_conversion_rate": 1},
	)

	newer = ensure_rate(PROBE_DATE, NEWER_RATE, for_buying=0)
	server_rate_at_sync = get_latest_rate("CDF", "USD", transaction_date=PROBE_DATE)

	response = frappe.get_attr(SUBMIT_METHOD)(invoice_json, data_json)
	frappe.db.commit()
	doc = frappe.get_doc("Sales Invoice", response["name"])
	return {
		"site": SITE,
		"captured_at": str(now_datetime()),
		"posting_date": str(doc.posting_date),
		"rate_records": {"cached_at_bill_time": cached, "newer_same_day": newer},
		"payload_conversion_rate": cached_cdf_to_usd,
		"server_get_latest_rate_at_sync": [server_rate_at_sync[0], str(server_rate_at_sync[1])],
		"invoice": {
			k: doc.get(k)
			for k in (
				"name",
				"docstatus",
				"currency",
				"conversion_rate",
				"plc_conversion_rate",
				"grand_total",
				"rounded_total",
				"base_grand_total",
				"base_rounded_total",
				"paid_amount",
				"base_paid_amount",
				"change_amount",
				"base_change_amount",
				"write_off_amount",
				"base_write_off_amount",
				"outstanding_amount",
			)
		},
		"items": [
			{
				k: i.get(k)
				for k in ("item_code", "qty", "price_list_rate", "rate", "amount", "base_rate", "base_amount")
			}
			for i in doc.items
		],
		"payments": [
			{k: p.get(k) for k in ("mode_of_payment", "account", "amount", "base_amount")}
			for p in doc.payments
			if flt(p.amount)
		],
		"gl_entries": frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Sales Invoice", "voucher_no": doc.name, "is_cancelled": 0},
			fields=["account", "debit", "credit", "debit_in_account_currency", "credit_in_account_currency"],
			order_by="account",
		),
	}
