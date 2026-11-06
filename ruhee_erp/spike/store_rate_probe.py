"""M1-05 C7 online: real handler/native submit, supported hooks, read-only profiler.

Run with PYTHONPATH=/tmp/ruhee-c7 from the bench, on disposable m105.localhost.
Existing scratch evidence is preserved. No precision/schema widening, module
monkeypatch, browser/offline acceptance or production idempotency claim.
"""

import hashlib
import json
import secrets
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import flt, now_datetime, nowdate

from ruhee_erp.spike.store_rate_hooks import PROFILE, RATE_TYPE, SITE, SUBMIT

COMPANY = "Ruhee Spike"
TRACE = []
PHASE = ""
WATCH = {
	"creation.py": {"update_invoice", "_submit_invoice_once", "submit_invoice", "submit_in_background_job"},
	"utils.py": {"resolve_erpnext_currency_rates"},
	"sales_invoice.py": {"validate", "on_submit", "make_gl_entries"},
	"accounts_controller.py": {"validate", "calculate_taxes_and_totals"},
	"payment_entry.py": {"validate", "on_submit", "make_gl_entries"},
	"payment_currency.py": {
		"normalize_invoice_payment_currencies",
		"preserve_multi_currency_payment_amounts",
	},
	"store_rate_hooks.py": {"bind_rate", "submit_invoice", "bind_payment_rate", "settle_cdf_tender"},
}


def guard():
	if frappe.local.site != SITE or not frappe.conf.get("pause_scheduler"):
		raise ValueError("Only the paused disposable m105.localhost site is allowed")
	if frappe.session.user != "Administrator":
		raise ValueError("Run the spike with bench execute as Administrator")


def profile(frame, event, arg):
	if event not in ("call", "return"):
		return
	name = frame.f_code.co_name
	if not any(name in names for names in WATCH.values()):
		return
	path = Path(frame.f_code.co_filename)
	if name not in WATCH.get(path.name, set()):
		return
	if not any(part in path.parts for part in ("erpnext", "posawesome", "ruhee_erp")):
		return
	row = {
		"seq": len(TRACE),
		"phase": PHASE,
		"event": event,
		"function": f"{path.name}:{name}",
		"line": frame.f_lineno,
	}
	doc = frame.f_locals.get("self") or frame.f_locals.get("doc") or frame.f_locals.get("invoice_doc")
	if hasattr(doc, "get") and doc.get("doctype") in ("Sales Invoice", "Payment Entry"):
		row.update(
			{
				k: doc.get(k)
				for k in (
					"doctype",
					"name",
					"docstatus",
					"conversion_rate",
					"ruhee_c7_rate",
					"grand_total",
					"base_grand_total",
					"paid_amount",
					"base_paid_amount",
					"outstanding_amount",
					"target_exchange_rate",
					"base_received_amount",
				)
			}
		)
		row["action"] = doc.get("_action")
	if event == "return" and name == "resolve_erpnext_currency_rates":
		row["resolved"] = arg
	TRACE.append(row)


@contextmanager
def tracing(phase):
	global PHASE
	PHASE = phase
	previous = sys.getprofile()
	sys.setprofile(profile)
	try:
		yield
	finally:
		sys.setprofile(previous)


