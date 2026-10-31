"""M1-04 native POS Awesome posting probe; invented data only, never production.

Run: bench --site dev.localhost execute ruhee_erp.spike.posting_model.run
Pass site=<exact staging hostname> explicitly in kwargs for staging. Configuration
and transactions are forbidden on staging on 4-6 November 2026 inclusive.
No rates, item prices, precision settings or submitted bills are adjusted here.
"""

import hashlib
import secrets

import frappe
from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as receivables
from frappe.utils import flt, now_datetime, nowdate
from posawesome.posawesome.api.employees import lock_terminal, save_cashier_pin, verify_terminal_employee_pin
from posawesome.posawesome.api.invoice_processing.creation import submit_invoice, update_invoice
from posawesome.posawesome.api.invoice_processing.utils import resolve_erpnext_currency_rates
from posawesome.posawesome.doctype.pos_closing_shift.closing_processing.creation import (
	make_closing_shift_from_opening,
	submit_closing_shift,
)

from ruhee_erp.spike.setup_spike import COMPANY, STORE, check_rate

PROFILE = "M1-04 New Depo"
PROFILE_SETTINGS = {
	"create_pos_invoice_instead_of_sales_invoice": 0,
	"update_stock": 1,
	"posa_allow_multi_currency": 1,
	"posa_allow_partial_payment": 1,
	"posa_allow_credit_sale": 1,
	"posa_allow_user_to_edit_additional_discount": 1,
	"posa_allow_submissions_in_background_job": 0,
	# M1-03 permits negative stock; avoid changing the shared baseline profile.
	"posa_block_sale_beyond_available_qty": 0,
}


def run(site="dev.localhost"):
	"""Print JSON evidence; bench execute commits successful transactions.

	Each invocation creates a fresh shift and bills. Failed runs roll back, subject
	to native POS Awesome transaction boundaries. Never retry by editing invoices.
	"""
	if frappe.local.site != site:
		raise ValueError("Pass the exact intended site in kwargs; default is dev.localhost")
	if site != "dev.localhost" and "2026-11-04" <= nowdate() <= "2026-11-06":
		raise ValueError("Staging offline-test freeze: no configuration or transactions from this probe")
	if frappe.session.user != "Administrator":
		raise ValueError("Run this spike as Administrator using bench execute")
	check_rate()
	profile = prepare_profile()
	# Use a fresh invented cashier and the real PIN endpoints, never bypass the
	# terminal lock or alter an existing user's PIN. The random PIN is not logged.
	cashier = f"m104-{frappe.generate_hash(length=10).lower()}@example.com"
	frappe.get_doc(
		{
			"doctype": "User",
			"email": cashier,
			"first_name": "M1-04",
			"last_name": "Spike",
			"send_welcome_email": 0,
			"roles": [{"role": "Sales User"}],
		}
	).insert()
	profile.append("applicable_for_users", {"user": cashier})
	profile.save()
	pin = str(100000 + secrets.randbelow(900000))
	save_cashier_pin(PROFILE, cashier, pin)
	verify_terminal_employee_pin(PROFILE, cashier, pin)
	customer = frappe.db.get_value("Customer", {"customer_name": "SPIKE-02 Client A"})
	if not customer:
		raise ValueError("Run the M1-03 baseline first")
	shift = frappe.get_doc(
		{
			"doctype": "POS Opening Shift",
			"company": COMPANY,
			"pos_profile": PROFILE,
			"user": frappe.session.user,
			"period_start_date": now_datetime(),
			"posting_date": nowdate(),
			"balance_details": [
				{"mode_of_payment": "Cash USD", "amount": 0, "currency": "USD"},
				{"mode_of_payment": "Cash CDF", "amount": 0, "currency": "CDF"},
			],
		}
	).insert()
	shift.submit()
	evidence = {
		"site": site,
		"captured_at": str(now_datetime()),
		"profile": PROFILE,
		"settings": PROFILE_SETTINGS,
		"opening_shift": shift.name,
		"bills": [],
	}
	for label in ("C2-1", "C2-2", "C2-3"):
		evidence["bills"].append(bill(label, profile, shift, customer, "USD", paid=100))

	rates = resolve_erpnext_currency_rates("CDF", "USD", "USD", nowdate())
	usd_price = frappe.db.get_value(
		"Item Price",
		{
			"item_code": "SPIKE-001",
			"price_list": profile.selling_price_list,
		},
		"price_list_rate",
	)
	# Mirrors frontend utils/erpnextCurrency.ts:priceListToSelectedCurrency.
	# This is a server-side reproduction, not evidence of a browser observation.
	precision = int(profile.posa_decimal_precision)
	native_rate = flt(usd_price * rates["plc_conversion_rate"] / rates["conversion_rate"], precision)
	evidence["unit_price_probe"] = {
		"usd_price": usd_price,
		**rates,
		"unrounded_cdf": usd_price / rates["conversion_rate"],
		"cdf_unit_price": native_rate,
		"exactly_230000": native_rate == 230000,
		"browser_verified": False,
	}
	evidence["bills"].append(
		bill("C3-native-price", profile, shift, customer, "CDF", rate=native_rate, paid=230000)
	)
	evidence["bills"].append(
		bill("C5-exact-input", profile, shift, customer, "CDF", rate=230000, paid=115000)
	)
	evidence["bills"].append(
		bill("large-exact-input", profile, shift, customer, "CDF", rate=230000, qty=100, paid=0)
	)
	# H uses the existing item and an explicit price override, no item import.
	evidence["bills"].append(bill("C6-H", profile, shift, customer, "CDF", rate=78200, discount=890, paid=0))
	# A second side of the rounding boundary produces a cent-valued GL difference.
	evidence["bills"].append(
		bill("C6-upper", profile, shift, customer, "CDF", rate=78200, discount=870, paid=0)
	)
	evidence["before_close"] = ledger_snapshot(evidence["bills"])
	closing = make_closing_shift_from_opening(frappe.as_json(shift.as_dict()))
	closing = closing["closing_shift"].as_dict()
	for row in closing.get("payment_reconciliation", []):
		row["closing_amount"] = row.get("expected_amount", 0)
		row["closing_amount_in_currency"] = row.get("expected_amount_in_currency", 0)
	evidence["closing_shift"] = submit_closing_shift(frappe.as_json(closing))
	evidence["after_close"] = ledger_snapshot(evidence["bills"])
	evidence["ledgers_unchanged_at_close"] = evidence["before_close"] == evidence["after_close"]
	evidence["accounts_receivable"] = receivable_rows(customer, evidence["bills"])
	lock_terminal(PROFILE)
	frappe.get_doc("User", cashier).update({"enabled": 0}).save()
	print("M1-04 EVIDENCE")
	print(frappe.as_json(evidence, indent=2))
	assert all(b["doctype"] == "Sales Invoice" and b["docstatus"] == 1 for b in evidence["bills"])
	assert all(sum(r.actual_qty for r in b["stock_ledger"]) == -b["qty"] for b in evidence["bills"])
	assert evidence["ledgers_unchanged_at_close"]
	part_paid = next(b for b in evidence["bills"] if b["label"] == "C5-exact-input")
	assert part_paid["outstanding_amount"] == 50
	assert any(
		r["voucher_no"] == part_paid["name"] and r["outstanding"] == 50
		for r in evidence["accounts_receivable"]
	)


