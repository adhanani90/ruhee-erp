"""M1-05 scratch-only rate adapter and Payment Entry proof, never a production hook.

All patches are scoped to this bench process and restored on exit. No hooks.py,
framework, ERPNext or POS Awesome files are edited. No offline claim is made.
"""

import json
import secrets
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import flt, now_datetime, nowdate

from ruhee_erp.spike.cross_currency import COMPANY, SCRATCH, account, guard, invoice_evidence

RATE_TYPE = "Ruhee Spike Store Rate"


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
					{"fieldname": "store", "label": "Magasin", "fieldtype": "Data", "reqd": 1},
					{"fieldname": "date", "label": "Date", "fieldtype": "Date", "reqd": 1},
					{
						"fieldname": "effective_time",
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
		if not frappe.get_meta(doctype).has_field("ruhee_spike_rate"):
			create_custom_field(
				doctype,
				{
					"fieldname": "ruhee_spike_rate",
					"label": "Taux du magasin (essai)",
					"fieldtype": "Link",
					"options": RATE_TYPE,
					"insert_after": "company",
					"read_only": 1,
					"no_copy": 1,
				},
			)
	print("Scratch-only store rate schema and document links ready")


@contextmanager
def store_rates(record):
	"""Prototype the rate hook only for this explicit immutable store record."""
	guard()
	from posawesome.posawesome.api import payment_currency
	from posawesome.posawesome.api.invoice_processing import creation

	def resolve(from_currency, to_currency, posting_date, cache, manual_rate=None):
		if from_currency == to_currency:
			value = 1
		elif (from_currency, to_currency) == ("CDF", "USD"):
			value = 1 / record.base
		elif (from_currency, to_currency) == ("USD", "CDF"):
			value = record.base
		else:
			raise ValueError("Prototype supports only USD/CDF")
		return value, record.date, "manual"

	def invoice_rates(invoice_currency, price_list_currency, company_currency, posting_date=None, cache=None):
		if company_currency != "USD" or price_list_currency != "USD":
			raise ValueError("Prototype preserves the single USD price list")
		return {
			"conversion_rate": flt(1 / record.base, 12) if invoice_currency == "CDF" else 1,
			"plc_conversion_rate": 1,
			"price_list_currency": "USD",
			"exchange_rate_date": record.date,
		}

	with (
		patch.object(creation, "resolve_erpnext_currency_rates", invoice_rates),
		patch.object(payment_currency, "_resolve_rate", resolve),
	):
		yield


def payment(doc, record, tender, allocated, nine_place=False):
	"""Pre-submit adapter: exact USD allocation, base-valued CDF cash, R7 deduction."""
	guard()
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry(
		"Sales Invoice",
		doc.name,
		bank_account=account("Cash CDF - New Depo"),
		party_amount=allocated,
		bank_amount=tender,
	)
	pe.paid_amount = allocated
	pe.received_amount = tender
	pe.source_exchange_rate = 1
	pe.target_exchange_rate = flt(1 / record.base, 9 if nine_place else 12)
	pe.mode_of_payment = "Cash CDF"
	pe.reference_no = doc.posa_pos_opening_shift
	pe.reference_date = doc.posting_date
	pe.ruhee_spike_rate = record.name
	for row in pe.references:
		row.allocated_amount = allocated
		row.exchange_rate = 1
	# ERPNext updates this row's difference during validation. Its account stays
	# the R7 management account; no submitted document/ledger correction occurs.
	pe.set(
		"deductions",
		[
			{
				"account": account("Exchange income"),
				"cost_center": doc.cost_center,
				"amount": flt(allocated - flt(tender * pe.target_exchange_rate, 2), 2),
				"is_exchange_gain_loss": 1,
			}
		],
	)
	pe.insert()
	pe.submit()
	return {
		"name": pe.name,
		"target_exchange_rate": pe.target_exchange_rate,
		"received_amount": pe.received_amount,
		"paid_amount": pe.paid_amount,
		"base_received_amount": pe.base_received_amount,
		"ruhee_spike_rate": pe.ruhee_spike_rate,
		"deductions": [{"account": r.account, "amount": r.amount} for r in pe.deductions],
		"gl": frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Payment Entry", "voucher_no": pe.name},
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
		),
	}


