"""Disposable-only C3 experiments. Native POS methods, no monkeypatch or GL edits."""

import secrets

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import flt, now_datetime

from ruhee_erp.spike import c3_precision, c3_verify

RATE_TYPE = "Ruhee C3 Spike Rate"
PHASES = ("baseline", "source", "invoice", "payment", "ledger")
PROFILE = "C3 Precision Lab"


def guard():
	c3_verify.guard(c3_verify.DISPOSABLE)
	if not frappe.conf.get("pause_scheduler"):
		raise ValueError("Disposable scheduler must remain paused")


def prepare():
	guard()
	from posawesome.patches.add_per_payment_multi_currency_fields import execute

	from ruhee_erp.spike.setup_spike import run as setup

	setup()
	execute()
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
					{"fieldname": "base", "label": "Taux de base", "fieldtype": "Int", "reqd": 1},
					{"fieldname": "higher", "label": "Taux majoré", "fieldtype": "Int", "reqd": 1},
				],
				"permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "submit": 1}],
			}
		).insert()
	for doctype in ("Sales Invoice", "Currency Exchange"):
		if not frappe.get_meta(doctype).has_field("ruhee_c3_rate"):
			create_custom_field(
				doctype,
				{
					"fieldname": "ruhee_c3_rate",
					"label": "Taux du magasin (essai C3)",
					"fieldtype": "Link",
					"options": RATE_TYPE,
					"read_only": 1,
					"no_copy": 1,
				},
			)
	if not frappe.db.exists("POS Profile", PROFILE):
		profile = frappe.copy_doc(frappe.get_doc("POS Profile", "New Depo"))
		profile.name = PROFILE
		profile.update(
			{
				"create_pos_invoice_instead_of_sales_invoice": 0,
				"update_stock": 1,
				"posa_decimal_precision": 2,
				"posa_allow_multi_currency": 1,
				"posa_enable_multi_currency_payments": 1,
				"posa_allow_payment_currency_selection": 1,
				"posa_allow_manual_payment_exchange_rate": 0,
				"posa_allow_credit_sale": 1,
				"posa_allow_partial_payment": 1,
				"posa_block_sale_beyond_available_qty": 0,
				"posa_allow_submissions_in_background_job": 0,
				"account_for_change_amount": account("Cash USD - New Depo"),
			}
		)
		profile.append("applicable_for_users", {"user": "Administrator"})
		profile.insert()
	print("Invented C3 baseline ready; no precision changed")


def account(name):
	result = frappe.db.get_value("Account", {"company": c3_verify.COMPANY, "account_name": name})
	if not result:
		raise ValueError(f"Missing baseline account {name}")
	return result