def prepare_profile():
	if frappe.db.exists("POS Profile", PROFILE):
		profile = frappe.get_doc("POS Profile", PROFILE)
		if any(profile.get(k) != v for k, v in PROFILE_SETTINGS.items()):
			raise ValueError("Existing M1-04 profile differs; inspect instead of overwriting it")
		return profile
	profile = frappe.copy_doc(frappe.get_doc("POS Profile", STORE))
	profile.name = PROFILE
	profile.update(PROFILE_SETTINGS)
	profile.append("applicable_for_users", {"user": "Administrator"})
	profile.insert()
	return profile


def bill(label, profile, shift, customer, currency, rate=100, qty=1, paid=0, discount=0):
	mode = "Cash CDF" if currency == "CDF" else "Cash USD"
	payload = {
		"doctype": "Sales Invoice",
		"company": COMPANY,
		"pos_profile": PROFILE,
		"posa_pos_opening_shift": shift.name,
		"customer": customer,
		"currency": currency,
		"price_list_currency": "USD",
		"selling_price_list": profile.selling_price_list,
		"posting_date": nowdate(),
		"due_date": nowdate(),
		"is_pos": 1,
		"update_stock": 1,
		"set_warehouse": profile.warehouse,
		"cost_center": profile.cost_center,
		"apply_discount_on": "Grand Total",
		"discount_amount": discount,
		"items": [
			{
				"item_code": "SPIKE-001",
				"qty": qty,
				"rate": rate,
				"price_list_rate": rate,
				"warehouse": profile.warehouse,
			}
		],
		"payments": [{"mode_of_payment": mode, "amount": paid}],
	}
	draft = update_invoice(frappe.as_json(payload))
	result = submit_invoice(
		frappe.as_json(draft),
		frappe.as_json(
			{
				"pos_profile": PROFILE,
				"posa_pos_opening_shift": shift.name,
				"is_credit_sale": not paid,
				"due_date": nowdate(),
			}
		),
	)
	doc = frappe.get_doc(result["doctype"], result["name"])
	fields = (
		"name",
		"doctype",
		"docstatus",
		"currency",
		"conversion_rate",
		"grand_total",
		"rounded_total",
		"rounding_adjustment",
		"base_grand_total",
		"base_rounded_total",
		"base_rounding_adjustment",
		"paid_amount",
		"base_paid_amount",
		"outstanding_amount",
		"party_account_currency",
		"debit_to",
		"update_stock",
		"pos_profile",
		"posa_pos_opening_shift",
	)
	row = {key: doc.get(key) for key in fields}
	row.update(
		label=label,
		qty=qty,
		input_rate=rate,
		payments=[p.as_dict() for p in doc.payments],
		items=[
			{k: i.get(k) for k in ("item_code", "qty", "rate", "amount", "base_rate", "base_amount")}
			for i in doc.items
		],
	)
	row.update(extract(doc.name))
	return row