def setup():
	guard()
	if not frappe.db.exists("DocType", RATE_TYPE):
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": RATE_TYPE,
				"module": "Ruhee ERP",
				"custom": 1,
				"autoname": "hash",
				"is_submittable": 1,
				"fields": [
					{
						"fieldname": "company",
						"label": "Société",
						"fieldtype": "Link",
						"options": "Company",
						"reqd": 1,
					},
					{"fieldname": "store", "label": "Magasin", "fieldtype": "Data", "reqd": 1},
					{
						"fieldname": "pos_profile",
						"label": "Profil de caisse",
						"fieldtype": "Link",
						"options": "POS Profile",
						"reqd": 1,
					},
					{
						"fieldname": "effective_from",
						"label": "Date et heure d'effet",
						"fieldtype": "Datetime",
						"reqd": 1,
					},
					{
						"fieldname": "base",
						"label": "Taux de base",
						"fieldtype": "Float",
						"precision": "9",
						"reqd": 1,
					},
					{
						"fieldname": "higher",
						"label": "Taux majoré",
						"fieldtype": "Float",
						"precision": "9",
						"reqd": 1,
					},
				],
				"permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "submit": 1}],
			}
		).insert()
	for doctype in ("Sales Invoice", "Payment Entry"):
		for fieldname, label, fieldtype, options in (
			("ruhee_c7_rate", "Taux magasin (essai C7)", "Link", RATE_TYPE),
			("ruhee_c7_tender_cdf", "Espèces CDF (essai C7)", "Currency", ""),
			("ruhee_c7_allocation_usd", "Montant USD (essai C7)", "Currency", ""),
		):
			if not frappe.get_meta(doctype).has_field(fieldname):
				create_custom_field(
					doctype,
					{
						"fieldname": fieldname,
						"label": label,
						"fieldtype": fieldtype,
						"options": options,
						"insert_after": "company",
						"read_only": 1,
						"no_copy": 1,
					},
				)
	if not frappe.db.exists("POS Profile", PROFILE):
		doc = frappe.copy_doc(frappe.get_doc("POS Profile", "M1-05 Native"))
		doc.name = PROFILE
		doc.posa_allow_submissions_in_background_job = 0
		doc.insert()
	# Add competing records on this disposable site only; never edit old records.
	for source, target, quote in (("USD", "CDF", 9999), ("CDF", "USD", flt(1 / 9999, 12))):
		name = frappe.db.get_value(
			"Currency Exchange", {"date": nowdate(), "from_currency": source, "to_currency": target}
		)
		if name:
			assert frappe.db.get_value("Currency Exchange", name, "exchange_rate") == quote
		else:
			frappe.get_doc(
				{
					"doctype": "Currency Exchange",
					"date": nowdate(),
					"from_currency": source,
					"to_currency": target,
					"exchange_rate": quote,
					"for_selling": 1,
					"for_buying": 1,
				}
			).insert()
	frappe.clear_cache()
	assert (
		"ruhee_erp.spike.store_rate_hooks.bind_rate"
		in frappe.get_doc_hooks()["Sales Invoice"]["before_validate"]
	)
	assert frappe.override_whitelisted_method(SUBMIT) == "ruhee_erp.spike.store_rate_hooks.submit_invoice"


def rate(base, higher, time):
	doc = frappe.get_doc(
		{
			"doctype": RATE_TYPE,
			"company": COMPANY,
			"store": "New Depo",
			"pos_profile": PROFILE,
			"effective_from": f"{nowdate()} {time}",
			"base": base,
			"higher": higher,
		}
	).insert()
	doc.submit()
	return doc


def account(name):
	return frappe.db.get_value("Account", {"company": COMPANY, "account_name": name})


def gl(doc):
	return frappe.get_all(
		"GL Entry",
		filters={"voucher_type": doc.doctype, "voucher_no": doc.name},
		fields=[
			"name",
			"account",
			"account_currency",
			"debit",
			"credit",
			"debit_in_account_currency",
			"credit_in_account_currency",
			"is_cancelled",
		],
		order_by="name",
	)


def snapshot(name):
	doc = frappe.get_doc("Sales Invoice", name)
	pes = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": "Sales Invoice", "reference_name": name, "docstatus": 1},
		pluck="parent",
	)
	return {
		"invoice": doc.as_dict(),
		"gl": gl(doc),
		"payments": [
			{
				"doc": frappe.get_doc("Payment Entry", p).as_dict(),
				"gl": gl(frappe.get_doc("Payment Entry", p)),
			}
			for p in pes
		],
	}


def assert_amounts(saved, label):
	"""Check the actual cash/debtor GL, not just cached invoice paid fields."""
	if label == "C4":
		rows = saved["payments"][0]["gl"]
		cash, cash_usd, credit, income = 232000, 100.87, 100, 0.87
	else:
		rows = saved["gl"]
		cash, cash_usd, credit, income = (115000, 50, 50, 0) if label == "C5" else (230000, 100, 100, 0)
	assert (
		sum(r["debit_in_account_currency"] for r in rows if r["account"] == account("Cash CDF - New Depo"))
		== cash
	)
	assert sum(r["debit"] for r in rows if r["account"] == account("Cash CDF - New Depo")) == cash_usd
	assert sum(r["credit"] for r in rows if r["account"] == account("Debtors")) == credit
	assert sum(r["credit"] - r["debit"] for r in rows if r["account"] == account("Exchange income")) == income
	assert not any(r["account"] == account("Exchange Gain/Loss") for r in rows)


def digest(value):
	return hashlib.sha256(frappe.as_json(value).encode()).hexdigest()