def phase(label):
	guard()
	index = PHASES.index(label)
	date = ("2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04")[index]
	if frappe.db.exists("Currency Exchange", {"date": date, "from_currency": "CDF", "to_currency": "USD"}):
		raise ValueError(
			"This phase already has a rate record; never update/reuse a control as a fresh experiment"
		)
	from posawesome.posawesome.api.employees import (
		lock_terminal,
		save_cashier_pin,
		verify_terminal_employee_pin,
	)
	from posawesome.posawesome.api.invoice_processing.creation import submit_invoice, update_invoice
	from posawesome.posawesome.api.invoice_processing.utils import resolve_erpnext_currency_rates

	if index:
		c3_precision.inspect(c3_verify.DISPOSABLE, through=index)
	rate_doc = frappe.get_doc(
		{"doctype": RATE_TYPE, "store": "New Depo", "date": date, "base": 2300, "higher": 2320}
	).insert()
	rate_doc.submit()
	precision = int(frappe.get_meta("Currency Exchange").get_field("exchange_rate").precision)
	source = frappe.get_doc(
		{
			"doctype": "Currency Exchange",
			"date": date,
			"from_currency": "CDF",
			"to_currency": "USD",
			"exchange_rate": flt(1 / rate_doc.base, precision),
			"for_selling": 1,
			"for_buying": 1,
			"ruhee_c3_rate": rate_doc.name,
		}
	).insert()
	source.reload()
	profile = frappe.get_doc("POS Profile", PROFILE)
	cashier = f"c3-{frappe.generate_hash(length=10).lower()}@example.com"
	frappe.get_doc(
		{
			"doctype": "User",
			"email": cashier,
			"first_name": "C3",
			"last_name": "Spike",
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
			"company": c3_verify.COMPANY,
			"pos_profile": profile.name,
			"user": "Administrator",
			"period_start_date": now_datetime(),
			"posting_date": date,
			"balance_details": [
				{"mode_of_payment": "Cash USD", "amount": 0, "currency": "USD"},
				{"mode_of_payment": "Cash CDF", "amount": 0, "currency": "CDF"},
			],
		}
	).insert()
	shift.submit()
	rates = resolve_erpnext_currency_rates("CDF", "USD", "USD", date)
	assert rates["conversion_rate"] == source.exchange_rate
	output = {
		"site": c3_verify.DISPOSABLE,
		"phase": label,
		"commits": c3_verify.app_commits(),
		"trace": c3_verify.field_trace(),
		"source": source.as_dict(),
		"store_record": rate_doc.as_dict(),
		"browser_verified": False,
		"cases": [],
	}
	# Boundary prices are reported, not silently replaced by exact direct quotes.
	for case, usd, qty in (
		("C3-01", 100, 1),
		("C3-02", 100, 100),
		("unit-3000", 3000, 1),
		("unit-3200", 3200, 1),
	):
		unit = flt(usd * rates["plc_conversion_rate"] / rates["conversion_rate"], 2)
		tender = usd * qty * rate_doc.base
		payload = {
			"doctype": "Sales Invoice",
			"company": c3_verify.COMPANY,
			"pos_profile": profile.name,
			"posa_pos_opening_shift": shift.name,
			"customer": frappe.db.get_value("Customer", {"customer_name": "SPIKE-02 Client A"}),
			"currency": "CDF",
			"price_list_currency": "USD",
			"selling_price_list": profile.selling_price_list,
			"conversion_rate": rates["conversion_rate"],
			"plc_conversion_rate": 1,
			"ruhee_c3_rate": rate_doc.name,
			"posting_date": date,
			"set_posting_time": 1,
			"due_date": date,
			"is_pos": 1,
			"update_stock": 1,
			"set_warehouse": profile.warehouse,
			"cost_center": profile.cost_center,
			"account_for_change_amount": profile.account_for_change_amount,
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
					"mode_of_payment": "Cash CDF",
					"account": account("Cash CDF - New Depo"),
					"amount": tender,
					"posa_original_amount": tender,
					"posa_payment_currency": "CDF",
				}
			],
		}
		draft = update_invoice(frappe.as_json(payload))
		result = submit_invoice(
			frappe.as_json(draft),
			frappe.as_json(
				{"pos_profile": profile.name, "posa_pos_opening_shift": shift.name, "due_date": date}
			),
		)
		values = c3_verify.snapshot(c3_verify.DISPOSABLE, result["name"])
		output["cases"].append(
			{
				"case": case,
				"input_usd": usd,
				"calculated_unit_price": unit,
				"exact_direct_unit_price": usd * rate_doc.base,
				"payload": payload,
				"draft_conversion_rate": draft["conversion_rate"],
				**values,
				"errors": c3_verify.check(values, qty=qty) if usd == 100 else [],
			}
		)
	from posawesome.posawesome.doctype.pos_closing_shift.closing_processing.creation import (
		make_closing_shift_from_opening,
		submit_closing_shift,
	)

	closing = make_closing_shift_from_opening(frappe.as_json(shift.as_dict()))["closing_shift"].as_dict()
	for row in closing.get("payment_reconciliation", []):
		row["closing_amount"] = row.get("expected_amount", 0)
		row["closing_amount_in_currency"] = row.get("expected_amount_in_currency", 0)
	submit_closing_shift(frappe.as_json(closing))
	lock_terminal(profile.name)
	frappe.get_doc("User", cashier).update({"enabled": 0}).save()
	print(frappe.as_json(output))
	return {"phase": label, "C3_acceptance": "not claimed"}


def customize():
	"""Exercise the actual Customize Form save method on disposable, without UI claims."""
	guard()
	doc = frappe.get_doc("Customize Form")
	doc.doc_type = "Sales Invoice"
	doc.run_method("fetch_to_customize")
	doc.run_method("save_customization")
	c3_precision.inspect(c3_verify.DISPOSABLE)


def resync():
	"""Force native JSON reimport without modifying upstream files. Never repairs."""
	guard()
	for doctype in dict(c3_verify.FIELDS):
		frappe.reload_doctype(doctype, force=True)
	print(frappe.as_json({"after_force_reload": c3_verify.field_trace()}))
	# Caller runs migrate, then c3_precision.inspect in another bench command.