def extract(name):
	return {
		"gl": frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Sales Invoice", "voucher_no": name},
			fields=[
				"name",
				"account",
				"party",
				"account_currency",
				"debit",
				"credit",
				"debit_in_account_currency",
				"credit_in_account_currency",
				"is_cancelled",
			],
			order_by="name",
		),
		"stock_ledger": frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": name},
			fields=[
				"name",
				"item_code",
				"warehouse",
				"actual_qty",
				"qty_after_transaction",
				"stock_value_difference",
				"is_cancelled",
			],
			order_by="name",
		),
	}


def ledger_snapshot(bills):
	shift = bills[0]["posa_pos_opening_shift"]
	return {
		"invoices": frappe.get_all(
			"Sales Invoice",
			filters={"posa_pos_opening_shift": shift},
			fields=["name", "docstatus", "update_stock"],
			order_by="name",
		),
		"pos_invoices": frappe.get_all(
			"POS Invoice",
			filters={"posa_pos_opening_shift": shift},
			fields=["name", "docstatus"],
			order_by="name",
		),
		"ledger_sha256": {
			b["name"]: hashlib.sha256(frappe.as_json(extract(b["name"])).encode()).hexdigest() for b in bills
		},
	}


def receivable_rows(customer, bills):
	"""Run the real report, retaining only the invented invoices from this run."""
	rows = receivables(
		{"company": COMPANY, "report_date": nowdate(), "party": [customer], "in_party_currency": 1}
	)[1]
	names = {b["name"] for b in bills}
	return [
		{
			key: row.get(key)
			for key in ("voucher_no", "party", "currency", "invoiced", "paid", "credit_note", "outstanding")
		}
		for row in rows
		if row.get("voucher_no") in names
	]


def inspect_saved():
	"""Read only: inspect the two saved M1-04 precision probes and live metadata."""
	if frappe.local.site != "dev.localhost":
		raise ValueError("These evidence invoice IDs belong only to dev.localhost")
	rows = []
	for name in ("ACC-SINV-2026-00012", "ACC-SINV-2026-00014"):
		doc = frappe.get_doc("Sales Invoice", name)
		if doc.company != COMPANY or doc.pos_profile != PROFILE or doc.docstatus != 1:
			raise ValueError("Saved document differs from the M1-04 evidence scope")
		row = {
			key: doc.get(key)
			for key in (
				"name",
				"docstatus",
				"currency",
				"conversion_rate",
				"grand_total",
				"rounded_total",
				"rounding_adjustment",
				"base_rounding_adjustment",
				"base_grand_total",
				"base_rounded_total",
				"debit_to",
				"outstanding_amount",
			)
		}
		row["items"] = [
			{
				key: item.get(key)
				for key in (
					"item_code",
					"qty",
					"rate",
					"amount",
					"base_rate",
					"base_amount",
				)
			}
			for item in doc.items
		]
		row["gl"] = extract(name)["gl"]
		row["resolved_conversion_rate_precision"] = doc.precision("conversion_rate")
		rows.append(row)
	metadata = []
	for doctype, fieldname in (("Sales Invoice", "conversion_rate"), ("Currency Exchange", "exchange_rate")):
		field = frappe.get_meta(doctype).get_field(fieldname)
		metadata.append(
			{
				"doctype": doctype,
				"fieldname": fieldname,
				"fieldtype": field.fieldtype,
				"precision": field.precision,
				"database_column_type": frappe.db.get_column_type(doctype, fieldname),
			}
		)
	print(
		frappe.as_json(
			{
				"site": frappe.local.site,
				"captured_at": str(now_datetime()),
				"metadata": metadata,
				"saved_invoices": rows,
			},
			indent=2,
		)
	)