def write_capture(filename, value):
	"""Keep each profiler event on one line, while preserving all captured data."""
	value = json.loads(frappe.as_json(value))
	fields = []
	for key, item in sorted(value.items()):
		if key == "trace":
			encoded = "[\n" + ",\n".join("  " + json.dumps(row, sort_keys=True) for row in item) + "\n]"
		else:
			encoded = json.dumps(item, indent=2, ensure_ascii=False, sort_keys=True)
		fields.append(f"  {json.dumps(key)}: " + encoded.replace("\n", "\n  "))
	Path(__file__).with_name(filename).write_text("{\n" + ",\n".join(fields) + "\n}\n")


def dispatch(payload, data):
	from frappe.handler import execute_cmd

	old_form = frappe.local.form_dict
	old_request = getattr(frappe.local, "request", None)
	frappe.local.form_dict = frappe._dict(invoice=frappe.as_json(payload), data=frappe.as_json(data))
	frappe.local.request = SimpleNamespace(method="POST")
	try:
		return execute_cmd(SUBMIT)
	finally:
		frappe.local.form_dict = old_form
		frappe.local.request = old_request


def run():
	guard()
	setup()
	from posawesome.posawesome.api.employees import (
		lock_terminal,
		save_cashier_pin,
		verify_terminal_employee_pin,
	)
	from posawesome.posawesome.api.invoice_processing.creation import update_invoice
	from posawesome.posawesome.api.invoice_processing.utils import resolve_erpnext_currency_rates

	TRACE.clear()
	profile_doc = frappe.get_doc("POS Profile", PROFILE)
	cashier = f"c7-{frappe.generate_hash(length=10).lower()}@example.com"
	frappe.get_doc(
		{
			"doctype": "User",
			"email": cashier,
			"first_name": "C7",
			"last_name": "Spike",
			"send_welcome_email": 0,
			"roles": [{"role": "Sales User"}],
		}
	).insert()
	profile_doc.append("applicable_for_users", {"user": cashier})
	profile_doc.save()
	pin = str(100000 + secrets.randbelow(900000))
	save_cashier_pin(PROFILE, cashier, pin)
	verify_terminal_employee_pin(PROFILE, cashier, pin)
	shift = frappe.get_doc(
		{
			"doctype": "POS Opening Shift",
			"company": COMPANY,
			"pos_profile": PROFILE,
			"user": "Administrator",
			"period_start_date": now_datetime(),
			"posting_date": nowdate(),
			"balance_details": [
				{"mode_of_payment": "Cash USD", "amount": 0, "currency": "USD"},
				{"mode_of_payment": "Cash CDF", "amount": 0, "currency": "CDF"},
			],
		}
	).insert()
	shift.submit()
	first_rate = rate(2300, 2320, "00:00:00")
	company_rates = resolve_erpnext_currency_rates("CDF", "USD", "USD", nowdate())
	assert company_rates["conversion_rate"] == flt(1 / 9999, 12)
	customer = frappe.db.get_value("Customer", {"customer_name": "SPIKE-02 Client A"})
	usd_price = frappe.db.get_value(
		"Item Price",
		{"item_code": "SPIKE-001", "price_list": profile_doc.selling_price_list},
		"price_list_rate",
	)
	assert usd_price == 100
	results, requests = [], []
	for label, currency, tender in (("C3", "CDF", 230000), ("C4", "USD", 232000), ("C5", "CDF", 115000)):
		for path in ("new", "existing"):
			case = f"{label}-{path}"
			compatibility = flt(
				1 / first_rate.base, frappe.get_meta("Sales Invoice").get_field("conversion_rate").precision
			)
			unit = flt(usd_price / compatibility, 2) if currency == "CDF" else usd_price
			payload = {
				"doctype": "Sales Invoice",
				"company": COMPANY,
				"pos_profile": PROFILE,
				"posa_pos_opening_shift": shift.name,
				"customer": customer,
				"currency": currency,
				"price_list_currency": "USD",
				"selling_price_list": profile_doc.selling_price_list,
				"posting_date": nowdate(),
				"posting_time": "08:00:00",
				"set_posting_time": 1,
				"due_date": nowdate(),
				"is_pos": 1,
				"update_stock": 1,
				"ruhee_c7_rate": first_rate.name,
				"posa_client_request_id": f"c7-{frappe.generate_hash(length=20)}",
				"set_warehouse": profile_doc.warehouse,
				"cost_center": profile_doc.cost_center,
				"items": [
					{
						"item_code": "SPIKE-001",
						"qty": 1,
						"rate": unit,
						"price_list_rate": unit,
						"warehouse": profile_doc.warehouse,
					}
				],
				"payments": [
					{
						"mode_of_payment": "Cash CDF",
						"account": account("Cash CDF - New Depo"),
						"amount": tender if currency == "CDF" else 100,
						"posa_original_amount": tender,
						"posa_payment_currency": "CDF",
					}
				],
			}
			context = {"pos_profile": PROFILE, "posa_pos_opening_shift": shift.name, "due_date": nowdate()}
			if path == "existing":
				draft_payload = json.loads(frappe.as_json(payload))
				if label == "C4":
					draft_payload["payments"] = [
						{
							"mode_of_payment": "Cash USD",
							"amount": 0,
							"posa_original_amount": 0,
							"posa_payment_currency": "USD",
						}
					]
				with tracing(f"{case}-draft"):
					draft = update_invoice(frappe.as_json(draft_payload))
				payload["name"] = draft["name"]
			with tracing(case):
				response = dispatch(payload, context)
			saved = snapshot(response["name"])
			doc = saved["invoice"]
			assert doc["docstatus"] == 1 and doc["ruhee_c7_rate"] == first_rate.name
			assert doc["conversion_rate"] == (compatibility if currency == "CDF" else 1)
			assert doc["outstanding_amount"] == (50 if label == "C5" else 0)
			assert doc["base_grand_total"] == 100
			assert sum(r.debit for r in saved["gl"] if r.account == account("Debtors")) == 100
			if label == "C4":
				assert len(saved["payments"]) == 1
				pe = saved["payments"][0]
				assert pe["doc"]["ruhee_c7_rate"] == first_rate.name
				assert pe["doc"]["base_received_amount"] == 100.87
				assert sum(r.credit for r in pe["gl"] if r.account == account("Exchange income")) == 0.87
				assert sum(r.credit for r in pe["gl"] if r.account == account("Debtors")) == 100
				assert (
					sum(
						r.debit_in_account_currency
						for r in pe["gl"]
						if r.account == account("Cash CDF - New Depo")
					)
					== 232000
				)
			else:
				assert doc["grand_total"] == 230000
				assert doc["base_paid_amount"] == (50 if label == "C5" else 100)
			assert_amounts(saved, label)
			results.append({"case": case, "response": response, **saved})
			requests.append((payload, context, response))
	before = [digest(snapshot(row["response"]["name"])) for row in results]
	later_rate = rate(2400, 2420, "12:00:00")
	after = [digest(snapshot(row["response"]["name"])) for row in results]
	assert before == after
	replays = []
	for payload, context, original in requests:
		with tracing(f"replay-{original['name']}"):
			replayed = dispatch(payload, context)
		assert replayed["name"] == original["name"]
		replays.append(replayed)
	assert after == [digest(snapshot(row["response"]["name"])) for row in results]
	from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as receivables

	_, ar, *_ = receivables(
		frappe._dict(
			company=COMPANY,
			report_date=nowdate(),
			age_from="Due Date",
			range1=30,
			range2=60,
			range3=90,
			range4=120,
		)
	)
	ar_rows = [r for r in ar if r.get("voucher_no") in [x["response"]["name"] for x in results]]
	for row in results:
		if row["case"].startswith("C5"):
			assert any(
				r.get("voucher_no") == row["response"]["name"] and r.get("outstanding") == 50 for r in ar_rows
			)
	lock_terminal(PROFILE)
	frappe.get_doc("User", cashier).update({"enabled": 0}).save()
	evidence = {
		"site": SITE,
		"captured_at": str(now_datetime()),
		"scope": "server handler/native synchronous submit; no browser/offline acceptance",
		"company_rates": company_rates,
		"first_rate": first_rate.as_dict(),
		"later_rate": later_rate.as_dict(),
		"precision": [
			{
				"doctype": dt,
				"field": field,
				"precision": frappe.get_meta(dt).get_field(field).precision,
				"column": frappe.db.get_column_type(dt, field),
			}
			for dt, field in (
				("Sales Invoice", "conversion_rate"),
				("Payment Entry", "target_exchange_rate"),
				("Sales Invoice Payment", "posa_company_exchange_rate"),
			)
		],
		"cases": results,
		"history": {"before": before, "after": after, "after_replay_unchanged": True},
		"replays": replays,
		"accounts_receivable": ar_rows,
		"trace": TRACE,
		"hooks": {
			"doc_events": frappe.get_hooks("doc_events", app_name="ruhee_erp"),
			"override_whitelisted_methods": frappe.get_hooks(
				"override_whitelisted_methods", app_name="ruhee_erp"
			),
		},
	}
	write_capture("store_rate_results.json", evidence)
	print(
		frappe.as_json(
			{
				"cases": [r["case"] for r in results],
				"history_unchanged": before == after,
				"replays": len(replays),
				"trace_events": len(TRACE),
			},
			indent=2,
		)
	)