def run():
	guard()
	for doctype, fieldname in (
		("Sales Invoice", "conversion_rate"),
		("Sales Invoice Payment", "posa_company_exchange_rate"),
		("Payment Entry", "target_exchange_rate"),
	):
		if frappe.db.get_column_type(doctype, fieldname) != "decimal(21,12)":
			raise ValueError("Finish the scratch precision/schema experiment before the store adapter proof")
	from posawesome.posawesome.api.employees import (
		lock_terminal,
		save_cashier_pin,
		verify_terminal_employee_pin,
	)
	from posawesome.posawesome.api.invoice_processing.creation import submit_invoice, update_invoice
	from posawesome.posawesome.doctype.pos_closing_shift.closing_processing.creation import (
		make_closing_shift_from_opening,
		submit_closing_shift,
	)

	profile_name = "M1-05 Store Adapter"
	if not frappe.db.exists("POS Profile", profile_name):
		profile = frappe.copy_doc(frappe.get_doc("POS Profile", "M1-05 Native"))
		profile.name = profile_name
		profile.insert()
	profile = frappe.get_doc("POS Profile", profile_name)
	cashier = f"m105p-{frappe.generate_hash(length=10).lower()}@example.com"
	frappe.get_doc(
		{
			"doctype": "User",
			"email": cashier,
			"first_name": "M1-05",
			"last_name": "Adapter",
			"send_welcome_email": 0,
			"roles": [{"role": "Sales User"}],
		}
	).insert()
	profile.append("applicable_for_users", {"user": cashier})
	profile.save()
	pin = str(100000 + secrets.randbelow(900000))
	save_cashier_pin(profile.name, cashier, pin)
	verify_terminal_employee_pin(profile.name, cashier, pin)
	shift = frappe.get_doc(
		{
			"doctype": "POS Opening Shift",
			"company": COMPANY,
			"pos_profile": profile.name,
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
	rate = frappe.get_doc(
		{
			"doctype": RATE_TYPE,
			"store": "New Depo",
			"date": nowdate(),
			"effective_time": now_datetime(),
			"base": 2300,
			"higher": 2320,
		}
	).insert()
	rate.submit()
	# Deliberately competing company-wide rates. Only scratch is affected, and
	# the adapter must still use the referenced store record for all test amounts.
	for from_currency, to_currency, value in (("USD", "CDF", 9999), ("CDF", "USD", flt(1 / 9999, 12))):
		name = frappe.db.get_value(
			"Currency Exchange", {"from_currency": from_currency, "to_currency": to_currency}
		)
		frappe.get_doc("Currency Exchange", name).update({"exchange_rate": value}).save()
	customer = frappe.db.get_value("Customer", {"customer_name": "SPIKE-02 Client A"})
	usd_price = frappe.db.get_value(
		"Item Price", {"item_code": "SPIKE-001", "price_list": profile.selling_price_list}, "price_list_rate"
	)
	if usd_price != 100:
		raise ValueError("The invented C/E/F test catalogue must retain its $100 USD item")
	rows = []
	cases = (
		("C3-store", "CDF", 1, 100, False),
		("C5-store", "CDF", 1, 50, False),
		("C4-nine-value", "USD", 1, 100, True),
		("large-nine-value", "USD", 100, 10000, True),
		("C4-store", "USD", 1, 100, False),
		("large-store", "USD", 100, 10000, False),
	)
	with store_rates(rate):
		for label, currency, qty, allocated, nine in cases:
			unit = usd_price * rate.base if currency == "CDF" else usd_price
			paid = allocated * rate.base if currency == "CDF" else 0
			payload = {
				"doctype": "Sales Invoice",
				"company": COMPANY,
				"pos_profile": profile.name,
				"posa_pos_opening_shift": shift.name,
				"customer": customer,
				"currency": currency,
				"price_list_currency": "USD",
				"selling_price_list": profile.selling_price_list,
				"posting_date": nowdate(),
				"due_date": nowdate(),
				"is_pos": 1,
				"update_stock": 1,
				"ruhee_spike_rate": rate.name,
				"set_warehouse": profile.warehouse,
				"cost_center": profile.cost_center,
				"items": [
					{
						"item_code": "SPIKE-001",
						"qty": qty,
						"rate": unit,
						"price_list_rate": unit,
						"warehouse": profile.warehouse,
					}
				],
				"payments": [
					{
						"mode_of_payment": "Cash CDF" if paid else "Cash USD",
						"amount": paid,
						"posa_original_amount": paid,
						"posa_payment_currency": currency if paid else "USD",
					}
				],
			}
			draft = update_invoice(frappe.as_json(payload))
			response = submit_invoice(
				frappe.as_json(draft),
				frappe.as_json(
					{
						"pos_profile": profile.name,
						"posa_pos_opening_shift": shift.name,
						"is_credit_sale": not paid,
						"due_date": nowdate(),
					}
				),
			)
			doc = frappe.get_doc(response["doctype"], response["name"])
			pe = None
			if currency == "USD":
				pe = payment(doc, rate, allocated * rate.higher, allocated, nine_place=nine)
				doc.reload()
			rows.append(
				{
					"case": label,
					"invoice": invoice_evidence(doc),
					"ruhee_spike_rate": doc.ruhee_spike_rate,
					"payment_entry": pe,
				}
			)
	before = [invoice_evidence(frappe.get_doc("Sales Invoice", r["invoice"]["name"])) for r in rows]
	new_rate = frappe.get_doc(
		{
			"doctype": RATE_TYPE,
			"store": "New Depo",
			"date": nowdate(),
			"effective_time": now_datetime(),
			"base": 2400,
			"higher": 2420,
		}
	).insert()
	new_rate.submit()
	after = [invoice_evidence(frappe.get_doc("Sales Invoice", r["invoice"]["name"])) for r in rows]
	assert before == after
	closing = make_closing_shift_from_opening(frappe.as_json(shift.as_dict()))["closing_shift"].as_dict()
	for row in closing.get("payment_reconciliation", []):
		row["closing_amount"] = row.get("expected_amount", 0)
		row["closing_amount_in_currency"] = row.get("expected_amount_in_currency", 0)
	close_name = submit_closing_shift(frappe.as_json(closing))
	lock_terminal(profile.name)
	frappe.get_doc("User", cashier).update({"enabled": 0}).save()
	print(
		frappe.as_json(
			{
				"site": SCRATCH,
				"captured_at": str(now_datetime()),
				"store_rate": rate.as_dict(),
				"later_rate": new_rate.as_dict(),
				"company_rate_competitor": 9999,
				"cases": rows,
				"old_invoices_unchanged_after_new_store_record": before == after,
				"closing_shift": close_name,
			},
			indent=2,
		)
	)
	for row in rows:
		if row["case"] == "C3-store":
			assert row["invoice"]["items"][0]["rate"] == 230000
			assert row["invoice"]["base_grand_total"] == 100
			assert row["invoice"]["outstanding_amount"] == 0
		if row["case"] == "C5-store":
			assert row["invoice"]["outstanding_amount"] == 50
		if row["case"] in ("C4-store", "large-store"):
			allocated = 100 if row["case"] == "C4-store" else 10000
			expected_cash = 100.87 if allocated == 100 else 10086.96
			gl = row["payment_entry"]["gl"]
			assert sum(r.debit for r in gl if r.account == account("Cash CDF - New Depo")) == expected_cash
			assert sum(r.credit for r in gl if r.account == account("Debtors")) == allocated
			assert sum(r.credit for r in gl if r.account == account("Exchange income")) == flt(
				expected_cash - allocated, 2
			)
			assert row["invoice"]["outstanding_amount"] == 0
			assert not any(r.account == account("Exchange Gain/Loss") for r in gl)


def verify_existing():
	"""Read back saved prototype documents after schema/rate changes; no new bills."""
	guard()
	directory = Path(__file__).with_name("evidence")
	before = json.loads((directory / "m105_precision_before.json").read_text())
	old = frappe.get_doc("Sales Invoice", before["old_invoice"]["name"])
	assert invoice_evidence(old) == before["old_invoice"]
	evidence = json.loads((directory / "m105_store_prototype.json").read_text())
	pe_results = []
	for row in evidence["cases"]:
		doc = frappe.get_doc("Sales Invoice", row["invoice"]["name"])
		assert invoice_evidence(doc) == row["invoice"]
		assert doc.ruhee_spike_rate == evidence["store_rate"]["name"]
		if not row["payment_entry"]:
			continue
		pe = frappe.get_doc("Payment Entry", row["payment_entry"]["name"])
		for key in (
			"target_exchange_rate",
			"paid_amount",
			"received_amount",
			"base_received_amount",
			"ruhee_spike_rate",
		):
			assert pe.get(key) == row["payment_entry"][key]
		gl = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Payment Entry", "voucher_no": pe.name},
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
		assert gl == row["payment_entry"]["gl"]
		pe_results.append(
			{
				"name": pe.name,
				"saved_target_rate": pe.target_exchange_rate,
				"saved_base_received_amount": pe.base_received_amount,
				"gl_unchanged": True,
			}
		)
	print(
		frappe.as_json(
			{
				"site": SCRATCH,
				"captured_at": str(now_datetime()),
				"old_native_invoice_and_gl_unchanged": True,
				"store_invoices_and_links_unchanged": True,
				"saved_payment_entries": pe_results,
				"pause_scheduler": bool(frappe.conf.pause_scheduler),
				"scratch_sales_invoice_count": frappe.db.count("Sales Invoice"),
				"dev_site_queried": False,
			},
			indent=2,
		)
	)