def verify_saved():
	"""Fresh-process readback, including the old PR #20 synthetic documents."""
	guard()
	evidence = json.loads(Path(__file__).with_name("store_rate_results.json").read_text())
	checks = []
	for i, result in enumerate(evidence["cases"]):
		current = snapshot(result["response"]["name"])
		assert digest(current) == evidence["history"]["after"][i]
		assert_amounts(current, result["case"].split("-")[0])
		checks.append({"case": result["case"], "unchanged": True})
	# These are the pre-existing invented C3 control and store-bound invoices
	# documented by PR #20. Never modify/reallocate them in this probe.
	old = [
		{
			"name": name,
			"rate": frappe.db.get_value("Sales Invoice", name, "conversion_rate"),
			"grand_total": frappe.db.get_value("Sales Invoice", name, "grand_total"),
		}
		for name in ("ACC-SINV-2026-00007", "ACC-SINV-2026-00008", "ACC-SINV-2026-00009")
	]
	result = {
		"site": SITE,
		"captured_at": str(now_datetime()),
		"checks": checks,
		"preexisting_controls_read_only": old,
	}
	write_capture("store_rate_readback.json", result)
	print(frappe.as_json(result, indent=2))


def native_c4_control():
	"""Prove rate doc_events alone do not fix native USD/CDF account validation."""
	guard()
	from posawesome.posawesome.api.employees import (
		lock_terminal,
		save_cashier_pin,
		verify_terminal_employee_pin,
	)
	from posawesome.posawesome.api.invoice_processing.creation import submit_invoice as native_submit

	evidence = json.loads(Path(__file__).with_name("store_rate_results.json").read_text())
	payload = next(r["invoice"] for r in evidence["cases"] if r["case"] == "C4-new").copy()
	# Reauthenticate a fresh invented cashier through the real PIN endpoints.
	user = f"c7-control-{frappe.generate_hash(length=10).lower()}@example.com"
	frappe.get_doc(
		{
			"doctype": "User",
			"email": user,
			"first_name": "C7 Control",
			"send_welcome_email": 0,
			"roles": [{"role": "Sales User"}],
		}
	).insert()
	pdoc = frappe.get_doc("POS Profile", PROFILE)
	pdoc.append("applicable_for_users", {"user": user})
	pdoc.save()
	pin = str(100000 + secrets.randbelow(900000))
	save_cashier_pin(PROFILE, user, pin)
	verify_terminal_employee_pin(PROFILE, user, pin)
	for key in (
		"name",
		"creation",
		"modified",
		"modified_by",
		"owner",
		"ruhee_c7_tender_cdf",
		"ruhee_c7_allocation_usd",
	):
		payload.pop(key, None)
	payload.update(docstatus=0, posa_client_request_id=f"c7-control-{frappe.generate_hash(length=20)}")
	payload["payments"] = [
		{
			"mode_of_payment": "Cash CDF",
			"account": account("Cash CDF - New Depo"),
			"amount": 100,
			"posa_original_amount": 232000,
			"posa_payment_currency": "CDF",
		}
	]
	context = {
		"pos_profile": PROFILE,
		"posa_pos_opening_shift": payload["posa_pos_opening_shift"],
		"due_date": nowdate(),
	}
	TRACE.clear()
	frappe.db.savepoint("c7_control")
	error = None
	try:
		with tracing("C4-native-control"):
			native_submit(frappe.as_json(payload), frappe.as_json(context))
	except frappe.ValidationError as exc:
		error = {"type": type(exc).__name__, "message": str(exc)}
	finally:
		frappe.db.rollback(save_point="c7_control")
	assert error and "currency" in error["message"].lower()
	assert not any(r["function"] == "store_rate_hooks.py:settle_cdf_tender" for r in TRACE)
	lock_terminal(PROFILE)
	frappe.get_doc("User", user).update({"enabled": 0}).save()
	result = {
		"site": SITE,
		"captured_at": str(now_datetime()),
		"error": error,
		"native_function_called_directly": True,
		"rate_doc_events_active": True,
		"on_submit_never_reached": True,
		"failed_attempt_rolled_back": True,
		"trace": TRACE,
	}
	write_capture("store_rate_native_control.json", result)
	print(frappe.as_json(error))
